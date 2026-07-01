# 健身计划助手 — 后端架构读懂文档

> 最后更新: 2026-06-30
> 技术栈: Python 3.10+ / FastAPI / SQLite / HelloAgents LLM / wger 开放 API

---

## 目录

1. [项目定位](#1-项目定位)
2. [技术栈概览](#2-技术栈概览)
3. [目录结构](#3-目录结构)
4. [核心架构：Pipeline + Map-Reduce](#4-核心架构pipeline--map-reduce)
5. [数据模型](#5-数据模型)
6. [API 接口总览](#6-api-接口总览)
7. [Service 层详解](#7-service-层详解)
8. [Agent 层详解（核心）](#8-agent-层详解核心)
9. [MCP 服务](#9-mcp-服务)
10. [计划生成全流程数据流](#10-计划生成全流程数据流)
11. [配置与启动](#11-配置与启动)
12. [给优化者的建议](#12-给优化者的建议)

---

## 1. 项目定位

这是一个 **AI 健身计划助手** 的后端服务。用户输入身体数据、训练目标和偏好，后端自动生成个性化的周训练计划，并支持记录训练日志和查看统计数据。

**核心亮点：**
- 用 LLM（大语言模型）替代人工教练做动作筛选和计划编排
- 基于 wger.de 开放健身数据库（859+ 训练动作，15 个肌群）
- Pipeline + Map-Reduce 架构：三天计划并行生成，互不阻塞
- SSE 流式推送：前端实时看到每一天的生成进度

---

## 2. 技术栈概览

| 层        | 技术                        | 说明                              |
|-----------|-----------------------------|-----------------------------------|
| Web 框架  | FastAPI + uvicorn           | 异步 Python Web 框架              |
| 数据库    | SQLite + SQLAlchemy 2.0     | 单文件数据库，无需安装             |
| LLM 框架  | HelloAgents (>=0.2.4)       | LLM 调用封装，支持流式输出         |
| LLM 模型  | DeepSeek V4 Flash（可换）   | 通过 OpenAI 兼容 API 调用          |
| 健身数据  | wger.de API v2              | 开源健身数据库（无需 API Key）     |
| 外部API   | 高德地图（天气查询）         | 预留，用于根据天气调整计划          |
| MCP       | FastMCP (Python)            | 健身数据 MCP Server                |

---

## 3. 目录结构

```
backend/
├── run.py                          # 启动入口
├── requirements.txt                # 依赖清单
├── .env                            # 环境变量（LLM Key、端口等）
├── fitness.db                      # SQLite 数据库文件（自动生成）
│
├── app/
│   ├── __init__.py                 # 版本号
│   ├── config.py                   # pydantic-settings 配置管理
│   ├── database.py                 # SQLAlchemy 引擎 + init_db 迁移
│   │
│   ├── api/
│   │   ├── main.py                 # FastAPI 应用组装 + CORS + 路由挂载
│   │   └── routes/
│   │       ├── user.py             # 用户资料 CRUD
│   │       ├── fitness.py          # 计划生成（SSE）+ 历史查询
│   │       ├── record.py           # 训练记录 + 统计
│   │       └── wger.py             # wger 动作详情代理（带内存缓存）
│   │
│   ├── models/
│   │   ├── orm_models.py           # SQLAlchemy ORM 模型（User / FitnessPlan / WorkoutRecord）
│   │   └── schemas.py              # Pydantic 请求/响应 Schema
│   │
│   ├── services/
│   │   ├── llm_service.py          # LLM 单例管理（主模型 + 快速模型）
│   │   ├── plan_service.py         # 计划生成编排（Pipeline + Map-Reduce + SSE）
│   │   └── wger_service.py         # wger REST API 封装（搜索/详情/分类/肌群）
│   │
│   ├── agents/
│   │   ├── exercise_agent.py       # Exercise 精选器：搜索 → 过滤 → LLM 精选
│   │   ├── plan_agent.py           # Plan 组装器：LLM 编排成 {warmup, main, cooldown}
│   │   └── test_mcp.py             # MCP 链路快速测试脚本
│   │
│
└── memory/                         # 运行时调试记录、todos、traces
```

---

## 4. 核心架构：Pipeline + Map-Reduce

整个后端的核心是 **计划生成管线**，采用 Map-Reduce 模式：

```
 ┌──────────────┐
 │  Coordinator │  Stage 1: 根据 days_per_week 选择 PPL 分化方案
 │  (硬编码)     │  （推/拉/腿 × N 天）
 └──────┬───────┘
        │  schedule: [{day, focus, muscles, desc}, ...]
        ▼
 ┌──────────────────────────────────────┐
 │  Map（并行）                         │  Stage 2
 │                                      │
 │  ┌──────────┐  ┌──────────┐  ┌───  │
 │  │ Day 1    │  │ Day 2    │  │... │
 │  │ 推 天    │  │ 拉 天    │  │    │
 │  │          │  │          │  │    │
 │  │ ① search │  │ ① search │  │    │
 │  │ ② filter │  │ ② filter │  │    │
 │  │ ③ select │  │ ③ select │  │    │
 │  │ ④assemble│  │ ④assemble│  │    │
 │  └────┬─────┘  └────┬─────┘  └───  │
 └───────┼──────────────┼──────────────┘
         ▼              ▼
 ┌──────────────────────────────┐
 │  Reduce                      │  Stage 3: 收集 → 校验 → 归并为周计划
 └──────────┬───────────────────┘
            ▼
 ┌──────────────────────────────┐
 │  Persist（存库 + done 事件） │  Stage 4
 └──────────────────────────────┘
```

**关键设计决策：**
- 每天的生成独立运行，通过 `asyncio.gather` 并行（默认支持 3-6 天并发）
- 每天内部是串行 Pipeline：`search → filter → llm_select → llm_assemble`
- 失败隔离：某天失败不影响其他天，Reduce 阶段标记空数组
- SSE 实时推送：`progress`、`exercise_done`、`day_done`、`done`、`error` 五种事件

---

## 5. 数据模型

### 5.1 ORM 模型（`orm_models.py`）

**User** — 用户资料表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| height | Float | 身高(cm) |
| weight | Float | 体重(kg) |
| age | Integer | |
| gender | String(10) | male / female |
| goal | String(50) | 减脂/增肌/塑形/保持健康 |
| experience | String(20) | 新手/中级/高级 |
| city | String(50) | 城市（天气查询用） |
| workout_location | String(20) | 健身房/居家/户外 |
| days_per_week | Integer | 每周训练天数（默认3） |

**FitnessPlan** — 训练计划表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| goal / experience_level / workout_location | String | 生成时的参数快照 |
| days_per_week / duration_weeks | Integer | |
| notes | Text | 用户备注 |
| plan_content | Text | JSON 字符串，存储完整周计划 |

**WorkoutRecord** — 训练记录表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | |
| plan_id | FK → fitness_plan.id | 关联计划 |
| date | String(20) | YYYY-MM-DD |
| exercise_name | String(100) | 动作名称 |
| planned_sets/reps / actual_sets/reps | Integer | 计划 vs 实际 |
| weight | Float | 重量(kg) |
| difficulty | Integer(1-5) | 主观难度 |

### 5.2 Pydantic Schema（`schemas.py`）

请求/响应模型分层：
```
PlanRequest (输入) →  goal / experience_level / workout_location / days_per_week / duration_weeks
  │
  ▼
FitnessPlanResponse (输出) →  id + 参数快照 + weekly_plans[]
                                ├── WeeklyPlan { week: 1, days: [DailyWorkout] }
                                │     └── DailyWorkout { day, focus, warmup[], main[], cooldown[] }
                                │           └── ExerciseItem { name, sets, reps, wger_id, ... }
```

---

## 6. API 接口总览

所有路由前缀为 `/api`，CORS 默认允许所有来源。

### 用户资料

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/user/profile` | 创建/更新用户资料 |
| GET  | `/api/user/profile` | 获取当前用户资料 |

### 健身计划

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/fitness/generate` | **生成计划（SSE 流式）** — 核心接口 |
| GET  | `/api/fitness/plans` | 获取历史计划列表 |
| GET  | `/api/fitness/plan/{plan_id}` | 获取单个计划详情 |

### 训练记录

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/fitness/record` | 保存一条训练记录 |
| GET  | `/api/fitness/records` | 获取训练记录列表（可按 plan_id 过滤） |
| GET  | `/api/fitness/stats` | 训练统计概览（总组数/总次数/训练天数/平均难度/每日计数/近期重量） |

### wger 代理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/wger/exercise/{wger_id}` | 获取 wger 动作详情（图片+描述，内存缓存） |

### 健康检查

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/` | API 信息 |
| GET  | `/health` | 健康检查 |

### SSE 事件协议（`/api/fitness/generate`）

```
event: progress     → {"day": N, "phase": "coordinator|search|select|assemble|reduce|save|done", "text": "..."}
event: llm_stream   → {"day": N, "phase": "select|assemble", "chunk": "..."}  (预留)
event: exercise_done → {"day": N, "exercise": {"name": "...", "sets": 4, "reps": 8, "wger_id": 123}}
event: day_done     → {"day": N, "focus": "...", "main_count": 5}
event: done         → {"id": 123, "weekly_plans": [...]}   ← 最终完整计划
event: error        → {"text": "..."}
```

---

## 7. Service 层详解

### 7.1 `llm_service.py` — LLM 管理

使用 **HelloAgentsLLM** 封装 OpenAI 兼容 API。

- `get_llm()` — 主模型（复杂推理用，如组装计划）
- `get_fast_llm()` — 快速模型（简单决策用，如精选动作）
- 两者都是单例模式，通过 `.env` 中的 `LLM_MODEL_ID` / `FAST_LLM_MODEL_ID` 控制

当前配置：两个都用 `deepseek-v4-flash`。如果希望省钱，可将 `FAST_LLM_MODEL_ID` 设为 `deepseek-chat` 等更便宜的模型。

### 7.2 `wger_service.py` — wger 数据源

封装 wger.de API v2（开源健身数据库，无需 API Key）：

| 函数 | 说明 |
|------|------|
| `search_exercises(muscle, query, ...)` | 搜索动作，返回 JSON 字符串 |
| `get_exercise_detail(wger_id)` | 获取单动作详情（图片列表+描述） |
| `list_categories()` | 列出所有分类 |
| `list_muscles()` | 列出所有肌群 |

注意：这个 service 是 **同步 httpx** 方式，被 plan_service 通过 `run_in_executor` 线程池调用。

### 7.3 `plan_service.py` — 计划生成编排（核心）

详见第 10 节。这里强调几个设计点：

- **PPL_SPLITS** 常量字典定义了 3/4/5/6 天四种 PPL（推/拉/腿）分化方案
- 每天内部是 sync 函数（exercise_agent / plan_agent 是同步的），通过 `loop.run_in_executor` 跑在线程池
- 天与天之间是 async 并行，通过 `asyncio.gather`
- Producer-Consumer 模式：producer 把 SSE 事件推入 `asyncio.Queue`，consumer 逐个 yield
- 错误处理：每个 `_run_one_day` 包 try-except，不会让某天的失败拖垮全部

---

## 8. Agent 层详解（核心）

### 8.1 `exercise_agent.py` — 动作精选器

职责：从 wger 搜出候选动作 → LLM 精选最优搭配。

**三阶段 Pipeline：**

```
search_all_muscles(muscle_ids)
    │  用 ThreadPoolExecutor 并行请求 wger（每个肌群一个 HTTP 请求）
    │  每个肌群取最多 15 个随机动作，打乱（增加多样性）
    ▼
filter_by_equipment(grouped, experience)
    │  按经验水平过滤器材（目前所有水平都放行，依赖 LLM 智能选择）
    ▼
llm_select(grouped, goal, experience, location, split_name, per_group)
    │  构造 SELECT_PROMPT → 调用 fast LLM → 解析 JSON 返回
    │  {"selected": [{"wger_id": 123, "muscle_id": 4}, ...]}
    │  如果 LLM 解析失败，降级为每个肌群取前 per_group 个
    ▼
return [...]  → 进入 plan_agent
```

**关键常量：**
- `MUSCLES` — 15 个 wger 肌群 ID 映射（中文名 → ID）
- `EXPERIENCE_GUIDE` — 按经验水平的选动作指引（会影响 LLM 输出质量）
- `SELECT_PROMPT` — 要求 LLM 选出每个肌群最优的 N 个动作，不同肌群间要有区分度

### 8.2 `plan_agent.py` — 计划组装器

职责：接收精选动作列表，LLM 编排成当天的完整训练。

```
assemble_one_day(day_spec, selected_exercises, goal, experience, location)
    │  构建 ASSEMBLY_PROMPT（含可用动作列表、用户信息、当天聚焦）
    │  调用 fast LLM（流式收集，最大 8192 tokens）
    │  解析 JSON → {day, focus, warmup[], main[], cooldown[]}
    │  如果解析失败，降级为直接用精选动作作为 main
    ▼
return day_plan
```

**Agent 之间的数据流转：**

```
exercise_agent                           plan_agent
┌────────────────────┐                  ┌──────────────────┐
│ search_all_muscles │  [{wger_id,      │                  │
│   → muscle_id列表  │    name,         │  ASSEMBLY_PROMPT │
│   → wger 搜索      │    muscle_id,    │  → LLM 编排      │
│   → 每组15个随机   │    equipment},   │  → warmup+main+  │
│                    │    ...]          │    cooldown      │
│ filter_by_equip    │                  │  → JSON 解析     │
│   → 按经验过滤     │                  │  → 降级兜底      │
│                    │                  │                  │
│ llm_select         │                  │                  │
│   → LLM 精选最优   │                  │                  │
└────────────────────┘                  └──────────────────┘
```

---

## 9. MCP 服务

项目内置的 `wger_mcp_server.py` **已移除**，由外部独立部署的 MCP 服务器替代。

当前 `plan_service.py` 和 `exercise_agent.py` 通过 `wger_service.py`（httpx）直连 wger.de API，不经过 MCP 协议。

---

## 10. 计划生成全流程数据流

以下是一次完整的计划生成请求(`POST /api/fitness/generate`)的数据流：

```
用户请求 {"goal": "增肌", "experience_level": "中级", "workout_location": "健身房",
           "days_per_week": 4, "duration_weeks": 4}
  │
  ▼
fitness.py (路由)
  │  创建 StreamingResponse → generate_plan_stream()
  ▼
plan_service.py generate_plan_stream()
  │
  ├── 1. Coordinator: 选择 PPL 方案
  │     days_per_week=4 → "ppl_4" → PPL + 全身补充
  │     schedule: [推, 拉, 腿, 全身] × 4 天
  │     发送 SSE: event=progress, phase=coordinator
  │
  ├── 2. Map: 并行生成每天计划
  │     asyncio.gather(4 个 _run_one_day)
  │     │
  │     ├── Day 1 (推):
  │     │   ├── search: wger 搜索 胸部(4)+肩部(2)+三头(5) 每个肌群~15个动作
  │     │   ├── filter: 按"中级"过滤器材
  │     │   ├── llm_select: LLM 从候选中选最优（每肌群 per_group 个）
  │     │   └── llm_assemble: LLM 编排成 warmup+main+cooldown
  │     │       发送 SSE: progress, exercise_done(每动作), day_done
  │     │
  │     ├── Day 2 (拉): 同上（背部+二头）
  │     ├── Day 3 (腿): 同上（腿部+臀部）
  │     └── Day 4 (全身): 同上（胸+背+腹）
  │
  ├── 3. Reduce: 校验 + 归并
  │     统计 success_days，标记失败天的空数组
  │     输出 {weekly_plans: [{week:1, days: [...]}]}
  │
  └── 4. Persist: 存库
         FitnessPlan 写入 SQLite
         发送 SSE: event=done {完整计划 JSON}
```

**SSE 事件流示例（前端收到的顺序）：**

```
event: progress  → 开始生成 PPL + 全身补充 周计划...
event: progress  → 正在搜索 胸部 + 肩部 + 三头 相关动作...
event: progress  → 搜索到 37 个候选动作
event: progress  → LLM 正在精选最优动作...
event: progress  → 正在组装 胸部 + 肩部 + 三头 训练计划...
event: exercise_done → {卧推, 4组, 8次}
event: exercise_done → {哑铃飞鸟, 3组, 12次}
...
event: day_done → 第1天 · 推, 5个动作
event: progress  → 正在搜索 背部 + 二头 相关动作...
...（第2-4天类似）
event: progress  → 4/4 天生成成功，正在汇总...
event: progress  → 保存计划中...
event: done → {id: 1, weekly_plans: [...]}
```

---

## 11. 配置与启动

### 11.1 `.env` 配置项

```ini
# LLM 配置（HelloAgents 读取 LLM_* 环境变量）
LLM_MODEL_ID=deepseek-v4-flash     # 主模型
FAST_LLM_MODEL_ID=deepseek-v4-flash # 快速模型（可设为便宜模型）
LLM_API_KEY=sk-xxx                  # API Key
LLM_BASE_URL=https://api.deepseek.com  # API 地址
LLM_TIMEOUT=60                      # 超时秒数

# 服务器
HOST=0.0.0.0
PORT=8000

# CORS（逗号分隔）
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# 高德地图 API（预留，天气查询）
AMAP_API_KEY=xxx
```

### 11.2 启动命令

```bash
cd backend/
pip install -r requirements.txt
python run.py
```

启动后访问：
- API: http://localhost:8000/
- Swagger 文档: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 11.3 启动流程

```
run.py
  │  uvicorn.run("app.api.main:app", reload=True)
  ▼
main.py (FastAPI app)
  │  @app.on_event("startup")
  │  → init_db()  ← 创建/迁移 SQLite 表
  │  → 打印启动信息
  ▼
就绪：user / fitness / record / wger 四个路由模块已挂载
```

---

## 12. 给优化者的建议

### 12.1 当前架构的已知局限

1. **没有独立 MCP 客户端**：`exercise_agent.py` 是直接调 `wger_service.py`（httpx 同步请求），不是通过 MCP Client 走 MCP Server。如果想解耦，应该让 agent 通过 MCP 协议调用 wger_mcp_server。

2. **同步阻塞风险**：`exercise_agent` 和 `plan_agent` 是纯同步代码（`httpx` + `HelloAgentsLLM` 同步调用），通过 `run_in_executor` 跑在线程池。如果 LLM 响应慢，线程池可能撑满。

3. **单用户设计**：用户资料表只有一条记录（`query.first()`），不支持多用户。前端目前也是单用户模式，但后端没有 user_id 体系。

4. **没有认证鉴权**：所有接口公开，无 JWT / Session。

5. **LLM 降级逻辑简单**：LLM 解析失败时直接取前 N 个，缺少重试机制。

6. **内存缓存粗糙**：wger 代理接口用全局 dict 做缓存，无 TTL/淘汰策略。

### 12.2 可能的优化方向

| 方向 | 说明 |
|------|------|
| 异步化 agent | 把 exercise_agent / plan_agent 改为原生 async，去掉 `run_in_executor` |
| MCP 协议统一 | 让 agent 通过 MCP Client 调用 wger，而不是直连 httpx |
| 多用户支持 | 加 user_id 字段 + 认证中间件 |
| LLM 调用优化 | 加重试、缓存、fallback 模型链 |
| 计划多样性 | 现在只有 PPL 分化，可扩展推拉腿上下肢、全身等方案 |
| 数据库升级 | SQLite → PostgreSQL（需要时） |
| 计划变体 | 支持多周进阶（每周渐进超负荷）、deload 周自动安排 |
| 异步 wger_service | 改 httpx 同步为 httpx.AsyncClient |

### 12.3 关键文件速查

| 想改什么 | 去哪个文件 |
|----------|-----------|
| 修改 PPL 分化方案 | `plan_service.py` → `PPL_SPLITS` 常量 |
| 改 LLM 精选 prompt | `exercise_agent.py` → `SELECT_PROMPT` |
| 改计划组装 prompt | `plan_agent.py` → `ASSEMBLY_PROMPT` |
| 新增 API 路由 | `api/routes/` 下建新文件，`main.py` 挂载 |
| 新增数据库表 | `orm_models.py` 加 class，`database.py` 加迁移 |
| 修改请求/响应格式 | `schemas.py` |
| 切换 LLM 模型 | `.env` → `LLM_MODEL_ID` |
| 修改 CORS | `.env` → `CORS_ORIGINS` 或 `api/main.py` 的 `allow_origins` |
