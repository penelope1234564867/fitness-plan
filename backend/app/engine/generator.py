"""周计划生成编排器 — 统筹所有引擎生成每周计划

两个入口：
  generate_init_week()   → 首次：搜索 wger → LLM 选动作 → 组日 → 写库
  generate_next_week()   → 后续：读上周打卡 → 自适应 → 渐进 → 写库
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Optional, Callable, Dict

from sqlalchemy.orm import Session

from app.models.orm_models import (
    Macrocycle, Mesocycle, Week, Day, ExerciseSlot, Exercise,
    UserCurrentState,
)
from app.models.schemas import InitPlanRequest
from app.services.wger_service import search_exercises as wger_search
from app.engine.progressive_overload import calc_next_week_params, calc_deload_params
from app.engine.adaptive_adjustment import analyze_slot, analyze_week
from app.engine.exercise_rotation import rotate_slots_for_new_mesocycle
from app.engine.mesocycle_manager import (
    decide_next_phase, needs_deload_this_week, is_mesocycle_complete,
)
from app.agents.exercise_agent import llm_select
from app.agents.plan_agent import assemble_one_day


# ── 分化方案 ────────────────────────────────────────────────

# wger 数字肌肉 ID
W_CHEST = 4
W_SHOULDERS = 2
W_TRICEPS = 5
W_BACK = 12
W_BICEPS = 1
W_QUADS = 10
W_HAMS = 11
W_GLUTES = 8
W_ABS = 6

PPL_DAYS = {
    3: [
        {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "day_label": "推",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_TRICEPS]},
        {"day": "第2天 · 拉", "focus": "背部 + 二头", "day_label": "拉",
         "muscle_ids": [W_BACK, W_BICEPS]},
        {"day": "第3天 · 腿", "focus": "腿部 + 臀部", "day_label": "腿",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES]},
    ],
    4: [
        {"day": "第1天 · 上肢(推)", "focus": "胸部 + 肩部 + 三头", "day_label": "上肢推",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_TRICEPS]},
        {"day": "第2天 · 下肢", "focus": "腿部 + 臀部", "day_label": "下肢",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES]},
        {"day": "第3天 · 上肢(拉)", "focus": "背部 + 二头", "day_label": "上肢拉",
         "muscle_ids": [W_BACK, W_BICEPS]},
        {"day": "第4天 · 全身补充", "focus": "核心 + 全身", "day_label": "全身",
         "muscle_ids": [W_ABS]},
    ],
}


def _get_split_days(days_per_week: int) -> list:
    """根据每周天数返回对应的分化方案。"""
    return PPL_DAYS.get(days_per_week, PPL_DAYS[3])


def _get_monday(dt: datetime = None) -> str:
    """返回本周一的 YYYY-MM-DD。"""
    if dt is None:
        dt = datetime.now()
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


def _add_days(date_str: str, days: int) -> str:
    """YYYY-MM-DD + 天数 → YYYY-MM-DD。"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return (dt + timedelta(days=days)).strftime("%Y-%m-%d")


async def _emit_sse(event_queue: asyncio.Queue, event: str, data: dict):
    """向 SSE 队列推送事件。"""
    await event_queue.put((event, data))


def _sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {data}\n\n"


# ═══════════════════════════════════════════════════════════════
#  generate_init_week — 首次生成
# ═══════════════════════════════════════════════════════════════

