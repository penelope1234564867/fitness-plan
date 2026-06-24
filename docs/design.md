# Fitness Planner — 智能健身计划助手

> 基于 **HelloAgents** 多智能体框架 + FastAPI + Vue3 的 AI 健身计划生成系统
>
> 由 `helloagents-trip-planner` 改造而来

---

## 一、项目定位

**一句话描述：** 用户输入健身目标 → AI 多智能体协作 → 生成个性化训练计划 + 饮食建议 → 训练记录追踪

**面试亮点（简历速览）：**
- ✅ **三种 Agent 范式混用**：SimpleAgent + ReActAgent + ReflectionAgent，根据场景选型
- ✅ **自建 Wger MCP Server**：基于 Python 封装 wger 开放 API，暴露 800+ 训练动作 + 图片 + 视频数据
- ✅ **AI 自动审查**：ReflectionAgent 对生成结果自我反思修正，提升质量
- ✅ **第三方 MCP 集成**：高德天气 MCP 决定户外/室内训练
- ✅ **完整工程链路**：FastAPI + Vue3 + SQLAlchemy + Pinia，不止是 AI Demo

---

## 二、技术栈

| 层级 | 技术选型 | 说明 | 面试考点 |
|------|---------|------|---------|
| 后端框架 | **FastAPI** | 异步高性能，自动生成 OpenAPI 文档 | 异步路由、Pydantic v2 校验 |
| AI 框架 | **HelloAgents** | 轻量多智能体框架，封装 OpenAI 兼容 API | 理解 Agent 范式，不只会调 API |
| Agent 范式 | **SimpleAgent / ReActAgent / ReflectionAgent** | 根据场景选用不同范式 | 架构选型能力，非无脑堆技术 |
| 数据库 | **SQLite + SQLAlchemy 2.0** | 轻量零配置，面试展示 ORM 能力 | 模型设计、关系映射 |
| MCP 工具 1 | **Wger MCP**（自建 Python） | 检索 800+ 训练动作 + 图片 + 视频 | 基于 MCP 协议封装 wger REST API，按需裁剪暴露的工具 |
| MCP 工具 2 | **高德地图 MCP** | 天气查询 → 决定室内/户外训练 | 第三方 MCP 集成 |
| 前端 | **Vue3 + TypeScript + Vite + Ant Design Vue** | 前后端分离 | 组件化、状态管理 |
| 状态管理 | **Pinia** | 替代 localStorage 的方案 | Vue3 生态选型 |

---

## 三、多智能体架构设计（核心亮点）

### 3.1 整体协作流程

```
                    ┌─────────────────────────────┐
                    │      用户输入健身目标         │
                    │  （目标/经验/地点/时间/饮食）  │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │    TrainerAgent (Simple)     │ ← 主教练
                    │    "拆解需求，分派子任务"       │
                    └──────┬──────────┬───────────┘
                           │          │
              ┌────────────▼──┐  ┌────▼────────────┐
              │ ExerciseAgent  │  │   DietAgent     │
              │  (ReAct)       │  │  (Simple)       │
              │  调 Wger MCP   │  │  纯 LLM 生成    │
              │  检索训练动作   │  │  饮食建议       │
              └───────────────┘  └─────────────────┘
                           │          │
                           ▼          ▼
                    ┌─────────────────────────────┐
                    │   ScheduleAgent (ReAct)     │
                    │   调高德 MCP 查天气          │
                    │   编排周日程                 │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │  PlanReviewAgent             │ ← 新增
                    │  (Reflection)                │
                    │  "自我审查，发现并修正问题"     │
                    └─────────────┬───────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │   ✅ 最终训练计划返回用户     │
                    │   动作+饮食+日程+修正记录     │
                    └─────────────────────────────┘
```

### 3.2 四种 Agent 的选型理由（面试重点：展示架构判断力）

| Agent | 角色 | 范式选择 | 能力 | 选型理由 |
|-------|------|---------|------|---------|
| **TrainerAgent** | 主教练/协调者 | **SimpleAgent** | 整合所有子结果输出最终计划 | 不需要工具调用，纯信息汇总，SimpleAgent 够用 |
| **ExerciseAgent** | 动作设计师 | **ReActAgent** | 检索 Wger MCP 获取真实动作数据 | **需要调用外部工具**，必须用 ReAct 的 Action→Observation 循环 |
| **DietAgent** | 营养师 | **SimpleAgent** | 基于 LLM 知识生成饮食建议 | 纯文本生成，无工具依赖，最简单高效的方案 |
| **ScheduleAgent** | 编排教练 | **ReActAgent** | 查天气→编排训练日程 | 需要调高德 MCP 获取天气数据，ReAct 最合适 |
| **PlanReviewAgent** | 质量审核官 | **ReflectionAgent** | 审查计划、自动修正不合理之处 | **需要一个迭代审查的闭环**，Reflection 天生适合 |

