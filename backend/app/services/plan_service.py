"""健身计划服务 — Agent 编排层

架构（2026-07 重构）:
  PlanService (总指挥)
    → CoachAgent 分析用户画像
    → ProgrammerAgent 搜索 + 精选动作
    → PlanAssembler 组装每日训练（纯函数）
    → CoachAgent 生成教练备注

  PlanService.analyze_week()
    → AnalystAgent 分析打卡数据
    → ProgrammerAgent 执行渐进超负荷
    → CoachAgent 生成周总结

SSE 事件协议（向后兼容）:
  progress     → {"day":N, "phase":"search|select|assemble", "text":"..."}
  llm_stream   → {"day":N, "phase":"select|assemble", "chunk":"..."}
  exercise_done → {"day":N, "exercise":{"name":"...","sets":4,"reps":8,"wger_id":123}}
  day_done     → {"day":N, "focus":"...", "main_count":5}
  done         → {"id":123, "weekly_plans":[...]}
"""

import json
import asyncio
import traceback
from typing import AsyncGenerator, Optional, Callable

from sqlalchemy.orm import Session

from app.models.schemas import InitPlanRequest
from app.models.orm_models import FitnessPlan, Macrocycle, Mesocycle, Week, Day
from app.agents.coach_agent import CoachAgent
from app.agents.programmer_agent import ProgrammerAgent
from app.agents.analyst_agent import AnalystAgent


# ═══════════════════════════════════════════════════════════════
#  Agent 实例（单例）
# ═══════════════════════════════════════════════════════════════

_coach: Optional[CoachAgent] = None
_programmer: Optional[ProgrammerAgent] = None
_analyst: Optional[AnalystAgent] = None


def get_coach() -> CoachAgent:
    global _coach
    if _coach is None:
        _coach = CoachAgent()
    return _coach


def get_programmer() -> ProgrammerAgent:
    global _programmer
    if _programmer is None:
        _programmer = ProgrammerAgent()
    return _programmer


def get_analyst() -> AnalystAgent:
    global _analyst
    if _analyst is None:
        _analyst = AnalystAgent()
    return _analyst


# ═══════════════════════════════════════════════════════════════
#  PPL 分化方案
# ═══════════════════════════════════════════════════════════════

PPL_SPLITS = {
    "ppl_3": {
        "name": "PPL（推/拉/腿）",
        "days": 3,
        "per_group": 3,
        "schedule": [
            {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "day_label": "推",
             "desc": "训练胸大肌、三角肌和肱三头肌，以推类复合动作为主"},
            {"day": "第2天 · 拉", "focus": "背部 + 二头", "muscles": [12, 1], "day_label": "拉",
             "desc": "训练背阔肌、菱形肌和肱二头肌，以拉类复合动作为主"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部 + 腹部", "muscles": [10, 11, 8, 6], "day_label": "腿",
             "desc": "训练股四头肌、腘绳肌、臀大肌和腹部"},
        ],
    },
    "ppl_4": {
        "name": "PPL + 全身补充",
        "days": 4,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "day_label": "推"},
            {"day": "第2天 · 拉", "focus": "背部 + 二头", "muscles": [12, 1], "day_label": "拉"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部", "muscles": [10, 11, 8], "day_label": "腿"},
            {"day": "第4天 · 全身", "focus": "全身轻量 + 腹部", "muscles": [4, 12, 6], "day_label": "全身"},
        ],
    },
    "ppl_5": {
        "name": "PPL + 弱项强化",
        "days": 5,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推(主)", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "day_label": "推"},
            {"day": "第2天 · 拉(主)", "focus": "背部 + 二头", "muscles": [12, 1], "day_label": "拉"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部 + 腹部", "muscles": [10, 11, 8, 6], "day_label": "腿"},
            {"day": "第4天 · 推(辅)", "focus": "肩部 + 三头 + 胸部轻量", "muscles": [2, 5, 4], "day_label": "推"},
            {"day": "第5天 · 拉(辅)", "focus": "二头 + 斜方肌 + 背部轻量", "muscles": [1, 9, 12], "day_label": "拉"},
        ],
    },
    "ppl_6": {
        "name": "PPL × 2（重量+容量）",
        "days": 6,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推(重)", "focus": "胸部 + 肩部 + 三头（大重量）", "muscles": [4, 2, 5], "day_label": "推"},
            {"day": "第2天 · 拉(重)", "focus": "背部 + 二头（大重量）", "muscles": [12, 1], "day_label": "拉"},
            {"day": "第3天 · 腿(重)", "focus": "腿部 + 臀部（大重量）", "muscles": [10, 11, 8], "day_label": "腿"},
            {"day": "第4天 · 推(轻)", "focus": "胸部 + 肩部 + 三头（增肌容量）", "muscles": [4, 2, 5], "day_label": "推"},
            {"day": "第5天 · 拉(轻)", "focus": "背部 + 二头（增肌容量）", "muscles": [12, 1], "day_label": "拉"},
            {"day": "第6天 · 腿(轻)", "focus": "腿部 + 腹部（增肌容量）", "muscles": [10, 11, 6], "day_label": "腿"},
        ],
    },
}


