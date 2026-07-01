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
          :data="{ days: formData.days, locations: formData.locations, city: formData.city, preferredDays: formData.preferredDays }"
          @prev="currentIndex--"
          @next="onGenerate"
        />
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import StepCardPersonal from '@/components/StepCardPersonal.vue'
import StepCardGoal from '@/components/StepCardGoal.vue'
import StepCardSchedule from '@/components/StepCardSchedule.vue'

const router = useRouter()
const userStore = useUserStore()

const currentIndex = ref(0)

const formData = reactive({
  height: undefined as number | undefined,
  weight: undefined as number | undefined,
  age: undefined as number | undefined,
  gender: undefined as string | undefined,
  experience: '新手',
  goal: '',
  days: 3,
  locations: [] as string[],
  city: '',
  preferredDays: '1,3,5',  // 新增
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
  formData.locations = data.locations
  formData.city = data.city || ''
  formData.preferredDays = data.preferredDays || '1,3,5'

  // 先保存用户资料
  await userStore.saveProfile({
    height: formData.height, weight: formData.weight, age: formData.age,
    gender: formData.gender, goal: formData.goal, experience: formData.experience,
    city: formData.city || '',
    workout_location: formData.locations[0] || '居家',
    days_per_week: formData.days || 3,
  })

  // ⚡markOnboardingDone() 移到 GeneratingPlan.vue——生成成功后才标记
  // 跳转到生成直播间（含个人信息）
  router.push({
    path: '/generating',
    query: {
      goal: formData.goal,
      experience: formData.experience || '新手',
      location: formData.locations[0] || '健身房',
      days: String(formData.days || 3),
      city: formData.city || '',
      preferredDays: formData.preferredDays,
      height: formData.height ? String(formData.height) : '',
      weight: formData.weight ? String(formData.weight) : '',
      age: formData.age ? String(formData.age) : '',
      gender: formData.gender || '',
    },
  })
}

onMounted(() => {
  // 已完成 onboarding 的用户直接跳转主页
  if (!userStore.isFirstVisit) {
    router.replace('/home')
  }
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
