/**
 * API 服务层 — 周期化训练引擎接口
 *
 * 新引擎 API（init-plan / generate-next / checkin 等）+ SSE 流式支持。
 * 旧接口保留标记 @deprecated 直至视图重构完成。
 */
import axios from 'axios'
import { consumeSSE } from './sse'
import type {
  InitPlanRequest,
  WeekPlan,
  MacrocycleSummary,
  MacrocycleDetail,
  DayCheckinRequest,
  UserCurrentState,
  UserCurrentStateUpdate,
  RescheduleRequest,
  CalendarEntryResponse,
  DayDetailResponse,
  TaskStatusResponse,
  SSEEventCallbacks,
  FitnessPlanSummary,
  FitnessPlan,
  PlanRequest,
  RecordRequest,
  RecordResponse,
  UserProfile,
  UserProfileResponse,
  ProfileCombined,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 分钟，SSE 可能较久
  headers: { 'Content-Type': 'application/json' },
})

// 请求/响应拦截器（保留调试日志）
apiClient.interceptors.request.use(
  (config) => {
    console.log('[API]', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => Promise.reject(error),
)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('[API] 响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  },
)

// ═══════════════════════════════════════════════════════════
//  新引擎 API
// ═══════════════════════════════════════════════════════════

// ── SSE 流式生成 ──────────────────────────────────────

/** SSE 流式请求通用函数（axios 不支持流，改用原生 fetch） */
async function _ssePost(path: string, body: unknown, callbacks: SSEEventCallbacks): Promise<WeekPlan> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok || !res.body) {
    throw new Error(`SSE 请求失败: ${res.status} ${res.statusText}`)
  }
  return consumeSSE(res, callbacks)
}

/** 首次初始化：创建大周期 → 中周期 → 第 1 周 */
export async function initPlan(
  req: InitPlanRequest,
  callbacks: SSEEventCallbacks,
): Promise<WeekPlan> {
  return _ssePost('/api/fitness/init-plan', req, callbacks)
}

/** 基于前一周打卡，生成下一周 */
export async function generateNextWeek(
  callbacks: SSEEventCallbacks,
): Promise<WeekPlan> {
  return _ssePost('/api/fitness/generate-next', {}, callbacks)
}

// ── 异步轮询生成（替代 SSE，解决 Render 100s 超时）──────

/** 创建异步生成任务，返回 task_id */
export async function createGenerateTask(req: InitPlanRequest): Promise<{ task_id: string }> {
  const res = await apiClient.post('/api/fitness/generate-task', req)
  return res.data
}

/** 轮询任务状态 */
export async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await apiClient.get<TaskStatusResponse>(`/api/fitness/generate-task/${taskId}`)
  return res.data
}

/** 创建下周生成任务，返回 task_id */
export async function createNextWeekTask(): Promise<{ task_id: string }> {
  const res = await apiClient.post('/api/fitness/generate-next-task')
  return res.data
}

// ── REST 接口 ─────────────────────────────────────────

/** 获取当前活跃周（含完整 days → slots → exercise） */
export async function fetchCurrentWeek(): Promise<WeekPlan> {
  const res = await apiClient.get<WeekPlan>('/api/fitness/current-week')
  return res.data
}

/** 大周期列表 */
export async function listMacrocycles(): Promise<MacrocycleSummary[]> {
  const res = await apiClient.get<MacrocycleSummary[]>('/api/fitness/macrocycles')
  return res.data
}

/** 大周期详情（嵌套所有 mesocycle → week → day） */
export async function getMacrocycleDetail(id: number): Promise<MacrocycleDetail> {
  const res = await apiClient.get<MacrocycleDetail>(`/api/fitness/macrocycle/${id}`)
  return res.data
}

/** 每日打卡 */
export async function checkin(data: DayCheckinRequest): Promise<void> {
  await apiClient.post('/api/fitness/checkin', data)
}

/** 获取用户当前状态 */
export async function fetchCurrentState(): Promise<UserCurrentState> {
  const res = await apiClient.get<UserCurrentState>('/api/fitness/current-state')
  return res.data
}