async def generate_init_week(
    macrocycle: Macrocycle,
    mesocycle: Mesocycle,
    user_state: UserCurrentState,
    db: Session,
    event_queue: asyncio.Queue,
    user_info: Optional[dict] = None,       # {height, weight, age, gender}
    start_date: Optional[str] = None,       # YYYY-MM-DD（默认为本周一）
) -> Week:
    """首次生成第 1 周（并行加速）。

    流程：
      并行 → ① 搜索所有肌群动作
      并行 → ② LLM 精选 + 组装（每个训练日各自独立）
      串行 → ③ 写入数据库
    """
    days_per_week = user_state.days_per_week
    split_days = _get_split_days(days_per_week)

    # 解析 preferred_days → [1,3,5]（day_of_week 列表）
    preferred_days_list = []
    if user_state.preferred_days:
        try:
            preferred_days_list = [int(d.strip()) for d in user_state.preferred_days.split(",") if d.strip()]
        except (ValueError, TypeError):
            preferred_days_list = []
    if not preferred_days_list:
        # 默认：从周一隔天分布
        preferred_days_list = list(range(1, days_per_week * 2, 2))[:days_per_week]

    await _emit_sse(event_queue, "progress", {
        "phase": "coordinator",
        "text": f"📋 开始并行生成第 1 周计划（{days_per_week} 天/周）...",
    })

    # ── 确定起始日期 ───────────────────────────────────
    if start_date is None:
        start_date = _get_monday()
    macrocycle.start_date = start_date

    # ── Phase 1: 创建 Week ──────────────────────────────
    week = Week(mesocycle_id=mesocycle.id, week_number=1,
                status="active", start_date=start_date)
    db.add(week)
    db.flush()

    # ── Phase 2: 并行从 wger 拉取数据（不写 DB） + 串行写入缓存 ──
    await _emit_sse(event_queue, "progress", {
        "phase": "search", "text": f"📡 从 wger 搜索 {sum(len(d['muscle_ids']) for d in split_days)} 个肌群的动作...",
    })

    all_muscle_ids = list(set(mid for d in split_days for mid in d.get("muscle_ids", [])))
    loop = asyncio.get_running_loop()

    # 2a: 并行调用 wger API（仅网络请求，不碰数据库，单个超时不影响整体）
    async def safe_search(mid: int) -> tuple:
        """安全搜索单个肌群，超时或失败时返回空列表不抛异常。"""
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda m=mid: wger_search(muscle=m, limit=30)),
                timeout=25.0,
            )
            return (mid, result or [])
        except asyncio.TimeoutError:
            print(f"[Generator] 肌群 ID={mid} wger 搜索超时")
            return (mid, [])
        except Exception as e:
            print(f"[Generator] 肌群 ID={mid} wger 搜索失败: {e}")
            return (mid, [])

    raw_results = await asyncio.gather(*[safe_search(mid) for mid in all_muscle_ids])

    # 2b: 直接记录 wger_id（不写入 Exercise 表缓存）
    seen_wger_ids = set()
    for mid, exercises in raw_results:
        count = len(exercises)
        if count == 0:
            await _emit_sse(event_queue, "progress", {
                "phase": "search",
                "text": f"📡 肌群 ID={mid}: wger 未返回数据",
            })
        else:
            await _emit_sse(event_queue, "progress", {
                "phase": "search",
                "text": f"📡 肌群 ID={mid}: 获取到 {count} 个动作",
            })

    # 2c: 汇总结果，构建 mid → [{wger_id, name, muscle_id, description, equipment}] 的映射
    muscle_exercises = {}
    for mid, exercises in raw_results:
        muscle_exercises[mid] = [
            {"wger_id": e.get("id"), "name": e.get("name", ""),
             "muscle_id": mid, "description": e.get("description", ""),
             "equipment": e.get("equipment", "")}
            for e in exercises if e.get("id")
        ]

    total_candidates = sum(len(exs) for exs in muscle_exercises.values())
    await _emit_sse(event_queue, "progress", {
        "phase": "search",
        "text": f"✅ 全部肌群搜索完成，共 {total_candidates} 个候选动作",
    })

    # ── Phase 3: 构建 LLM 输入数据（用内存中的 wger 结果，不查 DB） ──
    day_data = []
    for day_idx, day_spec in enumerate(split_days):
        muscle_ids = day_spec.get("muscle_ids", [])
        grouped = {
            mid: muscle_exercises.get(mid, [])
            for mid in muscle_ids
        }
        day_data.append({
            "day_order": day_idx + 1,
            "day_spec": day_spec,
            "grouped": grouped,
            "total": sum(len(v) for v in grouped.values()),
        })

    # ── Phase 4: 并行 LLM 精选 + 组装（每 天 独 立，不碰 DB） ──
    await _emit_sse(event_queue, "progress", {
        "phase": "llm_parallel", "text": f"🚀 并行执行 {len(split_days)} 天的 LLM 精选和组装...",
    })

    # 构建用户描述信息
    user_desc = f"目标={macrocycle.goal}, 经验={user_state.experience_level}, 地点={user_state.workout_location}"
    if user_info:
        parts = []
        if user_info.get("height"): parts.append(f"身高={user_info['height']}cm")
        if user_info.get("weight"): parts.append(f"体重={user_info['weight']}kg")
        if user_info.get("age"): parts.append(f"年龄={user_info['age']}岁")
        if user_info.get("gender"): parts.append(f"性别={'男' if user_info['gender']=='male' else '女'}")
        if parts:
            user_desc += ", " + ", ".join(parts)

    async def llm_for_one_day(data: dict) -> dict:
        do = data["day_order"]
        day_spec = data["day_spec"]
        grouped = data["grouped"]

        await _emit_sse(event_queue, "progress", {
            "day": do, "phase": "select",
            "text": f"🤖 第{do}天 LLM 正在从 {data['total']} 个候选中精选...",
        })
        selected = await loop.run_in_executor(
            None, llm_select,
            grouped, macrocycle.goal, user_state.experience_level,
            user_state.workout_location, "", 3, False, user_desc,
        )

        if not selected:
            await _emit_sse(event_queue, "progress", {
                "day": do, "phase": "select",
                "text": f"⚠️ 第{do}天 LLM 未返回结果，使用兜底方案",
            })
            selected = [{"name": e.name, "target_muscle": e.target_muscle,
                         "wger_id": e.wger_id, "sets": 3, "reps": 12}
                        for exs in grouped.values() for e in exs][:5]
        else:
            await _emit_sse(event_queue, "progress", {
                "day": do, "phase": "select",
                "text": f"🎯 第{do}天 LLM 精选完成：{len(selected)} 个动作",
            })

        await _emit_sse(event_queue, "progress", {
            "day": do, "phase": "assemble",
            "text": f"🔧 第{do}天 LLM 正在组装计划...",
        })
        day_plan = await loop.run_in_executor(
            None, assemble_one_day,
            day_spec, selected,
            macrocycle.goal, user_state.experience_level,
            user_state.workout_location, user_desc,
        )
        if day_plan is None:
            day_plan = {"warmup": [], "main": selected, "cardio": None, "stretch": []}

        main_count = len(day_plan.get("main", []))
        stretch_count = len(day_plan.get("stretch", []))
        cardio_name = day_plan.get("cardio", {}).get("name", "无")
        await _emit_sse(event_queue, "progress", {
            "day": do, "phase": "assemble",
            "text": f"✅ 第{do}天计划组装完成：{main_count} 个主项 + {cardio_name} + {stretch_count} 个拉伸",
        })
        return {"day_order": do, "day_spec": day_spec,
                "selected": selected, "day_plan": day_plan}

    day_results = await asyncio.gather(*[llm_for_one_day(d) for d in day_data])

    # ── Phase 4: 串行写入数据库 ──────────────────────
    for res in day_results:
        day_order = res["day_order"]
        day_spec = res["day_spec"]
        selected = res["selected"]
        day_plan = res["day_plan"]

        await _emit_sse(event_queue, "progress", {
            "day": day_order, "phase": "save",
            "text": f"💾 正在写入第{day_order}天数据库...",
        })

        day_of_week = preferred_days_list[day_order - 1] if day_order <= len(preferred_days_list) else (day_order * 2 - 1)
        day_date = _add_days(start_date, day_of_week - 1)
        day = Day(
            week_id=week.id, day_order=day_order,
            day_of_week=day_of_week, date=day_date,
            day_label=day_spec.get("day_label", ""),
            focus=day_spec.get("focus", ""),
        )
        db.add(day)
        db.flush()

        _write_slots(day.id, day_plan, selected, db, event_queue, day_order)
        db.flush()

        await _emit_sse(event_queue, "day_done", {
            "day": day_order, "focus": day_spec.get("focus", ""),
            "main_count": len(day_plan.get("main", [])),
        })

    db.commit()
    db.refresh(week)

    await _emit_sse(event_queue, "progress", {
        "phase": "done",
        "text": f"✅ 第 1 周计划生成完成！共 {len(split_days)} 天训练日",
    })

    return week


