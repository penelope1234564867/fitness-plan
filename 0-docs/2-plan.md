# 前端改造计划 — 最简化 Demo

> 基于 brainstorming 讨论结果，目标：**三步引导 → 日历主页 → 打勾训练**，砍掉冗余页面，只保留核心教练体验。

---

## 开发方式

| 维度 | 说明 |
|------|------|
| **UI/UX 设计** | 使用 `ui-ux-pro-max` skill 生成设计系统（颜色、字体、样式），每次创建/改造组件前先搜索对应 domain |
| **开发流程** | 按下方 `phase-tools-map.md` 风格的工具映射表执行，每个任务标注所需 Skills + MCP 工具 |
| **验收** | 每个 Phase 完成后用 `Playwright` 截图验收 |

---

## 一、改造目标

| 从（现在） | 到（Demo） |
|-----------|-----------|
| 首页12字段大表单 | 三步卡片引导，填完即走 |
| 每次重新填 | 只填一次，存在个人主页可编辑 |
| 记录页单独打字 | 直接在计划上打勾，自动保存 |
| 周 Tab 切换 | 日历视图 | 
| 进度图表页 | 砍掉，后续再补 |
| 4个导航tab | 2个：[📅训练计划] [👤个人主页] |

---

## 二、页面结构 & 路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | 三步引导（首次） | 三张卡片，填完跳 `/calendar` |
| `/calendar` | 日历主页（默认首页） | 日历 + 今日训练入口 |
| `/calendar?date=2026-06-04` | 打勾清单 | 点击某一天进入 |
| `/profile` | 个人主页 | 查看/编辑资料，重新生成 |

> ⚠️ `Record.vue`、`Progress.vue`、原 `Plan.vue` 全部砍掉，不再使用。

---

## 三、组件树设计

```
App.vue
├── NavBar.vue (改造)
│   ├── [📅 训练计划] → /calendar
│   └── [👤 个人主页] → /profile
│
├── OnboardingGuide.vue (新增) ← 三步引导卡片
│   ├── StepCardPersonal.vue      ← Step 1: 身高/体重/年龄/性别
│   ├── StepCardGoal.vue          ← Step 2: 目标选择
│   └── StepCardSchedule.vue      ← Step 3: 周天数/地点
│   └── GeneratingProgress.vue    ← 生成进度条
│
├── CalendarView.vue (新增) ← 日历主页（代替原 Plan.vue）
│   └── DayCell.vue              ← 日历格（显示训练部位图标）
│   └── TodayCard.vue            ← 底部今日训练入口
│
└── WorkoutChecklist.vue (新增) ← 打勾清单
    └── ExerciseRow.vue          ← 单个动作行（打勾/太重了）
```

---

## 四、详细页面设计

### 4.1 三步引导（首次进入）

> 不是大表单，是三张卡片，一张一张翻

**Step 1 — 个人资料：**
```
┌──────────────────────────────────┐
│  👤 第一步：你的资料              │
│                                  │
│  身高 [____] cm   体重 [____] kg │
│  年龄 [____]      性别 [男/女]   │
│                                  │
│            [下一步 →]            │
└──────────────────────────────────┘
```

**Step 2 — 目标：**
```
┌──────────────────────────────────┐
│  🎯 第二步：你的目标              │
│                                  │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐   │
│  │🔥   │ │💪  │ │✨  │ │🌿  │   │
│  │减脂 │ │增肌 │ │塑形│ │保持│   │
│  │     │ │    │ │    │ │健康│   │
│  └────┘ └────┘ └────┘ └────┘   │
│                                  │
│       [← 上一步]  [下一步 →]     │
└──────────────────────────────────┘
```

**Step 3 — 训练安排：**
```
┌──────────────────────────────────┐
│  ⏱ 第三步：训练安排              │
│                                  │
│  每周训练 [2/3/4/5/6] 天        │
│                                  │
│  锻炼地点                         │
│  ┌──────┐ ┌──────┐ ┌──────┐    │
│  │🏋️   │ │🏠   │ │🌳   │    │
│  │健身房│ │居家  │ │户外  │    │
│  └──────┘ └──────┘ └──────┘    │
│                                  │
│       [← 上一步]  [🚀 生成计划] │
└──────────────────────────────────┘
```

**生成进度条（点击生成后）：**
```
  [■■■■■■■■□□□□] 80%
  📋 正在分析你的健身目标...
  → 完成后自动跳转日历主页
```

