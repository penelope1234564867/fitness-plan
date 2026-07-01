"""健身计划服务 - Pipeline + Map-Reduce 编排层

架构:
  Coordinator (PPL 排期) → Map (三天并行 exercise_agent → plan_agent) → Reduce (校验归并) → 存库

SSE 事件协议:
  progress     → {"day":N, "phase":"search|select|assemble", "text":"..."}
  llm_stream   → {"day":N, "phase":"select|assemble", "chunk":"..."}
  exercise_done → {"day":N, "exercise":{"name":"...","sets":4,"reps":8,"wger_id":123}}
  day_done     → {"day":N, "focus":"...", "main_count":5}
  done         → {"id":123, "weekly_plans":[...]}
"""

import json
import asyncio
import traceback
from typing import AsyncGenerator, Tuple

from sqlalchemy.orm import Session

from app.models.schemas import PlanRequest
from app.models.orm_models import FitnessPlan
from app.agents import exercise_agent
from app.agents import plan_agent


# ═══════════════════════════════════════════════════════════════
#  PPL 分化方案（Coordinator 核心数据）
# ═══════════════════════════════════════════════════════════════

PPL_SPLITS = {
    "ppl_3": {
        "name": "PPL（推/拉/腿）",
        "days": 3,
        "per_group": 3,
        "schedule": [
            {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "desc": "训练胸大肌、三角肌和肱三头肌，以推类复合动作为主"},
            {"day": "第2天 · 拉", "focus": "背部 + 二头", "muscles": [12, 1], "desc": "训练背阔肌、菱形肌和肱二头肌，以拉类复合动作为主"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部 + 腹部", "muscles": [10, 11, 8, 6], "desc": "训练股四头肌、腘绳肌、臀大肌和腹部"},
        ],
    },
    "ppl_4": {
        "name": "PPL + 全身补充",
        "days": 4,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "desc": "力量日：胸肩三头推类复合动作"},
            {"day": "第2天 · 拉", "focus": "背部 + 二头", "muscles": [12, 1], "desc": "力量日：背和二头拉类复合动作"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部", "muscles": [10, 11, 8], "desc": "力量日：下肢综合训练"},
            {"day": "第4天 · 全身", "focus": "全身轻量 + 腹部", "muscles": [4, 12, 6], "desc": "补充日：轻重量全身训练，侧重腹部肌群"},
        ],
    },
    "ppl_5": {
        "name": "PPL + 弱项强化",
        "days": 5,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推(主)", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "desc": "主推日：大重量复合动作，5-8RM力量训练"},
            {"day": "第2天 · 拉(主)", "focus": "背部 + 二头", "muscles": [12, 1], "desc": "主拉日：大重量复合动作，5-8RM力量训练"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部 + 腹部", "muscles": [10, 11, 8, 6], "desc": "完整腿日：股四、腘绳、臀大肌和腹部"},
            {"day": "第4天 · 推(辅)", "focus": "肩部 + 三头 + 胸部轻量", "muscles": [2, 5, 4], "desc": "辅助推日：肩和三头强化，胸部轻容量"},
            {"day": "第5天 · 拉(辅)", "focus": "二头 + 斜方肌 + 背部轻量", "muscles": [1, 9, 12], "desc": "辅助拉日：二头和斜方肌强化，背部轻容量"},
        ],
    },
    "ppl_6": {
        "name": "PPL × 2（重量+容量）",
        "days": 6,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推(重)", "focus": "胸部 + 肩部 + 三头（大重量）", "muscles": [4, 2, 5], "desc": "大重量推日：5-8RM力量训练"},
            {"day": "第2天 · 拉(重)", "focus": "背部 + 二头（大重量）", "muscles": [12, 1], "desc": "大重量拉日：5-8RM力量训练"},
            {"day": "第3天 · 腿(重)", "focus": "腿部 + 臀部（大重量）", "muscles": [10, 11, 8], "desc": "大重量腿日：5-8RM力量训练"},
            {"day": "第4天 · 推(轻)", "focus": "胸部 + 肩部 + 三头（增肌容量）", "muscles": [4, 2, 5], "desc": "容量推日：10-15RM增肌训练"},
            {"day": "第5天 · 拉(轻)", "focus": "背部 + 二头（增肌容量）", "muscles": [12, 1], "desc": "容量拉日：10-15RM增肌训练"},
            {"day": "第6天 · 腿(轻)", "focus": "腿部 + 腹部（增肌容量）", "muscles": [10, 11, 6], "desc": "容量腿日：10-15RM增肌训练，加腹部"},
        ],
    },
}


def get_ppl_schedule(days_per_week: int) -> dict:
    """根据用户每周天数返回对应的 PPL 分化方案。"""
    key = f"ppl_{days_per_week}"
    if key not in PPL_SPLITS:
        key = "ppl_3"
    return PPL_SPLITS[key]


# ═══════════════════════════════════════════════════════════════
#  SSE 事件工具
# ═══════════════════════════════════════════════════════════════

