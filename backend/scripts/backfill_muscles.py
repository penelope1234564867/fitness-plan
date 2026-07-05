"""回填已有 exercise 的 primary_muscles / secondary_muscles。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models.orm_models import Exercise
from app.services.wger_service import get_exercise_detail
import json

db = SessionLocal()
exercises = db.query(Exercise).filter(Exercise.wger_id.isnot(None)).all()
print(f"共 {len(exercises)} 个待回填 exercise")

updated = 0
for ex in exercises:
    try:
        data = get_exercise_detail(ex.wger_id)
        if data.get("primary_muscles") or data.get("secondary_muscles"):
            ex.primary_muscles = data.get("primary_muscles", [])
            ex.secondary_muscles = data.get("secondary_muscles", [])
            updated += 1
            if updated % 5 == 0:
                print(f"  已回填 {updated}/{len(exercises)}")
    except Exception as e:
        print(f"  wger_id={ex.wger_id} 失败: {e}")

db.commit()
db.close()
print(f"回填完成: {updated}/{len(exercises)}")
