<template>
  <div class="calendar-panel">
    <!-- 月份导航 -->
    <div class="month-nav">
      <a-button class="nav-btn" @click="workoutStore.prevMonth()">‹</a-button>
      <h3 class="month-title">{{ workoutStore.monthLabel }}</h3>
      <a-button class="nav-btn" @click="workoutStore.nextMonth()">›</a-button>
      <a-button class="today-btn" size="small" @click="goToToday">今天</a-button>
    </div>

    <!-- 星期头 -->
    <div class="weekday-header">
      <div v-for="w in weekdays" :key="w" class="weekday-label">{{ w }}</div>
    </div>

    <!-- 日历格 -->
    <div class="calendar-grid">
      <div v-for="i in workoutStore.firstDayOfWeek" :key="'empty-' + i" class="day-placeholder"></div>
      <DayCell
        v-for="d in workoutStore.daysInMonth"
        :key="d"
        :day="d"
        :date="formatDate(d)"
        :is-today="formatDate(d) === todayStr"
        :status="getDayStatus(formatDate(d))"
        :focus-icon="getFocusIcon(formatDate(d))"
        :focus-label="getFocusLabel(formatDate(d))"
        @click="onDayClick"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWorkoutStore } from '@/stores/workout'
import DayCell from './DayCell.vue'
import dayjs from 'dayjs'

const emit = defineEmits<{ select: [date: string] }>()
const workoutStore = useWorkoutStore()

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const todayStr = dayjs().format('YYYY-MM-DD')

const focusIcons: Record<string, string> = {
  '胸部': '🏋️', '背部': '🏋️', '腿部': '🦵', '肩部': '🏋️',
  '手臂': '💪', '腹部': '🔥', '有氧': '🏃', '全身': '💪',
  '上肢': '💪', '下肢': '🦵', '核心': '🔥',
}

function formatDate(day: number) {
  return `${workoutStore.currentMonth}-${String(day).padStart(2, '0')}`
}

function getDayStatus(date: string) {
  return workoutStore.getDayStatus(date)
}

function getFocusIcon(date: string): string | undefined {
  const plan = workoutStore.getDayPlan(date)
  if (!plan || plan.isRestDay) return undefined
  for (const [key, icon] of Object.entries(focusIcons)) {
    if (plan.focusArea.includes(key)) return icon
  }
  return '💪'
}

function getFocusLabel(date: string): string | undefined {
  const plan = workoutStore.getDayPlan(date)
  if (!plan || plan.isRestDay) return undefined
  return plan.focusArea
}

function onDayClick(date: string) {
  const plan = workoutStore.getDayPlan(date)
  if (plan) {
    emit('select', date)
  }
}

function goToToday() {
  workoutStore.goToToday()
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
  cursor: pointer; transition: all 0.2s; padding: 0;
}
.nav-btn:hover { border-color: #f97316; color: #f97316; }
.month-title { font-size: 16px; font-weight: 700; color: #1a1a1a; margin: 0; min-width: 100px; text-align: center; }
.today-btn { margin-left: 4px; border-radius: 10px; font-size: 12px; height: 26px; padding: 0 10px; }

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
