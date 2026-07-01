# 前端适配计划 — 完整设计（数据层 + 宏观架构 + UI/UX）

> 版本：v2
> 日期：2026-06-30
> 状态：设计稿
> 对应后端引擎设计：`fitness-engine-design.md`

---

## 1. 概述

后端周期化引擎已就绪（`engine/` 四个引擎 + 新 ORM 模型 + 新 API 路由），
前端需要全面翻新以匹配新架构。

### 核心转变

```
旧模式（当前前端）                    → 新模式
──────────────────────────────────────────────────
FitnessPlan (JSON blob 概念)          → macrocycle → mesocycle → week → day → exercise_slot
一次性生成 4 周完整 JSON              → 每周独立生成（SSE 流式）
localStorage 打勾                      → 服务端持久化打卡（RPE + 实际组/次/重量）
2 个 Pinia store（plan + workout）    → 3 个领域 store
无周期概念                             → 三层周期展示 + 中周期切换
无日期选择                             → 用户自选训练日 + 可改日期
```

### 三层设计

| 层 | 内容 | 状态 |
|----|------|------|
| **数据层** | 类型系统 / SSE 解析器 / API 服务 / Pinia Store | ✅ 已定型 |
| **宏观架构** | 页面结构 / 路由 / 布局 / 数据流 / 日期调整 | ✅ 已定型 |
| **UI/UX 交互** | 各页面详细设计 / RPE 交互 / 打卡流程 | ✅ 已定型 |

---

# 第一部分：数据层

## 2. 类型系统 — `types/index.ts`（全部翻新）

### 2.1 核心类型

```typescript
// ═════════════════════════════════════════════════════════
//  动作库 — Exercise（来自 wger 缓存）
// ═════════════════════════════════════════════════════════

export interface ExerciseInfo {
  id: number | null
  name: string
  target_muscle: string
  muscle_group: string
  equipment: string
  image_url: string
  description: string
}

// ═════════════════════════════════════════════════════════
//  动作安排 + 打卡 — ExerciseSlot（计划+打卡二合一）
// ═════════════════════════════════════════════════════════

export type PhaseType = 'warmup' | 'main' | 'cardio' | 'stretch'

export type RPEQuick = 'easy' | 'normal' | 'hard'

export interface ExerciseSlot {
  id: number
  day_id: number
  phase_type: PhaseType
  sort_order: number
  wger_id: number | null
  exercise_name: string

  // ── 计划参数（生成时写入）──
  target_sets: number
  target_reps: number
  target_reps_max: number
  weight_kg: number
  weight_suggestion: string
  rest_seconds: number

  // ── 实际完成数据（打卡时更新）──
  actual_sets: number
  actual_reps: number
  rpe: number
  notes: string
  actual_weight_kg: number

  // ── 动作详情（来自本地 exercise 表或 wger）──
  exercise: ExerciseInfo | null

  // ── 前端 UI 状态（不来自后端）──
  _completed: boolean
  _rpeQuick: RPEQuick | null    // 快速按钮选择：easy/normal/hard
  _loading: boolean
}

// ═════════════════════════════════════════════════════════
//  训练日 — Day
// ═════════════════════════════════════════════════════════

export interface WorkoutDay {
  id: number
  day_order: number
  day_of_week: number           // 1=周一 … 7=周日（新增）
  day_label: string
  focus: string
  estimated_calories: number
  is_completed: boolean
  completed_date: string
  rpe_score: number
  slots: ExerciseSlot[]
}

/** 按 phase_type 分组的辅助类型（前端 UI 用） */
export interface WorkoutDayGrouped extends WorkoutDay {
  warmup: ExerciseSlot[]
  main: ExerciseSlot[]
  cardio: ExerciseSlot | null
  stretch: ExerciseSlot[]
}

// ═════════════════════════════════════════════════════════
//  小周期 — Week
// ═════════════════════════════════════════════════════════

export type WeekStatus = 'pending' | 'active' | 'completed' | 'skipped'

export interface WeekPlan {
  id: number
  week_number: number
  status: WeekStatus
  generated_at: string
  mesocycle_phase: string
  days: WorkoutDay[]
}

// ═════════════════════════════════════════════════════════
//  中周期 — Mesocycle
// ═════════════════════════════════════════════════════════

export type Phase = 'foundational' | 'hypertrophy' | 'strength' | 'deload'

export interface MesocycleSummary {
  id: number
  macrocycle_id: number
  phase: Phase
  week_count: number
  sort_order: number
  status: string
}

export interface MesocycleDetail extends MesocycleSummary {
  weeks: WeekSummary[]
}

export interface WeekSummary {
  id: number
  week_number: number
  status: WeekStatus
  day_count: number
}

// ═════════════════════════════════════════════════════════
//  大周期 — Macrocycle
// ═════════════════════════════════════════════════════════

export interface MacrocycleSummary {
  id: number
  goal: string
  start_date: string
  status: string
  created_at: string
}

export interface MacrocycleDetail extends MacrocycleSummary {
  mesocycles: MesocycleDetail[]
}

// ═════════════════════════════════════════════════════════
//  用户配置 — UserCurrentState
// ═════════════════════════════════════════════════════════

export interface UserCurrentState {
  id?: number
  experience_level: string
  workout_location: string
  days_per_week: number
  preferred_days: string           // "1,3,5"（新增：用户偏好的训练日）
  current_mesocycle_id: number | null
}

export interface UserCurrentStateUpdate {
  experience_level?: string
  workout_location?: string
  days_per_week?: number
  preferred_days?: string
}

// ═════════════════════════════════════════════════════════
//  API 请求类型
// ═════════════════════════════════════════════════════════

export interface InitPlanRequest {
  goal: string
  experience_level: string
  workout_location: string
  days_per_week: number
  preferred_days: string           // "1,3,5"（新增）
  city?: string
}

export interface SlotCheckinData {
  slot_id: number
  actual_sets: number
  actual_reps: number
  actual_weight_kg?: number
  rpe: number
  notes: string
}

export interface DayCheckinRequest {
  day_id: number
  is_completed: boolean
  rpe_score: number
  exercises: SlotCheckinData[]
}

export interface RescheduleRequest {
  /** 新的 day_of_week 值，1=周一 … 7=周日 */
  day_of_week: number
}

// ═════════════════════════════════════════════════════════
//  SSE 事件类型
// ═════════════════════════════════════════════════════════

export interface SSEProgressData {
  phase: string
  text: string
  day?: number
}

export interface SSEDayDoneData {
  day: number
  focus: string
  main_count: number
}

export interface SSEErrorData {
  text: string
}

export interface SSEEventCallbacks {
  onProgress?: (data: SSEProgressData) => void
  onDayDone?: (data: SSEDayDoneData) => void
  onDone?: (data: WeekPlan) => void
  onError?: (data: SSEErrorData) => void
}

// ═════════════════════════════════════════════════════════
//  RPE 映射表（前端用，帮助用户理解）
// ═════════════════════════════════════════════════════════

export const RPE_QUICK_MAP: Record<RPEQuick, { rpe: number; label: string; description: string; engineAction: string }> = {
  easy:   { rpe: 4, label: '😊 太轻松', description: '全部完成，感觉还能加', engineAction: '下周加重量' },
  normal: { rpe: 7, label: '✔ 正常完成', description: '有挑战但不吃力', engineAction: '下周加次数' },
  hard:   { rpe: 9, label: '😰 太重了', description: '很难完成，最后几个做不动', engineAction: '下周减量' },
}

export const RPE_QUICK_DEFAULT: RPEQuick = 'normal'
```

