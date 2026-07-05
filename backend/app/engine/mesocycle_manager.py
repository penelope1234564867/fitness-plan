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


# ═══════════════════════════════════════════════════════════════
#  中周期框架预生成（路线图用）
# ═══════════════════════════════════════════════════════════════

from datetime import datetime, timedelta
import asyncio
from typing import Optional


async def generate_mesocycle_skeleton(
    mesocycle,
    ucs,
    db,
    start_date: str,
    event_queue: Optional[asyncio.Queue] = None,
    start_week: int = 1,
):
    """为中周期预创建 Week 和 Day 的框架（无 ExerciseSlot）。

    创建 mesocycle.week_count 个 Week 从 start_week 开始，
    以及每个 Week 中对应 ucs.days_per_week 个 Day。
    Days 只有框架字段（day_order, date, day_of_week, day_label, focus），
    不含具体的 ExerciseSlot——那些会在每周 generate-next 时生成。

    典型用法：
      - init-plan 后调用 start_week=2 创建第2-4周框架（第1周已存在）
      - 新 mesocycle 切换时调用 start_week=1 创建全部4周

    Args:
        mesocycle: Mesocycle ORM 对象（需已 flush，有 id）
        ucs: UserCurrentState ORM 对象（需有 days_per_week, preferred_days）
        db: SQLAlchemy Session
        start_date: 起始日期 "YYYY-MM-DD"，会自动对齐到周一
        event_queue: 可选的 SSE 事件队列，用于发送进度
        start_week: 起始周序号（1-based），默认从第1周开始

    Returns:
        list[Week]: 创建的 Week 对象列表（每个 Week 含 days 列表）
    """
    from app.models import orm_models

    # 对齐到周一
    dt = datetime.strptime(start_date, "%Y-%m-%d")
    monday = dt - timedelta(days=dt.weekday())

    preferred_days = sorted(set(
        int(d.strip()) for d in (ucs.preferred_days or "1,3,5").split(",") if d.strip()
    ))
    if not preferred_days:
        preferred_days = [1, 3, 5]

    created_weeks = []

    for week_num in range(start_week, mesocycle.week_count + 1):
        week_start = monday + timedelta(weeks=week_num - 1)
        week = orm_models.Week(
            mesocycle_id=mesocycle.id,
            week_number=week_num,
            start_date=week_start.strftime("%Y-%m-%d"),
            status="pending",
        )
        db.add(week)
        db.flush()

        focus_labels = _generate_weekly_focus(week_num, mesocycle.phase, day_count=len(preferred_days))

        for day_idx, dow in enumerate(preferred_days):
            day_date = week_start + timedelta(days=dow - 1)
            focus = focus_labels[day_idx] if day_idx < len(focus_labels) else ""
            day = orm_models.Day(
                week_id=week.id,
                day_order=day_idx + 1,
                day_of_week=dow,
                date=day_date.strftime("%Y-%m-%d"),
                day_label=focus,
                focus=focus,
                estimated_calories=0,
                is_completed=0,
            )
            db.add(day)

        db.flush()
        created_weeks.append(week)

        if event_queue:
            await event_queue.put(("progress", {
                "phase": "skeleton",
                "text": f"📅 创建第{week_num}周框架"
            }))

    return created_weeks


def _generate_weekly_focus(week_number: int, phase: str, day_count: int = 3) -> list[str]:
    """根据中周期阶段、周次和每周天数生成训练重点标签。

    Args:
        week_number: 当前周在中周期内的序号（1-based）
        phase: 中周期阶段名称
        day_count: 每周训练天数，决定返回的标签数量

    Returns:
        list[str]: 长度 = day_count 的标签列表
    """
    phase_focus_map = {
        "foundational": {
            1: ["全身激活", "全身耐力", "核心稳定"],
            2: ["全身力量基础", "核心强化", "全身协调"],
            3: ["上肢推动", "下肢拉动", "核心旋转"],
            4: ["综合测试", "耐力维持", "灵活提升"],
        },
        "hypertrophy": {
            1: ["推力（胸+肩+三头）", "拉力（背+二头）", "腿部+核心"],
            2: ["推拉结合", "腿部强化", "肩部+手臂"],
            3: ["复合推", "复合拉", "下肢爆发"],
            4: ["容量日", "密度日", "减载准备"],
        },
        "strength": {
            1: ["基础力量", "辅助训练", "核心稳定"],
            2: ["强度递增", "辅助提升", "爆发力"],
            3: ["最大力量", "专项辅助", "功率输出"],
            4: ["巅峰测试", "减量", "灵活恢复"],
        },
        "deload": {
            1: ["轻松活动", "拉伸恢复", "低强度有氧"],
            2: ["灵活性", "轻量维持", "恢复"],
            3: ["轻松活动", "拉伸恢复", "低强度有氧"],
            4: ["灵活性", "轻量维持", "恢复"],
        },
    }
    default_base = ["上肢", "下肢", "核心"]
    phase_map = phase_focus_map.get(phase, {})
    base_labels = phase_map.get(week_number, default_base)

    # 如果所需的标签数 <= 3，直接返回前 day_count 个
    if day_count <= 3:
        return base_labels[:day_count]

    # 如果 > 3，从补充池中取标签（按周次偏移，让每周不同）
    extra_pool = [
        "全身综合", "上肢补充", "下肢补充", "核心强化",
        "综合体能", "专项强化", "恢复拉伸",
    ]
    result = list(base_labels)
    for i in range(3, day_count):
        pool_idx = (i - 3 + week_number - 1) % len(extra_pool)
        result.append(extra_pool[pool_idx])
    return result
