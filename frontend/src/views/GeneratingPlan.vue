<template>
  <div class="generating-container">
    <!-- 加载个人信息中 -->
    <div v-if="loadingProfile" class="gen-loading">
      <div class="loading-spinner">⏳</div>
      <h2>读取个人信息...</h2>
    </div>

    <!-- 正常生成流程 -->
    <template v-else>
      <header class="gen-header">
        <div class="gen-header-left">
          <span class="gen-header-icon">📅</span>
          <h2>正在生成你的训练计划</h2>
        </div>
        <div class="gen-header-right">
          <span class="gen-timer">⏱ {{ elapsed }}s</span>
          <span class="gen-divider">|</span>
          <span class="gen-progress-text">{{ cycleStore.generationStatus }}</span>
        </div>
      </header>

      <div class="gen-progress-bar">
        <div class="progress-bg">
          <div
            class="progress-fill"
            :style="{ width: cycleStore.generationProgress + '%' }"
            :class="{ complete: cycleStore.generationProgress >= 100 }"
          />
        </div>
        <span class="progress-pct">{{ cycleStore.generationProgress }}%</span>
      </div>

      <div class="gen-status-text">
        {{ cycleStore.generationStatus }}
      </div>

      <div v-if="cycleStore.error" class="gen-error">
        <span>⚠️ {{ cycleStore.error }}</span>
        <button class="retry-btn" @click="loadProfileAndGenerate">重试</button>
      </div>

      <div v-if="cycleStore.generationProgress >= 100 && !cycleStore.error" class="gen-done">
        ✅ 计划生成成功！即将跳转...
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCycleStore } from '@/stores/cycle'
import { useUserStore } from '@/stores/user'
import { getProfile } from '@/services/api'

const router = useRouter()
const route = useRoute()
const cycleStore = useCycleStore()
const userStore = useUserStore()

const elapsed = ref(0)
const loadingProfile = ref(true)
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  timer = setInterval(() => { elapsed.value++ }, 1000)
  loadProfileAndGenerate()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  cycleStore.stopPolling()  // 离开页面时停止轮询
})

async function loadProfileAndGenerate() {
  try {
    // 1. 从后端读取个人信息（路由守卫：无数据则跳回 /）
    const profile = await getProfile()
    if (!profile || !profile.id || profile.id <= 0) {
      router.replace('/')
      return
    }

    // 2. 加载当前训练状态
    await userStore.fetchCurrentState()

    // 3. 组装参数（优先从 URL query params 读取，因为首次生成时 UserCurrentState 还不存在）
    const preferred_days = (route.query.preferredDays as string)
      || userStore.currentState?.preferred_days
      || '1,3,5'
    const days_per_week = preferred_days.split(',').filter(Boolean).length || 3
    const goal = (route.query.goal as string) || profile.goal || '增肌'
    const experience_level = (route.query.experience as string)
      || userStore.currentState?.experience_level
      || profile.experience || '新手'
    const workout_location = (route.query.location as string)
      || profile.workout_location || '居家'

    loadingProfile.value = false

    // 4. 开始生成（异步轮询，不再依赖 SSE 长连接）
    await cycleStore.initPlanPolling({
      goal,
      experience_level,
      workout_location,
      days_per_week,
      preferred_days,
      city: profile.city || '',
      height: profile.height ?? undefined,
      weight: profile.weight ?? undefined,
      age: profile.age ?? undefined,
      gender: profile.gender ?? undefined,
    })

    // 生成成功
    userStore.markOnboardingDone()
    setTimeout(() => router.push('/home'), 800)
  } catch (e: any) {
    loadingProfile.value = false
    if (e?.message?.includes('404') || e?.response?.status === 404) {
      router.replace('/')
    }
    // 其他错误由 cycleStore.error 展示
  }
}
</script>

<style scoped>
.generating-container {
  min-height: calc(100vh - 40px);
  background: var(--bg-page);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
}

.gen-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 16px;
}
.loading-spinner {
  font-size: 48px;
  animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
}
.gen-loading h2 {
  font-size: 20px;
  color: var(--text-secondary);
  font-weight: 600;
}

.gen-header {
  width: 100%; max-width: 600px;
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 24px;
  background: var(--bg-card); border-radius: 12px;
  box-shadow: var(--shadow-card);
}
.gen-header-left { display: flex; align-items: center; gap: 10px; }
.gen-header-icon { font-size: 28px; }
.gen-header-left h2 { margin: 0; font-size: 20px; font-weight: 700; color: var(--text-primary); }
.gen-header-right { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--text-secondary); }
.gen-divider { color: var(--border-color); }
.gen-progress-text { color: var(--brand-orange); font-weight: 600; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.gen-progress-bar {
  width: 100%; max-width: 600px;
  display: flex; align-items: center; gap: 12px;
}
.progress-bg { flex: 1; height: 12px; background: var(--bg-subtle); border-radius: 6px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 6px; background: linear-gradient(90deg, var(--brand-orange), var(--brand-orange-light)); transition: width 0.5s ease; }
.progress-fill.complete { background: var(--color-success); }
.progress-pct { font-size: 16px; font-weight: 700; color: var(--text-primary); min-width: 40px; text-align: right; }

.gen-status-text {
  font-size: 16px; color: var(--text-secondary); text-align: center;
  padding: 20px; background: var(--bg-card); border-radius: 12px;
  width: 100%; max-width: 600px; min-height: 60px;
  display: flex; align-items: center; justify-content: center;
}

.gen-error {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 20px; background: var(--color-error-subtle); border: 1px solid var(--color-error); border-radius: 8px;
  color: var(--color-error-deep); font-size: 14px;
}
.retry-btn {
  padding: 6px 16px; border: 1px solid var(--color-error); border-radius: 6px;
  background: var(--bg-card); color: var(--color-error); font-size: 13px; cursor: pointer;
}
.retry-btn:hover { background: var(--color-error); color: #fff; }

.gen-done {
  font-size: 20px; font-weight: 700; color: var(--color-success);
  padding: 40px; background: var(--color-success-subtle); border-radius: 12px;
  width: 100%; max-width: 600px; text-align: center;
}
</style>
