<template>
  <div class="checklist-container">
    <a-button class="back-btn" type="text" @click="goBack">
      ← 返回日历
    </a-button>

    <!-- 加载中 -->
    <div v-if="!dayPlan" class="loading-state">
      <a-spin size="large" />
      <p>加载中...</p>
    </div>

    <!-- 休息日 -->
    <div v-else-if="dayPlan.isRestDay" class="rest-day">
      <span class="rest-icon">🎉</span>
      <h2>今天是休息日</h2>
      <p>好好恢复，下次训练效果更好</p>
    </div>

    <!-- 未来日期 -->
    <div v-else-if="isFuture" class="future-day">
      <span class="future-icon">📅</span>
      <h2>这是未来的训练计划</h2>
      <p>到了那天再来完成吧</p>
    </div>

    <!-- 清单内容 -->
    <div v-else class="checklist-content">
      <!-- 日期头部 -->
      <div class="checklist-header">
        <h2 class="date-title">{{ dateTitle }}</h2>
        <span class="focus-tag">{{ dayPlan.focusArea }}</span>
      </div>

      <!-- 进度条 -->
      <div class="progress-section">
        <a-progress
          :percent="progressPercent"
          :stroke-color="progressPercent >= 100 ? '#22c55e' : '#f97316'"
          :stroke-width="10"
          :format="() => `${doneCount}/${totalCount}`"
        />
        <p v-if="progressPercent >= 100" class="complete-text">🎉 今日训练全部完成！</p>
      </div>

      <!-- 训练区块 -->
      <div v-for="(section, si) in dayPlan.sections" :key="si" class="section-block">
        <h3 class="section-title">{{ section.label }}</h3>
        <div class="exercise-list">
          <ExerciseRow
            v-for="(ex, ei) in section.exercises"
            :key="ei"
            :exercise="ex"
            @toggle="toggleExercise(si, ei)"
            @too-heavy="onTooHeavy(si, ei)"
            @show-detail="openDrawer(si, ei)"
          />
        </div>
      </div>
    </div>

    <!-- 错误 -->
    <a-alert v-if="error" type="error" :message="error" closable style="margin-top: 16px;" @close="error = null" />

    <!-- 动作详情 Drawer -->
    <a-drawer
      :open="drawerVisible"
      :title="drawerExercise?.name || '动作详情'"
      placement="right"
      :width="380"
      @close="drawerVisible = false"
    >
      <div v-if="drawerExercise" class="drawer-content">
        <div class="drawer-image">
          <img
            v-if="drawerExercise.imageUrl"
            :src="drawerExercise.imageUrl"
            :alt="drawerExercise.name"
          />
          <div v-else class="drawer-image-placeholder">
            <span>{{ drawerExercise.name.charAt(0) }}</span>
          </div>
        </div>

        <div class="drawer-info">
          <div class="drawer-info-row">
            <span class="drawer-info-label">🎯 目标肌群</span>
            <span class="drawer-info-value">{{ drawerExercise.targetMuscle || '全身' }}</span>
          </div>
          <div class="drawer-info-row">
            <span class="drawer-info-label">⚙️ 训练量</span>
            <span class="drawer-info-value">
              <template v-if="drawerExercise.duration">{{ drawerExercise.duration }}秒</template>
              <template v-else>{{ drawerExercise.sets }}组 × {{ drawerExercise.reps }}次</template>
              <template v-if="drawerExercise.weight"> · {{ drawerExercise.weight }}</template>
            </span>
          </div>
          <div v-if="drawerExercise.description" class="drawer-desc-section">
            <span class="drawer-info-label">📝 动作描述</span>
            <p class="drawer-desc">{{ drawerExercise.description }}</p>
          </div>
        </div>
      </div>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Modal } from 'ant-design-vue'
import { useWorkoutStore } from '@/stores/workout'
import ExerciseRow from '@/components/ExerciseRow.vue'
import type { ExerciseState } from '@/types'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const workoutStore = useWorkoutStore()

const error = ref<string | null>(null)
const dateStr = computed(() => (route.query.date as string) || dayjs().format('YYYY-MM-DD'))
const isFuture = computed(() => dateStr.value > dayjs().format('YYYY-MM-DD'))

// 动作详情 Drawer
const drawerVisible = ref(false)
const drawerExercise = ref<ExerciseState | null>(null)

