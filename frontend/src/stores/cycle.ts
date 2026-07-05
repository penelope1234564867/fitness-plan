/**
 * cycleStore — 周期管理
 *
 * 管理大周期 / 中周期 / 周计划的完整生命周期。
 * 包含 SSE 生成状态、进度追踪、computed 属性（阶段标签/完成率）。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/services/api'
import { getProgress } from '@/services/sse'
import dayjs from 'dayjs'
import type { WeekPlan, MacrocycleDetail, MacrocycleSummary, InitPlanRequest, TaskStatusResponse, CalendarEntry, PhaseSegment, RoadmapData } from '@/types'
import { PHASE_LABEL_MAP, PHASE_COLORS } from '@/types'

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
  /** 实时日志列表 { time, phase, text, day?, progress? } */
  const generationLog = ref<{ time: string; phase: string; text: string; day?: number; progress: number }[]>([])
  const MAX_LOG_ENTRIES = 200

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
    const goal = macrocycle.value?.goal || '增肌'
    const labels = PHASE_LABEL_MAP[goal] || PHASE_LABEL_MAP['增肌']
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

  /** 路线图数据：转为前端展示格式 */
  const roadmapData = computed<RoadmapData | null>(() => {
    if (!macrocycle.value || !macrocycle.value.mesocycles.length) return null
    const goal = macrocycle.value.goal || '增肌'
    const phaseLabels = PHASE_LABEL_MAP[goal] || PHASE_LABEL_MAP['增肌']
    const currentPhase = currentWeek.value?.mesocycle_phase ?? ''

    let totalWeeksSum = 0
    let currentWeekNumber = 0
    let found = false

    const segments: PhaseSegment[] = macrocycle.value.mesocycles.map(ms => {
      totalWeeksSum += ms.week_count
      let segStatus: 'completed' | 'active' | 'pending' = 'pending'
      let weekInPhase = 0

      if (ms.status === 'completed') {
        segStatus = 'completed'
      } else if (ms.phase === currentPhase && !found) {
        segStatus = 'active'
        weekInPhase = currentWeek.value?.week_number ?? 1
        currentWeekNumber = totalWeeksSum - ms.week_count + weekInPhase
        found = true
      }

      return {
        phase: ms.phase,
        label: phaseLabels[ms.phase] || ms.phase,
        color: PHASE_COLORS[ms.phase] || '#999',
        status: segStatus,
        weekCount: ms.week_count,
        currentWeek: segStatus === 'active' ? weekInPhase : undefined,
        completionRate: ms.completion_rate ?? 0,
        weeks: ms.weeks || [],
      }
    })

    return {
      macrocycleId: macrocycle.value.id,
      goal,
      totalWeeks: totalWeeksSum,
      currentWeekNumber,
      mesocycles: segments,
    }
  })

  /** 当前阶段的下一个阶段名称 */
  const nextPhaseLabel = computed<string | null>(() => {
    if (!roadmapData.value) return null
    const segs = roadmapData.value.mesocycles
    const idx = segs.findIndex(s => s.status === 'active')
    if (idx >= 0 && idx < segs.length - 1) return segs[idx + 1].label
    return null
  })

  // ── Actions ──

  /** 添加一条日志 + 更新进度（重复文本只更新进度，不新增条目） */
  function _addLog(data: { phase: string; text: string; progress?: number; day?: number }) {
    const now = new Date()
    const time = now.toLocaleTimeString('zh-CN', { hour12: false })
    const pct = getProgress(data)
    const last = generationLog.value[generationLog.value.length - 1]
    if (last && last.text === data.text && last.day === data.day) {
      // 相同文本只更新进度
      last.progress = pct
      return
    }
    generationLog.value.push({ time, phase: data.phase, text: data.text, day: data.day, progress: pct })
    if (generationLog.value.length > MAX_LOG_ENTRIES) {
      generationLog.value = generationLog.value.slice(-MAX_LOG_ENTRIES)
    }
  }

  /** → polling ref（追踪轮询定时器） */
  let _pollTimer: ReturnType<typeof setTimeout> | null = null
  let _pollTaskId = ref('')

  async function initPlanPolling(req: InitPlanRequest) {
    // 停止之前的轮询
    stopPolling()

    isGenerating.value = true
    generationProgress.value = 0
    generationStatus.value = '🚀 创建生成任务...'
    generationLog.value = []
    error.value = null

    _addLog({ phase: 'init', text: '🚀 开始生成训练计划...', progress: 0 })

    try {
      // 1. 创建后台任务
      const { task_id } = await api.createGenerateTask(req)
      _pollTaskId.value = task_id
      _addLog({ phase: 'init', text: `📋 任务已创建: ${task_id}`, progress: 1 })

      // 2. 轮询等待完成
      const result = await _pollUntilDone(task_id)

      // 3. 设置结果
      currentWeek.value = result.week
      generationProgress.value = 100
      generationStatus.value = '✅ 计划生成成功！'
      _addLog({ phase: 'done', text: '✅ 计划生成成功！', progress: 100 })
      await fetchMacrocycles()
      return result.week
    } catch (e: any) {
      error.value = e.message || '生成失败'
      _addLog({ phase: 'error', text: `❌ ${e.message}`, progress: generationProgress.value })
      throw e
    } finally {
      setTimeout(() => { isGenerating.value = false }, 500)
    }
  }

  /** 轮询任务直到 done 或 error */
  function _pollUntilDone(taskId: string): Promise<TaskStatusResponse> {
    return new Promise((resolve, reject) => {
      let retries = 0
      const MAX_RETRIES = 3

      function poll() {
        _pollTimer = setTimeout(async () => {
          try {
            const status = await api.fetchTaskStatus(taskId)

            // 更新进度
            generationProgress.value = status.progress
            generationStatus.value = status.text
            generationPhase.value = status.phase
            _addLog({ phase: status.phase, text: status.text, progress: status.progress })

            if (status.status === 'done') {
              resolve(status)
            } else if (status.status === 'error') {
              reject(new Error(status.error || '生成失败'))
            } else {
              retries = 0  // 重置重试计数
              poll()       // 继续轮询
            }
          } catch (e: any) {
            retries++
            if (retries > MAX_RETRIES) {
              reject(new Error(`轮询失败: ${e.message}`))
            } else {
              // 网络抖动，等一会重试
              _addLog({ phase: 'retry', text: `⚠️ 轮询重试 ${retries}/${MAX_RETRIES}...`, progress: generationProgress.value })
              _pollTimer = setTimeout(poll, 3000)
            }
          }
        }, 2000)  // 每 2 秒轮询一次
      }

      poll()
    })
  }

  /** 停止轮询（页面离开时调用） */
  function stopPolling() {
    if (_pollTimer) {
      clearTimeout(_pollTimer)
      _pollTimer = null
    }
  }

  async function initPlan(req: InitPlanRequest) {
    isGenerating.value = true
    generationProgress.value = 0
    generationStatus.value = '🚀 开始初始化...'
    generationLog.value = []
    error.value = null

    _addLog({ phase: 'init', text: '🚀 开始生成训练计划...', progress: 0 })

    try {
      const result = await api.initPlan(req, {
        onProgress: (data) => {
          generationStatus.value = data.text
          generationPhase.value = data.phase
          const pct = getProgress(data)
          generationProgress.value = pct
          _addLog({ ...data, progress: pct })
        },
        onDayDone: (data) => {
          generationStatus.value = `✅ 第${data.day}天生成完成`
          _addLog({ phase: 'day_done', text: `✅ 第${data.day}天 (${data.focus}) 完成 — ${data.main_count} 个主项`, day: data.day, progress: generationProgress.value })
        },
        onError: (data) => {
          error.value = data.text
          _addLog({ phase: 'error', text: `❌ ${data.text}`, progress: generationProgress.value })
        },
      })

      currentWeek.value = result
      generationProgress.value = 100
      generationStatus.value = '✅ 计划生成成功！'
      _addLog({ phase: 'done', text: '✅ 计划生成成功！', progress: 100 })
      await fetchMacrocycles()
      return result
    } catch (e: any) {
      error.value = e.message || '初始化失败'
      _addLog({ phase: 'error', text: `❌ ${e.message}`, progress: generationProgress.value })
      throw e
    } finally {
      setTimeout(() => { isGenerating.value = false }, 500)
    }
  }

  async function generateNextWeekPolling() {
    stopPolling()
    isGenerating.value = true
    generationProgress.value = 0
    generationStatus.value = '📋 创建生成任务...'
    generationLog.value = []
    error.value = null

    _addLog({ phase: 'init', text: '📋 开始生成下周计划...', progress: 0 })

    try {
      const { task_id } = await api.createNextWeekTask()
      _pollTaskId.value = task_id
      _addLog({ phase: 'init', text: `📋 任务已创建: ${task_id}`, progress: 2 })

      const status = await _pollUntilDone(task_id)

      if (status.week) {
        currentWeek.value = status.week
      }
      generationProgress.value = 100
      generationStatus.value = '✅ 下周计划已生成！'
      _addLog({ phase: 'done', text: '✅ 下周计划生成成功！', progress: 100 })
      await fetchMacrocycles()
      return status.week
    } catch (e: any) {
      error.value = e.message || '生成失败'
      _addLog({ phase: 'error', text: `❌ ${e.message}`, progress: generationProgress.value })
      throw e
    } finally {
      setTimeout(() => { isGenerating.value = false }, 500)
    }
  }

  async function generateNextWeek() {
    isGenerating.value = true
    generationProgress.value = 0
    generationStatus.value = '📋 分析前一周打卡数据...'
    generationLog.value = []
    error.value = null

    _addLog({ phase: 'init', text: '📋 开始生成下周计划...', progress: 0 })

    try {
      const result = await api.generateNextWeek({
        onProgress: (data) => {
          generationStatus.value = data.text
          generationPhase.value = data.phase
          const pct = getProgress(data)
          generationProgress.value = pct
          _addLog({ ...data, progress: pct })
        },
        onDayDone: (data) => {
          generationStatus.value = `✅ 第${data.day}天已生成`
          _addLog({ phase: 'day_done', text: `✅ 第${data.day}天 (${data.focus}) 写入完成 — ${data.main_count} 个主项`, day: data.day, progress: generationProgress.value })
        },
        onError: (data) => {
          error.value = data.text
          _addLog({ phase: 'error', text: `❌ ${data.text}`, progress: generationProgress.value })
        },
      })

      currentWeek.value = result
      generationProgress.value = 100
      generationStatus.value = '✅ 下周计划已生成！'
      _addLog({ phase: 'done', text: '✅ 下周计划生成成功！', progress: 100 })
      await fetchMacrocycles()
      return result
    } catch (e: any) {
      error.value = e.message || '生成失败'
      _addLog({ phase: 'error', text: `❌ ${e.message}`, progress: generationProgress.value })
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
    isGenerating, generationProgress, generationStatus, generationPhase, generationLog,
    loading, error,
    currentMesocycle, currentWeekNumber, mesocycleTotalWeeks,
    mesocyclePhaseLabel, weekCompletionRate, isWeekComplete,
    roadmapData, nextPhaseLabel,
    initPlan, initPlanPolling, stopPolling,
    generateNextWeek, generateNextWeekPolling, fetchCurrentWeek, fetchMacrocycles,
    fetchCalendarData, initCalendarRange,
  }
})
