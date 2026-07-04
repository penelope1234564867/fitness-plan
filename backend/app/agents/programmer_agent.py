"""ProgrammerAgent — 选动作 + 排组次数 + 渐进超负荷

使用 HelloAgents 的 ReActAgent（推理 + 行动）。
核心负责所有"编程"决策：选什么动作、做几组几次、何时加量。

职责：
  - select_exercises() → 从 wger 搜索 + LLM 精选候选动作
  - build_week_plan() → 为整周生成完整训练计划
  - calculate_progression() → 基于打卡数据的渐进超负荷
  - rotate_exercises() → 中周期边界时的动作轮换
"""

import json
import asyncio
from typing import List, Dict, Any, Optional, Callable

from hello_agents import ReActAgent
from sqlalchemy.orm import Session

from app.services.llm_service import get_llm, get_fast_llm
from app.agents import exercise_agent
from app.agents.plan_assembler import assemble_one_day
from app.engine.progressive_overload import calc_next_week_params, calc_deload_params
from app.engine.exercise_rotation import rotate_slots_for_new_mesocycle


# ── 系统提示词 ──────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个专业健身编程师（Programmer）。
你的职责是根据科学训练原则，为用户编排训练计划。

核心原则：
1. 渐进超负荷 — 每周逐步增加训练刺激
2. 分化训练 — PPL（推/拉/腿）三分化
3. 复合优先 — 复合动作在前，孤立动作在后
4. 动作轮换 — 每 4 周调整动作变式

你的输出始终是结构化 JSON。"""


# ── 选动作提示词 ────────────────────────────────────────────

SELECT_PROMPT = """根据用户画像，从候选动作中精选最适合的动作。

用户画像: {profile_summary}
训练日: {day_name} — {focus}
目标: {goal}
经验: {experience}
地点: {location}

候选动作（每个肌群最多 15 个）:
{grouped_data}

精选规则:
- {experience_guide}
- 优先选择标记了 [有图] 的动作（有示范图片）
- 同一天的不同肌群间动作要有区分度（不同器材/模式）
- 每个肌群选 {per_group} 个