const dayPlan = computed(() => {
  const plan = workoutStore.getDayPlan(dateStr.value)
  if (plan) {
    workoutStore.restoreLocalState(dateStr.value)
  }
  return plan
})

const dateTitle = computed(() => {
  const d = dayjs(dateStr.value)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.format('M月D日')} ${weekdays[d.day()]}`
})

const totalCount = computed(() => {
  if (!dayPlan.value) return 0
  return dayPlan.value.sections.reduce((s, sec) => s + sec.exercises.length, 0)
})

const doneCount = computed(() => {
  if (!dayPlan.value) return 0
  return dayPlan.value.sections.reduce((s, sec) => s + sec.exercises.filter(e => e.completed).length, 0)
})

const progressPercent = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((doneCount.value / totalCount.value) * 100)
})

onMounted(() => {
  if (!dayPlan.value && !isFuture.value) {
    // 尝试加载计划
    const planId = localStorage.getItem('fitness_current_plan_id')
    if (planId) {
      workoutStore.fetchPlan(Number(planId))
    }
  }
})

function toggleExercise(sectionIdx: number, exerciseIdx: number) {
  workoutStore.toggleExercise(dateStr.value, sectionIdx, exerciseIdx)
}

function onTooHeavy(sectionIdx: number, exerciseIdx: number) {
  Modal.confirm({
    title: '记录反馈',
    content: '下次训练时减轻这个动作的重量？',
    okText: '好的，下次减轻',
    cancelText: '取消',
    onOk: () => {
      workoutStore.markTooHeavy(dateStr.value, sectionIdx, exerciseIdx)
    },
  })
}

function openDrawer(sectionIdx: number, exerciseIdx: number) {
  const plan = dayPlan.value
  if (!plan) return
  const ex = plan.sections[sectionIdx]?.exercises[exerciseIdx]
  if (ex) {
    drawerExercise.value = ex
    drawerVisible.value = true
  }
}

function goBack() {
  router.push('/calendar')
}
</script>

<style scoped>
.checklist-container { max-width: 640px; margin: 0 auto; }
.back-btn { margin-bottom: 8px; color: #666; font-size: 14px; padding-left: 0; }
.back-btn:hover { color: #f97316; }

.loading-state { text-align: center; padding: 80px 20px; }
.loading-state p { margin-top: 12px; color: #999; }

.rest-day, .future-day {
  text-align: center; padding: 80px 20px;
  background: #fff; border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.rest-icon, .future-icon { font-size: 64px; margin-bottom: 16px; display: block; }
.rest-day h2, .future-day h2 { font-size: 22px; color: #333; margin-bottom: 8px; }
.rest-day p, .future-day p { color: #999; }

.checklist-content { animation: fadeIn 0.3s ease-out; }

.checklist-header {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 16px;
}
.date-title { font-size: 22px; font-weight: 700; color: #1a1a1a; margin: 0; }
.focus-tag {
  padding: 4px 14px; border-radius: 20px;
  background: #fff7ed; color: #f97316;
  font-size: 13px; font-weight: 600;
}

.progress-section { margin-bottom: 24px; }
.complete-text {
  text-align: center; font-size: 18px; font-weight: 700;
  color: #22c55e; margin-top: 12px;
  animation: bounce 0.5s ease-out;
}
@keyframes bounce {
  0% { transform: scale(0.8); opacity: 0; }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); opacity: 1; }
}

.section-block { margin-bottom: 20px; }
.section-title {
  font-size: 16px; font-weight: 700; color: #444;
  margin: 0 0 8px 16px;
}
.exercise-list { display: flex; flex-direction: column; gap: 6px; }

@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* Drawer 样式 */
.drawer-content { }
.drawer-image { margin-bottom: 20px; border-radius: 12px; overflow: hidden; background: #f5f5f5; }
.drawer-image img { width: 100%; height: 220px; object-fit: cover; display: block; }
.drawer-image-placeholder {
  width: 100%; height: 220px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #f97316, #fb923c);
  font-size: 64px; font-weight: 700; color: rgba(255,255,255,0.3);
}
.drawer-info { display: flex; flex-direction: column; gap: 16px; }
.drawer-info-row { display: flex; flex-direction: column; gap: 4px; }
.drawer-info-label { font-size: 13px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
.drawer-info-value { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.drawer-desc-section { margin-top: 8px; }
.drawer-desc { font-size: 14px; line-height: 1.7; color: #555; margin: 8px 0 0 0; }
</style>
