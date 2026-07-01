# Phase 6 工具映射表：打通 wger MCP Server 全链路

> 列出 Phase 6 的具体任务所需 Skills 和 MCP 工具。

---

## Phase 6：wger MCP Server 独立部署 + 全链路打通（Day 1-2）

> **状态：** 🔵 进行中（已完成 6.1-6.4，待完成 6.5-6.8）

| # | 任务 | Skills | MCP 工具 | 状态 |
|---|------|--------|----------|------|
| 6.1 | 创建 `wger-mcp-server/` 独立目录，从 `backend/app/mcp_servers/` 迁移 `wger_mcp_server.py` 到根目录 | — | `Filesystem`（mkdir / move / write 文件） | ✅ |
| 6.2 | **逐行教学**：拆解 MCP Server 代码，理解 FastMCP / @mcp.tool / JSON-RPC | — | `Filesystem`（read wger_mcp_server.py） | ✅ |
| 6.3 | **手动调试**：通过 stdio 发送 JSON-RPC 请求，验证 7 个工具返回正确 | `verify` | `VS Code IDE`（运行 python wger_mcp_server.py） | ✅ |
| 6.4 | **新建** `wger_mcp_client.py` — 自己写 MCP Client 桥接层（subprocess + JSON-RPC），因为 `hello_agents` 没有内置 MCPTool | — | `Filesystem`（write wger_mcp_client.py）<br>`VS Code IDE`（运行验证） | ✅ |
| 6.5 | **小改** `exercise_agent.py` — `WgerSearchTool` 里面调 `WgerMCPClient` 代替直接 REST | — | `Filesystem`（edit exercise_agent.py）<br>`VS Code IDE`（诊断语法错误） | ✅ |
| 6.6 | 更新 Agent Prompt 中工具调用说明 | — | `Filesystem`（edit exercise_agent.py 的 prompt） | ✅ |
| 6.7 | **清理**：删除旧 `wger_service.py` + 无用代码 | `simplify` | `Filesystem`（delete 文件） | 🔜 |
| 6.8 | **端到端验证**：全流程跑通，确认走的是 MCP 协议 | `verify` | `Playwright`（截图验收）<br>`VS Code IDE`（日志检查） | 🔜 |

**Phase 6 核心工具组合：** `Filesystem` + `VS Code IDE` + `Playwright`

---

## 架构决策：方案 B ✅ — MCP Server 独立部署

> **核心决定：** MCP Server 放在根目录独立文件夹，不藏在 `backend/` 下面。

### 目录结构

```
wger-mcp-server/              ← 独立 MCP 项目（简历亮点！）
├── wger_mcp_server.py        ← MCP Server，7 个工具（✅ 已迁移）
├── wger_mcp_client.py        ← MCP Client 桥接层（✅ 已新建）
├── requirements.txt          ← 依赖：mcp, httpx（✅ 已创建）
├── debug_test.py             ← 调试脚本（✅ 已验证通过）
└── README.md                 ← 独立说明（📋 待补充）

backend/                      ← 后端
├── app/
│   ├── agents/
│   │   ├── exercise_agent.py ← 🔜 小改：调 MCP Client 代替 REST
│   │   └── schedule_agent.py ← ⏭️ 不动（高德保持 ToolRegistry）
│   └── api/routes/
│       └── wger.py           ← 🔜 待清理
└── ...
```

### 为什么选方案 B？— 面试角度

| 维度 | 方案 A（藏在 backend/） | ✅ 方案 B（根目录独立） |
|:--|:--|:--|
| **第一印象** | 像个工具函数 | **像个完整项目** |
| **GitHub 展示** | 翻三层目录才找到 | **根目录直接看到，配 README** |
| **技术深度** | 「我调了 API」 | **「我实现了 MCP 协议标准」** |
| **可复用性** | 只能自己项目用 | **任何 AI 客户端即插即用** |
| **面试能讲多久** | 30 秒 | **3 分钟（协议、架构、跨框架）** |

### 各组件改动状态

| 文件 | 操作 | 状态 |
|:--|:--|:--|
| `wger-mcp-server/wger_mcp_client.py` | **新增** — MCP Client 桥接层 | ✅ 已完成 |
| `wger-mcp-server/wger_mcp_server.py` | **从 backend 搬过来** — 已改造为平铺参数 | ✅ 已完成 |
| `wger-mcp-server/requirements.txt` | **新增** — `mcp`, `httpx` | ✅ 已完成 |
| `backend/app/agents/exercise_agent.py` | **小改** — Tool 里调 Client 代替 REST | 🔜 进行中 |
| `backend/app/agents/schedule_agent.py` | **不动** — 高德保持 ToolRegistry | ⏭️ |
| `backend/app/services/wger_service.py` | **删除** — 被 MCP Server 替代 | 🔜 |
| `backend/app/api/routes/wger.py` | **删除** — 前端改走新接口 | 🔜 |

---

## 二、现状诊断

### 当前架构（已修复）

