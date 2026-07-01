"""Pydantic Schema — 周期化训练引擎 API 数据模型"""

from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
#  用户资料（保留原有）
# ═══════════════════════════════════════════════════════════════

class UserProfile(BaseModel):
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None
    experience: Optional[str] = None
    city: Optional[str] = None
    workout_location: Optional[str] = None
    days_per_week: Optional[int] = None

class UserProfileResponse(UserProfile):
    id: int
    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  大周期
# ═══════════════════════════════════════════════════════════════

class MacrocycleCreate(BaseModel):
    goal: str                          # 减脂/增肌/塑形/保持健康

class MacrocycleResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    goal: str
    start_date: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  用户当前状态
# ═══════════════════════════════════════════════════════════════

class UserCurrentStateUpdate(BaseModel):
    experience_level: Optional[str] = None       # 新手/中级/高级
    workout_location: Optional[str] = None       # 居家/健身房/户外
    days_per_week: Optional[int] = None
    preferred_days: Optional[str] = None         # "1,3,5"

class UserCurrentStateResponse(BaseModel):
    id: int
    user_id: int
    experience_level: str
    workout_location: str
    days_per_week: int
    preferred_days: str = "1,3,5"
    current_mesocycle_id: Optional[int] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  中周期
# ═══════════════════════════════════════════════════════════════

class MesocycleResponse(BaseModel):
    id: int
    macrocycle_id: int
    phase: str               # foundational / hypertrophy / strength / deload
    week_count: int = 4
    sort_order: int = 0
    status: str = "pending"

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  动作库
# ═══════════════════════════════════════════════════════════════

class ExerciseResponse(BaseModel):
    id: int
    wger_id: Optional[int] = None
    name: str
    target_muscle: str = ""
    muscle_group: str = ""
    movement_pattern: str = ""
    equipment: str = ""
    description: str = ""
    image_url: str = ""
    difficulty: int = 1

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  动作安排 + 打卡
# ═══════════════════════════════════════════════════════════════

class ExerciseSlotResponse(BaseModel):
    id: int
    day_id: int
    exercise_id: int
    phase_type: str = "main"
    sort_order: int = 0
    # 计划参数
    target_sets: int = 3
    target_reps: int = 12
    target_reps_max: int = 15
    weight_kg: float = 0.0
    weight_suggestion: str = ""
    rest_seconds: int = 60
    # 实际完成
    actual_sets: int = 0
    actual_reps: int = 0
    actual_weight_kg: float = 0.0
    rpe: int = 0
    notes: str = ""

    class Config:
        from_attributes = True

class ExerciseSlotCheckin(BaseModel):
    """打卡 — 更新某个动作的实际完成数据"""
    slot_id: int
    actual_sets: int
    actual_reps: int
    actual_weight_kg: float = 0.0
    rpe: int = 0
    notes: str = ""


# ═══════════════════════════════════════════════════════════════
#  训练日
# ═══════════════════════════════════════════════════════════════

class DayResponse(BaseModel):
    id: int
    week_id: int
    day_order: int
    day_of_week: int = 0
    date: str = ""                      # YYYY-MM-DD
    day_label: str = ""
    focus: str = ""
    estimated_calories: int = 0
    is_completed: int = 0
    completed_date: str = ""
    rpe_score: int = 0
    slots: List[ExerciseSlotResponse] = []

    class Config:
        from_attributes = True

class DayCheckin(BaseModel):
    """训练日整体打卡"""
    day_id: int
    is_completed: bool = True
    rpe_score: int = 0
    exercises: List[ExerciseSlotCheckin] = []


# ═══════════════════════════════════════════════════════════════
#  小周期（每周）
# ═══════════════════════════════════════════════════════════════

class WeekResponse(BaseModel):
    id: int
    mesocycle_id: int
    week_number: int
    start_date: str = ""                # YYYY-MM-DD
    status: str = "pending"
    generated_at: Optional[datetime] = None
    days: List[DayResponse] = []

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  完整中周期（含周/天/动作）
# ═══════════════════════════════════════════════════════════════

class MesocycleDetailResponse(MesocycleResponse):
    weeks: List[WeekResponse] = []


# ═══════════════════════════════════════════════════════════════
#  完整大周期（含中周期/周/天/动作）
# ═══════════════════════════════════════════════════════════════

class MacrocycleDetailResponse(MacrocycleResponse):
    mesocycles: List[MesocycleDetailResponse] = []


# ═══════════════════════════════════════════════════════════════
#  计划生成请求（首次初始化用）
# ═══════════════════════════════════════════════════════════════

class InitPlanRequest(BaseModel):
    goal: str                           # 减脂/增肌/塑形/保持健康
    experience_level: str               # 新手/中级/高级
    workout_location: str               # 居家/健身房/户外
    days_per_week: int = 3
    preferred_days: str = "1,3,5"       # 用户偏好的训练日
    start_date: Optional[str] = None    # YYYY-MM-DD（默认本周一）
    city: Optional[str] = None
    # 个人信息（用于个性化训练参数）
    height: Optional[float] = None      # cm
    weight: Optional[float] = None      # kg
    age: Optional[int] = None           # 岁
    gender: Optional[str] = None        # male / female

class RescheduleRequest(BaseModel):
    """调整训练日到新的 day_of_week"""
    day_of_week: int                    # 1=周一 … 7=周日

class NextWeekRequest(BaseModel):
    """手动触发生成下周"""
    pass


# ═══════════════════════════════════════════════════════════════
#  日历相关（新增）
# ═══════════════════════════════════════════════════════════════

class CalendarEntry(BaseModel):
    """日历网格轻量数据 — 一条表示某天"""
    date: str                           # YYYY-MM-DD
    has_plan: bool
    day_status: str = "pending"         # pending / completed / future / no_plan
    focus: str = ""                     # 训练主题（可选）
    mesocycle_phase: str = ""           # 所属中周期阶段（可选）

    class Config:
        from_attributes = True


class CalendarEntryResponse(BaseModel):
    """日历数据响应"""
    entries: List[CalendarEntry] = []


class DayDetailResponse(BaseModel):
    """单日详细数据"""
    date: str = ""
    day_status: str = "pending"         # pending / completed / future / no_plan
    day_label: str = ""
    focus: str = ""
    week_id: int = 0
    mesocycle_phase: str = ""
    is_rest_day: bool = False
    has_plan: bool = False
    slots: List[ExerciseSlotResponse] = []
    warmup: list = []
    main: list = []
    cardio: Optional[dict] = None
    stretch: list = []

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  大周期列表（摘要）
# ═══════════════════════════════════════════════════════════════

class MacrocycleSummary(BaseModel):
    id: int
    goal: str
    start_date: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════
#  变式链
# ═══════════════════════════════════════════════════════════════

class ExerciseVariationResponse(BaseModel):
    id: int
    series_name: str
    exercise_id: int
    sort_order: int

    class Config:
        from_attributes = True