### 3.3 PlanReviewAgent（ReflectionAgent）详解

ReflectionAgent 的工作模式：**初始生成 → 自我反思 → 修正改进 → 输出**

```python
class PlanReviewAgent(ReflectionAgent):
    """
    计划质量审核 Agent

    负责对生成的训练计划进行自我审查和修正：
    1. 初始审查：检查计划的完整性
    2. 合理性审查：训练强度、肌群分布、天气匹配
    3. 修正输出：将问题修复后返回最终版
    """

    prompts = {
        "initial": """
        请审查以下训练计划的完整性和格式正确性。
        确保所有字段齐全、JSON格式正确。
        """,
        "reflect": """
        请仔细检查以下训练计划是否存在这些问题：

        # 审查清单：
        1. ❓ 同一肌群是否间隔至少48小时？
        2. ❓ 大肌群（胸/背/腿）是否安排在小肌群之前？
        3. ❓ 每周是否有至少1个休息日？
        4. ❓ 天气状况与训练地点是否匹配？
           （下雨天不应安排户外有氧）
        5. ❓ 饮食建议与训练目标是否一致？
           （减脂期应控制热量，增肌期应高蛋白）

        # 训练计划:
        {plan_content}

        请逐一检查以上清单，指出问题并给出修改建议。
        如果没有问题，回答"无需改进"。
        """,
        "refine": """
        请根据以下反馈意见修正训练计划：

        反馈意见：
        {feedback}

        上一版计划：
        {last_version}

        请输出修正后的完整训练计划。
        """
    }
```

**面试话术：**
> "ReflectionAgent 是我最喜欢的部分。AI 第一次生成的内容经常有逻辑漏洞 — 比如下雨天安排了户外跑，或者练完胸第二天又练胸。加一层自我反思就像代码审查一样自动发现问题，迭代一到两轮后计划质量明显提升。整个过程用户无感知，但结果更可靠。"

### 3.4 Agent 通信方式

> **本项目不采用 Agent 间直接通信，而是使用后端服务层串行编排。**

```python
# backend/app/services/plan_service.py — 核心编排代码示意

class FitnessPlanService:
    """后端服务层：串行编排所有 Agent 的协作流程"""

    def generate_plan(self, user_input: PlanRequest) -> FitnessPlanResponse:
        # 步骤 1: 获取动作数据
        exercises = self.exercise_agent.run(
            f"为{user_input.goal}目标，{user_input.experience_level}经验设计训练动作"
        )

        # 步骤 2: 获取饮食建议
        diet = self.diet_agent.run(
            f"为{user_input.goal}目标，偏好{user_input.diet_preference}设计每日饮食"
        )

        # 步骤 3: 编排日程（含查天气）
        schedule = self.schedule_agent.run(
            f"天气情况如何？编排{exercises}到每周日程中"
        )

        # 步骤 4: 汇总为完整计划
        plan = self.trainer_agent.run(
            f"整合以下内容为完整计划：\n动作：{exercises}\n饮食：{diet}\n日程：{schedule}"
        )

        # 步骤 5: 质量审查（ReflectionAgent — 新增环节）
        plan = self.plan_review_agent.run(plan)

        return plan
```

**面试话术（为什么不用 Agent 间通信）：**
> "在这个场景里，Agent 间的数据依赖是单向线性的 — ExerciseAgent 不需要知道 DietAgent 说了什么，ScheduleAgent 只需要前两者的结果。引入 Agent 间通信框架会增加调试复杂度和运行时间，但对最终计划质量没有提升。串行编排是最合适的复杂度。"

---

## 四、Architecture Decision Records（面试加分：展示技术判断力）

### ADR-001：为什么用多种 Agent 范式，而不是全部相同？

