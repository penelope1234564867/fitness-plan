# Wger MCP Server 实现文档

> 本文档记录了自建 Wger MCP Server 的完整实现过程，包括问题分析、方案选型、具体步骤和最终功能清单。

---

## 一、背景与问题分析

### 1.1 项目需求

Fitness Planner 的 ExerciseAgent 需要从 wger 平台获取真实的训练动作数据，包括：

- 按肌群/器材/关键词搜索动作
- 动作的名称、描述、目标肌群
- 训练教学图片和演示视频
- 分类、器材等筛选条件

### 1.2 社区 MCP Server 的问题

最初计划使用社区维护的 `@juxsta/wger-mcp`，但通过 MCP 工具测试发现两个阻塞性 bug：

---

**Bug 1：`search_exercises` 类型校验失败**

测试命令：
```
search_exercises(query="bench press", limit=5)
```

报错信息：
```json
[
  {
    "code": "invalid_type",
    "expected": "number",
    "received": "undefined",
    "path": ["results", 0, "variations"]
  }
]
```

**根因分析：**

通过浏览器直接访问 wger API 对比真实数据：

```json
// wger API 实际返回（exerciseinfo 端点）
{
  "id": 9,
  "variation_group": "a30b1f92-7b73-477e-abb0-e91993c5fb05"
  // ↑ 字段名是 variation_group，类型是 UUID 字符串
}

// 社区 MCP Server schema 要求
{
  "variations": 123  // ↑ 字段名是 variations，类型是 number
}
```

wger API 返回的是 `variation_group`（UUID v4 字符串），但社区 MCP 的 TypeScript Zod schema 写的是 `variations`（number 类型），导致 Zod 校验拦截了全部响应。

---

**Bug 2：`get_exercise_details` 找不到动作**

对任意 ID 调用均返回 "not found"。同样是因为内部 schema 校验失败，导致请求无法到达 wger API 层。

---

### 1.3 选型决策

| 方案 | 说明 | 选型结果 |
|------|------|---------|
| A. Fork 修 bug | Fork 社区仓库，改 schema 字段名 | 淘汰。项目多一套 TypeScript + Node 依赖 |
| B. 自建 Python MCP Server | 从零实现，只暴露本项目需要的工具 | ✅ **选中** |
| C. 直接调 REST API | 不用 MCP，Agent 直接 HTTP 调用 | 淘汰。少了 MCP 协议这个简历亮点 |

**决策理由：**
1. 项目后端是 Python FastAPI，自建 Python MCP Server 不需要额外运行时
2. 可以按本项目需求精确裁剪暴露的工具
3. 可以自行处理 wger API 的字段映射，不受第三方库限制
4. 简历叙事：从"修了别人的 bug"变成"从零实现了 MCP Server"

---

## 二、实现步骤

### 第 1 步：分析 wger REST API 数据结构

**工具：** Playwright 浏览器 + wger API 文档

通过浏览器直接访问 wger API，确认以下端点的数据格式：

| 端点 | 用途 | 关键发现 |
|------|------|---------|
| `GET /api/v2/exerciseinfo/` | 搜索动作（含详情） | 字段名为 `variation_group`，不是 `variations` |
| `GET /api/v2/exerciseimage/` | 教学图片 | 共 360 张，PNG 格式，含缩略图 |
| `GET /api/v2/video/` | 演示视频 | 共 78 个，MOV 格式，1080p/4K |
| `GET /api/v2/muscle/` | 肌群列表 | 15 个肌群，含 SVG 解剖图 URL |
| `GET /api/v2/exercisecategory/` | 分类列表 | 8 个分类 |
| `GET /api/v2/equipment/` | 器材列表 | 11 种器材 |

关键发现：wger API v2 的 `exercise` 列表端点返回的是精简数据，而 `exerciseinfo` 端点返回的是完整信息（含图片、翻译），**本项目直接使用 `exerciseinfo` 端点**，一次请求拿全所有数据。

---

### 第 2 步：确定工具清单

根据 `design.md` 中 ExerciseItem 模型的字段需求，确定需要暴露的工具：