---

## 3. SSE 解析器 — `services/sse.ts`

### 3.1 为什么需要

后端 `POST /fitness/init-plan` 和 `POST /fitness/generate-next`
采用 **SSE（Server-Sent Events）** 流式返回进度事件。

- EventSource API 只支持 GET → ❌
- `fetch` + `ReadableStream` → ✅
- 封装为 `consumeSSE()`，对接 SSE 事件流

### 3.2 实现方案

```typescript
/**
 * 解析 SSE 流式响应
 *
 * 后端事件格式：
 *   event: progress
 *   data: {"phase":"search","text":"📡 正在搜索动作..."}
 *
 *   event: day_done
 *   data: {"day":1,"focus":"胸部","main_count":3}
 *
 *   event: done
 *   data: { ... 完整 WeekPlan 数据 ... }
 *
 *   event: error
 *   data: {"text":"生成失败: ..."}
 */
export async function consumeSSE(
  response: Response,
  callbacks: SSEEventCallbacks,
): Promise<WeekPlan> {
  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })

    // SSE 以 \n\n 分隔事件
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''

    for (const block of blocks) {
      const lines = block.split('\n')
      let eventType = ''
      let dataStr = ''

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          dataStr = line.slice(6)
        }
      }

      if (!dataStr) continue

      try {
        const data = JSON.parse(dataStr)

        switch (eventType) {
          case 'progress':
            callbacks.onProgress?.(data as SSEProgressData)
            break
          case 'day_done':
            callbacks.onDayDone?.(data as SSEDayDoneData)
            break
          case 'done':
            callbacks.onDone?.(data as WeekPlan)
            return data as WeekPlan
          case 'error':
            callbacks.onError?.(data as SSEErrorData)
            throw new Error(data.text || '生成失败')
        }
      } catch (e) {
        if (e instanceof SyntaxError) {
          console.warn('[SSE] JSON 解析失败:', dataStr)
        } else {
          throw e
        }
      }
    }
  }

  throw new Error('SSE 流提前结束，未收到 done 事件')
}

/**
 * 根据后端 phase 估算进度百分比
 *
 * phase 序列：
 *   init → coordinator → search → llm_parallel → select(per-day) → assemble(per-day) → save → done
 */
export function estimateProgress(phase: string): number {
  const phases: Record<string, number> = {
    'init': 5,
    'coordinator': 8,
    'search': 20,
    'llm_parallel': 30,
    'select': 45,
    'assemble': 55,
    'save': 75,
    'done': 100,
  }
  return phases[phase] ?? 55
}
```