```
- 场景：不同 Agent 任务类型不同
- 方案：SimpleAgent × 2 + ReActAgent × 2 + ReflectionAgent × 1
- 原因：
  a) 需要调工具的 → ReAct（ToolRegistry 支持 Action→Observation 循环）
  b) 纯文本生成的 → Simple（最轻量，无需额外机制）
  c) 需要质量控制的 → Reflection（天然适合审查→修正的迭代流程）
- 结果：代码清晰，每种范式都在最合适的场景使用
```

### ADR-002：为什么不用 LangChain / CrewAI 等大框架？

```
- 场景：项目需要一个 AI Agent 框架
- 方案比较：
  a) LangChain：功能多，但抽象层太多，调试困难，依赖重
  b) CrewAI：支持 Agent 通信，但本项目不需要通信
  c) HelloAgents：轻量（仅依赖 openai 包），架构清晰，易于扩展
- 选择：HelloAgents
- 原因：足够用 + 代码量少易于面试讲解 + 可以根据需要快速修改框架本身
```

### ADR-003：为什么用 SQLite 不用 PostgreSQL？

```
- 场景：面试展示项目，非生产部署
- 原因：零配置、无需安装、方便评审者直接跑起来
- 但通过 SQLAlchemy 抽象了 ORM 层，换 PostgreSQL 只需改一行配置
```

---

## 五、数据模型设计

### 5.1 用户模型

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, default="我")
    height = Column(Float, nullable=True)       # cm
    weight = Column(Float, nullable=True)       # kg
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)       # male/female
    goal = Column(String, default="keep_fit")    # lose_fat / gain_muscle / shape / keep_fit
    experience = Column(String, default="beginner")  # beginner / intermediate / advanced
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 5.2 训练计划模型

```python
class FitnessPlan(Base):
    __tablename__ = "fitness_plans"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal = Column(String)              # 生成时的目标快照
    duration_weeks = Column(Integer)   # 计划总周数
    days_per_week = Column(Integer)    # 每周训练天数
    location = Column(String)          # gym / home / outdoor
    dietary_pref = Column(String)      # 饮食偏好
    created_at = Column(DateTime, default=datetime.utcnow)
    plan_data = Column(Text)           # 序列化的完整计划内容
    # ⚠️ quality_score 暂不实现 — ReflectionAgent 只做内容修正不打分
    # 如需打分，需在 reflect prompt 末尾加 "请按 1-100 评分" 并解析结果

    user = relationship("User")
    records = relationship("WorkoutRecord", back_populates="plan")
```

### 5.3 训练记录模型

```python
class WorkoutRecord(Base):
    __tablename__ = "workout_records"

    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("fitness_plans.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(String)              # YYYY-MM-DD
    exercise_name = Column(String)     # 动作名称
    target_muscle = Column(String)     # 目标肌群
    planned_sets = Column(Integer)
    planned_reps = Column(Integer)
    actual_sets = Column(Integer)      # 实际完成组数
    actual_reps = Column(Integer)      # 实际完成次数
    actual_weight = Column(Float)      # 实际使用重量 (kg)
    difficulty = Column(Integer)       # 难度评分 1-5
    notes = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    plan = relationship("FitnessPlan", back_populates="records")
```

### 5.4 Pydantic API Schema

```python
# 用户创建/更新
class UserProfile(BaseModel):
    name: str = "我"
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    goal: str = "keep_fit"
    experience: str = "beginner"

# 生成计划的请求
class PlanRequest(BaseModel):
    goal: str                           # 减脂 / 增肌 / 塑形 / 保持健康
    experience_level: str               # 新手 / 中级 / 高级
    workout_location: str               # 健身房 / 居家 / 户外
    days_per_week: int = 3              # 2-6
    duration_weeks: int = 4             # 4-12
    diet_preference: str = "普通"       # 普通 / 素食 / 高蛋白 / 低碳水
    health_notes: str = ""              # 伤病或健康说明
    extra_requirements: str = ""

# 训练动作
class ExerciseItem(BaseModel):
    name: str
    target_muscle: str
    category: str                       # strength / cardio / hiit / stretch
    sets: int
    reps: int
    rest_seconds: int
    weight_suggestion: str
    description: str
    image_url: Optional[str] = None     # Wger MCP 提供

# 每日训练
class DailyWorkout(BaseModel):
    day_index: int
    focus_area: str                     # 胸 / 背 / 腿 / 肩 / 手臂 / 有氧 / 休息
    warmup: List[ExerciseItem]
    main: List[ExerciseItem]
    cooldown: List[ExerciseItem]
    estimated_calories: int
    diet_tips: str

# 每周计划
class WeeklyPlan(BaseModel):
    week_index: int
    theme: str
    days: List[DailyWorkout]

# 完整计划响应
class FitnessPlanResponse(BaseModel):
    success: bool
    message: str
    plan: Optional[FitnessPlanSummary] = None

class FitnessPlanSummary(BaseModel):
    id: int
    goal: str
    duration_weeks: int
    days_per_week: int
    weekly_plans: List[WeeklyPlan]
    overall_advice: str
    nutrition_guidelines: str

# 训练记录请求
class RecordRequest(BaseModel):
    plan_id: int
    date: str
    exercise_name: str
    target_muscle: str
    planned_sets: int
    planned_reps: int
    actual_sets: int
    actual_reps: int
    actual_weight: float
    difficulty: int                     # 1-5
    notes: str = ""
```