# ═══════════════════════════════════════════════════════════════
#  PlanService — 编排器
# ═══════════════════════════════════════════════════════════════

class PlanService:
    """训练计划编排服务。

    职责：
      1. 首次生成：CoachAgent(画像) → ProgrammerAgent(选动作+组装) → CoachAgent(备注)
      2. 每周调整：AnalystAgent(分析) → ProgrammerAgent(渐进) → CoachAgent(总结)
      3. SSE 流式推送
    """

    def __init__(self):
        self.coach = get_coach()
        self.programmer = get_programmer()
        self.analyst = get_analyst()

    # ═══════════════════════════════════════════════════════════
    #  首次生成（新 Agent 编排方式）
    # ═══════════════════════════════════════════════════════════

    async def generate_plan(
        self,
        request: InitPlanRequest,
        emit: Callable,
    ) -> dict:
        """完整链路生成：CoachAgent → ProgrammerAgent → PlanAssembler → CoachAgent。

        Args:
            request: InitPlanRequest 用户请求
            emit: SSE 事件发送函数 f(event_type, data)

        Returns:
            dict: {profile, weekly_plans: [{week, days}], ...}
        """
        loop = asyncio.get_running_loop()

        # ── Step 1: CoachAgent 分析用户画像 ──
        emit("progress", {"phase": "coach",
                           "text": "🤖 CoachAgent 正在分析用户画像..."})

        profile = await loop.run_in_executor(
            None, self.coach.analyze_user, request,
        )
        emit("progress", {"phase": "coach",
                           "text": f"✅ 画像分析完成：{profile.get('profile_summary', '')}"})

        # ── Step 2: 确定分化方案 ──
        ppl_key = f"ppl_{request.days_per_week}"
        split = PPL_SPLITS.get(ppl_key, PPL_SPLITS["ppl_3"])
        schedule = split["schedule"]
        user_desc = self._build_user_desc(request)

        emit("progress", {"phase": "programmer",
                           "text": f"📋 分化方案：{split['name']}，{len(schedule)} 天"})

        # ── Step 3: ProgrammerAgent 选动作 + PlanAssembler 组装 ──
        week_plans = await loop.run_in_executor(
            None, self.programmer.build_week_plan,
            schedule, profile, request.goal, request.experience_level,
            request.workout_location, emit, user_desc,
        )

        # ── Step 4: CoachAgent 为每天加教练备注 ──
        for idx, day_plan in enumerate(week_plans):
            if day_plan.get("main"):
                emit("progress", {
                    "day": idx + 1, "phase": "coach",
                    "text": f"🤖 正在为第{idx+1}天生成教练备注...",
                })
                day_plan = await loop.run_in_executor(
                    None, self.coach.add_reasoning,
                    day_plan, profile, request.goal,
                )
                week_plans[idx] = day_plan

        # ── 返回结果 ──
        return {
            "profile": profile,
            "weekly_plans": [{"week": 1, "days": week_plans}],
            "split_name": split["name"],
        }

    # ═══════════════════════════════════════════════════════════
    #  周分析和调整
    # ═══════════════════════════════════════════════════════════

    async def analyze_week_and_adjust(
        self,
        days: list,
        profile: dict,
        emit: Callable,
    ) -> dict:
        """分析一周打卡 + 生成调整建议。

        Args:
            days: 本周所有 Day 对象（含 slots）
            profile: 用户画像
            emit: SSE 事件发送函数（同步回调）

        Returns:
            dict: {analysis, adjustments, summary}
        """
        loop = asyncio.get_running_loop()

        emit("progress", {"phase": "analyst",
                           "text": "📊 AnalystAgent 正在分析本周打卡数据..."})

        analysis = await loop.run_in_executor(
            None, self.analyst.analyze_week_checkins, days, profile,
        )
        adjustments = await loop.run_in_executor(
            None, self.analyst.determine_adjustments, analysis,
        )

        emit("progress", {"phase": "analyst",
                           "text": f"✅ 分析完成：{analysis.get('overall_assessment', '')}"})

        return {"analysis": analysis, "adjustments": adjustments}

    # ═══════════════════════════════════════════════════════════
    #  周总结生成
    # ═══════════════════════════════════════════════════════════

    async def generate_weekly_summary(
        self,
        profile: dict,
        week_data: dict,
        emit: Callable,
    ) -> dict:
        """生成周训练总结。

        Args:
            profile: 用户画像
            week_data: 周数据（含 completion_rate, days 等）
            emit: SSE 事件发送函数（同步回调）

        Returns:
            dict: CoachAgent 生成的周总结
        """
        loop = asyncio.get_running_loop()

        emit("progress", {"phase": "summary",
                           "text": "📝 CoachAgent 正在生成周总结..."})

        summary = await loop.run_in_executor(
            None, self.coach.generate_weekly_summary, profile, week_data,
        )
        return summary

    # ═══════════════════════════════════════════════════════════
    #  内部方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _build_user_desc(request: InitPlanRequest) -> str:
        parts = []
        if request.height:
            parts.append(f"身高={request.height}cm")
        if request.weight:
            parts.append(f"体重={request.weight}kg")
        if request.age:
            parts.append(f"年龄={request.age}岁")
        if request.gender:
            gender_cn = "男" if request.gender == "male" else "女"
            parts.append(f"性别={gender_cn}")
        if request.city:
            parts.append(f"城市={request.city}")
        return ", ".join(parts)


