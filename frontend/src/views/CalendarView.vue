<template>
  <div class="calendar-container">
    <!-- 无计划空状态 -->
    <div v-if="!hasPlan && !loading" class="empty-state">
      <div class="empty-icon">📅</div>
      <h3>还没有训练计划</h3>
      <p>先去填写个人资料，AI 将为你生成专属计划</p>
      <a-space direction="vertical" style="width: 100%; max-width: 280px;">
        <a-button type="primary" size="large" class="cta-btn" @click="goToOnboarding" block>
          🚀 开始设置
        </a-button>
        <a-button size="large" @click="loadDemo" block>
          👀 预览示例计划
        </a-button>
      </a-space>
    </div>

    <!-- 加载中 -->
    <div v-else-if="loading" class="loading-state">
      <a-spin size="large" />
      <p>加载中...</p>
    </div>

    <!-- 日历 -->
    <div v-else class="calendar-content">
      <!-- 月份导航 -->
      <div class="month-nav">
        <a-button class="nav-btn" @click="prevMonth">‹</a-button>
        <h2 class="month-title">{{ monthLabel }}</h2>
        <a-button class="nav-btn" @click="nextMonth">›</a-button>
        <a-button class="today-btn" size="small" @click="goToToday">今天</a-button>
      </div>

      <!-- 星期头 -->
      <div class="weekday-header">
        <div v-for="w in weekdays" :key="w" class="weekday-label">{{ w }}</div>
      </div>

      <!-- 日历格 -->
      <div class="calendar-grid">
        <!-- 占位格 -->
        <div v-for="i in firstDayOfWeek" :key="'empty-' + i" class="day-placeholder"></div>

        <!-- 日期格 -->
        <DayCell
          v-for="d in daysInMonth"
          :key="d"
          :day="d"
          :date="formatDate(d)"
          :is-today="formatDate(d) === todayStr"
          :status="getDayStatus(formatDate(d))"
          :focus-icon="getFocusIcon(formatDate(d))"
          @click="onDayClick"
        />
      </div>

      <!-- 今日训练卡片 -->
      <div class="today-section" v-if="todayPlan">
        <TodayCard
          :focus-label="todayPlan.isRestDay ? '休息日 🎉' : todayPlan.focusArea"
          :status="getDayStatus(todayStr)"
          :progress-text="getTodayProgressText()"
          @start="startTodayWorkout"
        />
      </div>

      <!-- 错误状态 -->
      <a-alert
        v-if="error"
        type="error"
        :message="error"
        closable
        style="margin-top: 16px;"
        @close="error = null"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkoutStore } from '@/stores/workout'
import { useUserStore } from '@/stores/user'
import DayCell from '@/components/DayCell.vue'
import TodayCard from '@/components/TodayCard.vue'
import dayjs from 'dayjs'

const router = useRouter()
const workoutStore = useWorkoutStore()
const userStore = useUserStore()

const error = ref<string | null>(null)
const loading = ref(false)

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const todayStr = dayjs().format('YYYY-MM-DD')

const hasPlan = computed(() => workoutStore.currentPlan !== null)
const monthLabel = computed(() => workoutStore.monthLabel)
const daysInMonth = computed(() => workoutStore.daysInMonth)
const firstDayOfWeek = computed(() => workoutStore.firstDayOfWeek)
const currentMonth = computed(() => workoutStore.currentMonth)

const todayPlan = computed(() => workoutStore.getDayPlan(todayStr))

const focusIcons: Record<string, string> = {
  '胸部': '🏋️', '背部': '🏋️', '腿部': '🦵', '肩部': '🏋️',
  '手臂': '💪', '腹部': '🔥', '有氧': '🏃', '全身': '💪',
  '上肢': '💪', '下肢': '🦵', '核心': '🔥',
}

onMounted(async () => {
  // 检查是否处于预览模式
  if (localStorage.getItem('fitness_demo_mode') === 'true') {
    workoutStore.loadDemoData()
    return
  }

  // 尝试从 localStorage 恢复计划
  const planId = localStorage.getItem('fitness_current_plan_id')
  if (planId) {
    loading.value = true
    try {
      await workoutStore.fetchPlan(Number(planId))
    } catch {
      // 没有计划，显示空状态
    } finally {
      loading.value = false
    }
  }
})

function formatDate(day: number) {
  return `${currentMonth.value}-${String(day).padStart(2, '0')}`
}

function getDayStatus(date: string) {
  return workoutStore.getDayStatus(date)
}

function getFocusIcon(date: string): string | undefined {
  const plan = workoutStore.getDayPlan(date)
  if (!plan || plan.isRestDay) return undefined

  // 找匹配的图标
  for (const [key, icon] of Object.entries(focusIcons)) {
    if (plan.focusArea.includes(key)) return icon
  }
  return '💪'
}

function getTodayProgressText(): string {
  const plan = workoutStore.getDayPlan(todayStr)
  if (!plan || plan.isRestDay) return '今天是休息日'
  const total = plan.sections.reduce((s, sec) => s + sec.exercises.length, 0)
  const done = plan.sections.reduce((s, sec) => s + sec.exercises.filter(e => e.completed).length, 0)
  if (done === 0) return `${total} 个动作待完成`
  if (done >= total) return '全部完成 🎉'
  return `${done}/${total} 已完成`
}

function onDayClick(date: string) {
  const plan = workoutStore.getDayPlan(date)
  if (!plan) return
  const today = dayjs().format('YYYY-MM-DD')
  if (date > today) return // 未来日期不可操作
  router.push(`/checklist?date=${date}`)
}

function startTodayWorkout() {
  router.push(`/checklist?date=${todayStr}`)
}

function prevMonth() { workoutStore.prevMonth() }
function nextMonth() { workoutStore.nextMonth() }
function goToToday() { workoutStore.goToToday() }

function goToOnboarding() {
  userStore.resetOnboarding()
  router.push('/')
}

function loadDemo() {
  workoutStore.loadDemoData()
}

// 月份切换时检查当月是否有数据
watch(currentMonth, () => {
  // 可以在这里加载当月数据
})
</script>

<style scoped>
.calendar-container {
  max-width: 700px;
  margin: 0 auto;
}

.empty-state, .loading-state {
  text-align: center;
  padding: 80px 20px;
}
.empty-icon { font-size: 80px; margin-bottom: 16px; }
.empty-state h3 { font-size: 22px; color: #333; margin-bottom: 8px; }
.empty-state p { color: #999; margin-bottom: 24px; }
.cta-btn {
  height: 48px; border-radius: 24px; font-size: 16px;
  background: linear-gradient(135deg, #f97316, #fb923c);
  border: none; box-shadow: 0 4px 14px rgba(249,115,22,0.35);
}

.calendar-content {
  background: #fff;
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.month-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 20px;
}
.nav-btn {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; font-size: 20px; font-weight: 700;
  border: 1px solid #e8e8e8; background: #fff;
  cursor: pointer; transition: all 0.2s;
}
.nav-btn:hover { border-color: #f97316; color: #f97316; }
.month-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0; min-width: 120px; text-align: center; }
.today-btn { margin-left: 8px; border-radius: 12px; }

.weekday-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  margin-bottom: 8px;
}
.weekday-label {
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: #999;
  padding: 4px 0;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.day-placeholder { aspect-ratio: 1; }

.today-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