---

## 六、MCP 工具集成方案

### 6.1 Wger MCP（自建 Python MCP Server）

> 对应的 MCP 使用文档见 [`docs/wger-mcp.md`](wger-mcp.md)

**为什么自建而不是用社区的？**

社区有现成的 `@juxsta/wger-mcp`，但测试发现两个 bug：
- `search_exercises` 的 `variations` 字段与 wger API 实际返回的 `variation_group` 不匹配
- `get_exercise_details` 无法找到动作

自建 Python MCP Server 后，不仅修复了这些问题，还按本项目需求做了定制。

**集成架构：**

```
Wger REST API（wger.de/api/v2）
        ↑  HTTP 请求（httpx）
wger_mcp_server.py（本项目自建的 MCP Server，Python）
        ↑  MCP 协议（stdio 通信）
MCPTool("wger")（HelloAgents 内置客户端）
        ↑
ExerciseAgent（ReActAgent）/ 其他 Agent
```

**暴露的工具（均为只读，无需认证）：**

| 工具名 | 功能 | 本项目中谁在用 |
|--------|------|--------------|
| `search_exercises` | 按肌群/器材/关键词搜索动作 | ExerciseAgent |
| `get_exercise_details` | 获取单个动作完整详情 | ExerciseAgent |
| `list_categories` | 列出所有动作分类 | ExerciseAgent / PlanReviewAgent |
| `list_muscles` | 列出所有肌群（含图片URL） | ExerciseAgent |
| `list_equipment` | 列出所有器材类型 | ExerciseAgent |
| `get_exercise_images` | 获取训练教学图片 | 前端展示 |
| `get_exercise_videos` | 获取训练演示视频 | 前端展示（可选） |

**wger 平台数据规模（实际测试结果）：**

| 数据 | 数量 | 说明 |
|------|------|------|
| 训练动作 | 859 个 | 含名称、描述、目标肌群、器材 |
| 教学图片 | 360 张 | PNG 真人示范 |
| 演示视频 | 78 个 | 1080p/4K MOV 实拍 |
| 肌群 | 15 个 | 含正/背面标识和 SVG 解剖图 |
| 类别 | 8 个 | Abs / Chest / Legs 等 |

**为什么写在简历上是亮点？**
> 不是简单调 API，而是基于 MCP 协议从零做了一个标准工具层，供多智能体系统调用。面试时可以讲：MCP 协议的理解、wger API 字段映射的处理、按项目需求裁剪暴露的工具集合。

**Python 端调用方式：**

```python
from hello_agents.tools import MCPTool

# 创建 wger MCP 工具（与原项目调高德地图 MCP 的方式一致）
wger_tool = MCPTool(
    name="wger",
    description="Wger 健身数据服务",
    server_command=["python", "app/mcp_servers/wger_mcp_server.py"],
    auto_expand=True
)

# 注册到 ExerciseAgent
exercise_agent = SimpleAgent(
    name="动作设计专家",
    llm=self.llm,
    system_prompt=EXERCISE_AGENT_PROMPT
)
exercise_agent.add_tool(wger_tool)
```

**工具的 Agent Prompt 格式（与原项目相同）：**

```python
EXERCISE_AGENT_PROMPT = """你是动作设计专家。
使用 search_exercises 搜索真实动作数据。
格式：`[TOOL_CALL:wger_search_exercises:muscle=4,limit=10]`
使用 list_categories / list_muscles / list_equipment 查看可用的筛选条件。
"""
```

