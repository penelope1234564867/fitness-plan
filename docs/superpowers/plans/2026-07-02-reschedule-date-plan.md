# 调整训练日 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在日历面板上实现"调整模式"，用户两步操作（选源日 → 选目标日）把训练迁到本周空闲日期。

**Architecture:** 所有改动集中在 `CalendarPanel.vue` + `DayCell.vue`，复用已有的 `workoutStore.rescheduleDay` + 后端 API。不修改后端。

**Tech Stack:** Vue 3 + TypeScript + Pinia + dayjs

## 全局约束

- 只能调整到**本周内**的空闲日期
- 已过期日期（`date < today`）不可作为目标
- 已有训练的日期不可作为目标
- 已完成打卡的训练日不可作为源
- 所有操作在日历网格上完成，不依赖侧边面板

---

### Task 1: 更新 DayCell.vue — 添加调整模式视觉状态

**文件：**
- Modify: `frontend/src/components/DayCell.vue`

**Interfaces:**
- Consumes: 现有 DayCell 全部 props
- Produces: 新增 props → `rescheduleState` 控制 CSS 类

- [ ] **Step 1: 新增 props 和 reschedule 相关 CSS 类**

在 `DayCell.vue` 的 script 中新增 prop：

```typescript
const props = defineProps<{
  day: number
  date: string
  isToday: boolean
  isCurrentMonth?: boolean
  status: 'rest' | 'pending' | 'partial' | 'completed' | 'missed' | 'future'
  focusIcon?: string
  focusLabel?: string
  phaseColor?: string
  // 新增：调整模式状态
  rescheduleState?: 'source' | 'target-available' | 'target-occupied' | 'target-expired'
}>()
```

同时更新 template 内容，添加调整模式的 CSS 类（在现有 class 绑定中加入基于 `rescheduleState` 的类）：

```diff
  <div
    class="day-cell"
    :class="[
      status,
      {
        today: isToday,
        hasPlan: !!focusIcon,
        'adjacent-month': !isCurrentMonth,
+       'reschedule-source': rescheduleState === 'source',
+       'reschedule-target-available': rescheduleState === 'target-available',
+       'reschedule-target-occupied': rescheduleState === 'target-occupied',
+       'reschedule-target-expired': rescheduleState === 'target-expired',
      },
    ]"
  >
```

在 template 中，如果处于调整模式且为 target-available，显示"空闲"标签：

```diff
  <span v-if="focusIcon && status !== 'rest'" class="day-icon" :title="focusLabel">{{ focusIcon }}</span>
  <span v-else-if="status === 'rest'" class="day-icon rest-icon" title="休息日">☕</span>
  <span v-if="phaseColor" class="phase-dot" :style="{ background: phaseColor }" />
+ <span v-if="rescheduleState === 'target-available'" class="reschedule-badge">空闲</span>
+ <span v-if="rescheduleState === 'source'" class="reschedule-badge source-badge">移动此日</span>
```

在 style 末尾添加调整模式的 CSS：

```css
/* ═══ 调整模式 ═══ */
.day-cell.reschedule-source {
  border-color: #f97316;
  box-shadow: 0 0 0 2px #f97316, 0 0 12px rgba(249,115,22,0.3);
  animation: pulse-source 1.5s ease-in-out infinite;
}
@keyframes pulse-source {
  0%, 100% { box-shadow: 0 0 0 2px #f97316, 0 0 12px rgba(249,115,22,0.3); }
  50% { box-shadow: 0 0 0 4px #f97316, 0 0 20px rgba(249,115,22,0.5); }
}

.day-cell.reschedule-target-available {
  background: #f0fdf4;
  border-color: #22c55e;
  cursor: pointer !important;
}
.day-cell.reschedule-target-available:hover {
  background: #dcfce7;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(34,197,94,0.25);
}

.day-cell.reschedule-target-occupied {
  opacity: 0.4;
  cursor: not-allowed !important;
}
.day-cell.reschedule-target-expired {
  opacity: 0.3;
  cursor: not-allowed !important;
  background: repeating-linear-gradient(45deg, transparent, transparent 3px, #f5f5f5 3px, #f5f5f5 6px);
}
.day-cell.reschedule-target-expired:hover {
  background: repeating-linear-gradient(45deg, transparent, transparent 3px, #f5f5f5 3px, #f5f5f5 6px);
  border-color: transparent;
  transform: none;
  box-shadow: none;
}

.reschedule-badge {
  position: absolute;
  top: 1px;
  right: 1px;
  font-size: 8px;
  padding: 0 4px;
  border-radius: 6px;
  line-height: 14px;
  font-weight: 700;
  white-space: nowrap;
  pointer-events: none;
}
.reschedule-badge.source-badge {
  background: #f97316;
  color: #fff;
  bottom: 1px;
  top: auto;
  right: 1px;
  font-size: 7px;
  padding: 0 3px;
}
.day-cell.reschedule-target-available .reschedule-badge {
  background: #22c55e;
  color: #fff;
}
```

