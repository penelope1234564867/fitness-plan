"""自适应调整引擎 — 基于 RPE 和完成情况的调整规则

根据用户打卡数据（RPE、实际组数/次数、备注），
为下周生成提供调整建议。
"""

from typing import List, Optional
from app.models.orm_models import ExerciseSlot, Day


def analyze_slot(slot: ExerciseSlot) -> dict:
    """分析单个动作的打卡数据，返回调整建议。

    Args:
        slot: 已打卡的 exercise_slot 对象

    Returns:
        dict: {"action": str, "reason": str}
          action 取值:
            "keep"              保持当前参数
            "increase_weight"   加重量（太轻松）
            "increase_reps"     加次数（达到上限）
            "reduce_intensity"  降强度（太难）
            "swap_exercise"     替换动作（疼痛/超负荷）
    """
    rpe = getattr(slot, "rpe", 0) or 0
    actual_sets = getattr(slot, "actual_sets", 0) or 0
    target_sets = getattr(slot, "target_sets", 3) or 3
    actual_reps = getattr(slot, "actual_reps", 0) or 0
    target_reps_max = getattr(slot, "target_reps_max", 12) or 12
    notes = getattr(slot, "notes", "") or ""

    # 没打卡 — 不调整
    if rpe == 0 or (actual_sets == 0 and actual_reps == 0):
        return {"action": "keep", "reason": "no_data"}

    # 用户反馈疼痛 → 直接替换动作
    pain_keywords = ["疼", "痛", "受伤", "不舒服", "酸胀异常", "扭伤"]
    if any(kw in notes for kw in pain_keywords):
        return {"action": "swap_exercise", "reason": f"疼痛反馈: {notes}"}

    # RPE 10 或未完成 → 降阶/减量
    if rpe >= 10 or (actual_sets < target_sets and rpe >= 8):
        return {"action": "swap_exercise" if rpe >= 10 else "reduce_intensity",
                "reason": f"RPE={rpe}, 完成 {actual_sets}/{target_sets} 组"}

    # RPE ≤ 5 且全部完成 → 太轻松，加重量
    if rpe <= 5 and actual_sets >= target_sets:
        return {"action": "increase_weight", "reason": f"RPE={rpe}, 全部完成"}

    # RPE ≤ 7 且达到次数上限 → 可以加次数
    if rpe <= 7 and actual_reps >= target_reps_max:
        return {"action": "increase_reps", "reason": f"达到次数上限 {target_reps_max} 次"}

    # RPE 8-9 且完成 → 保持
    if 8 <= rpe <= 9 and actual_sets >= target_sets:
        return {"action": "keep", "reason": f"RPE={rpe}, 强度适中"}

    # 默认保持
    return {"action": "keep", "reason": "default"}


def analyze_week(days: List[Day]) -> dict:
    """分析一周整体数据，判断是否需要提前减载或降阶。

    Args:
        days: 本周所有 Day 对象（含 slots 关系）

    Returns:
        dict: {
            "high_rpe_ratio": float,    # RPE>=9 的动作比例
            "no_checkin_ratio": float,  # 未打卡的比例
            "needs_deload": bool,        # 是否需要提前减载
            "completion_rate": float,    # 整体完成率
        }
    """
    all_slots = []
    for day in days:
        if hasattr(day, "slots") and day.slots:
            all_slots.extend(day.slots)

    if not all_slots:
        return {
            "high_rpe_ratio": 0.0,
            "no_checkin_ratio": 1.0,
            "needs_deload": False,
            "completion_rate": 0.0,
        }

    total = len(all_slots)
    high_rpe_count = sum(1 for s in all_slots if (getattr(s, "rpe", 0) or 0) >= 9)
    no_checkin_count = sum(
        1 for s in all_slots
        if (getattr(s, "rpe", 0) or 0) == 0
    )
    completed_count = sum(
        1 for s in all_slots
        if (getattr(s, "actual_sets", 0) or 0) > 0
    )

    # 如果有任何实际打卡数据，才基于打卡率判断是否需减载
    # 如果完全没有打卡数据（新生成的周），不触发减载
    has_any_checkin = completed_count > 0
    needs_deload = (
        has_any_checkin
        and (high_rpe_count / total > 0.5
             or (no_checkin_count > 0 and no_checkin_count / total > 0.8))
    )

    return {
        "high_rpe_ratio": round(high_rpe_count / total, 2),
        "no_checkin_ratio": round(no_checkin_count / total, 2),
        "needs_deload": needs_deload,
        "completion_rate": round(completed_count / total, 2),
    }