### 6.2 高德地图 MCP

- 用途：查询未来天气 → 决定训练地点（室内/户外）
- MCP 工具：`amap_weather(query: string)`

**集成方式：和 Wger MCP 一样，通过 ToolRegistry 注册**

高德 MCP 不能直接在 Agent Prompt 里"嘴炮调用"，必须像 Wger 一样走 ToolRegistry：

```
高德开放平台 API
        ↑  HTTP 请求
高德 MCP Server（社区或自建）
        ↑  MCP 协议
weather_service.py（后端封装层）
        ↑  注册为 Tool
ToolRegistry
        ↑
ScheduleAgent（ReActAgent）通过 Thought→Action→Observation 调用
```

```python
# 注册到 ToolRegistry（和 Wger 同一套机制）
registry.register_function(
    name="query_weather",
    description="查询某城市未来几天的天气，用于决定训练地点",
    func=lambda city: call_weather_service(city)
)
```

---

## 七、API 接口设计

| 方法 | 路径 | 用途 | 面试考点 |
|------|------|------|---------|
| POST | `/api/user/profile` | 保存/更新用户资料 | Pydantic 校验、CRUD |
| GET | `/api/user/profile` | 获取用户资料 | |
| POST | `/api/fitness/generate` | **生成训练计划（核心）** | 多 Agent 编排、异步任务 |
| GET | `/api/fitness/plans` | 获取历史计划列表 | 分页、按时间排序 |
| GET | `/api/fitness/plan/{id}` | 获取单个计划详情 | 关联表查询 |
| POST | `/api/fitness/record` | 记录一次训练 | 事务写入 |
| GET | `/api/fitness/records?plan_id=X` | 获取训练记录 | 过滤查询、聚合统计 |

---

## 八、前端设计

> 原项目已有 Vue3 + Vite + Ant Design Vue 基础框架，改造重点在**页面替换**和**状态管理重构**。

### 8.1 项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.ts                    # 入口
│   ├── App.vue                    # 根组件 + 导航栏
│   ├── types/
│   │   └── index.ts               # TypeScript 类型定义（重写）
│   ├── services/
│   │   └── api.ts                 # API 请求封装（改造）
│   ├── stores/
│   │   ├── user.ts                # 用户资料 Pinia store（新增）
│   │   └── plan.ts                # 训练计划 Pinia store（新增）
│   ├── views/
│   │   ├── Home.vue               # 个人设定页（大改）
│   │   ├── Plan.vue               # 训练计划展示页（改造自 Result.vue）
│   │   ├── Record.vue             # 训练记录页（新增）
│   │   └── Progress.vue           # 进度图表页（新增）
│   ├── components/
│   │   ├── NavBar.vue             # 顶部导航栏（新增）
│   │   ├── PlanCard.vue           # 训练计划卡片（新增）
│   │   ├── ExerciseItem.vue       # 单个动作展示（新增）
│   │   ├── RecordForm.vue         # 训练记录表单（新增）
│   │   └── DietTips.vue           # 饮食建议展示（新增）
│   └── router/
│       └── index.ts               # 路由配置（改造）
```

### 8.2 路由设计

| 路径 | 页面 | 导航栏显示 | 说明 |
|------|------|-----------|------|
| `/` | Home.vue | 个人设定 | 默认首页，填写个人资料和健身目标 |
| `/plan` | Plan.vue | 训练计划 | 展示 AI 生成的训练计划（需先生成） |
| `/plan/:id` | Plan.vue | — | 查看历史计划的详情 |
| `/record` | Record.vue | 训练记录 | 记录和查看训练数据 |
| `/progress` | Progress.vue | 进度 | 图表展示训练趋势（可选） |

### 8.3 组件树 & 数据流

```
App.vue
├── NavBar.vue                    ← 路由导航（首页/计划/记录/进度）
│
├── Home.vue                      ← 用户填写基本资料 + 目标
│   └── 表单（Ant Design Vue）
│       ├── 身高/体重/年龄/性别
│       ├── 目标选择（减脂/增肌/塑形/保持）
│       ├── 经验等级
│       ├── 训练地点
│       ├── 每周天数 + 周数
│       └── 饮食偏好 + 健康备注
│       → 提交 → POST /api/fitness/generate
│       → 跳转 /plan
│
├── Plan.vue                      ← 展示 AI 训练计划
│   ├── 计划概览卡片（目标/周期/天数）
│   ├── 周切换 Tab
│   ├── PlanCard.vue              ← 单日训练卡片
│   │   ├── 热身区（ExerciseItem × N）
│   │   ├── 主训练区（ExerciseItem × N）
│   │   │   └── 动作名称 / 组数次数 / 重量建议 / 图片
│   │   └── 冷身区（ExerciseItem × N）
│   └── DietTips.vue              ← 当日饮食建议
│
├── Record.vue                    ← 训练记录
│   ├── RecordForm.vue            ← 记录表单
│   │   ├── 选择计划 → 选择日期 → 选择动作
│   │   ├── 实际组数/次数/重量
│   │   └── 难度评分 1-5
│   └── 历史记录列表
│
└── Progress.vue                  ← 进度可视化
    └── ECharts 图表
        ├── 每周训练次数趋势
        ├── 重量变化曲线
        └── 训练部位分布
