# 执行速查文档

> plan.md 精简引用版，每步标注所需工具，方便直接执行。
> 详细工具映射见 `phase-tools-map.md`。

---

## Phase 1：后端骨架（Day 1-2）

**目标：** 后端能启动，6 条 API 路由存在，SQLite 数据库自动创建。

| # | 做什么 | 工具 |
|---|--------|------|
| 1.1 | 复制 trip-planner 目录 → 建 `backend/` `frontend/`，删旅行残留文件 | `Filesystem` `file-organizer` |
| 1.2 | 确认 requirements.txt 含 fastapi/uvicorn/sqlalchemy/fastmcp 等 9 个包 | `Filesystem` `VS Code IDE` |
| 1.3 | 配置 `backend/.env`（LLM Key + AMAP Key） | `Filesystem` |
| 1.4 | 新建 `orm_models.py`：User / FitnessPlan / WorkoutRecord 三张表 | `Filesystem` `VS Code IDE` |
| 1.5 | 新建 `schemas.py`：UserProfile / PlanRequest / ExerciseItem 等 7 个模型 | `Filesystem` `VS Code IDE` |
| 1.6 | 新建 user/fitness/record 三个路由文件（先返回占位数据），挂载 CORS | `Filesystem` |
| 1.7 ✅ | 运行 `uvicorn app.api.main:app --reload`，验收 Swagger UI 截图 | `verify` `Playwright` |

**验收标志：** Swagger 显示 6 个路由 + `fitness.db` 文件出现。

---

## Phase 2：Agent + MCP（Day 3-4）

**目标：** 输入目标 → 5 个 Agent 协作 → 返回含 wger 真实图片的训练计划 JSON。

| # | 做什么 | 工具 |
|---|--------|------|
| 2.1 | 新建 `wger_mcp_server.py`，用 fastmcp 包装 7 个只读工具（无需 Key） | `wger` `Exa` `Filesystem` |
| 2.2 | `ExerciseAgent`：**ReActAgent** + ToolRegistry，搜真实动作，输出含 image_url | `wger` `systematic-debugging` `Filesystem` |
| 2.3 | `DietAgent`：SimpleAgent，纯 LLM 生成热量/三餐/营养比例 JSON | `Filesystem` |
| 2.4 | `ScheduleAgent`：**ReActAgent** + WeatherTool（高德），查天气→编排日程 | `systematic-debugging` `Filesystem` |
| 2.5 | `TrainerAgent`：SimpleAgent，汇总 3 个 Agent 结果 → 完整计划 JSON | `Filesystem` |
| 2.6 | `PlanReviewAgent`：ReflectionAgent，3 段 Prompt（检查→反思→修正），最多迭代 2 轮 | `Filesystem` |
| 2.7 | `plan_service.py`：串行编排 5 个 Agent（1→2→3→4→5），结果存 DB | `Filesystem` `VS Code IDE` |
| 2.8 | 路由接通：fitness.py 调 `generate_plan()`，user.py 读写 User 表 | `Filesystem` |
| 2.9 ✅ | curl/Swagger 调 generate，验收：5 Agent 日志 + image_url 含 wger.de + DB 写入 | `verify` `Playwright` `wger` |

**关键约束：**
- ExerciseAgent / ScheduleAgent → **必须 ReActAgent**（SimpleAgent 不支持工具）
- Wger 字段：`variation_group`（UUID），**不是** `variations`
- MCP 工具需包装为 ToolRegistry Tool（HelloAgents 无原生 MCP 支持）

**验收标志：** 终端出现 5 Agent 日志顺序打印 + JSON 含真实 wger.de 图片。

---

## Phase 3：前端改造（Day 5）

**目标：** 前端完整可交互，用户能填表生成计划并查看。

