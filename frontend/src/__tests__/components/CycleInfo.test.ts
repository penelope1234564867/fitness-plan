import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import CycleInfo from '@/components/CycleInfo.vue'

describe('CycleInfo', () => {
  it('shows phase label and week progress', () => {
    const wrapper = mount(CycleInfo, {
      props: {
        phaseLabel: '基础适应期',
        weekNumber: 3,
        totalWeeks: 4,
        completionRate: 50,
        isWeekComplete: false,
      },
    })
    expect(wrapper.text()).toContain('基础适应期')
    expect(wrapper.text()).toContain('第3周')
    expect(wrapper.text()).toContain('共4周')
  })

  it('shows completion rate', () => {
    const wrapper = mount(CycleInfo, {
      props: {
        phaseLabel: '基础适应期',
        weekNumber: 1,
        totalWeeks: 4,
        completionRate: 67,
        isWeekComplete: false,
      },
    })
    expect(wrapper.text()).toContain('67%')
  })

  it('shows generate button when week is complete', () => {
    const wrapper = mount(CycleInfo, {
      props: {
        phaseLabel: '基础适应期',
        weekNumber: 4,
        totalWeeks: 4,
        completionRate: 100,
        isWeekComplete: true,
      },
    })
    const btn = wrapper.find('.generate-btn')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeFalsy()
  })

  it('disables generate button when week is not complete', () => {
    const wrapper = mount(CycleInfo, {
      props: {
        phaseLabel: '基础适应期',
        weekNumber: 2,
        totalWeeks: 4,
        completionRate: 33,
        isWeekComplete: false,
      },
    })
    const btn = wrapper.find('.generate-btn')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('emits generate on button click', async () => {
    const wrapper = mount(CycleInfo, {
      props: {
        phaseLabel: '基础适应期',
        weekNumber: 4,
        totalWeeks: 4,
        completionRate: 100,
        isWeekComplete: true,
      },
    })
    await wrapper.find('.generate-btn').trigger('click')
    expect(wrapper.emitted('generate')).toBeTruthy()
  })

  it('shows deload indicator for deload phase', () => {
    const wrapper = mount(CycleInfo, {
      props: {
        phaseLabel: '减载周',
        weekNumber: 1,
        totalWeeks: 1,
        completionRate: 0,
        isWeekComplete: false,
        isDeload: true,
      },
    })
    expect(wrapper.text()).toContain('恢复为主')
  })
})