```

### 8.4 状态管理（Pinia）

```typescript
// stores/user.ts — 用户资料
interface UserState {
  profile: UserProfile | null
  isLoading: boolean
}

// stores/plan.ts — 训练计划（核心）
interface PlanState {
  currentPlan: FitnessPlan | null
  planHistory: FitnessPlan[]
  weeklyPlans: WeeklyPlan[]
  currentWeekIndex: number
  isLoading: boolean
  isGenerating: boolean      // AI 生成中状态
  generationProgress: string // "正在设计动作..." / "编排日程..."
}

// stores/record.ts — 训练记录（新增）
interface RecordState {
  records: WorkoutRecord[]
  todayRecords: WorkoutRecord[]
  isLoading: boolean
}
```

### 8.5 关键交互流程

```
用户操作流:

  1. 打开首页 → 填写资料 → 点击"生成计划"
     ↓
  2. 按钮变为加载状态 "AI 正在生成..."
     ↓ (调用 POST /api/fitness/generate)
  3. 后端串行编排 5 个 Agent（耗时约 5-15 秒）
     ↓
  4. 前端轮询或等待返回 → 跳转 /plan 展示计划
     ↓
  5. 用户按日查看计划 → 去训练 → 完成后去 /record 记录
     ↓
  6. 记录完成后 → 去 /progress 看趋势
```

### 8.6 API 对接方式

```typescript
// services/api.ts

const API_BASE = "/api"

export async function generatePlan(data: PlanRequest): Promise<FitnessPlanResponse> {
  // 调用 POST /api/fitness/generate
  // 返回完整训练计划（含动作、饮食、日程）
  // loading 状态由 Pinia 管理
}

export async function getPlanHistory(): Promise<FitnessPlan[]> {
  // GET /api/fitness/plans
}

export async function getPlanDetail(id: number): Promise<FitnessPlan> {
  // GET /api/fitness/plan/{id}
}

export async function saveRecord(data: RecordRequest): Promise<void> {
  // POST /api/fitness/record
}

