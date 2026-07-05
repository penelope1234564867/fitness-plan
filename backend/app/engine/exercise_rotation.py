"""动作轮换引擎 — 每中周期沿变式链移动到下一难度级别

每个肌群的某个动作维护一条变式链（如俯卧撑系列），
每 4 周（中周期边界）沿链条前进一个级别，避免身体适应。
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.orm_models import Exercise, ExerciseVariation, ExerciseSlot

logger = logging.getLogger("exercise_rotation")


def rotate_exercise(
    exercise_id: int,
    db: Session,
    direction: str = "next",
) -> int:
    """沿变式链移动动作到下一个/上一个难度级别。

    Args:
        exercise_id: 当前动作的 exercise.id
        db: 数据库 session
        direction: "next" 升阶 / "prev" 降阶

    Returns:
        int: 新的 exercise_id（没有变式链则返回原 id）
    """
    ex = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not ex:
        return exercise_id

    # 查当前动作属于哪个变式系列
    current_var = db.query(ExerciseVariation).filter(
        ExerciseVariation.exercise_id == exercise_id
    ).first()
    if not current_var:
        # 不在任何变式链中，保持原样
        return exercise_id

    series_name = current_var.series_name
    current_order = current_var.sort_order

    if direction == "next":
        # 找本系列中下一难度
        next_var = db.query(ExerciseVariation).filter(
            ExerciseVariation.series_name == series_name,
            ExerciseVariation.sort_order > current_order,
        ).order_by(ExerciseVariation.sort_order).first()

        if next_var:
            return next_var.exercise_id
        # 已经是最高难度 → 循环回最简单
        first_var = db.query(ExerciseVariation).filter(
            ExerciseVariation.series_name == series_name,
        ).order_by(ExerciseVariation.sort_order).first()
        return first_var.exercise_id if first_var else exercise_id

    else:  # direction == "prev"
        prev_var = db.query(ExerciseVariation).filter(
            ExerciseVariation.series_name == series_name,
            ExerciseVariation.sort_order < current_order,
        ).order_by(ExerciseVariation.sort_order.desc()).first()

        if prev_var:
            return prev_var.exercise_id
        # 已经是最低难度 → 保持
        return exercise_id


def rotate_slots_for_new_mesocycle(
    slots: List[ExerciseSlot],
    db: Session,
) -> List[dict]:
    """给定一批 exercise_slot，全部沿变式链移动到下一个难度级别。

    只轮换 main 阶段的动作，warmup 和 cooldown 保持原样。
    2026-07-04: 缓存池模式下，主力轮换逻辑被 PoolManager.refresh_pool 替代，
    此函数保留作为后备（没有缓存池的数据时）。

    Args:
        slots: 当前中周期最后一周的 exercise_slot 列表
        db: 数据库 session

    Returns:
        List[dict]: [{"slot_id": int, "new_exercise_id": int, "old_exercise_id": int}, ...]
    """
    results = []
    for slot in slots:
        if getattr(slot, "phase_type", "") != "main":
            continue

        old_id = slot.exercise_id
        new_id = rotate_exercise(old_id, db, direction="next")

        if new_id != old_id:
            logger.info(f"[Rotation] 轮换: slot={slot.id}, {slot.exercise_name} ({old_id}) → ({new_id})")

        results.append({
            "slot_id": slot.id,
            "old_exercise_id": old_id,
            "new_exercise_id": new_id,
        })

    return results
