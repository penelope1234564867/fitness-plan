"""MCP Server 调试脚本 — Windows 兼容版"""

import subprocess
import json
import sys
import time

# ── 启动 MCP Server 子进程 ──────────────────────────────────
print("=" * 50)
print("Step 1: 启动 MCP Server 子进程...")
print("=" * 50)

process = subprocess.Popen(
    [sys.executable, "wger_mcp_server.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=".",
    # Windows 需要这些参数
    bufsize=0,
)

time.sleep(1)

# 检查进程是否还活着
if process.poll() is not None:
    print("[ERROR] MCP Server 启动后立即退出了！")
    stderr_output = process.stderr.read().decode("utf-8", errors="replace")
    print("[STDERR]", stderr_output[:1000])
    sys.exit(1)

print("[OK] MCP Server 子进程已启动 (PID: %d)\n" % process.pid)


# ── 发请求的工具函数 ─────────────────────────────────────────
def send_request(method: str, params: dict = None) -> dict:
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }
    request_bytes = (json.dumps(request) + "\n").encode("utf-8")
    print("[SEND]", request_bytes.decode("utf-8").strip())

    # Windows 需要二进制写入
    process.stdin.write(request_bytes)
    process.stdin.flush()

    # 读响应（按 jsonrpc 格式，读到完整一行）
    response_bytes = process.stdout.readline()
    response = json.loads(response_bytes.decode("utf-8"))
    print("[RECV]", json.dumps(response, indent=2, ensure_ascii=False)[:800])
    print()
    return response


# ── Step 2: 初始化 ──────────────────────────────────────────
print("=" * 50)
print("Step 2: 发 initialize 请求")
print("=" * 50)
send_request("initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "debug-test", "version": "1.0"},
})

# ── Step 3: 通知初始化完成 ──────────────────────────────────
print("=" * 50)
print("Step 2.5: 发 notifications/initialized")
print("=" * 50)
init_notification = json.dumps({
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
    "params": {},
}) + "\n"
process.stdin.write(init_notification.encode())
process.stdin.flush()
# 通知没有响应，直接继续
print("[OK] 通知已发送\n")

# ── Step 4: 列出所有工具 ────────────────────────────────────
print("=" * 50)
print("Step 3: 发 tools/list — 看 Server 暴露了哪些工具")
print("=" * 50)
resp = send_request("tools/list")

tools = resp.get("result", {}).get("tools", [])
print("[LIST] Server 暴露了 %d 个工具:" % len(tools))
for t in tools:
    desc = t.get("description", "")
    print("   Tool: %s — %s..." % (t["name"], desc[:60]))

# ── Step 5: 调用一个工具 ────────────────────────────────────
print("\n" + "=" * 50)
print("Step 4: 发 tools/call — 调用 wger_list_categories")
print("=" * 50)
send_request("tools/call", {
    "name": "wger_list_categories",
    "arguments": {},
})

# ── 关进程 ───────────────────────────────────────────────────
process.terminate()
process.wait()
print("=" * 50)
print("调试完成")
print("=" * 50)
