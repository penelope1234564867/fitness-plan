"""diff_calculator — 计算每个动作与上周同动作的对比差异

纯函数模块，无副作用。
提供给 get_day_detail() 调用，为每个 slot 计算 change_type。
"""
from typing import Dict
from sqlalchemy.orm import Session
from app.models.orm_models import Day


def compute_slot_diffs(
    current_slots: list,
    prev_week_id: int,
    db: Session,
) -> Dict[int, Dict]:
    """对比当天动作与上周同 exercise_id 的最近一次数据。

    Args:
        current_slots: 当天的 ExerciseSlot 对象列表（不含 warmup/stretch）
        prev_week_id: 上一周 week.id
        db: 数据库 session

    Returns:
        {slot_id: {change_type, weight_diff, prev_weight_kg, prev_target_reps}}
        只包含 phase_type == 'main' 的 slot
    """
    if not prev_week_id:
        return {}

    # 1. 获取上周所有天
    prev_days = (
        db.query(Day)
        .filter(Day.week_id == prev_week_id)
        .order_by(Day.day_of_week.desc())
        .all()
    )
    if not prev_days:
        return {}

    # 2. 获取上周所有 main slot，按 exercise_id 分组取最近一天
    prev_by_exercise: Dict[int, dict] = {}
    for day in prev_days:
        for slot in (day.slots or []):
            if getattr(slot, "phase_type", "") != "main":
                continue
            eid = getattr(slot, "exercise_id", None)
            if not eid or eid in prev_by_exercise:
                continue  # 已经有过该 exercise_id 的记录，day_of_week 降序第一个就是最近
            prev_by_exercise[eid] = {
                "weight_kg": getattr(slot, "weight_kg", 0) or 0,
                "target_reps": getattr(slot, "target_reps", 0) or 0,
                "day_of_week": day.day_of_week,
            }

    # 3. 计算每个 slot 的 diff
    results: Dict[int, Dict] = {}
    for slot in current_slots:
        if getattr(slot, "phase_type", "") != "main":
            continue

        eid = getattr(slot, "exercise_id", None)
        if not eid:
            continue

        cur_weight = getattr(slot, "weight_kg", 0) or 0
        cur_reps = getattr(slot, "target_reps", 0) or 0

        prev = prev_by_exercise.get(eid)
        if not prev:
            results[slot.id] = {
                "change_type": "new_exercise",
                "weight_diff": 0,
                "prev_weight_kg": 0,
                "prev_target_reps": 0,
            }
            continue

        prev_weight = prev["weight_kg"]
        prev_reps = prev["target_reps"]
        weight_diff = round(cur_weight - prev_weight, 1)

        if cur_weight > prev_weight:
            change_type = "increased_weight"
        elif cur_weight < prev_weight:
            change_type = "decreased_weight"
        elif cur_reps > prev_reps:
            change_type = "increased_reps"
        else:
            change_type = "same"

        results[slot.id] = {
            "change_type": change_type,
            "weight_diff": weight_diff,
            "prev_weight_kg": prev_weight,
            "prev_target_reps": prev_reps,
        }

    return results
