import { defineStore } from 'pinia'
import { ref } from 'vue'
import { generatePlan, getPlans, getPlan } from '@/services/api'
import type { PlanRequest, FitnessPlan, FitnessPlanSummary } from '@/types'

export const usePlanStore = defineStore('plan', () => {
  const currentPlan = ref<FitnessPlan | null>(null)
  const planList = ref<FitnessPlanSummary[]>([])
  const loading = ref(false)
  const generating = ref(false)
  const error = ref<string | null>(null)

  /** 生成训练计划 */
  async function createPlan(request: PlanRequest) {
    generating.value = true
    error.value = null
    try {
      const result = await generatePlan(request)
      if (result?.id) {
        currentPlan.value = result as FitnessPlan
      }
      return result
    } catch (e: any) {
      error.value = e.message || '生成计划失败'
      throw e
    } finally {
      generating.value = false
    }
  }

  /** 获取计划列表 */
  async function fetchPlans() {
    loading.value = true
    try {
      planList.value = await getPlans()
      return planList.value
    } finally {
      loading.value = false
    }
  }

  /** 获取单个计划详情 */
  async function fetchPlan(id: number) {
    loading.value = true
    try {
      const plan = await getPlan(id)
      currentPlan.value = plan
      return plan
    } finally {
      loading.value = false
    }
  }

  function clearCurrent() {
    currentPlan.value = null
  }

  return {
    currentPlan,
    planList,
    loading,
    generating,
    error,
    createPlan,
    fetchPlans,
    fetchPlan,
    clearCurrent,
  }
})
