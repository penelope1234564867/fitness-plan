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
    db.refresh(user)
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
    else:
        ucs = orm_models.UserCurrentState(
            experience_level=data.experience_level or "新手",
            workout_location=data.workout_location or "居家",
            preferred_days=data.preferred_days or "1,3,5",
        )
        db.add(ucs)

    db.commit()
    return {"message": "保存成功"}
