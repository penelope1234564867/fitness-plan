"""测试5: TrainerAgent（汇总子结果）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_API_KEY"] = "sk-f67e90469a0b4de9ab483196f6d5eb87"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"

from app.agents.trainer_agent import run_trainer_agent
import json

print("=" * 50)
print("测试5: TrainerAgent")
print("=" * 50)

try:
    mock_exercises = json.dumps([{"name":"卧推","target_muscle":"胸部","sets":4,"reps":10,"rest_seconds":60,"image_url":"https://wger.de/test.png"},{"name":"划船","target_muscle":"背部","sets":4,"reps":10,"rest_seconds":60,"image_url":""},{"name":"深蹲","target_muscle":"腿部","sets":4,"reps":10,"rest_seconds":90,"image_url":""}], ensure_ascii=False)
    mock_diet = json.dumps({"daily_calories":2000,"protein_ratio":"30%","carb_ratio":"50%","fat_ratio":"20%","meals":{"breakfast":{"time":"08:00","foods":["鸡蛋","面包"],"calories":500}},"tips":["多喝水"]}, ensure_ascii=False)
    mock_schedule = json.dumps({"schedule":[{"day":"周一","focus":"胸部","location":"健身房","workout_type":"力量"},{"day":"周二","focus":"背部","location":"健身房","workout_type":"力量"},{"day":"周四","focus":"腿部","location":"健身房","workout_type":"力量"}],"weather_summary":"良好"}, ensure_ascii=False)

    result = run_trainer_agent("目标：增肌\n经验：中级", mock_exercises, mock_diet, mock_schedule)
    print(f"  输出长度: {len(result)} 字符")
    print(f"  前300字: {result[:300]}")
    try:
        data = json.loads(result)
        print(f"  JSON解析成功, {len(data.get('weekly_plans',[]))}周")
    except json.JSONDecodeError:
        print("  非标准JSON")
    print("✅ TrainerAgent 执行完成")
except Exception as e:
    print(f"❌ TrainerAgent 失败: {e}")
