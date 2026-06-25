<template>
  <div class="main-content">
    <!-- 左侧栏 -->
    <aside class="left-column">
      <div class="calendar-section">
        <CalendarPanel @select="onDateSelect" />
      </div>
      <div class="chat-section">
        <AIChatPanel />
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <main class="right-column">
      <DailyPlanPanel :date-str="selectedDate" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWorkoutStore } from '@/stores/workout'
import { useUserStore } from '@/stores/user'
import CalendarPanel from '@/components/CalendarPanel.vue'
import AIChatPanel from '@/components/AIChatPanel.vue'
import DailyPlanPanel from '@/components/DailyPlanPanel.vue'
import dayjs from 'dayjs'

const workoutStore = useWorkoutStore()
const userStore = useUserStore()

const selectedDate = ref<string | null>(null)
const todayStr = dayjs().format('YYYY-MM-DD')

onMounted(async () => {
  const planId = localStorage.getItem('fitness_current_plan_id')
  if (planId) {
    try {
      await workoutStore.fetchPlan(Number(planId))
    } catch {
      workoutStore.loadDemoData()
    }
  } else {
    workoutStore.loadDemoData()
  }

  if (workoutStore.getDayPlan(todayStr)) {
    selectedDate.value = todayStr
  } else {
    const firstPlan = Array.from(workoutStore.dayPlans.values())[0]
    if (firstPlan) selectedDate.value = firstPlan.date
  }

  userStore.fetchProfile().catch(() => {})
})

function onDateSelect(date: string) {
  selectedDate.value = date
}
</script>

<style scoped>
.main-content {
  display: flex;
  gap: 16px;
  min-height: calc(100vh - 80px);
}

.left-column {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.calendar-section { flex-shrink: 0; }
.chat-section { flex: 1; min-height: 0; }

.right-column {
  flex: 1;
  min-width: 0;
}
</style>
