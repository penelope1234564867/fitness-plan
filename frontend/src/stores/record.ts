import { defineStore } from 'pinia'
import { ref } from 'vue'
import { saveRecord, getRecords } from '@/services/api'
import type { RecordRequest, RecordResponse } from '@/types'

export const useRecordStore = defineStore('record', () => {
  const records = ref<RecordResponse[]>([])
  const loading = ref(false)

  /** 获取训练记录 */
  async function fetchRecords(planId?: number) {
    loading.value = true
    try {
      records.value = await getRecords(planId)
      return records.value
    } finally {
      loading.value = false
    }
  }

  /** 保存新记录 */
  async function addRecord(data: RecordRequest) {
    loading.value = true
    try {
      const result = await saveRecord(data)
      await fetchRecords(data.plan_id)
      return result
    } finally {
      loading.value = false
    }
  }

  return { records, loading, fetchRecords, addRecord }
})
