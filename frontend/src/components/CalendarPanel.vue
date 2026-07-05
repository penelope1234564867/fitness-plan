<template>
  <div class="calendar-panel">
    <!-- 月份导航 -->
    <div class="month-nav">
      <button class="nav-btn" @click="prevMonth">‹</button>
      <h3 class="month-title">{{ monthLabel }}</h3>
      <button class="nav-btn" @click="nextMonth">›</button>
      <button
        class="reschedule-toggle"
        :class="{ active: rescheduleMode }"
        @click="toggleRescheduleMode"
      >
        {{ rescheduleMode ? '退出调整' : '调整日期' }}
      </button>
    </div>

    <!-- 星期头 -->
    <div class="weekday-header">
      <div v-for="w in weekdays" :key="w" class="weekday-label">{{ w }}</div>
    </div>

    <!-- 日历格（完整周） -->
    <div class="calendar-grid">
      <DayCell
        v-for="cd in calendarDays"
        :key="cd.date"
        :day="cd.day"
        :date="cd.date"
        :is-today="cd.isToday"
        :is-selected="cd.isSelected"
        :is-current-month="cd.isCurrentMonth"
        :status="cd.status"
        :focus-icon="cd.focusIcon"
        :focus-label="cd.focusLabel"
        :phase-color="cd.phaseColor"
        :reschedule-state="cd.rescheduleState"
        @click="onDayClick"
    />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useCycleStore } from '@/stores/cycle'
import DayCell from './DayCell.vue'
import dayjs from 'dayjs'
import * as api from '@/services/api'
import type { DayStatus } from '@/types'
import { PHASE_COLORS } from '@/types'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

const emit = defineEmits<{ select: [date: string] }>()
const cycleStore = useCycleStore()

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const todayStr = dayjs().format('YYYY-MM-DD')

const currentMonth = ref(dayjs().format('YYYY-MM'))
const selectedDate = ref<string | null>(null)

// 调整日期模式
const rescheduleMode = ref(false)
const sourceDate = ref<string | null>(null)
const sourceDayId = ref<number | null>(null)

/** 目标日映射：dateStr → 'available' | 'occupied' | 'expired' */
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

    if (date === sourceDate.value) continue
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

const focusIcons: Record<string, string> = {
  '胸部': '🏋️', '背部': '🏋️', '腿部': '🦵', '肩部': '🏋️',
  '手臂': '💪', '腹部': '🔥', '有氧': '🏃', '全身': '💪',
  '上肢': '💪', '下肢': '🦵', '核心': '🔥',
}

const monthLabel = computed(() => dayjs(currentMonth.value).format('YYYY年M月'))

/** 当月最后一天的日期字符串 */
const lastDateOfMonth = computed(() =>
  dayjs(currentMonth.value + '-01').endOf('month').format('YYYY-MM-DD'),
)

/** 可见范围：包含当月完整周的起始日期（周日） */
const firstVisibleDate = computed(() =>
  dayjs(currentMonth.value + '-01').startOf('week').format('YYYY-MM-DD'),
)

/** 可见范围：包含当月完整周的结束日期（周六） */
const lastVisibleDate = computed(() =>
  dayjs(lastDateOfMonth.value).endOf('week').format('YYYY-MM-DD'),
)

/** 根据主题返回阶段色 */
function getPhaseColor(phase: string): string {
  if (!themeStore.isDark) return PHASE_COLORS[phase] || '#999'
  const darkMap: Record<string, string> = {
    foundational: '#60a5fa',
    hypertrophy: '#4ade80',
    strength: '#fb923c',
    deload: '#c084fc',
  }
  return darkMap[phase] || PHASE_COLORS[phase] || '#999'
}

/** 显示的日期数组 */
interface CalendarDay {
  day: number
  date: string
  isCurrentMonth: boolean
  isToday: boolean
  isSelected: boolean
  status: DayStatus
  focusIcon?: string
  focusLabel?: string
  phaseColor?: string
  rescheduleState?: 'source' | 'target-available' | 'target-occupied' | 'target-expired'
}
const calendarDays = computed<CalendarDay[]>(() => {
  const start = dayjs(firstVisibleDate.value)
  const end = dayjs(lastVisibleDate.value)
  const totalDays = end.diff(start, 'day') + 1
  const currentMonthStr = currentMonth.value

  const result: CalendarDay[] = []
  for (let i = 0; i < totalDays; i++) {
    const d = start.add(i, 'day')
    const dateStr = d.format('YYYY-MM-DD')
    const isCurrentMonth = d.format('YYYY-MM') === currentMonthStr

    const entry = getEntry(dateStr)

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
      isSelected: dateStr === selectedDate.value,
      status: getCellStatus(dateStr),
      focusIcon: getFocusIcon(dateStr),
      focusLabel: getFocusLabel(dateStr),
      phaseColor: entry?.mesocycle_phase ? getPhaseColor(entry.mesocycle_phase) : undefined,
      rescheduleState,
    })
  }
  return result
})

