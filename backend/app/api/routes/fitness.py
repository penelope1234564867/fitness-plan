"""健身计划路由"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import orm_models, schemas
from app.services.plan_service import FitnessPlanService

router = APIRouter(prefix="/fitness", tags=["健身计划"])


@router.post("/generate")
async def generate_plan(request: schemas.PlanRequest, db: Session = Depends(get_db)):
    """生成训练计划（调用 5 个 Agent 协作生成）"""
    result = FitnessPlanService.generate_plan(request, db)
    return result


@router.get("/plans")
async def get_plans(db: Session = Depends(get_db)):
    """获取历史计划列表"""
    plans = db.query(orm_models.FitnessPlan).order_by(orm_models.FitnessPlan.id.desc()).all()
    return [
        {
            "id": p.id,
            "goal": p.goal,
            "duration_weeks": p.duration_weeks,
            "days_per_week": p.days_per_week,
            "created_at": str(p.created_at),
        }
        for p in plans
    ]


@router.get("/plan/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """获取单个计划详情"""
    plan = db.query(orm_models.FitnessPlan).filter(orm_models.FitnessPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    try:
        plan_content = json.loads(plan.plan_content) if plan.plan_content else {}
    except (json.JSONDecodeError, TypeError):
        plan_content = {}
    return {
        "id": plan.id,
        "goal": plan.goal,
        "experience_level": plan.experience_level,
        "workout_location": plan.workout_location,
        "days_per_week": plan.days_per_week,
        "duration_weeks": plan.duration_weeks,
        "diet_preference": plan.diet_preference,
        **plan_content,
        "created_at": str(plan.created_at),
    }
