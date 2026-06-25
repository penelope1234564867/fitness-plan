<template>
  <a-card class="record-form-card" :bordered="false">
    <template #title>
      <span>📝 记录训练</span>
    </template>

    <a-form :model="form" layout="vertical" @finish="handleSubmit">
      <a-row :gutter="16">
        <a-col :span="8">
          <a-form-item label="关联计划" name="plan_id">
            <a-select
              v-model:value="form.plan_id"
              placeholder="选择计划（可选）"
              :options="planOptions"
              allow-clear
            />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item
            label="训练日期"
            name="date"
            :rules="[{ required: true, message: '请选择日期' }]"
          >
            <a-date-picker
              v-model:value="form.date"
              style="width: 100%"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
            />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item
            label="动作名称"
            name="exercise_name"
            :rules="[{ required: true, message: '请输入动作名称' }]"
          >
            <a-input v-model:value="form.exercise_name" placeholder="例如: 深蹲" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="6">
          <a-form-item
            label="目标组数"
            name="planned_sets"
          >
            <a-input-number v-model:value="form.planned_sets" :min="0" :max="20" style="width: 100%" placeholder="计划组数" />
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item
            label="目标次数"
            name="planned_reps"
          >
            <a-input-number v-model:value="form.planned_reps" :min="0" :max="100" style="width: 100%" placeholder="计划次数" />
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item
            label="实际组数"
            name="actual_sets"
            :rules="[{ required: true, message: '请填写实际组数' }]"
          >
            <a-input-number v-model:value="form.actual_sets" :min="0" :max="20" style="width: 100%" placeholder="实际组数" />
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item
            label="实际次数"
            name="actual_reps"
            :rules="[{ required: true, message: '请填写实际次数' }]"
          >
            <a-input-number v-model:value="form.actual_reps" :min="0" :max="100" style="width: 100%" placeholder="实际次数" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="8">
          <a-form-item label="重量 (kg)" name="weight">
            <a-input-number v-model:value="form.weight" :min="0" :step="0.5" style="width: 100%" placeholder="例如: 20" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="目标肌群" name="target_muscle">
            <a-input v-model:value="form.target_muscle" placeholder="例如: 腿部" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item
            label="难度评级"
            name="difficulty"
            :rules="[{ required: true, message: '请评价难度' }]"
          >
            <a-rate v-model:value="form.difficulty" :count="5" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="备注" name="notes">
        <a-textarea v-model:value="form.notes" :rows="2" placeholder="训练感受或备注" />
      </a-form-item>

      <a-form-item>
        <a-button type="primary" html-type="submit" :loading="submitting" block size="large">
          💾 保存记录
        </a-button>
      </a-form-item>
    </a-form>
  </a-card>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useRecordStore } from '@/stores/record'
import { usePlanStore } from '@/stores/plan'
import type { FitnessPlanSummary } from '@/types'

const emit = defineEmits<{
  saved: []
}>()

const recordStore = useRecordStore()
const planStore = usePlanStore()

const submitting = ref(false)
const planOptions = ref<{ value: number; label: string }[]>([])

const form = reactive({
  plan_id: undefined as number | undefined,
  date: '',
  exercise_name: '',
  target_muscle: '',
  planned_sets: 3,
  planned_reps: 12,
  actual_sets: 3,
  actual_reps: 12,
  weight: 0,
  difficulty: 3,
  notes: '',
})

onMounted(async () => {
  // 加载计划列表用于下拉
  try {
    const plans = await planStore.fetchPlans()
    planOptions.value = plans.map((p: FitnessPlanSummary) => ({
      value: p.id,
      label: `${p.goal}计划 (${p.duration_weeks}周)`,
    }))
  } catch { /* 忽略 */ }
})

const handleSubmit = async () => {
  if (!form.date) {
    message.error('请选择训练日期')
    return
  }
  submitting.value = true
  try {
    await recordStore.addRecord({
      plan_id: form.plan_id || undefined,
      date: form.date as string,
      exercise_name: form.exercise_name,
      target_muscle: form.target_muscle || undefined,
      planned_sets: form.planned_sets,
      planned_reps: form.planned_reps,
      actual_sets: form.actual_sets,
      actual_reps: form.actual_reps,
      weight: form.weight,
      difficulty: form.difficulty,
      notes: form.notes || undefined,
    })
    message.success('训练记录已保存！')
    // 重置表单
    form.exercise_name = ''
    form.target_muscle = ''
    form.planned_sets = 3
    form.planned_reps = 12
    form.actual_sets = 3
    form.actual_reps = 12
    form.weight = 0
    form.difficulty = 3
    form.notes = ''
    emit('saved')
  } catch (error: any) {
    message.error(error.message || '保存失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.record-form-card {
  border-radius: 12px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
</style>
