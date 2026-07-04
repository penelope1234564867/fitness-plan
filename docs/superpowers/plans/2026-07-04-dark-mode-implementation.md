# Dark Mode 暗色模式实现计划

> **For agentic workers:** 使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 逐任务实现。

**目标:** 为 Fitness Plan 应用添加完整的日夜间模式切换功能

**架构:** CSS 变量全面迁移（~21 个变量）+ Ant Design Vue ConfigProvider + Pinia 主题 store + localStorage 持久化 + 首次访问跟随系统偏好

**技术栈:** Vue 3, Ant Design Vue v4, Pinia, CSS Custom Properties

---

### 任务 1: 创建 CSS 变量定义 (theme.css)

**文件:**
- 创建: `frontend/src/styles/theme.css`

- [ ] **Step 1: 创建 styles 目录和 theme.css**

创建 `frontend/src/styles/` 目录，然后创建 `theme.css`，定义所有 21 个 CSS 变量：

```css
/* ========== 亮色模式（:root） ========== */
:root {
  /* 背景色 */
  --bg-page: #f0f2f5;
  --bg-card: #ffffff;
  --bg-subtle: #f5f5f5;
  --bg-hover: #fafafa;

  /* 文字色 */
  --text-primary: #1a1a1a;
  --text-secondary: #555555;
  --text-muted: #999999;
  --text-inverse: #ffffff;

  /* 品牌/功能色 */
  --brand-orange: #f97316;
  --brand-orange-light: #fb923c;
  --brand-orange-deep: #ea580c;
  --brand-orange-subtle: #fff7ed;
  --color-success: #22c55e;
  --color-success-deep: #16a34a;
  --color-success-subtle: #f0fdf4;
  --color-error: #ef4444;
  --color-error-deep: #dc2626;
  --color-error-subtle: #fef2f2;
  --color-info: #3b82f6;
  --color-info-deep: #2563eb;
  --color-info-subtle: #dbeafe;
  --color-purple: #a855f7;

  /* 阶段色 */
  --phase-foundational: #3b82f6;
  --phase-hypertrophy: #22c55e;
  --phase-strength: #f97316;
  --phase-deload: #a855f7;

  /* 边框/阴影 */
  --border-color: #e8e8e8;
  --border-subtle: #f0f0f0;
  --shadow-card: 0 2px 8px rgba(0,0,0,0.06);
  --shadow-card-lg: 0 2px 12px rgba(0,0,0,0.08);
}

/* ========== 暗色模式（:root.dark） ========== */
:root.dark {
  /* 背景色 */
  --bg-page: #141414;
  --bg-card: #1f1f1f;
  --bg-subtle: #2a2a2a;
  --bg-hover: #333333;

  /* 文字色 */
  --text-primary: #e5e5e5;
  --text-secondary: #a0a0a0;
  --text-muted: #666666;
  --text-inverse: #1a1a1a;

  /* 品牌/功能色（降低饱和度） */
  --brand-orange: #d97706;
  --brand-orange-light: #b45309;
  --brand-orange-deep: #92400e;
  --brand-orange-subtle: #2a1f0e;
  --color-success: #16a34a;
  --color-success-deep: #15803d;
  --color-success-subtle: #0a1f0f;
  --color-error: #dc2626;
  --color-error-deep: #b91c1c;
  --color-error-subtle: #1f0a0a;
  --color-info: #2563eb;
  --color-info-deep: #1d4ed8;
  --color-info-subtle: #0a1428;
  --color-purple: #9333ea;

  /* 阶段色（提高亮度，在深色背景上可见） */
  --phase-foundational: #60a5fa;
  --phase-hypertrophy: #4ade80;
  --phase-strength: #fb923c;
  --phase-deload: #c084fc;

  /* 边框/阴影 */
  --border-color: #333333;
  --border-subtle: #2a2a2a;
  --shadow-card: 0 2px 8px rgba(0,0,0,0.3);
  --shadow-card-lg: 0 2px 12px rgba(0,0,0,0.4);
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/styles/theme.css
git commit -m "feat(dark-mode): add CSS variables definition for theme system"
```

---

### 任务 2: 创建主题 Pinia Store (theme.ts)

**文件:**
- 创建: `frontend/src/stores/theme.ts`

