# Fitness Planner — 任务流程文档

> 基于 `design.md` 整理，按实施顺序逐步执行。
> 所有改造基于 `helloagents-trip-planner/` 原项目进行。

---

## Phase 1：项目初始化 & 后端骨架（Day 1-2）

### 任务 1.1：复制原项目，建立新目录结构

- [ ] 在 `fitness-plan/` 下创建 `backend/` 和 `frontend/` 目录（从原项目复制）
- [ ] 复制 `helloagents-trip-planner/backend/` → `fitness-plan/backend/`
- [ ] 复制 `helloagents-trip-planner/frontend/` → `fitness-plan/frontend/`
- [ ] 删除所有旅行相关残留（trip、attraction、hotel 相关文件名和代码）

### 任务 1.2：后端依赖更新

- [ ] 打开 `backend/requirements.txt`，确认以下包存在（没有则添加）：
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
- [ ] 运行 `pip install -r requirements.txt` 确认安装成功

### 任务 1.3：配置环境变量

- [ ] 编辑 `backend/.env`，确保包含：
  ```
  # LLM 配置（从原项目复制）
  LLM_API_KEY=your_key
  LLM_BASE_URL=your_base_url
  LLM_MODEL=your_model

  # 高德地图 API Key（从原项目复制）
  AMAP_API_KEY=your_amap_key
  ```
- [ ] 确认 `backend/app/config.py` 能读取上述变量

### 任务 1.4：数据库模型建立

- [ ] 新建 `backend/app/models/orm_models.py`，实现三张表：
  - `User`（用户资料：身高/体重/年龄/性别/目标/经验）
  - `FitnessPlan`（训练计划：目标快照/周数/天数/地点/饮食偏好/计划内容 JSON）
  - `WorkoutRecord`（训练记录：计划ID/日期/动作名/组数次数重量/难度评分）
- [ ] 在 `backend/app/database.py` 中配置 SQLite 连接和 `Base.metadata.create_all()`

### 任务 1.5：Pydantic API Schema 定义

- [ ] 新建或重写 `backend/app/models/schemas.py`，实现以下模型：
  - `UserProfile`（用户创建/更新）
  - `PlanRequest`（生成计划请求：目标/经验/地点/天数/周数/饮食/备注）
  - `ExerciseItem`（单个训练动作）
  - `DailyWorkout`（每日训练：热身+主训练+冷身）
  - `WeeklyPlan`（每周计划）
  - `FitnessPlanResponse` / `FitnessPlanSummary`（完整计划响应）
  - `RecordRequest`（训练记录请求）

### 任务 1.6：API 路由骨架建立

- [ ] 新建 `backend/app/api/routes/user.py`，注册以下路由（先返回空数据）：
  - `POST /api/user/profile`
  - `GET /api/user/profile`
- [ ] 新建 `backend/app/api/routes/fitness.py`，注册以下路由（先返回占位数据）：
  - `POST /api/fitness/generate`
  - `GET /api/fitness/plans`
  - `GET /api/fitness/plan/{id}`
- [ ] 新建 `backend/app/api/routes/record.py`，注册以下路由：
  - `POST /api/fitness/record`
  - `GET /api/fitness/records`
- [ ] 更新 `backend/app/api/main.py`，挂载所有路由，配置 CORS

### 任务 1.7：验证后端可启动

- [ ] 运行 `uvicorn app.api.main:app --reload`
- [ ] 打开 `http://localhost:8000/docs`，确认所有路由出现在 Swagger UI 中
- [ ] 访问 `POST /api/user/profile`，确认接口可调通（返回占位响应即可）

**Phase 1 完成标志：** 后端可启动，所有 API 路由存在，数据库文件自动创建。

---

## Phase 2：Agent 改造 & MCP 集成（Day 3-4）

### 任务 2.1：自建 Wger MCP Server

- [ ] 新建 `backend/app/mcp_servers/wger_mcp_server.py`
- [ ] 使用 `fastmcp` 实现以下工具（所有工具只读，无需 API Key）：
  - `list_categories` — 列出所有动作分类
  - `list_muscles` — 列出所有肌群（含图片 URL）
  - `list_equipment` — 列出所有器材类型
  - `search_exercises` — 按肌群/器材/关键词/分类搜索动作（参数：query/muscle/equipment/category/limit/offset）
  - `get_exercise_details` — 获取单个动作完整详情（参数：exercise_id）
  - `get_exercise_images` — 获取动作教学图片列表（参数：exercise_id）
  - `get_exercise_videos` — 获取动作演示视频列表（参数：exercise_id）
