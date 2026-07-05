import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWorkoutStore } from '@/stores/workout'
import type { ExerciseSlot } from '@/types'

function createMockDayDetail() {
  return {
    date: '2026-07-06',
    day_status: 'pending',
    day_label: '推',
    focus: '胸部',
    week_id: 1,
    mesocycle_phase: 'foundational',
    is_rest_day: false,
    has_plan: true,
    slots: [
      {
        id: 1, day_id: 1, phase_type: 'main' as const, sort_order: 1,
        wger_id: 100, exercise_name: '俯卧撑',
        target_sets: 3, target_reps: 10, target_reps_max: 12,
        weight_kg: 0, weight_suggestion: '自重', rest_seconds: 60,
        actual_sets: 0, actual_reps: 0, actual_weight_kg: 0,
        rpe: 0, notes: '',
        exercise: null,
      },
      {
        id: 2, day_id: 1, phase_type: 'main' as const, sort_order: 2,
        wger_id: 101, exercise_name: '哑铃飞鸟',
        target_sets: 3, target_reps: 12, target_reps_max: 15,
        weight_kg: 8, weight_suggestion: '8kg', rest_seconds: 60,
        actual_sets: 0, actual_reps: 0, actual_weight_kg: 0,
        rpe: 0, notes: '',
        exercise: null,
      },
    ] as ExerciseSlot[],
    warmup: [],
    main: [
      { name: '俯卧撑', sets: 3, reps: 10 },
      { name: '哑铃飞鸟', sets: 3, reps: 12 },
    ],
    cardio: null,
    stretch: [],
  }
}

describe('workoutStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('currentDay from dayDetail', () => {
    it('builds from dayDetail when selectedDate is set', async () => {
      const store = useWorkoutStore()
      store.dayDetail = createMockDayDetail() as any
      store.selectedDate = '2026-07-06'

      // Wait for watch to fire
      await vi.waitFor(() => {
        expect(store.currentDay).not.toBeNull()
      })

      expect(store.currentDay!.day_label).toBe('推')
      expect(store.currentDay!.slots).toHaveLength(2)
      expect(store.currentDay!.main).toHaveLength(2)
    })

    it('returns null when day has no plan', () => {
      const store = useWorkoutStore()
      store.dayDetail = {
        date: '2026-07-07',
        day_status: 'no_plan',
        has_plan: false,
      } as any
      store.selectedDate = '2026-07-07'
      expect(store.currentDay).toBeNull()
    })
  })

  describe('toggleExercise', () => {
    it('toggles _completed from false to true and sets default RPE', () => {
      const store = useWorkoutStore()
      store.dayDetail = createMockDayDetail() as any
      store.selectedDate = '2026-07-06'

      store.toggleExercise(1)
      const slot = store.currentDay!.slots.find(s => s.id === 1)
      expect(slot!._completed).toBe(true)
      expect(slot!._rpeQuick).toBe('normal')
      expect(slot!.rpe).toBe(7)
    })

    it('toggles _completed from true to false and clears RPE', () => {
      const store = useWorkoutStore()
      store.dayDetail = createMockDayDetail() as any
      store.selectedDate = '2026-07-06'

      store.toggleExercise(1)
      store.toggleExercise(1)
      const slot = store.currentDay!.slots.find(s => s.id === 1)
      expect(slot!._completed).toBe(false)
      expect(slot!._rpeQuick).toBeNull()
      expect(slot!.rpe).toBe(0)
    })

    it('toggle reflected in main array (same objects as slots)', () => {
      const store = useWorkoutStore()
      store.dayDetail = createMockDayDetail() as any
      store.selectedDate = '2026-07-06'

      store.toggleExercise(1)
      // 从 main 数组中找同一个动作 — 应该和 slots 是同一个对象
      const mainSlot = store.currentDay!.main.find(s => s.id === 1)
      expect(mainSlot!._completed).toBe(true)
      // 验证对象引用相同
      const slot = store.currentDay!.slots.find(s => s.id === 1)
      expect(mainSlot).toBe(slot)
    })
  })

  describe('setRPEQuick', () => {
    it('sets easy to RPE 4 and marks completed', () => {
      const store = useWorkoutStore()
      store.dayDetail = createMockDayDetail() as any
      store.selectedDate = '2026-07-06'

      store.setRPEQuick(1, 'easy')
      const slot = store.currentDay!.slots.find(s => s.id === 1)
      expect(slot!._rpeQuick).toBe('easy')
      expect(slot!.rpe).toBe(4)
      expect(slot!._completed).toBe(true)
    })

    it('sets hard to RPE 9 and marks completed', () => {
      const store = useWorkoutStore()
      store.dayDetail = createMockDayDetail() as any
      store.selectedDate = '2026-07-06'

      store.setRPEQuick(1, 'hard')
      const slot = store.currentDay!.slots.find(s => s.id === 1)
      expect(slot!._rpeQuick).toBe('hard')
      expect(slot!.rpe).toBe(9)
    })
  })

  describe('warmup/main/cardio/stretch grouping', () => {
    it('groups slots from dayDetail response', () => {
      const store = useWorkoutStore()
      const detail = createMockDayDetail()
      // 添加一个 warmup slot 到 slots 数组中
      const warmupSlot: Record<string, unknown> = {
        id: 3, day_id: 1, phase_type: 'warmup', sort_order: 0,
        wger_id: null, exercise_name: '开合跳',
        target_sets: 1, target_reps: 1, target_reps_max: 1,
        weight_kg: 0, weight_suggestion: '', rest_seconds: 15,
        actual_sets: 0, actual_reps: 0, actual_weight_kg: 0,
        rpe: 0, notes: '',
        exercise: null,
      }
      detail.slots.unshift(warmupSlot as unknown as ExerciseSlot)
      store.dayDetail = detail as any
      store.selectedDate = '2026-07-06'

      expect(store.currentDay!.warmup).toHaveLength(1)
      expect(store.currentDay!.main).toHaveLength(2)
      expect(store.currentDay!.cardio).toBeNull()
      expect(store.currentDay!.stretch).toHaveLength(0)
    })
  })

  describe('todayStr', () => {
    it('returns today date string', () => {
      const store = useWorkoutStore()
      const today = new Date()
      const yyyymmdd = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
      expect(store.todayStr).toBe(yyyymmdd)
    })
  })
})
