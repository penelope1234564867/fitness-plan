# Fitness Planner — 任务流程文档

> 基于 `design.md` 整理，按实施顺序逐步执行。且边完成边把[ ] 改成 [x]
> 所有改造基于 `helloagents-trip-planner/` 原项目进行。

---

## Phase 1：项目初始化 & 后端骨架（Day 1-2）

### 任务 1.1：复制原项目，建立新目录结构

- [x] 在 `fitness-plan/` 下创建 `backend/` 和 `frontend/` 目录（从原项目复制）
- [x] 复制 `helloagents-trip-planner/backend/` → `fitness-plan/backend/`
- [x] 复制 `helloagents-trip-planner/frontend/` → `fitness-plan/frontend/`
- [x] 删除所有旅行相关残留（trip、attraction、hotel 相关文件名和代码）— 后端已清除，前端残留留待 Phase 3

### 任务 1.2：后端依赖更新

- [x] 打开 `backend/requirements.txt`，确认以下包存在（没有则添加）：
  ```
  hello-agents[protocols]>=0.2.4,<=0.2.9
  fastapi>=0.115.0
  uvicorn[standard]>=0.32.0
  pydantic>=2.0.0
  pydantic-settings>=2.0.0
  httpx>=0.27.0
  python-dotenv>=1.0.0
  sqlalchemy>=2.0.0
  fastmcp>=2.0.0
  loguru>=0.7.0
  ```
- [x] 运行 `pip install -r requirements.txt` 确认安装成功

### 任务 1.3：配置环境变量

- [x] 编辑 `backend/.env`，确保包含：
  ```
  # LLM 配置（从原项目复制）
  LLM_API_KEY=your_key
  LLM_BASE_URL=your_base_url
  LLM_MODEL=your_model

  # 高德地图 API Key（从原项目复制）
  AMAP_API_KEY=your_amap_key
  ```
- [x] 确认 `backend/app/config.py` 能读取上述变量

### 任务 1.4：数据库模型建立

- [x] 新建 `backend/app/models/orm_models.py`，实现三张表：
  - `User`（用户资料：身高/体重/年龄/性别/目标/经验）
  - `FitnessPlan`（训练计划：目标快照/周数/天数/地点/饮食偏好/计划内容 JSON）
  - `WorkoutRecord`（训练记录：计划ID/日期/动作名/组数次数重量/难度评分）
- [x] 在 `backend/app/database.py` 中配置 SQLite 连接和 `Base.metadata.create_all()`

### 任务 1.5：Pydantic API Schema 定义

- [x] 新建或重写 `backend/app/models/schemas.py`，实现以下模型：
  - `UserProfile`（用户创建/更新）
  - `PlanRequest`（生成计划请求：目标/经验/地点/天数/周数/饮食/备注）
  - `ExerciseItem`（单个训练动作）
  - `DailyWorkout`（每日训练：热身+主训练+冷身）
  - `WeeklyPlan`（每周计划）
  - `FitnessPlanResponse` / `FitnessPlanSummary`（完整计划响应）
  - `RecordRequest`（训练记录请求）

### 任务 1.6：API 路由骨架建立

- [x] 新建 `backend/app/api/routes/user.py`，注册以下路由（已关联数据库）：
  - `POST /api/user/profile`
  - `GET /api/user/profile`
- [x] 新建 `backend/app/api/routes/fitness.py`，注册以下路由（先返回占位数据）：
  - `POST /api/fitness/generate`
  - `GET /api/fitness/plans`
  - `GET /api/fitness/plan/{id}`
- [x] 新建 `backend/app/api/routes/record.py`，注册以下路由：
  - `POST /api/fitness/record`
  - `GET /api/fitness/records`
- [x] 更新 `backend/app/api/main.py`，挂载所有路由，配置 CORS

### 任务 1.7：验证后端可启动

- [x] 运行 `uvicorn app.api.main:app --reload`
- [x] 打开 `http://localhost:8000/docs`，确认所有路由出现在 Swagger UI 中
- [x] 访问 `POST /api/user/profile`，确认接口可调通（返回占位响应即可）

### ✅ Phase 1 可视化验收

**验收方式：浏览器 + 终端输出**

