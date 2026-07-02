<template>
  <div class="main-content">
    <!-- 左侧栏 -->
    <aside class="left-column">
      <div class="progress-section">
        <CycleInfo
          :phase-label="cycleStore.mesocyclePhaseLabel"
          :week-number="cycleStore.currentWeekNumber"
          :total-weeks="cycleStore.mesocycleTotalWeeks"
          :completion-rate="cycleStore.weekCompletionRate"
          :is-week-complete="cycleStore.isWeekComplete"
          :completed-days="completedDays"
          :total-days="totalDays"
          :next-phase="cycleStore.nextPhaseLabel ?? undefined"
          :is-deload="cycleStore.currentWeek?.mesocycle_phase === 'deload'"
          @generate="handleGenerateNext"
        />
      </div>
      <div class="calendar-section">
        <CalendarPanel @select="onDateSelect" />
      </div>
      <div class="muscle-section">
        <MuscleDiagram
          :gender="userStore.profile?.gender"
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCycleStore } from '@/stores/cycle'
import { useUserStore } from '@/stores/user'
import { useWorkoutStore } from '@/stores/workout'
import CycleInfo from '@/components/CycleInfo.vue'
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

const completedDays = computed(() => cycleStore.currentWeek?.days.filter(d => d.is_completed).length ?? 0)
const totalDays = computed(() => cycleStore.currentWeek?.days.length ?? 0)

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
function handleGenerateNext() { router.push('/?force=true') }
</script>

<style scoped>
.main-content { display: flex; gap: 16px; height: 100%; min-height: 0; padding-bottom: 16px; }
.left-column { width: 380px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.progress-section { flex-shrink: 0; }
.calendar-section { flex-shrink: 0; }
.muscle-section { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.right-column { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }
</style>