# ═══════════════════════════════════════════════════════════════
#  用户数据压缩（generate_next_week 重构新增）
# ═══════════════════════════════════════════════════════════════

def update_user_state(
    current_week,
    week_analysis: dict,
    db,
):
    """更新 UserCurrentState 的压缩历史字段。

    在 generate_next_week() 末尾调用。

    Args:
        current_week: Week 对象（含 week_number）
        week_analysis: analyze_week 返回的分析结果
        db: 数据库 session
    """
    from app.models.orm_models import UserCurrentState
    ucs = db.query(UserCurrentState).first()
    if not ucs:
        return

    import json

    # 更新 weekly_progress
    progress = json.loads(ucs.weekly_progress or "[]")
    progress.append({
        "week": current_week.week_number,
        "completion_rate": week_analysis.get("completion_rate", 0),
        "avg_rpe": week_analysis.get("avg_rpe", 0),
    })
    if len(progress) > 10:  # 只保留最近 10 周
        progress = progress[-10:]
    ucs.weekly_progress = json.dumps(progress, ensure_ascii=False)

    # 更新 RPE 趋势
    if len(progress) >= 2:
        recent = progress[-2:]
        rpe_prev = recent[0].get("avg_rpe", 0) or 0
        rpe_curr = recent[1].get("avg_rpe", 0) or 0
        if rpe_curr > rpe_prev + 0.5:
            ucs.rpe_trend = "rising"
        elif rpe_curr < rpe_prev - 0.5:
            ucs.rpe_trend = "falling"
        else:
            ucs.rpe_trend = "stable"

    # 更新平均完成率（移动平均 4 周）
    recent_cr = [p["completion_rate"] for p in progress[-4:] if isinstance(p.get("completion_rate"), (int, float))]
    ucs.avg_completion_rate = round(sum(recent_cr) / len(recent_cr), 2) if recent_cr else 0.0

    # 检查是否连续完成
    if week_analysis.get("completion_rate", 0) >= 0.7:
        ucs.consecutive_weeks_completed += 1
    else:
        ucs.consecutive_weeks_completed = 0


def update_blacklist(prev_days: list, db):
    """更新 exercise_blacklist。

    在 analyze_week 后调用，检查每个 slot 的 RPE。

    Args:
        prev_days: 前一周的 Day 对象列表（含 slots）
        db: 数据库 session
    """
    from app.models.orm_models import UserCurrentState
    ucs = db.query(UserCurrentState).first()
    if not ucs:
        return

    import json

    blacklist = json.loads(ucs.exercise_blacklist or "[]")
    high_rpe_exercises = set()

    for day in prev_days:
        for slot in (day.slots or []):
            if (getattr(slot, "rpe", 0) or 0) >= 9:
                if slot.exercise_name:
                    high_rpe_exercises.add(slot.exercise_name)

    # 简化策略：只保留仍在 high_rpe_exercises 中的黑名单项
    new_blacklist = [name for name in blacklist if name in high_rpe_exercises]
    # 连续 2 周 RPE≥9 才加入黑名单（简化：暂时由调用方处理频率计数）
    for name in high_rpe_exercises:
        if name not in new_blacklist:
            # 首次出现，标记为"观察"而不是立即拉黑
            pass

    ucs.exercise_blacklist = json.dumps(new_blacklist, ensure_ascii=False)
