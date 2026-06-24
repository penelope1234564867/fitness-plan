"""ORM 数据库模型"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from app.database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    height = Column(Float)
    weight = Column(Float)
    age = Column(Integer)
    gender = Column(String(10))
    goal = Column(String(50))        # 减脂/增肌/塑形/保持健康
    experience = Column(String(20))  # 新手/中级/高级
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FitnessPlan(Base):
    __tablename__ = "fitness_plan"

    id = Column(Integer, primary_key=True, index=True)
    goal = Column(String(50))
    experience_level = Column(String(20))
    workout_location = Column(String(20))   # 健身房/居家/户外
    days_per_week = Column(Integer)
    duration_weeks = Column(Integer)
    diet_preference = Column(String(20))    # 普通/素食/高蛋白/低碳水
    notes = Column(Text, default="")
    plan_content = Column(Text)             # JSON 字符串
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkoutRecord(Base):
    __tablename__ = "workout_record"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("fitness_plan.id"), nullable=True)
    date = Column(String(20))               # YYYY-MM-DD
    exercise_name = Column(String(100))
    target_muscle = Column(String(50), default="")
    planned_sets = Column(Integer, default=0)
    planned_reps = Column(Integer, default=0)
    actual_sets = Column(Integer, default=0)
    actual_reps = Column(Integer, default=0)
    weight = Column(Float, default=0.0)     # kg
    difficulty = Column(Integer, default=3) # 1-5
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