# ═══════════════════════════════════════════════════════════════
#  旧版 SSE 流式生成入口（向后兼容）
# ═══════════════════════════════════════════════════════════════

def _sse_event(event: str, data: str) -> str:
    """构造 SSE 消息格式。"""
    return f"event: {event}\ndata: {data}\n\n"


def get_ppl_schedule(days_per_week: int) -> dict:
    """根据用户每周天数返回对应的 PPL 分化方案。"""
    key = f"ppl_{days_per_week}"
    return PPL_SPLITS.get(key, PPL_SPLITS["ppl_3"])


# ── 旧版逻辑（兼容已有 fitness.py 引用） ──────────────────

async def generate_plan_stream(request, db: Session) -> AsyncGenerator[str, None]:
    """（旧）SSE 流式生成入口 — 保留向后兼容。"""
    event_queue: asyncio.Queue = asyncio.Queue()

    async def _emit(event_type: str, data: object):
        await event_queue.put((event_type, data))

    # ── 简单转发到新版 PlanService ──
    # 新版 adapt：用 CoachAgent 分析画像
    ps = PlanService()
    loop = asyncio.get_running_loop()

    # 构造 InitPlanRequest 兼容对象
    class _CompatRequest:
        goal = request.goal
        experience_level = request.experience_level
        workout_location = request.workout_location
        days_per_week = request.days_per_week
        height = getattr(request, 'height', None)
        weight = getattr(request, 'weight', None)
        age = getattr(request, 'age', None)
        gender = getattr(request, 'gender', None)
        city = getattr(request, 'city', None)
        preferred_days = "1,3,5"
        notes = getattr(request, 'notes', "")
        duration_weeks = getattr(request, 'duration_weeks', 4)

    compat = _CompatRequest()

    try:
        result = await ps.generate_plan(compat, _emit)

        for day_idx, day_plan in enumerate(result.get("weekly_plans", [{"days": []}])[0]["days"]):
            for ex in day_plan.get("main", []):
                await _emit("exercise_done", {
                    "day": day_idx,
                    "exercise": {
                        "name": ex.get("name", ""),
                        "sets": ex.get("sets", 3),
                        "reps": ex.get("reps", 10),
                        "wger_id": ex.get("wger_id"),
                        "target_muscle": ex.get("target_muscle", ""),
                        "rest_seconds": ex.get("rest_seconds", 60),
                    },
                })
            await _emit("day_done", {
                "day": day_idx,
                "focus": day_plan.get("focus", ""),
                "main_count": len(day_plan.get("main", [])),
            })

        final_result = {
            "weekly_plans": result["weekly_plans"],
            "profile": result.get("profile", {}),
        }

        # 存库
        try:
            plan = FitnessPlan(
                goal=request.goal,
                experience_level=request.experience_level,
                workout_location=request.workout_location,
                days_per_week=request.days_per_week or 3,
                duration_weeks=request.duration_weeks or 4,
                notes=request.notes or "",
                plan_content=json.dumps(final_result, ensure_ascii=False),
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
            final_result["id"] = plan.id
        except Exception as e:
            print(f"[PlanService] 存库失败: {e}")
            db.rollback()
            final_result["id"] = -1

        await _emit("done", final_result)

    except Exception as e:
        print(f"[PlanService] 生成失败: {e}")
        traceback.print_exc()
        await _emit("error", {"text": f"生成失败: {str(e)}"})

    await event_queue.put(("__END__", None))

    # Consumer
    while True:
        event_type, data = await event_queue.get()
        if event_type == "__END__":
            break
        yield _sse_event(event_type, json.dumps(data, ensure_ascii=False))