### 4.2 日历主页 `/calendar`

```
┌──────────────────────────────────────────┐
|  📅 2026年6月            ← → 切换月份    |
|  日   一   二   三   四   五   六         |
|        1    2    3    4    5    6        |
|                   🦵    💪    🧘        |
|  7    8    9   10   11   12   13        |
|  ☕   🦵         💪                     |
| 14   15   16   17   18   19   20        |
|  ☕   🦵         💪    ☕               |
| ...                                     |
|                                         |
|  🟢 今日：6/4 腿部训练 → [开始训练]     |
└──────────────────────────────────────────┘
```

- 没有计划时显示空日历 + "还没有训练计划，先去设置吧" 的提示
- 日历格右下角小图标标识训练部位

### 4.3 打勾清单 `/calendar?date=2026-06-04`

```
┌──────────────────────────────────────────┐
|  ◀  📅 6月4日 周四 · 腿部训练             |
|                                          |
|  🔥 热身                                 |
|  □ 开合跳 30秒                [完成✅]   |
|  □ 高抬腿 30秒                [完成✅]   |
|                                          |
|  💪 主训练                               |
|  □ 徒手深蹲  3组×12次         [完成✅]   |
|  □ 弓步蹲    3组×12次         [太重了😰] |
|  □ 臀桥      3组×15次         [完成✅]   |
|  □ 蚌式开合  3组×12次/L      [完成✅]   |
|                                          |
|  🧘 拉伸                                 |
|  □ 大腿前侧拉伸 30秒                     |
|  □ 臀部拉伸 30秒                         |
|  ─────────────────────────               |
|  进度: 5/7  ███████░░░                   |
|                                          |
|  [💾 自动保存中]                          |
└──────────────────────────────────────────┘
```

**状态处理：**
| 状态 | 表现 |
|------|------|
| 加载中 | 骨架屏 / Spin |
| 该天无训练 | "今天是休息日 🎉" |
| 训练进行中（部分完成） | 进度条 + 已勾选状态 |
| 训练全部完成 | "🎉 今日训练全部完成！" + 庆祝动画 |
| 错误 | 错误提示 + 重新加载按钮 |
| 该天还没到 | "这是未来的训练计划哦" |
| 过去未完成 | "未完成"标记 |

**点击「太重了😰」的交互：**
- 弹窗确认："下次减轻这个动作的重量？"
- 确认后该动作旁边显示 "✅ 已记录，下次减轻"

### 4.4 个人主页 `/profile`

```
┌──────────────────────────────────────────┐
|  👤 个人资料                             |
|                                          |
|  身高  165 cm    体重  65 kg             |
|  年龄  25        性别  女                |
|  目标  减脂                              |
|  每周  3 天      地点  健身房            |
|                                          |
|  [✏️ 编辑资料] → 打开编辑模式            |
|  [🔄 重新生成计划] → 确认 → AI重新生成    |
|                                          |
|  ─── 统计数据 ───                        |
|  已训练 12 天    当前连续 3 天            |
|  本月完成 36/60 个动作                   |
└──────────────────────────────────────────┘
```

---

## 五、数据流（前端状态管理）

### 5.1 Pinia Store 改造

现有 `plan.ts`、`user.ts`、`record.ts` 三个 Store → **合并重构为两个**：

**`userStore`（用户资料）：**
```typescript
interface UserState {
  profile: {
    height: number | null
    weight: number | null
    age: number | null
    gender: 'male' | 'female' | null
    goal: string | null
    experience: string | null
    days_per_week: number
    workout_location: string | null
  }
  isFirstVisit: boolean  // 控制是否显示三步引导
  stats: {
    totalWorkoutDays: number
    currentStreak: number
    monthlyCompletion: { done: number; total: number }
  }
}
```