1. **终端启动日志** — 运行 `uvicorn` 后终端应出现：
   ```
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   INFO:     Started reloader process
   INFO:     Application startup complete.
   ```
   无 `ImportError` / `ModuleNotFoundError`。

2. **Swagger UI 截图验收** — 打开 `http://localhost:8000/docs`，页面应显示：
   - 标题：`Fitness Planner API`（或类似名称）
   - 至少 6 个路由分组可见：`/api/user/profile`（GET/POST）、`/api/fitness/generate`、`/api/fitness/plans`、`/api/fitness/plan/{id}`、`/api/fitness/record`、`/api/fitness/records`

3. **在线测试接口** — 在 Swagger UI 中展开 `POST /api/user/profile`，点击「Try it out」，输入：
   ```json
   {"height": 170, "weight": 65, "age": 25, "gender": "male", "goal": "减脂", "experience": "新手"}
   ```
   响应状态码为 `200`，返回任意 JSON（占位数据即可）。

4. **数据库文件检查** — 在 `backend/` 目录下应出现 `fitness.db`（SQLite 文件），大小 > 0 字节。

**Phase 1 完成标志：** 后端可启动，所有 API 路由存在，数据库文件自动创建。

---

## Phase 2：Agent 改造 & MCP 集成（Day 3-4）

### 任务 2.1：自建 Wger MCP Server ✅

- [x] 新建 `backend/app/mcp_servers/wger_mcp_server.py`
- [x] 使用 `mcp` 官方 Python SDK 实现 7 个只读工具（无需 API Key）：
  - `wger_list_categories` — 列出所有动作分类
  - `wger_list_muscles` — 列出所有肌群（含图片 URL）
  - `wger_list_equipment` — 列出所有器材类型
  - `wger_search_exercises` — 按肌群/器材/关键词/分类搜索动作（参数：query/muscle/equipment/category/limit/offset）
  - `wger_get_exercise_details` — 获取单个动作完整详情（参数：exercise_id）
  - `wger_get_exercise_images` — 获取动作教学图片列表（参数：exercise_id）
  - `wger_get_exercise_videos` — 获取动作演示视频列表（参数：exercise_id）
- [x] 使用 `httpx` 异步 HTTP 客户端请求 `https://wger.de/api/v2/`，已处理 301 跳转
- [x] 字段映射已处理：API 返回 `variation_group`（UUID），不是 `variations`；肌群过滤参数为 `muscles`（复数）
- [x] 使用 `exerciseinfo` 端点（含完整数据：名称/描述/肌群/图片），无需分别请求多个端点
- [x] 验证通过：`list_categories` → 8 个分类；`search_exercises(muscle=4)` → 99 个胸部动作，含教学图片

### 任务 2.2：实现 ExerciseAgent（ReActAgent + Wger 工具）✅

> ⚠️ 注意：必须用 **ReActAgent**，SimpleAgent 无法调用工具

- [x] 新建 `backend/app/agents/exercise_agent.py`
- [x] 封装 3 个 Tool 类：`WgerSearchTool`、`WgerListCategoriesTool`、`WgerListMusclesTool`
  - 注意：不使用 MCPTool（hello_agents v1.0.0 没有此模块），而是直接继承 `Tool` 基类调 REST API
- [x] 使用 `ReActAgent` + `ToolRegistry` 注册 Wger 工具
- [x] 编写 `EXERCISE_AGENT_PROMPT`，明确告知可用工具、组次策略（新手→高级）和 JSON 格式
- [x] Agent 输出 JSON 数组，每项包含：name / target_muscle / category / sets / reps / rest_seconds / weight_suggestion / description / image_url

### 任务 2.3：实现 DietAgent（SimpleAgent）✅

- [x] 新建 `backend/app/agents/diet_agent.py`
- [x] 使用 `SimpleAgent`，纯 LLM 知识生成饮食建议
- [x] 输入：目标 + 饮食偏好；输出：JSON（daily_calories / meals / tips）
- [x] 内置热量策略：减脂 1500-1800、增肌 2200-2800、塑形 1800-2200

### 任务 2.4：实现 ScheduleAgent（ReActAgent + 高德天气）✅

> ⚠️ 注意：必须用 **ReActAgent**，需要调用天气工具