---

## 4. API 服务层 — `services/api.ts`

### 4.1 全部新接口

```typescript
// ═══════════════════════════════════════════════════════════
//  新引擎 API
// ═══════════════════════════════════════════════════════════

// ── SSE 流式生成 ──────────────────────────────────────

export async function initPlan(
  req: InitPlanRequest,
  callbacks: SSEEventCallbacks,
): Promise<WeekPlan> {
  const res = await apiClient.post('/api/fitness/init-plan', req, {
    responseType: 'stream',
  })
  return consumeSSE(res, callbacks)
}

export async function generateNextWeek(
  callbacks: SSEEventCallbacks,
): Promise<WeekPlan> {
  const res = await apiClient.post('/api/fitness/generate-next', {}, {
    responseType: 'stream',
  })
  return consumeSSE(res, callbacks)
}

// ── REST 接口 ─────────────────────────────────────────

export async function fetchCurrentWeek(): Promise<WeekPlan> {
  const res = await apiClient.get<WeekPlan>('/api/fitness/current-week')
  return res.data
}

export async function listMacrocycles(): Promise<MacrocycleSummary[]> {
  const res = await apiClient.get<MacrocycleSummary[]>('/api/fitness/macrocycles')
  return res.data
}

export async function getMacrocycleDetail(id: number): Promise<MacrocycleDetail> {
  const res = await apiClient.get<MacrocycleDetail>(`/api/fitness/macrocycle/${id}`)
  return res.data
}

export async function checkin(data: DayCheckinRequest): Promise<void> {
  await apiClient.post('/api/fitness/checkin', data)
}

export async function fetchCurrentState(): Promise<UserCurrentState> {
  const res = await apiClient.get<UserCurrentState>('/api/fitness/current-state')
  return res.data
}

export async function updateCurrentState(data: UserCurrentStateUpdate): Promise<void> {
  await apiClient.put('/api/fitness/current-state', data)
}

/** 调整训练日到新的 day_of_week */
export async function rescheduleDay(dayId: number, data: RescheduleRequest): Promise<void> {
  await apiClient.put(`/api/fitness/day/${dayId}/reschedule`, data)
}
```

### 4.2 axios 流式响应配置

```typescript
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,           // 5 分钟（SSE 可能较久）
  headers: { 'Content-Type': 'application/json' },
  adapter: 'fetch',          // fetch adapter 支持 ReadableStream
})
```

> axios 默认的 XMLHttpRequest adapter 不支持 `responseType: 'stream'`，需用 `adapter: 'fetch'`。

---

## 5. Pinia Store 设计

### 5.1 Store 职责划分

