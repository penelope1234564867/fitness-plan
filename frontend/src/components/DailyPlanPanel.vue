<template>
  <div class="daily-plan-panel">
    <!-- 未选择日期 -->
    <div v-if="!dateStr" :key="'empty'" class="empty-state">
      <span class="empty-icon">📅</span>
      <p>点击日历中的日期查看训练计划</p>
    </div>

    <!-- 内容区域（切换日期时淡入动画） -->
    <template v-else>
      <Transition name="fade-slide" mode="out-in">
        <div :key="dateStr" class="panel-content">
          <!-- 没有计划 -->
          <div v-if="!dayPlan" class="empty-state">
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
      <!-- 日期头部 + 阶段标识 -->
      <div class="plan-header">
        <div class="plan-header-left">
          <h2 class="date-title">{{ dateTitle }}</h2>
          <span class="focus-tag">{{ dayPlan.focus }}</span>
        </div>
        <div class="plan-header-right">
          <span
            v-if="phaseInfo.label"
            class="phase-badge"
            :style="{ background: phaseInfo.color + '20', color: phaseInfo.color, borderColor: phaseInfo.color + '40' }"
          >
            {{ phaseInfo.emoji }} {{ phaseInfo.label }} · 第{{ phaseInfo.week }}周
          </span>
          <span v-if="phaseInfo.rpeTrend === 'rising'" class="rpe-trend-badge trend-up">
            📈 RPE 趋势：上升中
          </span>
          <span v-else-if="phaseInfo.rpeTrend === 'falling'" class="rpe-trend-badge trend-down">
            📉 RPE 趋势：下降中
          </span>
          <span v-else-if="phaseInfo.rpeTrend === 'stable'" class="rpe-trend-badge trend-stable">
            📊 RPE 趋势：稳定
          </span>
        </div>
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

      <!-- 变化摘要 -->
      <div v-if="workoutStore.changeSummary.total > 0" class="change-summary">
        📊 变化摘要：
        <span v-if="workoutStore.changeSummary.increased" class="cs-up">
          {{ workoutStore.changeSummary.increased }} 个动作加重
        </span>
        <span v-if="workoutStore.changeSummary.decreased" class="cs-down">
          {{ workoutStore.changeSummary.decreased }} 个动作减载
        </span>
        <span v-if="workoutStore.changeSummary.newExercise" class="cs-new">
          {{ workoutStore.changeSummary.newExercise }} 个新动作
        </span>
        <span v-if="workoutStore.changeSummary.same" class="cs-same">
          {{ workoutStore.changeSummary.same }} 个动作保持
        </span>
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
      </div>
      </Transition>
    </template>

    <!-- 错误提示 -->
    <div v-if="error" class="error-msg">{{ error }}</div>

    <!-- 动作详情抽屉（精细调整用） -->
    <ExerciseDrawer
      v-if="drawerExercise"
      :visible="drawerVisible"
      :exercise="drawerExercise"
      @close="drawerVisible = false"
      @toggle="workoutStore.toggleExercise(drawerExercise!.id)"
      @too-heavy="handleTooHeavy"
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
  return dayDetail.value?.is_rest_day === true
})
const isFuture = computed(() => {
  if (!props.dateStr) return false
  if (props.dateStr <= todayStr) return false
  // 有训练数据的未来日期正常展示，不显示"未来"占位
  const dd = dayDetail.value
  if (dd?.has_plan) return false
  return true
})