---

### Task 2: 改造 CalendarPanel.vue — 调整模式 + 两步操作

**文件：**
- Modify: `frontend/src/components/CalendarPanel.vue`

**Interfaces:**
- Consumes: `cycleStore`（calendarEntries, fetchCalendarData）, `workoutStore`（rescheduleDay — 在 onDayClick 中调用）
- Produces: 更新后的日历网格

- [ ] **Step 1: 替换「今天」按钮为「调整日期」按钮**

修改 template 中的导航栏：

```diff
  <div class="month-nav">
    <button class="nav-btn" @click="prevMonth">‹</button>
    <h3 class="month-title">{{ monthLabel }}</h3>
    <button class="nav-btn" @click="nextMonth">›</button>
-   <button class="today-btn" @click="goToToday">今天</button>
+   <button
+     class="reschedule-toggle"
+     :class="{ active: rescheduleMode }"
+     @click="toggleRescheduleMode"
+   >
+     {{ rescheduleMode ? '退出调整' : '调整日期' }}
+   </button>
  </div>
```

- [ ] **Step 2: 新增 import 和状态 ref 和 computed**

在文件顶部的 import 区域添加：

```typescript
import * as api from '@/services/api'
```

在 script 的 `const currentMonth = ref(...)` 后面添加：

```typescript
// 调整日期模式
const rescheduleMode = ref(false)
const sourceDate = ref<string | null>(null)
const sourceDayId = ref<number | null>(null)

// 调整模式下的目标日 Map: dateStr → 'available' | 'occupied' | 'expired'
const targetDates = computed<Map<string, string>>(() => {
  const map = new Map<string, string>()
  if (!rescheduleMode.value || !sourceDate.value) return map

  const d = dayjs(sourceDate.value)
  const jsDay = d.day()
  const dayOfWeek = jsDay || 7
  const monday = d.subtract(dayOfWeek - 1, 'day')

  for (let i = 0; i < 7; i++) {
    const date = monday.add(i, 'day').format('YYYY-MM-DD')
    const entry = getEntry(date)
    const hasPlan = entry?.has_plan || false

    if (date === sourceDate.value) continue  // 源日在 DayCell 中通过 rescheduleState='source' 显示
    if (hasPlan) {
      map.set(date, 'occupied')
    } else if (date < todayStr) {
      map.set(date, 'expired')
    } else {
      map.set(date, 'available')
    }
  }
  return map
})
```

- [ ] **Step 3: 修改 `calendarDays` computed，传入 `rescheduleState` 到 DayCell**

在 `calendarDays` computed 的循环中，在 `result.push` 之前添加 rescheduleState：

```typescript
    // 调整模式状态
    let rescheduleState: CalendarDay['rescheduleState']
    if (rescheduleMode.value && sourceDate.value) {
      if (dateStr === sourceDate.value) {
        rescheduleState = 'source'
      } else {
        const t = targetDates.value.get(dateStr)
        if (t === 'available') rescheduleState = 'target-available'
        else if (t === 'occupied') rescheduleState = 'target-occupied'
        else if (t === 'expired') rescheduleState = 'target-expired'
      }
    }

    result.push({
      day: d.date(),
      date: dateStr,
      isCurrentMonth,
      isToday: dateStr === todayStr,
      status: getCellStatus(dateStr),
      focusIcon: getFocusIcon(dateStr),
      focusLabel: getFocusLabel(dateStr),
      phaseColor: entry?.mesocycle_phase ? (PHASE_COLORS[entry.mesocycle_phase] || undefined) : undefined,
      rescheduleState,  // 传给 DayCell
    })
```

同时更新 template 中 DayCell 的绑定：

```diff
  <DayCell
    v-for="cd in calendarDays"
    :key="cd.date"
    :day="cd.day"
    :date="cd.date"
    :is-today="cd.isToday"
    :is-current-month="cd.isCurrentMonth"
    :status="cd.status"
    :focus-icon="cd.focusIcon"
    :focus-label="cd.focusLabel"
    :phase-color="cd.phaseColor"
+   :reschedule-state="cd.rescheduleState"
    @click="onDayClick"
  />
```

更新 `CalendarDay` 接口：

```diff
  interface CalendarDay {
    day: number
    date: string
    isCurrentMonth: boolean
    isToday: boolean
    status: DayStatus
    focusIcon?: string
    focusLabel?: string
    phaseColor?: string
+   rescheduleState?: 'source' | 'target-available' | 'target-occupied' | 'target-expired'
  }
```

- [ ] **Step 4: 改造 `onDayClick` — 区分正常模式/调整模式**