/** 更新用户当前状态 */
export async function updateCurrentState(data: UserCurrentStateUpdate): Promise<void> {
  await apiClient.put('/api/fitness/current-state', data)
}

/** 合并保存用户个人信息 + 训练状态 */
export async function saveProfileCombined(data: ProfileCombined): Promise<void> {
  await apiClient.put('/api/user/profile-combined', data)
}

/** 调整训练日到新的 day_of_week */
export async function rescheduleDay(dayId: number, data: RescheduleRequest): Promise<void> {
  await apiClient.put(`/api/fitness/day/${dayId}/reschedule`, data)
}

// ── 日历 API ───────────────────────────────────────────

/** 获取指定日期范围的日历网格轻量数据 */
export async function fetchCalendarData(
  from: string,
  to: string,
): Promise<CalendarEntryResponse> {
  const res = await apiClient.get<CalendarEntryResponse>(
    `/api/fitness/calendar-data?from_date=${from}&to_date=${to}`,
  )
  return res.data
}

/** 获取某天的完整训练内容 */
export async function fetchDayDetail(date: string): Promise<DayDetailResponse> {
  const res = await apiClient.get<DayDetailResponse>(
    `/api/fitness/day-detail?date=${date}`,
  )
  return res.data
}

// ═══════════════════════════════════════════════════════════
//  @deprecated 旧接口 — 视图重构后删除
// ═══════════════════════════════════════════════════════════

/** @deprecated 使用 initPlan 替代 */
export async function generatePlan(request: PlanRequest): Promise<any> {
  const res = await apiClient.post('/api/fitness/generate', request)
  return res.data
}

/** @deprecated */
export async function getPlans(): Promise<FitnessPlanSummary[]> {
  const res = await apiClient.get<FitnessPlanSummary[]>('/api/fitness/plans')
  return res.data
}

/** @deprecated */
export async function getPlan(planId: number): Promise<FitnessPlan> {
  const res = await apiClient.get<FitnessPlan>(`/api/fitness/plan/${planId}`)
  return res.data
}

/** @deprecated 使用 checkin 替代 */
export async function saveRecord(record: RecordRequest): Promise<{ id: number; message: string }> {
  const res = await apiClient.post('/api/fitness/record', record)
  return res.data
}

/** @deprecated */
export async function getRecords(planId?: number): Promise<RecordResponse[]> {
  const params = planId ? { plan_id: planId } : {}
  const res = await apiClient.get<RecordResponse[]>('/api/fitness/records', { params })
  return res.data
}

/** @deprecated */
export async function getStats(): Promise<any> {
  const res = await apiClient.get('/api/fitness/stats')
  return res.data
}

/** @deprecated */
export async function updateExerciseStatus(
  exerciseId: number,
  data: { completed: boolean; date: string },
): Promise<any> {
  const res = await apiClient.put(`/api/fitness/exercise/${exerciseId}/status`, data)
  return res.data
}

/** @deprecated */
export async function markExerciseTooHeavy(
  exerciseId: number,
  data: { date: string; weight?: string },
): Promise<any> {
  const res = await apiClient.put(`/api/fitness/exercise/${exerciseId}/weight`, data)
  return res.data
}

/** @deprecated 外部 wger 动作详情缓存查询 */
export async function fetchExerciseDetail(wgerId: number): Promise<{
  images: string[];
  description: string;
  primary_muscles?: {id: number; name_en: string; name_cn: string}[];
  secondary_muscles?: {id: number; name_en: string; name_cn: string}[];
  equipment_list?: string[];
  muscle_group?: string;
}> {
  const res = await apiClient.get(`/api/wger/exercise/${wgerId}`)
  return res.data
}

/** @deprecated 使用 fetchCurrentState 替代 */
export async function createOrUpdateProfile(profile: UserProfile): Promise<UserProfileResponse> {
  const res = await apiClient.post<UserProfileResponse>('/api/user/profile', profile)
  return res.data
}

/** @deprecated */
export async function getProfile(): Promise<UserProfileResponse> {
  const res = await apiClient.get<UserProfileResponse>('/api/user/profile')
  return res.data
}

export default apiClient
