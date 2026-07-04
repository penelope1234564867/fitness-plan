import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ExerciseRow from '@/components/ExerciseRow.vue'
import type { ExerciseSlot } from '@/types'

function makeSlot(overrides: Partial<ExerciseSlot> = {}): ExerciseSlot {
  return {
    id: 1, day_id: 1,
    phase_type: 'main', sort_order: 1,
    wger_id: null, exercise_name: '俯卧撑',
    target_sets: 3, target_reps: 10, target_reps_max: 12,
    weight_kg: 0, weight_suggestion: '自重', rest_seconds: 60,
    actual_sets: 0, actual_reps: 0, rpe: 0, notes: '', actual_weight_kg: 0,
    exercise: null,
    _completed: false, _rpeQuick: null, _loading: false,
    change_type: 'none', weight_diff: 0, prev_weight_kg: 0, prev_target_reps: 0,
    ...overrides,
  }
}

describe('ExerciseRow', () => {
  it('renders exercise name and detail', () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot() },
    })
    expect(wrapper.text()).toContain('俯卧撑')
    expect(wrapper.text()).toContain('3组×10次')
  })

  it('renders weight when provided', () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot({ weight_suggestion: '10kg' }) },
    })
    expect(wrapper.text()).toContain('10kg')
  })

  it('shows RPE buttons for main phase exercise', () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot() },
    })
    // 应显示三个 RPE 快捷按钮
    expect(wrapper.find('.rpe-btn-easy').exists()).toBe(true)
    expect(wrapper.find('.rpe-btn-normal').exists()).toBe(true)
    expect(wrapper.find('.rpe-btn-hard').exists()).toBe(true)
  })

  it('does NOT show RPE buttons for warmup phase', () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot({ phase_type: 'warmup' }) },
    })
    expect(wrapper.find('.rpe-btn-easy').exists()).toBe(false)
  })

  it('emits toggle on checkbox click', async () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot() },
    })
    await wrapper.find('.exercise-check').trigger('click')
    expect(wrapper.emitted('toggle')).toBeTruthy()
  })

  it('emits set-rpe-quick with "easy" when clicking easy button', async () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot() },
    })
    await wrapper.find('.rpe-btn-easy').trigger('click')
    expect(wrapper.emitted('set-rpe-quick')).toBeTruthy()
    expect(wrapper.emitted('set-rpe-quick')![0]).toEqual(['easy'])
  })

  it('emits set-rpe-quick with "hard" when clicking hard button', async () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot() },
    })
    await wrapper.find('.rpe-btn-hard').trigger('click')
    expect(wrapper.emitted('set-rpe-quick')![0]).toEqual(['hard'])
  })

  it('emits show-detail on name click', async () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot() },
    })
    await wrapper.find('.exercise-info').trigger('click')
    expect(wrapper.emitted('show-detail')).toBeTruthy()
  })

  it('applies completed class when _completed is true', () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot({ _completed: true }) },
    })
    expect(wrapper.classes()).toContain('completed')
  })

  it('highlights the selected RPE button', () => {
    const wrapper = mount(ExerciseRow, {
      props: { exercise: makeSlot({ _rpeQuick: 'easy', _completed: true }) },
    })
    expect(wrapper.find('.rpe-btn-easy').classes()).toContain('active')
    expect(wrapper.find('.rpe-btn-normal').classes()).not.toContain('active')
  })
})
