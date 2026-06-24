"""测试3: DietAgent（单 Agent 纯 LLM）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_API_KEY"] = "sk-f67e90469a0b4de9ab483196f6d5eb87"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"

from app.agents.diet_agent import run_diet_agent
import json

print("=" * 50)
print("测试3: DietAgent")
print("=" * 50)

try:
    result = run_diet_agent("减脂", "普通")
    print(f"  原始输出长度: {len(result)} 字符")
    print(f"  前300字符: {result[:300]}")
    try:
        data = json.loads(result)
        print(f"  JSON解析成功")
        print(f"  每日热量: {data.get('daily_calories')}")
        print(f"  三餐数: {len(data.get('meals', {}))}")
        print(f"  建议条数: {len(data.get('tips', []))}")
    except json.JSONDecodeError:
        print("  原始输出不是标准JSON")
    print("✅ DietAgent 执行完成")
except Exception as e:
    print(f"❌ DietAgent 失败: {e}")
