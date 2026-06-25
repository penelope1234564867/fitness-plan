"""训练记录路由"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
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


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """获取训练统计概览"""
    total_records = db.query(func.count(orm_models.WorkoutRecord.id)).scalar() or 0

    total_sets = db.query(func.coalesce(func.sum(orm_models.WorkoutRecord.actual_sets), 0)).scalar() or 0
    total_reps = db.query(func.coalesce(func.sum(orm_models.WorkoutRecord.actual_reps), 0)).scalar() or 0

    # 不同训练天数
    days_result = db.query(func.count(func.distinct(orm_models.WorkoutRecord.date))).scalar() or 0

    # 平均难度
    avg_diff = db.query(func.avg(orm_models.WorkoutRecord.difficulty)).scalar() or 0

    # 按日期分组统计
    daily_counts = (
        db.query(
            orm_models.WorkoutRecord.date,
            func.count(orm_models.WorkoutRecord.id).label("count"),
        )
        .group_by(orm_models.WorkoutRecord.date)
        .order_by(orm_models.WorkoutRecord.date.desc())
        .limit(30)
        .all()
    )

    # 最近 7 天重量记录
    recent_weights = (
        db.query(
            orm_models.WorkoutRecord.date,
            orm_models.WorkoutRecord.exercise_name,
            orm_models.WorkoutRecord.weight,
            orm_models.WorkoutRecord.difficulty,
        )
        .filter(orm_models.WorkoutRecord.weight > 0)
        .order_by(orm_models.WorkoutRecord.date.desc())
        .limit(20)
        .all()
    )

    return {
        "total_records": total_records,
        "total_sets": total_sets,
        "total_reps": total_reps,
        "total_days": days_result,
        "avg_difficulty": round(float(avg_diff), 1),
        "daily_counts": [
            {"date": d.date, "count": d.count} for d in daily_counts
        ],
        "recent_weights": [
            {
                "date": w.date,
                "exercise_name": w.exercise_name,
                "weight": w.weight,
                "difficulty": w.difficulty,
            }
            for w in recent_weights
        ],
    }
