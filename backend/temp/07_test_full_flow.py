"""测试7: 全流程（5 Agent 串行）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_API_KEY"] = "sk-f67e90469a0b4de9ab483196f6d5eb87"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"

from app.services.plan_service import FitnessPlanService
from app.models.schemas import PlanRequest
from app.database import SessionLocal, init_db
import json

print("=" * 50)
print("测试7: 全流程 5 Agent 串行")
print("=" * 50)

try:
    init_db()
    db = SessionLocal()
    req = PlanRequest(goal="减脂", experience_level="新手", workout_location="健身房", days_per_week=3, duration_weeks=4, diet_preference="普通", city="北京", notes="")
    result = FitnessPlanService.generate_plan(req, db)
    db.close()
    print(f"计划ID: {result.get('id')}  目标: {result.get('goal')}")
    print(f"周计划数: {len(result.get('weekly_plans', []))}")
    with open("temp/full_result.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("结果已保存 temp/full_result.json")
    print("✅ 全流程完成")
except Exception as e:
    import traceback
    print(f"❌ 全流程失败: {e}")
    traceback.print_exc()
