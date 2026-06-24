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
