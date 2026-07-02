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
  completion_rate?: number
}

export interface WeekSummary {
  id: number
  week_number: number
  status: WeekStatus
  day_count: number
  completed_days?: number
  completion_rate?: number
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
//  路线图展示类型（中周期路线图用）
// ═════════════════════════════════════════════════════════

/** 各目标对应的阶段中文名 */
export const PHASE_LABEL_MAP: Record<string, Record<string, string>> = {
  '增肌': {
    foundational: '基础适应期',
    hypertrophy: '肌肥大期',
    strength: '力量提升期',
    deload: '减载恢复周',
  },
  '减脂': {
    foundational: '基础适应期',
    hypertrophy: '燃脂强化期',
    strength: '代谢提升期',
    deload: '减载恢复周',
  },
  '塑形': {
    foundational: '基础适应期',
    hypertrophy: '塑形雕刻期',
    strength: '紧致提升期',
    deload: '减载恢复周',
  },
  '保持健康': {
    foundational: '基础适应期',
    hypertrophy: '综合维持期',
    strength: '活跃恢复期',
    deload: '减载恢复周',
  },
}

/** 阶段对应颜色 */
export const PHASE_COLORS: Record<string, string> = {
  foundational: '#3b82f6',
  hypertrophy: '#22c55e',
  strength: '#f97316',
  deload: '#a855f7',
}

/** 各目标各阶段的大白话说明（做什么 + 达到什么目标） */
export const PHASE_DESCRIPTIONS: Record<string, Record<string, { title: string; description: string }>> = {
  '增肌': {
    foundational: { title: '🤔 这个阶段练什么？', description: '用比较轻的重量先把动作学标准，重点练深蹲、卧推这些基础动作。这个阶段不用着急上大重量，先把姿势练对，以后的训练才能不受伤、效果更好。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '用中等重量每组做 8-12 下，做到最后几下感觉吃力就对了。这样能给肌肉足够的刺激，让它变大变厚。每次要尝试比上周多做一下或者多加一点点重量，才能持续进步。' },
    strength: { title: '🤔 这个阶段练什么？', description: '加重重量减少次数，每组做 4-6 下。目标是让神经更高效地调动肌肉，举起更重的重量。这阶段练出来的不只是肌肉，更是实打实的力量增长。' },
    deload: { title: '🤔 这个阶段练什么？', description: '重量减轻一半，运动量也减少，让身体彻底恢复。连续练了几个月，身体和神经都很疲劳。这一周就是让身体「充充电」，休息好了下一轮才能练得更好。' },
  },
  '减脂': {
    foundational: { title: '🤔 这个阶段练什么？', description: '用比较轻的重量先把动作学标准，重点练深蹲、卧推这些基础动作。这个阶段即使吃得少一点，身体也能同时长肌肉和减脂肪。先把姿势练对，后面才能全力燃脂。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '用中等偏重的重量每组做 8-12 下，配合有氧运动。这样可以一边消耗热量一边给肌肉足够的刺激，不会因为少吃而掉肌肉。这个阶段最关键的是多吃蛋白质（肉蛋奶），才能保住练出来的肌肉。' },
    strength: { title: '🤔 这个阶段练什么？', description: '一周里有几天练重一点、有几天练轻一点，配合高强度间歇运动来突破瓶颈。如果减脂速度变慢了，这就说明身体适应了，需要通过变化来重新激活代谢。太累的时候可以安排一两天正常吃饭补充能量。' },
    deload: { title: '🤔 这个阶段练什么？', description: '运动量减半，重量也减轻，让身体彻底放松恢复。连续减脂好几个月，身体和神经都很疲劳。这一周就是让身体「充充电」，休息好了下一轮减脂效果才会更好。' },
  },
  '塑形': {
    foundational: { title: '🤔 这个阶段练什么？', description: '用比较轻的重量先把动作学标准，把全身各部位都练一遍。这个阶段重点是找到肌肉发力的感觉，为后续的雕刻塑形打好基础。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '中等重量每组做 10-15 下，重点打磨肩部、背部、臀腿这些部位。目标是让肌肉线条更好看，体态更挺拔。注意动作质量比重量更重要。' },
    strength: { title: '🤔 这个阶段练什么？', description: '增加训练强度，复合动作和孤立动作搭配练。这个阶段要练出全身的紧致感，让肌肉轮廓更明显，皮肤看起来更紧实有弹性。' },
    deload: { title: '🤔 这个阶段练什么？', description: '运动量减半，重点是拉伸和放松。让肌肉和关节好好恢复，下一轮练起来效果更好。' },
  },
  '保持健康': {
    foundational: { title: '🤔 这个阶段练什么？', description: '从最简单的运动开始，主要以适应为主。不用追求强度，重点是让身体养成规律运动的习惯。每周练 2-3 次比一次练很猛更重要。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '保持中等强度的训练，全身各部位都练到。这个阶段不求突破，主要是维持现有的力量和体能水平，让运动成为生活的一部分。' },
    strength: { title: '🤔 这个阶段练什么？', description: '以轻松愉快的运动为主，增加一些户外活动和有氧运动。保持身体活跃度，享受运动带来的好心情，不给自己太大压力。' },
    deload: { title: '🤔 这个阶段练什么？', description: '减少运动量，做一些简单的拉伸和散步。让身体休息一下，为下一轮训练做准备。' },
  },
}

/** 路线图上单个阶段的显示数据 */
export interface PhaseSegment {
  phase: string
  label: string
  color: string
  status: 'completed' | 'active' | 'pending'
  weekCount: number
  currentWeek?: number
  completionRate: number
  weeks: WeekSummary[]
}

/** 路线图全部数据 */
export interface RoadmapData {
  macrocycleId: number
  goal: string
  totalWeeks: number
  currentWeekNumber: number
  mesocycles: PhaseSegment[]
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
  day_id: number                 // training_day id（has_plan = true 时有值）
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
