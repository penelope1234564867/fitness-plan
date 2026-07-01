"""渐进超负荷引擎 — 双渐进（Double Progression）规则

核心逻辑：
  每个动作设定次数范围（如 8-12 次）。
  先加次数，达到上限后加重量，次数回到下限。
"""

from typing import Optional
from app.models.orm_models import ExerciseSlot

# 各阶段参数表
PHASE_PARAMS = {
    "foundational": {
        "rep_lower": 12,
        "rep_upper": 15,
        "sets": 2,
        "weight_increment": 0.0,      # 基础期不加重量，只加次数
        "rest_seconds": 90,
    },
    "hypertrophy": {
        "rep_lower": 8,
        "rep_upper": 12,
        "sets": 3,
        "weight_increment": 1.25,     # 小重量递增
        "rest_seconds": 75,
    },
    "strength": {
        "rep_lower": 5,
        "rep_upper": 8,
        "sets": 4,
        "weight_increment": 2.5,      # 大重量递增
        "rest_seconds": 120,
    },
    "deload": {
        "rep_lower": 10,
        "rep_upper": 12,
        "sets": 2,                     # 组数减半
        "weight_increment": 0.0,       # 不加重量
        "rest_seconds": 90,
    },
}


def calc_next_week_params(
    prev_slot: ExerciseSlot,
    phase: str,
) -> dict:
    """根据前一周的完成情况和当前阶段，计算下周的计划参数。

    Args:
        prev_slot: 前一周的 exercise_slot（含 actual_* 打卡数据）
        phase: 当前阶段 foundational / hypertrophy / strength / deload

    Returns:
        dict: 包含 target_sets, target_reps, target_reps_max, weight_kg, rest_seconds
    """
    params = PHASE_PARAMS.get(phase, PHASE_PARAMS["foundational"])

    # 双渐进核心判断
    actual_reps = getattr(prev_slot, "actual_reps", 0) or 0
    target_reps_max = getattr(prev_slot, "target_reps_max", params["rep_upper"]) or params["rep_upper"]
    weight_kg = getattr(prev_slot, "weight_kg", 0.0) or 0.0
    actual_sets = getattr(prev_slot, "actual_sets", 0) or 0
    target_sets = getattr(prev_slot, "target_sets", params["sets"]) or params["sets"]
    rpe = getattr(prev_slot, "rpe", 0) or 0

    # 如果没打卡，保持相同参数
    if actual_reps == 0 and actual_sets == 0:
        return {
            "target_sets": target_sets,
            "target_reps": params["rep_lower"],
            "target_reps_max": params["rep_upper"],
            "weight_kg": weight_kg,
            "rest_seconds": params["rest_seconds"],
        }

    # 达到次数上限 → 加重量，次数回到下限
    if actual_reps >= target_reps_max and rpe <= 8:
        new_weight = weight_kg + params["weight_increment"]
        new_reps = params["rep_lower"]
    elif rpe >= 9:
        # RPE 太高 → 保持或减量
        new_weight = max(0, weight_kg - params["weight_increment"])
        new_reps = max(params["rep_lower"], getattr(prev_slot, "target_reps", 0) - 1)
    else:
        # 没到上限 → 加次数
        new_weight = weight_kg
        current_target = getattr(prev_slot, "target_reps", params["rep_lower"]) or params["rep_lower"]
        new_reps = min(current_target + 1, params["rep_upper"])

    return {
        "target_reps": new_reps,
        "target_reps_max": params["rep_upper"],
        "weight_kg": new_weight,
        "rest_seconds": params["rest_seconds"],
        "target_sets": params["sets"],
    }


def calc_deload_params(slot: ExerciseSlot) -> dict:
    """减载周参数：组数减半，重量降低 50-60%。"""
    params = PHASE_PARAMS["deload"]
    weight = getattr(slot, "weight_kg", 0.0) or 0.0
    return {
        "target_sets": params["sets"],
        "target_reps": params["rep_lower"],
        "target_reps_max": params["rep_upper"],
        "weight_kg": round(weight * 0.5, 1),
        "rest_seconds": params["rest_seconds"],
    }
