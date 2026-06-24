"""测试2: ExerciseAgent（单 Agent 调用 Wger API + LLM）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_API_KEY"] = "sk-f67e90469a0b4de9ab483196f6d5eb87"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"

from app.agents.exercise_agent import run_exercise_agent
import json

print("=" * 50)
print("测试2: ExerciseAgent")
print("=" * 50)

try:
    result = run_exercise_agent("增肌", "中级", "健身房", 3)
    print(f"  原始输出长度: {len(result)} 字符")
    print(f"  前200字符: {result[:200]}")

    try:
        data = json.loads(result)
        print(f"  JSON解析成功，共 {len(data)} 个动作")
        for item in data[:3]:
            has_img = "✅" if item.get("image_url") else "❌"
            print(f"    - {item.get('name')} | {item.get('sets')}x{item.get('reps')} | 图片{has_img}")
    except json.JSONDecodeError:
        print("  原始输出不是标准JSON")

    print("✅ ExerciseAgent 执行完成")
except Exception as e:
    print(f"❌ ExerciseAgent 失败: {e}")
