<template>
  <div class="calendar-panel">
    <!-- 月份导航 -->
    <div class="month-nav">
      <button class="nav-btn" @click="prevMonth">‹</button>
      <h3 class="month-title">{{ monthLabel }}</h3>
      <button class="nav-btn" @click="nextMonth">›</button>
      <button class="today-btn" @click="goToToday">今天</button>
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
        :is-current-month="cd.isCurrentMonth"
        :status="cd.status"
        :focus-icon="cd.focusIcon"
        :focus-label="cd.focusLabel"
        @click="onDayClick"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useCycleStore } from '@/stores/cycle'
import DayCell from './DayCell.vue'
import dayjs from 'dayjs'
import type { DayStatus } from '@/types'

const emit = defineEmits<{ select: [date: string] }>()
const cycleStore = useCycleStore()

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const todayStr = dayjs().format('YYYY-MM-DD')

const currentMonth = ref(dayjs().format('YYYY-MM'))

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

/** 显示的日期数组 */
interface CalendarDay {
  day: number
  date: string
  isCurrentMonth: boolean
  isToday: boolean
  status: DayStatus
  focusIcon?: string
  focusLabel?: string
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

    result.push({
      day: d.date(),
      date: dateStr,
      isCurrentMonth,
      isToday: dateStr === todayStr,
      status: getCellStatus(dateStr),
      focusIcon: getFocusIcon(dateStr),
      focusLabel: getFocusLabel(dateStr),
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
  if (!entry || !entry.has_plan || !entry.focus) return undefined
  for (const [key, icon] of Object.entries(focusIcons)) {
    if (entry.focus.includes(key)) return icon
  }
  return '💪'
}

function getFocusLabel(date: string): string | undefined {
  return getEntry(date)?.focus || undefined
}

function onDayClick(date: string) {
  const entry = getEntry(date)
  if (entry?.has_plan) emit('select', date)
}

function prevMonth() {
  currentMonth.value = dayjs(currentMonth.value).subtract(1, 'month').format('YYYY-MM')
}
function nextMonth() {
  currentMonth.value = dayjs(currentMonth.value).add(1, 'month').format('YYYY-MM')
}
function goToToday() {
  currentMonth.value = dayjs().format('YYYY-MM')
  emit('select', todayStr)
}
</script>

<style scoped>
.calendar-panel {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  border: 1px solid #e8e8e8;
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
  border: 1px solid #e8e8e8; background: #fff;
  cursor: pointer; transition: all 0.2s; padding: 0; line-height: 1;
}
.nav-btn:hover { border-color: #f97316; color: #f97316; }
.month-title { font-size: 16px; font-weight: 700; color: #1a1a1a; margin: 0; min-width: 100px; text-align: center; }
.today-btn { margin-left: 4px; border-radius: 10px; font-size: 12px; height: 26px; padding: 0 10px; border: 1px solid #e8e8e8; background: #fff; cursor: pointer; }
.today-btn:hover { border-color: #f97316; color: #f97316; }

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
  color: #999;
  padding: 2px 0;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
</style>