```
ExerciseItem 需要:                MCP 工具提供:
├── name                          ← search_exercises（从 translations 提取英文名）
├── target_muscle                 ← search_exercises（从 muscles 提取）
├── category                      ← search_exercises（从 category 提取）
├── description                   ← search_exercises（从 translations 提取）
├── image_url                     ← get_exercise_images（教学图片）
├── sets / reps / rest            ← Agent 根据经验水平决定（非 wger 数据）
└── weight_suggestion             ← Agent 根据目标决定（非 wger 数据）
```

暴露的 7 个工具：

| 工具名 | 对应 wger 端点 | 本项目用途 |
|--------|---------------|-----------|
| `list_categories` | `GET /api/v2/exercisecategory/` | Agent 获取筛选选项 |
| `list_muscles` | `GET /api/v2/muscle/` | Agent 获取筛选选项 |
| `list_equipment` | `GET /api/v2/equipment/` | Agent 获取筛选选项 |
| `search_exercises` | `GET /api/v2/exerciseinfo/` | **核心工具**：动作搜索 |
| `get_exercise_details` | `GET /api/v2/exerciseinfo/{id}/` | 单动作详情 |
| `get_exercise_images` | `GET /api/v2/exerciseimage/` | 前端展示教学图片 |
| `get_exercise_videos` | `GET /api/v2/video/` | 前端展示演示视频 |

---

### 第 3 步：编写 MCP Server

**技术选型：**

| 组件 | 选择 | 原因 |
|------|------|------|
| MCP SDK | `mcp` Python 包（官方） | 项目 requirements.txt 已有 `fastmcp`，但使用原生 `mcp` 更轻量 |
| HTTP 客户端 | `httpx` | 项目已有，支持异步 |
| 运行方式 | stdio 协议 | 与 HelloAgents 的 MCPTool 兼容 |

**代码结构：**

```
backend/app/mcp_servers/
└── wger_mcp_server.py        ← 单文件，约 150 行
```

**核心实现逻辑（伪代码）：**

```python
# 整体结构：
# 1. 定义 7 个异步 handler 函数，分别对应 7 个工具
# 2. 每个 handler 接收参数 → httpx 请求 wger API → 返回处理后的数据
# 3. 通过 MCP Server 注册所有工具
# 4. 启动 stdio 模式，等待 Agent 调用

# 关键处理逻辑：
# - search_exercises: 将参数映射为 wger 查询参数
#     muscle → params["muscles"]  (注意是复数!)
#     query  → params["search"]
# - get_exercise_details: 从 exerciseinfo 端点获取完整数据
# - get_exercise_images/videos: 从对应端点按 exercise_id 过滤
```

**与社区版本的关键区别：**

| 项目 | 社区 MCP Server | 本项目 MCP Server |
|------|----------------|------------------|
| 语言 | TypeScript | Python |
| 数据端点 | `/api/v2/exercise/`（精简） | `/api/v2/exerciseinfo/`（完整） |
| 字段映射 | `variations: number`（错误） | `variation_group: string`（正确） |
| 工具数量 | 12 个（含写入） | 7 个（只读，按需） |
| 启动方式 | `npx @juxsta/wger-mcp` | `python wger_mcp_server.py` |

---

### 第 4 步：在项目中集成 MCP Server

**注册方式：** 与原项目集成高德地图 MCP 完全一致

```python
from hello_agents.tools import MCPTool

wger_tool = MCPTool(
    name="wger",
    description="Wger 健身数据服务",
    server_command=["python", "app/mcp_servers/wger_mcp_server.py"],
    auto_expand=True
)
```

MCPTool 自动管理子进程生命周期：
- 首次调用时启动 Python 进程
- 通过 stdio 发送 JSON-RPC 请求
- 进程空闲时保持连接，避免重复启动开销

**Agent 调用流程：**

```
Agent Prompt 中有 [TOOL_CALL:wger_search_exercises:muscle=4]
    ↓
MCPTool 解析指令
    ↓
通过 stdio 发送 JSON-RPC 请求到 wger_mcp_server.py
    ↓
MCP Server 调用 httpx.get("https://wger.de/api/v2/exerciseinfo/?muscles=4")
    ↓
返回数据 → 经过字段映射 → 返回给 Agent
```

---

### 第 5 步：验证测试

通过 MCP 协议直接调用工具验证：

