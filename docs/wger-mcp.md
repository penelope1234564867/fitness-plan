# Wger MCP 集成文档

## 一、什么是 wger？

[wger](https://wger.de) 是一个开源健身平台，提供 **800+ 训练动作数据**，涵盖：

| 数据类型 | 数量 | 说明 |
|---------|------|------|
| 训练动作 | 859 个 | 含名称、描述、目标肌群、所需器材 |
| 教学图片 | 360 张 | 真人示范动作姿势（PNG） |
| 演示视频 | 78 个 | 1080p/4K 实拍训练演示（MOV） |
| 肌群分类 | 15 个 | 覆盖全身主要肌肉群 |
| 动作类别 | 8 个 | Abs / Arms / Back / Cardio / Chest / Legs / Shoulders / Calves |
| 器材类型 | 11 种 | Barbell / Dumbbell / Kettlebell / Bodyweight 等 |

所有数据通过 REST API 公开，**无需认证即可读取**。

---

## 二、为什么自建 MCP Server？

本项目原本计划集成社区 MCP Server `@juxsta/wger-mcp`，但测试发现两个 bug：

| 问题 | 原因 |
|------|------|
| `search_exercises` 调用失败 | API 返回 `variation_group`（UUID），MCP schema 写的是 `variations`（number），类型校验不通过 |
| `get_exercise_details` 找不到动作 | 同上，字段名对不上 |

**解决方案：** 自建 Python MCP Server，优点：

- ✅ 字段映射完全对齐 wger API，无校验 bug
- ✅ Python 项目不需要多一套 Node.js / TypeScript 依赖
- ✅ 可以按本项目需求裁剪功能（只暴露需要的工具）
- ✅ 简历亮点："基于 MCP 协议从零封装健身数据接口"

---

## 三、架构设计

```
┌──────────────────────────────────────────────────────────┐
│                   Fitness Planner 后端                      │
│                                                           │
│  ReActAgent / SimpleAgent                                 │
│       │                                                    │
│       ▼                                                    │
│  MCPTool("wger")  ←── HelloAgents 内置 MCP 客户端          │
│       │                                                    │
│       │  stdio 通信（启动 Python 子进程）                    │
├───────┼──────────────────────────────────────────────────┤
│       ▼                                                    │
│  wger_mcp_server.py  ─── 本项目自建的 MCP Server            │
│       │                                                    │
│       ▼                                                    │
│  httpx 请求                                                │
├───────┼──────────────────────────────────────────────────┤
│       ▼                                                    │
│  wger REST API (https://wger.de/api/v2)                    │
└──────────────────────────────────────────────────────────┘
```

**通信流程：**

1. Agent 调用工具（如 `search_exercises`）
2. HelloAgents 的 `MCPTool` 通过 stdio 将请求发给 MCP Server
3. MCP Server 调用 wger REST API
4. 结果原路返回给 Agent

---

## 四、工具清单

> 所有工具均为只读，**不需要 API Key**。

### 4.1 基础查询工具

#### `list_categories`

列出所有动作分类（Abs / Chest / Legs 等）。

```python
# 调用示例
result = await session.call_tool("list_categories", {})
# 返回:
# [{"id": 10, "name": "Abs"}, {"id": 11, "name": "Chest"}, ...]
```

#### `list_muscles`

列出所有肌群（含正/背面标识和图片 URL）。

```python
result = await session.call_tool("list_muscles", {})
# 返回:
# [
#   {"id": 4, "name": "Pectoralis major", "name_en": "Chest",
#    "is_front": true,
#    "image_url_main": "https://wger.de/static/images/muscles/main/muscle-4.svg",
#    "image_url_secondary": "..."},
#   ...
# ]
```

#### `list_equipment`

列出所有器材类型。

```python
result = await session.call_tool("list_equipment", {})
# 返回:
# [{"id": 1, "name": "Barbell"}, {"id": 3, "name": "Dumbbell"}, ...]
```

### 4.2 动作搜索工具

#### `search_exercises`

按条件搜索训练动作，**本项目最核心的工具**。

**参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 否 | 关键词搜索（动作名称/描述） |
| `muscle` | int | 否 | 目标肌群 ID（从 list_muscles 获取） |
| `equipment` | int | 否 | 器材 ID（从 list_equipment 获取） |
| `category` | int | 否 | 分类 ID（从 list_categories 获取） |
| `limit` | int | 否 | 返回数量（默认 20，最大 100） |
| `offset` | int | 否 | 分页偏移 |

```python
# 示例 1: 搜索胸肌训练动作
result = await session.call_tool("search_exercises", {
    "muscle": 4,    # Pectoralis major
    "limit": 10
})

# 示例 2: 搜索哑铃二头肌动作
result = await session.call_tool("search_exercises", {
    "muscle": 1,      # Biceps
    "equipment": 3,   # Dumbbell
    "limit": 5
})

# 示例 3: 搜索卷腹动作
result = await session.call_tool("search_exercises", {
    "query": "crunch",
    "category": 10    # Abs
})
```

**返回数据字段说明（映射到 ExerciseItem）：**

```python
{
    "id": 167,                    # 动作 ID
    "category": {"id": 10, "name": "Abs"},  # 分类
    "muscles": [{"id": 6, "name": "Rectus abdominis", "name_en": "Abs", ...}],  # 目标肌群
    "muscles_secondary": [...],   # 辅助肌群
    "equipment": [...],           # 所需器材
    "images": [                   # 教学图片（关键字段）
        {
            "image": "https://wger.de/media/exercise-images/...png",
            "thumbnails": {
                "small": "...200x200.png",
                "medium": "...400x400.png"
            },
            "is_main": true
        }
    ],
    "translations": [             # 多语言名称和描述
        {
            "name": "Crunches",   # 动作名称
            "description": "<p>训练说明...</p>",  # HTML 格式描述
            "language": 2         # 2=英语
        }
    ],
    "variation_group": "..."      # 变体分组 UUID
}
```

#### `get_exercise_details`

获取单个动作的完整详情。

```python
result = await session.call_tool("get_exercise_details", {
    "exercise_id": 167
})
# 返回结构与 search_exercises 的单个结果一致
```

### 4.3 图片和视频工具

#### `get_exercise_images`

获取训练教学图片列表。

```python
result = await session.call_tool("get_exercise_images", {
    "exercise_id": 167   # 可选：按动作筛选
})
# 返回:
# [
#   {
#     "id": 3,
#     "exercise": 167,
#     "image": "https://wger.de/media/exercise-images/91/Crunches-1.png",
#     "thumbnails": {"small": "...", "medium": "..."},
#     "is_main": true
#   }
# ]
```

#### `get_exercise_videos`

获取训练演示视频列表。

```python
result = await session.call_tool("get_exercise_videos", {
    "exercise_id": 82    # Bent-over Lateral Raises
})
# 返回:
# [
#   {
#     "id": 7,
#     "exercise": 82,
#     "video": "https://wger.de/media/exercise-video/82/xxx.MOV",
#     "duration": "7.60",
#     "width": 1920,
#     "height": 1080
#   }
# ]
```

---

## 五、在 Agent 中使用

### 5.1 注册 MCP 工具

跟原项目集成高德地图 MCP 的方式完全一致：

```python
from hello_agents import SimpleAgent
from hello_agents.tools import MCPTool

# 创建 wger MCP 工具
wger_tool = MCPTool(
    name="wger",
    description="Wger 健身数据服务",
    server_command=["python", "app/mcp_servers/wger_mcp_server.py"],
    auto_expand=True
)

# 创建 ExerciseAgent（ReActAgent）
exercise_agent = SimpleAgent(
    name="动作设计专家",
    llm=self.llm,
    system_prompt=EXERCISE_AGENT_PROMPT
)
exercise_agent.add_tool(wger_tool)
```

### 5.2 Agent Prompt 设计

```python
EXERCISE_AGENT_PROMPT = """你是动作设计专家。你的任务是根据用户健身目标搜索合适的训练动作。

**工具调用格式:**
你必须使用工具来搜索真实动作数据，不要自己编造！

使用 search_exercises 工具时，格式如下：
`[TOOL_CALL:wger_search_exercises:muscle=4,limit=10]`
`[TOOL_CALL:wger_search_exercises:query=bench press,category=11]`

使用 list_categories 查看有哪些分类
使用 list_muscles 查看有哪些肌群
使用 list_equipment 查看有哪些器材

**要求:**
1. 每个动作必须从 wger 获取真实数据
2. 返回每个动作的名称、目标肌群、组数次数建议、训练说明
3. 优先使用教学图片（images[0].image）作为展示
"""
```

### 5.3 数据映射

wger API 返回的数据映射到本项目的 `ExerciseItem` 模型：

```python
class ExerciseItem(BaseModel):
    name: str                     # ← translations[0].name (英文)
    target_muscle: str            # ← muscles[0].name_en
    category: str                 # ← category.name (strength/cardio/...)
    sets: int                     # ← Agent 根据经验水平决定
    reps: int                     # ← Agent 根据经验水平决定
    rest_seconds: int             # ← Agent 根据动作类型决定
    weight_suggestion: str        # ← Agent 根据目标决定
    description: str              # ← translations[0].description
    image_url: Optional[str]      # ← images[0].image (优先)
```

---

## 六、FAQ

### Q: 需要注册 wger 账号吗？

**不需要。** 本项目只使用 wger 的只读接口（动作搜索、图片和视频查询），均无需认证。只有创建训练计划等写入功能才需要 API Key。

### Q: 社区 MCP Server 有 bug，你们怎么解决的？

社区包 `@juxsta/wger-mcp` 的 TypeScript schema 中 `variations` 字段类型与 wger API 实际返回的 `variation_group`（UUID）不匹配。我们的 Python MCP Server 完全对齐了 wger API 的真实字段结构，同时按本项目需求增加了图片和视频查询工具。

### Q: 启动这个 MCP Server 需要什么依赖？

```bash
pip install mcp httpx
```

这两个包已经在本项目的 `requirements.txt` 中。

### Q: 这个 MCP Server 性能怎么样？

单次请求 ≈ wger API 的响应时间（通常 200-500ms）。与社区 Node.js 版本相比，**少了 Node 进程启动开销**（原版每次连接要 1-3 秒启动 Node）。

### Q: 如何测试 MCP Server 是否正常工作？

```bash
# 直接运行 MCP Server，会进入 stdio 交互模式
python backend/app/mcp_servers/wger_mcp_server.py

# 可以用调试工具发送 JSON-RPC 请求测试
```

---

## 七、参考链接

- [wger 官网](https://wger.de)
- [wger API 文档](https://wger.de/api/v2/)
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [HelloAgents MCPTool 文档](https://github.com/your-repo/hello-agents)