- [x] 新建 `backend/app/agents/schedule_agent.py`
- [x] 封装 `WeatherTool(Tool)`，直接通过 httpx 调高德天气 API（因原 `amap_service.py` 已在 Phase 1 删除）
  - 查询区域码 → 获取天气预报（5 天）
  - 自动判断：雨/雪/霾/极端天气 → 室内；好天气 → 户外
- [x] 无 API Key 时降级给出备选建议，不阻塞流程
- [x] Agent 输出 JSON：schedule（每日 focus/location）+ weather_summary

### 任务 2.5：实现 TrainerAgent（SimpleAgent）✅

- [x] 新建 `backend/app/agents/trainer_agent.py`
- [x] 使用 `SimpleAgent`，汇总 ExerciseAgent + DietAgent + ScheduleAgent + 用户信息
- [x] 输出 JSON：weekly_plans（含 warmup/main/cooldown/calories）+ diet

### 任务 2.6：实现 PlanReviewAgent（ReflectionAgent）✅

- [x] 新建 `backend/app/agents/plan_review_agent.py`
- [x] 使用 `ReflectionAgent`，三段 Prompt：
  - `initial`：检查完整性和格式
  - `reflect`：肌群间隔/大肌群顺序/休息日/天气匹配/饮食一致性
  - `refine`：根据反馈修正
- [x] 最多迭代 2 轮，超限直接输出当前版本

### 任务 2.7：实现 FitnessPlanService（核心编排层）✅

- [x] 新建 `backend/app/services/plan_service.py`
- [x] 实现 `FitnessPlanService.generate_plan()` 方法，串行编排 5 个 Agent
- [x] 编排顺序：ExerciseAgent → DietAgent → ScheduleAgent → TrainerAgent → PlanReviewAgent
- [x] 每步有 try/except 捕获异常，单个 Agent 失败不阻塞整体流程
- [x] 内置 `_extract_json()` 函数处理 Agent 输出（代码块/多余文字）
- [x] 最终计划序列化为 JSON 存入 `FitnessPlan.plan_content` 字段

### 任务 2.8：接通 API 路由 ✅

- [x] 更新 `backend/app/api/routes/fitness.py`：
  - `POST /api/fitness/generate` → 调用 `FitnessPlanService.generate_plan()`
  - `GET /api/fitness/plans` → 查询数据库返回列表
  - `GET /api/fitness/plan/{id}` → 查询详情，JSON 解析后展开
- [x] user.py 路由已在 Phase 1 实现写入/读取逻辑

### 任务 2.9：端到端后端测试

- [ ] 用 Swagger UI 或 curl 调用 `POST /api/fitness/generate`，传入：
  ```json
  {
    "goal": "减脂",
    "experience_level": "新手",
    "workout_location": "健身房",
    "days_per_week": 3,
    "duration_weeks": 4,
    "diet_preference": "普通"
  }
  ```
- [ ] 确认返回的 JSON 包含 `weekly_plans`、真实动作数据（有 `image_url`）、饮食建议
- [ ] 确认计划已写入 SQLite 数据库

### ✅ Phase 2 可视化验收

**验收方式：终端日志 + curl/Swagger 响应 + DB Browser**

1. **MCP Server 独立启动** — 单独运行：
   ```bash
   python backend/app/mcp_servers/wger_mcp_server.py
   ```
   终端应显示 `Wger MCP Server running` 类似消息，无报错退出。

2. **Agent 调用日志** — 调用 `POST /api/fitness/generate` 时，后端终端应按顺序打印：
   ```
   [ExerciseAgent] 开始搜索训练动作...
   [DietAgent] 生成饮食建议...
   [ScheduleAgent] 查询天气，编排日程...
   [TrainerAgent] 汇总完整计划...
   [PlanReviewAgent] 第 1 轮审查...
   [PlanReviewAgent] 审查完成，计划已修正
   ```
   （日志内容可以调整，但必须能看到 5 个 Agent 依次执行。）

3. **返回 JSON 结构验收** — 响应 JSON 必须包含：
   ```json
   {
     "id": 1,
     "goal": "减脂",
     "weekly_plans": [
       {
         "week": 1,
         "days": [
           {
             "day": "周一",
             "focus": "胸部",
             "warmup": [...],
             "main": [
               {
                 "name": "卧推",
                 "image_url": "https://wger.de/...",
                 "sets": 3,
                 "reps": 12
               }
             ],
             "cooldown": [...]
           }
         ]
       }
     ],
     "diet": {
       "daily_calories": 1800,
       "meals": {...}
     }
   }
   ```
   **关键验收点：** `image_url` 字段不为空，且以 `https://wger.de/` 开头（证明是真实数据而非 Mock）。

