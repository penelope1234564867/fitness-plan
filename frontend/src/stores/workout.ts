/**
 * workoutStore — 训练交互 + 打卡
 *
 * 管理选中日期的训练计划、动作打勾/RPE 快捷反馈、日期调整、打卡提交。
 * 现在通过 dayDetail API 获取单日数据，不再从 currentWeek 推导。
 */
import { defineStore } from 'pinia'
import { ref, computed, reactive } from 'vue'
import { watch } from 'vue'
import * as api from '@/services/api'
import { RPE_QUICK_MAP, RPE_QUICK_DEFAULT } from '@/types'
import type {
  WorkoutDayGrouped, DayDetailResponse,
  RPEQuick, SlotCheckinData,
} from '@/types'
import dayjs from 'dayjs'

export const useWorkoutStore = defineStore('workout', () => {
  const selectedDate = ref<string | null>(null)
  const dayDetail = ref<DayDetailResponse | null>(null)
  const dayDetailLoading = ref(false)
  const checkinLoading = ref(false)
  const error = ref<string | null>(null)

  // 肌肉图状态
  const activePrimaryMuscles = ref<{id: number; name_en: string; name_cn: string}[]>([])
  const activeSecondaryMuscles = ref<{id: number; name_en: string; name_cn: string}[]>([])

  const todayStr = computed(() => dayjs().format('YYYY-MM-DD'))

  // 将 DayDetailResponse 转为 WorkoutDayGrouped 兼容格式
  const currentDay = computed<WorkoutDayGrouped | null>(() => {
    const dd = dayDetail.value
    if (!dd || !dd.has_plan) return null
    // ★ 创建一次 mappedSlots，slots/warmup/main/cardio/stretch 共享同一组对象引用
    const mappedSlots = dd.slots.map(s => _mapSlot(s, dd))
    return {
      id: mappedSlots[0]?.day_id || 0,
      day_order: 0,
      day_of_week: dayjs(dd.date).day() || 7,
      date: dd.date,
      day_label: dd.day_label,
      focus: dd.focus,
      estimated_calories: 0,
      is_completed: dd.day_status === 'completed',
      completed_date: dd.day_status === 'completed' ? dd.date : '',
      rpe_score: 0,
      slots: mappedSlots,
      warmup: mappedSlots.filter(s => s.phase_type === 'warmup'),
      main: mappedSlots.filter(s => s.phase_type === 'main'),
      cardio: (() => {
        const items = mappedSlots.filter(s => s.phase_type === 'cardio')
        return items[0] || null
      })(),
      stretch: mappedSlots.filter(s => s.phase_type === 'stretch'),
    }
  })

  /** 当天变化摘要统计 */
  const changeSummary = computed(() => {
    const day = currentDay.value
    if (!day || !day.main.length) {
      return { increased: 0, newExercise: 0, same: 0, decreased: 0, total: 0 }
    }
    let increased = 0
    let newExercise = 0
    let same = 0
    let decreased = 0
    for (const s of day.main) {
      const ct = (s as any).change_type
      if (ct === 'increased_weight' || ct === 'increased_reps') increased++
      else if (ct === 'new_exercise') newExercise++
      else if (ct === 'same' || ct === 'none') same++
      else if (ct === 'decreased_weight') decreased++
    }
    return { increased, newExercise, same, decreased, total: day.main.length }
  })

  /** 为 slot 添加前端 UI 状态字段
   *
   *  _completed 从后端 actual_* 字段派生：
   *  如果 actual_sets>0 或 actual_reps>0 或 rpe>0，认为该动作已完成。
   *  这样打卡后重新拉取数据时 checkmark 不会消失。
   */
  function _mapSlot(s: any, dd: any) {
    const completed = s.actual_sets > 0 || s.actual_reps > 0 || s.rpe > 0
    let rpeQuick: RPEQuick | null = null
    if (completed) {
      if (s.rpe === 4) rpeQuick = 'easy'
      else if (s.rpe === 7) rpeQuick = 'normal'
      else if (s.rpe === 9) rpeQuick = 'hard'
      else rpeQuick = 'normal'  // 其他 RPE 值默认 normal
    }
    return reactive({
      ...s,
      day_id: dd?.slots?.[0]?.day_id || s.day_id || 0,
      _completed: completed,
      _rpeQuick: rpeQuick,
      _loading: false,
      change_type: s.change_type || 'none',
      weight_diff: s.weight_diff || 0,
      prev_weight_kg: s.prev_weight_kg || 0,
      prev_target_reps: s.prev_target_reps || 0,
    })
  }

  // selectedDate 变化时自动获取 day detail
  watch(selectedDate, async (date) => {
    if (!date) {
      dayDetail.value = null
      return
    }
    dayDetailLoading.value = true
    try {
      dayDetail.value = await api.fetchDayDetail(date)
    } catch (e: any) {
      console.error('[WorkoutStore] 获取日详情失败:', e.message)
      dayDetail.value = null
    } finally {
      dayDetailLoading.value = false
    }
  })

  // ── 交互动作（乐观更新）──

  function toggleExercise(slotId: number) {
    const slot = currentDay.value?.slots.find(s => s.id === slotId)
    if (!slot) return

    slot._completed = !slot._completed

    if (slot._completed) {
      if (!slot._rpeQuick) {
        slot._rpeQuick = RPE_QUICK_DEFAULT
        slot.rpe = RPE_QUICK_MAP[RPE_QUICK_DEFAULT].rpe
      }
    } else {
      slot._rpeQuick = null
      slot.rpe = 0
    }
  }

  function setRPEQuick(slotId: number, quick: RPEQuick) {
    const slot = currentDay.value?.slots.find(s => s.id === slotId)
    if (!slot) return

    slot._rpeQuick = quick
    slot.rpe = RPE_QUICK_MAP[quick].rpe
    slot._completed = true
  }

  /** 调整训练日到新的 day_of_week */
  async function rescheduleDay(dayId: number, newDayOfWeek: number) {
    await api.rescheduleDay(dayId, { day_of_week: newDayOfWeek })
    // 重新加载当前日
    if (selectedDate.value) {
      dayDetail.value = await api.fetchDayDetail(selectedDate.value)
    }
  }

  /** 重新加载当前日的详情 */
  async function reloadDayDetail() {
    if (!selectedDate.value) return
    dayDetail.value = await api.fetchDayDetail(selectedDate.value)
  }

  // ── 提交打卡 ──

  async function submitCheckin() {
    if (!currentDay.value || !dayDetail.value) return
    checkinLoading.value = true

    try {
      const exercises: SlotCheckinData[] = currentDay.value.slots
        .filter(s => s._completed || s._rpeQuick)
        .map(s => ({
          slot_id: s.id,
          actual_sets: s.actual_sets || s.target_sets,
          actual_reps: s.actual_reps || s.target_reps,
          rpe: s.rpe || 7,
          notes: '',
        }))

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
      dayDetail.value = await api.fetchDayDetail(selectedDate.value!)
    } catch (e: any) {
      error.value = e.message
      throw e
    } finally {
      checkinLoading.value = false
    }
  }

  return {
    selectedDate, dayDetail, currentDay, todayStr,
    dayDetailLoading, checkinLoading, error,
    activePrimaryMuscles, activeSecondaryMuscles,
    changeSummary,
    toggleExercise, setRPEQuick, rescheduleDay, submitCheckin, reloadDayDetail,
  }
})