**`workoutStore`（训练计划 + 打勾记录，代替原 plan + record）：**
```typescript
interface WorkoutState {
  // 日历数据
  monthPlans: Record<string, DayPlan> // key: "2026-06-04"
  currentMonth: string  // "2026-06"
  
  // 当前打开的某天清单
  currentDayPlan: DayPlan | null
  
  // 生成状态
  isGenerating: boolean
  generationProgress: number
  generationStatus: string
  
  // 加载状态
  loading: boolean
  error: string | null
}

interface DayPlan {
  date: string        // "2026-06-04"
  weekIndex: number
  dayIndex: number
  focusArea: string   // "腿部训练" / "休息"
  sections: {
    type: 'warmup' | 'main' | 'cooldown'
    exercises: ExerciseState[]
  }[]
}

interface ExerciseState {
  name: string
  targetMuscle: string
  sets: number
  reps: number
  weight: string
  duration?: string   // 热身/拉伸用秒
  completed: boolean  // ✅ 打勾状态
  tooHeavy: boolean   // 😰 太重了标记
  order: number
}
```

### 5.2 数据持久化

- 用户资料、三步引导完成状态 → `localStorage`
- 训练数据 → API（后端 DB），前端通过 API 调用
- 离线缓存：已完成状态可以先存 localStorage，提交时批量同步

### 5.3 API 接口（前端视角）

现有 API 接口不变，前端新增/修改以下调用：

| 方法 | 用途 | 备注 |
|------|------|------|
| `POST /api/fitness/generate` | 生成计划（三步引导后调用） | 已有 |
| `GET /api/fitness/plan/{id}` | 获取计划详情（含每日清单数据） | 已有 |
| `GET /api/fitness/plans` | 获取计划列表 | 已有 |
| `PUT /api/fitness/exercise/{id}/status` | 更新某个动作的完成状态 | **新增** |
| `PUT /api/fitness/exercise/{id}/weight` | 记录「太重了」反馈 | **新增** |

---

## 六、文件改动清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/views/CalendarView.vue` | 日历主页 |
| `src/views/WorkoutChecklist.vue` | 打勾清单页 |
| `src/views/ProfilePage.vue` | 个人主页 |
| `src/views/OnboardingGuide.vue` | 三步引导容器 |
| `src/components/StepCardPersonal.vue` | Step 1 卡片 |
| `src/components/StepCardGoal.vue` | Step 2 目标选择卡片 |
| `src/components/StepCardSchedule.vue` | Step 3 训练安排卡片 |
| `src/components/GeneratingProgress.vue` | 生成进度条 |
| `src/components/DayCell.vue` | 日历格 |
| `src/components/TodayCard.vue` | 今日训练入口 |
| `src/components/ExerciseRow.vue` | 单行动作（打勾/太重了） |
| `src/stores/workout.ts` | 训练计划+记录 Store |

### 删除文件

| 文件 | 替代 |
|------|------|
| `src/views/Home.vue` | OnboardingGuide.vue |
| `src/views/Plan.vue` | CalendarView.vue |
| `src/views/Record.vue` | 砍掉，功能合并到 WorkoutChecklist |
| `src/views/Progress.vue` | 砍掉，后续再补 |
| `src/components/RecordForm.vue` | 砍掉 |
| `src/components/PlanCard.vue` | 砍掉 |
| `src/components/ExerciseItem.vue` | ExerciseRow.vue |
| `src/components/DietTips.vue` | 砍掉，后续再补 |
| `src/stores/record.ts` | 合并到 workout.ts |

### 修改文件

| 文件 | 改动 |
|------|------|
| `src/App.vue` | 路由更新，只保留 [训练计划] [个人主页] |
| `src/components/NavBar.vue` | 2 个导航项 |
| `src/stores/user.ts` | 加 isFirstVisit、stats |
| `src/services/api.ts` | 加新接口 |
| `src/types/index.ts` | 加新类型，删旧类型 |
| `src/main.ts` | 注册新路由 |

---

## 七、Phase 工具映射表（执行用）

> 每个任务标注所需 Skills 和 MCP 工具，按顺序执行。每完成一个 Phase 用 `Playwright` 截图验收。

### Phase 1：结构搭建（清理 + 路由 + 类型）

