# Phase 5 计划：打通生成计划 + SSE 进度推送 + 动作详情缓存

> 目标：生成计划真正跑通、用户全程有进度反馈、ExerciseDrawer 显示真实图片

---

## 架构决策

### Agent 从 5 个砍到 3 个

**旧架构（太慢，2-4 分钟）：**
```
ExerciseAgent → DietAgent → ScheduleAgent → TrainerAgent → PlanReviewAgent
```

**新架构（目标 40-80 秒）：**
```
ExerciseAgent → ScheduleAgent → PlanAgent
```

| Agent | 类型 | 职责 | 保留原因 |
|-------|------|------|----------|
| ExerciseAgent | ReActAgent | 调 wger 搜真实动作，max_steps=4 | wger 真实数据，简历亮点 |
| ScheduleAgent | ReActAgent | 查高德天气，编排训练日程 | 天气 API，简历亮点 |
| PlanAgent | SimpleAgent | 整合动作+日程，生成完整计划 JSON | 合并原 Trainer+Review |

**去掉的 Agent：**
- `DietAgent`：前端页面没有饮食模块，以后再加
- `PlanReviewAgent`：让 LLM 审查 LLM，效果有限，还多花 30-60 秒

### 进度反馈用 SSE（Server-Sent Events）

后端边执行边推消息，前端实时展示：
```
🔍 正在搜索适合你的训练动作...   ← ExerciseAgent 开始
☀️  查询天气，编排训练日程...     ← ScheduleAgent 开始
📋 AI 教练正在生成完整计划...    ← PlanAgent 开始
✅ 计划生成完成！                 ← 存库完成，推送计划 ID
```

---

## 现状诊断

### 问题 1：前端传参错误

1. `experience_level` 硬编码：`formData.gender === 'male' ? '中级' : '新手'`
   → 应让用户在 StepCardPersonal 里自己选经验水平

2. `workout_location` 把多选地点顿号拼接 `"健身房、居家"`
   → Agent prompt 只认识单一地点，改为取第一个选择

### 问题 2：TrainerAgent 会丢掉 wger_id 和 image_url

ExerciseAgent 搜索时带了 `wger_id`、`image_url`、`description`，
但 TrainerAgent 的输出模板里没有 `wger_id`，LLM 整合时会把它丢掉。
→ PlanAgent 的 prompt 和输出模板必须明确包含这三个字段

### 问题 3：PlanReviewAgent 返回"无需改进"导致计划丢失

```python
reviewed = run_plan_review(trainer_result)
final_plan = reviewed  # 如果返回"无需改进"，_extract_json 解析失败
```
→ 去掉 PlanReviewAgent，问题自然消失

### 问题 4：ExerciseDrawer 图片为空

真实计划生成后 `imageUrl` 大概率是空的（PlanAgent 可能丢字段）。
→ Task 2 用 wger_id + localStorage 缓存方案解决

---

## 实施计划

### Task 1：重构 Agent + SSE 进度推送

**Step 1.1 前端：StepCardPersonal 加经验水平选择**

文件：`frontend/src/components/StepCardPersonal.vue`
- 增加经验水平单选（新手 / 中级 / 高级）
- 把选择结果 emit 给父组件

文件：`frontend/src/views/OnboardingGuide.vue`
- `formData` 加 `experience` 字段
- `experience_level` 改为 `formData.experience`
- `workout_location` 改为 `formData.locations[0] || '健身房'`

**Step 1.2 前端：GeneratingProgress 改为 SSE 接收**

文件：`frontend/src/components/GeneratingProgress.vue`
- 把模拟进度 timer 改为监听 SSE 事件流
- 每收到一条消息就更新显示的文字和进度条

文件：`frontend/src/views/OnboardingGuide.vue`
- `onGenerate` 里改为调 SSE 接口（`EventSource`）
- 收到 `done` 事件时拿 `plan_id`，跳转 `/home`

**Step 1.3 后端：新建 PlanAgent，去掉 DietAgent 和 PlanReviewAgent**

文件：`backend/app/agents/plan_agent.py`（新建，替换 trainer_agent.py）
- 合并原 TrainerAgent 的整合职责
- **只生成一周计划**（减少 LLM 输出 token，提速）
- 输出模板必须包含 `wger_id`、`image_url`、`description`，不得丢失
- 去掉饮食字段

文件：`backend/app/agents/exercise_agent.py`
- `max_steps` 从 8 改为 4