def _sse_event(event: str, data: str) -> str:
    """构造 SSE 消息格式。"""
    return f"event: {event}\ndata: {data}\n\n"


# ═══════════════════════════════════════════════════════════════
#  Pipeline: 单天 Pipeline（Map 阶段的基本单元）
# ═══════════════════════════════════════════════════════════════

async def _run_one_day(
    day_spec: dict,
    day_index: int,
    goal: str,
    experience: str,
    location: str,
    split_name: str,
    per_group: int,
    emit,
) -> dict:
    """单天 Pipeline: 搜索 → 过滤 → LLM 精选 → 组装，沿途 emit SSE 事件。

    Returns:
        day_plan dict，失败时返回带 error 标志的 dict
    """
    try:
        # ── 2a. Search ──
        await emit("progress", {"day": day_index, "phase": "search",
                                "text": f"正在搜索 {day_spec['focus']} 相关动作..."})

        loop = asyncio.get_running_loop()
        muscle_ids = day_spec["muscles"]

        # 搜索（同步，走线程池）
        grouped = await loop.run_in_executor(
            None, exercise_agent.search_all_muscles, muscle_ids,
        )
        total_found = sum(len(v) for v in grouped.values())
        await emit("progress", {"day": day_index, "phase": "search",
                                "text": f"搜索到 {total_found} 个候选动作"})

        # ── 2b. Filter ──
        filtered = exercise_agent.filter_by_equipment(grouped, experience)

        # ── 2c. LLM Select ──
        await emit("progress", {"day": day_index, "phase": "select",
                                "text": f"LLM 正在精选最优动作..."})

        selected = await loop.run_in_executor(
            None, exercise_agent.llm_select,
            filtered, goal, experience, location, split_name, per_group,
        )

        if not selected:
            await emit("progress", {"day": day_index, "phase": "select",
                                    "text": "⚠️ 未找到合适的动作"})
            return {"day": day_spec.get("day", ""), "focus": day_spec.get("focus", ""),
                    "warmup": [], "main": [], "cooldown": [], "_error": "no_exercises"}

        # ── 2d. LLM Assemble ──
        await emit("progress", {"day": day_index, "phase": "assemble",
                                "text": f"正在组装 {day_spec['focus']} 训练计划..."})

        day_plan = await loop.run_in_executor(
            None, plan_agent.assemble_one_day,
            day_spec, selected, goal, experience, location,
        )

        if day_plan is None:
            return {"day": day_spec.get("day", ""), "focus": day_spec.get("focus", ""),
                    "warmup": [], "main": [], "cooldown": [], "_error": "assemble_failed"}

        # ── 逐条推送 exercise_done ──
        for ex in day_plan.get("main", []):
            exercise_item = {
                "name": ex.get("name", ""),
                "sets": ex.get("sets", 3),
                "reps": ex.get("reps", 10),
                "wger_id": ex.get("wger_id"),
                "target_muscle": ex.get("target_muscle", ""),
                "rest_seconds": ex.get("rest_seconds", 60),
                "exercise_type": ex.get("exercise_type", "compound"),
            }
            await emit("exercise_done", {"day": day_index, "exercise": exercise_item})

        main_count = len(day_plan.get("main", []))
        await emit("day_done", {"day": day_index,
                                "focus": day_spec.get("focus", ""),
                                "main_count": main_count})

        return day_plan

    except Exception as e:
        print(f"[Day {day_index}] 生成失败: {e}")
        traceback.print_exc()
        await emit("progress", {"day": day_index, "phase": "error",
                                "text": f"⚠️ 该天生成失败: {str(e)[:60]}"})
        return {"day": day_spec.get("day", ""), "focus": day_spec.get("focus", ""),
                "warmup": [], "main": [], "cooldown": [], "_error": str(e)}


# ═══════════════════════════════════════════════════════════════
#  Reduce 阶段
# ═══════════════════════════════════════════════════════════════

def reduce_to_weekly_plan(per_day_plans: list, schedule: list) -> dict:
    """收集 → 校验 → 归并 → 输出周计划。

    Args:
        per_day_plans: 每天的生成结果（可能含 _error）
        schedule: 原始 PPL 排期

    Returns:
        {weekly_plans: [{week: 1, days: [...]}]}
    """
    days = []
    for i, plan in enumerate(per_day_plans):
        day_entry = {
            "day": schedule[i]["day"] if i < len(schedule) else plan.get("day", f"第{i+1}天"),
            "focus": schedule[i]["focus"] if i < len(schedule) else plan.get("focus", ""),
            "warmup": plan.get("warmup", []),
            "main": plan.get("main", []),
            "cooldown": plan.get("cooldown", []),
        }
        # 如果该天失败，给空数组
        if plan.get("_error"):
            day_entry["warmup"] = []
            day_entry["main"] = []
            day_entry["cooldown"] = []
        days.append(day_entry)

    return {
        "weekly_plans": [{"week": 1, "days": days}]
    }