| # | 任务 | Skills | MCP 工具 |
|---|------|--------|----------|
| 1.1 | 删除旧文件（Home/Plan/Record/Progress/RecordForm/PlanCard/ExerciseItem/DietTips） | — | `Filesystem`（delete 文件） |
| 1.2 | 创建新文件目录结构 | — | `Filesystem`（创建空文件） |
| 1.3 | 改造 `NavBar.vue`：2 个导航项 [📅训练计划] [👤个人主页]，高亮激活态 | `ui-ux-pro-max`（导航栏样式、激活态） | `Filesystem`（write NavBar.vue） |
| 1.4 | 改造 `App.vue` + `main.ts`：新路由配置，移除旧路由 | — | `Filesystem`（edit App.vue、main.ts） |
| 1.5 | 重写 `types/index.ts`：加新类型（DayPlan/ExerciseState 等），删旧类型 | — | `Filesystem`（write types/index.ts） |
| 1.6 | 改造 `api.ts`：保留旧接口 + 新增 exercise status/weight 接口 | — | `Filesystem`（edit api.ts） |
| 1.7 | 改造 `stores/user.ts`：加 isFirstVisit、stats | — | `Filesystem`（edit user.ts） |
| 1.8 | 新增 `stores/workout.ts`：合并原 plan + record store | — | `Filesystem`（write workout.ts） |
| 1.9 ✅ | `npm run dev` 验证无报错 | `verify` | `VS Code IDE`（getDiagnostics 检查无错误） |

**Phase 1 核心工具组合：** `ui-ux-pro-max`（导航栏）+ `Filesystem` + `VS Code IDE`

---

### Phase 2：三步引导设计 + 实现

> 先走 `ui-ux-pro-max` 设计系统，再写代码。每张卡片用 Search 查询 domain 获取最佳样式。

| # | 任务 | Skills | MCP 工具 |
|---|------|--------|----------|
| 2.1 | 🎨 设计系统生成：三步引导的整体样式、配色、字体 | `ui-ux-pro-max`（`--design-system "fitness health coaching" -p "AI健身助手"`） | `Filesystem`（运行 search.py） |
| 2.2 | 🎨 搜索表单/卡片 domain：卡片布局、翻页动画、输入样式 | `ui-ux-pro-max`（`--domain ux "multi-step form progressive disclosure"`） | `Filesystem`（运行 search.py） |
| 2.3 | 实现 `OnboardingGuide.vue`：三步容器 + 翻页动画 + 步骤指示器 | `ui-ux-pro-max`（卡片布局、过渡动画） | `Filesystem`（write） |
| 2.4 | 实现 `StepCardPersonal.vue`：身高/体重/年龄/性别表单 | `ui-ux-pro-max`（表单样式、输入框） | `Filesystem`（write） |
| 2.5 | 实现 `StepCardGoal.vue`：四选一目标卡片 | `ui-ux-pro-max`（选择卡片样式） | `Filesystem`（write） |
| 2.6 | 实现 `StepCardSchedule.vue`：周天数 + 地点选择 | `ui-ux-pro-max`（选择控件） | `Filesystem`（write） |
| 2.7 | 实现 `GeneratingProgress.vue`：实时进度条 + 状态文字 + 自动跳转 | `ui-ux-pro-max`（进度条动画、加载状态） | `Filesystem`（write） |
| 2.8 | 联调：三步引导 → 生成 → 跳转日历 | — | `VS Code IDE` |
| 2.9 ✅ | 验收：三张卡片翻完，生成按钮正常工作 | `verify` | `Playwright`（截图三步引导各步骤） |

> 💡 ui-ux-pro-max 路径：`C:\Users\18194\.claude\plugins\marketplaces\nextlevelbuilder-ui-ux-pro-max-skill\src\ui-ux-pro-max\scripts\search.py`
> 运行：`python <path> "fitness health coaching" --design-system -p "AI健身助手"`

---

### Phase 3：日历主页

| # | 任务 | Skills | MCP 工具 |
|---|------|--------|----------|
| 3.1 | 🎨 搜索日历/时间线 domain：日历格样式、日期展示 | `ui-ux-pro-max`（`--domain ux "calendar date-picker time"`） | `Filesystem`（运行 search.py） |
| 3.2 | 实现 `DayCell.vue`：日历格（含训练部位图标、今日高亮、休息日样式） | `ui-ux-pro-max`（日期格样式） | `Filesystem`（write） |
| 3.3 | 实现 `TodayCard.vue`：底部今日训练入口卡片 | `ui-ux-pro-max`（入口卡片样式） | `Filesystem`（write） |
| 3.4 | 实现 `CalendarView.vue`：月日历容器 + 月份切换 + 数据绑定 | `ui-ux-pro-max`（日历布局） | `Filesystem`（write） |
| 3.5 | 状态处理：空状态（无计划）、加载中（骨架屏）、错误 | — | `Filesystem`（edit CalendarView） |
| 3.6 | 点击某一天 → 跳转 `/calendar?date=YYYY-MM-DD` | — | `Filesystem`（路由跳转逻辑） |
| 3.7 ✅ | 验收：日历显示正常，有训练部位图标，点击进入清单 | `verify` | `Playwright`（截图日历主页） |