| # | 做什么 | 工具 |
|---|--------|------|
| 3.1 | package.json 添加 pinia / echarts / vue-echarts，npm install | `Filesystem` `VS Code IDE` |
| 3.2 | 重写 `types/index.ts`，删旅行类型，加 7 个健身类型 | `Filesystem` `VS Code IDE` |
| 3.3 | 重写 `api.ts`，实现 7 个 API 方法（generatePlan/getPlanHistory 等） | `Filesystem` |
| 3.4 | 新建 user/plan/record 三个 Pinia Store，挂载到 main.ts | `Filesystem` |
| 3.5 | App.vue 加 NavBar，router 配置 4 条路由（`/` `/plan` `/plan/:id` `/record`） | `Filesystem` `ui-ux-pro-max` |
| 3.6 | NavBar.vue：4 个导航项，高亮激活路由 | `ui-ux-pro-max` `Filesystem` |
| 3.7 | Home.vue：健身目标表单（10 个字段），生成中加载状态，完成跳 `/plan` | `ui-ux-pro-max` `Filesystem` |
| 3.8 | ExerciseItem.vue：展示动作名/肌群/组数/重量/图片 | `ui-ux-pro-max` `Filesystem` |
| 3.9 | PlanCard.vue：每日训练卡片（热身+主训+冷身+消耗卡路里） | `ui-ux-pro-max` `Filesystem` |
| 3.10 | DietTips.vue：热量目标 + 三餐推荐 | `ui-ux-pro-max` `Filesystem` |
| 3.11 | Plan.vue：计划概览卡 + 周 Tab + PlanCard 列表 + DietTips | `ui-ux-pro-max` `Filesystem` |
| 3.12 | Record.vue：RecordForm（上）+ 历史列表（下） | `ui-ux-pro-max` `Filesystem` |
| 3.13 | RecordForm.vue：下拉计划/日期/动作/组次重量/难度星级 | `ui-ux-pro-max` `Filesystem` |
| 3.14 | Progress.vue（可选）：ECharts 折线图/饼图 | `ui-ux-pro-max` `Filesystem` |
| 3.15 ✅ | `npm run dev`，浏览器走完主流程，确认图片/加载状态正常 | `verify` `Playwright` |

**验收标志：** localhost:5173 可交互，计划页出现 wger.de 真实图片。

---

## Phase 4：打磨 & 记录功能（Day 6）

**目标：** ReflectionAgent 能发现逻辑问题并修正，训练记录可持久化。

| # | 做什么 | 工具 |
|---|--------|------|
| 4.1 | 测试 PlanReviewAgent：检查连续肌群/无休息日/天气冲突，调整 reflect prompt | `systematic-debugging` `code-review` `Filesystem` |
| 4.2 | 完善 `record.py`：POST 写入 WorkoutRecord，GET 按 plan_id 过滤；可选 stats 接口 | `Filesystem` `VS Code IDE` |
| 4.3 ✅ | Record.vue 联调：提交→DB 写入→列表实时刷新，难度显示为星级 | `verify` `Playwright` |

**验收标志：** 终端出现 `[PlanReviewAgent] 第 N 轮反思` 日志；DB 写入验证（sqlite3 查询）。

---

## Phase 5：测试 & 收尾（Day 7）

**目标：** pytest 全绿，代码无旅行残留，README 完整，项目可演示。

| # | 做什么 | 工具 |
|---|--------|------|
| 5.1 | 新建 `tests/test_api.py`：4 个 smoke test（user/generate/record/records），pytest 全绿 | `test-driven-development` `VS Code IDE` |
| 5.2 | 删除 trip/hotel/attraction/unsplash 相关所有文件和代码，`__pycache__` 清理 | `simplify` `file-search` `Filesystem` |
| 5.3 | 模拟从零启动：git clone → pip install → uvicorn → npm install → npm dev，全程无错 | `verify` `Playwright` |
| 5.4 | 写 README.md：一句话介绍/技术亮点/快速启动/env 说明/截图/架构图 | `document-writer` `Filesystem` `Playwright` |
| 5.5 ✅ | 完整演示流程：填表→生成→计划→记录→历史；最终 push | `verify` `Playwright` `GitHub` |

**最终验收清单（截图留存）：**

| 截图 | 关键验收点 |
|------|-----------|
| pytest 4 passed | 无 FAILED/ERROR |
| 首页填表 | 10 个字段均有输入，按钮可点 |
| 生成中 Spinner | 按钮灰色不可重点 |
| 计划页 4 个 Week Tab | 动作名真实，非 Mock |
| wger.de 教学图片 | 非占位图 |
| 记录提交后列表更新 | 无需刷新页面 |
| 历史记录倒序+星级 | 难度显示为 ★ |

**Phase 5 完成标志：** pytest 全绿 + 无旅行残留（`grep -r "trip\|hotel\|attraction"` 无输出）+ README 可直接复制执行。
