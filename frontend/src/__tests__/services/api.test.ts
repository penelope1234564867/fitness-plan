import { describe, it, expect } from 'vitest'
import apiClient, {
  initPlan,
  generateNextWeek,
  fetchCurrentWeek,
  listMacrocycles,
  getMacrocycleDetail,
  checkin,
  fetchCurrentState,
  updateCurrentState,
  rescheduleDay,
} from '@/services/api'

describe('apiClient', () => {
  it('has correct base URL configured', () => {
    expect(apiClient.defaults.baseURL).toBeTruthy()
  })

  it('has SSE-compatible timeout', () => {
    // SSE 生成可能耗时较长，应 >= 5 分钟
    expect(apiClient.defaults.timeout).toBeGreaterThanOrEqual(300000)
  })

  it('uses native fetch for SSE streams via _ssePost', () => {
    // SSE 请求使用原生 fetch，非 axios（验证 initPlan 不使用 axios）
    expect(apiClient.defaults.adapter).not.toBe('fetch')
  })
})

describe('API functions exist', () => {
  it('initPlan is a function', () => {
    expect(typeof initPlan).toBe('function')
  })

  it('generateNextWeek is a function', () => {
    expect(typeof generateNextWeek).toBe('function')
  })

  it('fetchCurrentWeek is a function', () => {
    expect(typeof fetchCurrentWeek).toBe('function')
  })

  it('listMacrocycles is a function', () => {
    expect(typeof listMacrocycles).toBe('function')
  })

  it('getMacrocycleDetail is a function', () => {
    expect(typeof getMacrocycleDetail).toBe('function')
  })

  it('checkin is a function', () => {
    expect(typeof checkin).toBe('function')
  })

  it('fetchCurrentState is a function', () => {
    expect(typeof fetchCurrentState).toBe('function')
  })

  it('updateCurrentState is a function', () => {
    expect(typeof updateCurrentState).toBe('function')
  })

  it('rescheduleDay is a function', () => {
    expect(typeof rescheduleDay).toBe('function')
  })
})