只输出 JSON: {{"selected": [{{"wger_id": 123, "muscle_id": 4}}, ...]}}
不要 markdown 代码块，不要多余文字。"""


# ═══════════════════════════════════════════════════════════════
#  ProgrammerAgent 类
# ═══════════════════════════════════════════════════════════════

class ProgrammerAgent:
    """训练编程 Agent — 选动作、排计划、算渐进。"""

    def __init__(self):
        self._agent = ReActAgent(
            name="ProgrammerAgent",
            llm=get_llm(),
            system_prompt=SYSTEM_PROMPT,
        )
        self._fast_llm = get_fast_llm()

    # ═══════════════════════════════════════════════════════════
    #  公开方法
    # ═══════════════════════════════════════════════════════════

    def select_exercises(
        self,
        muscle_ids: List[int],
        profile: dict,
        goal: str,
        experience: str,
        location: str,
        per_group: int = 3,
        split_name: str = "",
        user_desc: str = "",
    ) -> List[dict]:
        """从 wger 搜索 + LLM 精选最优动作。

        Args:
            muscle_ids: 当天涉及的 wger 肌群 ID 列表
            profile: 用户画像（含 profile_summary）
            goal, experience, location: 用户训练参数
            per_group: 每个肌群选几个动作
            split_name: 分化方案名称
            user_desc: 用户描述（额外信息）

        Returns:
            List[dict]: [{wger_id, name, muscle_id, equipment, image_url}, ...]
        """
        # 1. Map-Reduce 搜索所有肌群
        grouped = exercise_agent.search_all_muscles(muscle_ids)

        # 2. 器材过滤
        filtered = exercise_agent.filter_by_equipment(grouped, experience)

        # 3. LLM 精选
        selected = self._llm_select(
            filtered, profile, goal, experience, location,
            split_name, per_group, user_desc,
        )
        return selected

    def build_week_plan(
        self,
        schedule: List[dict],
        profile: dict,
        goal: str,
        experience: str,
        location: str,
        emit: Optional[Callable] = None,
        user_desc: str = "",
    ) -> List[dict]:
        """为整周生成完整训练计划（每 天 并行）。

        Args:
            schedule: 分化排期 [{day, focus, muscles, ...}]
            profile: 用户画像
            goal, experience, location: 训练参数
            emit: 可选 SSE 事件发送函数
            user_desc: 额外用户描述

        Returns:
            List[dict]: 每天的计划 [{day, focus, warmup, main, cardio, stretch}, ...]
        """
        week_plans = []
        for i, day_spec in enumerate(schedule):
            day_index = i + 1
            self._emit(emit, "progress", {
                "day": day_index, "phase": "search",
                "text": f"🔍 正在搜索 {day_spec['focus']} 相关动作...",
            })

            muscle_ids = day_spec.get("muscles", day_spec.get("muscle_ids", []))
            selected = self.select_exercises(
                muscle_ids, profile, goal, experience, location,
                per_group=3, user_desc=user_desc,
            )

            if not selected:
                self._emit(emit, "progress", {
                    "day": day_index, "phase": "select",
                    "text": f"⚠️ 第{day_index}天未找到合适动作",
                })
                week_plans.append({
                    "day": day_spec.get("day", f"第{day_index}天"),
                    "focus": day_spec.get("focus", ""),
                    "warmup": [], "main": [], "cardio": None, "stretch": [],
                })
                continue

            self._emit(emit, "progress", {
                "day": day_index, "phase": "assemble",
                "text": f"🔧 正在组装 {day_spec['focus']} 训练...",
            })

            day_plan = assemble_one_day(
                day_spec, selected, goal, experience, location, user_desc,
            )

            if day_plan is None:
                day_plan = {
                    "day": day_spec.get("day", ""),
                    "focus": day_spec.get("focus", ""),
                    "warmup": [], "main": selected, "cardio": None, "stretch": [],
                }

            week_plans.append(day_plan)

            self._emit(emit, "day_done", {
                "day": day_index,
                "focus": day_spec.get("focus", ""),
                "main_count": len(day_plan.get("main", [])),
            })

        return week_plans

    def calculate_progression(
        self,
        prev_slot,
        phase: str,
    ) -> dict:
        """基于前一周的打卡数据计算下周训练参数。

        Args:
            prev_slot: 前一周的 exercise_slot（含实际完成数据）
            phase: 当前阶段 foundational / hypertrophy / strength / deload

        Returns:
            dict: {target_sets, target_reps, target_reps_max, weight_kg, rest_seconds}
        """
        if phase == "deload":
            return calc_deload_params(prev_slot)
        return calc_next_week_params(prev_slot, phase)

    def rotate_exercises(
        self,
        slots: List,
        db: Session,
    ) -> List[dict]:
        """中周期边界时轮换动作。

        Args:
            slots: 当前中周期最后一周的 exercise_slot 列表
            db: 数据库 session

        Returns:
            List[dict]: [{slot_id, new_exercise_id, old_exercise_id}, ...]
        """
        return rotate_slots_for_new_mesocycle(slots, db)

    # ═══════════════════════════════════════════════════════════
    #  新增：从本地缓存池精选（generate_next_week 重构）
    # ═══════════════════════════════════════════════════════════

    def select_from_pool(
        self,
        candidates: list,
        day_spec: dict,
        profile: dict,
        goal: str,
        experience: str,
        location: str,
        user_desc: str = "",
        exclude_names: Optional[list] = None,
        user_state: Optional[dict] = None,
    ) -> list:
        """从本地缓存池中精选动作（不调 wger）。

        与 select_exercises 的区别：
        - 数据源是候选列表（已从 mesocycle_exercise_pool 获取），不是 wger API
        - 传入 exclude_names（上周已选），LLM 会选不同的组合
        - 传入 user_state（压缩历史），LLM 了解用户状态

        Args:
            candidates: 候选动作列表 [{"wger_id", "name", "target_muscle", ...}]
            day_spec: 当天规格 {"day_label", "focus", "muscle_ids"}
            profile: 用户画像
            goal: 用户目标
            experience: 经验水平
            location: 训练地点
            user_desc: 用户描述
            exclude_names: 上周已选动作名列表
            user_state: 用户压缩历史 {"avg_completion_rate", "rpe_trend", ...}

        Returns:
            List[dict]: [{wger_id, name, target_muscle, image_url, ...}, ...]
        """
        if not candidates:
            return []

        exclude_set = set(exclude_names or [])

        # 过滤掉排除列表中的动作
        filtered = [c for c in candidates if c.get("name") not in exclude_set]

        if not filtered:
            # 全部被排除 → 使用全部候选（让 LLM 重新选）
            filtered = candidates

        # 动态计算每个肌群选几个：单肌群日选多些（核心日需要更多动作），多肌群日 2-3 个
        unique_muscle_groups = set(
            c.get("muscle_group_id", 0) for c in filtered if c.get("muscle_group_id")
        )
        num_groups = len(unique_muscle_groups)
        per_group = 5 if num_groups <= 1 else 3

        # 构建候选文本
        items = "\n".join(
            f"  [{c['wger_id']}] {c.get('name', '')} — {c.get('target_muscle', '未知肌群')}"
            f"{' [有图]' if c.get('image_url') else ' [无图]'}"
            for c in filtered
        )

        exclude_text = ""
        if exclude_names:
            exclude_text = f"\n上周已选动作: {', '.join(exclude_names[:10])}"

        user_state_text = ""
        if user_state:
            user_state_text = (
                f"\n用户历史: 平均完成率={user_state.get('avg_completion_rate', 0)*100:.0f}%, "
                f"RPE 趋势={user_state.get('rpe_trend', '稳定')}, "
                f"连续完成={user_state.get('consecutive_weeks_completed', 0)}周"
            )

        # 阶段 → 组/次数范围
        PHASE_REP_RANGES = {
                   "foundational": "每组 12-15 次，2-3 组，选轻/中等重量，以学会动作为主",
                   "hypertrophy": "每组 8-12 次，3-4 组，选中等重量，追求训练容量",
                   "strength": "每组 5-8 次，4-5 组，选大重量（75-85% 1RM），组间休息 2-3 分钟",
                   "deload": "每组 10-12 次，2 组，重量降低 50%，以恢复为主",
               }
        rep_guide = PHASE_REP_RANGES.get(goal, PHASE_REP_RANGES["foundational"])

               prompt = f"""你是一个专业健身教练。从候选动作中精选最适合当天训练的动作。