```
┌─────────────────────────────────────────────────────────────┐
│                        userStore                             │
│  用户资料（profile）+ 当前状态（currentState）                │
│  → 含 preferred_days 管理                                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       cycleStore （新建）                     │
│  大周期 / 中周期 / 周计划 的完整生命周期                     │
│  - currentWeek, macrocycle                                   │
│  - SSE 生成状态 + 进度                                       │
│  - initPlan / generateNextWeek / fetchCurrentWeek            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     workoutStore （重构）                     │
│  当日训练交互 + 打卡状态                                     │
│  - 选中日期 → 从 currentWeek.days 匹配 day_of_week          │
│  - 动作打勾 / RPE 快捷按钮 / 日期调整                        │
│  - submitCheckin / rescheduleDay                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 cycleStore 详细设计

```typescript
// stores/cycle.ts
export const useCycleStore = defineStore('cycle', () => {
  const currentWeek = ref<WeekPlan | null>(null)
  const macrocycle = ref<MacrocycleDetail | null>(null)
  const macrocycles = ref<MacrocycleSummary[]>([])

  // SSE 生成状态
  const isGenerating = ref(false)
  const generationProgress = ref(0)
  const generationStatus = ref('')
  const generationPhase = ref('')

  const loading = ref(false)
  const error = ref<string | null>(null)

  // ── Computed ──
  const currentMesocycle = computed(() => {
    if (!currentWeek.value || !macrocycle.value) return null
    return macrocycle.value.mesocycles.find(
      m => m.phase === currentWeek.value!.mesocycle_phase
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

  /** 本周完成率（已打卡天数 / 总训练天数） */
  const weekCompletionRate = computed(() => {
    if (!currentWeek.value?.days.length) return 0
    const done = currentWeek.value.days.filter(d => d.is_completed).length
    return Math.round((done / currentWeek.value.days.length) * 100)
  })

  /** 本周是否全部完成（可触发生成下周） */
  const isWeekComplete = computed(() => weekCompletionRate.value >= 100)

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
      }
    } catch { /* 首次可能没有大周期 */ }
  }

  return {
    currentWeek, macrocycle, macrocycles,
    isGenerating, generationProgress, generationStatus, generationPhase,
    loading, error,
    currentMesocycle, currentWeekNumber, mesocycleTotalWeeks,
    mesocyclePhaseLabel, weekCompletionRate, isWeekComplete,
    initPlan, generateNextWeek, fetchCurrentWeek, fetchMacrocycles,
  }
})
```

### 5.3 workoutStore 重构设计

```typescript
// stores/workout.ts
export const useWorkoutStore = defineStore('workout', () => {
  const cycleStore = useCycleStore()

  const selectedDate = ref<string | null>(null)
  const checkinLoading = ref(false)
  const error = ref<string | null>(null)

  // ── Computed ──

  /** 当前选中日期的训练计划（按 phase_type 分组） */
  const currentDay = computed<WorkoutDayGrouped | null>(() => {
    if (!cycleStore.currentWeek || !selectedDate.value) return null
    const day = findDayByDate(cycleStore.currentWeek, selectedDate.value)
    if (!day) return null
    return groupSlotsByPhase(day)
  })

  const todayStr = computed(() => dayjs().format('YYYY-MM-DD'))

  /** 通过 day_of_week 匹配日期 */
  function findDayByDate(week: WeekPlan, targetDate: string): WorkoutDay | null {
    const targetDayjs = dayjs(targetDate)
    const targetDow = targetDayjs.day() || 7  // dayjs: 0=周日 → 转 7
    return week.days.find(d => d.day_of_week === targetDow) ?? null
  }

  function groupSlotsByPhase(day: WorkoutDay): WorkoutDayGrouped {
    return {
      ...day,
      warmup: day.slots.filter(s => s.phase_type === 'warmup'),
      main: day.slots.filter(s => s.phase_type === 'main'),
      cardio: day.slots.find(s => s.phase_type === 'cardio') ?? null,
      stretch: day.slots.filter(s => s.phase_type === 'stretch'),
    }
  }

  // ── 交互（乐观更新）──

  function toggleExercise(slotId: number) {
    const slot = currentDay.value?.slots.find(s => s.id === slotId)
    if (!slot) return
    slot._completed = !slot._completed
    // 打勾时默认 RPE = normal（7）
    if (slot._completed && !slot._rpeQuick) {
      slot._rpeQuick = RPE_QUICK_DEFAULT
      slot.rpe = RPE_QUICK_MAP.normal.rpe
    }
    if (!slot._completed) {
      slot._rpeQuick = null
      slot.rpe = 0
    }
  }

  function setRPEQuick(slotId: number, quick: RPEQuick) {
    const slot = currentDay.value?.slots.find(s => s.id === slotId)
    if (!slot) return
    slot._rpeQuick = quick
    slot.rpe = RPE_QUICK_MAP[quick].rpe
    slot._completed = true  // 选了反馈自动视为完成
  }

  /** 更新 day_of_week（用户调整训练日期） */
  async function rescheduleDay(dayId: number, newDayOfWeek: number) {
    await api.rescheduleDay(dayId, { day_of_week: newDayOfWeek })
    // 刷新周计划
    await cycleStore.fetchCurrentWeek()
  }

  // ── 提交打卡 ──

  async function submitCheckin() {
    if (!currentDay.value) return
    checkinLoading.value = true

    try {
      // 只提交有反馈的动作（打勾或点了 RPE 按钮）
      const exercises: SlotCheckinData[] = currentDay.value.slots
        .filter(s => s._completed || s._rpeQuick)
        .map(s => ({
          slot_id: s.id,
          actual_sets: s.actual_sets || s.target_sets,
          actual_reps: s.actual_reps || s.target_reps,
          rpe: s.rpe || 7,
          notes: '',
        }))

      // 计算当天整体 RPE（取所有动作的中位数）
      const rpeValues = exercises.filter(e => e.rpe > 0).map(e => e.rpe)
      const avgRpe = rpeValues.length
        ? Math.round(rpeValues.reduce((a, b) => a + b, 0) / rpeValues.length)
        : 0

      await api.checkin({
        day_id: currentDay.value.id,
        is_completed: true,
        rpe_score: avgRpe,
        exercises,
      })

      // 打卡后刷新
      await cycleStore.fetchCurrentWeek()
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      checkinLoading.value = false
    }
  }

  return {
    selectedDate, currentDay, todayStr,
    checkinLoading, error,
    toggleExercise, setRPEQuick, rescheduleDay, submitCheckin,
  }
})
```

### 5.4 userStore 改造

```typescript
// stores/user.ts — 新增 currentState + preferred_days
export const useUserStore = defineStore('user', () => {
  const profile = ref<UserProfileResponse | null>(null)
  const currentState = ref<UserCurrentState | null>(null)
  const loading = ref(false)

  async function fetchCurrentState() {
    try {
      currentState.value = await api.fetchCurrentState()
      return currentState.value
    } catch { /* 首次可能没有状态 */ }
  }

  async function saveCurrentState(data: UserCurrentStateUpdate) {
    await api.updateCurrentState(data)
    if (currentState.value) {
      Object.assign(currentState.value, data)
    }
  }

  // 保留原有 profile 相关方法（fetchProfile / saveProfile / markOnboardingDone ...）

  return {
    profile, currentState, loading,
    fetchCurrentState, saveCurrentState,
    // ...原有 profile 方法
  }
})
```

---

# 第二部分：宏观架构

## 6. 页面结构与路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | `OnboardingGuide` | 三步引导 → 选训练日 → init-plan |
| `/generating` | `GeneratingPlan` | SSE 流式进度展示 → 完成自动跳转 |
| `/home` | `MainPage` | 主力页面：周期信息 + 日历 + 训练面板 |
| `/profile` | `ProfilePage` | 个人资料 + 当前训练状态编辑 |

```
用户流程：