**接口:**
- 导出: `useThemeStore()` — Pinia store
- 状态: `mode: 'light' | 'dark'`
- 计算属性: `isDark: boolean`, `antTheme: ThemeConfig`
- 动作: `toggleTheme()`, `initTheme()`

- [ ] **Step 1: 创建 theme store**

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { theme } from 'ant-design-vue'

type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'fitness-theme-mode'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>('light')

  const isDark = computed(() => mode.value === 'dark')

  const antTheme = computed(() => ({
    algorithm: isDark.value ? theme.darkAlgorithm : theme.defaultAlgorithm,
  }))

  function applyMode(val: ThemeMode) {
    mode.value = val
    if (val === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem(STORAGE_KEY, val)
  }

  function toggleTheme() {
    applyMode(isDark.value ? 'light' : 'dark')
  }

  function initTheme() {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeMode | null
    if (saved) {
      applyMode(saved)
    } else {
      // 首次访问：跟随系统偏好
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      applyMode(prefersDark ? 'dark' : 'light')
    }
  }

  return { mode, isDark, antTheme, toggleTheme, initTheme }
})
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/stores/theme.ts
git commit -m "feat(dark-mode): add theme Pinia store with persistence and system preference"
```

---

### 任务 3: 修改 main.ts (引入 theme.css)

**文件:**
- 修改: `frontend/src/main.ts`

- [ ] **Step 1: 在 main.ts 中引入 theme.css**

在 `import 'ant-design-vue/dist/reset.css'` 之后添加：

```typescript
import './styles/theme.css'
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/main.ts
git commit -m "feat(dark-mode): import theme CSS variables in main.ts"
```

---

### 任务 4: 修改 App.vue (ConfigProvider + 切换按钮 + 暗色 class)

**文件:**
- 修改: `frontend/src/App.vue`

**改动内容:**
1. 在 `<template>` 中添加 `<a-config-provider>` 包裹 `<router-view>`
2. 在 Header 右侧（头像按钮左边）添加切换按钮
3. 在 `<script>` 中初始化主题 store

- [ ] **Step 1: 修改 App.vue 的 script 部分**

在 `<script setup lang="ts">` 中添加：

```typescript
import { onMounted } from 'vue'
import { ConfigProvider } from 'ant-design-vue'
import { useThemeStore } from './stores/theme'
// ... 原有 imports ...

const themeStore = useThemeStore()

onMounted(() => {
  themeStore.initTheme()
})
```

- [ ] **Step 2: 修改 App.vue 的 template 部分**

找到 `<router-view />`，用 `<a-config-provider>` 包裹：

```vue
<a-config-provider :theme="themeStore.antTheme">
  <router-view />
</a-config-provider>
```

在 Header 右侧，头像按钮左侧添加切换按钮：

```vue
<!-- 日夜间切换按钮（在头像按钮左侧） -->
<button
  class="theme-toggle-btn"
  @click="themeStore.toggleTheme()"
  :title="themeStore.isDark ? '切换到日间模式' : '切换到夜间模式'"
>
  <span class="toggle-icon">{{ themeStore.isDark ? '☀️' : '🌙' }}</span>
</button>

<!-- 原有头像按钮保持不变 -->
```

注意：要在 `@click` 前加上 `.prevent` 或使用 `@click.stop` 防止事件冒泡。上述 template 中找到头像按钮区域，在其前面插入切换按钮。

实际的 template 结构大致为：

```vue
<div class="header-right">
  <button class="theme-toggle-btn" @click="themeStore.toggleTheme()">
    {{ themeStore.isDark ? '☀️' : '🌙' }}
  </button>
  <button class="avatar-btn" @click="goProfile">
    <UserOutlined class="avatar-icon" />
  </button>