# ═══════════════════════════════════════════════════════════════
#  generate_next_week — 生成下一周
# ═══════════════════════════════════════════════════════════════

async def generate_next_week(
    current_week: Week,
    db: Session,
    event_queue: asyncio.Queue,
) -> Optional[Week]:
    """基于前一周的打卡数据生成下一周。

    流程：自适应分析 → 渐进超负荷 →（切换边界时轮换）→ 写入。
    """
    mesocycle = db.query(Mesocycle).filter(Mesocycle.id == current_week.mesocycle_id).first()
    if not mesocycle:
        await _emit_sse(event_queue, "error", {"text": "找不到当前中周期"})
        return None

    # 读取前一周的所有 days + slots
    prev_days = db.query(Day).filter(Day.week_id == current_week.id).order_by(Day.day_order).all()
    for d in prev_days:
        d.slots = db.query(ExerciseSlot).filter(ExerciseSlot.day_id == d.id).all()

    # 自适应分析
    week_analysis = analyze_week(prev_days)
    next_phase = mesocycle.phase

    # 判断是否需要切换中周期
    mesocycle_ended = is_mesocycle_complete(
        current_week.week_number, mesocycle.week_count
    )

    # 计算下一周起始日期
    prev_start = current_week.start_date or _get_monday()
    next_start = _add_days(prev_start, 7)

    if mesocycle_ended or needs_deload_this_week(week_analysis):
        next_phase = decide_next_phase(mesocycle.phase, week_analysis["completion_rate"])

        await _emit_sse(event_queue, "progress", {
            "phase": "mesocycle",
            "text": f"🔄 中周期切换: {mesocycle.phase} → {next_phase}",
        })

        # 创建新 Mesocycle
        new_mesocycle = Mesocycle(
            macrocycle_id=mesocycle.macrocycle_id,
            phase=next_phase,
            week_count=1 if next_phase == "deload" else 4,
            sort_order=(mesocycle.sort_order or 0) + 1,
            status="active",
        )
        db.add(new_mesocycle)
        db.flush()
        mesocycle.status = "completed"
        mesocycle = new_mesocycle

        # 更新 user_current_state
        from app.models.orm_models import UserCurrentState
        ucs = db.query(UserCurrentState).first()
        if ucs:
            ucs.current_mesocycle_id = mesocycle.id

        db.flush()

    next_week_number = current_week.week_number + 1

    # 如果已切换到新 mesocycle，周数重置为 1
    if mesocycle_ended:
        next_week_number = 1
        # 动作轮换
        all_prev_slots = [s for d in prev_days for s in d.slots]
        rotation_result = rotate_slots_for_new_mesocycle(all_prev_slots, db)
        rotation_map = {r["slot_id"]: r["new_exercise_id"] for r in rotation_result}

        await _emit_sse(event_queue, "progress", {
            "phase": "rotation",
            "text": f"🔄 轮换了 {len(rotation_result)} 个主项动作",
        })
    else:
        rotation_map = {}

    # 创建新 Week
    new_week = Week(
        mesocycle_id=mesocycle.id,
        week_number=next_week_number,
        status="active",
        start_date=next_start,
    )
    db.add(new_week)
    db.flush()

    # 遍历每天的 slots，应用渐进超负荷
    for day_idx, prev_day in enumerate(prev_days):
        day_order = day_idx + 1
        day_label = prev_day.day_label
        focus = prev_day.focus

        # 计算该训练日的具体日期
        dow = prev_day.day_of_week or (day_order * 2 - 1)
        if dow < 1:
            dow = 1
        day_date = _add_days(next_start, dow - 1)

        new_day = Day(
            week_id=new_week.id,
            day_order=day_order,
            day_of_week=prev_day.day_of_week or 0,
            date=day_date,
            day_label=day_label,
            focus=focus,
        )
        db.add(new_day)
        db.flush()

        for slot in prev_day.slots:
            # 主项用 wger_id，热身/有氧/拉伸用 exercise_id
            wger_id = slot.wger_id
            exercise_id = slot.exercise_id
            if slot.id in rotation_map:
                rotation = rotation_map[slot.id]
                wger_id = rotation.get("wger_id")
                exercise_id = rotation.get("exercise_id")

            if next_phase == "deload":
                params = calc_deload_params(slot)
            else:
                params = calc_next_week_params(slot, next_phase)

            new_slot = ExerciseSlot(
                day_id=new_day.id,
                exercise_id=exercise_id,
                wger_id=wger_id,
                exercise_name=slot.exercise_name,
                phase_type=slot.phase_type,
                sort_order=slot.sort_order,
                target_sets=params["target_sets"],
                target_reps=params["target_reps"],
                target_reps_max=params["target_reps_max"],
                weight_kg=params["weight_kg"],
                rest_seconds=params.get("rest_seconds", 60),
            )
            db.add(new_slot)

        db.flush()

        await _emit_sse(event_queue, "day_done", {
            "day": day_order,
            "focus": focus,
            "main_count": len([s for s in prev_day.slots if s.phase_type == "main"]),
        })

    db.commit()
    db.refresh(new_week)

    await _emit_sse(event_queue, "progress", {
        "phase": "done",
        "text": f"✅ 第 {mesocycle.week_count + 1 - mesocycle_ended} 周计划生成完成",
    })

    return new_week


# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def _write_slots(
    day_id: int,
    day_plan: dict,
    selected_exercises: list,
    db: Session,
    event_queue: asyncio.Queue,
    day_order: int,
):
    """按科学流程写入 exercise_slot 表。

    流程: 动态热身 → 无氧主项 → 有氧收尾 → 静态拉伸
    """
    sort_order = 0

    # 1. 动态热身
    warmup_list = day_plan.get("warmup", [])
    for ex in warmup_list:
        sort_order += 1
        slot = ExerciseSlot(
            day_id=day_id,
            exercise_id=_get_or_create_general_exercise(ex, db),
            phase_type="warmup",
            sort_order=sort_order,
            target_sets=ex.get("sets", 2),
            target_reps=ex.get("reps", 12),
            target_reps_max=15,
            rest_seconds=15,
            weight_suggestion=ex.get("instruction", ""),
        )
        db.add(slot)

    # 2. 无氧主项（直接存 wger_id + name，不缓存到 Exercise 表）
    main_list = day_plan.get("main", [])
    for ex in main_list:
        sort_order += 1
        slot = ExerciseSlot(
            day_id=day_id,
            wger_id=ex.get("wger_id") or ex.get("id"),
            exercise_name=ex.get("name", ""),
            phase_type="main",
            sort_order=sort_order,
            target_sets=ex.get("sets", 3),
            target_reps=ex.get("reps", 10),
            target_reps_max=12,
            weight_kg=ex.get("weight_kg", 0.0),
            weight_suggestion=ex.get("weight_suggestion", ""),
            rest_seconds=ex.get("rest_seconds", 60),
        )
        db.add(slot)

    # 3. 有氧收尾（可选）
    cardio = day_plan.get("cardio")
    if cardio:
        sort_order += 1
        slot = ExerciseSlot(
            day_id=day_id,
            exercise_id=_get_or_create_general_exercise(
                {"name": cardio.get("name", "有氧运动")}, db
            ),
            phase_type="cardio",
            sort_order=sort_order,
            target_sets=1,
            target_reps=cardio.get("duration_minutes", 15),
            weight_suggestion=cardio.get("suggestion", ""),
            rest_seconds=0,
        )
        db.add(slot)

    # 4. 静态拉伸（对应训练肌群）
    for ex in day_plan.get("stretch", []):
        sort_order += 1
        slot = ExerciseSlot(
            day_id=day_id,
            exercise_id=_get_or_create_general_exercise(ex, db),
            phase_type="stretch",
            sort_order=sort_order,
            target_sets=1,
            target_reps=1,
            target_reps_max=20,
            weight_suggestion=ex.get("instruction", ""),
            rest_seconds=5,
        )
        db.add(slot)


