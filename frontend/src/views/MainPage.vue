<template>
  <div class="main-content">
    <!-- 左侧栏 -->
    <aside class="left-column">
      <div class="calendar-section">
        <div class="calendar-actions">
          <!-- 空闲态: 生成按钮 -->
          <button
            v-if="!cycleStore.isGenerating"
            class="gen-next-btn"
            @click="handleGenerateNext"
          >
            ➡️ 生成下周计划
          </button>

          <!-- 生成态: 实时进度卡片 -->
          <div v-else class="gen-progress-card">
            <div class="gen-header-row">
              <span class="gen-header-icon">📋</span>
              <span class="gen-header-title">正在生成下周计划</span>
            </div>

            <!-- 进度条 -->
            <div class="gen-progress-bar">
              <div class="gen-progress-bg">
                <div
                  class="gen-progress-fill"
                  :style="{ width: cycleStore.generationProgress + '%' }"
                  :class="{ complete: cycleStore.generationProgress >= 100 }"
                />
              </div>
              <span class="gen-progress-pct">{{ cycleStore.generationProgress }}%</span>
            </div>

            <!-- 当前状态 -->
            <div class="gen-current-status">{{ cycleStore.generationStatus }}</div>

            <!-- 滚动日志 -->
            <div ref="logContainerRef" class="gen-log-container">
              <div
                v-for="(entry, idx) in cycleStore.generationLog"
                :key="idx"
                class="gen-log-entry"
                :class="'gen-log-' + entry.phase"
              >
                <span class="gen-log-time">{{ entry.time }}</span>
                <span class="gen-log-text">{{ entry.text }}</span>
              </div>
            </div>
          </div>
        </div>
        <CalendarPanel @select="onDateSelect" />
      </div>
      <div class="muscle-section">
        <MuscleDiagram
          :gender="userGender"
          :primary-muscles="workoutStore.activePrimaryMuscles"
          :secondary-muscles="workoutStore.activeSecondaryMuscles"
        />
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <main class="right-column">
      <DailyPlanPanel :date-str="selectedDate" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useCycleStore } from '@/stores/cycle'
import { useUserStore } from '@/stores/user'
import { useWorkoutStore } from '@/stores/workout'
import CalendarPanel from '@/components/CalendarPanel.vue'
import DailyPlanPanel from '@/components/DailyPlanPanel.vue'
import MuscleDiagram from '@/components/MuscleDiagram.vue'
import dayjs from 'dayjs'

const router = useRouter()
const cycleStore = useCycleStore()
const userStore = useUserStore()
const workoutStore = useWorkoutStore()

const selectedDate = ref<string | null>(null)
const todayStr = dayjs().format('YYYY-MM-DD')
const logContainerRef = ref<HTMLElement | null>(null)

/** 用户性别（类型收窄，兼容 MuscleDiagram props） */
const userGender = computed<'male' | 'female' | undefined>(() =>
  userStore.profile?.gender === 'male' || userStore.profile?.gender === 'female'
    ? userStore.profile.gender
    : undefined,
)

// 日志自动滚动到底部
watch(() => cycleStore.generationLog.length, async () => {
  await nextTick()
  if (logContainerRef.value) {
    logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  }
})

onMounted(async () => {
  try {
    await cycleStore.fetchCurrentWeek()
    cycleStore.fetchMacrocycles()
    if (cycleStore.currentWeek && cycleStore.currentWeek.days.length > 0) {
      const todayDay = cycleStore.currentWeek.days.find(d => d.date === todayStr)
      if (todayDay) selectedDate.value = todayStr
      else selectedDate.value = cycleStore.currentWeek.days[0].date || todayStr
    }
  } catch {
    userStore.resetOnboarding()
    router.replace('/')
  }
  userStore.fetchProfile().catch(() => {})
  userStore.fetchCurrentState().catch(() => {})
})

function onDateSelect(date: string) { selectedDate.value = date }

/** 生成下周计划（测试用，模拟多周训练） */
async function handleGenerateNext() {
  try {
    await cycleStore.generateNextWeekPolling()
    // 刷新日历数据
    const { start, end } = cycleStore.calendarRange
    if (start && end) {
      cycleStore.fetchCalendarData(start, end)
    } else {
      cycleStore.fetchMacrocycles()
    }
    // 选中新一周的第一天
    if (cycleStore.currentWeek?.days?.length) {
      selectedDate.value = cycleStore.currentWeek.days[0].date
    }
  } catch (e: any) {
    alert('生成失败: ' + (e.message || '未知错误'))
  }
}
</script>

