"""测试4: ScheduleAgent（单 Agent 查天气 + 编排）"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["LLM_API_KEY"] = "sk-f67e90469a0b4de9ab483196f6d5eb87"
os.environ["LLM_BASE_URL"] = "https://api.deepseek.com"
os.environ["LLM_MODEL_ID"] = "deepseek-v4-flash"

from app.agents.schedule_agent import run_schedule_agent
import json

print("=" * 50)
print("测试4: ScheduleAgent")
print("=" * 50)

try:
    result = run_schedule_agent("减脂", "健身房", 3, "北京")
    print(f"  原始输出长度: {len(result)} 字符")
    print(f"  前300字符: {result[:300]}")
    try:
        data = json.loads(result)
        schedule = data.get("schedule", [])
        print(f"  JSON解析成功")
        print(f"  日程天数: {len(schedule)}")
        for s in schedule:
            print(f"    - {s.get('day')}: {s.get('focus')} @ {s.get('location')}")
    except json.JSONDecodeError:
        print("  原始输出不是标准JSON")
    print("✅ ScheduleAgent 执行完成")
except Exception as e:
    print(f"❌ ScheduleAgent 失败: {e}")
