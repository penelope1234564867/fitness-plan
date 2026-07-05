"""CoachAgent — 用户画像分析 + 周总结 + 动作备注生成

使用 HelloAgents 的 PlanAndSolveAgent（先规划再执行的 Agent）。
负责所有"人话"部分：分析用户、写总结、加教练备注。

职责：
  - analyze_user() → 用户画像总结（目标/经验/注意事项）
  - generate_weekly_summary() → 周训练总结 + 下周预览
  - add_reasoning() → 为每个动作生成"教练说"
"""

import json
from typing import Optional, List, Dict, Any

from hello_agents import PlanAndSolveAgent
from app.services.llm_service import get_llm, get_fast_llm


# ── 系统提示词 ──────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个专业、有同理心的健身教练。你的职责是：
1. 分析用户画像，理解他们的目标、经验水平和身体条件
2. 为每个训练动作提供简明实用的"教练说"备注
3. 生成周训练总结，给予鼓励和具体反馈

你的风格：专业但不学术，鼓励但不浮夸，具体但不啰嗦。"""


# ── 画像分析 Prompt ──────────────────────────────────────────

ANALYZE_PROMPT = """分析以下用户信息，生成一份用户画像总结。

用户信息：
- 目标: {goal}
- 经验水平: {experience}
- 训练地点: {location}
- 每周天数: {days_per_week}
- 身高: {height}cm, 体重: {weight}kg, 年龄: {age}岁, 性别: {gender}
- 城市: {city}

请输出严格 JSON（不要 markdown 代码块，不要添加额外字段，不要中英文重复）：
{{
  "profile_summary": "一句话概括用户画像，如'新手增肌，居家哑铃训练'",
  "training_phase": "适合的训练阶段，可选 foundational / hypertrophy / strength",
  "focus_points": ["针对该用户的 2-3 个训练重点"],
  "precautions": ["需要注意的事项，如'新手优先学动作模式'、'体重较大注意关节保护'"],
  "coach_advice": "给用户的入门建议，50字以内"
}}"""


# ── 周总结 Prompt ────────────────────────────────────────────

WEEKLY_SUMMARY_PROMPT = """根据以下训练数据，生成周总结。

用户画像: {profile_summary}
本周完成率: {completion_rate}%
高 RPE 动作占比: {high_rpe_ratio}%
训练天数: {days_completed}/{days_total}

本周训练详情:
{day_details}

请输出 JSON 格式（不要 markdown 代码块）：
{{
  "week_summary": "一句话总结本周表现",
  "highlights": ["2-3 个亮点"],
  "improvements": ["1-2 个改进点"],
  "next_week_focus": "下周训练重点",
  "coach_message": "教练的话（鼓励为主，50字以内）"
}}"""


# ── 动作备注 Prompt ──────────────────────────────────────────

REASONING_PROMPT = """为以下训练日计划添加教练备注。

用户画像: {profile_summary}

训练日: {day_name} — {focus}
目标: {goal}

动作列表:
{exercises_text}

对每个动作，生成一句简短实用的教练备注（20字内）。
备注要求：具体、可操作，如"肘部回收，感受胸肌发力"而不是"注意姿势"。