<style scoped>
.main-content {
  display: grid;
  grid-template-columns: clamp(280px, 26%, 380px) 1fr;
  gap: clamp(16px, 2vw, 32px);
  height: 100%;
  min-height: 0;
  padding-bottom: 16px;
}
.left-column { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.calendar-section { flex-shrink: 0; }

.calendar-actions {
  margin-bottom: 8px;
}

/* ── 生成按钮（空闲态）── */
.gen-next-btn {
  width: 100%;
  padding: 10px 16px;
  border-radius: 12px;
  border: 2px dashed var(--brand-orange);
  background: var(--brand-orange-subtle);
  color: var(--brand-orange);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.gen-next-btn:hover {
  background: var(--brand-orange-subtle);
  border-color: var(--brand-orange-deep);
  color: var(--brand-orange-deep);
}

/* ── 进度卡片（生成态）── */
.gen-progress-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px;
  box-shadow: var(--shadow-card);
}

.gen-header-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.gen-header-icon { font-size: 18px; }
.gen-header-title { font-size: 14px; font-weight: 700; color: var(--text-primary); }

/* 进度条 */
.gen-progress-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.gen-progress-bg {
  flex: 1;
  height: 10px;
  background: var(--bg-subtle);
  border-radius: 5px;
  overflow: hidden;
}
.gen-progress-fill {
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, var(--brand-orange), var(--brand-orange-light));
  transition: width 0.4s ease;
}
.gen-progress-fill.complete { background: var(--color-success); }
.gen-progress-pct {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
  min-width: 36px;
  text-align: right;
}

/* 当前状态文字 */
.gen-current-status {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-height: 18px;
  line-height: 1.4;
}

/* 日志容器 */
.gen-log-container {
  max-height: 260px;
  overflow-y: auto;
  background: var(--bg-hover);
  border-radius: 8px;
  padding: 6px 8px;
  font-size: 11px;
  line-height: 1.5;
  font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
}
.gen-log-container::-webkit-scrollbar { width: 4px; }
.gen-log-container::-webkit-scrollbar-thumb { background: var(--border-color); border-radius: 2px; }

.gen-log-entry {
  display: flex;
  gap: 6px;
  padding: 1px 0;
  color: var(--text-secondary);
}
.gen-log-time {
  color: var(--text-muted);
  flex-shrink: 0;
}
.gen-log-text {
  flex: 1;
  word-break: break-all;
}

/* 不同阶段颜色（亮色） */
.gen-log-init .gen-log-text { color: #666; }
.gen-log-analysis .gen-log-text { color: #7c3aed; }
.gen-log-read .gen-log-text,
.gen-log-decision .gen-log-text { color: #2563eb; }
.gen-log-mesocycle .gen-log-text,
.gen-log-pool .gen-log-text { color: #f97316; }
.gen-log-create .gen-log-text,
.gen-log-config .gen-log-text { color: #6366f1; }
.gen-log-llm .gen-log-text { color: #8b5cf6; }
.gen-log-candidates .gen-log-text { color: #0891b2; }
.gen-log-select .gen-log-text { color: #d97706; }
.gen-log-assemble .gen-log-text { color: #059669; }
.gen-log-overload .gen-log-text { color: #65a30d; }
.gen-log-save .gen-log-text { color: #2563eb; }
.gen-log-finalize .gen-log-text { color: #7c3aed; }
.gen-log-done .gen-log-text { color: #16a34a; font-weight: 600; }
.gen-log-error .gen-log-text { color: #dc2626; font-weight: 600; }
.gen-log-day_done .gen-log-text { color: #16a34a; }

/* 不同阶段颜色（暗色 — 提高亮度） */
:root.dark .gen-log-init .gen-log-text { color: #999; }
:root.dark .gen-log-analysis .gen-log-text { color: #a78bfa; }
:root.dark .gen-log-read .gen-log-text,
:root.dark .gen-log-decision .gen-log-text { color: #60a5fa; }
:root.dark .gen-log-mesocycle .gen-log-text,
:root.dark .gen-log-pool .gen-log-text { color: #fb923c; }
:root.dark .gen-log-create .gen-log-text,
:root.dark .gen-log-config .gen-log-text { color: #818cf8; }
:root.dark .gen-log-llm .gen-log-text { color: #a78bfa; }
:root.dark .gen-log-candidates .gen-log-text { color: #22d3ee; }
:root.dark .gen-log-select .gen-log-text { color: #fbbf24; }
:root.dark .gen-log-assemble .gen-log-text { color: #34d399; }
:root.dark .gen-log-overload .gen-log-text { color: #a3e635; }
:root.dark .gen-log-save .gen-log-text { color: #60a5fa; }
:root.dark .gen-log-finalize .gen-log-text { color: #a78bfa; }
:root.dark .gen-log-done .gen-log-text { color: #4ade80; font-weight: 600; }
:root.dark .gen-log-error .gen-log-text { color: #f87171; font-weight: 600; }
:root.dark .gen-log-day_done .gen-log-text { color: #4ade80; }

.muscle-section { flex: 1; display: flex; flex-direction: column; min-height: 100px; }
.right-column { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
</style>