首次使用:
  / (OnboardingGuide) → /generating (SSE) → /home

日常使用:
  /home → 日历看计划 → 点日期 → 打勾/RPE → 提交打卡
       → 本周打完 → 点[生成下周] → /generating (SSE) → /home

修改设置:
  /home → /profile → 改经验/地点/天数 → 影响下周生成
```

## 7. 主页布局

```
┌─ MainPage ───────────────────────────────────────────┐
│                                                        │
│ ┌─ 左列(380px) ─────────────┐ ┌─ 右列 ──────────────┐│
│ │                           │ │                      ││
│ │  📅 日历                  │ │  DailyPlanPanel      ││
│ │  [月 导航 < 6月 > 今天]    │ │  (选中日的训练计划)   ││
│ │  [日] [一] [二] [三] [四] [五] [六] │              ││
│ │  ┌──┐    ┌──┐    ┌──┐   │ │  🔥 热身              ││
│ │  │推│    │拉│    │腿│   │ │  ☑ 开合跳    30s      ││
│ │  └──┘    └──┘    └──┘   │ │  ☑ 高抬腿    30s      ││
│ │                           │ │                      ││
│ ├─ 周期信息 ──────────────┤ │  💪 主训练            ││
│ │ 🎯 基础适应期 · 第3/4周  │ │  ☑ 深蹲 3×12·10kg    ││
│ │ ████████░░ 82% 完成率    │ │    😊 ✔ 😰           ││
│ │ ✅ 本周打卡: 一推 三拉    │ │  ☐ 弓步蹲 3×12·自重  ││
│ │                           │ │    😊 ✔ 😰           ││
│ │ [⚡ 生成下周] ← 打完才亮   │ │                      ││
│ └───────────────────────────┘ │  🧘 拉伸              ││
│                               │  ☑ 大腿前侧拉伸  30s  ││
│                               │                      ││
│                               │  [📝 提交打卡]        ││
│                               └──────────────────────┘│
└────────────────────────────────────────────────────────┘
```

## 8. 日期选择与调整

### 8.1 引导页选训练日（Step 3）

```
┌─ StepCardSchedule ──────────────────────────┐
│                                              │
│  🏋️ 你打算哪几天训练？                      │
│                                              │
│  [一] [二] [三] [四] [五] [六] [日]         │
│   ✓    □    ✓    □    ✓    □    □           │
│                                              │
│  每周 3 天                                   │
│                                              │
│  训练地点: [居家 ▼]                          │
│  经验等级: [新手 ▼]                          │
│                                              │
│           [✨ 生成计划]                      │
└──────────────────────────────────────────────┘
```

选择结果 → `preferred_days: "1,3,5"` → 传给 `init-plan` 请求。
后端据此设置 `day.day_of_week`。

### 8.2 主页调整日期（改 day_of_week）

```
用户点击训练日卡片（如「拉」）：
   ↓
