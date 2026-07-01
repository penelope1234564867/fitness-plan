import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/stores/user'

describe('userStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('currentState', () => {
    it('starts with null currentState', () => {
      const store = useUserStore()
      expect(store.currentState).toBeNull()
    })

    it('starts with null profile', () => {
      const store = useUserStore()
      expect(store.profile).toBeNull()
    })

    it('markOnboardingDone sets isFirstVisit to false', () => {
      const store = useUserStore()
      store.markOnboardingDone()
      expect(store.isFirstVisit).toBe(false)
    })

    it('resetOnboarding sets isFirstVisit to true', () => {
      const store = useUserStore()
      store.resetOnboarding()
      expect(store.isFirstVisit).toBe(true)
    })
  })
})
