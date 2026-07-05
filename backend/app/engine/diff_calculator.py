"""diff_calculator — 计算每个动作与上周同动作的对比差异

纯函数模块，无副作用。
提供给 get_day_detail() 调用，为每个 slot 计算 change_type。
当动作被替换时（新动作无 exercise_id 匹配），按同肌群找上周的旧动作名。
"""
from typing import Dict
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from app.models.orm_models import Day


def compute_slot_diffs(
    current_slots: list,
    prev_week_id: int,
    db: Session,
    prev_phase: str = "",
) -> Dict[int, Dict]:
    """对比当天动作与上周同 exercise_id 的最近一次数据。

    Args:
        current_slots: 当天的 ExerciseSlot 对象列表
        prev_week_id: 上一周 week.id
        db: 数据库 session

    Returns:
        {slot_id: {change_type, weight_diff, prev_weight_kg, prev_target_reps,
                    prev_exercise_name}}
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
    #    同时按 muscle_group 分组（用于新动作找同肌群替代关系）
    prev_by_exercise: Dict[int, dict] = {}
    prev_by_muscle_group: Dict[str, dict] = {}
    for day in prev_days:
        for slot in (day.slots or []):
            if getattr(slot, "phase_type", "") != "main":
                continue
            eid = getattr(slot, "exercise_id", None)
            if not eid or eid in prev_by_exercise:
                continue
            # 获取 exercise 的 muscle_group
            exercise = slot.exercise if hasattr(slot, 'exercise') else None
            if exercise is None and eid:
                from app.models.orm_models import Exercise
                exercise = db.query(Exercise).filter(Exercise.id == eid).first()
            muscle_group = getattr(exercise, "muscle_group", "") or ""
            prev_by_exercise[eid] = {
                "weight_kg": getattr(slot, "weight_kg", 0) or 0,
                "target_reps": getattr(slot, "target_reps", 0) or 0,
                "target_sets": getattr(slot, "target_sets", 0) or 0,
                "exercise_name": getattr(slot, "exercise_name", "") or "",
                "muscle_group": muscle_group,
                "day_of_week": day.day_of_week,
            }
            # 同肌群只保留最后一条（day_of_week 降序）
            if muscle_group and muscle_group not in prev_by_muscle_group:
                prev_by_muscle_group[muscle_group] = prev_by_exercise[eid]

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
            # 新动作：按同肌群找上周练的是什么
            exercise = slot.exercise if hasattr(slot, 'exercise') else None
            if exercise is None and eid:
                from app.models.orm_models import Exercise
                exercise = db.query(Exercise).filter(Exercise.id == eid).first()
            cur_muscle_group = getattr(exercise, "muscle_group", "") or ""

            prev_name = ""
            prev_reps = 0
            prev_sets = 0
            if cur_muscle_group and cur_muscle_group in prev_by_muscle_group:
                prev_data = prev_by_muscle_group[cur_muscle_group]
                prev_name = prev_data.get("exercise_name", "")
                prev_reps = prev_data.get("target_reps", 0) or 0
                prev_sets = prev_data.get("target_sets", 0) or 0

            results[slot.id] = {
                "change_type": "new_exercise",
                "weight_diff": 0,
                "prev_weight_kg": 0,
                "prev_target_reps": prev_reps,
                "prev_target_sets": prev_sets,
                "prev_exercise_name": prev_name,
                "prev_phase": prev_phase,
            }
            continue

        prev_weight = prev["weight_kg"]
        prev_reps = prev["target_reps"]
        prev_sets = prev.get("target_sets", 0) or 0
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
            "prev_target_sets": prev_sets,
            "prev_exercise_name": prev.get("exercise_name", ""),
            "prev_phase": prev_phase,
        }

    return results
