// ── 健身计划类型定义 ──────────────────────────────────────────

// 用户资料
export interface UserProfile {
  height?: number       // cm
  weight?: number       // kg
  age?: number
  gender?: string       // male / female
  goal?: string         // 减脂/增肌/塑形/保持健康
  experience?: string   // 新手/中级/高级
}

export interface UserProfileResponse extends UserProfile {
  id: number
}

// 计划生成请求
export interface PlanRequest {
  goal: string
  experience_level: string
  workout_location: string
  days_per_week: number
  duration_weeks: number
  diet_preference: string
  city?: string
  notes?: string
}

// 训练动作（后端返回格式）
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
}

// 每日训练（后端返回格式）
export interface DailyWorkout {
  day: string
  focus: string
  warmup: ExerciseItem[]
  main: ExerciseItem[]
  cooldown: ExerciseItem[]
  estimated_calories?: number
}

// 每周计划（后端返回格式）
export interface WeeklyPlan {
  week: number
  days: DailyWorkout[]
}

// 饮食建议
export interface DietAdvice {
  daily_calories?: number
  protein_ratio?: string
  carb_ratio?: string
  fat_ratio?: string
  meals?: Record<string, string>
  tips: string[]
}

// 完整计划（后端返回）
export interface FitnessPlan {
  id: number
  goal: string
  experience_level: string
  workout_location: string
  days_per_week: number
  duration_weeks: number
  diet_preference: string
  weekly_plans: WeeklyPlan[]
  diet?: DietAdvice
  created_at: string
}

export interface FitnessPlanSummary {
  id: number
  goal: string
  duration_weeks: number
  days_per_week: number
  created_at: string
}

// 训练记录请求（保留，API 仍用）
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

export interface RecordResponse extends RecordRequest {
  id: number
}

// ── 新增：前端日历 & 打勾清单类型 ─────────────────────────

// 训练动作状态（前端用，含完成状态）
export interface ExerciseState {
  name: string
  targetMuscle?: string
  category?: string
  sets: number
  reps: number
  weight?: string
  duration?: number      // 热身/拉伸用秒
  completed: boolean     // ✅ 打勾
  tooHeavy: boolean      // 😰 太重了
  order: number
  imageUrl?: string      // 动作图片
  description?: string   // 动作描述
}

// 训练区块（热身/主训/冷身）
export interface WorkoutSection {
  type: 'warmup' | 'main' | 'cooldown'
  label: string
  exercises: ExerciseState[]
}

// 每日训练（前端日历视图用）
export interface DayPlan {
  date: string           // "2026-06-04"
  dayOfWeek: number      // 0=周日, 1=周一...
  focusArea: string      // "腿部训练" / "休息"
  isRestDay: boolean
  sections: WorkoutSection[]
}

// 月日历数据
export interface MonthData {
  year: number
  month: number          // 1-12
  days: DayPlan[]
}

// 完成状态分类
export type DayStatus = 'rest' | 'pending' | 'partial' | 'completed' | 'missed'

// ── 通用响应 ──────────────────────────────────────────────

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
}