弹出可选日期列表（只显示本周未占用的日期）：
  [一] [二] [三] [四] [五] [六] [日]
  占用  空闲  占用  👈   空闲  空闲  空闲
                  ↑ 用户点周四
   ↓
调 API: PUT /api/fitness/day/{id}/reschedule
  body: { "day_of_week": 4 }
   ↓
日历刷新，「拉」移到周四
```

### 8.3 数据流（日期相关）

```
引导页选 [一][三][五]
       ↓ preferred_days: "1,3,5"
init-plan → 后端生成 Day 时设 day_of_week=1,3,5
       ↓
前端 GET /api/fitness/current-week
  day[0]: day_order=1, day_of_week=1, focus="推"
  day[1]: day_order=2, day_of_week=3, focus="拉"
  day[2]: day_order=3, day_of_week=5, focus="腿"
       ↓
日历渲染: 周一=推, 周三=拉, 周五=腿
       ↓ 用户点"拉"→选"周四"
PUT /api/fitness/day/{id}/reschedule?day_of_week=4
       ↓ 后端更新 day_of_week → 下次 generate-next 保持新的分布
```

## 9. 数据流全景（完整版）

```
GeneratingPlan.vue
  │
  │  initPlan({
  │    goal, experience_level, workout_location,
  │    days_per_week: 3, preferred_days: "1,3,5"
  │  }, {
  │    onProgress: (data) → 实时进度条+文字
  │    onDayDone: (data) → "第N天已生成"
  │    onDone: (data) → cycleStore.currentWeek = data
  │  })
  │
  ▼
cycleStore.currentWeek
  │
  ├── MainPage.vue
  │    ├── 周期信息栏 ← cycleStore.mesocyclePhaseLabel
  │    │                + weekCompletionRate + isWeekComplete
  │    ├── 日历 ← currentWeek.days[].day_of_week + focus
  │    │    点击训练日 → 调 workoutStore.rescheduleDay(dayId, newDow)
  │    │    点击过去日期 → 显示打卡数据（actual_*）
  │    │    点击未来日期 → 预览
  │    └── DailyPlanPanel ← workoutStore.currentDay (grouped)
  │          ├── 打勾 → toggleExercise(slotId)
  │          ├── RPE 快捷按钮 → setRPEQuick(slotId, 'easy'|'hard')
  │          └── 提交 → submitCheckin() → POST /api/fitness/checkin
  │
  ├── [生成下周] 按钮 ← cycleStore.isWeekComplete
  │      点击 → cycleStore.generateNextWeek() → SSE → 刷新
  │
  └── ProfilePage
       └── 编辑当前状态 → userStore.saveCurrentState()
```

## 10. 需要后端配合的改动

| 改动 | 说明 | 优先级 |
|------|------|--------|
| `Day` 表加 `day_of_week` INTEGER | 1=周一…7=周日 | ✅ 必须 |
| `UserCurrentState` 加 `preferred_days` TEXT | 如 "1,3,5" | ✅ 必须 |
| `InitPlanRequest` 加 `preferred_days` | 引导页传到后端 | ✅ 必须 |
| 新增 `PUT /fitness/day/{id}/reschedule` | 改 day_of_week | ✅ 必须 |
| init-plan 按 preferred_days 设 day_of_week | 生成时用 | ✅ 必须 |
| generate-next 沿用上一周的 day_of_week 分布 | 保持用户调整 | ✅ 必须 |

---

# 第三部分：UI/UX 交互设计

## 11. 各页面详细设计

### 11.1 OnboardingGuide（三步引导）

**第一步 — 个人资料（StepCardPersonal）**
```
身高: [___] cm
体重: [___] kg
年龄: [___]
性别: [男] [女]
经验: [新手 ▼]

            [下一步 →]
```

**第二步 — 健身目标（StepCardGoal）**
```
🎯 你的目标是什么？

[🔥 减脂]  [💪 增肌]  [🧘 塑形]  [❤️ 保持健康]

         [← 上一步] [下一步 →]
```

**第三步 — 训练安排（StepCardSchedule）** ← 主要改动
```
🏋️ 你打算哪几天训练？

[一] [二] [三] [四] [五] [六] [日]
 ✓    □    ✓    □    ✓    □    □
        每周 3 天

训练地点: [居家 ▼]
经验等级: [新手 ▼]

      [← 上一步] [✨ 生成计划]
