# Phase 工具映射表

> 列出每个 Phase 的具体任务所需 Skills 和 MCP 工具。

---

## Phase 1：项目初始化 & 后端骨架（Day 1-2）

| 任务 | Skills | MCP 工具 |
|------|--------|----------|
| 1.1 复制目录结构、删旅行残留 | `file-organizer`（整理目录）<br>`file-search`（查找残留文件） | `Filesystem`（list/move/delete 文件） |
| 1.2 后端依赖更新（requirements.txt） | — | `Filesystem`（read/write 文件）<br>`VS Code IDE`（运行 pip install） |
| 1.3 配置 .env 环境变量 | — | `Filesystem`（read/write .env） |
| 1.4 数据库 ORM 模型建立 | `writing-plans`（建模前先规划字段） | `Filesystem`（write orm_models.py）<br>`VS Code IDE`（语法诊断） |
| 1.5 Pydantic Schema 定义 | — | `Filesystem`（write schemas.py）<br>`VS Code IDE`（getDiagnostics 检查类型错误） |
| 1.6 API 路由骨架 | — | `Filesystem`（write 路由文件）<br>`VS Code IDE`（运行/诊断） |
| 1.7 验证后端可启动 | `verify`（运行后端、截图 Swagger UI） | `Playwright`（打开 localhost:8000/docs 截图验收） |

**Phase 1 核心工具组合：** `Filesystem` + `VS Code IDE` + `Playwright`（验收用）

---

## Phase 2：Agent 改造 & MCP 集成（Day 3-4）

| 任务 | Skills | MCP 工具 |
|------|--------|----------|
| 2.1 ✅ 自建 Wger MCP Server | `mcp-builder`（按官方指南构建 MCP Server） | `Filesystem`（write wger_mcp_server.py）<br>`wger`（验证字段：exerciseinfo 端点含 translations/images） |
| 2.2 ✅ ExerciseAgent（ReActAgent） | — | `Filesystem`（write exercise_agent.py）<br>**注意：** hello_agents 无 MCPTool，Tool 直接包装 REST API 调 wger |
| 2.3 ✅ DietAgent（SimpleAgent） | — | `Filesystem`（write diet_agent.py） |
| 2.4 ✅ ScheduleAgent（ReActAgent + 高德天气） | — | `Filesystem`（write schedule_agent.py）<br>**注意：** amap_service.py 已在 Phase 1 删除，WeatherTool 直接 httpx 调高德 API |
| 2.5 ✅ TrainerAgent（SimpleAgent） | — | `Filesystem`（write trainer_agent.py） |
| 2.6 ✅ PlanReviewAgent（ReflectionAgent） | — | `Filesystem`（write plan_review_agent.py） |
| 2.7 ✅ FitnessPlanService 编排层 | — | `Filesystem`（write plan_service.py） |
| 2.8 ✅ 接通 API 路由 | — | `Filesystem`（更新 fitness.py 调 generate_plan） |
| 2.9 端到端后端测试 | `verify`（调用 generate 接口，验证 5 Agent 日志） | `Playwright`（Swagger UI 发请求、截图验收） |

**Phase 2 核心工具组合：** `wger` + `Filesystem` + `VS Code IDE` + `Playwright`（验收）+ `Exa`（查 API 文档）

---

## Phase 3：前端改造（Day 5）

