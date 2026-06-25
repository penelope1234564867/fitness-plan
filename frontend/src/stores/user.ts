import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { createOrUpdateProfile, getProfile } from '@/services/api'
import type { UserProfile, UserProfileResponse } from '@/types'

export const useUserStore = defineStore('user', () => {
  const profile = ref<UserProfileResponse | null>(null)
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

  /** 标记首次引导已完成 */
  function markOnboardingDone() {
    isFirstVisit.value = false
    localStorage.setItem('fitness_first_visit', 'false')
  }

  /** 重置引导状态（允许重新走引导） */
  function resetOnboarding() {
    isFirstVisit.value = true
    localStorage.setItem('fitness_first_visit', 'true')
  }

  /** 加载用户资料 */
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

  /** 创建或更新用户资料 */
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
    loading,
    isFirstVisit,
    stats,
    fullName,
    markOnboardingDone,
    resetOnboarding,
    fetchProfile,
    saveProfile,
  }
})
