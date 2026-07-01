<template>
  <div class="daily-plan-panel">
    <!-- 未选择日期 -->
    <div v-if="!dateStr" class="empty-state">
      <span class="empty-icon">📅</span>
      <p>点击日历中的日期查看训练计划</p>
    </div>

    <!-- 没有计划 -->
    <div v-else-if="!dayPlan" class="empty-state">
      <span class="empty-icon">📭</span>
      <p>{{ dateStr }} 没有训练计划</p>
    </div>

    <!-- 休息日 -->
    <div v-else-if="isRestDay" class="rest-day">
      <span class="rest-icon">🎉</span>
      <h2>休息日</h2>
      <p>好好恢复，下次训练效果更好</p>
    </div>

    <!-- 未来日期 -->
    <div v-else-if="isFuture" class="future-day">
      <span class="future-icon">📅</span>
      <h2>未来的计划</h2>
      <p>到了那天再来完成吧</p>
    </div>

    <!-- 计划内容 -->
    <div v-else class="plan-content">
      <!-- 日期头部 -->
      <div class="plan-header">
        <h2 class="date-title">{{ dateTitle }}</h2>
        <span class="focus-tag">{{ dayPlan.focus }}</span>
      </div>

      <!-- 训练区块 -->
      <div v-if="dayPlan.warmup.length" class="section-block">
        <h3 class="section-title">🔥 热身</h3>
        <div class="exercise-list">
          <ExerciseRow
            v-for="(ex) in dayPlan.warmup"
            :key="ex.id"
            :exercise="ex"
            @toggle="workoutStore.toggleExercise(ex.id)"
          />
        </div>
      </div>

      <div v-if="dayPlan.main.length" class="section-block">
        <h3 class="section-title">💪 主训练</h3>
        <div class="exercise-list">
          <ExerciseRow
            v-for="(ex) in dayPlan.main"
            :key="ex.id"
            :exercise="ex"
            @toggle="workoutStore.toggleExercise(ex.id)"
            @set-rpe-quick="(v) => workoutStore.setRPEQuick(ex.id, v)"
            @show-detail="openDrawer(ex)"
          />
        </div>
      </div>

      <div v-if="dayPlan.cardio" class="section-block">
        <h3 class="section-title">🏃 有氧收尾</h3>
        <div class="exercise-list">
          <ExerciseRow :exercise="dayPlan.cardio" @toggle="workoutStore.toggleExercise(dayPlan.cardio!.id)" />
        </div>
      </div>

      <div v-if="dayPlan.stretch.length" class="section-block">
        <h3 class="section-title">🧘 拉伸</h3>
        <div class="exercise-list">
          <ExerciseRow
            v-for="(ex) in dayPlan.stretch"
            :key="ex.id"
            :exercise="ex"
            @toggle="workoutStore.toggleExercise(ex.id)"
          />
        </div>
      </div>

      <!-- RPE 说明 -->
      <div class="rpe-hint">
        <span class="rpe-hint-icon">ℹ️</span>
        <span class="rpe-hint-text">
          😊 太轻松 → 加重量 &nbsp;|&nbsp; ✔ 正常完成 → 加次数 &nbsp;|&nbsp; 😰 太重了 → 减量
        </span>
      </div>

      <!-- 提交打卡 -->
      <button
        class="checkin-btn"
        :disabled="checkinLoading || noFeedback"
        @click="handleCheckin"
      >
        {{ checkinLoading ? '⏳ 提交中...' : '📝 提交打卡' }}
      </button>

      <p v-if="noFeedback && !checkinLoading" class="checkin-hint">
        请至少完成一个动作再提交
      </p>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 动作详情抽屉（精细调整用） -->
    <ExerciseDrawer
      v-if="drawerExercise"
      :visible="drawerVisible"
      :exercise="drawerExercise as any"
      @close="drawerVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useWorkoutStore } from '@/stores/workout'
import ExerciseRow from './ExerciseRow.vue'
import ExerciseDrawer from './ExerciseDrawer.vue'
import type { ExerciseSlot } from '@/types'
import dayjs from 'dayjs'

const props = defineProps<{ dateStr: string | null }>()
const workoutStore = useWorkoutStore()
const todayStr = dayjs().format('YYYY-MM-DD')

const drawerVisible = ref(false)
const drawerExercise = ref<ExerciseSlot | null>(null)
const error = ref<string | null>(null)

// 设置 selectedDate 以驱动 workoutStore 通过 dayDetail API 获取数据
watch(() => props.dateStr, (val) => {
  workoutStore.selectedDate = val
}, { immediate: true })

const dayPlan = computed(() => workoutStore.currentDay)
const dayDetail = computed(() => workoutStore.dayDetail)

const isRestDay = computed(() => {
  const dd = dayDetail.value
  if (!dd) return false
  return !dd.has_plan
})
const isFuture = computed(() => !!props.dateStr && props.dateStr > todayStr)

const dateTitle = computed(() => {
  if (!props.dateStr) return ''
  const d = dayjs(props.dateStr)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.format('M月D日')} ${weekdays[d.day()]}`
})

const checkinLoading = computed(() => workoutStore.checkinLoading)
const noFeedback = computed(() => {
  if (!dayPlan.value) return true
  return !dayPlan.value.slots.some(s => s._completed || s._rpeQuick)
})

async function handleCheckin() {
  try {
    error.value = null
    await workoutStore.submitCheckin()
  } catch (e: any) {
    error.value = e.message || '打卡失败'
  }
}

function openDrawer(ex: ExerciseSlot) {
  drawerExercise.value = ex
  drawerVisible.value = true
}
</script>

<style scoped>
.daily-plan-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  border: 1px solid #e8e8e8;
  padding: 20px;
  overflow-y: auto;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #bbb;
  text-align: center;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { font-size: 14px; margin: 0; }

.rest-day, .future-day {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.rest-icon, .future-icon { font-size: 56px; margin-bottom: 12px; }
.rest-day h2, .future-day h2 { font-size: 20px; color: #333; margin: 0 0 8px 0; }
.rest-day p, .future-day p { color: #999; margin: 0; }

.plan-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.date-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0; }
.focus-tag {
  padding: 3px 12px; border-radius: 20px;
  background: #fff7ed; color: #f97316;
  font-size: 12px; font-weight: 600;
}

.section-block { margin-bottom: 14px; }
.section-title {
  font-size: 14px; font-weight: 700; color: #555;
  margin: 0 0 6px 4px;
}
.exercise-list { display: flex; flex-direction: column; gap: 4px; }

.rpe-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 8px;
  margin: 8px 0 12px;
  font-size: 11px;
  color: #888;
  line-height: 1.4;
}
.rpe-hint-icon { font-size: 14px; flex-shrink: 0; }

.checkin-btn {
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: none;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  transition: all 0.2s;
}
.checkin-btn:hover:not(:disabled) { box-shadow: 0 4px 14px rgba(249,115,22,0.35); transform: translateY(-1px); }
.checkin-btn:disabled { background: #d9d9d9; color: #999; cursor: not-allowed; }
.checkin-hint { text-align: center; font-size: 12px; color: #999; margin: 6px 0 0; }
.error-msg { color: #ef4444; font-size: 13px; text-align: center; margin-top: 8px; }
</style>