| 测试项 | 命令 | 结果 |
|--------|------|------|
| 基础查询 | `list_categories` | ✅ 返回 8 个分类 |
| 基础查询 | `list_muscles` | ✅ 返回 15 个肌群（含图片 URL） |
| 基础查询 | `list_equipment` | ✅ 返回 11 种器材 |
| 动作搜索 | `search_exercises(muscle=4)` | ✅ 返回胸肌相关动作 |
| 动作搜索 | `search_exercises(query="crunch")` | ✅ 返回卷腹动作 |
| 图片查询 | `get_exercise_images(exercise_id=167)` | ✅ 返回 Crunches 教学图片 URL |
| 视频查询 | `get_exercise_videos(exercise_id=82)` | ✅ 返回 Bent-over Lateral Raises 视频 URL |

---

## 三、最终功能清单

### 工具一览

| # | 工具名 | 功能 | 参数 | 返回数据 |
|---|--------|------|------|---------|
| 1 | `list_categories` | 列出动作分类 | 无 | `[{id, name}]` |
| 2 | `list_muscles` | 列出所有肌群 | 无 | `[{id, name, name_en, is_front, image_url_main, image_url_secondary}]` |
| 3 | `list_equipment` | 列出器材类型 | 无 | `[{id, name}]` |
| 4 | `search_exercises` | 搜索训练动作 | `query`, `muscle`, `equipment`, `category`, `limit`, `offset` | `{count, results: [{id, category, muscles, equipment, images, translations, ...}]}` |
| 5 | `get_exercise_details` | 获取单动作详情 | `exercise_id` | 单个完整动作对象 |
| 6 | `get_exercise_images` | 获取教学图片 | `exercise_id`（可选） | `[{id, image, thumbnails, is_main}]` |
| 7 | `get_exercise_videos` | 获取演示视频 | `exercise_id`（可选） | `[{id, video, duration, width, height}]` |

### 数据来源验证

| 数据项 | wger API 实际数据 | 本项目使用情况 |
|--------|------------------|--------------|
| 动作总数 | 859 个 | 全部可搜索 |
| 教学图片 | 360 张 PNG | 用于前端动作展示 |
| 演示视频 | 78 个 MOV | 用于前端教学（可选） |
| 肌群数据 | 15 个（含 15 张 SVG 解剖图） | Agent 筛选条件 |
| 器材数据 | 11 种 | Agent 筛选条件 |
| 分类数据 | 8 个 | Agent 筛选条件 |

---

## 四、面试话术

### Q：为什么要自建 MCP Server，不直接用社区的？

> 我测试了社区 MCP Server，发现两个数据字段不匹配的 bug。wger API 返回的是 `variation_group`，但社区版写的是 `variations`，导致所有搜索请求都被拦截。与其修别人的代码，不如我基于 Python 从零实现一个，还能按项目需求裁剪功能。最终代码只有 150 行，没有多余的依赖。

### Q：这个 MCP Server 有什么技术亮点？

> 三点。第一，我通过 Playwright 浏览器直接调试 wger API，确认了所有字段的真实数据结构，确保字段映射完全准确。第二，我使用 `exerciseinfo` 端点代替 `exercise` 端点，一次请求拿到动作名称、描述、肌群、图片全部数据，减少了 Agent 的调用次数。第三，我额外封装了图片和视频查询工具，社区版本没有这两个功能。

### Q：和社区版本比有什么区别？

> 社区版是 TypeScript 写的 12 个工具，包含写入功能但需要 API Key，而且有两个 bug。我的版本是 Python 写的 7 个工具，全部只读无需认证，字段完全对齐 wger API，并且按本项目需求增加了图片和视频查询。另外我的版本和项目同语言，不需要额外安装 Node.js。

---

## 五、相关文件

| 文件 | 说明 |
|------|------|
| `backend/app/mcp_servers/wger_mcp_server.py` | MCP Server 实现代码 |
| `backend/app/services/mcp_client.py` | MCP 客户端封装（连接 MCP Server） |
| `backend/app/services/exercise_service.py` | 动作数据服务层（供 Agent 调用） |
| `docs/wger-mcp.md` | Wger MCP 使用文档 |
| `docs/design.md` | 项目设计文档（含 MCP 集成方案） |
