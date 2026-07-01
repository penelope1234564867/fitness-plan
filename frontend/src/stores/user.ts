import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { createOrUpdateProfile, getProfile, fetchCurrentState as apiFetchState, updateCurrentState as apiUpdateState } from '@/services/api'
import type { UserProfile, UserProfileResponse, UserCurrentState, UserCurrentStateUpdate } from '@/types'

export const useUserStore = defineStore('user', () => {
  const profile = ref<UserProfileResponse | null>(null)
  const currentState = ref<UserCurrentState | null>(null)
  const loading = ref(false)

  // 是否首次使用（控制三步引导显示）
  const isFirstVisit = ref(localStorage.getItem('fitness_first_visit') !== 'false')

  // 统计数据
  const stats = ref({
    totalWorkoutDays: 0,
    currentStreak: 0,
    monthlyDone: 0,
    monthlyTotal: 0,
  })

  const fullName = computed(() => {
    if (!profile.value) return ''
    const p = profile.value
    return `${p.gender === 'male' ? '♂' : '♀'} ${p.height || '?'}cm ${p.weight || '?'}kg`
  })

  // ── 引导状态 ──

  function markOnboardingDone() {
    isFirstVisit.value = false
    localStorage.setItem('fitness_first_visit', 'false')
  }

  function resetOnboarding() {
    isFirstVisit.value = true
    localStorage.setItem('fitness_first_visit', 'true')
  }

  // ── 用户状态（新引擎）──

  async function fetchCurrentState() {
    try {
      currentState.value = await apiFetchState()
      return currentState.value
    } catch {
      /* 首次可能没有状态 */
      return null
    }
  }

  async function saveCurrentState(data: UserCurrentStateUpdate) {
    await apiUpdateState(data)
    if (currentState.value) {
      Object.assign(currentState.value, data)
    }
  }

  // ── 用户资料（旧引擎，过渡用）──

  async function fetchProfile() {
    loading.value = true
    try {
      const res = await getProfile()
      profile.value = res.id > 0 ? res : null
      return profile.value
    } finally {
      loading.value = false
    }
  }

  async function saveProfile(data: UserProfile) {
    loading.value = true
    try {
      const res = await createOrUpdateProfile(data)
      profile.value = res
      return res
    } finally {
      loading.value = false
    }
  }

  return {
    profile,
    currentState,
    loading,
    isFirstVisit,
    stats,
    fullName,
    markOnboardingDone,
    resetOnboarding,
    fetchCurrentState,
    saveCurrentState,
    fetchProfile,
    saveProfile,
  }
})
