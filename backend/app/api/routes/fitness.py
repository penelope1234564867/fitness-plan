"""健身计划路由 — 周期化训练引擎 API"""

import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import orm_models, schemas
from app.engine.generator import generate_init_week, generate_next_week, _sse_event
from app.engine.exercise_cache import get_or_fetch_exercise
from typing import Optional
import asyncio

router = APIRouter(prefix="/fitness", tags=["健身计划"])


# ═══════════════════════════════════════════════════════════════
#  新引擎接口
# ═══════════════════════════════════════════════════════════════

@router.post("/init-plan", response_class=StreamingResponse)
async def init_plan(req: schemas.InitPlanRequest, db: Session = Depends(get_db)):
    """首次初始化：创建大周期 → 中周期 → 生成第 1 周（SSE 流式）。"""
    event_queue: asyncio.Queue = asyncio.Queue()

    async def event_stream():
        try:
            # 创建 Macrocycle
            macrocycle = orm_models.Macrocycle(
                goal=req.goal,
                status="active",
            )
            db.add(macrocycle)
            db.flush()

            await event_queue.put(("progress", {
                "phase": "init", "text": f"🎯 大周期创建完成：{req.goal}"
            }))

            # 创建第一个 Mesocycle（新手默认 foundational）
            first_phase = "foundational"
            if req.experience_level in ("中级", "高级"):
                first_phase = "hypertrophy"

            mesocycle = orm_models.Mesocycle(
                macrocycle_id=macrocycle.id,
                phase=first_phase,
                week_count=4,
                sort_order=1,
                status="active",
            )
            db.add(mesocycle)
            db.flush()

            # 创建或更新 UserCurrentState
            ucs = db.query(orm_models.UserCurrentState).first()
            if not ucs:
                ucs = orm_models.UserCurrentState(
                    experience_level=req.experience_level,
                    workout_location=req.workout_location,
                    days_per_week=req.days_per_week,
                    preferred_days=req.preferred_days,
                    current_mesocycle_id=mesocycle.id,
                )
                db.add(ucs)
            else:
                ucs.experience_level = req.experience_level
                ucs.workout_location = req.workout_location
                ucs.days_per_week = req.days_per_week
                ucs.preferred_days = req.preferred_days
                ucs.current_mesocycle_id = mesocycle.id
            db.flush()

            # 保存/更新用户个人信息
            user_record = db.query(orm_models.User).first()
            if not user_record:
                user_record = orm_models.User(
                    height=req.height,
                    weight=req.weight,
                    age=req.age,
                    gender=req.gender,
                    goal=req.goal,
                    experience=req.experience_level,
                    workout_location=req.workout_location,
                    city=req.city or "",
                )
                db.add(user_record)
            else:
                if req.height is not None:
                    user_record.height = req.height
                if req.weight is not None:
                    user_record.weight = req.weight
                if req.age is not None:
                    user_record.age = req.age
                if req.gender is not None:
                    user_record.gender = req.gender
                user_record.goal = req.goal
                user_record.experience = req.experience_level
                user_record.workout_location = req.workout_location
                if req.city:
                    user_record.city = req.city
            db.flush()

            await event_queue.put(("progress", {
                "phase": "init", "text": f"📋 中周期创建：{first_phase}"
            }))

            # 生成第 1 周（传入个人信息）
            user_info = {}
            if req.height is not None: user_info["height"] = req.height
            if req.weight is not None: user_info["weight"] = req.weight
            if req.age is not None: user_info["age"] = req.age
            if req.gender is not None: user_info["gender"] = req.gender

            week = await generate_init_week(
                macrocycle, mesocycle, ucs, db, event_queue,
                user_info=user_info,
                start_date=req.start_date,
            )

            # 预创建第 2~4 周框架（路线图用）
            try:
                from app.engine.mesocycle_manager import generate_mesocycle_skeleton
                skeleton_weeks = await generate_mesocycle_skeleton(
                    mesocycle, ucs, db,
                    start_date=req.start_date or week.start_date,
                    event_queue=event_queue,
                    start_week=2,
                )
                await event_queue.put(("progress", {
                    "phase": "skeleton",
                    "text": f"📅 预创建了 {len(skeleton_weeks)} 周框架"
                }))
            except Exception as e:
                # 框架创建失败不应阻止主流程
                print(f"[Fitness] 中周期框架预创建失败: {e}")

            # 提交所有数据库变更
            db.commit()

            # 构建响应数据 + 宏周期详情
            response = _build_week_response(week, db)
            macrocycle_detail = _build_macrocycle_detail(macrocycle, db)

            # 先发送 macrocycle_detail 再发送 done
            await event_queue.put(("macrocycle_detail", macrocycle_detail))
            await event_queue.put(("__DONE__", response))

        except Exception as e:
            import traceback
            traceback.print_exc()
            await event_queue.put(("error", {"text": f"初始化失败: {str(e)}"}))
        finally:
            await event_queue.put(("__END__", None))

    async def _consumer():
        asyncio.create_task(event_stream())
        while True:
            event_type, data = await event_queue.get()
            if event_type == "__END__":
                break
            elif event_type == "__DONE__":
                yield _sse_event("done", json.dumps(data, ensure_ascii=False))
            else:
                yield _sse_event(event_type, json.dumps(data, ensure_ascii=False))

    return StreamingResponse(
        _consumer(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate-next", response_class=StreamingResponse)
async def generate_next(db: Session = Depends(get_db)):
    """基于前一周打卡数据，生成下一周（SSE 流式）。"""
    event_queue: asyncio.Queue = asyncio.Queue()

    async def event_stream():
        try:
            # 找当前活跃的 week
            current_week = db.query(orm_models.Week).filter(
                orm_models.Week.status == "active"
            ).order_by(orm_models.Week.id.desc()).first()

            if not current_week:
                await event_queue.put(("error", {"text": "没有活跃的周计划，请先 init-plan"}))
                await event_queue.put(("__END__", None))
                return

            # 标记前一周完成
            current_week.status = "completed"

            # 生成下一周
            new_week = await generate_next_week(current_week, db, event_queue)

            if new_week is None:
                await event_queue.put(("__END__", None))
                return

            response = _build_week_response(new_week, db)

            # 返回更新后的 macrocycle_detail
            macrocycle = db.query(orm_models.Macrocycle).filter(
                orm_models.Macrocycle.status == "active"
            ).first()
            if macrocycle:
                macrocycle_detail = _build_macrocycle_detail(macrocycle, db)
                await event_queue.put(("macrocycle_detail", macrocycle_detail))

            await event_queue.put(("__DONE__", response))

        except Exception as e:
            import traceback
            traceback.print_exc()
            await event_queue.put(("error", {"text": f"生成失败: {str(e)}"}))
        finally:
            await event_queue.put(("__END__", None))

    async def _consumer():
        asyncio.create_task(event_stream())
        while True:
            event_type, data = await event_queue.get()
            if event_type == "__END__":
                break
            elif event_type == "__DONE__":
                yield _sse_event("done", json.dumps(data, ensure_ascii=False))
            else:
                yield _sse_event(event_type, json.dumps(data, ensure_ascii=False))

    return StreamingResponse(
        _consumer(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/current-week")
async def get_current_week(db: Session = Depends(get_db)):
    """获取当前周的完整计划（含 days → slots → exercise 详情）。"""
    week = db.query(orm_models.Week).filter(
        orm_models.Week.status == "active"
    ).order_by(orm_models.Week.id.desc()).first()

    if not week:
        # 没有活跃周，查最新的
        week = db.query(orm_models.Week).order_by(
            orm_models.Week.id.desc()
        ).first()

    if not week:
        raise HTTPException(status_code=404, detail="还没有训练计划，请先 init-plan")

    return _build_week_response(week, db)


@router.get("/macrocycles")
async def list_macrocycles(db: Session = Depends(get_db)):
    """列出所有大周期。"""
    cycles = db.query(orm_models.Macrocycle).order_by(
        orm_models.Macrocycle.id.desc()
    ).all()
    return [
        {
            "id": c.id,
            "goal": c.goal,
            "start_date": str(c.start_date) if c.start_date else "",
            "status": c.status,
            "created_at": str(c.created_at) if c.created_at else "",
        }
        for c in cycles
    ]


@router.get("/macrocycle/{macrocycle_id}")
async def get_macrocycle(macrocycle_id: int, db: Session = Depends(get_db)):
    """获取大周期详情（嵌套所有子数据）。"""
    mc = db.query(orm_models.Macrocycle).filter(
        orm_models.Macrocycle.id == macrocycle_id
    ).first()
    if not mc:
        raise HTTPException(status_code=404, detail="大周期不存在")

    return _build_macrocycle_detail(mc, db)


@router.post("/checkin")
async def checkin(data: schemas.DayCheckin, db: Session = Depends(get_db)):
    """每日打卡：更新 day + exercise_slot 的实际完成数据。"""
    day = db.query(orm_models.Day).filter(
        orm_models.Day.id == data.day_id
    ).first()
    if not day:
        raise HTTPException(status_code=404, detail="训练日不存在")

    # 更新 day
    day.is_completed = 1 if data.is_completed else 0
    if data.rpe_score:
        day.rpe_score = data.rpe_score

    # 更新每个 slot
    for ex_data in data.exercises:
        slot = db.query(orm_models.ExerciseSlot).filter(
            orm_models.ExerciseSlot.id == ex_data.slot_id,
            orm_models.ExerciseSlot.day_id == data.day_id,
        ).first()
        if not slot:
            continue
        slot.actual_sets = ex_data.actual_sets
        slot.actual_reps = ex_data.actual_reps
        slot.actual_weight_kg = ex_data.actual_weight_kg
        slot.rpe = ex_data.rpe
        slot.notes = ex_data.notes or ""

    db.commit()
    return {"message": "打卡成功", "day_id": data.day_id}


@router.get("/current-state")
async def get_current_state(db: Session = Depends(get_db)):
    """获取用户当前状态。"""
    ucs = db.query(orm_models.UserCurrentState).first()
    if not ucs:
        return {
            "experience_level": "新手",
            "workout_location": "居家",
            "days_per_week": 3,
            "preferred_days": "1,3,5",
            "current_mesocycle_id": None,
        }
    return {
        "id": ucs.id,
        "experience_level": ucs.experience_level,
        "workout_location": ucs.workout_location,
        "days_per_week": ucs.days_per_week,
        "preferred_days": ucs.preferred_days or "1,3,5",
        "current_mesocycle_id": ucs.current_mesocycle_id,
    }


@router.put("/current-state")
async def update_current_state(data: schemas.UserCurrentStateUpdate,
                                db: Session = Depends(get_db)):
    """更新（或创建）用户当前状态（经验/地点/天数）。"""
    ucs = db.query(orm_models.UserCurrentState).first()
    if not ucs:
        # 首次使用时自动创建
        ucs = orm_models.UserCurrentState(
            experience_level=data.experience_level or "新手",
            workout_location=data.workout_location or "居家",
            days_per_week=data.days_per_week or 3,
            preferred_days=data.preferred_days or "1,3,5",
        )
        db.add(ucs)

    if data.experience_level is not None:
        ucs.experience_level = data.experience_level
    if data.workout_location is not None:
        ucs.workout_location = data.workout_location
    if data.days_per_week is not None:
        ucs.days_per_week = data.days_per_week
    if data.preferred_days is not None:
        ucs.preferred_days = data.preferred_days

    db.commit()
    return {"message": "状态已更新"}


@router.put("/day/{day_id}/reschedule")
async def reschedule_day(day_id: int, data: schemas.RescheduleRequest,
                          db: Session = Depends(get_db)):
    """调整训练日到新的 day_of_week（同步更新 date 字段 + 冲突检查）。"""
    day = db.query(orm_models.Day).filter(orm_models.Day.id == day_id).first()
    if not day:
        raise HTTPException(status_code=404, detail="训练日不存在")
    if data.day_of_week < 1 or data.day_of_week > 7:
        raise HTTPException(status_code=400, detail="day_of_week 必须在 1-7 之间")

    # 冲突检查：同一 week_id 内不能有重复 day_of_week
    conflict = db.query(orm_models.Day).filter(
        orm_models.Day.week_id == day.week_id,
        orm_models.Day.id != day_id,
        orm_models.Day.day_of_week == data.day_of_week,
    ).first()
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"day_of_week={data.day_of_week} 已被 Day id={conflict.id} 占用"
        )

    # 同步更新 date
    week = db.query(orm_models.Week).filter(orm_models.Week.id == day.week_id).first()
    if week and week.start_date:
        from datetime import datetime, timedelta
        ws = datetime.strptime(week.start_date, "%Y-%m-%d")
        new_date = ws + timedelta(days=data.day_of_week - 1)
        day.date = new_date.strftime("%Y-%m-%d")

    day.day_of_week = data.day_of_week
    db.commit()
    return {"message": "日期已更新", "day_id": day_id,
            "day_of_week": data.day_of_week, "date": day.date}


# ═══════════════════════════════════════════════════════════════
#  日历 API（新增）
# ═══════════════════════════════════════════════════════════════

@router.get("/calendar-data")
async def get_calendar_data(from_date: str = "", to_date: str = "",
                             db: Session = Depends(get_db)):
    """获取指定日期范围的日历网格轻量数据。

    Query params: from=YYYY-MM-DD, to=YYYY-MM-DD
    返回当月所有日期的状态（含无计划的 days）。
    """
    if not from_date or not to_date:
        raise HTTPException(status_code=400,
                            detail="请提供 from 和 to 参数 (YYYY-MM-DD)")

    # 查询该日期范围内所有 Day
    days = db.query(orm_models.Day).filter(
        orm_models.Day.date >= from_date,
        orm_models.Day.date <= to_date,
    ).order_by(orm_models.Day.date).all()

    # 构建 date → Day 的映射
    day_map = {d.date: d for d in days}

    # 获取中周期阶段映射（week_id → mesocycle_phase）
    week_phases = {}
    for d in days:
        if d.week_id not in week_phases:
            week = db.query(orm_models.Week).filter(
                orm_models.Week.id == d.week_id
            ).first()
            if week:
                meso = db.query(orm_models.Mesocycle).filter(
                    orm_models.Mesocycle.id == week.mesocycle_id
                ).first()
                week_phases[d.week_id] = meso.phase if meso else ""
            else:
                week_phases[d.week_id] = ""

    # 生成日期范围内的所有条目
    from datetime import datetime, timedelta
    start = datetime.strptime(from_date, "%Y-%m-%d")
    end = datetime.strptime(to_date, "%Y-%m-%d")
    current = start

    entries = []
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        day = day_map.get(date_str)
        if day:
            phase = week_phases.get(day.week_id, "")
            day_status = "completed" if day.is_completed else "pending"
            entries.append({
                "date": date_str,
                "has_plan": True,
                "day_status": day_status,
                "focus": day.focus or "",
                "mesocycle_phase": phase,
            })
        else:
            entries.append({
                "date": date_str,
                "has_plan": False,
                "day_status": "no_plan",
                "focus": "",
                "mesocycle_phase": "",
            })
        current += timedelta(days=1)

    return {"entries": entries}


@router.get("/day-detail")
async def get_day_detail(date: str = "",
                          db: Session = Depends(get_db)):
    """获取某天的完整训练内容（含 slots + exercise 详情）。"""
    if not date:
        raise HTTPException(status_code=400, detail="请提供 date 参数 (YYYY-MM-DD)")

    day = db.query(orm_models.Day).filter(
        orm_models.Day.date == date
    ).first()

    if not day:
        return {
            "date": date,
            "day_status": "no_plan",
            "day_label": "",
            "focus": "",
            "week_id": 0,
            "mesocycle_phase": "",
            "is_rest_day": False,
            "has_plan": False,
            "slots": [],
            "warmup": [],
            "main": [],
            "cardio": None,
            "stretch": [],
        }

    # 获取中周期阶段
    week = db.query(orm_models.Week).filter(orm_models.Week.id == day.week_id).first()
    mesocycle_phase = ""
    if week:
        meso = db.query(orm_models.Mesocycle).filter(
            orm_models.Mesocycle.id == week.mesocycle_id
        ).first()
        if meso:
            mesocycle_phase = meso.phase

    # 构建 slots 数据（复用 _build_week_response 中的逻辑）
    response = _build_day_detail(day, db)
    response["mesocycle_phase"] = mesocycle_phase
    return response


# ═══════════════════════════════════════════════════════════════
#  旧接口（保留向后兼容）
# ═══════════════════════════════════════════════════════════════

@router.get("/plans")
async def get_plans(db: Session = Depends(get_db)):
    """（旧）获取历史计划列表 — 仅查看旧版数据。"""
    plans = db.query(orm_models.FitnessPlan).order_by(
        orm_models.FitnessPlan.id.desc()
    ).all()
    return [
        {
            "id": p.id,
            "goal": p.goal,
            "duration_weeks": p.duration_weeks,
            "days_per_week": p.days_per_week,
            "created_at": str(p.created_at),
        }
        for p in plans
    ]


@router.get("/plan/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """（旧）获取单个旧版计划详情。"""
    plan = db.query(orm_models.FitnessPlan).filter(
        orm_models.FitnessPlan.id == plan_id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    try:
        plan_content = json.loads(plan.plan_content) if plan.plan_content else {}
    except (json.JSONDecodeError, TypeError):
        plan_content = {}
    return {
        "id": plan.id,
        "goal": plan.goal,
        "experience_level": plan.experience_level,
        "workout_location": plan.workout_location,
        "days_per_week": plan.days_per_week,
        "duration_weeks": plan.duration_weeks,
        **plan_content,
        "created_at": str(plan.created_at),
    }


# ═══════════════════════════════════════════════════════════════
#  辅助函数
# ═══════════════════════════════════════════════════════════════

def _build_week_response(week: orm_models.Week, db: Session) -> dict:
    """构建周计划的 JSON 响应（含按阶段分组的 days/slots/exercise）。"""
    days = db.query(orm_models.Day).filter(
        orm_models.Day.week_id == week.id
    ).order_by(orm_models.Day.day_order).all()

    days_data = []
    for day in days:
        slots = db.query(orm_models.ExerciseSlot).filter(
            orm_models.ExerciseSlot.day_id == day.id
        ).order_by(orm_models.ExerciseSlot.sort_order).all()

        slots_data = []
        for slot in slots:
            # 主项用 wger_id，热身/有氧/拉伸用 exercise_id
            ex = None
            if slot.exercise_id:
                ex = db.query(orm_models.Exercise).filter(
                    orm_models.Exercise.id == slot.exercise_id
                ).first()
            slot_dict = {
                "id": slot.id,
                "phase_type": slot.phase_type,
                "sort_order": slot.sort_order,
                "wger_id": slot.wger_id,
                "exercise_name": slot.exercise_name,
                "target_sets": slot.target_sets,
                "target_reps": slot.target_reps,
                "target_reps_max": slot.target_reps_max,
                "weight_kg": slot.weight_kg,
                "weight_suggestion": slot.weight_suggestion,
                "rest_seconds": slot.rest_seconds,
                "actual_sets": slot.actual_sets,
                "actual_reps": slot.actual_reps,
                "rpe": slot.rpe,
                "notes": slot.notes,
                "exercise": {
                    "id": ex.id if ex else None,
                    "name": ex.name if ex else (slot.wger_id and f"wger:{slot.wger_id}" or "未知"),
                    "target_muscle": ex.target_muscle if ex else "",
                    "muscle_group": ex.muscle_group if ex else "",
                    "equipment": ex.equipment if ex else "",
                    "image_url": ex.image_url if ex else "",
                    "description": ex.description if ex else "",
                    "instruction": slot.weight_suggestion or "",
                } if ex else ({
                    "id": None,
                    "name": slot.exercise_name or (f"wger:{slot.wger_id}" if slot.wger_id else "未知"),
                    "target_muscle": "",
                    "muscle_group": "",
                    "equipment": "",
                    "image_url": "",
                    "description": "",
                    "instruction": slot.weight_suggestion or "",
                }),
            }
            slots_data.append(slot_dict)

        # 按 phase_type 分组
        def _to_exercise_item(s: dict) -> dict:
            ex = s.get("exercise") or {}
            return {
                "name": ex.get("name", ""),
                "target_muscle": ex.get("target_muscle", ""),
                "sets": s.get("target_sets", 0),
                "reps": s.get("target_reps", 0),
                "weight_suggestion": s.get("weight_suggestion", ""),
                "instruction": ex.get("instruction", ""),
                "duration_minutes": s.get("target_reps", 15) if s["phase_type"] == "cardio" else None,
                "suggestion": s.get("weight_suggestion", ""),
            }

        warmup_items = [_to_exercise_item(s) for s in slots_data if s["phase_type"] == "warmup"]
        main_items = [_to_exercise_item(s) for s in slots_data if s["phase_type"] == "main"]
        cardio_slot = next((s for s in slots_data if s["phase_type"] == "cardio"), None)
        cardio_item = _to_exercise_item(cardio_slot) if cardio_slot else None
        stretch_items = [_to_exercise_item(s) for s in slots_data if s["phase_type"] == "stretch"]

        days_data.append({
            "id": day.id,
            "day_order": day.day_order,
            "day_of_week": day.day_of_week or 0,
            "date": day.date or "",
            "day_label": day.day_label,
            "focus": day.focus,
            "estimated_calories": day.estimated_calories,
            "is_completed": day.is_completed,
            "rpe_score": day.rpe_score,
            "slots": slots_data,
            "warmup": warmup_items,
            "main": main_items,
            "cardio": cardio_item,
            "stretch": stretch_items,
        })

    mesocycle = db.query(orm_models.Mesocycle).filter(
        orm_models.Mesocycle.id == week.mesocycle_id
    ).first()

    return {
        "id": week.id,
        "week_number": week.week_number,
        "start_date": week.start_date or "",
        "status": week.status,
        "generated_at": str(week.generated_at) if week.generated_at else "",
        "mesocycle_phase": mesocycle.phase if mesocycle else "",
        "days": days_data,
    }


def _build_macrocycle_detail(mc: orm_models.Macrocycle, db: Session) -> dict:
    """构建大周期的完整 JSON 响应（嵌套所有子数据）。"""
    mesocycles = db.query(orm_models.Mesocycle).filter(
        orm_models.Mesocycle.macrocycle_id == mc.id
    ).order_by(orm_models.Mesocycle.sort_order).all()

    meso_data = []
    for ms in mesocycles:
        weeks = db.query(orm_models.Week).filter(
            orm_models.Week.mesocycle_id == ms.id
        ).order_by(orm_models.Week.week_number).all()

        weeks_data = []
        for w in weeks:
            days = db.query(orm_models.Day).filter(
                orm_models.Day.week_id == w.id
            ).order_by(orm_models.Day.day_order).all()

            completed_days = sum(1 for d in days if d.is_completed)
            total_days = len(days) or 1
            week_completion_rate = round((completed_days / total_days) * 100)

            weeks_data.append({
                "id": w.id,
                "week_number": w.week_number,
                "status": w.status,
                "day_count": len(days),
                "completed_days": completed_days,
                "completion_rate": week_completion_rate,
            })

        # mesocycle 级完成率（已有数据的周的均值）
        active_weeks = [w for w in weeks_data if w["status"] != "pending"]
        if active_weeks:
            meso_completion = round(sum(w["completion_rate"] for w in active_weeks) / len(active_weeks))
        else:
            meso_completion = 0

        meso_data.append({
            "id": ms.id,
            "phase": ms.phase,
            "week_count": ms.week_count,
            "sort_order": ms.sort_order,
            "status": ms.status,
            "completion_rate": meso_completion,
            "weeks": weeks_data,
        })

    return {
        "id": mc.id,
        "goal": mc.goal,
        "start_date": str(mc.start_date) if mc.start_date else "",
        "status": mc.status,
        "created_at": str(mc.created_at) if mc.created_at else "",
        "mesocycles": meso_data,
    }


def _build_day_detail(day: orm_models.Day, db: Session) -> dict:
    """构建单日训练的 JSON 响应（含 slots 分组）。"""
    slots = db.query(orm_models.ExerciseSlot).filter(
        orm_models.ExerciseSlot.day_id == day.id
    ).order_by(orm_models.ExerciseSlot.sort_order).all()

    slots_data = []
    for slot in slots:
        ex = None
        if slot.exercise_id:
            ex = db.query(orm_models.Exercise).filter(
                orm_models.Exercise.id == slot.exercise_id
            ).first()
        # 降级：exercise_id 为空时按 wger_id 查
        if not ex and slot.wger_id:
            ex = db.query(orm_models.Exercise).filter(
                orm_models.Exercise.wger_id == slot.wger_id
            ).first()
        # 再降级：本地还没缓存，从 wger 拉取并缓存（针对已有计划）
        if not ex and slot.wger_id:
            try:
                ex = get_or_fetch_exercise(slot.wger_id, db)
            except Exception:
                pass
        # 懒加载回填：ex 存在但缺图片，异步信号（前端的 ExerciseDrawer 会异步调 /api/wger/exercise/{id}）
        # 去掉同步 HTTP 请求以解决加载慢的问题
        slot_dict = {
            "id": slot.id,
            "phase_type": slot.phase_type,
            "sort_order": slot.sort_order,
            "wger_id": slot.wger_id,
            "exercise_name": slot.exercise_name,
            "target_sets": slot.target_sets,
            "target_reps": slot.target_reps,
            "target_reps_max": slot.target_reps_max,
            "weight_kg": slot.weight_kg,
            "weight_suggestion": slot.weight_suggestion,
            "rest_seconds": slot.rest_seconds,
            "actual_sets": slot.actual_sets,
            "actual_reps": slot.actual_reps,
            "actual_weight_kg": slot.actual_weight_kg,
            "rpe": slot.rpe,
            "notes": slot.notes,
            "exercise": {
                "id": ex.id if ex else None,
                "name": ex.name if ex else (slot.wger_id and f"wger:{slot.wger_id}" or "未知"),
                "target_muscle": ex.target_muscle if ex else "",
                "muscle_group": ex.muscle_group if ex else "",
                "movement_pattern": ex.movement_pattern if ex else "",
                "equipment": ex.equipment if ex else "",
                "image_url": ex.image_url if ex else "",
                "description": ex.description if ex else "",
                "difficulty": ex.difficulty if ex else 1,
                "instruction": slot.weight_suggestion or "",
            } if ex else ({
                "id": None,
                "name": slot.exercise_name or (f"wger:{slot.wger_id}" if slot.wger_id else "未知"),
                "target_muscle": "",
                "muscle_group": "",
                "movement_pattern": "",
                "equipment": "",
                "image_url": "",
                "description": "",
                "difficulty": 1,
                "instruction": slot.weight_suggestion or "",
            }),
        }
        slots_data.append(slot_dict)

    def _to_exercise_item(s: dict) -> dict:
        ex = s.get("exercise") or {}
        base = {
            "id": s.get("id"),
            "phase_type": s.get("phase_type", ""),
            "name": ex.get("name", ""),
            "exercise_name": ex.get("name", ""),
            "target_muscle": ex.get("target_muscle", ""),
            "sets": s.get("target_sets", 0),
            "target_sets": s.get("target_sets", 0),
            "reps": s.get("target_reps", 0),
            "target_reps": s.get("target_reps", 0),
            "target_reps_max": s.get("target_reps_max", 0),
            "weight_kg": s.get("weight_kg", 0),
            "weight_suggestion": s.get("weight_suggestion", ""),
            "rest_seconds": s.get("rest_seconds", 60),
            "instruction": ex.get("instruction", ""),
            "duration_minutes": s.get("target_reps", 15) if s["phase_type"] == "cardio" else None,
            "suggestion": s.get("weight_suggestion", ""),
        }
        return base

    day_status = "completed" if day.is_completed else "pending"

    return {
        "date": day.date or "",
        "day_status": day_status,
        "day_label": day.day_label or "",
        "focus": day.focus or "",
        "week_id": day.week_id,
        "is_rest_day": False,
        "has_plan": True,
        "slots": slots_data,
        "warmup": [_to_exercise_item(s) for s in slots_data if s["phase_type"] == "warmup"],
        "main": [_to_exercise_item(s) for s in slots_data if s["phase_type"] == "main"],
        "cardio": _to_exercise_item(next((s for s in slots_data if s["phase_type"] == "cardio"), None)) if any(s["phase_type"] == "cardio" for s in slots_data) else None,
        "stretch": [_to_exercise_item(s) for s in slots_data if s["phase_type"] == "stretch"],
    }
