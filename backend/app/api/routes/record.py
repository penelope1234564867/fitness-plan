"""训练记录路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import orm_models, schemas

router = APIRouter(prefix="/fitness", tags=["训练记录"])


@router.post("/record")
async def save_record(record: schemas.RecordRequest, db: Session = Depends(get_db)):
    """保存训练记录"""
    db_record = orm_models.WorkoutRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return {"id": db_record.id, "message": "记录已保存"}


@router.get("/records")
async def get_records(plan_id: int = None, db: Session = Depends(get_db)):
    """获取训练记录列表"""
    query = db.query(orm_models.WorkoutRecord)
    if plan_id:
        query = query.filter(orm_models.WorkoutRecord.plan_id == plan_id)
    records = query.order_by(orm_models.WorkoutRecord.date.desc()).all()
    return [
        {
            "id": r.id,
            "plan_id": r.plan_id,
            "date": r.date,
            "exercise_name": r.exercise_name,
            "actual_sets": r.actual_sets,
            "actual_reps": r.actual_reps,
            "weight": r.weight,
            "difficulty": r.difficulty,
        }
        for r in records
    ]