| 任务 | Skills | MCP 工具 |
|------|--------|----------|
| 3.1 前端依赖更新（pinia/echarts） | — | `Filesystem`（edit package.json）<br>`VS Code IDE`（run npm install） |
| 3.2 重写 TypeScript 类型定义 | — | `Filesystem`（rewrite types/index.ts）<br>`VS Code IDE`（getDiagnostics 检查类型） |
| 3.3 改造 API 服务层 | — | `Filesystem`（rewrite api.ts） |
| 3.4 新增 Pinia Store（3 个） | `writing-plans`（规划 store 结构） | `Filesystem`（write user/plan/record store）<br>`VS Code IDE`（诊断） |
| 3.5 App.vue + 路由配置 | `ui-ux-pro-max`（NavBar 设计） | `Filesystem`（edit App.vue、router/index.ts） |
| 3.6 NavBar.vue 组件 | `ui-ux-pro-max`（导航栏样式/高亮激活态） | `Filesystem`（write NavBar.vue） |
| 3.7 Home.vue（个人设定页表单） | `ui-ux-pro-max`（表单布局、加载状态动画） | `Filesystem`（rewrite Home.vue）<br>`VS Code IDE`（诊断） |
| 3.8 ExerciseItem.vue 组件 | `ui-ux-pro-max`（动作卡片展示，含图片） | `Filesystem`（write ExerciseItem.vue） |
| 3.9 PlanCard.vue 组件 | `ui-ux-pro-max`（每日训练卡片布局） | `Filesystem`（write PlanCard.vue） |
| 3.10 DietTips.vue 组件 | `ui-ux-pro-max`（饮食建议展示） | `Filesystem`（write DietTips.vue） |
| 3.11 Plan.vue 改造（计划展示页） | `ui-ux-pro-max`（Tab 切换、周计划布局） | `Filesystem`（rewrite Plan.vue） |
| 3.12 Record.vue 训练记录页 | `ui-ux-pro-max`（表单 + 历史列表布局） | `Filesystem`（write Record.vue） |
| 3.13 RecordForm.vue 组件 | `ui-ux-pro-max`（星级评分组件） | `Filesystem`（write RecordForm.vue） |
| 3.14 Progress.vue 进度图表（可选） | `ui-ux-pro-max`（ECharts 折线图/饼图） | `Filesystem`（write Progress.vue） |
| 3.15 前端联调验证 | `verify`（运行前端，截图验收全流程） | `Playwright`（打开 localhost:5173，逐页截图）<br>`VS Code IDE`（控制台错误检查） |

**Phase 3 核心工具组合：** `ui-ux-pro-max`（所有 Vue 组件）+ `Filesystem` + `Playwright`（验收）

---

## Phase 4：ReflectionAgent 打磨 & 训练记录功能（Day 6）

| 任务 | Skills | MCP 工具 |
|------|--------|----------|
| 4.1 调优 PlanReviewAgent Prompt | `systematic-debugging`（分析审查失败案例）<br>`code-review`（审查三段 prompt 质量） | `VS Code IDE`（运行测试验证输出）<br>`Filesystem`（edit plan_review_agent.py） |
| 4.2 训练记录后端接口完善 | — | `Filesystem`（edit record.py）<br>`VS Code IDE`（运行验证） |
| 4.3 前后端训练记录联调 | `verify`（提交记录 → DB 写入 → 列表刷新） | `Playwright`（在浏览器操作记录页，验收数据更新） |

**Phase 4 核心工具组合：** `systematic-debugging` + `Playwright`（验收）+ `VS Code IDE`

---

## Phase 5：测试 & 收尾（Day 7）

| 任务 | Skills | MCP 工具 |
|------|--------|----------|
| 5.1 编写后端 Smoke Test | `test-driven-development`（编写 pytest 测试） | `Filesystem`（write tests/test_api.py）<br>`VS Code IDE`（run pytest） |
| 5.2 清理残留旅行代码 | `simplify`（清理无用代码）<br>`file-search`（搜索 trip/hotel/attraction 残留） | `Filesystem`（delete 文件）<br>`VS Code IDE`（grep 验证无残留） |
| 5.3 验证从零启动流程 | `verify`（按 clone→install→run 顺序验证） | `Playwright`（最终截图验收） |
| 5.4 编写 README.md | `document-writer`（撰写项目文档） | `Filesystem`（write README.md）<br>`Playwright`（截图首页 + 计划页用于 README） |
| 5.5 最终演示验证（全流程） | `verify`（完整演示流程截图） | `Playwright`（逐步截图：填表→生成→计划→记录）<br>`GitHub`（提交最终代码） |

**Phase 5 核心工具组合：** `verify` + `Playwright`（截图）+ `GitHub`（收尾提交）

---

## 工具总用量一览

| 工具/技能 | 使用 Phase |
|-----------|-----------|
| `Filesystem` | 1-5 全程（读写文件主力） |
| `VS Code IDE` | 1-5 全程（运行/诊断主力） |
| `Playwright` | 1、2、3、4、5（所有验收节点） |
| `wger` MCP | Phase 2（验证 ExerciseAgent 数据） |
| `ui-ux-pro-max` | Phase 3（所有前端组件） |
| `verify` skill | 1.7、2.9、3.15、4.3、5.3、5.5 |
| `mcp-builder` skill | Phase 2（构建 Wger MCP Server） |
| `deep-research` / `Exa` | 2.1（查 wger API 文档） |
| `document-writer` | 5.4（README） |
| `GitHub` MCP | 5.5（最终提交） |
| `writing-plans` | 1.4、2.1、2.6、3.4 |
| `simplify` / `code-review` | 5.2、4.1 |
