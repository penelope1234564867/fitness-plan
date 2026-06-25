// 健身计划类型定义

// ── 用户资料 ──────────────────────────────────────────────

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

// ── 计划生成请求 ──────────────────────────────────────────

export interface PlanRequest {
  goal: string                          // 减脂/增肌/塑形/保持健康
  experience_level: string              // 新手/中级/高级
  workout_location: string              // 健身房/居家/户外
  days_per_week: number
  duration_weeks: number
  diet_preference: string               // 普通/素食/高蛋白/低碳水
  city?: string
  notes?: string
}

// ── 训练动作 ──────────────────────────────────────────────

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

// ── 每日训练 ──────────────────────────────────────────────

export interface DailyWorkout {
  day: string                           // 周一 / 周二 ...
  focus: string                         // 胸部/背部/腿部...
  warmup: ExerciseItem[]
  main: ExerciseItem[]
  cooldown: ExerciseItem[]
  estimated_calories?: number
}

// ── 每周计划 ──────────────────────────────────────────────

export interface WeeklyPlan {
  week: number
  days: DailyWorkout[]
}

// ── 饮食建议 ──────────────────────────────────────────────

export interface DietAdvice {
  daily_calories?: number
  protein_ratio?: string
  carb_ratio?: string
  fat_ratio?: string
  meals?: Record<string, string>
  tips: string[]
}

// ── 完整计划响应 ──────────────────────────────────────────

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

// ── 训练记录 ──────────────────────────────────────────────

export interface RecordRequest {
  plan_id?: number
  date: string                          // YYYY-MM-DD
  exercise_name: string
  target_muscle?: string
  planned_sets?: number
  planned_reps?: number
  actual_sets: number
  actual_reps: number
  weight?: number
  difficulty: number                    // 1-5
  notes?: string
}

export interface RecordResponse extends RecordRequest {
  id: number
}

// ── 通用响应 ──────────────────────────────────────────────

export interface ApiResponse<T = any> {
  success: boolean
  message: string
  data?: T
}