文件：`frontend/src/views/OnboardingGuide.vue`
- `duration_weeks` 固定传 1，不让用户选

文件：`backend/app/agents/exercise_agent.py`
- `max_steps` 从 8 改为 4，减少搜索轮次

**Step 1.4 后端：plan_service 改为 SSE 流式接口**

文件：`backend/app/api/routes/fitness.py`
- `/api/fitness/generate` 改为返回 `StreamingResponse`（SSE 格式）
- 每个 Agent 开始前推一条进度消息
- 最后推 `{"event": "done", "plan_id": 123}`

文件：`backend/app/services/plan_service.py`
- 改为生成器函数，用 `yield` 推进度消息
- 流程：ExerciseAgent → ScheduleAgent → PlanAgent → 存库

**验收标准：**
- OnboardingGuide 进度页能看到文字实时变化：
  `🔍 正在搜索动作 & 查询天气...` → `🏋️ 动作搜索完成` → `☀️ 天气查询完成` → `📋 AI 教练正在生成完整计划...` → `✅ 完成！`
- 跑完后自动跳转 `/home`，日历上有训练日标记
- 点击日历中有训练的日期（如 6月25日 周四），右侧面板能完整显示：
  ```
  6月25日 周四
  核心+有氧
  5/8
  🔥 热身
    开合跳   30秒 · 自重
    原地踏步  30秒 · 自重
  💪 主训练
    卷腹     3组×15次 · 自重
    登山跑    3组×1次 · 自重
    俄罗斯转体 3组×16次 · 自重
    高抬腿    3组×1次 · 自重
  🧘 拉伸
    腹部拉伸  30秒
    全身放松  30秒
  ```
- 每个动作可以打勾（✓）、标记太重
- 后端日志能看到 ExerciseAgent 和 ScheduleAgent 并行执行，PlanAgent 最后汇总

---

### Task 2：让 ExerciseDrawer 显示更丰富的动作详情

**方案：localStorage 缓存 + 按需拉取**

逻辑：
- 每个动作用 `wger_id` 作为 key 存在 `localStorage` 里
- Drawer 打开时先查缓存，命中就直接用，不发请求
- 缓存没有就去 wger 拉，拉到了存进缓存，Drawer 再显示
- 拉不到就 fallback 到占位图，不影响 Drawer 正常使用
- 缓存不设过期（wger 动作数据基本不变）

好处：
- 同一个动作出现在多个训练日，只拉一次
- 离线也能看已缓存过的动作
- 对 wger 服务器友好，不重复请求

缓存格式（`localStorage` key = `"wger_ex_<id>"`）：
```json
{
  "images": ["https://wger.de/...1.png", "https://wger.de/...2.png"],
  "description": "完整动作描述文字..."
}
```

**前提：Task 1 打通后，计划数据里每个动作带上 `wger_id`**

- `ExerciseAgent` 搜索 wger 时已经拿到了每个动作的 `id`，
  只需确保 `TrainerAgent` 在整合时把 `wger_id` 原样保留
- 前端 `ExerciseState` 类型加一个 `wgerId?: number` 字段
- `buildDayPlans()` 映射时把 `wger_id` 存进去

**第一步：后端新增 wger 详情代理接口**

文件：`backend/app/api/routes/wger.py`（新建）

```
GET /api/wger/exercise/{wger_id}
```
- 接收 wger 动作 ID（整数）
- 调 wger `/exerciseinfo/{id}` 拿图片列表 + 完整 description
- 返回：`{ images: string[], description: string }`
- 如果 wger 请求失败，返回 `{ images: [], description: "" }`，不抛 500

**第二步：前端加缓存 + Drawer 异步加载**

文件：`frontend/src/services/api.ts`
- 新增 `fetchExerciseDetail(wgerId: number)` 函数
- 内部先查 `localStorage`，命中直接返回
- 未命中才调后端接口，拿到后写入缓存再返回

文件：`frontend/src/components/ExerciseDrawer.vue`
- watch `visible` 变为 true 时，如果有 `exercise.wgerId`，调 `fetchExerciseDetail()`
- 拉取期间图片区域显示骨架屏（Ant Design 的 `a-skeleton`）
- 拉到后替换图片，最多展示 2 张（避免 Drawer 太长）

**验收标准：**
- 第一次点开某个动作：能看到加载中 → 真实图片出现
- 再次点开同一动作：直接显示图片，无加载过程
- 网络断开时：fallback 到名称首字母占位图，不报错