// 翻月时获取完整跨月范围的数据
watch(currentMonth, (month) => {
  const from = dayjs(month + '-01').startOf('week').format('YYYY-MM-DD')
  const to = dayjs(month + '-01').endOf('month').endOf('week').format('YYYY-MM-DD')
  cycleStore.fetchCalendarData(from, to)
}, { immediate: true })

/** 从 calendarEntries 找该日期对应的 CalendarEntry */
function getEntry(date: string) {
  return cycleStore.calendarEntries.get(date) ?? null
}

function getCellStatus(date: string): DayStatus {
  const entry = getEntry(date)
  if (!entry || !entry.has_plan) return 'pending'
  if (entry.day_status === 'rest') return 'rest'
  if (date > todayStr && entry.day_status !== 'completed') return 'future'
  if (entry.day_status === 'completed') return 'completed'
  if (entry.day_status === 'partial') return 'partial'
  if (entry.day_status === 'missed') return 'missed'
  return 'pending'
}

function getFocusIcon(date: string): string | undefined {
  const entry = getEntry(date)
  // 有计划但 focus 为空（如骨架周预创建的 day 4/5），兜底显示 💪
  if (!entry || !entry.has_plan) return undefined
  if (!entry.focus) return '💪'
  for (const [key, icon] of Object.entries(focusIcons)) {
    if (entry.focus.includes(key)) return icon
  }
  return '💪'
}

function getFocusLabel(date: string): string | undefined {
  return getEntry(date)?.focus || undefined
}

function onDayClick(date: string) {
  selectedDate.value = date
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
  } else if (entry?.has_plan && entry.day_status !== 'completed') {
    // 点击另一个训练日 → 重新选源
    sourceDate.value = date
    try {
      const detail = await api.fetchDayDetail(date)
      sourceDayId.value = detail.day_id
    } catch {
      exitRescheduleMode()
    }
  }
}

async function doReschedule(targetDate: string) {
  if (!sourceDayId.value) { exitRescheduleMode(); return }

  const d = dayjs(targetDate)
  const jsDay = d.day()
  const newDayOfWeek = jsDay || 7

  try {
    await api.rescheduleDay(sourceDayId.value, { day_of_week: newDayOfWeek })

    // 刷新本周日历数据
    const monday = dayjs(sourceDate.value!).subtract((dayjs(sourceDate.value!).day() || 7) - 1, 'day')
    await cycleStore.fetchCalendarData(
      monday.format('YYYY-MM-DD'),
      monday.add(6, 'day').format('YYYY-MM-DD'),
    )

    exitRescheduleMode()
    emit('select', targetDate)
  } catch (e: any) {
    console.error('[Reschedule] 调整失败:', e.message)
    exitRescheduleMode()
  }
}

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

function prevMonth() {
  if (rescheduleMode.value) exitRescheduleMode()
  currentMonth.value = dayjs(currentMonth.value).subtract(1, 'month').format('YYYY-MM')
}
function nextMonth() {
  if (rescheduleMode.value) exitRescheduleMode()
  currentMonth.value = dayjs(currentMonth.value).add(1, 'month').format('YYYY-MM')
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && rescheduleMode.value) {
    exitRescheduleMode()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.calendar-panel {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 16px;
  box-shadow: var(--shadow-card-lg);
  border: 1px solid var(--border-color);
}

.month-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 14px;
}
.nav-btn {
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; font-size: 16px; font-weight: 700;
  border: 1px solid var(--border-color); background: var(--bg-card);
  cursor: pointer; transition: all 0.2s; padding: 0; line-height: 1;
}
.nav-btn:hover { border-color: var(--brand-orange); color: var(--brand-orange); }
.month-title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin: 0; min-width: 100px; text-align: center; }
.reschedule-toggle {
  margin-left: 4px;
  border-radius: 10px;
  font-size: 12px;
  height: 28px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
  color: var(--brand-orange);
  white-space: nowrap;
}
.reschedule-toggle:hover {
  border-color: var(--brand-orange);
  background: var(--brand-orange-subtle);
}
.reschedule-toggle.active {
  background: var(--brand-orange);
  color: var(--text-inverse);
  border-color: var(--brand-orange);
  box-shadow: 0 2px 8px rgba(217,119,6,0.3);
}

.weekday-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  margin-bottom: 6px;
}
.weekday-label {
  text-align: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 2px 0;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
</style>
