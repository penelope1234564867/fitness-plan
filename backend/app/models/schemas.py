"""健身计划 Pydantic Schema 定义"""

from typing import List, Optional
from pydantic import BaseModel


# ── 用户资料 ──────────────────────────────────────────────

class UserProfile(BaseModel):
    height: Optional[float] = None       # cm
    weight: Optional[float] = None       # kg
    age: Optional[int] = None
    gender: Optional[str] = None         # male / female
    goal: Optional[str] = None           # 减脂/增肌/塑形/保持健康
    experience: Optional[str] = None     # 新手/中级/高级

class UserProfileResponse(UserProfile):
    id: int
    class Config:
        from_attributes = True


# ── 计划生成请求 ──────────────────────────────────────────

class PlanRequest(BaseModel):
    goal: str                            # 减脂/增肌/塑形/保持健康
    experience_level: str                # 新手/中级/高级
    workout_location: str                # 健身房/居家/户外
    days_per_week: int = 3
    duration_weeks: int = 4
    diet_preference: str = "普通"        # 普通/素食/高蛋白/低碳水
    city: Optional[str] = None           # 用于天气查询
    notes: Optional[str] = ""


# ── 训练动作 ──────────────────────────────────────────────

class ExerciseItem(BaseModel):
    name: str
    target_muscle: Optional[str] = ""
    category: Optional[str] = ""
    sets: int = 3
    reps: int = 12
    rest_seconds: int = 60
    weight_suggestion: Optional[str] = ""
    description: Optional[str] = ""
    image_url: Optional[str] = ""


# ── 每日训练 ──────────────────────────────────────────────

class DailyWorkout(BaseModel):
    day: str                             # 周一 / 周二 ...
    focus: str                           # 胸部/背部/腿部...
    warmup: List[ExerciseItem] = []
    main: List[ExerciseItem] = []
    cooldown: List[ExerciseItem] = []
    estimated_calories: Optional[int] = None


# ── 每周计划 ──────────────────────────────────────────────

class WeeklyPlan(BaseModel):
    week: int
    days: List[DailyWorkout] = []


# ── 饮食建议 ──────────────────────────────────────────────

class DietAdvice(BaseModel):
    daily_calories: Optional[int] = None
    protein_ratio: Optional[str] = ""
    carb_ratio: Optional[str] = ""
    fat_ratio: Optional[str] = ""
    meals: Optional[dict] = {}
    tips: List[str] = []


# ── 完整计划响应 ──────────────────────────────────────────

class FitnessPlanResponse(BaseModel):
    id: int
    goal: str
    experience_level: str
    workout_location: str
    days_per_week: int
    duration_weeks: int
    diet_preference: str
    weekly_plans: List[WeeklyPlan] = []
    diet: Optional[DietAdvice] = None

    class Config:
        from_attributes = True

class FitnessPlanSummary(BaseModel):
    id: int
    goal: str
    duration_weeks: int
    days_per_week: int
    created_at: str

    class Config:
        from_attributes = True


# ── 训练记录 ──────────────────────────────────────────────

class RecordRequest(BaseModel):
    plan_id: Optional[int] = None
    date: str                            # YYYY-MM-DD
    exercise_name: str
    target_muscle: Optional[str] = ""
    planned_sets: int = 0
    planned_reps: int = 0
    actual_sets: int
    actual_reps: int
    weight: float = 0.0
    difficulty: int = 3                  # 1-5
    notes: Optional[str] = ""

class RecordResponse(RecordRequest):
    id: int
    class Config:
        from_attributes = True