---

### Task 3：wger 代理接口（供 Drawer 使用）

Task 1 打通后，后端新增一个接口让前端能按 `wger_id` 拉动作详情。

文件：`backend/app/api/routes/wger.py`（新建）

```
GET /api/wger/exercise/{wger_id}
```
- 调 wger `/exerciseinfo/{id}` 拿图片列表 + 完整描述
- 返回 `{ images: string[], description: string }`
- wger 失败时返回 `{ images: [], description: "" }`，不抛 500

把 `_format_exercise()` 逻辑抽到 `backend/app/services/wger_service.py`，
`exercise_agent.py` 和这个接口都从这里 import，消除重复代码。

---

### Task 4：MCP 协议桥接（最后做，简历亮点）

**目标：** ExerciseAgent 通过 MCP 协议调用 `wger_mcp_server.py`，
而不是直接调 REST API。简历能写"实现 MCP 协议桥接，将外部 MCP Server 集成进 Agent 工具链"。

**为什么现在做不了：** `hello_agents` 框架没有内置 MCP 工具支持，
需要自己写桥接层。

**实现方案：写一个通用 `MCPTool` 包装类（约 100 行）**

文件：`backend/app/tools/mcp_tool.py`（新建）

```python
class MCPTool(Tool):
    """通用 MCP Server 桥接工具。
    
    启动 MCP Server 子进程（stdio 模式），
    通过 JSON-RPC 协议调用其工具，
    把结果包装成 hello_agents ToolResponse 返回。
    """
    # 启动子进程：python wger_mcp_server.py
    # 发送 JSON-RPC: {"method": "tools/call", "params": {...}}
    # 读取 stdout 拿结果
```

文件：`backend/app/agents/exercise_agent.py`
- 替换 `WgerSearchTool` / `WgerListMusclesTool` 等
- 改为用 `MCPTool("wger_search_exercises")` 等包装 wger MCP Server 的工具

**验收标准：**
- ExerciseAgent 跑起来时能看到 `wger_mcp_server.py` 子进程被启动
- 后端日志显示通过 MCP 协议拿到了 wger 动作数据
- 简历能写：自实现 MCP stdio 协议桥接，集成外部 MCP Server 到 Agent 工具链

---

## 执行顺序

```
Task 1（Agent 重构 + 并行 + SSE 进度推送）
  └─ [x] Step 1.1  前端：StepCardPersonal 加经验水平选择 + 修复传参
  └─ [x] Step 1.2  前端：GeneratingProgress 改为 SSE 接收
  └─ [x] Step 1.3  后端：新建 PlanAgent，去掉 DietAgent/PlanReviewAgent
  └─ [x] Step 1.4  后端：plan_service 改为并行 ExerciseAgent+ScheduleAgent，SSE 推送进度
  └─ [ ] Step 1.5  端到端验证：进度文字实时变化，跑完跳转主页有数据

Task 2（Drawer 显示真实图片，依赖 Task 1 的 wger_id）
  └─ [x] Step 2.1  前端：ExerciseState 加 wgerId 字段 + buildDayPlans 映射
  └─ [x] Step 2.2  后端：新增 GET /api/wger/exercise/{wger_id} 接口（已修复 404 bug）
  └─ [x] Step 2.3  前端：api.ts 加 fetchExerciseDetail()（含 localStorage 缓存）
  └─ [x] Step 2.4  前端：ExerciseDrawer 打开时异步加载 + 骨架屏

Task 3（wger 代理接口 + 抽 wger_service，依赖 Task 2）
  └─ [x] Step 3.1  后端：抽 wger_service.py 消除重复代码
  └─ [ ] Step 3.2  验收：Drawer 第一次点开有加载动画，再次点开秒显示

Task 4（MCP 协议桥接，最后做）
  └─ [ ] Step 4.1  后端：实现通用 MCPTool 桥接类（stdio JSON-RPC）
  └─ [ ] Step 4.2  后端：ExerciseAgent 改用 MCPTool 调 wger MCP Server
  └─ [ ] Step 4.3  验收：日志能看到 MCP 子进程启动 + 数据正常拿到
```

---

## 不做的事（本次范围外）

- 饮食建议模块（前端没有页面，以后再加）
- 计划修改/重新生成功能
- 日历外观改动（已做好）
- wger 视频展示（MOV 格式，移动端体验差）
