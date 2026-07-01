"""中周期管理器 — 阶段切换与减载决策

负责在每周生成时判断：
1. 当前中周期是否结束
2. 下一阶段是什么（foundational → hypertrophy → strength → deload → 循环）
3. 是否需要提前插入减载周
"""


# 阶段顺序
PHASE_ORDER = ["foundational", "hypertrophy", "strength"]


def decide_next_phase(current_phase: str, completion_rate: float) -> str:
    """根据完成率和当前阶段，决策下一中周期阶段。

    Args:
        current_phase: 当前阶段 foundational / hypertrophy / strength / deload
        completion_rate: 该中周期的平均完成率 (0.0 - 1.0)

    Returns:
        str: 下一阶段名称
    """
    # 完成率低于 60% → 重复当前阶段
    if completion_rate < 0.6:
        return current_phase

    # 减载完成后 → 进入下一轮（hypertrophy）
    if current_phase == "deload":
        return "hypertrophy"

    # 正常阶段递进
    if current_phase in PHASE_ORDER:
        idx = PHASE_ORDER.index(current_phase)
        if idx < len(PHASE_ORDER) - 1:
            return PHASE_ORDER[idx + 1]  # foundational → hypertrophy → strength
        return "deload"  # strength 完成后减载

    # 未知阶段 → 默认 hypertrophy
    return "hypertrophy"


def needs_deload_this_week(week_data: dict) -> bool:
    """判断本周是否需要提前插入减载周。

    基于自适应引擎输出的 week_data 做判断。

    Args:
        week_data: analyze_week() 的输出，含 needs_deload / high_rpe_ratio

    Returns:
        bool: True 表示需要插入减载周
    """
    return week_data.get("needs_deload", False)


def is_mesocycle_complete(
    current_week_number: int,
    mesocycle_week_count: int,
) -> bool:
    """判断当前中周期是否已完成。

    Args:
        current_week_number: 当前周在中周期内的序号（1-based）
        mesocycle_week_count: 该中周期的总周数

    Returns:
        bool: True 表示该中周期已完成，需要切换
    """
    return current_week_number >= mesocycle_week_count