训练日: {day_spec.get('day_label', '')} — {day_spec.get('focus', '')}
当前阶段: {goal}
用户经验: {experience}
训练地点: {location}
用户画像: {profile.get('profile_summary', '')}

当前阶段训练参数指导:
{rep_guide}

候选动作:
{items}

选动作规则:
1. 复合动作（多关节）优先，孤立动作在后
2. 优先选择有示范图片的动作 [有图]
3. 不同肌群间动作要有区分度（不同器材/模式）
4. 每个肌群选 {per_group} 个{exclude_text}{user_state_text}
5. 请选择与上周不同的组合，保持训练的多样性

输出的 sets 和 reps 必须符合当前阶段的训练参数指导。
动作名请翻译成中文，如 "Leg Press" → "腿举"，"Lat Pull Down" → "高位下拉"。

只输出 JSON: {{"selected": [{{"wger_id": 123, "name": "中文动作名", "sort_order": 1, "sets": 3, "reps": 10, "rest_seconds": 60}}, ...]}}
不要 markdown 代码块，不要多余文字。"""

        text = self._invoke_fast(prompt)
        try:
            result = json.loads(text)
            raw_selected = result.get("selected", [])
            selected_ids = {item["wger_id"] for item in raw_selected}
        except (json.JSONDecodeError, KeyError) as e:
            num_groups_fb = len(set(c.get('muscle_group_id') for c in filtered if c.get('muscle_group_id')))
            fb_count = 8 if num_groups_fb <= 1 else 6
            print(f"  ⚠️ select_from_pool LLM 解析失败: {e}，使用前 {fb_count} 个")
            return filtered[:fb_count]

        # 按选中 ID 从候选中提取，并回填 LLM 给出的组次数参数和中文名
        selected_map = {item["wger_id"]: item for item in raw_selected}
        result_list = []
        for c in filtered:
            wid = c["wger_id"]
            if wid in selected_ids:
                llm_params = selected_map.get(wid, {})
                # LLM 返回的 name（中文）优先，兜底用缓存池中的原始名
                llm_name = llm_params.get("name", "").strip()
                result_list.append({
                    "wger_id": wid,
                    "name": llm_name if llm_name else c.get("name", ""),
                    "target_muscle": c.get("target_muscle", ""),
                    "muscle_group_id": c.get("muscle_group_id", ""),
                    "equipment": c.get("equipment", ""),
                    "image_url": c.get("image_url", ""),
                    "description": c.get("description", ""),
                    "difficulty": c.get("difficulty", 1),
                    "sets": llm_params.get("sets", 3),
                    "reps": llm_params.get("reps", 10),
                    "rest_seconds": llm_params.get("rest_seconds", 60),
                })

        return result_list

    # ═══════════════════════════════════════════════════════════
    #  内部方法
    # ═══════════════════════════════════════════════════════════

    def _llm_select(
        self,
        grouped: Dict[int, List[dict]],
        profile: dict,
        goal: str,
        experience: str,
        location: str,
        split_name: str = "",
        per_group: int = 3,
        user_desc: str = "",
    ) -> List[dict]:
        """LLM 从候选动作中精选最优。"""
        # 构建 grouped_data 文本
        id_to_name = {v: k for k, v in exercise_agent.MUSCLES.items()}
        lines = []
        for mid, exs in grouped.items():
            if not exs:
                continue
            name = id_to_name.get(mid, str(mid))
            items = ", ".join(
                f"[{e['wger_id']}] {e['name']}{'[有图]' if e.get('image_url') else '[无图]'}"
                for e in exs
            )
            lines.append(f"  {name}(ID={mid}): {items}")

        experience_guide = exercise_agent.EXPERIENCE_GUIDE.get(
            experience, exercise_agent.EXPERIENCE_GUIDE["中级"]
        )
        prompt = SELECT_PROMPT.format(
            profile_summary=profile.get("profile_summary", ""),
            day_name=split_name,
            focus=split_name,
            goal=goal, experience=experience, location=location,
            grouped_data="\n".join(lines),
            experience_guide=experience_guide,
            per_group=per_group,
        )

        if user_desc:
            prompt += (
                f"\n\n用户信息: {user_desc}\n"
                f"请根据用户的体能水平选择合适的动作。"
            )

        text = self._invoke_fast(prompt)
        try:
            result = json.loads(text)
            raw_selected = result.get("selected", [])
            selected_ids = {(item["wger_id"], item["muscle_id"]) for item in raw_selected}
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  ⚠️ ProgrammerAgent LLM 解析失败: {e}")
            selected = []
            for mid, exs in grouped.items():
                for ex in exs[:per_group]:
                    selected.append(ex)
            return selected

        selected = []
        for mid, exs in grouped.items():
            count = 0
            for ex in exs:
                if (ex["wger_id"], mid) in selected_ids and count < per_group:
                    selected.append(ex)
                    count += 1
        return selected

    def _invoke_fast(self, prompt: str) -> str:
        """调用快速 LLM，返回纯文本。"""
        collected = []
        for chunk in self._fast_llm.stream_invoke(
            [{"role": "user", "content": prompt}],
            max_tokens=4096,
        ):
            collected.append(chunk)
        text = "".join(collected).strip()
        return text.replace("```json", "").replace("```", "").strip()

    @staticmethod
    def _emit(emit_fn, event_type: str, data: dict):
        """安全发送 SSE 事件。"""
        if emit_fn:
            emit_fn(event_type, data)