- [ ] 所有工具底层用 `httpx` 请求 `https://wger.de/api/v2/`
- [ ] 注意字段映射：API 返回 `variation_group`（UUID），不是 `variations`（number）
- [ ] 本地测试：`python backend/app/mcp_servers/wger_mcp_server.py` 能启动，无报错

### 任务 2.2：实现 ExerciseAgent（ReActAgent + Wger MCP）

> ⚠️ 注意：必须用 **ReActAgent**，SimpleAgent 无法调用工具

- [ ] 新建 `backend/app/agents/exercise_agent.py`
- [ ] 使用 `ReActAgent` + `ToolRegistry` 注册 Wger 工具
- [ ] 封装一个 `WgerSearchTool(Tool)` 类，内部调用 Wger MCP Server 或直接调 wger REST API
- [ ] 编写 `EXERCISE_AGENT_PROMPT`，告知 Agent 可用工具和返回格式要求
- [ ] Agent 输出格式：JSON 数组，每项包含 `name / target_muscle / category / sets / reps / rest_seconds / weight_suggestion / description / image_url`

### 任务 2.3：实现 DietAgent（SimpleAgent）

- [ ] 新建 `backend/app/agents/diet_agent.py`
- [ ] 使用 `SimpleAgent`，纯 LLM 知识生成饮食建议（无需工具）
- [ ] 输入：目标（减脂/增肌/塑形）+ 饮食偏好（普通/素食/高蛋白/低碳水）
- [ ] 输出：JSON，包含每日热量目标、三餐建议、营养比例

### 任务 2.4：实现 ScheduleAgent（ReActAgent + 高德天气）

> ⚠️ 注意：必须用 **ReActAgent**，需要调用天气工具

- [ ] 新建 `backend/app/agents/schedule_agent.py`
- [ ] 将高德天气查询封装为 `WeatherTool(Tool)`（参考原项目 `amap_service.py` 的调用方式）
- [ ] 使用 `ReActAgent` + `ToolRegistry` 注册 WeatherTool
- [ ] Agent 职责：查询城市天气 → 根据天气决定室内/户外 → 编排每周日程
- [ ] 输出：JSON，包含每周每天的训练重点和地点建议

### 任务 2.5：实现 TrainerAgent（SimpleAgent）

- [ ] 新建 `backend/app/agents/trainer_agent.py`
- [ ] 使用 `SimpleAgent`，职责是汇总所有子 Agent 的结果，输出完整训练计划
- [ ] 输入：ExerciseAgent 结果 + DietAgent 结果 + ScheduleAgent 结果 + 用户信息
- [ ] 输出：符合 `FitnessPlanSummary` 结构的 JSON

### 任务 2.6：实现 PlanReviewAgent（ReflectionAgent）

- [ ] 新建 `backend/app/agents/plan_review_agent.py`
- [ ] 使用 `ReflectionAgent`（不需要工具，只做内容审查）
- [ ] 实现三段 Prompt：
  - `initial`：检查计划完整性和格式
  - `reflect`：检查肌群间隔/大肌群顺序/休息日/天气匹配/饮食目标一致性
  - `refine`：根据反思意见修正计划
- [ ] 最多迭代 2 轮，超过则直接输出当前版本

### 任务 2.7：实现 FitnessPlanService（核心编排层）

- [ ] 新建 `backend/app/services/plan_service.py`
- [ ] 实现 `FitnessPlanService.generate_plan(user_input: PlanRequest)` 方法
- [ ] 串行编排顺序：
  1. `ExerciseAgent.run()` — 获取真实训练动作
  2. `DietAgent.run()` — 生成饮食建议
  3. `ScheduleAgent.run()` — 查天气 + 编排日程
  4. `TrainerAgent.run()` — 汇总为完整计划
  5. `PlanReviewAgent.run()` — 自我审查修正
- [ ] 将最终计划序列化存入 `FitnessPlan` 表

### 任务 2.8：接通 API 路由

- [ ] 更新 `backend/app/api/routes/fitness.py`：
  - `POST /api/fitness/generate` 调用 `FitnessPlanService.generate_plan()`
  - `GET /api/fitness/plans` 查询数据库返回历史计划列表
  - `GET /api/fitness/plan/{id}` 查询单个计划详情
- [ ] 更新 `backend/app/api/routes/user.py`：
  - `POST /api/user/profile` 写入 User 表
  - `GET /api/user/profile` 读取 User 表

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
| Phase 1：后端骨架 | ⬜ 未开始 |
| Phase 2：Agent + MCP | ⬜ 未开始 |
| Phase 3：前端改造 | ⬜ 未开始 |
| Phase 4：调优 + 记录功能 | ⬜ 未开始 |
| Phase 5：测试 + 收尾 | ⬜ 未开始 |
