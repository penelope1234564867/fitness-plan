<template>
  <div class="daily-plan-panel">
    <!-- 未选择日期 -->
    <div v-if="!dateStr" class="empty-state">
      <span class="empty-icon">📅</span>
      <p>点击日历中的日期查看训练计划</p>
    </div>

    <!-- 没有计划 -->
    <div v-else-if="!plan && !loading" class="empty-state">
      <span class="empty-icon">📭</span>
      <p>{{ dateStr }} 没有训练计划</p>
    </div>

    <!-- 加载中 -->
    <div v-else-if="loading" class="loading-state">
      <a-spin size="large" />
      <p>加载中...</p>
    </div>

    <!-- 休息日 -->
    <div v-else-if="plan?.isRestDay" class="rest-day">
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
    <div v-else-if="plan" class="plan-content">
      <!-- 日期头部 -->
      <div class="plan-header">
        <h2 class="date-title">{{ dateTitle }}</h2>
        <span class="focus-tag">{{ plan.focusArea }}</span>
      </div>

      <!-- 进度条 -->
      <div class="progress-section">
        <a-progress
          :percent="progressPercent"
          :stroke-color="progressPercent >= 100 ? '#22c55e' : '#f97316'"
          :stroke-width="8"
          :format="() => `${doneCount}/${totalCount}`"
        />
        <p v-if="progressPercent >= 100" class="complete-text">🎉 全部完成！</p>
      </div>

      <!-- 训练区块 -->
      <div v-for="(section, si) in plan.sections" :key="si" class="section-block">
        <h3 class="section-title">{{ section.label }}</h3>
        <div class="exercise-list">
          <ExerciseRow
            v-for="(ex, ei) in section.exercises"
            :key="ei"
            :exercise="ex"
            @toggle="handleToggle(si, ei)"
            @too-heavy="handleTooHeavy(si, ei)"
            @show-detail="openDrawer(si, ei)"
          />
        </div>
      </div>
    </div>

    <!-- 动作详情 Drawer -->
    <ExerciseDrawer
      :visible="drawerVisible"
      :exercise="drawerExercise"
      @close="drawerVisible = false"
      @toggle="handleDrawerToggle"
      @too-heavy="handleDrawerTooHeavy"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Modal } from 'ant-design-vue'
import { useWorkoutStore } from '@/stores/workout'
import ExerciseRow from './ExerciseRow.vue'
import ExerciseDrawer from './ExerciseDrawer.vue'
import type { ExerciseState } from '@/types'
import dayjs from 'dayjs'

const props = defineProps<{ dateStr: string | null }>()
const workoutStore = useWorkoutStore()
const todayStr = dayjs().format('YYYY-MM-DD')

// Drawer state
const drawerVisible = ref(false)
const drawerExercise = ref<ExerciseState | null>(null)
const drawerSectionIdx = ref(-1)
const drawerExerciseIdx = ref(-1)

const loading = ref(false)

const plan = computed(() => {
  if (!props.dateStr) return undefined
  const p = workoutStore.getDayPlan(props.dateStr)
  if (p) {
    workoutStore.restoreLocalState(props.dateStr)
  }
  return p
})

const isFuture = computed(() => {
  if (!props.dateStr) return false
  return props.dateStr > todayStr
})

const dateTitle = computed(() => {
  if (!props.dateStr) return ''
  const d = dayjs(props.dateStr)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.format('M月D日')} ${weekdays[d.day()]}`
})

const totalCount = computed(() => {
  if (!plan.value) return 0
  return plan.value.sections.reduce((s, sec) => s + sec.exercises.length, 0)
})

const doneCount = computed(() => {
  if (!plan.value) return 0
  return plan.value.sections.reduce((s, sec) => s + sec.exercises.filter(e => e.completed).length, 0)
})

const progressPercent = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((doneCount.value / totalCount.value) * 100)
})

// 日期变化时关掉 drawer
watch(() => props.dateStr, () => {
  drawerVisible.value = false
})

function handleToggle(sectionIdx: number, exerciseIdx: number) {
  if (!props.dateStr) return
  workoutStore.toggleExercise(props.dateStr, sectionIdx, exerciseIdx)
}

function handleTooHeavy(sectionIdx: number, exerciseIdx: number) {
  if (!props.dateStr) return
  Modal.confirm({
    title: '记录反馈',
    content: '下次训练时减轻这个动作的重量？',
    okText: '好的，下次减轻',
    cancelText: '取消',
    onOk: () => {
      workoutStore.markTooHeavy(props.dateStr!, sectionIdx, exerciseIdx)
    },
  })
}

function openDrawer(sectionIdx: number, exerciseIdx: number) {
  if (!plan.value) return
  const ex = plan.value.sections[sectionIdx]?.exercises[exerciseIdx]
  if (ex) {
    drawerExercise.value = ex
    drawerSectionIdx.value = sectionIdx
    drawerExerciseIdx.value = exerciseIdx
    drawerVisible.value = true
  }
}

function handleDrawerToggle() {
  if (!props.dateStr) return
  workoutStore.toggleExercise(props.dateStr, drawerSectionIdx.value, drawerExerciseIdx.value)
  // 更新当前 exercise 引用
  const ex = plan.value?.sections[drawerSectionIdx.value]?.exercises[drawerExerciseIdx.value]
  if (ex) drawerExercise.value = { ...ex }
}

function handleDrawerTooHeavy() {
  if (!props.dateStr) return
  workoutStore.markTooHeavy(props.dateStr, drawerSectionIdx.value, drawerExerciseIdx.value)
  const ex = plan.value?.sections[drawerSectionIdx.value]?.exercises[drawerExerciseIdx.value]
  if (ex) drawerExercise.value = { ...ex }
}

// 有 dateStr 但没有 plan 时尝试加载
watch(() => props.dateStr, async (newDate) => {
  if (!newDate) return
  const p = workoutStore.getDayPlan(newDate)
  if (!p && !isFuture.value) {
    const planId = localStorage.getItem('fitness_current_plan_id')
    if (planId) {
      loading.value = true
      try {
        await workoutStore.fetchPlan(Number(planId))
      } catch { /* ignore */ } finally {
        loading.value = false
      }
    }
  }
}, { immediate: true })
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

.empty-state, .loading-state {
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
.loading-state p { margin-top: 12px; color: #999; }

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
  margin-bottom: 12px;
}
.date-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0; }
.focus-tag {
  padding: 3px 12px; border-radius: 20px;
  background: #fff7ed; color: #f97316;
  font-size: 12px; font-weight: 600;
}

.progress-section { margin-bottom: 18px; }
.complete-text {
  text-align: center; font-size: 16px; font-weight: 700;
  color: #22c55e; margin-top: 8px;
  animation: bounce 0.5s ease-out;
}
@keyframes bounce {
  0% { transform: scale(0.8); opacity: 0; }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); opacity: 1; }
}

.section-block { margin-bottom: 16px; }
.section-title {
  font-size: 15px; font-weight: 700; color: #444;
  margin: 0 0 6px 12px;
}
.exercise-list { display: flex; flex-direction: column; gap: 5px; }
</style>