4. **数据库写入验收** — 用 [DB Browser for SQLite](https://sqlitebrowser.org/) 或命令行打开 `backend/fitness.db`：
   ```bash
   sqlite3 backend/fitness.db "SELECT id, goal, created_at FROM fitness_plan;"
   ```
   应看到刚才生成的记录一行，`goal` 为 `减脂`。

5. **Wger 真实数据验证** — 单独测试 `search_exercises` 工具：
   ```bash
   curl "https://wger.de/api/v2/exercise/?format=json&language=2&limit=3"
   ```
   返回有内容的 JSON（证明外部 API 可达）。

**Phase 2 完成标志：** 输入目标 → 后端 5 个 Agent 协作 → 返回含真实动作数据的完整训练计划。

---

## Phase 3：前端改造（Day 5）

### 任务 3.1：更新前端依赖

- [ ] 编辑 `frontend/package.json`，添加：
  - `pinia`（状态管理）
  - `echarts`（进度图表，可选）
  - `vue-echarts`（ECharts Vue 封装，可选）
- [ ] 运行 `npm install`

### 任务 3.2：重写 TypeScript 类型定义

- [ ] 重写 `frontend/src/types/index.ts`，删除所有旅行类型，新增：
  - `UserProfile`
  - `PlanRequest`
  - `ExerciseItem`
  - `DailyWorkout`
  - `WeeklyPlan`
  - `FitnessPlan` / `FitnessPlanSummary`
  - `WorkoutRecord`

### 任务 3.3：改造 API 服务层

- [ ] 改造 `frontend/src/services/api.ts`，替换所有旅行 API 调用，实现：
  - `generatePlan(data: PlanRequest): Promise<FitnessPlanResponse>`
  - `getPlanHistory(): Promise<FitnessPlan[]>`
  - `getPlanDetail(id: number): Promise<FitnessPlan>`
  - `saveRecord(data: RecordRequest): Promise<void>`
  - `getRecords(planId: number): Promise<WorkoutRecord[]>`
  - `getUserProfile(): Promise<UserProfile>`
  - `saveUserProfile(data: UserProfile): Promise<void>`

### 任务 3.4：新增 Pinia Store

- [ ] 新建 `frontend/src/stores/user.ts`，管理用户资料状态
- [ ] 新建 `frontend/src/stores/plan.ts`，管理训练计划状态（含 `isGenerating` / `generationProgress`）
- [ ] 新建 `frontend/src/stores/record.ts`，管理训练记录状态
- [ ] 在 `frontend/src/main.ts` 中挂载 Pinia

### 任务 3.5：改造 App.vue + 路由配置

- [ ] 改造 `frontend/src/App.vue`：删除登录逻辑，加入 `NavBar.vue` 导航栏
- [ ] 改造 `frontend/src/router/index.ts`，配置路由：
  - `/` → `Home.vue`（个人设定）
  - `/plan` → `Plan.vue`（训练计划）
  - `/plan/:id` → `Plan.vue`（历史计划详情）
  - `/record` → `Record.vue`（训练记录）
  - `/progress` → `Progress.vue`（进度图表，可选）

### 任务 3.6：新建 NavBar.vue 组件

- [ ] 新建 `frontend/src/components/NavBar.vue`
- [ ] 包含四个导航项：个人设定 / 训练计划 / 训练记录 / 进度
- [ ] 高亮当前激活路由

### 任务 3.7：改造 Home.vue（个人设定页）

- [ ] 大改 `frontend/src/views/Home.vue`，替换旅行表单为健身目标表单：
  - 身高 / 体重 / 年龄 / 性别
  - 健身目标（减脂/增肌/塑形/保持健康）
  - 经验等级（新手/中级/高级）
  - 训练地点（健身房/居家/户外）
  - 每周训练天数（2-6）+ 计划周数（4-12）
  - 饮食偏好（普通/素食/高蛋白/低碳水）
  - 健康备注（文本输入）
- [ ] 点击「生成计划」→ 调用 `generatePlan()` → 显示加载状态 → 跳转 `/plan`

### 任务 3.8：新建 ExerciseItem.vue 组件

- [ ] 新建 `frontend/src/components/ExerciseItem.vue`
- [ ] 展示单个动作：名称 / 目标肌群 / 组数×次数 / 重量建议 / 训练说明 / 教学图片

### 任务 3.9：新建 PlanCard.vue 组件

- [ ] 新建 `frontend/src/components/PlanCard.vue`
- [ ] 展示单日训练卡片：
  - 训练焦点（胸/背/腿/肩/手臂/有氧）
  - 热身区（ExerciseItem 列表）
  - 主训练区（ExerciseItem 列表）
  - 冷身区（ExerciseItem 列表）
  - 预计消耗卡路里

### 任务 3.10：新建 DietTips.vue 组件

- [ ] 新建 `frontend/src/components/DietTips.vue`
- [ ] 展示当日饮食建议：热量目标 / 三餐推荐 / 营养建议

### 任务 3.11：改造 Plan.vue（训练计划展示页）

- [ ] 改造（原 `Result.vue`）为 `frontend/src/views/Plan.vue`
- [ ] 布局：
  - 顶部：计划概览卡片（目标/周期/每周天数）
  - 中部：周切换 Tab（Week 1 / Week 2 / ...）
  - 主体：当周每日 PlanCard 列表
  - 底部：DietTips 当日饮食建议
- [ ] 无计划时显示「还没有计划，去个人设定生成」跳转按钮

### 任务 3.12：新建 Record.vue（训练记录页）

- [ ] 新建 `frontend/src/views/Record.vue`
- [ ] 包含两部分：
  - 上方：RecordForm 记录表单
  - 下方：历史记录列表（按日期倒序）

### 任务 3.13：新建 RecordForm.vue 组件

- [ ] 新建 `frontend/src/components/RecordForm.vue`
- [ ] 表单字段：
  - 选择计划（下拉，从历史计划中选）
  - 选择日期
  - 动作名称
  - 目标肌群
  - 计划组数/次数 vs 实际组数/次数/重量
  - 难度评分（1-5 星）
  - 备注
- [ ] 提交后调用 `saveRecord()`，刷新历史记录列表

### 任务 3.14：新建 Progress.vue（进度图表页，可选）

- [ ] 新建 `frontend/src/views/Progress.vue`
- [ ] 使用 ECharts 展示：
  - 每周训练次数趋势折线图
  - 重量变化曲线（按动作筛选）
  - 训练部位分布饼图

### 任务 3.15：前端联调验证

- [ ] 启动前端 `npm run dev`
- [ ] 完整走通主流程：填写信息 → 生成计划 → 查看计划 → 记录训练
- [ ] 确认动作教学图片正常展示
- [ ] 确认加载状态（AI 生成中）正常显示

### ✅ Phase 3 可视化验收

**验收方式：浏览器截图（每页至少看一眼）**

1. **首页（`/`）个人设定页** — 浏览器打开 `http://localhost:5173`，应看到：
   - 页面顶部有导航栏，包含「个人设定 / 训练计划 / 训练记录」
   - 表单包含：身高、体重、年龄、性别、目标（下拉）、经验等级（下拉）、训练地点（下拉）、每周天数、计划周数、饮食偏好
   - 底部有「生成计划」按钮，颜色明显

2. **生成中加载状态** — 点击「生成计划」后，按钮区域应出现加载动画（Spinner 或进度条），文字变为「AI 生成中…」或类似提示，期间按钮不可重复点击。

3. **计划展示页（`/plan`）** — 生成完成后自动跳转，页面应包含：
   - 顶部：计划概览卡片，显示「目标：减脂 | 周期：4 周 | 每周 3 天」
   - 周次切换 Tab：「Week 1」「Week 2」「Week 3」「Week 4」
   - 每日训练卡片（PlanCard），包含：
     - 训练焦点标签（如「胸部 + 三头」）
     - 热身区：2-3 个动作列表
     - 主训练区：3-5 个动作，每个动作显示名称 + 组数×次数
     - **动作教学图片**（来自 wger.de 的真实图片，非占位图）
   - 底部：当日饮食建议（热量目标 + 三餐推荐）

4. **训练记录页（`/record`）** — 点击导航「训练记录」，应看到：
   - 上方：记录表单（计划下拉 + 日期 + 动作名 + 组数次数重量 + 难度评分）
   - 下方：历史记录列表（初始为空，提示「暂无记录」）

5. **无计划时的提示** — 清空数据库后访问 `/plan`，页面显示「还没有计划，去个人设定生成」，并有跳转按钮。

**Phase 3 完成标志：** 前端完整可交互，用户可以填表生成计划并查看。

---

## Phase 4：ReflectionAgent 打磨 & 训练记录功能（Day 6）

### 任务 4.1：调优 PlanReviewAgent

- [ ] 测试 ReflectionAgent 输出质量，检查是否发现以下问题：
  - 同一肌群连续两天训练（违反 48 小时原则）
  - 下雨天安排户外训练
  - 一周无休息日
- [ ] 如审查效果不理想，调整 `reflect` prompt 的检查项描述
- [ ] 确认修正后的计划质量提升

### 任务 4.2：训练记录后端接口完善

- [ ] 完善 `backend/app/api/routes/record.py`：
  - `POST /api/fitness/record`：写入 `WorkoutRecord` 表
  - `GET /api/fitness/records?plan_id=X`：按计划查询记录，支持按日期过滤
- [ ] 添加基础统计接口（可选）：`GET /api/fitness/stats`，返回每周训练次数统计

### 任务 4.3：前后端训练记录联调

- [ ] 在 Record.vue 页面完整测试：提交记录 → 数据库写入 → 列表刷新
- [ ] 确认历史记录按日期倒序展示
- [ ] 确认难度评分（1-5）正确存储和展示

### ✅ Phase 4 可视化验收

**验收方式：浏览器操作 + 终端日志 + DB 查询**

1. **PlanReviewAgent 修正日志** — 调用生成接口时，终端应出现：
   ```
   [PlanReviewAgent] 第 1 轮反思：发现问题 - 周二/周三连续训练背部
   [PlanReviewAgent] 修正中...
   [PlanReviewAgent] 第 2 轮反思：无新问题，输出最终计划
   ```
   如果首次计划没有问题，则显示「第 1 轮反思：计划符合规则，无需修正」。

2. **训练记录提交验收** — 在记录页填写并提交：
   - 选择已生成的计划
   - 日期选今天
   - 动作名：「卧推」，实际组数：3，实际次数：12，重量：60kg，难度：4 星
   - 点击提交后，下方历史列表立即出现刚才的记录（无需刷新页面）

3. **数据库记录验证** — 执行：
   ```bash
   sqlite3 backend/fitness.db "SELECT exercise_name, actual_sets, actual_reps, weight, difficulty FROM workout_record ORDER BY date DESC LIMIT 5;"
   ```
   应看到「卧推 | 3 | 12 | 60.0 | 4」一行。

4. **难度评分显示验收** — 历史记录列表中，难度 4 星应显示为「★★★★☆」或数字「4/5」，而非原始数字。

**Phase 4 完成标志：** 训练完可记录，数据持久化，ReflectionAgent 能发现并修正计划逻辑问题。

---

## Phase 5：测试 & 收尾（Day 7）

### 任务 5.1：编写后端 Smoke Test

- [ ] 新建 `backend/tests/test_api.py`，覆盖：
  - `POST /api/user/profile` — 创建用户
  - `POST /api/fitness/generate` — 生成训练计划（核心链路）
  - `POST /api/fitness/record` — 写入训练记录
  - `GET /api/fitness/records` — 查询记录
- [ ] 运行 `pytest backend/tests/` 全绿

### 任务 5.2：清理残留代码

- [ ] 删除所有旅行相关文件（trip、attraction、hotel、map、poi、unsplash 相关）
- [ ] 删除所有 `__pycache__` 目录
- [ ] 删除前端旧组件（旅行结果展示等）
- [ ] 检查所有 `import` 语句无悬空引用

### 任务 5.3：验证从零启动流程

- [ ] 模拟全新环境，按以下步骤验证能跑起来：
  ```bash
  git clone <repo>
  cd backend && pip install -r requirements.txt
  uvicorn app.api.main:app --reload
  # 新终端
  cd frontend && npm install && npm run dev
  ```
- [ ] 确认无需额外配置即可访问 `http://localhost:5173`

### 任务 5.4：编写 README.md

- [ ] 新建项目根目录 `README.md`，包含：
  - 项目一句话介绍
  - 技术亮点（三种 Agent 范式 / 自建 Wger MCP / ReflectionAgent）
  - 快速启动步骤（后端 + 前端）
  - 环境变量说明（需要哪些 Key）
  - 项目截图（至少首页 + 计划展示页）
  - 架构图（可直接引用 design.md 中的 ASCII 图）

### 任务 5.5：最终演示验证

- [ ] 完整走通演示流程：
  1. 打开首页，填写健身目标（减脂 / 新手 / 健身房 / 3天/周 / 4周）
  2. 点击生成，等待 5-15 秒，观察加载提示
  3. 跳转计划页，切换周次，展开动作详情，查看教学图片
  4. 去记录页，记录一次训练
  5. 查看历史记录列表
- [ ] 确认整个流程无报错，UI 无明显异常

### ✅ Phase 5 可视化验收（最终验收）

**验收方式：全流程录屏或逐页截图**

1. **pytest 全绿截图** — 运行 `pytest backend/tests/ -v` 后终端应显示：
   ```
   test_create_user_profile PASSED
   test_generate_fitness_plan PASSED
   test_save_workout_record PASSED
   test_get_workout_records PASSED

   4 passed in X.XXs
   ```
   无 FAILED / ERROR。

2. **从零启动验证** — 在新终端按以下步骤执行，全程无报错：
   ```bash
   # 终端 1
   cd backend && pip install -r requirements.txt
   uvicorn app.api.main:app --reload
   # 出现 "Application startup complete." 即可

   # 终端 2
   cd frontend && npm install && npm run dev
   # 出现 "Local: http://localhost:5173/" 即可
   ```

3. **完整演示流程截图清单**（每步截图留存）：
   | 步骤 | 截图内容 | 验收标准 |
   |------|----------|----------|
   | ① 首页填表 | 表单已填写，目标=减脂，地点=健身房 | 所有字段有值，按钮可点击 |
   | ② 生成中 | 加载动画 + 「AI 生成中」文字 | Spinner 可见，按钮灰色不可点 |
   | ③ 计划页总览 | 4 个 Week Tab，第1周日程卡片 | Tab 切换正常，卡片有真实动作名 |
   | ④ 动作详情 | 卧推/深蹲等动作，含教学图片 | 图片来自 wger.de，非占位图 |
   | ⑤ 记录页提交 | 填完表单，点提交，列表更新 | 新记录出现在列表顶部 |
   | ⑥ 历史记录 | 含日期、动作名、难度星级 | 按日期倒序，难度显示正确 |

4. **代码干净度检查** — 运行：
   ```bash
   grep -r "trip\|hotel\|attraction\|travel\|unsplash" backend/ frontend/src/
   ```
   **期望输出：无任何匹配行**（旅行残留代码已全部清除）。

5. **README 验收** — 打开 `README.md`，应包含：
   - 项目截图（至少首页 + 计划页）
   - 快速启动命令可以直接复制粘贴执行

**Phase 5 完成标志：** 项目可演示，README 完整，代码干净无旅行残留。

---

## 关键约束备忘

| 约束 | 说明 |
|------|------|
| ExerciseAgent / ScheduleAgent 必须用 ReActAgent | SimpleAgent 不支持工具调用，写了不会生效 |
| PlanReviewAgent 用 ReflectionAgent | 只做内容审查，不需要工具 |
| Wger API 无需 Key | `https://wger.de/api/v2/` 只读接口全部免认证 |
| wger 字段名 | API 返回 `variation_group`（UUID），不是 `variations` |
| Agent 间无直接通信 | 所有编排逻辑在 `plan_service.py` 的后端代码中完成 |
| MCP 工具需包装为 ToolRegistry Tool | HelloAgents 框架没有原生 MCP 支持，需要中间适配层 |

---

## 任务完成状态追踪

| Phase | 状态 |
|-------|------|
| Phase 1：后端骨架 | ✅ 已完成 |
| Phase 2：Agent + MCP | ✅ 代码已实现（待端到端测试） |
| Phase 3：前端改造 | ⬜ 未开始 |
| Phase 4：调优 + 记录功能 | ⬜ 未开始 |
| Phase 5：测试 + 收尾 | ⬜ 未开始 |