```

### 11.2 GeneratingPlan（SSE 生成进度）

```
┌─ GeneratingPlan ──────────────────────┐
│                                        │
│        💪 AI 正在为你生成计划          │
│                                        │
│   ████████████░░░░░░  65%              │
│                                        │
│   📡 正在从 wger 搜索动作...           │
│   🤖 LLM 正在精选第 2 天动作...        │
│   💾 正在写入第 1 天数据库...          │
│                                        │
│   ✅ 第 1 天生成完成                   │
│   🕐 第 2 天生成中...                  │
│                                        │
│           生成中请稍候...               │
└────────────────────────────────────────┘
```

- 完成后自动跳转到 `/home`
- 失败时显示错误 + [重试] 按钮

### 11.3 MainPage（主力页面）

**周期信息栏（左下角）：**

```
┌─ 周期信息 ───────────────────────┐
│  🎯 基础适应期                    │
│  第 3 周 / 共 4 周               │
│  ████████░░ 82% 完成率           │
│                                   │
│  本周打卡:                        │
│  周一 ✅ 推  周三 ☐ 拉  周五 ☐ 腿 │
│                                   │
│  [⚡ 生成下周]  ← 全部打完才可点   │
└───────────────────────────────────┘
```

- 阶段名映射：foundational→基础适应期, hypertrophy→肌肥大期, strength→力量期, deload→减载周
- 进度条：已完成天数 / 总训练天数
- 打卡状态：每个训练日显示 ✅/☐
- [生成下周] 按钮：所有训练日打完才亮起，hover 时如果没打完显示"还有 N 天未打卡"
- 减载周时显示"🔄 减载周 · 恢复为主"

**日历（左上角）：**

```
        2026年7月
  日   一   二   三   四   五   六
                1    2    3    4
        ┌──┐             ┌──┐
  5   6 │推│  7   8   9  │拉│  11
        └──┘             └──┘
  12  13   14   15   16  17   18
  19  20   21   22   23  24   25
  26  27   28   29   30  31

  ─────────────────────────────
  今日训练:  推（周一）
  ──── 已训练 ────
  上周一  推  ✅ 完成
```

- 训练日格子显示 focus 标签（"推"/"拉"/"腿"），不同颜色区分
- 已完成日期右下角显示 ✅
- 点击训练日 → 弹出可选日期列表供调整
- 点击过去已打卡日期 → 右侧显示当时的打卡数据
- 点击未来日期 → 预览

**DailyPlanPanel（右列）：**

```
┌─ DailyPlanPanel ──────────────────┐
│  7月1日 周三 · 拉                │
│  ─────────────────────────────── │
│  🔥 热身                         │
│  ☑ 肩部环绕           30s       │
│  ☑ 手臂摆动           30s       │
│                                   │
│  💪 主训练                        │
│  ☑ 俯卧撑 3×10·自重              │
│    😊  ✔  😰                     │
│  ☐ 弹力带划船 3×12·弹力带        │
│    😊  ✔  😰                     │
│  ☐ 平板支撑 3×30s·自重           │
│    😊  ✔  😰                     │
│                                   │
│  🧘 拉伸                         │
│  ☑ 胸部拉伸           30s       │
│                                   │
│  [📝 提交打卡]                    │
└───────────────────────────────────┘
```

### 11.4 ProfilePage（个人设置）

```
┌─ ProfilePage ─────────────────────────┐
│                                        │
│  👤 个人资料                           │
│  身高: [175] cm                        │
│  体重: [70] kg                         │
│  年龄: [28]                            │
│  性别: [♂ 男]                          │
│                                        │
│  ── 当前训练状态 ──                   │
│  💡 修改后将在下周生成时生效            │
│                                        │
│  经验等级: [新手 ▼]                    │
│  训练地点: [居家 ▼]                    │
│                                        │
│  训练日:                               │
│  [一] [二] [三] [四] [五] [六] [日]   │
│   ✓    □    ✓    □    ✓    □    □     │
│                                        │
│          [💾 保存设置]                  │
└────────────────────────────────────────┘
```

## 12. RPE 交互设计

### 12.1 三种快捷按钮（主项动作旁）

```
☐ 深蹲  3×12·10kg

  😊        ✔         😰
 太轻松   正常完成    太重了
 ─────────────────────────────
 RPE=4    RPE=7      RPE=9
 下周加重量 下周加次数  下周减量
```

- 默认无选择
- 用户打勾（点 ☐）→ 自动设为 ✔（RPE=7）
- 用户点 😊 → RPE=4，动作自动变为已勾选
- 用户点 😰 → RPE=9，动作自动变为已勾选
- 三个按钮互斥
- 点动作名称 → 弹出 Drawer 精细调整（填实际组/次/重量/RPE）

### 12.2 RPE 帮助提示

页面放置一个 ℹ️ 图标，hover 或点击显示：

```
RPE（主观疲劳度）帮助你了解训练强度，AI 根据你的反馈调整下周计划：

