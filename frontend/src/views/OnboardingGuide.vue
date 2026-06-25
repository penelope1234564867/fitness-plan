<template>
  <div class="onboarding-container">
    <!-- Logo -->
    <div class="logo-area">
      <span class="logo-icon">💪</span>
      <h1 class="logo-title">AI 智能健身助手</h1>
    </div>

    <!-- 卡片 -->
    <div class="card-wrapper">
      <transition name="slide" mode="out-in">
        <StepCardPersonal
          v-if="currentIndex === 0"
          key="step1"
          :data="formData"
          @next="onStep1Next"
        />
        <StepCardGoal
          v-else-if="currentIndex === 1"
          key="step2"
          :data="formData.goal"
          @prev="currentIndex--"
          @next="onStep2Next"
        />
        <StepCardSchedule
          v-else-if="currentIndex === 2"
          key="step3"
          :data="{ days: formData.days, location: formData.location }"
          @prev="currentIndex--"
          @next="onGenerate"
        />
        <GeneratingProgress
          v-else-if="currentIndex === 3"
          key="progress"
          :progress="generatingProgress"
          :status="generatingStatus"
        />
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { useWorkoutStore } from '@/stores/workout'
import StepCardPersonal from '@/components/StepCardPersonal.vue'
import StepCardGoal from '@/components/StepCardGoal.vue'
import StepCardSchedule from '@/components/StepCardSchedule.vue'
import GeneratingProgress from '@/components/GeneratingProgress.vue'

const router = useRouter()
const userStore = useUserStore()
const workoutStore = useWorkoutStore()

const currentIndex = ref(0)
const generatingProgress = ref(0)
const generatingStatus = ref('')
let progressTimer: number | null = null

const formData = reactive({
  height: undefined as number | undefined,
  weight: undefined as number | undefined,
  age: undefined as number | undefined,
  gender: undefined as string | undefined,
  goal: '',
  days: 3,
  location: '',
})

function onStep1Next(data: any) {
  Object.assign(formData, data)
  currentIndex.value = 1
}

function onStep2Next(goal: string) {
  formData.goal = goal
  currentIndex.value = 2
}

async function onGenerate(data: any) {
  formData.days = data.days
  formData.location = data.location
  currentIndex.value = 3

  progressTimer = window.setInterval(() => {
    if (generatingProgress.value < 90) {
      generatingProgress.value += 8
      if (generatingProgress.value <= 30) generatingStatus.value = '📋 分析你的健身目标...'
      else if (generatingProgress.value <= 50) generatingStatus.value = '🏋️ 搜索适合的训练动作...'
      else if (generatingProgress.value <= 70) generatingStatus.value = '📅 编排训练日程...'
      else generatingStatus.value = '📝 生成完整计划...'
    }
  }, 400)

  try {
    await workoutStore.createPlan({
      goal: formData.goal,
      experience_level: formData.gender === 'male' ? '中级' : '新手',
      workout_location: formData.location || '健身房',
      days_per_week: formData.days || 3,
      duration_weeks: 4,
      diet_preference: '普通',
    })

    await userStore.saveProfile({
      height: formData.height, weight: formData.weight, age: formData.age,
      gender: formData.gender, goal: formData.goal, experience: '新手',
    }).catch(() => {})

    userStore.markOnboardingDone()
    clearInterval(progressTimer!)
    generatingProgress.value = 100
    generatingStatus.value = '✅ 计划生成成功！'
    setTimeout(() => router.push('/calendar'), 800)
  } catch (e: any) {
    clearInterval(progressTimer!)
    message.error(e.message || '生成失败，请重试')
    currentIndex.value = 2
  }
}

onUnmounted(() => {
  if (progressTimer) clearInterval(progressTimer)
})
</script>

<style scoped>
.onboarding-container {
  min-height: calc(100vh - 64px);
  background: #f5f7fa;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.logo-area {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 6px;
}

.logo-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
}

.card-wrapper {
  width: 100%;
  max-width: 480px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  padding: 36px 32px;
}

/* 过渡动画 */
.slide-enter-active { animation: slideIn 0.3s ease-out; }
.slide-leave-active { animation: slideOut 0.2s ease-in; }
@keyframes slideIn {
  from { opacity: 0; transform: translateX(30px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes slideOut {
  from { opacity: 1; transform: translateX(0); }
  to { opacity: 0; transform: translateX(-30px); }
}
</style>
