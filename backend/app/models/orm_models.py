"""ORM 数据库模型 — 周期化训练引擎三层体系

Schema:
  user
   ├── macrocycle (大周期：只存目标)
   │    └── mesocycle (中周期：4周一阶段)
   │         └── week (小周期：每周)
   │              └── day (训练日)
   │                   └── exercise_slot (动作安排 + 打卡数据)
   │
   ├── user_current_state (动态配置)
   │
   exercise (动作库)
    └── exercise_variation (升降阶变式链)

遗留表（过渡用，不再写入）:
  - fitness_plan
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


# ═══════════════════════════════════════════════════════════════
#  用户
# ═══════════════════════════════════════════════════════════════

class User(Base):
    """用户信息。"""
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    height = Column(Float)
    weight = Column(Float)
    age = Column(Integer)
    gender = Column(String(10))
    goal = Column(String(50))               # 减脂/增肌/塑形/保持健康
    experience = Column(String(20))         # 新手/中级/高级
    city = Column(String(50), default="")
    workout_location = Column(String(20), default="")
    days_per_week = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    macrocycles = relationship("Macrocycle", back_populates="user", lazy="dynamic")


# ═══════════════════════════════════════════════════════════════
#  大周期（Macrocycle）
# ═══════════════════════════════════════════════════════════════

class Macrocycle(Base):
    """大周期。只定义长期目标，不做过多约束。
    训练经验、地点、每周天数等可变参数放在 UserCurrentState 中动态管理。"""
    __tablename__ = "macrocycle"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    goal = Column(String(50))               # 减脂/增肌/塑形/保持健康
    start_date = Column(String(20))         # YYYY-MM-DD
    status = Column(String(20), default="active")  # active / completed / paused
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="macrocycles")
    mesocycles = relationship("Mesocycle", back_populates="macrocycle",
                              order_by="Mesocycle.sort_order",
                              cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════
#  用户当前状态（User Current State）
# ═══════════════════════════════════════════════════════════════

class UserCurrentState(Base):
    """用户当前状态 — 动态配置，随时可改。
    修改后影响下周生成，不回溯历史计划。"""
    __tablename__ = "user_current_state"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)  # 单用户场景，非强制 FK
    experience_level = Column(String(20), default="新手")      # 新手/中级/高级
    workout_location = Column(String(20), default="居家")      # 居家/健身房/户外
    days_per_week = Column(Integer, default=3)
    preferred_days = Column(String(20), default="1,3,5")  # 用户偏好的训练日，如 "1,3,5"
    current_mesocycle_id = Column(Integer,
                                  ForeignKey("mesocycle.id", ondelete="SET NULL"),
                                  nullable=True)              # 当前所在的 mesocycle
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系 — 单用户场景，不强制 FK 关联 User 表


# ═══════════════════════════════════════════════════════════════
#  中周期（Mesocycle） — 4 周一阶段
# ═══════════════════════════════════════════════════════════════

class Mesocycle(Base):
    """中周期阶段。4 周一个阶段：基础适应期 → 肌肥大期 → 力量期 → 减载。"""
    __tablename__ = "mesocycle"

    id = Column(Integer, primary_key=True, index=True)
    macrocycle_id = Column(Integer, ForeignKey("macrocycle.id", ondelete="CASCADE"),
                           nullable=False)
    phase = Column(String(20), nullable=False)     # foundational / hypertrophy / strength / deload
    week_count = Column(Integer, default=4)        # 持续周数
    sort_order = Column(Integer, default=0)        # 第几个中周期
    status = Column(String(20), default="pending") # active / completed / pending

    # 关系
    macrocycle = relationship("Macrocycle", back_populates="mesocycles")
    weeks = relationship("Week", back_populates="mesocycle",
                         order_by="Week.week_number",
                         cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════
#  小周期（Week）— 每周
# ═══════════════════════════════════════════════════════════════

class Week(Base):
    """小周期 — 一周的训练计划。每周动态生成。"""
    __tablename__ = "week"

    id = Column(Integer, primary_key=True, index=True)
    mesocycle_id = Column(Integer, ForeignKey("mesocycle.id", ondelete="CASCADE"),
                          nullable=False)
    week_number = Column(Integer, nullable=False)  # 在中周期内的第几周（1-4）
    start_date = Column(String(10), default="")     # YYYY-MM-DD，本周一的日期
    status = Column(String(20), default="pending") # pending / active / completed / skipped
    generated_at = Column(DateTime, default=datetime.utcnow)  # 该周何时被生成

    # 关系
    mesocycle = relationship("Mesocycle", back_populates="weeks")
    days = relationship("Day", back_populates="week",
                        order_by="Day.day_order",
                        cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("mesocycle_id", "week_number", name="uq_mesocycle_week"),
    )


# ═══════════════════════════════════════════════════════════════
#  训练日（Day）
# ═══════════════════════════════════════════════════════════════

class Day(Base):
    """某周中的一天训练。默认排好日期，用户可自由调整。"""
    __tablename__ = "day"

    id = Column(Integer, primary_key=True, index=True)
    week_id = Column(Integer, ForeignKey("week.id", ondelete="CASCADE"),
                     nullable=False)
    day_order = Column(Integer, nullable=False)    # 1=第一个训练日, 2=第二个...
    day_of_week = Column(Integer, default=0)       # 1=周一 … 7=周日（新增，用户可调整）
    date = Column(String(10), default="")           # YYYY-MM-DD，具体训练日期
    day_label = Column(String(30), default="")     # "推" / "拉" / "腿"
    focus = Column(String(100), default="")        # "胸部+肩部+三头"
    estimated_calories = Column(Integer, default=0)
    is_completed = Column(Integer, default=0)
    completed_date = Column(String(20), default="")  # YYYY-MM-DD 实际完成日期
    rpe_score = Column(Integer, default=0)         # 当天整体难度评价

    # 关系
    week = relationship("Week", back_populates="days")
    slots = relationship("ExerciseSlot", back_populates="day",
                         order_by="ExerciseSlot.sort_order",
                         cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("week_id", "day_order", name="uq_week_day"),
    )


# ═══════════════════════════════════════════════════════════════
#  动作安排（ExerciseSlot）— 计划 + 打卡二合一
# ═══════════════════════════════════════════════════════════════

class ExerciseSlot(Base):
    """某天训练中的一个动作。
    包含计划参数（target_*）和实际完成数据（actual_*）。
    用户打卡时直接更新 actual_* 字段。"""
    __tablename__ = "exercise_slot"

    id = Column(Integer, primary_key=True, index=True)
    day_id = Column(Integer, ForeignKey("day.id", ondelete="CASCADE"),
                    nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercise.id"), nullable=True)  # warmup/cardio/stretch 用
    wger_id = Column(Integer, nullable=True)                                 # 主项动作直接用 wger_id
    exercise_name = Column(String(200), default="")                          # 显示用（前端不必再查 wger）
    phase_type = Column(String(10), default="main")    # warmup / main / cardio / stretch
    sort_order = Column(Integer, default=0)

    # ── 计划参数（生成时写入）──
    target_sets = Column(Integer, default=3)
    target_reps = Column(Integer, default=12)
    target_reps_max = Column(Integer, default=15)      # 双渐进次数范围上限
    weight_kg = Column(Float, default=0.0)             # 数字重量，给引擎算渐进用
    weight_suggestion = Column(String(50), default="") # 文字展示，如"自重" / "弹力带中等阻力"
    rest_seconds = Column(Integer, default=60)

    # ── 实际完成数据（打卡时写入）──
    actual_sets = Column(Integer, default=0)
    actual_reps = Column(Integer, default=0)
    actual_weight_kg = Column(Float, default=0.0)
    rpe = Column(Integer, default=0)                   # 该动作难度 1-10
    notes = Column(Text, default="")

    # 关系
    day = relationship("Day", back_populates="slots")
    exercise = relationship("Exercise")

    __table_args__ = (
        Index("idx_slot_day_phase", "day_id", "phase_type"),
    )


# ═══════════════════════════════════════════════════════════════
#  动作库（Exercise）— 独立计划存在
# ═══════════════════════════════════════════════════════════════

class Exercise(Base):
    """动作库。独立于任何训练计划。
    懒加载缓存：用到时从 wger 拉取，存本地后复用。"""
    __tablename__ = "exercise"

    id = Column(Integer, primary_key=True, index=True)
    wger_id = Column(Integer, unique=True, nullable=True)  # wger 平台 ID
    name = Column(String(100), nullable=False, index=True)
    name_en = Column(String(100), default="")
    target_muscle = Column(String(50), default="")         # 具体肌肉，如"股四头肌"
    target_muscle_en = Column(String(50), default="")
    muscle_group = Column(String(30), default="")          # 肌肉群：chest/back/legs/shoulders/arms/core
    movement_pattern = Column(String(30), default="")      # 动作模式：push/pull/squat/hinge/carry/core
    category = Column(String(30), default="")              # strength / cardio / stretching
    equipment = Column(String(50), default="")             # bodyweight / dumbbell / barbell / band
    description = Column(Text, default="")
    image_url = Column(String(500), default="")
    difficulty = Column(Integer, default=1)                # 1-5
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    slots = relationship("ExerciseSlot", back_populates="exercise")
    variations = relationship("ExerciseVariation", back_populates="exercise")


# ═══════════════════════════════════════════════════════════════
#  变式链（ExerciseVariation）— 升降阶路径
# ═══════════════════════════════════════════════════════════════

class ExerciseVariation(Base):
    """动作变式链。同一系列按难度排序。
    例子：俯卧撑系列: 跪姿(1) → 标准(2) → 宽距(3) → 钻石(4) → 负重(5)
    sort_order: 1=最简单, 5=最难"""
    __tablename__ = "exercise_variation"

    id = Column(Integer, primary_key=True, index=True)
    series_name = Column(String(100), nullable=False, index=True)  # 如"俯卧撑系列"
    exercise_id = Column(Integer, ForeignKey("exercise.id"),
                         nullable=False)
    sort_order = Column(Integer, nullable=False)  # 难度排序，从易到难

    # 关系
    exercise = relationship("Exercise", back_populates="variations")

    __table_args__ = (
        UniqueConstraint("series_name", "exercise_id", name="uq_variation_series_exercise"),
        Index("idx_variation_series_order", "series_name", "sort_order"),
    )


# ═══════════════════════════════════════════════════════════════
#  遗留表（过渡用 — 已有数据迁移前保留，不再写入）
# ═══════════════════════════════════════════════════════════════

class FitnessPlan(Base):
    """（遗留）旧版训练计划。使用新引擎后不再写入。
    plan_content 列将在数据迁移完成后移除。"""
    __tablename__ = "fitness_plan"

    id = Column(Integer, primary_key=True, index=True)
    goal = Column(String(50))
    experience_level = Column(String(20))
    workout_location = Column(String(20))
    days_per_week = Column(Integer)
    duration_weeks = Column(Integer)
    notes = Column(Text, default="")
    plan_content = Column(Text)             # 旧版 JSON 字符串
    created_at = Column(DateTime, default=datetime.utcnow)