def _get_or_create_general_exercise(ex: dict, db: Session) -> int:
    """为通用动作（热身/有氧/拉伸）创建或查找 exercise 记录。

    通用动作不在 wger 中，按名称创建并缓存，每次返回相同 ID。
    """
    name = ex.get("name", "").strip()
    if not name:
        return 0

    existing = db.query(Exercise).filter(Exercise.name == name).first()
    if existing:
        return existing.id

    tmp = Exercise(name=name, description=ex.get("instruction", ""), target_muscle="全身")
    db.add(tmp)
    db.flush()
    return tmp.id


def _resolve_exercise_id(ex: dict, selected: list, db: Session) -> int:
    """根据 LLM 返回的动作信息，找到 exercise 表中的 ID。"""
    wger_id = ex.get("wger_id")

    # 先按 wger_id 查
    if wger_id:
        exercise = db.query(Exercise).filter(Exercise.wger_id == wger_id).first()
        if exercise:
            return exercise.id

    # 按名称模糊匹配
    name = ex.get("name", "")
    if name:
        exercise = db.query(Exercise).filter(Exercise.name.contains(name[:10])).first()
        if exercise:
            return exercise.id

    # 从选中的动作中匹配
    for sel in selected:
        if sel.get("name") == name or sel.get("wger_id") == wger_id:
            eid = sel.get("id") or sel.get("exercise_id")
            if eid:
                return eid

    # 兜底：用第一个可用的 exercise
    fallback = db.query(Exercise).first()
    if fallback:
        return fallback.id

    # 极端情况（表为空）→ 创建临时
    tmp = Exercise(name=name or "未知动作")
    db.add(tmp)
    db.flush()
    return tmp.id
