<template>
  <div class="main-content">
    <!-- 左侧栏 -->
    <aside class="left-column">
      <div class="calendar-section">
        <CalendarPanel @select="onDateSelect" />
      </div>
      <div class="cycle-section">
        <CycleInfo
          :phase-label="cycleStore.mesocyclePhaseLabel"
          :week-number="cycleStore.currentWeekNumber"
          :total-weeks="cycleStore.mesocycleTotalWeeks"
          :completion-rate="cycleStore.weekCompletionRate"
          :is-week-complete="cycleStore.isWeekComplete"
          :is-deload="cycleStore.currentWeek?.mesocycle_phase === 'deload'"
          @generate="handleGenerateNext"
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
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCycleStore } from '@/stores/cycle'
import { useUserStore } from '@/stores/user'
import CalendarPanel from '@/components/CalendarPanel.vue'
import CycleInfo from '@/components/CycleInfo.vue'
import DailyPlanPanel from '@/components/DailyPlanPanel.vue'
import dayjs from 'dayjs'

const router = useRouter()
const cycleStore = useCycleStore()
const userStore = useUserStore()

const selectedDate = ref<string | null>(null)
const todayStr = dayjs().format('YYYY-MM-DD')

onMounted(async () => {
  // 尝试加载当前周
  try {
    await cycleStore.fetchCurrentWeek()
    cycleStore.fetchMacrocycles()

    // 默认选中当天（如果有训练）或第一个训练日
    if (cycleStore.currentWeek && cycleStore.currentWeek.days.length > 0) {
      const todayDay = cycleStore.currentWeek.days.find(d => d.date === todayStr)
      if (todayDay) {
        selectedDate.value = todayStr
      } else {
        // 选第一个训练日（使用 date 字段）
        selectedDate.value = cycleStore.currentWeek.days[0].date || todayStr
      }
    }
  } catch {
    // 没有计划 → 去个人信息页
    router.replace('/')
  }

  // 并行拉取用户资料
  userStore.fetchProfile().catch(() => {})
  userStore.fetchCurrentState().catch(() => {})
})

function onDateSelect(date: string) {
  selectedDate.value = date
}

async function handleGenerateNext() {
  // 重新生成 → 去个人信息页（已有数据会自动预填）
  router.push('/')
}
</script>

<style scoped>
.main-content {
  display: flex;
  gap: 16px;
  min-height: auto;
}

.left-column {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.calendar-section { flex-shrink: 0; }
.cycle-section { flex-shrink: 0; }

.right-column {
  flex: 1;
  min-width: 0;
}
</style>
