import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCycleStore } from '@/stores/cycle'

describe('cycleStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('computed properties', () => {
    it('mesocyclePhaseLabel returns correct Chinese label for foundational', () => {
      const store = useCycleStore()
      store.currentWeek = { mesocycle_phase: 'foundational' } as any
      expect(store.mesocyclePhaseLabel).toBe('基础适应期')
    })

    it('mesocyclePhaseLabel returns correct Chinese label for hypertrophy', () => {
      const store = useCycleStore()
      store.currentWeek = { mesocycle_phase: 'hypertrophy' } as any
      expect(store.mesocyclePhaseLabel).toBe('肌肥大期')
    })

    it('mesocyclePhaseLabel returns correct Chinese label for strength', () => {
      const store = useCycleStore()
      store.currentWeek = { mesocycle_phase: 'strength' } as any
      expect(store.mesocyclePhaseLabel).toBe('力量期')
    })

    it('mesocyclePhaseLabel returns correct Chinese label for deload', () => {
      const store = useCycleStore()
      store.currentWeek = { mesocycle_phase: 'deload' } as any
      expect(store.mesocyclePhaseLabel).toBe('减载周')
    })

    it('mesocyclePhaseLabel returns empty string for unknown phase', () => {
      const store = useCycleStore()
      store.currentWeek = { mesocycle_phase: 'unknown' } as any
      expect(store.mesocyclePhaseLabel).toBe('')
    })

    it('weekCompletionRate calculates 0% when no days', () => {
      const store = useCycleStore()
      store.currentWeek = { days: [] } as any
      expect(store.weekCompletionRate).toBe(0)
    })

    it('weekCompletionRate calculates 67% for 2/3 completed', () => {
      const store = useCycleStore()
      store.currentWeek = {
        days: [
          { is_completed: true },
          { is_completed: false },
          { is_completed: true },
        ],
      } as any
      expect(store.weekCompletionRate).toBe(67)
    })

    it('weekCompletionRate calculates 100% when all days completed', () => {
      const store = useCycleStore()
      store.currentWeek = {
        days: [
          { is_completed: true },
          { is_completed: true },
        ],
      } as any
      expect(store.weekCompletionRate).toBe(100)
    })

    it('isWeekComplete is true when all days done', () => {
      const store = useCycleStore()
      store.currentWeek = {
        days: [
          { is_completed: true },
          { is_completed: true },
          { is_completed: true },
        ],
      } as any
      expect(store.isWeekComplete).toBe(true)
    })

    it('isWeekComplete is false when not all done', () => {
      const store = useCycleStore()
      store.currentWeek = {
        days: [
          { is_completed: true },
          { is_completed: false },
        ],
      } as any
      expect(store.isWeekComplete).toBe(false)
    })

    it('isWeekComplete is false when no days', () => {
      const store = useCycleStore()
      store.currentWeek = { days: [] } as any
      expect(store.isWeekComplete).toBe(false)
    })

    it('currentWeekNumber returns week_number from currentWeek', () => {
      const store = useCycleStore()
      store.currentWeek = { week_number: 3 } as any
      expect(store.currentWeekNumber).toBe(3)
    })

    it('currentWeekNumber returns 0 when no currentWeek', () => {
      const store = useCycleStore()
      store.currentWeek = null
      expect(store.currentWeekNumber).toBe(0)
    })
  })

  describe('state defaults', () => {
    it('starts with null currentWeek', () => {
      const store = useCycleStore()
      expect(store.currentWeek).toBeNull()
    })

    it('starts with null macrocycle', () => {
      const store = useCycleStore()
      expect(store.macrocycle).toBeNull()
    })

    it('starts not generating', () => {
      const store = useCycleStore()
      expect(store.isGenerating).toBe(false)
    })

    it('starts with progress 0', () => {
      const store = useCycleStore()
      expect(store.generationProgress).toBe(0)
    })
  })
})
