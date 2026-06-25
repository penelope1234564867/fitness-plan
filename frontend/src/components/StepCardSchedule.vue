<template>
  <div class="step-card">
    <h2 class="step-title">⏱ 训练安排</h2>
    <p class="step-desc">你的训练节奏和场地</p>

    <div class="form-row">
      <label class="form-label">每周训练</label>
      <div class="day-options">
        <a-button v-for="n in [2, 3, 4, 5, 6]" :key="n" :class="['day-btn', { active: localData.days === n }]" @click="localData.days = n">
          {{ n }} 天
        </a-button>
      </div>
    </div>

    <div class="form-row">
      <label class="form-label">锻炼地点</label>
      <div class="location-options">
        <div v-for="loc in locations" :key="loc.value" class="location-card" :class="{ active: localData.location === loc.value }" @click="localData.location = loc.value">
          <span class="loc-icon">{{ loc.icon }}</span>
          <span class="loc-label">{{ loc.label }}</span>
        </div>
      </div>
    </div>

    <div class="step-actions">
      <a-button size="large" class="back-btn" @click="$emit('prev')">← 上一步</a-button>
      <a-button type="primary" size="large" class="generate-btn" :disabled="!localData.days || !localData.location" @click="$emit('next', localData)">
        🚀 生成计划
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

interface ScheduleData { days: number; location: string }

const props = defineProps<{ data: ScheduleData }>()
const emit = defineEmits<{ prev: []; next: [data: ScheduleData] }>()
const localData = reactive<ScheduleData>({ ...props.data })
const locations = [
  { value: '健身房', icon: '🏋️', label: '健身房' },
  { value: '居家', icon: '🏠', label: '居家' },
  { value: '户外', icon: '🌳', label: '户外' },
]
</script>

<style scoped>
.step-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px 0; }
.step-desc { font-size: 14px; color: #888; margin: 0 0 24px 0; }
.form-row { margin-bottom: 24px; }
.form-label { display: block; font-size: 14px; font-weight: 600; color: #444; margin-bottom: 10px; }
.day-options { display: flex; gap: 8px; }
.day-btn { flex: 1; height: 44px; border-radius: 10px; font-size: 14px; font-weight: 600; transition: all 0.2s; }
.day-btn.active { background: #f97316; border-color: #f97316; color: #fff; box-shadow: 0 2px 8px rgba(249,115,22,0.25); }
.location-options { display: flex; gap: 10px; }
.location-card { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 18px 12px; border: 1.5px solid #e8e8e8; border-radius: 12px; cursor: pointer; transition: all 0.2s ease; background: #fff; }
.location-card:hover { border-color: #f97316; }
.location-card.active { border-color: #f97316; background: #fff7ed; box-shadow: 0 2px 8px rgba(249,115,22,0.12); }
.loc-icon { font-size: 28px; margin-bottom: 4px; }
.loc-label { font-size: 14px; font-weight: 600; color: #333; }
.step-actions { display: flex; gap: 12px; margin-top: 24px; }
.back-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 15px; }
.generate-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 16px; font-weight: 600; background: #22c55e; border: none; }
.generate-btn:hover { background: #16a34a; }
.generate-btn:disabled { background: #d9d9d9; }
</style>
