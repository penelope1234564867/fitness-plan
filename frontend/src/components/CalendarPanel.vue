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

    <!-- 日历格 -->
    <div class="calendar-grid">
      <div v-for="i in firstDayOfWeek" :key="'empty-' + i" class="day-placeholder"></div>
      <DayCell
        v-for="d in daysInMonth"
        :key="d"
        :day="d"
        :date="formatDate(d)"
        :is-today="formatDate(d) === todayStr"
        :status="getCellStatus(formatDate(d))"
        :focus-icon="getFocusIcon(formatDate(d))"
        :focus-label="getFocusLabel(formatDate(d))"
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
const daysInMonth = computed(() => dayjs(currentMonth.value).daysInMonth())
const firstDayOfWeek = computed(() => dayjs(currentMonth.value + '-01').day())

// 翻月时自动获取日历数据
watch(currentMonth, (month) => {
  const monthStart = dayjs(month + '-01').format('YYYY-MM-DD')
  const monthEnd = dayjs(month + '-01').endOf('month').format('YYYY-MM-DD')
  cycleStore.fetchCalendarData(monthStart, monthEnd)
}, { immediate: true })

/** 从 calendarEntries 找该日期对应的 CalendarEntry */
function getEntry(date: string) {
  return cycleStore.calendarEntries.get(date) ?? null
}

function formatDate(day: number) {
  return `${currentMonth.value}-${String(day).padStart(2, '0')}`
}

function getCellStatus(date: string): DayStatus {
  const entry = getEntry(date)
  if (!entry || !entry.has_plan) return 'pending'
  if (date > todayStr && entry.day_status !== 'completed') return 'future'
  if (entry.day_status === 'completed') return 'completed'
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
.day-placeholder { aspect-ratio: 1; }
</style>