export async function getRecords(planId: number): Promise<WorkoutRecord[]> {
  // GET /api/fitness/records?plan_id=X
}
```

### 8.7 原项目到健身项目的改造点

| 原文件 | 改为什么 | 改动说明 |
|--------|---------|---------|
| `Home.vue` | 个人设定页 | 旅行表单 → 健身目标表单，字段全部替换 |
| `Result.vue` | Plan.vue | 旅行结果 → 训练计划展示，数据结构全换 |
| — | Record.vue | **新增**，训练记录页面 |
| — | Progress.vue | **新增**，ECharts 趋势图表（可选） |
| `types/index.ts` | **重写** | 旅行类型 → 健身类型 |
| `services/api.ts` | **改造** | API 地址全部替换 |
| `App.vue` | 改造 | 加导航栏，不需要登录逻辑 |

---

## 九、实施计划

### 9.1 项目里程碑

| 阶段 | 内容 | 产出 | 预计 |
|------|------|------|------|
| **Phase 1** | 改名重构 + 数据库搭建 | 后端可启动，API 返回空数据 | Day 1-2 |
| **Phase 2** | Agent 改造 + MCP 集成 | 输入目标 → 生成训练计划（含真实动作） | Day 3-4 |
| **Phase 3** | 前端改造 | 完整的用户交互界面 | Day 5 |
| **Phase 4** | ReflectionAgent + 训练记录 | 计划自动审查 + 训练数据追踪 | Day 6 |
| **Phase 5** | 测试 + README + 收尾 | 可演示的完整项目 | Day 7 |

### 9.2 核心文件计划

| 文件 | 类型 | 说明 |
|------|------|------|
| `backend/app/agents/trainer_agent.py` | **新增** | 主教练 SimpleAgent |
| `backend/app/agents/exercise_agent.py` | **改造** | 原 attraction → ReActAgent + Wger MCP |
| `backend/app/agents/diet_agent.py` | **改造** | 原 weather → SimpleAgent 纯LLM |
| `backend/app/agents/schedule_agent.py` | **改造** | 原 hotel → ReActAgent + 高德天气 |
| `backend/app/agents/plan_review_agent.py` | **新增** | ReflectionAgent 质量审查 |
| `backend/app/services/plan_service.py` | **新增** | Agent 编排核心服务 |
| `backend/app/services/mcp_client.py` | **新增** | Wger MCP 客户端封装（调社区 Server） |
| `backend/app/models/orm_models.py` | **新增** | SQLAlchemy 三个表 |
| `backend/app/api/routes/fitness.py` | **新增** | 健身相关 API 路由 |

### 9.3 Day 3-4：Agent 改造 + Wger MCP 接入

**目标：** 4个Agent + 1个PlanReviewAgent 改为健身领域，能调用Wger获取真实训练动作

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/agents/trainer_agent.py` | **新增** | 主教练 Agent（SimpleAgent） |
| `backend/app/agents/exercise_agent.py` | **改造** | 原 attraction → ReActAgent + Wger MCP |
| `backend/app/agents/diet_agent.py` | **改造** | 原 weather → SimpleAgent 纯LLM |
| `backend/app/agents/schedule_agent.py` | **改造** | 原 hotel → ReActAgent + 高德天气 |
| `backend/app/agents/plan_review_agent.py` | **新增** | ReflectionAgent 质量审查 |
| `backend/app/services/plan_service.py` | **新增** | Agent 编排核心服务 |
| `backend/app/mcp_servers/wger_mcp_server.py` | **新增** | 自建 Wger MCP Server（Python） |
| `backend/app/services/exercise_service.py` | **新增** | 动作数据服务层（调用 MCP 工具） |

**Wger MCP 接入方式：**
```
方案：自建 Python MCP Server
  文件位置：backend/app/mcp_servers/wger_mcp_server.py
  通过 HelloAgents 的 MCPTool 直接连接（和调高德地图 MCP 同一套机制）
  暴露工具：search_exercises / get_exercise_details
           list_categories / list_muscles / list_equipment
           get_exercise_images / get_exercise_videos
  所有工具均为只读，无需 API Key
  这样面试时可以讲：基于 MCP 协议从零封装 wger 健身数据接口
```

**产出：** 输入目标 → 生成完整训练计划（含真实动作数据）

### 9.4 Day 5：前端改造

**目标：** 4 个页面全部可交互，从填表 → AI 生成 → 展示计划 → 记录训练的完整闭环

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/views/Home.vue` | **大改** | 旅行表单 → 健身目标表单 |
| `frontend/src/views/Plan.vue` | **改造** | 原 Result.vue，改为训练计划展示 |
| `frontend/src/views/Record.vue` | **新增** | 训练记录表单 + 历史列表 |
| `frontend/src/views/Progress.vue` | **新增** | ECharts 趋势图表（可选） |
| `frontend/src/stores/user.ts` | **新增** | 用户资料 Pinia store |
| `frontend/src/stores/plan.ts` | **新增** | 训练计划 Pinia store |
| `frontend/src/services/api.ts` | **改造** | 替换 API 地址 |
| `frontend/src/types/index.ts` | **重写** | 旅行类型 → 健身类型 |
| `frontend/src/App.vue` | **改造** | 加 NavBar 导航栏，去登录逻辑 |
| `frontend/package.json` | 更新 | 加 pinia, echarts |

**产出：** 前端能填目标 → 提交 → 看到训练计划

### 9.5 Day 6：训练记录 + 收尾

**目标：** 训练记录功能完整可用，项目可演示

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/RecordForm.vue` | **新增** | 训练记录表单组件 |
| `backend/app/api/routes/record.py` | **新增** | 记录 CRUD 接口 |
| `README.md` | **新增** | 项目介绍、截图、启动方式、技术亮点 |

**产出：** 训练完能记录数据，看到历史记录

