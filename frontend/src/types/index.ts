// ── 健身计划类型定义（引擎 v2）─────────────────────────
//  对应后端引擎设计：fitness-engine-design.md
//  完整设计文档：0-docs/10-frontend-plan.md

// ═════════════════════════════════════════════════════════
//  动作库 — Exercise（来自 wger 缓存）
// ═════════════════════════════════════════════════════════

export interface ExerciseInfo {
  id: number | null
  name: string
  target_muscle: string
  muscle_group: string
  movement_pattern: string
  equipment: string
  image_url: string
  description: string
  difficulty: number
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
  _rpeQuick: RPEQuick | null
  _loading: boolean
}

// ═════════════════════════════════════════════════════════
//  训练日 — Day
// ═════════════════════════════════════════════════════════

export interface WorkoutDay {
  id: number
  day_order: number
  day_of_week: number          // 1=周一 … 7=周日
  date: string                 // YYYY-MM-DD
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
  start_date: string            // YYYY-MM-DD
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
  preferred_days: string           // "1,3,5"
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
  preferred_days: string
  start_date?: string       // YYYY-MM-DD
  city?: string
  height?: number      // cm
  weight?: number      // kg
  age?: number         // 岁
  gender?: string      // male / female
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
//  日历相关（新增）
// ═════════════════════════════════════════════════════════

export interface CalendarEntry {
  date: string                   // YYYY-MM-DD
  has_plan: boolean
  day_status: string             // pending / completed / future / no_plan
  focus: string
  mesocycle_phase: string
}

export interface CalendarEntryResponse {
  entries: CalendarEntry[]
}

export interface DayDetailResponse {
  date: string
  day_status: string             // pending / completed / future / no_plan
  day_label: string
  focus: string
  week_id: number
  mesocycle_phase: string
  is_rest_day: boolean
  has_plan: boolean
  slots: ExerciseSlot[]
  warmup: any[]
  main: any[]
  cardio: any | null
  stretch: any[]
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
//  RPE 映射表（前端用，帮助用户理解引擎行为）
// ═════════════════════════════════════════════════════════

export const RPE_QUICK_MAP: Record<RPEQuick, { rpe: number; label: string; description: string; engineAction: string }> = {
  easy: { rpe: 4, label: '😊 太轻松', description: '全部完成，感觉还能加', engineAction: '下周加重量' },
  normal: { rpe: 7, label: '✔ 正常完成', description: '有挑战但不吃力', engineAction: '下周加次数' },
  hard: { rpe: 9, label: '😰 太重了', description: '很难完成，最后几个做不动', engineAction: '下周减量' },
}

export const RPE_QUICK_DEFAULT: RPEQuick = 'normal'

// ═════════════════════════════════════════════════════════
//  @deprecated 旧类型 — 视图重构完成后删除
// ═════════════════════════════════════════════════════════

/** @deprecated 使用 WorkoutDay / ExerciseSlot 替代 */
export interface UserProfile {
  height?: number
  weight?: number
  age?: number
  gender?: string
  goal?: string
  experience?: string
  experience_level?: string
  city?: string
  workout_location?: string
  days_per_week?: number
}

/** @deprecated */
export interface UserProfileResponse extends UserProfile {
  id: number
}

/** @deprecated 使用 InitPlanRequest 替代 */
export interface PlanRequest {
  goal: string
  experience_level: string
  workout_location: string
  days_per_week: number
  duration_weeks: number
  city?: string
  notes?: string
}

/** @deprecated 使用 ExerciseSlot 替代 */
export interface ExerciseItem {
  name: string
  target_muscle?: string
  category?: string
  sets: number
  reps: number
  rest_seconds?: number
  weight_suggestion?: string
  description?: string
  image_url?: string
  /** @deprecated 前端示例数据用 */
  instruction?: string
  /** @deprecated 前端示例数据用 */
  duration?: number
}

/** @deprecated 使用 WorkoutDay 替代 */
export interface DailyWorkout {
  day: string
  focus: string
  warmup: ExerciseItem[]
  main: ExerciseItem[]
  cardio?: ExerciseItem | null
  stretch?: ExerciseItem[]
  cooldown?: ExerciseItem[]
  estimated_calories?: number
}

/** @deprecated 使用 WeekPlan 替代 */
export interface WeeklyPlan {
  week: number
  days: DailyWorkout[]
}

/** @deprecated 不再使用 */
export interface FitnessPlan {
  id: number
  goal: string
  experience_level: string
  workout_location: string
  days_per_week: number
  duration_weeks: number
  weekly_plans: WeeklyPlan[]
  created_at: string
}

/** @deprecated */
export interface FitnessPlanSummary {
  id: number
  goal: string
  duration_weeks: number
  days_per_week: number
  created_at: string
}

/** @deprecated 使用 SlotCheckinData 替代 */
export interface RecordRequest {
  plan_id?: number
  date: string
  exercise_name: string
  target_muscle?: string
  planned_sets?: number
  planned_reps?: number
  actual_sets: number
  actual_reps: number
  weight?: number
  difficulty: number
  notes?: string
}

/** @deprecated */
export interface RecordResponse extends RecordRequest {
  id: number
}

/** @deprecated 使用 ExerciseSlot 替代 */
export interface ExerciseState {
  name: string
  targetMuscle?: string
  category?: string
  sets: number
  reps: number
  weight?: string
  duration?: number
  completed: boolean
  tooHeavy: boolean
  order: number
  imageUrl?: string
  description?: string
  wgerId?: number
}

/** @deprecated */
export interface WorkoutSection {
  type: 'warmup' | 'main' | 'cardio' | 'stretch'
  label: string
  exercises: ExerciseState[]
}

/** @deprecated 使用 WorkoutDayGrouped 替代 */
export interface DayPlan {
  date: string
  dayOfWeek: number
  focusArea: string
  isRestDay: boolean
  sections: WorkoutSection[]
}

/** @deprecated */
export type DayStatus = 'rest' | 'pending' | 'partial' | 'completed' | 'missed' | 'future'

/** @deprecated */
export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
}
