"""测试6: PlanReviewAgent（自我审查修正）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_API_KEY"] = "sk-f67e90469a0b4de9ab483196f6d5eb87"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"

from app.agents.plan_review_agent import run_plan_review
import json

print("=" * 50)
print("测试6: PlanReviewAgent")
print("=" * 50)

try:
    test_plan = json.dumps({"weekly_plans":[{"week":1,"days":[{"day":"周一","focus":"胸部","warmup":[],"main":[{"name":"卧推","target_muscle":"胸部","sets":3,"reps":12,"image_url":""}],"cooldown":[]},{"day":"周二","focus":"胸部","warmup":[],"main":[{"name":"飞鸟","target_muscle":"胸部","sets":3,"reps":12,"image_url":""}],"cooldown":[]}]}],"diet":{"daily_calories":1800,"meals":{},"tips":[]}}, ensure_ascii=False)

    result = run_plan_review(test_plan)
    print(f"  输出长度: {len(result)} 字符")
    print(f"  前500字: {result[:500]}")
    print("✅ PlanReviewAgent 执行完成")
except Exception as e:
    print(f"❌ PlanReviewAgent 失败: {e}")