# ═══════════════════════════════════════════════════════════════
#  主入口：generate_plan_stream
# ═══════════════════════════════════════════════════════════════

async def generate_plan_stream(request: PlanRequest, db: Session) -> AsyncGenerator[str, None]:
    """SSE 流式生成入口。

    Stage 1: Coordinator — 硬编码 PPL 排期
    Stage 2: Map — 三天并行 (exercise_agent → plan_agent)
    Stage 3: Reduce — 校验 + 归并
    Stage 4: Persist — 存库 + done
    """
    event_queue: asyncio.Queue[Tuple[str, object]] = asyncio.Queue()

    async def _emit(event_type: str, data: object):
        """向 SSE 队列推送事件。"""
        await event_queue.put((event_type, data))

    # ── Stage 1: Coordinator ──
    print(f"\n{'='*50}")
    print(f"[PlanService] 开始生成训练计划 (Pipeline + Map-Reduce)")
    print(f"[PlanService] {request.goal} | {request.experience_level} | {request.workout_location} | {request.days_per_week}天/周")

    ppl_schedule = get_ppl_schedule(request.days_per_week)
    split_name = ppl_schedule["name"]
    per_group = ppl_schedule["per_group"]
    schedule = ppl_schedule["schedule"]

    print(f"[PlanService] PPL方案: {split_name}, {len(schedule)}天, 每肌群{per_group}个动作")

    yield _sse_event("progress", json.dumps({
        "day": 0, "phase": "coordinator",
        "text": f"📋 开始生成 {split_name} 周计划..."
    }, ensure_ascii=False))

    # ── 启动 Producer 后台任务 ──
    async def _producers():
        """并行执行所有天的生成，结果放入队列。"""
        try:
            async def run_one(day_spec, i):
                return await _run_one_day(
                    day_spec, i,
                    request.goal, request.experience_level,
                    request.workout_location,
                    split_name, per_group,
                    _emit,
                )

            tasks = [run_one(day_spec, i) for i, day_spec in enumerate(schedule)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果（过滤异常）
            valid = []
            for r in results:
                if isinstance(r, Exception):
                    print(f"[PlanService] 某天生成异常: {r}")
                    valid.append({"_error": str(r), "warmup": [], "main": [], "cooldown": []})
                else:
                    valid.append(r)

            return valid
        finally:
            # 通知 consumer 结束
            await event_queue.put(("__END__", None))

    producer_task = asyncio.create_task(_producers())

    # ── Consumer: 从队列中逐个 yield SSE 事件 ──
    while True:
        event_type, data = await event_queue.get()
        if event_type == "__END__":
            break
        yield _sse_event(event_type, json.dumps(data, ensure_ascii=False))

    # 等待 producer 完成，拿结果
    per_day_plans = await producer_task

    # ── Stage 3: Reduce ──
    print(f"[PlanService] Reduce: {len(per_day_plans)} 天计划汇总")
    final_plan = reduce_to_weekly_plan(per_day_plans, schedule)

    # 统计成功天数
    success_days = sum(1 for p in per_day_plans if not p.get("_error"))
    if success_days == 0:
        yield _sse_event("error", json.dumps({
            "text": "所有天数生成失败，请重试"
        }, ensure_ascii=False))
        return

    yield _sse_event("progress", json.dumps({
        "day": 0, "phase": "reduce",
        "text": f"✅ {success_days}/{len(schedule)} 天生成成功，正在汇总..."
    }, ensure_ascii=False))

    # ── Stage 4: Persist ──
    yield _sse_event("progress", json.dumps({
        "day": 0, "phase": "save",
        "text": "💾 保存计划中..."
    }, ensure_ascii=False))

    try:
        plan = FitnessPlan(
            goal=request.goal,
            experience_level=request.experience_level,
            workout_location=request.workout_location,
            days_per_week=request.days_per_week,
            duration_weeks=request.duration_weeks,
            notes=request.notes or "",
            plan_content=json.dumps(final_plan, ensure_ascii=False),
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        print(f"[PlanService] 计划已存入数据库，ID: {plan.id}")

        response = {
            "id": plan.id,
            "goal": plan.goal,
            "experience_level": plan.experience_level,
            "workout_location": plan.workout_location,
            "days_per_week": plan.days_per_week,
            "duration_weeks": plan.duration_weeks,
            **final_plan,
            "created_at": str(plan.created_at),
        }

        yield _sse_event("progress", json.dumps({
            "day": 0, "phase": "done",
            "text": "✅ 计划生成完成！"
        }, ensure_ascii=False))

        yield _sse_event("done", json.dumps(response, ensure_ascii=False))

    except Exception as e:
        print(f"[PlanService] 数据库写入失败: {e}")
        traceback.print_exc()
        db.rollback()
        yield _sse_event("error", json.dumps({
            "text": f"保存计划失败: {str(e)}"
        }, ensure_ascii=False))
