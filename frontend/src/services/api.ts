import axios from 'axios'
import type {
  UserProfile,
  UserProfileResponse,
  PlanRequest,
  FitnessPlan,
  FitnessPlanSummary,
  RecordRequest,
  RecordResponse,
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('[API] 发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('[API] 收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('[API] 响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  },
)

// ── 用户资料 ──────────────────────────────────────────────

/** 创建或更新用户资料 */
export async function createOrUpdateProfile(
  profile: UserProfile,
): Promise<UserProfileResponse> {
  const res = await apiClient.post<UserProfileResponse>('/api/user/profile', profile)
  return res.data
}

/** 获取用户资料 */
export async function getProfile(): Promise<UserProfileResponse> {
  const res = await apiClient.get<UserProfileResponse>('/api/user/profile')
  return res.data
}

// ── 健身计划 ──────────────────────────────────────────────

/** 生成训练计划 */
export async function generatePlan(request: PlanRequest): Promise<any> {
  const res = await apiClient.post('/api/fitness/generate', request)
  return res.data
}

/** 获取计划列表 */
export async function getPlans(): Promise<FitnessPlanSummary[]> {
  const res = await apiClient.get<FitnessPlanSummary[]>('/api/fitness/plans')
  return res.data
}

/** 获取单个计划详情 */
export async function getPlan(planId: number): Promise<FitnessPlan> {
  const res = await apiClient.get<FitnessPlan>(`/api/fitness/plan/${planId}`)
  return res.data
}

// ── 训练记录 ──────────────────────────────────────────────

/** 保存训练记录 */
export async function saveRecord(record: RecordRequest): Promise<{ id: number; message: string }> {
  const res = await apiClient.post('/api/fitness/record', record)
  return res.data
}

/** 获取训练记录列表 */
export async function getRecords(planId?: number): Promise<RecordResponse[]> {
  const params = planId ? { plan_id: planId } : {}
  const res = await apiClient.get<RecordResponse[]>('/api/fitness/records', { params })
  return res.data
}

/** 获取训练统计 */
export async function getStats(): Promise<any> {
  const res = await apiClient.get('/api/fitness/stats')
  return res.data
}

export default apiClient