</div>
```

- [ ] **Step 3: 修改 App.vue 的全局 style 部分**

在全局 unscoped `<style>` 中添加主题切换按钮样式：

```css
/* 日夜间切换按钮 */
.theme-toggle-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: all 0.3s ease;
  margin-right: 8px;
}
.theme-toggle-btn:hover {
  border-color: var(--brand-orange);
  transform: rotate(15deg);
}
.toggle-icon {
  display: inline-block;
  transition: transform 0.3s ease;
}
```

同时，将全局的硬编码背景色替换为 CSS 变量：

```css
html, body, #app {
  background: var(--bg-page);
}
.main-header {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
}
.header-title {
  color: var(--text-primary);
}
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/App.vue
git commit -m "feat(dark-mode): add ConfigProvider, theme toggle button, and CSS variable backgrounds"
```

---

### 任务 5: 替换 View 文件的颜色 (MainPage + ProfilePage)

**文件:**
- 修改: `frontend/src/views/MainPage.vue`
- 修改: `frontend/src/views/ProfilePage.vue`

**改动:** 将所有硬编码颜色值替换为对应的 `var(--xxx)` CSS 变量。

- [ ] **Step 1: 替换 MainPage.vue 的颜色**

主要替换模式：
- `#fff` → `var(--bg-card)`
- `#1a1a1a` → `var(--text-primary)`
- `#666`, `#555`, `#444` → `var(--text-secondary)`
- `#999`, `#888`, `#bbb` → `var(--text-muted)`
- `#f97316` → `var(--brand-orange)`
- `#ea580c` → `var(--brand-orange-deep)`
- `#fff7ed` → `var(--brand-orange-subtle)`
- `#e8e8e8`, `#eee` → `var(--border-color)`
- `#f0f0f0`, `#f5f5f5` → `var(--bg-subtle)`
- `#f8f9fb`, `#fafafa` → `var(--bg-hover)`
- `#22c55e` → `var(--color-success)`
- `#16a34a` → `var(--color-success-deep)`
- `#dc2626` → `var(--color-error-deep)`
- 阴影 `rgba(0,0,0,0.06)` → `var(--shadow-card)`
- `linear-gradient(135deg, #f97316, #fb923c)` → `linear-gradient(135deg, var(--brand-orange), var(--brand-orange-light))`
- `linear-gradient(90deg, #f97316, #fb923c)` → `linear-gradient(90deg, var(--brand-orange), var(--brand-orange-light))`
- `linear-gradient(135deg, #22c55e, #16a34a)` → `linear-gradient(135deg, var(--color-success), var(--color-success-deep))`

通用（以下所有任务通用此映射表）。

MainPage.vue 的 `.gen-next-btn` 的 `2px dashed #f97316` 替换为 `2px dashed var(--brand-orange)`。

进度条日志的阶段颜色（gen-log-init, gen-log-analysis 等）保持独立颜色不变（它们是日志阶段标识色，不是主题色），但可以选择在暗色下稍微调亮。由于这些颜色在 spec 中没有对应的阶段变量且使用场景特别，保留硬编码但手动加一套暗色覆盖，或者就保持原样 — 这些日志阶段色在暗色背景上可能已经可读。建议暂时保留，后续按需调整。

- [ ] **Step 2: 替换 ProfilePage.vue 的颜色**

同样按上述映射表替换。