```typescript
function onDayClick(date: string) {
  if (rescheduleMode.value) {
    handleRescheduleClick(date)
  } else {
    emit('select', date)
  }
}

async function handleRescheduleClick(date: string) {
  const entry = getEntry(date)

  // 第一步：选源日（有训练的、未完成的）
  if (!sourceDate.value) {
    if (!entry?.has_plan) return
    if (entry.day_status === 'completed') return

    sourceDate.value = date
    // 立即获取 day_id（API 很快，用户选目标日前已就绪）
    try {
      const detail = await api.fetchDayDetail(date)
      sourceDayId.value = detail.day_id
    } catch {
      exitRescheduleMode()
    }
    return
  }

  // 第二步：选目标日
  const targetState = targetDates.value.get(date)
  if (targetState === 'available') {
    await doReschedule(date)
  }
}

/** 执行调整 */
async function doReschedule(targetDate: string) {
  if (!sourceDayId.value) { exitRescheduleMode(); return }

  const d = dayjs(targetDate)
  const jsDay = d.day()
  const newDayOfWeek = jsDay || 7

  try {
    await api.rescheduleDay(sourceDayId.value, { day_of_week: newDayOfWeek })

    // 刷新日历数据
    const monday = dayjs(sourceDate.value).subtract((dayjs(sourceDate.value).day() || 7) - 1, 'day')
    const weekEnd = monday.add(6, 'day').format('YYYY-MM-DD')
    await cycleStore.fetchCalendarData(monday.format('YYYY-MM-DD'), weekEnd)

    // 退出调整模式
    exitRescheduleMode()

    // 如果目标日就是当前选中日，刷新详情；否则跳转到目标日
    emit('select', targetDate)
  } catch (e: any) {
    console.error('[Reschedule] 调整失败:', e.message)
    // 失败时退出
    exitRescheduleMode()
  }
}

/** 退出调整模式 */
function exitRescheduleMode() {
  rescheduleMode.value = false
  sourceDate.value = null
  sourceDayId.value = null
}

function toggleRescheduleMode() {
  if (rescheduleMode.value) {
    exitRescheduleMode()
  } else {
    rescheduleMode.value = true
  }
}
```

- [ ] **Step 5: 修改 `goToToday` 并添加 ESC 键退出**

`goToToday` 不应受调整模式影响，但如果用户在调整模式点击导航翻月，应该退出调整模式：

```diff
  function prevMonth() {
+   if (rescheduleMode.value) exitRescheduleMode()
    currentMonth.value = dayjs(currentMonth.value).subtract(1, 'month').format('YYYY-MM')
  }
  function nextMonth() {
+   if (rescheduleMode.value) exitRescheduleMode()
    currentMonth.value = dayjs(currentMonth.value).add(1, 'month').format('YYYY-MM')
  }
```

添加键盘 ESC 退出（在 `onMounted` 或模板 `@keydown` 中）：

```typescript
import { onMounted, onUnmounted } from 'vue'

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && rescheduleMode.value) {
    exitRescheduleMode()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
```

- [ ] **Step 6: 新增 CSS 样式**

在 style 末尾添加：

```css
/* ═══ 调整日期按钮 ═══ */
.reschedule-toggle {
  margin-left: 4px;
  border-radius: 10px;
  font-size: 12px;
  height: 28px;
  padding: 0 12px;
  border: 1px solid #e8e8e8;
  background: #fff;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  color: #f97316;
  white-space: nowrap;
}
.reschedule-toggle:hover {
  border-color: #f97316;
  background: #fff7ed;
}
.reschedule-toggle.active {
  background: #f97316;
  color: #fff;
  border-color: #f97316;
  box-shadow: 0 2px 8px rgba(249,115,22,0.3);
}
```

- [ ] **Step 7: 验证改动**

```bash
cd C:/Users/18194/Desktop/fitness-plan/frontend && npx vue-tsc --noEmit 2>&1 | grep -i error | grep -v "node_modules"
```

预期：无新增错误（只有已有的预存错误）

---

### Task 3: 恢复 DailyPlanPanel 的调整按钮（可选清理）

**文件：**
- Modify: `frontend/src/components/DailyPlanPanel.vue`

之前的 "📅 调整" 按钮现在移到日历面板了，DailyPlanPanel 里不再需要。可选删除以保持代码干净：

删除 DailyPlanPanel.vue 模板中的「调整日期」button 和 `reschedule-grid` div，以及 script 中的 `showRescheduler`、`weekDays`、`isDayCompleted`、`doReschedule`。保留 `cycleStore` 导入（后续可能用到）。

或者保留它们作为备选入口（不做改动）。由开发者决定。

---

### 执行交接

Plan 完成。两种执行方式：

1. **Subagent-Driven（推荐）** — 为每个 task 派生子 agent，审阅后再继续，快速迭代
2. **Inline Execution** — 在当前会话中按任务逐步执行，每个 checkpoint 确认