```
✅ wger-mcp-server/wger_mcp_server.py  ← 已迁到根目录，7 个工具，平铺参数
✅ wger-mcp-server/wger_mcp_client.py  ← 已新建，subprocess + JSON-RPC
✅ 手动调试已通过 — MCP 协议通信正常

待完成:
🔜 exercise_agent.py  → 改调 WgerMCPClient
🔜 删除 wger_service.py（旧代码）
🔜 端到端全流程验证
```

### 关键澄清

**高德天气也没有用 MCP。** 所有 Agent 工具原本都是「ToolRegistry + 直接 REST API」。
只有 wger 改成了 MCP，因为 7 个工具值得独立。高德 1 个工具保持不动。

### 目标架构（已实现到橙色部分）

```
AI Agent 层（计划生成时 — 用 MCP）:
  ExerciseAgent ──ToolRegistry──→ ✅ WgerMCPClient ──JSON-RPC──→ ✅ wger_mcp_server.py
                                                                    │
                                                               httpx → wger.de/api/v2

前端展示层（用户看详情时 — 用 REST）:
  浏览器 ──REST──→ 后端代理 ──httpx──→ wger.de/api/v2

高德天气（保持现状 — ToolRegistry + REST）:
  ScheduleAgent ──ToolRegistry──→ WeatherTool ──httpx──→ restapi.amap.com
```

---

## 三、MCP 基础知识

### 3.1 什么是 MCP？

**MCP = Model Context Protocol（模型上下文协议）** — AI 的「USB 接口标准」

### 3.2 MCP vs REST

```
不 MCP:  Agent → Tool → httpx.get(REST API)    ← 每个框架自己写一套
用 MCP:  Agent → Tool → MCP Client → JSON-RPC → MCP Server → httpx.get(REST API)
                                                   ↑ 标准协议，跨框架通用
```

### 3.3 MCP 通信流程

```
Step 1: MCP Client 自动启动子进程 → python wger_mcp_server.py
Step 2: Client 发 initialize → Server 回复版本、能力
Step 3: Client 发 tools/list → Server 返回 7 个工具的 schema
Step 4: Client 发 tools/call → Server 调 httpx → 返回结果
Step 5: Agent 拿到数据，整合到回答
```

### 3.4 为什么自己写 MCP Client？

`hello_agents` 没有内置 MCPTool，所以写了一个 `WgerMCPClient` 类：
- 自动启动子进程（`subprocess.Popen`）
- 发送 JSON-RPC 请求（`tools/list`, `tools/call`）
- 解析 Server 返回
- 自动关闭子进程

---

## 四、wger MCP Server 工具清单（7 个全保留）

| # | 工具名 | Agent 使用场景 |
|---|--------|---------------|
| 1 | `wger_list_categories` | 了解训练类别（Chest/Legs/Abs 等） |
| 2 | `wger_list_muscles` | 按肌群搜索前查 ID |
| 3 | `wger_list_equipment` | 按器材搜索前查 ID |
| 4 | `wger_search_exercises` | **核心**：按肌群+器材+关键词组合搜索 |
| 5 | `wger_get_exercise_details` | 选中动作后看完整描述/辅助肌群 |
| 6 | `wger_get_exercise_images` | 获取教学图片 URL |
| 7 | `wger_get_exercise_videos` | 获取演示视频 URL |

---

## 五、实施顺序（已完成 + 待完成）

```
✅ Step 6.1: 创建 wger-mcp-server/ 目录，迁移文件
✅ Step 6.2: 逐行教学 — 拆解 MCP Server 代码
✅ Step 6.3: 手动调试 — 验证 MCP Server stdio 通信
✅ Step 6.4: 新建 wger_mcp_client.py — MCP Client 桥接层
✅ Step 6.5: 小改 exercise_agent.py — 接 MCP Client
✅ Step 6.6: 更新 Agent Prompt
🔜 Step 6.7: 删除旧 wger_service.py 等遗留代码（保留 routes/wger.py 给前端用）
🔜 Step 6.8: 端到端验证全流程
```

---

## 六、简历亮点（方案 B 专属优势）

```
技术栈：Python FastMCP + JSON-RPC + subprocess + httpx + hello_agents

- ✅ 根目录独立 MCP 项目，不依赖后端框架，任何 MCP 客户端即插即用
- ✅ 基于 MCP 协议从零开发健身数据服务端，封装 7 个标准工具
- ✅ 自建 MCP Client 桥接层（subprocess + JSON-RPC over stdio）
- ✅ AI Agent 通过标准协议动态搜索 800+ 真实训练动作
- ✅ 面试可讲：MCP 协议设计、JSON-RPC 通信、子进程管理、跨框架标准
```

**面试话术对比：**
- 方案 A：「我调了 wger API 给 Agent 用」 ← 30 秒结束
- **方案 B：「我独立开发了一个 MCP Server，支持标准 MCP 协议，任何兼容 MCP 的 AI 客户端（Claude Desktop、VS Code 等）都可以即插即用。同时在我的项目里通过自写的 MCP Client 桥接层集成到了 Agent 系统中。」** ← 3 分钟技术深度展示