请输出 JSON 格式（不要 markdown 代码块）：
{{
  "remarks": [
    {{"wger_id": 123, "coach_says": "肘部回收，感受胸肌发力"}},
    ...
  ]
}}"""


# ═══════════════════════════════════════════════════════════════
#  CoachAgent 类
# ═══════════════════════════════════════════════════════════════

class CoachAgent:
    """教练 Agent — 用户画像分析 + 周总结 + 备注生成。

    同步方法设计，由调用方（plan_service）决定在 async 上下文中
    用 run_in_executor 或在 sync 上下文中直接调用。
    """

    def __init__(self):
        self._agent = PlanAndSolveAgent(
            name="CoachAgent",
            llm=get_llm(),
            system_prompt=SYSTEM_PROMPT,
        )
        self._fast_llm = get_fast_llm()

    # ── 公开方法 ──────────────────────────────────────────

    def analyze_user(self, request) -> dict:
        """分析用户信息，生成用户画像总结。

        Args:
            request: InitPlanRequest 对象（含 goal, experience_level, ...）

        Returns:
            dict: {"profile_summary", "training_phase", "focus_points",
                   "precautions", "coach_advice"}
        """
        gender_cn = {"male": "男", "female": "女"}.get(
            request.gender, request.gender or "未知"
        )
        prompt = ANALYZE_PROMPT.format(
            goal=request.goal,
            experience=request.experience_level,
            location=request.workout_location,
            days_per_week=request.days_per_week,
            height=request.height or "未知",
            weight=request.weight or "未知",
            age=request.age or "未知",
            gender=gender_cn,
            city=request.city or "未知",
        )

        text = self._agent.run(input_text=prompt).strip()
        return self._parse_json(text, {
            "profile_summary": f"{request.experience_level}{request.goal}",
            "training_phase": "foundational"
                if request.experience_level == "新手" else "hypertrophy",
            "focus_points": [],
            "precautions": [],
            "coach_advice": "",
        })

    def add_reasoning(self, day_plan: dict, profile: dict, goal: str) -> dict:
        """为训练计划中的每个主项动作添加教练备注。

        Args:
            day_plan: assemble_one_day 返回的单天计划
            profile: analyze_user 返回的用户画像
            goal: 用户目标

        Returns:
            dict: 添加了 coach_says 字段的 day_plan
        """
        main_exercises = day_plan.get("main", [])
        if not main_exercises:
            return day_plan

        ex_lines = "\n".join(
            f"  [{ex.get('wger_id', '?')}] {ex.get('name', '')} — "
            f"{ex.get('target_muscle', '')}"
            for ex in main_exercises
        )
        prompt = REASONING_PROMPT.format(
            profile_summary=profile.get("profile_summary", ""),
            day_name=day_plan.get("day", ""),
            focus=day_plan.get("focus", ""),
            goal=goal,
            exercises_text=ex_lines,
        )

        text = self._invoke_fast(prompt)
        result = self._parse_json(text, {"remarks": []})
        remark_map = {
            r.get("wger_id"): r.get("coach_says", "")
            for r in result.get("remarks", []) if r.get("wger_id")
        }
        for ex in main_exercises:
            wid = ex.get("wger_id")
            ex["coach_says"] = remark_map.get(wid, "")

        day_plan["main"] = main_exercises
        return day_plan

    def generate_weekly_summary(self, profile: dict, week_data: dict) -> dict:
        """生成周训练总结。

        Args:
            profile: analyze_user 返回的用户画像
            week_data: 包含 completion_rate, high_rpe_ratio, days 等

        Returns:
            dict: {"week_summary", "highlights", "improvements",
                   "next_week_focus", "coach_message"}
        """
        day_details = "\n".join(
            f"  {d.get('day_label', '')} ({d.get('focus', '')}) — "
            f"{'✅ 完成' if d.get('is_completed') else '⏳ 未完成'}"
            for d in week_data.get("days", [])
        )

        prompt = WEEKLY_SUMMARY_PROMPT.format(
            profile_summary=profile.get("profile_summary", ""),
            completion_rate=week_data.get("completion_rate", 0),
            high_rpe_ratio=week_data.get("high_rpe_ratio", 0),
            days_completed=week_data.get("days_completed", 0),
            days_total=week_data.get("days_total", 0),
            day_details=day_details,
        )

        text = self._agent.run(input_text=prompt).strip()
        return self._parse_json(text, {
            "week_summary": "本周训练完成",
            "highlights": [],
            "improvements": [],
            "next_week_focus": "继续按计划训练",
            "coach_message": "坚持训练，加油！",
        })

    # ── 内部方法 ──────────────────────────────────────────

    def _invoke_fast(self, prompt: str) -> str:
        """调用快速 LLM，返回纯文本。"""
        collected = []
        for chunk in self._fast_llm.stream_invoke(
            [{"role": "user", "content": prompt}],
            max_tokens=2048,
        ):
            collected.append(chunk)
        text = "".join(collected).strip()
        return text.replace("```json", "").replace("```", "").strip()

    @staticmethod
    def _parse_json(text: str, default: dict) -> dict:
        """安全解析 LLM 返回的 JSON。"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            print(f"  ⚠️ CoachAgent JSON 解析失败，使用默认值")
            return default
