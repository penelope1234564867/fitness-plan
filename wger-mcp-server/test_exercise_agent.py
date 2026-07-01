"""验证 exercise_agent.py 能否通过 MCP 协议拿到 wger 数据。

这个脚本直接调 exercise_agent 内部的 Tool 类，不启动整个后端。
"""

import sys
from pathlib import Path

# 添加 backend 到系统路径，让 import 能找到 app.*
backend_path = str(Path(__file__).parents[1] / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# 加载 .env（如果有）
from dotenv import load_dotenv
load_dotenv()

# ── 测试 1：验证 MCP Client 导入和连接 ────────────────────
print("=" * 50)
print("测试 1: 验证 MCP Client 导入")
print("=" * 50)

# 先手动添加 wger-mcp-server 到路径
_wger_mcp_path = str(Path(__file__).parent)
if _wger_mcp_path not in sys.path:
    sys.path.insert(0, _wger_mcp_path)

from wger_mcp_client import WgerMCPClient
print("[OK] MCP Client 导入成功")

client = WgerMCPClient()
tools = client.list_tools()
print(f"[OK] MCP Server 已连接，暴露 {len(tools)} 个工具")

# ── 测试 2：直接调 Tool 类 ────────────────────────────────
print("\n" + "=" * 50)
print("测试 2: 直接调 WgerSearchTool")
print("=" * 50)

from app.agents.exercise_agent import WgerSearchTool

tool = WgerSearchTool()
result = tool.run({"query": "bench press", "limit": 2})
print(f"状态: {result.status}")
print(f"返回数据前 200 字符: {result.text[:200]}")

# ── 测试 3：调 WgerListCategoriesTool ─────────────────────
print("\n" + "=" * 50)
print("测试 3: 调 WgerListCategoriesTool")
print("=" * 50)

from app.agents.exercise_agent import WgerListCategoriesTool

tool2 = WgerListCategoriesTool()
result2 = tool2.run({})
print(f"状态: {result2.status}")
print(f"返回数据: {result2.text[:200]}")

# ── 测试 4：完整创建 Agent ────────────────────────────────
print("\n" + "=" * 50)
print("测试 4: 创建 ExerciseAgent 实例")
print("=" * 50)

from app.agents.exercise_agent import create_exercise_agent

agent = create_exercise_agent()
print(f"[OK] Agent 创建成功: {agent.name}")
print(f"[OK] Agent 工具有: {[t.name for t in agent.tool_registry.list_tools()]}")

# ── 清理 ──────────────────────────────────────────────────
client.close()
print("\n" + "=" * 50)
print("全部测试通过! ✅")
print("=" * 50)