const dateTitle = computed(() => {
  if (!props.dateStr) return ''
  const d = dayjs(props.dateStr)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.format('M月D日')} ${weekdays[d.day()]}`
})

/** 阶段标识信息 */
const phaseInfo = computed(() => {
  const dd = dayDetail.value
  if (!dd) return { label: '', color: '', week: 0, emoji: '', rpeTrend: 'stable' }
  const phaseEmoji: Record<string, string> = {
    foundational: '🌱',
    hypertrophy: '🔥',
    strength: '💪',
    deload: '🧘',
  }
  return {
    label: dd.phase_label || '',
    color: dd.phase_color || '#999',
    week: dd.week_number || 0,
    emoji: phaseEmoji[dd.mesocycle_phase] || '🏋️',
    rpeTrend: dd.rpe_trend || 'stable',
  }
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
  // 从完整 slots 中找对应项（含嵌套 exercise 详情）
  const full = dayPlan.value?.slots.find(s => s.id === ex.id)
  drawerExercise.value = full || ex
  drawerVisible.value = true
}

function handleTooHeavy() {
  if (!drawerExercise.value) return
  workoutStore.setRPEQuick(drawerExercise.value.id, 'hard')
}
</script>

<style scoped>
.daily-plan-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border-radius: 16px;
  box-shadow: var(--shadow-card-lg);
  border: 1px solid var(--border-color);
  padding: 20px;
  overflow-y: auto;
}
.daily-plan-panel::-webkit-scrollbar { width: 4px; }
.daily-plan-panel::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 2px; }
.daily-plan-panel::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

/* Transition 包装容器——撑满剩余空间让子元素居中 */
.panel-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
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
.rest-day h2, .future-day h2 { font-size: 20px; color: var(--text-primary); margin: 0 0 8px 0; }
.rest-day p, .future-day p { color: var(--text-muted); margin: 0; }

.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.plan-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.plan-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.date-title { font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 0; }
.focus-tag {
  padding: 3px 12px; border-radius: 20px;
  background: var(--brand-orange-subtle); color: var(--brand-orange);
  font-size: 12px; font-weight: 600;
}
.phase-badge {
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.rpe-trend-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: var(--bg-subtle);
  font-weight: 500;
}
.trend-up { color: var(--color-success-deep); }
.trend-down { color: var(--brand-orange-deep); }
.trend-stable { color: var(--text-secondary); }

.change-summary {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-subtle);
  border-radius: 8px;
  margin: 8px 0 12px;
  font-size: 12px;
  color: var(--text-secondary);
  flex-wrap: wrap;
}
.change-summary span { font-weight: 600; }
.cs-up { color: var(--color-success-deep); }
.cs-down { color: var(--brand-orange-deep); }
.cs-new { color: var(--color-info-deep); }
.cs-same { color: var(--text-muted); }

.section-block { margin-bottom: 14px; }
.section-title {
  font-size: 14px; font-weight: 700; color: var(--text-secondary);
  margin: 0 0 6px 4px;
}
.exercise-list { display: flex; flex-direction: column; gap: 4px; }

.rpe-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--bg-subtle);
  border-radius: 8px;
  margin: 8px 0 12px;
  font-size: 11px;
  color: var(--text-muted);
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
  background: linear-gradient(135deg, var(--brand-orange), var(--brand-orange-light));
  color: #fff;
  transition: all 0.2s;
}
.checkin-btn:hover:not(:disabled) { box-shadow: 0 4px 14px rgba(217,119,6,0.35); transform: translateY(-1px); }
.checkin-btn:disabled { background: var(--bg-subtle); color: var(--text-muted); cursor: not-allowed; }
.checkin-hint { text-align: center; font-size: 12px; color: var(--text-muted); margin: 6px 0 0; }
.error-msg { color: var(--color-error); font-size: 13px; text-align: center; margin-top: 8px; }

/* ═══ 日期切换动画 ═══ */
.fade-slide-enter-active {
  animation: fade-slide-in 0.25s ease-out;
}
.fade-slide-leave-active {
  animation: fade-slide-out 0.15s ease-in;
}
@keyframes fade-slide-in {
  0% { opacity: 0; transform: translateX(12px); }
  100% { opacity: 1; transform: translateX(0); }
}
@keyframes fade-slide-out {
  0% { opacity: 1; transform: translateX(0); }
  100% { opacity: 0; transform: translateX(-8px); }
}
</style>
