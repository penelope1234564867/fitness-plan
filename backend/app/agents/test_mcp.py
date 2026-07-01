"""快速测试 MCP 链路 — 直接调 Tool，不经过 Agent LLM 思考

使用方法:
  cd backend/
  python -m app.agents.test_mcp
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.agents.exercise_agent import WgerSearchTool, WgerListCategoriesTool, WgerListMusclesTool

ok = True

# 测试 1: 列分类
print("=" * 50)
print("测试 1: WgerListCategoriesTool")
print("=" * 50)
r = WgerListCategoriesTool().run({})
if r.status == "SUCCESS":
    data = json.loads(r.text)
    print(f"  OK! 分类: {', '.join(c['name'] for c in data)}")
else:
    print(f"  失败: {r.text}")
    ok = False

# 测试 2: 列肌群
print("\n" + "=" * 50)
print("测试 2: WgerListMusclesTool")
print("=" * 50)
r = WgerListMusclesTool().run({})
if r.status == "SUCCESS":
    data = json.loads(r.text)
    print(f"  OK! 肌群: {', '.join(m.get('name_en','') or m['name'] for m in data[:8])}...")
else:
    print(f"  失败: {r.text}")
    ok = False

# 测试 3: 搜动作
print("\n" + "=" * 50)
print("测试 3: WgerSearchTool (胸肌)")
print("=" * 50)
r = WgerSearchTool().run({"muscle": 4, "limit": 3})
if r.status == "SUCCESS":
    data = json.loads(r.text)
    exercises = data.get("exercises", [])
    print(f"  OK! 共 {data['total']} 个匹配，返回 {len(exercises)} 个:")
    for ex in exercises:
        print(f"    - {ex['name']} (肌群: {ex['target_muscle']})")
        print(f"      wger_id={ex['wger_id']}, 图片={'有' if ex.get('image_url') else '无'}")
else:
    print(f"  失败: {r.text}")
    ok = False

# 测试 4: 搜动作 (关键词)
print("\n" + "=" * 50)
print("测试 4: WgerSearchTool (关键词 bench press)")
print("=" * 50)
r = WgerSearchTool().run({"query": "bench press", "limit": 2})
if r.status == "SUCCESS":
    data = json.loads(r.text)
    exercises = data.get("exercises", [])
    print(f"  OK! 共 {data['total']} 个匹配，返回 {len(exercises)} 个:")
    for ex in exercises:
        print(f"    - {ex['name']} (肌群: {ex['target_muscle']})")
else:
    print(f"  失败: {r.text}")
    ok = False

print("\n" + "=" * 50)
if ok:
    print("全部测试通过! MCP 链路通畅 ✅")
    print("数据流: Tool → MCP Client → MCP Server → wger.de")
else:
    print("有测试失败")
print("=" * 50)
