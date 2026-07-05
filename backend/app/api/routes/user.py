"""用户资料路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import orm_models, schemas

router = APIRouter(prefix="/user", tags=["用户资料"])


@router.post("/profile", response_model=schemas.UserProfileResponse)
async def create_or_update_profile(profile: schemas.UserProfile, db: Session = Depends(get_db)):
    user = db.query(orm_models.User).first()
    if user:
        for key, value in profile.model_dump(exclude_none=True).items():
            setattr(user, key, value)
    else:
        user = orm_models.User(**profile.model_dump(exclude_none=True))
        db.add(user)
    db.commit()
    return user


@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_profile(db: Session = Depends(get_db)):
    user = db.query(orm_models.User).first()
    if not user:
        return {"id": 0, "message": "未创建用户资料"}
    return user


@router.put("/profile-combined")
async def update_profile_combined(data: schemas.ProfileCombinedRequest,
                                   db: Session = Depends(get_db)):
    """合并保存用户个人信息 + 训练状态（一次请求更新两张表）"""
    # 1. 更新 User 表
    user = db.query(orm_models.User).first()
    if user:
        if data.height is not None:
            user.height = data.height
        if data.weight is not None:
            user.weight = data.weight
        if data.age is not None:
            user.age = data.age
        if data.gender is not None:
            user.gender = data.gender
        if data.goal is not None:
            user.goal = data.goal
    else:
        user = orm_models.User(
            height=data.height,
            weight=data.weight,
            age=data.age,
            gender=data.gender,
            goal=data.goal,
        )
        db.add(user)

    # 2. 更新 UserCurrentState 表
    ucs = db.query(orm_models.UserCurrentState).first()
    if ucs:
        if data.experience_level is not None:
            ucs.experience_level = data.experience_level
        if data.workout_location is not None:
            ucs.workout_location = data.workout_location
        if data.preferred_days is not None:
            ucs.preferred_days = data.preferred_days
        if data.days_per_week is not None:
            ucs.days_per_week = data.days_per_week
        elif data.preferred_days is not None:
            # 自动从 preferred_days 推算
            try:
                day_list = [int(d.strip()) for d in data.preferred_days.split(",") if d.strip()]
                ucs.days_per_week = len(day_list)
            except (ValueError, TypeError):
                pass
    else:
        computed_dpw = data.days_per_week
        if computed_dpw is None and data.preferred_days:
            try:
                day_list = [int(d.strip()) for d in data.preferred_days.split(",") if d.strip()]
                computed_dpw = len(day_list)
            except (ValueError, TypeError):
                computed_dpw = 3
        ucs = orm_models.UserCurrentState(
            experience_level=data.experience_level or "新手",
            workout_location=data.workout_location or "居家",
            preferred_days=data.preferred_days or "1,3,5",
            days_per_week=computed_dpw or 3,
        )
        db.add(ucs)

    # 3. 同时更新 User 表的 days_per_week
    if data.days_per_week is not None and user:
        user.days_per_week = data.days_per_week
    elif data.preferred_days is not None and user:
        try:
            day_list = [int(d.strip()) for d in data.preferred_days.split(",") if d.strip()]
            user.days_per_week = len(day_list)
        except (ValueError, TypeError):
            pass

    db.commit()
    return {"message": "保存成功"}
