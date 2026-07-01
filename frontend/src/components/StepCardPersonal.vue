<template>
  <div class="step-card">
    <h2 class="step-title">👤 你的资料</h2>
    <p class="step-desc">让我先认识你</p>

    <a-form layout="vertical" class="step-form">
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="身高 (cm)" name="height">
            <a-input-number v-model:value="localData.height" :min="100" :max="250" style="width: 100%" placeholder="例如: 165" size="large" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="体重 (kg)" name="weight">
            <a-input-number v-model:value="localData.weight" :min="30" :max="250" style="width: 100%" placeholder="例如: 65" size="large" />
          </a-form-item>
        </a-col>
      </a-row>
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="年龄" name="age">
            <a-input-number v-model:value="localData.age" :min="10" :max="100" style="width: 100%" placeholder="例如: 25" size="large" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="性别" name="gender">
            <a-select v-model:value="localData.gender" placeholder="请选择" size="large" style="width: 100%">
              <a-select-option value="male">♂ 男</a-select-option>
              <a-select-option value="female">♀ 女</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-form-item label="🏋️ 训练经验" name="experience">
        <a-radio-group v-model:value="localData.experience" size="large">
          <a-radio-button value="新手">🌱 新手</a-radio-button>
          <a-radio-button value="中级">💪 中级</a-radio-button>
          <a-radio-button value="高级">🔥 高级</a-radio-button>
        </a-radio-group>
      </a-form-item>
    </a-form>

    <div class="step-actions">
      <a-button type="primary" size="large" block class="next-btn" @click="$emit('next', localData)">
        下一步
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

interface PersonalData {
  height: number | undefined
  weight: number | undefined
  age: number | undefined
  gender: string | undefined
  experience: string
}

const props = defineProps<{ data: PersonalData }>()
defineEmits<{ next: [data: PersonalData] }>()
const localData = reactive<PersonalData>({ ...props.data, experience: props.data.experience || '新手' })
</script>

<style scoped>
.step-card { }
.step-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px 0; }
.step-desc { font-size: 14px; color: #888; margin: 0 0 24px 0; }
.step-form { }
.step-actions { margin-top: 24px; }
.next-btn { height: 48px; border-radius: 12px; font-size: 16px; font-weight: 600; background: #f97316; border: none; box-shadow: none; }
.next-btn:hover { background: #ea580c; }
</style>