😊 太轻松 (RPE 1-4)
  全部完成，感觉还能加 → 下周加重量

✔ 正常完成 (RPE 5-7)  
  有挑战但不吃力 → 下周加次数

😰 太重了 (RPE 8-10)
  很难完成，最后几个做不动 → 下周减量

不操作 → 默认正常完成，引擎自动保持进度
```

### 12.3 提交打卡逻辑

```
用户点 [提交打卡]
     ↓
只发送有反馈的动作（打勾或点了 RPE 按钮）
     ↓
未操作的动作 → 引擎按"未打卡"处理，保持参数不变
     ↓
打卡成功后刷新 currentWeek（获取最新的 actual_* 数据）
```

---

## 13. 交互状态对照表

| 动作 | 用户操作 | UI 反馈 | 发给后端 | 引擎理解 |
|------|---------|---------|---------|---------|
| 正常完成 | 点 ☐ | ☑ 显示 | RPE=7 | 加次数 |
| 太轻松 | 点 😊 | ☑ + 😊 高亮 | RPE=4 | 加重量 |
| 太重了 | 点 😰 | ☑ + 😰 高亮 | RPE=9 | 减量 |
| 精细调整 | 点动作名 | 弹 Drawer | 手动值 | 按手动值 |
| 不操作 | 不点 | 保持 ☐ | 不发送 | 保持参数 |
| 提交打卡 | 点按钮 | 成功提示 | 汇总数据 | 更新实际值 |

---

## 14. 文件结构（完整版）

```
frontend/src/
  types/
    index.ts              ← 全部翻新（含 RPE 映射表）
  services/
    api.ts                ← 新增 9 个新接口，删除旧接口
    sse.ts                ← 新增 SSE 解析器
  stores/
    cycle.ts              ← 新增：周期管理
    workout.ts            ← 重构：训练交互 + 打卡 + 日期调整
    user.ts               ← 改造：新增 currentState + preferred_days
    plan.ts               ← 删除（功能合并到 cycle.ts）
  components/
    CalendarPanel.vue     ← 重构：按 day_of_week 渲染，支持点击调日期
    DayCell.vue           ← 重构：显示 focus 标签 + 完成状态
    DailyPlanPanel.vue    ← 重构：RPE 快捷按钮 + 提交打卡
    TodayCard.vue         ← 重构：调整为周期信息卡片
    ExerciseRow.vue       ← 重构：新增 RPE 三个快捷按钮
    ExerciseDrawer.vue    ← 重构：支持精细调整（组/次/重量/RPE）
    CycleInfo.vue         ← 新增：周期信息栏组件
    NavBar.vue            ← 保持
    AIChatPanel.vue       ← 保持
    StepCardPersonal.vue  ← 保持
    StepCardGoal.vue      ← 保持
    StepCardSchedule.vue  ← 重构：新增日期多选
  views/
    OnboardingGuide.vue   ← 改造：传 preferred_days
    GeneratingPlan.vue    ← 重构：SSE 流式进度
    MainPage.vue          ← 重构：新布局（日历左上+周期左下+右侧面板）
    ProfilePage.vue       ← 改造：新增当前状态编辑
```

---

## 15. 设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| SSE 方案 | `fetch` + `ReadableStream` | 后端用 POST，原生 EventSource 不支持 |
| Store 拆分 | 3 个领域 store | cycle / workout / user 各司其职 |
| 训练日映射 | 后端 `day_of_week` 字段 | 持久化用户调整，跨设备同步 |
| 日期调整方式 | 点击训练日 → 选新日期 | 比拖拽好实现，用户操作成本接近 |
| RPE 录入方式 | 三按钮快捷选择（😊✔😰） | 90% 场景只需打勾，特殊场景点按钮 |
| 默认 RPE | 打勾 = RPE 7（normal） | 用户不额外操作也能让引擎正常调整 |
| 打卡提交 | 只发有反馈的动作 | 未操作动作保持引擎默认 |
| axios adapter | `adapter: 'fetch'` | XMLHttpRequest 不支持流式响应 |
| 旧类型处理 | 全部删除 | 数据结构完全不兼容 |
| 独立打卡页面 | 不要，合入主页 | 减少路由切换，操作更流畅 |

---

## 16. 未完成事项（后续迭代）

- 周期切换时的过渡动画
- 中周期切换前的"下一阶段预告"提示
- 训练历史统计图表（ECharts）
- 离线模式支持
- 错误重试与网络恢复
