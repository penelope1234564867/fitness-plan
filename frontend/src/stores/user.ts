import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createOrUpdateProfile, getProfile } from '@/services/api'
import type { UserProfile, UserProfileResponse } from '@/types'

export const useUserStore = defineStore('user', () => {
  const profile = ref<UserProfileResponse | null>(null)
  const loading = ref(false)

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

  return { profile, loading, fetchProfile, saveProfile }
})
