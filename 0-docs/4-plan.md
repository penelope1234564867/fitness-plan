# Phase 4 计划：UI 重构 + 流程优化

## 背景

用户希望彻底改变应用交互方式，在修复后端流程的基础上，实现更简洁的 UI。

## 三个核心变更

### 1. 锻炼地点改为多选（Step 3）

**现状：** StepCardSchedule 中 location 为单选，仅能选「健身房/居家/户外」之一。

**变更：** location 改为 `string[]`，用户可多选。

**影响范围：**
- 前端：`StepCardSchedule.vue` → location 改为多选
- 前端：`OnboardingGuide.vue` → formData.location 改为数组
- 前端：`types/index.ts` → PlanRequest.workout_location 改为可选数组
- 后端：`schemas.py` → PlanRequest.workout_location 改为 `List[str]`
- 后端：`fitness.py` → 参数透传改为逗号拼接或取第一个
- 后端：`plan_service.py` → user_info 中 location 展示改为多值

---

### 2. UI 重构：单界面模式

去掉导航栏（NavBar）切换模式，改为**只有一个主界面 + 个人主页**的两页结构。

#### 主界面布局

```
┌──────────────────────────────────────────────────┐
│  🏋️ AI 智能健身助手              [👤 头像] → 个人主页 │
├────────────────┬─────────────────────────────────┤
│                │                                 │
│   ┌────日历────┐│   ← 选中某天后，右边显示当日计划  │
│   │  June 2026 ││                                 │
│   │ 日 一 二 三││   ┌─ 腿部训练 ─────────────┐   │
│   │      1 2 3 ││   │ 🔥 热身                  │   │
│   │  4 5 6 7...││   │   ☐ 开合跳 30s           │   │
│   │            ││   │   ☐ 高抬腿 30s           │   │
│   │  左上角     ││   ├─────────────────────────┤   │
│   │            ││   │ 💪 主训练                  │   │
│   │            ││   │   ☐ 深蹲 3×12             │   │
│   │            ││   │   ☐ 弓步蹲 3×12  → 弹出  │   │
│   │            ││   │   ☐ 臀桥 3×15             │   │
│   └────────────┘│   └─────────────────────────┘   │
│                │                                 │
│  ┌──AI 提问区──┐│          右边一整块都是训练计划    │
│  │ 💬 问AI...  ││                                 │
│  └────────────┘│                                 │
├────────────────┴─────────────────────────────────┤
│         ← 唯一的「主界面」，无导航栏切换              │
└──────────────────────────────────────────────────┘
```

#### 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | OnboardingGuide | 三步走引导（未 onboarding 时） |
| `/home` | **MainPage**（新） | **唯一主界面**，日历 + 训练计划 + AI 提问 |
| `/profile` | ProfilePage | 个人主页，右上角头像进入 |

- **三步走完成后** → 跳转到 `/home`
- **已完成 onboarding** → 直接进入 `/home`
- **右上角头像** → `/profile`（新页面），点标题/返回按钮回到 `/home`

#### 新的/修改的组件

| 文件 | 状态 | 说明 |
|------|------|------|
| `MainPage.vue` | ✨ 新增 | 主界面容器，左右分栏布局 |
| `CalendarPanel.vue` | 重构 from DayCell | 左侧日历面板，可选择日期 |
| `DailyPlanPanel.vue` | ✨ 新增 | 右侧训练计划面板，显示选中日期的计划 |
| `ExerciseDrawer.vue` | ✨ 新增 | 动作详情 Drawer（从 WorkoutChecklist 提取） |
| `AIChatPanel.vue` | ✨ 新增 | 左下角 AI 提问组件 |
| `NavBar.vue` | 🗑️ 移除 | 不再需要 |
| `CalendarView.vue` | 🗑️ 移除 | 被 MainPage 替代 |
| `WorkoutChecklist.vue` | 🗑️ 移除 | 功能合并到 DailyPlanPanel + ExerciseDrawer |
| `DayCell.vue` | 保留 | 日历格组件继续使用 |
| `TodayCard.vue` | 🗑️ 移除 | 不再单独需要 |

#### 关键交互

- **日历点击日期** → 右侧显示该日计划
- **计划中点击动作** → 弹出 ExerciseDrawer（含图片、描述、打勾、太重了）
- **打勾/完成状态** → 存储在 localStorage（同现方案）
- **AI 提问** → 输入框 + 发送按钮，调用后端 AI 接口（可后续实现）

---

### 3. MVP 优先：先修好现有的后端流程

**目标：** 三步走 → 后端生成计划 → 计划正确存入数据库 → 前端正确展示

**已知问题（待验证）：**
- [ ] Agent 编排是否正常跑通（5 个 Agent 串行）
- [ ] 生成的 JSON 结构是否被前端正确解析
- [ ] weekly_plans → days → day 映射是否正确
- [ ] 前端 `buildDayPlans` 中 `planStart` 计算是否正确

**验证方法：**
1. 用现有的 `07_test_full_flow.py` 测试完整流程
2. 手工调用 API 生成计划，检查返回 JSON
3. 前端加载数据库中的计划，检查日历展示
4. 修复发现的问题

---

## 执行顺序

```
Step 0: 修后端流程（保证三步走 → 数据库 → 前端展示正确）
Step 1: 锻炼地点改为多选（StepCardSchedule + Schema）
Step 2: 新 MainPage.vue 布局（左日历 + 右训练计划）
Step 3: DailyPlanPanel 展示选中日期计划 + 打勾
Step 4: ExerciseDrawer（动作详情弹出）
Step 5: AIChatPanel（AI 提问框）
Step 6: 路由改造 + 移除旧组件
Step 7: 右上角头像 → ProfilePage
Step 8: 整体联调
```
