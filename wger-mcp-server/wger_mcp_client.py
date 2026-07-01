"""MCP Client 桥接层 — 管理 MCP Server 子进程 + JSON-RPC 通信

因为 hello_agents 没有内置 MCPTool，所以自己写一个。
用法:
    client = WgerMCPClient()
    result = client.call_tool("wger_list_categories", {})
    client.close()
"""

import subprocess
import json
import sys
import time
from pathlib import Path
from typing import Optional


class WgerMCPClient:
    """MCP Client 桥接层。

    管理 MCP Server 子进程生命周期，通过 stdio 发送 JSON-RPC 请求。
    """

    def __init__(self, server_path: Optional[str] = None):
        """启动 MCP Server 子进程并完成初始化握手。

        Args:
            server_path: wger_mcp_server.py 的路径。
                        默认为本文件同级目录下的 wger_mcp_server.py。
        """
        # 确定 Server 路径
        if server_path is None:
            server_path = str(Path(__file__).parent / "wger_mcp_server.py")

        # ── 启动子进程 ──
        self.process = subprocess.Popen(
            [sys.executable, server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        # 等进程启动
        time.sleep(0.5)

        # 检查进程是否还活着
        if self.process.poll() is not None:
            stderr = self.process.stderr.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"MCP Server 启动失败!\nSTDERR: {stderr[:500]}"
            )

        self._req_id = 0

        # ── 初始化握手 ──
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "wger-mcp-client", "version": "1.0"},
        })
        self._send_notification("notifications/initialized")

    # ── 内部方法 ─────────────────────────────────────────────

    def _send_request(self, method: str, params: dict) -> dict:
        """发送 JSON-RPC 请求并等待响应。"""
        self._req_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._req_id,
        }
        self.process.stdin.write((json.dumps(request) + "\n").encode("utf-8"))
        self.process.stdin.flush()

        response_bytes = self.process.stdout.readline()
        return json.loads(response_bytes.decode("utf-8"))

    def _send_notification(self, method: str):
        """发送 JSON-RPC 通知（不需要响应）。"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": {},
        }
        self.process.stdin.write((json.dumps(notification) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    # ── 公开方法 ─────────────────────────────────────────────

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """调用 MCP Server 上的工具。

        Args:
            tool_name: 工具名，如 "wger_search_exercises"
            arguments: 参数字典，如 {"muscle": 4, "limit": 10}

        Returns:
            str: 工具返回的文本内容（JSON 字符串）

        Raises:
            RuntimeError: 工具调用失败
        """
        response = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        if "error" in response:
            error = response["error"]
            raise RuntimeError(f"MCP 工具调用失败: {error.get('message', str(error))}")

        result = response.get("result", {})
        if result.get("isError"):
            raise RuntimeError(f"工具执行错误: {result.get('content', [{}])[0].get('text', '')}")

        # 提取文本内容
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                return item["text"]

        # fallback: 返回结构化内容
        structured = result.get("structuredContent", {})
        if structured:
            return json.dumps(structured)

        return json.dumps(result)

    def list_tools(self) -> list:
        """列出 Server 上所有可用的工具。"""
        response = self._send_request("tools/list", {})
        tools = response.get("result", {}).get("tools", [])
        return tools

    def close(self):
        """关闭 MCP Server 子进程。"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ── 独立测试 ────────────────────────────────────────────────

if __name__ == "__main__":
    print("测试 WgerMCPClient...")
    client = WgerMCPClient()

    # 测试 1: 列出工具
    tools = client.list_tools()
    print(f"\n[OK] Server 暴露了 {len(tools)} 个工具:")
    for t in tools:
        print(f"  - {t['name']}")

    # 测试 2: 调用 list_categories
    result = client.call_tool("wger_list_categories", {})
    print(f"\n[OK] list_categories 返回: {result[:200]}...")

    # 测试 3: 搜索动作
    result = client.call_tool("wger_search_exercises", {
        "query": "bench press",
        "limit": 2,
    })
    print(f"\n[OK] search_exercises 返回: {result[:200]}...")

    client.close()
    print("\n所有测试通过! ✅")
