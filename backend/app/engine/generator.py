"""周计划生成编排器 — 统筹所有引擎生成每周计划

两个入口：
  generate_init_week()   → 首次：搜索 wger → LLM 选动作 → 组日 → 写库
  generate_next_week()   → 后续：读上周打卡 → 自适应 → 渐进 → 写库
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import AsyncGenerator, List, Optional, Callable, Dict

from sqlalchemy.orm import Session, joinedload, contains_eager

from app.models.orm_models import (
    Macrocycle, Mesocycle, Week, Day, ExerciseSlot, Exercise,
    UserCurrentState, MesocycleExercisePool,
)
from app.models.schemas import InitPlanRequest
from app.services.wger_service import search_exercises as wger_search
from app.engine.progressive_overload import calc_next_week_params, calc_deload_params, PHASE_PARAMS
from app.engine.adaptive_adjustment import analyze_slot, analyze_week, update_user_state, update_blacklist
from app.engine.exercise_rotation import rotate_slots_for_new_mesocycle
from app.engine.exercise_pool import PoolManager, _muscle_id_to_group
from app.engine.mesocycle_manager import (
    decide_next_phase, needs_deload_this_week, is_mesocycle_complete,
)
from app.agents.programmer_agent import ProgrammerAgent
from app.agents.coach_agent import CoachAgent
from app.agents.plan_assembler import assemble_one_day


# ── 日志 ────────────────────────────────────────────────────

logger = logging.getLogger("generator")


# ── Agent 实例（惰性加载）────────────────────────────────────

_programmer: Optional[ProgrammerAgent] = None
_coach: Optional[CoachAgent] = None


def _get_programmer() -> ProgrammerAgent:
    global _programmer
    if _programmer is None:
        _programmer = ProgrammerAgent()
    return _programmer


def _get_coach() -> CoachAgent:
    global _coach
    if _coach is None:
        _coach = CoachAgent()
    return _coach


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
    5: [
        {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "day_label": "推",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_TRICEPS]},
        {"day": "第2天 · 拉", "focus": "背部 + 二头", "day_label": "拉",
         "muscle_ids": [W_BACK, W_BICEPS]},
        {"day": "第3天 · 腿", "focus": "腿部 + 臀部", "day_label": "腿",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES]},
        {"day": "第4天 · 上肢(推+拉)", "focus": "胸 + 肩 + 背", "day_label": "上肢综合",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_BACK]},
        {"day": "第5天 · 下肢+核心", "focus": "腿部 + 核心", "day_label": "下肢补充",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES, W_ABS]},
    ],
    6: [
        {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "day_label": "推",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_TRICEPS]},
        {"day": "第2天 · 拉", "focus": "背部 + 二头", "day_label": "拉",
         "muscle_ids": [W_BACK, W_BICEPS]},
        {"day": "第3天 · 腿", "focus": "腿部 + 臀部", "day_label": "腿",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES]},
        {"day": "第4天 · 推(补充)", "focus": "胸部 + 肩部 + 三头", "day_label": "推②",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_TRICEPS]},
        {"day": "第5天 · 拉(补充)", "focus": "背部 + 二头", "day_label": "拉②",
         "muscle_ids": [W_BACK, W_BICEPS]},
        {"day": "第6天 · 腿+核心", "focus": "腿部 + 核心", "day_label": "腿+核心",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES, W_ABS]},
    ],
    7: [
        {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "day_label": "推",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_TRICEPS]},
        {"day": "第2天 · 拉", "focus": "背部 + 二头", "day_label": "拉",
         "muscle_ids": [W_BACK, W_BICEPS]},
        {"day": "第3天 · 腿", "focus": "腿部 + 臀部", "day_label": "腿",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES]},
        {"day": "第4天 · 推(补充)", "focus": "胸部 + 肩部 + 三头", "day_label": "推②",
         "muscle_ids": [W_CHEST, W_SHOULDERS, W_TRICEPS]},
        {"day": "第5天 · 拉(补充)", "focus": "背部 + 二头", "day_label": "拉②",
         "muscle_ids": [W_BACK, W_BICEPS]},
        {"day": "第6天 · 腿+核心", "focus": "腿部 + 核心", "day_label": "腿+核心",
         "muscle_ids": [W_QUADS, W_HAMS, W_GLUTES, W_ABS]},
        {"day": "第7天 · 全身+有氧", "focus": "全身 + 核心", "day_label": "全身",
         "muscle_ids": [W_CHEST, W_BACK, W_QUADS, W_ABS]},
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

    # ── Phase 0: CoachAgent 分析用户画像 ─────────────────
    if user_info:
        user_desc = f"目标={macrocycle.goal}"
        if user_info.get("height"): user_desc += f", 身高={user_info['height']}cm"
        if user_info.get("weight"): user_desc += f", 体重={user_info['weight']}kg"
        if user_info.get("age"): user_desc += f", 年龄={user_info['age']}岁"
        if user_info.get("gender"): user_desc += f", 性别={'男' if user_info['gender']=='male' else '女'}"
    else:
        user_desc = f"目标={macrocycle.goal}"

    profile = {}
    try:
        await _emit_sse(event_queue, "progress", {
            "phase": "coach", "text": "🤖 CoachAgent 正在分析用户画像...",
        })
        # 构造一个兼容的 request 对象
        class _CompatReq:
            goal = macrocycle.goal
            experience_level = user_state.experience_level
            workout_location = user_state.workout_location
            days_per_week = user_state.days_per_week
            height = (user_info or {}).get("height")
            weight = (user_info or {}).get("weight")
            age = (user_info or {}).get("age")
            gender = (user_info or {}).get("gender")
            city = ""
        loop = asyncio.get_running_loop()
        profile = await loop.run_in_executor(None, _get_coach().analyze_user, _CompatReq())
        await _emit_sse(event_queue, "progress", {
            "phase": "coach",
            "text": f"✅ 画像分析：{profile.get('profile_summary', '')}",
        })
    except Exception as e:
        print(f"[Generator] CoachAgent 分析失败: {e}")
        profile = {"profile_summary": user_desc, "precautions": []}

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

    # 2c: 汇总结果，构建 mid → [{wger_id, name, muscle_id, muscle_group, description, equipment, image_url}] 的映射
    muscle_exercises = {}
    for mid, exercises in raw_results:
        muscle_exercises[mid] = [
            {"wger_id": e.get("id"), "name": e.get("name", ""),
             "muscle_id": mid,
             "muscle_group": _muscle_id_to_group(mid),
             "description": e.get("description", ""),
             "equipment": e.get("equipment", ""),
             "image_url": e.get("image_url", "")}
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

        await _emit_sse(event_queue, "progress", {
            "day": do, "phase": "select",
            "text": f"🤖 ProgrammerAgent 正在从 {data['total']} 个候选中精选...",
        })
        selected = await loop.run_in_executor(
            None, _get_programmer().select_exercises,
            day_spec.get("muscle_ids", []), profile,
            macrocycle.goal, user_state.experience_level,
            user_state.workout_location, 3, "", user_desc,
        )

        if not selected:
            await _emit_sse(event_queue, "progress", {
                "day": do, "phase": "select",
                "text": f"⚠️ 第{do}天 ProgrammerAgent 未返回结果，使用兜底方案",
            })
            # 兜底：从已缓存的 wger 结果中取
            fallback_exercises = []
            for mid in day_spec.get("muscle_ids", []):
                fallback_exercises.extend(muscle_exercises.get(mid, []))
            selected = fallback_exercises[:5]
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

        # CoachAgent 加教练备注
        if profile and day_plan.get("main"):
            try:
                day_plan = _get_coach().add_reasoning(
                    day_plan, profile, macrocycle.goal,
                )
            except Exception as e:
                print(f"[Generator] CoachAgent 备注生成失败: {e}")

        main_count = len(day_plan.get("main", []))
        stretch_count = len(day_plan.get("stretch", []))
        cardio_name = (day_plan.get("cardio") or {}).get("name", "无")
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

        _write_slots(day.id, day_plan, selected, db, event_queue, day_order, phase=mesocycle.phase)
        db.flush()

        await _emit_sse(event_queue, "day_done", {
            "day": day_order, "focus": day_spec.get("focus", ""),
            "main_count": len(day_plan.get("main", [])),
        })

    db.commit()
    db.refresh(week)

    # 自动填充缓存池（供第 2 周的 generate_next_week 使用）
    try:
        all_muscle_ids = list(set(mid for d in split_days for mid in d.get("muscle_ids", [])))
        pool_total = PoolManager.refresh_pool(mesocycle.id, all_muscle_ids, db)
        db.commit()

        # 设置 pool_loaded 标记
        ucs = db.query(UserCurrentState).first()
        if ucs:
            ucs.pool_loaded = 1
            db.commit()

        await _emit_sse(event_queue, "progress", {
            "phase": "pool",
            "text": f"📦 缓存池初始化完成：{pool_total} 个动作",
        })
    except Exception as e:
        print(f"[Generator] 缓存池填充失败（不影响第 1 周）: {e}")

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
    """基于前一周的打卡数据生成下一周（重构版：缓存池 + AI 热身拉伸）。

    全程广播进度事件，前端可实时展示进度条 + 日志。
    """
    logger.info(f"[🔍 generate_next_week] ====== 进入 =====")

    # ── 进度辅助 ──────────────────────────────────────────
    async def prog(phase: str, pct: int, text: str, day: int = None):
        d = {"phase": phase, "progress": pct, "text": text}
        if day is not None:
            d["day"] = day
        await _emit_sse(event_queue, "progress", d)

    # ═══════════════════════════════════════════════════════
    #  Step 0: 查询中周期 + UserCurrentState
    # ═══════════════════════════════════════════════════════
    await prog("init", 1, "🔍 查询中周期配置...")
    mesocycle = db.query(Mesocycle).filter(Mesocycle.id == current_week.mesocycle_id).first()
    if not mesocycle:
        logger.info("[🔍 generate_next_week] ❌ 找不到中周期")
        await _emit_sse(event_queue, "error", {"text": "找不到当前中周期"})
        return None

    await prog("init", 2, f"🔍 查询用户训练状态...")
    ucs = db.query(UserCurrentState).first()
    await prog("init", 3, f"📋 中周期: {mesocycle.phase} (第{current_week.week_number}/{mesocycle.week_count}周)")

    # ═══════════════════════════════════════════════════════
    #  Step 1: 读取前一周 days + slots
    # ═══════════════════════════════════════════════════════
    await prog("read", 5, "📖 读取前一周训练数据 (含打卡反馈)...")
    prev_days = (
        db.query(Day)
        .filter(Day.week_id == current_week.id)
        .order_by(Day.day_order)
        .outerjoin(ExerciseSlot)
        .options(contains_eager(Day.slots))
        .all()
    )
    prev_slot_count = sum(len(d.slots) for d in prev_days)
    total_days = max(len(prev_days), 1)
    await prog("read", 7, f"📖 前一周: {len(prev_days)} 个训练日, {prev_slot_count} 个动作")

    # ═══════════════════════════════════════════════════════
    #  Step 2: 自适应分析
    # ═══════════════════════════════════════════════════════
    await prog("analysis", 8, "📊 分析本周打卡数据 (完成率/RPE/超负荷信号)...")
    week_analysis = analyze_week(prev_days)
    all_rpes = [
        getattr(s, "rpe", 0) or 0
        for d in prev_days for s in (d.slots or [])
        if (getattr(s, "rpe", 0) or 0) > 0
    ]
    week_analysis["avg_rpe"] = round(sum(all_rpes) / len(all_rpes), 1) if all_rpes else 0

    cr = week_analysis.get("completion_rate", 0) * 100
    ar = week_analysis.get("avg_rpe", "N/A")
    hr = week_analysis.get("high_rpe_ratio", 0) * 100
    await prog("analysis", 10, f"📊 完成率 {cr:.0f}% | 平均RPE {ar} | RPE≥9占比 {hr:.0f}% | 减载建议: {'是' if week_analysis.get('needs_deload') else '否'}")

    next_phase = mesocycle.phase
    next_week_number = current_week.week_number + 1

    # ═══════════════════════════════════════════════════════
    #  Step 3: 中周期切换判断
    # ═══════════════════════════════════════════════════════
    await prog("decision", 12, "🔀 判断是否需要切换中周期...")
    mesocycle_ended = is_mesocycle_complete(
        current_week.week_number, mesocycle.week_count
    )

    prev_start = current_week.start_date or _get_monday()
    next_start = _add_days(prev_start, 7)
    pool_needs_refresh = False

    if mesocycle_ended or needs_deload_this_week(week_analysis):
        next_phase = decide_next_phase(mesocycle.phase, week_analysis["completion_rate"])
        await prog("mesocycle", 15, f"🔄 切换中周期: {mesocycle.phase} → {next_phase}")
        logger.info(f"[🔍 generate_next_week] ⚡ 切换中周期: {mesocycle.phase} → {next_phase}")

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

        if ucs:
            ucs.current_mesocycle_id = mesocycle.id
            ucs.pool_loaded = 0

        db.flush()
        next_week_number = 1
        pool_needs_refresh = True
    else:
        await prog("decision", 14, f"✅ 中周期延续: {mesocycle.phase} 第{next_week_number}周")

    # ═══════════════════════════════════════════════════════
    #  Step 3b: 刷新缓存池（按肌群从 wger 拉取）
    # ═══════════════════════════════════════════════════════
    need_pool = pool_needs_refresh or not ucs or not ucs.pool_loaded
    await prog("pool", 16, f"{'📦 需要刷新缓存池...' if need_pool else '📦 缓存池已就绪 (跳过刷新)'}"
               f" (pool_loaded={ucs.pool_loaded if ucs else 'N/A'})")

    if need_pool:
        split_days = _get_split_days(getattr(ucs, "days_per_week", 3) if ucs else 3)
        all_muscle_ids = list(set(mid for d in split_days for mid in d.get("muscle_ids", [])))

        await prog("pool", 18, f"📦 按 {len(all_muscle_ids)} 个肌群从 wger 搜索动作...")

        total = PoolManager.refresh_pool(mesocycle.id, all_muscle_ids, db)
        if ucs:
            ucs.pool_loaded = 1

        await prog("pool", 22, f"✅ 缓存池刷新完成: {total} 个动作已缓存")

    # ═══════════════════════════════════════════════════════
    #  Step 4: 创建新 Week 框架
    # ═══════════════════════════════════════════════════════
    await prog("create", 24, "📅 创建新周框架...")
    existing_week = db.query(Week).filter(
        Week.mesocycle_id == mesocycle.id,
        Week.week_number == next_week_number,
        Week.status == "pending",
    ).first()
    if existing_week:
        await prog("create", 26, "♻️ 重用预创建的骨架周，清理旧数据...")
        for skeleton_day in db.query(Day).filter(Day.week_id == existing_week.id).all():
            db.query(ExerciseSlot).filter(ExerciseSlot.day_id == skeleton_day.id).delete()
            db.delete(skeleton_day)
        existing_week.status = "active"
        existing_week.start_date = next_start
        new_week = existing_week
    else:
        await prog("create", 26, "🆕 创建全新周记录...")
        new_week = Week(
            mesocycle_id=mesocycle.id,
            week_number=next_week_number,
            status="active",
            start_date=next_start,
        )
        db.add(new_week)
    db.flush()

    # ═══════════════════════════════════════════════════════
    #  Step 5: 构建排除列表
    # ═══════════════════════════════════════════════════════
    await prog("config", 28, "📋 构建动作排除列表 (避免上周重复)...")
    exclude_names = list(set(
        s.exercise_name for d in prev_days for s in (d.slots or [])
        if s.phase_type == "main" and s.exercise_name
    ))
    await prog("config", 29, f"📋 排除 {len(exclude_names)} 个上周已选动作")

    # ═══════════════════════════════════════════════════════
    #  Step 6-7: 并行 LLM 精选 + 组装
    # ═══════════════════════════════════════════════════════
    split_days = _get_split_days(getattr(ucs, "days_per_week", 3) if ucs else 3)
    loop = asyncio.get_running_loop()
    day_count = len(split_days)

    user_desc = f"目标={mesocycle.phase}, 经验={ucs.experience_level if ucs else '新手'}, 地点={ucs.workout_location if ucs else '居家'}"
    user_state_dict = {}
    if ucs:
        user_state_dict = {
            "avg_completion_rate": ucs.avg_completion_rate or 0,
            "rpe_trend": ucs.rpe_trend or "stable",
            "consecutive_weeks_completed": ucs.consecutive_weeks_completed or 0,
        }
    profile = {"profile_summary": user_desc, "precautions": []}

    await prog("llm", 30, f"🚀 开始并行生成 {day_count} 天训练内容 (缓存池→LLM精选→AI热身拉伸)...")

    async def llm_for_one_day(day_idx: int) -> dict:
        day_order = day_idx + 1
        day_spec = split_days[day_idx] if day_idx < len(split_days) else {
            "day_label": prev_days[day_idx].day_label if day_idx < len(prev_days) else "",
            "focus": prev_days[day_idx].focus if day_idx < len(prev_days) else "",
            "muscle_ids": [],
        }
        prev_day = prev_days[day_idx] if day_idx < len(prev_days) else None
        prev_slots = prev_day.slots if prev_day else []
        focus = day_spec.get("focus", "")
        label = day_spec.get("day_label", "")

        await prog("candidates", 32, f"📦 第{day_order}天({focus}): 从缓存池获取候选动作...", day_order)
        muscle_ids = day_spec.get("muscle_ids", [])
        candidates = PoolManager.get_candidates(
            mesocycle.id, muscle_ids,
            exclude_names=exclude_names, db=db,
        )
        await prog("candidates", 34, f"📦 第{day_order}天: 候选 {len(candidates)} 个", day_order)

        # 缓存池为空且该天有目标肌群时，直接从 wger 回源并填入缓存池
        if not candidates and muscle_ids:
            await prog("pool", 34, f"📡 缓存池无该肌群数据，从 wger 回源搜索...", day_order)
            try:
                from app.services.wger_service import search_exercises as wger_search
                from app.engine.exercise_pool import _muscle_id_to_group
                raw_all = []
                for mid in muscle_ids:
                    raw = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda m=mid: wger_search(muscle=m, limit=30)),
                        timeout=25.0,
                    )
                    raw_all.extend(raw or [])
                # 去重
                seen_wger = set()
                for item in raw_all:
                    wid = item.get("wger_id") or item.get("id")
                    if wid and wid not in seen_wger:
                        seen_wger.add(wid)
                        candidates.append({
                            "wger_id": wid,
                            "name": item.get("name", ""),
                            "target_muscle": _muscle_id_to_group(muscle_ids[0]) if muscle_ids else "",
                            "muscle_group_id": muscle_ids[0] if muscle_ids else 0,
                            "equipment": item.get("equipment", ""),
                            "image_url": item.get("image_url", ""),
                            "description": item.get("description", ""),
                            "difficulty": 1,
                        })
                    # 同时补回 Exercise 表 + 缓存池
                    if wid:
                        from app.models.orm_models import Exercise
                        existing_ex = db.query(Exercise).filter(Exercise.wger_id == wid).first()
                        if not existing_ex:
                            group_name = _muscle_id_to_group(muscle_ids[0]) if muscle_ids else ""
                            ex_rec = Exercise(
                                wger_id=wid,
                                name=item.get("name", ""),
                                target_muscle=group_name,
                                muscle_group=group_name,
                                equipment=item.get("equipment", ""),
                                description=item.get("description", ""),
                                image_url=item.get("image_url", ""),
                                difficulty=1,
                            )
                            db.add(ex_rec)
                            # 注意：不 flush，等所有并行任务完成后再统一提交
                            # 加入缓存池
                            pool_entry = MesocycleExercisePool(
                                mesocycle_id=mesocycle.id,
                                wger_id=wid,
                                name=item.get("name", ""),
                                target_muscle=group_name,
                                muscle_group_id=muscle_ids[0] if muscle_ids else 0,
                                equipment=item.get("equipment", ""),
                                image_url=item.get("image_url", ""),
                                description=item.get("description", ""),
                                difficulty=1,
                            )
                            db.add(pool_entry)
                        else:
                            # 已有 Exercise 但不在池中 → 加入池
                            existing_pool = db.query(MesocycleExercisePool).filter(
                                MesocycleExercisePool.mesocycle_id == mesocycle.id,
                                MesocycleExercisePool.wger_id == wid,
                            ).first()
                            if not existing_pool:
                                pool_entry = MesocycleExercisePool(
                                    mesocycle_id=mesocycle.id,
                                    wger_id=wid,
                                    name=existing_ex.name,
                                    target_muscle=existing_ex.target_muscle,
                                    muscle_group_id=muscle_ids[0] if muscle_ids else 0,
                                    equipment=existing_ex.equipment,
                                    image_url=existing_ex.image_url,
                                    description=existing_ex.description,
                                    difficulty=existing_ex.difficulty,
                                )
                                db.add(pool_entry)
                # 注意：不 flush，等所有并行任务完成后再统一提交
                await prog("pool", 35, f"📡 wger 回源成功: {len(candidates)} 个候选动作", day_order)
            except Exception as e:
                print(f"[Generator] wger 回源失败 (第{day_order}天): {e}")

        await prog("select", 36, f"🤖 第{day_order}天: LLM 从 {len(candidates)} 个候选中精选...", day_order)
        selected = []
        if candidates:
            selected = await loop.run_in_executor(
                None, _get_programmer().select_from_pool,
                candidates, day_spec, profile,
                mesocycle.phase, ucs.experience_level if ucs else "中级",
                ucs.workout_location if ucs else "居家",
                user_desc, exclude_names, user_state_dict,
            )
        if not selected:
            await prog("select", 38, f"⚠️ 第{day_order}天: LLM未返回结果, 使用兜底方案", day_order)
            selected = candidates[:5]
        await prog("select", 42, f"🎯 第{day_order}天: LLM精选 {len(selected)} 个主项动作", day_order)

        await prog("assemble", 46, f"🔧 第{day_order}天: AI 正在生成热身+拉伸方案...", day_order)
        day_plan = await loop.run_in_executor(
            None, lambda: assemble_one_day(
                day_spec, selected,
                mesocycle.phase, ucs.experience_level if ucs else "中级",
                ucs.workout_location if ucs else "居家",
                user_desc, use_ai_warmup_stretch=True,
            ),
        )
        if day_plan is None:
            day_plan = {"warmup": [], "main": selected, "cardio": None, "stretch": []}

        await prog("overload", 54, f"⚖️ 第{day_order}天: 计算渐进超负荷 (对比上周RPE)...", day_order)
        if prev_slots:
            prev_slot_map = {s.exercise_name: s for s in prev_slots if s.exercise_name}
            overload_count = 0
            for main_ex in day_plan.get("main", []):
                ex_name = main_ex.get("name", "")
                if ex_name in prev_slot_map:
                    prev = prev_slot_map[ex_name]
                    if next_phase == "deload":
                        params = calc_deload_params(prev)
                    else:
                        params = calc_next_week_params(prev, next_phase)
                    main_ex["weight_kg"] = params.get("weight_kg", 0.0)
                    main_ex["sets"] = params.get("target_sets", main_ex.get("sets", 3))
                    main_ex["reps"] = params.get("target_reps", main_ex.get("reps", 10))
                    main_ex["target_reps_max"] = params.get("target_reps_max", 12)
                    main_ex["rest_seconds"] = params.get("rest_seconds", main_ex.get("rest_seconds", 60))
                    overload_count += 1
            await prog("overload", 58, f"⚖️ 第{day_order}天: {overload_count}/{len(day_plan.get('main', []))} 个动作自适应调整", day_order)

        main_count = len(day_plan.get("main", []))
        cardio_name = (day_plan.get("cardio") or {}).get("name", "无")
        stretch_count = len(day_plan.get("stretch", []))
        await prog("assemble", 62, f"✅ 第{day_order}天: {main_count}主项 + {cardio_name} + {stretch_count}拉伸", day_order)

        return {"day_order": day_order, "day_spec": day_spec,
                "selected": selected, "day_plan": day_plan,
                "prev_day": prev_day}

    day_results = await asyncio.gather(*[llm_for_one_day(i) for i in range(day_count)])
    await prog("llm", 68, f"✅ 全部 {day_count} 天LLM工作完成，准备写入数据库")

    # ═══════════════════════════════════════════════════════
    #  Step 9: 串行写库
    # ═══════════════════════════════════════════════════════
    save_pct_start = 72
    save_pct_range = 20  # 72 → 92
    for idx, res in enumerate(day_results):
        day_order = res["day_order"]
        day_spec = res["day_spec"]
        selected = res["selected"]
        day_plan = res["day_plan"]
        sp = save_pct_start + int((idx + 1) / day_count * save_pct_range)

        await prog("save", sp - 3, f"💾 写入第{day_order}天 ({day_spec.get('focus', '')})...", day_order)

        dow = (day_order * 2 - 1) if len(split_days) >= day_order else 1
        if res["prev_day"] and res["prev_day"].day_of_week:
            dow = res["prev_day"].day_of_week
        day_date = _add_days(next_start, dow - 1)

        new_day = Day(
            week_id=new_week.id,
            day_order=day_order,
            day_of_week=dow,
            date=day_date,
            day_label=day_spec.get("day_label", ""),
            focus=day_spec.get("focus", ""),
        )
        db.add(new_day)
        db.flush()

        _write_slots(new_day.id, day_plan, selected, db, event_queue, day_order, phase=mesocycle.phase)
        db.flush()

        await _emit_sse(event_queue, "day_done", {
            "day": day_order,
            "focus": day_spec.get("focus", ""),
            "main_count": len(day_plan.get("main", [])),
        })

    db.commit()
    db.refresh(new_week)
    await prog("save", 94, f"✅ 数据库写入完成，共 {len(day_results)} 天")

    # ═══════════════════════════════════════════════════════
    #  Step 10: 更新 UserCurrentState
    # ═══════════════════════════════════════════════════════
    await prog("finalize", 96, "💾 更新用户训练状态 (完成率趋势/RPE趋势/黑名单)...")
    update_user_state(new_week, week_analysis, db)
    update_blacklist(prev_days, db)
    db.commit()

    await prog("done", 100, f"✅ 第 {next_week_number} 周计划生成完成!")
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
    phase: str = "foundational",
):
    """按科学流程写入 exercise_slot 表。

    流程: 动态热身 → 无氧主项 → 有氧收尾 → 静态拉伸

    从 PHASE_PARAMS 读取当前阶段的组/次/休息参数，
    确保第 1 周就使用合理的基线值（不再全部 3×10）。
    """
    params = PHASE_PARAMS.get(phase, PHASE_PARAMS["foundational"])
    sort_order = 0

    # 1. 动态热身（reps 代表次数，前端显示 "N次" / "N秒" 由 phase_type 决定）
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
            rest_seconds=0,
            weight_suggestion=ex.get("instruction", ""),
        )
        db.add(slot)

    # 2. 无氧主项 — 用阶段参数作为基线
    main_list = day_plan.get("main", [])
    for ex in main_list:
        sort_order += 1
        wger_id = ex.get("wger_id") or ex.get("id")
        exercise_id = None
        if wger_id:
            cached = db.query(Exercise).filter(Exercise.wger_id == wger_id).first()
            if cached:
                exercise_id = cached.id
            else:
                cached = Exercise(
                    wger_id=wger_id,
                    name=ex.get("name", ""),
                    target_muscle=ex.get("target_muscle", ""),
                    muscle_group=(ex.get("muscle_group", "")
                                  or _muscle_id_to_group(ex.get("muscle_group_id", 0))
                                  or _muscle_id_to_group(ex.get("muscle_id", 0))),
                    movement_pattern=ex.get("movement_pattern", ""),
                    equipment=ex.get("equipment", ""),
                    description=ex.get("description", ""),
                    image_url=ex.get("image_url", ""),
                    difficulty=ex.get("difficulty", 1),
                )
                db.add(cached)
                db.flush()
                exercise_id = cached.id
        slot = ExerciseSlot(
            day_id=day_id,
            exercise_id=exercise_id,
            wger_id=wger_id,
            exercise_name=ex.get("name", ""),
            phase_type="main",
            sort_order=sort_order,
            target_sets=ex.get("sets", params["sets"]),
            target_reps=ex.get("reps", params["rep_lower"]),
            target_reps_max=ex.get("reps_max", params["rep_upper"]),
            weight_kg=ex.get("weight_kg", 0.0),
            weight_suggestion=ex.get("weight_suggestion", ""),
            rest_seconds=ex.get("rest_seconds", params["rest_seconds"]),
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

    # 4. 静态拉伸（target_reps = 保持秒数，不再硬编码 1 秒）
    for ex in day_plan.get("stretch", []):
        sort_order += 1
        # 从 instruction 中提取保持秒数（如 "保持20秒" → 20），默认 20
        inst = ex.get("instruction", "")
        import re
        dur_match = re.search(r"(\d+)\s*秒", inst)
        hold_sec = int(dur_match.group(1)) if dur_match else 20
        slot = ExerciseSlot(
            day_id=day_id,
            exercise_id=_get_or_create_general_exercise(ex, db),
            phase_type="stretch",
            sort_order=sort_order,
            target_sets=1,
            target_reps=hold_sec,
            target_reps_max=hold_sec,
            weight_suggestion=inst,
            rest_seconds=0,
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