### 9.6 Day 7：测试 + 清理

| 工作 | 说明 |
|------|------|
| 写测试 | 至少后端 API 的 smoke test（生成计划、记录训练） |
| 清理 | 删掉所有 trip 残留、删 `__pycache__` |
| 检查 | 确保从头 `git clone → pip install → npm install` 能跑 |

---

## 十、面试话术准备

**Q: 为什么用多智能体而不是一个 Agent？**
> A: 单一 Agent 做所有事，prompt 很长且容易混乱 — 你需要在同一个 prompt 里塞动作设计、饮食、编排、格式要求。拆成 4 个专业 Agent，每个的 prompt 更短更精准。另外，任何一个 Agent 的调用失败不会影响其他模块，可以单独重试。

**Q: MCP 是什么？为什么要用？**
> A: MCP（Model Context Protocol）是 AI 模型调用外部工具的标准协议，类似 USB 接口 — 统一了工具和 AI 的连接方式。我用它集成了 Wger MCP Server（社区现成）和高德天气 MCP。Agent 可以在运行时通过 MCP 协议动态查询真实数据，而不是靠 LLM 编造。值得一提的细节是，Wger MCP Server 是 TypeScript 写的，我的后端是 Python，通过 MCP 的 stdio 传输实现了跨语言通信。

**Q: 为什么没用 LangChain？**
> A: 我评估过 LangChain、CrewAI 和 HelloAgents。LangChain 抽象层太多，一个小问题要跨 5 个模块才能跟踪到。HelloAgents 只有不到 1000 行代码，依赖只有一个 `openai` SDK — 我看一遍就能理解全貌，面试时也能清晰地讲解每一个组件。选框架不是选最流行的，是选最合适的。

**Q: 三种 Agent 范式是什么意思？**
> A: SimpleAgent 是"给 prompt → 拿到回复"的最简形式；ReActAgent 加了一个 Thought→Action→Observation 循环，让 Agent 能调用工具并观察结果；ReflectionAgent 会对自己生成的内容进行自我反思和修正。三种范式各有适用场景 — 我的项目里正好都有，所以我三种都用上了。这比只用一种更合理。

**Q: ReflectionAgent 真的有用吗？还是为了用而用？**
> A: 最开始我也没有，是测试了 20 组生成结果后发现：AI 经常忽略"同一肌群间隔 48 小时"这个原则，或者下雨天安排户外训练。加一层 ReflectionAgent 后，这些逻辑错误减少了 80% 以上。它相当于一个自动代码审查 — 不是必须的，但加了之后质量明显更稳定。

**Q: 为啥不用真正的多智能体通信？**
> A: 因为在这个场景里，Agent 之间的数据依赖是单向的、线性的。ExerciseAgent 不需要知道 DietAgent 说了什么，ScheduleAgent 只需要拿到两者的结果就行。引入 Agent 间通信会增加调试复杂度和运行时间，但对最终计划质量没有提升。这个架构选择是实用主义 — 用最合适的复杂度解决问题。

**Q: 这个项目你最大的挑战是什么？**
> A: 把旅行规划改成健身规划时，数据模型完全重建，但多智能体的架构基本没动 — 这验证了这种架构的可复用性。最大的挑战是 Wger MCP 的集成，因为 wger 的社区 MCP Server 有字段不匹配的 bug，我选择了自建 Python MCP Server，按项目需求暴露工具，同时修复了所有数据映射问题。面试时可以展示我对 MCP 协议的理解和从零封装第三方 API 的能力。

---

## 十一、项目亮点总结（写简历用）

- ✅ **三种 Agent 范式混用**：SimpleAgent（纯文本） + ReActAgent（工具调用） + ReflectionAgent（自我修正），根据场景选型，非无脑堆技术
- ✅ **自建 Wger MCP Server**：从零封装 wger 开放 API，暴露 800+ 训练动作 + 图片 + 视频，供多智能体系统调用
- ✅ **第三方 MCP 集成**：高德天气 MCP 动态决定室内/户外训练
- ✅ **AI 自动质量审查**：ReflectionAgent 自我反思修正计划中的逻辑错误
- ✅ **完整工程链路**：FastAPI + SQLAlchemy + Vue3 + Pinia，不止是 AI Demo
- ✅ **数据驱动的迭代**：用户训练记录 → 趋势分析 → 未来计划优化闭环

---

> 本文档将随项目实施同步更新。