特别注意：
- `.profile-goal` 的 `color: #f97316` → `var(--brand-orange)`
- `.avatar-icon` 的渐变保留不变（品牌渐变）
- `.save-all-btn` 的 `linear-gradient(135deg, #f97316, #fb923c)` → `linear-gradient(135deg, var(--brand-orange), var(--brand-orange-light))`
- `.save-all-btn:disabled` 的 `#d9d9d9` → `var(--text-muted)` (近似)

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/MainPage.vue frontend/src/views/ProfilePage.vue
git commit -m "feat(dark-mode): replace hardcoded colors with CSS variables in MainPage and ProfilePage"
```

---

### 任务 6: 替换 View 文件的颜色 (SetupWizard + GeneratingPlan + OnboardingGuide)

**文件:**
- 修改: `frontend/src/views/SetupWizard.vue`
- 修改: `frontend/src/views/GeneratingPlan.vue`
- 修改: `frontend/src/views/OnboardingGuide.vue`

**改动:** 按任务 5 的映射表替换所有硬编码颜色为 CSS 变量。

- [ ] **Step 1: 替换 SetupWizard.vue**

SetupWizard 颜色较多，特别注意：
- 页面背景渐变 `linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%)` — 这是一个装饰性渐变，暗色下改为 `linear-gradient(135deg, #1a1a2e 0%, #141414 100%)`
- `.btn-generate` 绿色渐变 → `linear-gradient(135deg, var(--color-success), var(--color-success-deep))`
- 所有 `.day-chip.active` 的 `#f97316` 背景 → `var(--brand-orange)`
- `.btn-primary` 禁用时的 `#d9d9d9` 背景 → 保留（或使用 `var(--bg-subtle)`）

- [ ] **Step 2: 替换 GeneratingPlan.vue**

注意：
- `.gen-error` 相关颜色（`#fff2f0`, `#ffccc7`, `#cf1322`）→ `var(--color-error-subtle)`, `var(--color-error)`, `var(--color-error-deep)`
- `.gen-done` 相关颜色（`#f0fdf4`, `#22c55e`）→ `var(--color-success-subtle)`, `var(--color-success)`
- `.retry-btn` 的 `#ff4d4f` 系列 → `var(--color-error)`

- [ ] **Step 3: 替换 OnboardingGuide.vue**

较少颜色，主要是 `#f5f7fa` → `var(--bg-page)`，`#fff` → `var(--bg-card)`，`#1a1a1a` → `var(--text-primary)`。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/SetupWizard.vue frontend/src/views/GeneratingPlan.vue frontend/src/views/OnboardingGuide.vue
git commit -m "feat(dark-mode): replace hardcoded colors with CSS variables in SetupWizard, GeneratingPlan, OnboardingGuide"
```

---

### 任务 7: 替换日历组件颜色 (CalendarPanel + DayCell)

**文件:**
- 修改: `frontend/src/components/CalendarPanel.vue`
- 修改: `frontend/src/components/DayCell.vue`

**改动:** 按映射表替换颜色。

- [ ] **Step 1: 替换 CalendarPanel.vue**

- `.calendar-panel` 背景 `#fff` → `var(--bg-card)`
- `.calendar-panel` 阴影 `0 2px 12px rgba(0,0,0,0.08)` → `var(--shadow-card-lg)`
- `.nav-btn` 边框 `#e8e8e8` → `var(--border-color)`
- `.reschedule-toggle.active` 阴影 → `0 2px 8px rgba(217,119,6,0.3)`（暗色下使用暗橙）

- [ ] **Step 2: 替换 DayCell.vue**

- `.day-cell` 背景 `#fff` → `var(--bg-card)`
- `.day-cell.today` 边框 `2px solid #f97316` → `2px solid var(--brand-orange)`
- `.day-cell.completed .day-number` 等橙色文字 → `var(--brand-orange)`
- `.day-cell.missed .day-number` 的 `#ef4444` → `var(--color-error)`
- `.day-cell` 悬停背景 `#fff7ed` → `var(--brand-orange-subtle)`
- 脉冲动画的阴影也要用 CSS 变量替代（注意 animation 中的颜色不支持 var，所以脉冲动画中的 `#f97316` 需要保留硬编码或使用 JS 控制）

对于 `@keyframes pulse-source` 中的 `box-shadow`，由于 CSS 关键帧动画不支持 `var()`，有两种方案：
1. 保留硬编码（动画颜色不影响功能）
2. 将 `@keyframes` 移到 theme.css 中分别在 `:root` 和 `.dark` 下定义

推荐方案 1：保留脉冲动画的硬编码颜色，因为它只出现在重新排期交互过程中，不影响整体主题一致性。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/CalendarPanel.vue frontend/src/components/DayCell.vue
git commit -m "feat(dark-mode): replace colors with CSS variables in CalendarPanel and DayCell"
```

---

### 任务 8: 替换训练面板组件颜色 (DailyPlanPanel + ExerciseRow)

**文件:**
- 修改: `frontend/src/components/DailyPlanPanel.vue`
- 修改: `frontend/src/components/ExerciseRow.vue`

- [ ] **Step 1: 替换 DailyPlanPanel.vue**

- `.daily-plan-panel` → `var(--bg-card)`, `var(--shadow-card-lg)`, `var(--border-color)`
- `.checkin-btn` 渐变 → `var(--brand-orange)`
- `.checkin-btn:disabled` → `var(--text-muted)` 背景
- `.error-msg` → `var(--color-error)`
- `.focus-tag` → `var(--brand-orange-subtle)` 背景, `var(--brand-orange)` 文字
- `.rpe-trend-badge` → `var(--bg-subtle)`
- `.change-summary` → `var(--bg-subtle)`
- `.rest-day`, `.future-day` 文字 → `var(--text-primary)`, `var(--text-secondary)`
- `.date-title` → `var(--text-primary)`

- [ ] **Step 2: 替换 ExerciseRow.vue**

- `.exercise-row` → `var(--bg-card)`, `var(--border-color)`
- `.exercise-row:hover` 边框 → `var(--brand-orange)`
- `.exercise-row.completed` → `var(--color-success-subtle)` 背景, `var(--color-success)` 边框
- `.exercise-row.rpe-easy` → `var(--color-info-subtle)` 背景, `var(--color-info)` 边框
- `.exercise-row.rpe-hard` → `var(--color-error-subtle)` 背景, `var(--color-error)` 边框
- `.checkbox.checked` → `var(--color-success)` 背景/边框
- `.exercise-name` → `var(--text-primary)`
- `.marker-up` → `var(--color-success-subtle)` 背景, `var(--color-success-deep)` 文字
- `.marker-down` → `var(--brand-orange-subtle)` 背景, `var(--brand-orange-deep)` 文字
- `.marker-new` → `var(--color-info-subtle)` 背景, `var(--color-info-deep)` 文字

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/DailyPlanPanel.vue frontend/src/components/ExerciseRow.vue
git commit -m "feat(dark-mode): replace colors with CSS variables in DailyPlanPanel and ExerciseRow"
```

---

### 任务 9: 替换信息组件颜色 (CycleRoadmapNew + CycleInfo + CycleHistory)

**文件:**
- 修改: `frontend/src/components/CycleRoadmapNew.vue`
- 修改: `frontend/src/components/CycleInfo.vue`
- 修改: `frontend/src/components/CycleHistory.vue`

- [ ] **Step 1: 替换 CycleRoadmapNew.vue**

- 卡片背景/边框/阴影 → CSS 变量
- `.cr-desc` 的装饰渐变 `linear-gradient(135deg, #fef7e6 0%, #fff5f5 100%)` → 暗色下改为 `linear-gradient(135deg, #1a1505 0%, #1f0f0f 100%)`（或直接使用 `var(--bg-subtle)`）
- `.cr-desc` 边框 `#ffe8cc` → 暗色下改为 `#3d2e14`
- `.cr-desc-title` 的 `#d97706` → 保持或改为 `var(--brand-orange)`
- 进度条 pending 段的 `#e8e8e8` → `var(--bg-subtle)`

- [ ] **Step 2: 替换 CycleInfo.vue**

- `.week-progress` → `var(--bg-card)`, `var(--border-color)`, `var(--shadow-card)`
- `.wp-bar-fill` 渐变 → `var(--brand-orange)` 渐变
- `.wp-generate-btn` → `var(--brand-orange)` 渐变

- [ ] **Step 3: 替换 CycleHistory.vue**

- 卡片背景/边框 → CSS 变量
- `.history-item:hover` → `var(--bg-hover)`
- `.week-chip` 未选中 → `var(--bg-subtle)` 背景, `var(--text-muted)` 文字
- `.week-chip.completed` → `var(--color-success)` 背景
- `.week-chip.partial` → `var(--brand-orange-subtle)` 背景, `var(--brand-orange)` 文字
- `.week-chip.active` → `var(--brand-orange)` 边框/文字

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/CycleRoadmapNew.vue frontend/src/components/CycleInfo.vue frontend/src/components/CycleHistory.vue
git commit -m "feat(dark-mode): replace colors with CSS variables in CycleRoadmapNew, CycleInfo, CycleHistory"
```

---

### 任务 10: 替换工具组件颜色 (ExerciseDrawer + MuscleDiagram + AIChatPanel)

**文件:**
- 修改: `frontend/src/components/ExerciseDrawer.vue`
- 修改: `frontend/src/components/MuscleDiagram.vue`
- 修改: `frontend/src/components/AIChatPanel.vue`

- [ ] **Step 1: 替换 ExerciseDrawer.vue**

- 所有 `.image-area`, `.single-img`, `.multi-image-main` 的背景/边框 → `var(--bg-subtle)`, `var(--border-color)`
- `.no-image-placeholder` 渐变 → `var(--brand-orange)` 渐变
- `.skeleton-block` → `var(--bg-subtle)`
- `.muscle-section` → `var(--bg-hover)`
- `.info-card` → `var(--bg-hover)`
- `.desc-section` → `var(--bg-card)`, `var(--border-color)`
- `.btn-done` → `var(--color-success)` 背景
- `.btn-undo` 的 `#666` → `var(--text-secondary)` 背景
- `.btn-heavy` → `var(--brand-orange)` 边框/文字

- [ ] **Step 2: 替换 MuscleDiagram.vue**

注意：MuscleDiagram 使用了 `@lucawahlen/vue-human-muscle-anatomy` 组件，其颜色通过 props 传递（`primary-highlight-color`, `secondary-highlight-color`, `default-muscle-color`, `background-color`）。这些需要用 JS 根据主题动态设置。

在组件的 `<script>` 中：

```typescript
const themeStore = useThemeStore()

const muscleColors = computed(() => ({
  primaryHighlightColor: themeStore.isDark ? '#d97706' : '#fb923c',
  secondaryHighlightColor: themeStore.isDark ? '#92400e' : '#fdba74',
  defaultMuscleColor: themeStore.isDark ? '#3a3a3a' : '#e5e5e5',
  backgroundColor: themeStore.isDark ? '#1f1f1f' : '#ffffff',
}))
```

然后将这些 computed 值绑定到 HumanAnatomy 组件的 props 上。

卡片样式替换：
- `.muscle-diagram` → `var(--bg-card)`, `var(--shadow-card-lg)`, `var(--border-color)`
- `.diagram-title` → `var(--text-primary)`
- `.muscle-tooltip` 背景保留黑色 `rgba(0,0,0,0.8)`（工具提示在黑/白背景下都适用）

- [ ] **Step 3: 替换 AIChatPanel.vue**

- `.ai-chat-panel` → `var(--bg-card)`, `var(--shadow-card-lg)`, `var(--border-color)`
- `.chip`（建议标签）→ `var(--brand-orange-subtle)` 背景, `var(--brand-orange)` 文字
- `.chip:hover` → `var(--brand-orange)` 背景, 白色文字
- `.msg-row.user .msg-bubble` → `var(--brand-orange)` 背景, 白色文字
- `.msg-row.ai .msg-bubble` → `var(--bg-subtle)` 背景, `var(--text-primary)` 文字

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/ExerciseDrawer.vue frontend/src/components/MuscleDiagram.vue frontend/src/components/AIChatPanel.vue
git commit -m "feat(dark-mode): replace colors with CSS variables in ExerciseDrawer, MuscleDiagram, AIChatPanel"
```

---

### 任务 11: 替换其余组件颜色 (TodayCard + TrainingKnowledgeCard + NavBar + StepCard*)

**文件:**
- 修改: `frontend/src/components/TodayCard.vue`
- 修改: `frontend/src/components/TrainingKnowledgeCard.vue`
- 修改: `frontend/src/components/NavBar.vue`
- 修改: `frontend/src/components/StepCardPersonal.vue`
- 修改: `frontend/src/components/StepCardGoal.vue`
- 修改: `frontend/src/components/StepCardSchedule.vue`

- [ ] **Step 1: 替换 TodayCard.vue**

- `.today-card` 渐变背景 `linear-gradient(135deg, #fff7ed, #fff)` → `linear-gradient(135deg, var(--brand-orange-subtle), var(--bg-card))`
- `.today-card` 边框 `2px solid #f97316` → `2px solid var(--brand-orange)`
- `.today-card:hover` 阴影 → `0 8px 24px rgba(217,119,6,0.3)`（暗色下阴影）
- `.today-badge` → `var(--brand-orange)` 背景
- `.start-btn` 渐变 → `var(--brand-orange)` 渐变

- [ ] **Step 2: 替换 TrainingKnowledgeCard.vue**

- `.slide` 背景 `#fffcf5` → `var(--brand-orange-subtle)`, 边框 `#fde68a` → `#3d2e14`
- `.dot`（导航圆点）→ `var(--border-color)` 背景, `.dot.active` → `var(--brand-orange)` 背景
- `.ppl-cell`, `.period-cell` → `var(--brand-orange-subtle)` 背景, `#3d2e14` 边框

- [ ] **Step 3: 替换 NavBar.vue（按需）**

NavBar 目前未被使用，但保留更新。将 `#00b09b` 品牌色保留（这不属于主题色体系），其余白色背景/阴影替换为 CSS 变量。

- [ ] **Step 4: 替换 StepCardPersonal/Goal/Schedule.vue**

三个 StepCard 组件颜色较少，主要替换：
- `#1a1a1a` → `var(--text-primary)`
- `#888`, `#999` → `var(--text-muted)`
- `#f97316` → `var(--brand-orange)`
- `#ea580c` → `var(--brand-orange-deep)`
- `#e8e8e8` → `var(--border-color)`
- `#fff` → `var(--bg-card)`
- `#fff7ed` → `var(--brand-orange-subtle)`
- `#d9d9d9` → `var(--bg-subtle)` 或保留（禁用状态）

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/TodayCard.vue frontend/src/components/TrainingKnowledgeCard.vue frontend/src/components/NavBar.vue frontend/src/components/StepCardPersonal.vue frontend/src/components/StepCardGoal.vue frontend/src/components/StepCardSchedule.vue
git commit -m "feat(dark-mode): replace colors with CSS variables in TodayCard, TrainingKnowledgeCard, NavBar, StepCards"
```

---

### 任务 12: 更新 PHASE_COLORS 动态支持暗色

**文件:**
- 修改: `frontend/src/types/index.ts`（或使用 theme store 动态计算）

**问题:** `PHASE_COLORS` 定义在 `types/index.ts` 中，被 `CalendarPanel.vue` 和 `CycleRoadmapNew.vue` 通过内联 style 绑定使用。这些颜色在暗色下需要调整。

**方案:** 不修改 `types/index.ts`（它是纯类型/常量文件），而是在使用组件中根据 `themeStore.isDark` 动态映射。

- [ ] **Step 1: 在 CalendarPanel.vue 中添加暗色阶段色映射**

在 CalendarPanel.vue 中添加：

```typescript
const themeStore = useThemeStore()

function getPhaseColor(phase: string): string {
  const darkMap: Record<string, string> = {
    foundational: '#60a5fa',
    hypertrophy: '#4ade80',
    strength: '#fb923c',
    deload: '#c084fc',
  }
  return themeStore.isDark
    ? (darkMap[phase] || PHASE_COLORS[phase])
    : PHASE_COLORS[phase]
}
```

然后在模板中将 `PHASE_COLORS[phase]` 替换为 `getPhaseColor(phase)`。

- [ ] **Step 2: 同样的逻辑应用到 CycleRoadmapNew.vue**

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/CalendarPanel.vue frontend/src/components/CycleRoadmapNew.vue
git commit -m "feat(dark-mode): add dynamic phase colors for dark mode in CalendarPanel and CycleRoadmapNew"
```

---

### 任务 13: 全局验证

**文件:** 无代码修改

- [ ] **Step 1: 启动后端和前端**

```bash
# 终端1
cd backend && python run.py

# 终端2
cd frontend && npm run dev
```

- [ ] **Step 2: 验证亮色模式**

1. 访问 http://localhost:5173
2. 确认亮色模式下的各页面颜色与改动前一致（无视觉回归）
3. 检查：引导页、主页日历、训练面板、资料页、动作详情 Drawer

- [ ] **Step 3: 验证暗色模式**

1. 点击 Header 的 🌙 按钮切换到暗色
2. 检查以下各页面是否正常：
   - 主页日历（日历格子、今日高亮、已完成标记）
   - 训练面板（动作列表、RPE 按钮、打卡状态）
   - 动作 Drawer（图片、肌群、描述）
   - 资料页（表单、选项按钮）
   - 引导页（步骤卡片、选项卡片）
   - AI 对话面板（消息气泡、建议标签）
3. 刷新页面确认 localStorage 持久化生效

- [ ] **Step 4: 验证系统偏好跟随**

1. 清除 localStorage > 刷新页面
2. 使用浏览器 DevTools → Rendering → Emulate CSS prefers-color-scheme: dark
3. 检查是否正确进入暗色模式

- [ ] **Step 5: 提交最终验证 commit**

```bash
git commit --allow-empty -m "feat(dark-mode): verify dark mode end-to-end across all pages"
```
