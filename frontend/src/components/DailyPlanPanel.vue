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
        :class="{ 'checked-in': isDayCheckedIn }"
        :disabled="isBtnDisabled"
        @click="handleCheckin"
      >
        <template v-if="isDayCheckedIn">✅ 已打卡</template>
        <template v-else-if="checkinLoading">⏳ 提交中...</template>
        <template v-else>📝 提交打卡</template>
      </button>

      <p v-if="noFeedback && !checkinLoading && !isDayCheckedIn" class="checkin-hint">
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

    <!-- 烟花庆祝 -->
    <Teleport to="body">
      <div v-if="showFireworks" class="fireworks-overlay" @click="showFireworks = false">
        <div class="fireworks-inner">
          <div class="fireworks-congrats">
            <span class="fireworks-big-emoji">🎉</span>
            <h2>完成的很好！</h2>
            <p>继续保持，你是最棒的！</p>
          </div>
          <div
            v-for="i in 30"
            :key="i"
            class="fireworks-particle"
            :style="getParticleStyle(i)"
          />
        </div>
      </div>
    </Teleport>
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
const showFireworks = ref(false)

// ═══ 本地打卡状态（乐观锁 + API 双重确认）═══
// dateStr 变化时自动重置
const localCheckedIn = ref(false)
const isDayCheckedIn = computed(() => {
  // ① 本地乐观锁：点击打卡成功后立即生效，不等 API
  if (localCheckedIn.value) return true
  // ② API 确认：已打卡的日从后端取到 day_status='completed'
  return dayDetail.value?.day_status === 'completed'
})
const isBtnDisabled = computed(() => checkinLoading.value || noFeedback.value || isDayCheckedIn.value)

watch(() => props.dateStr, () => {
  localCheckedIn.value = false
})

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
  // 多重防护：任何已打卡状态都不执行
  if (isDayCheckedIn.value) return
  if (localCheckedIn.value) return

  try {
    error.value = null
    await workoutStore.submitCheckin()
    // ★ 本地乐观锁：立即锁定，不等 API 刷新
    localCheckedIn.value = true
    // 打卡成功：烟花 + 音效
    playCheckinSound()
    showFireworks.value = true
    setTimeout(() => { showFireworks.value = false }, 3000)
  } catch (e: any) {
    error.value = e.message || '打卡失败'
  }
}

/** Web Audio API 合成一段上行琶音（C5→E5→G5）作为完成音效 */
function playCheckinSound() {
  try {
    const ctx = new AudioContext()
    const notes = [523.25, 659.25, 783.99] // C5 E5 G5 — C 大三和弦
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = freq
      osc.type = 'sine'
      gain.gain.setValueAtTime(0.25, ctx.currentTime + i * 0.12)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.12 + 0.6)
      osc.start(ctx.currentTime + i * 0.12)
      osc.stop(ctx.currentTime + i * 0.12 + 0.6)
    })
  } catch { /* 浏览器可能阻止音频，静默忽略 */ }
}

/** 生成烟花粒子的随机样式 */
function getParticleStyle(i: number) {
  const colors = ['#ff6b6b','#ffd93d','#6bcb77','#4d96ff','#ff6bff','#ff9f43']
  const angle = (i / 30) * 360
  const dist = 120 + Math.random() * 180
  const rad = (angle * Math.PI) / 180
  return {
    '--tx': `${Math.cos(rad) * dist}px`,
    '--ty': `${Math.sin(rad) * dist}px`,
    background: colors[i % colors.length],
    width: `${8 + Math.random() * 12}px`,
    height: `${8 + Math.random() * 12}px`,
    left: '50%',
    top: '50%',
    animationDelay: `${Math.random() * 0.3}s`,
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
  margin-bottom: 24px;
}
.checkin-btn:hover:not(:disabled):not(.checked-in) { box-shadow: 0 4px 14px rgba(217,119,6,0.35); transform: translateY(-1px); }
.checkin-btn:disabled { background: var(--bg-subtle); color: var(--text-muted); cursor: not-allowed; }
.checkin-btn.checked-in {
  background: linear-gradient(135deg, var(--color-success-deep, #52c41a), var(--color-success, #73d13d));
  cursor: default;
  opacity: 1;
  box-shadow: 0 2px 12px rgba(82, 196, 26, 0.3);
}
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

/* ═══ 烟花庆祝 ═══ */
.fireworks-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.45);
  animation: fw-fadeIn 0.3s ease;
  cursor: pointer;
}
.fireworks-inner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}
.fireworks-congrats {
  text-align: center;
  z-index: 1;
  animation: fw-popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.fireworks-big-emoji { font-size: 80px; display: block; }
.fireworks-congrats h2 {
  font-size: 28px;
  color: #fff;
  margin: 16px 0 8px;
  text-shadow: 0 2px 12px rgba(0,0,0,0.3);
}
.fireworks-congrats p {
  font-size: 16px;
  color: rgba(255,255,255,0.85);
  margin: 0;
}
.fireworks-particle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  animation: fw-burst 1.5s ease-out forwards;
}
@keyframes fw-fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes fw-popIn {
  0% { transform: scale(0); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
@keyframes fw-burst {
  0% { transform: translate(0, 0) scale(1); opacity: 1; }
  100% { transform: translate(var(--tx), var(--ty)) scale(0); opacity: 0; }
}
</style>