---

### Phase 4：打勾清单

| # | 任务 | Skills | MCP 工具 |
|---|------|--------|----------|
| 4.1 | 🎨 搜索清单/任务 domain：打勾样式、进度条、完成动画 | `ui-ux-pro-max`（`--domain ux "checklist progress task completion"`） | `Filesystem`（运行 search.py） |
| 4.2 | 实现 `ExerciseRow.vue`：单行动作（名称/组次/重量/打勾/太重了按钮） | `ui-ux-pro-max`（清单行样式） | `Filesystem`（write） |
| 4.3 | 实现 `WorkoutChecklist.vue`：清单容器（热身/主训/冷身分区 + 顶部返回） | `ui-ux-pro-max`（分区布局、进度条） | `Filesystem`（write） |
| 4.4 | 打勾交互：□ → ✅ 状态切换，进度条实时更新 | — | `Filesystem`（edit） |
| 4.5 | 「太重了😰」交互：弹窗确认 → 记录 → 下次减轻标识 | `ui-ux-pro-max`（弹窗样式、确认对话框） | `Filesystem`（edit） |
| 4.6 | 状态处理：休息日、进行中、全部完成（庆祝动画）、未来日期、过去未完成 | `ui-ux-pro-max`（空状态、完成动画） | `Filesystem`（edit） |
| 4.7 | 本地状态持久化：完成状态存 localStorage + 同步到 API | — | `Filesystem`（edit workout.ts） |
| 4.8 ✅ | 验收：打勾正常、进度条动、太重了记录、全部完成🎉 | `verify` | `Playwright`（截图各状态清单） |

---

### Phase 5：个人主页

| # | 任务 | Skills | MCP 工具 |
|---|------|--------|----------|
| 5.1 | 🎨 搜索个人资料 domain：用户信息展示样式 | `ui-ux-pro-max`（`--domain ux "profile user settings"`） | `Filesystem`（运行 search.py） |
| 5.2 | 实现 `ProfilePage.vue`：用户资料展示 + 编辑模式 + 重新生成 | `ui-ux-pro-max`（个人主页布局） | `Filesystem`（write） |
| 5.3 | 编辑资料功能：切换编辑/查看模式，保存到 localStorage + API | — | `Filesystem`（edit） |
| 5.4 | 重新生成计划：确认弹窗 → 调用生成 → 替换计划 → 跳转日历 | — | `Filesystem`（edit） |
| 5.5 | 统计数据展示：已训练天数、连续天数、本月完成率 | `ui-ux-pro-max`（统计数据卡片） | `Filesystem`（edit） |
| 5.6 ✅ | 验收：个人主页显示正确，编辑/重新生成功能正常 | `verify` | `Playwright`（截图个人主页） |

---

### 工具总用量一览

| 工具/技能 | 使用 Phase | 用途 |
|-----------|-----------|------|
| `Filesystem` | 1-5 全程 | 读写文件主力 |
| `VS Code IDE` | 1-5 全程 | 运行/诊断 |
| `Playwright` | 1-5 所有验收节点 | 截图验收 |
| `ui-ux-pro-max` | 2/3/4/5 设计阶段 | 设计系统 + 组件样式 |
| `verify` skill | 1.9 / 2.9 / 3.7 / 4.8 / 5.6 | 验证执行

---

## 八、验收标准

| 验收点 | 标准 |
|-------|------|
| 首次打开 | 看到三步引导，不是大表单 |
| 三步引导 | 三张卡片翻完，信息填完，点击生成 |
| 生成进度条 | 实时更新，完成后自动跳转日历 |
| 日历主页 | 显示当前月份，日期间有训练部位图标 |
| 点击某一天 | 进入打勾清单 |
| 打勾 | 点击 □ → ✅，进度条更新 |
| 太重了 | 点击 → 弹窗确认 → 记录 |
| 所有完成 | "今日训练全部完成" |
| 个人主页 | 显示用户资料，可编辑，可重新生成 |
| 导航 | 两个tab切换正常 |
| 刷新页面 | 资料不丢（localStorage），训练状态从API加载 |
| 无计划时 | 日历显示空状态提示 |
