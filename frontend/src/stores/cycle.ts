/**
 * cycleStore — 周期管理
 *
 * 管理大周期 / 中周期 / 周计划的完整生命周期。
 * 包含 SSE 生成状态、进度追踪、computed 属性（阶段标签/完成率）。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/services/api'
import { estimateProgress } from '@/services/sse'
import dayjs from 'dayjs'
import type { WeekPlan, MacrocycleDetail, MacrocycleSummary, InitPlanRequest, CalendarEntry } from '@/types'

export const useCycleStore = defineStore('cycle', () => {
  // ── 状态 ──
  const currentWeek = ref<WeekPlan | null>(null)
  const macrocycle = ref<MacrocycleDetail | null>(null)
  const macrocycles = ref<MacrocycleSummary[]>([])

  // SSE 生成状态
  const isGenerating = ref(false)
  const generationProgress = ref(0)
  const generationStatus = ref('')
  const generationPhase = ref('')

  // 日历数据（按日期索引）
  const calendarEntries = ref<Map<string, CalendarEntry>>(new Map())
  const calendarRange = ref<{ start: string; end: string }>({ start: '', end: '' })

  const loading = ref(false)
  const error = ref<string | null>(null)

  // ── Computed ──
  const currentMesocycle = computed(() => {
    if (!currentWeek.value || !macrocycle.value) return null
    return macrocycle.value.mesocycles.find(
      m => m.phase === currentWeek.value!.mesocycle_phase,
    ) ?? null
  })

  const currentWeekNumber = computed(() => currentWeek.value?.week_number ?? 0)
  const mesocycleTotalWeeks = computed(() => currentMesocycle.value?.week_count ?? 4)

  const mesocyclePhaseLabel = computed(() => {
    const labels: Record<string, string> = {
      foundational: '基础适应期',
      hypertrophy: '肌肥大期',
      strength: '力量期',
      deload: '减载周',
    }
    return labels[currentWeek.value?.mesocycle_phase ?? ''] ?? ''
  })

  const weekCompletionRate = computed(() => {
    if (!currentWeek.value?.days.length) return 0
    const done = currentWeek.value.days.filter(d => d.is_completed).length
    return Math.round((done / currentWeek.value.days.length) * 100)
  })

  const isWeekComplete = computed(() => {
    if (!currentWeek.value?.days.length) return false
    return currentWeek.value.days.every(d => d.is_completed)
  })

  // ── Actions ──

  async function initPlan(req: InitPlanRequest) {
    isGenerating.value = true
    generationProgress.value = 0
    generationStatus.value = '🚀 开始初始化...'
    error.value = null

    try {
      const result = await api.initPlan(req, {
        onProgress: (data) => {
          generationStatus.value = data.text
          generationPhase.value = data.phase
          generationProgress.value = estimateProgress(data.phase)
        },
        onDayDone: (data) => {
          generationStatus.value = `✅ 第${data.day}天生成完成`
        },
        onError: (data) => {
          error.value = data.text
        },
      })

      currentWeek.value = result
      generationProgress.value = 100
      generationStatus.value = '✅ 计划生成成功！'
      await fetchMacrocycles()
      return result
    } catch (e: any) {
      error.value = e.message || '初始化失败'
      throw e
    } finally {
      setTimeout(() => { isGenerating.value = false }, 500)
    }
  }

  async function generateNextWeek() {
    isGenerating.value = true
    generationProgress.value = 0
    generationStatus.value = '📋 分析前一周打卡数据...'
    error.value = null

    try {
      const result = await api.generateNextWeek({
        onProgress: (data) => {
          generationStatus.value = data.text
          generationPhase.value = data.phase
          generationProgress.value = estimateProgress(data.phase)
        },
        onDayDone: (data) => {
          generationStatus.value = `✅ 第${data.day}天已生成`
        },
        onError: (data) => {
          error.value = data.text
        },
      })

      currentWeek.value = result
      generationProgress.value = 100
      generationStatus.value = '✅ 下周计划已生成！'
      await fetchMacrocycles()
      return result
    } catch (e: any) {
      error.value = e.message || '生成失败'
      throw e
    } finally {
      setTimeout(() => { isGenerating.value = false }, 500)
    }
  }

  async function fetchCurrentWeek() {
    loading.value = true
    try {
      currentWeek.value = await api.fetchCurrentWeek()
      return currentWeek.value
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchMacrocycles() {
    try {
      macrocycles.value = await api.listMacrocycles()
      if (macrocycles.value.length > 0) {
        macrocycle.value = await api.getMacrocycleDetail(macrocycles.value[0].id)
        // 初始化日历范围
        initCalendarRange()
      }
    } catch { /* 首次可能没有大周期 */ }
  }

  /** 获取指定日期的日历数据 */
  async function fetchCalendarData(from: string, to: string) {
    try {
      const resp = await api.fetchCalendarData(from, to)
      const map = new Map<string, CalendarEntry>()
      for (const entry of resp.entries) {
        map.set(entry.date, entry)
      }
      calendarEntries.value = map
    } catch (e: any) {
      console.error('[CycleStore] 加载日历数据失败:', e.message)
    }
  }

  /** 初始化日历范围：从 Macrocycle 推算 */
  function initCalendarRange() {
    if (!macrocycle.value?.start_date) return
    const start = macrocycle.value.start_date
    // 终点：大周期最后一个中周期的最后一周 + 1个月
    const lastMeso = macrocycle.value.mesocycles[macrocycle.value.mesocycles.length - 1]
    if (lastMeso?.weeks?.length) {
      const lastWeek = lastMeso.weeks[lastMeso.weeks.length - 1]
      // 粗略推算：start_date + (mesocycle_weeks * 7) + 30
      const totalWeeks = lastMeso.week_count || 4
      const endDate = dayjs(start).add(totalWeeks * 7 + 30, 'day').format('YYYY-MM-DD')
      calendarRange.value = { start, end: endDate }
    } else {
      // 无中周期数据时，起始 + 3 个月
      calendarRange.value = { start, end: '' }
    }
  }

  return {
    currentWeek, macrocycle, macrocycles,
    calendarEntries, calendarRange,
    isGenerating, generationProgress, generationStatus, generationPhase,
    loading, error,
    currentMesocycle, currentWeekNumber, mesocycleTotalWeeks,
    mesocyclePhaseLabel, weekCompletionRate, isWeekComplete,
    initPlan, generateNextWeek, fetchCurrentWeek, fetchMacrocycles,
    fetchCalendarData, initCalendarRange,
  }
})
