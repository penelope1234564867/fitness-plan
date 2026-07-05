<template>
  <div class="step-card">
    <h2 class="step-title">📅 每周安排</h2>
    <p class="step-desc">选择你的训练日和训练地点</p>

    <div class="form-row">
      <label class="form-label">训练日</label>
      <div class="day-picker">
        <div
          v-for="d in dayOptions"
          :key="d.value"
          class="day-chip"
          :class="{ active: selectedDays.includes(d.value) }"
          @click="toggleDay(d.value)"
        >{{ d.label }}</div>
      </div>
      <p class="day-count">共 {{ selectedDays.length }} 天/周</p>
    </div>

    <div class="form-row">
      <label class="form-label">训练地点 <span class="multi-hint">（可多选）</span></label>
      <div class="location-options">
        <div
          v-for="loc in locationOptions"
          :key="loc.value"
          class="location-card"
          :class="{ active: localData.locations.includes(loc.value) }"
          @click="toggleLocation(loc.value)"
        >
          <span class="check-mark" v-if="localData.locations.includes(loc.value)">✓</span>
          <span class="loc-icon">{{ loc.icon }}</span>
          <span class="loc-label">{{ loc.label }}</span>
        </div>
      </div>
    </div>

    <div class="step-actions">
      <a-button class="back-btn" @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" class="generate-btn" :disabled="selectedDays.length === 0" @click="onGenerate">
        生成计划 🚀
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

interface ScheduleData {
  days: number
  locations: string[]
  city: string
  preferredDays: string
}

const props = defineProps<{ data: ScheduleData }>()
const emit = defineEmits<{ prev: []; next: [data: ScheduleData] }>()

const dayOptions = [
  { value: 1, label: '一' }, { value: 2, label: '二' }, { value: 3, label: '三' },
  { value: 4, label: '四' }, { value: 5, label: '五' }, { value: 6, label: '六' }, { value: 7, label: '日' },
]

const locationOptions = [
  { value: '居家', icon: '🏠', label: '居家' },
  { value: '健身房', icon: '🏋️', label: '健身房' },
  { value: '户外', icon: '🌳', label: '户外' },
]

const localData = reactive({
  locations: [...(props.data.locations || [])],
  city: props.data.city || '',
})

const selectedDays = reactive<number[]>([])

if (props.data.preferredDays) {
  selectedDays.push(...props.data.preferredDays.split(',').map(Number))
} else if (props.data.days) {
  const defaults: Record<number, number[]> = { 2: [1, 4], 3: [1, 3, 5], 4: [1, 2, 4, 5], 5: [1, 2, 3, 4, 5], 6: [1, 2, 3, 4, 5, 6] }
  selectedDays.push(...(defaults[props.data.days] || defaults[3]))
}

function toggleDay(value: number) {
  const idx = selectedDays.indexOf(value)
  if (idx >= 0) { selectedDays.splice(idx, 1) }
  else { selectedDays.push(value) }
  selectedDays.sort()
}

function toggleLocation(value: string) {
  const idx = localData.locations.indexOf(value)
  if (idx >= 0) { localData.locations.splice(idx, 1) }
  else { localData.locations.push(value) }
}

function onGenerate() {
  emit('next', {
    days: selectedDays.length,
    locations: localData.locations,
    city: localData.city,
    preferredDays: selectedDays.join(','),
  })
}
</script>

<style scoped>
.step-title { font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0; }
.step-desc { font-size: 14px; color: var(--text-muted); margin: 0 0 24px 0; }
.form-row { margin-bottom: 24px; }
.form-label { display: block; font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 10px; }

.day-picker { display: flex; gap: 6px; flex-wrap: wrap; }
.day-chip {
  width: 44px; height: 44px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700;
  border: 2px solid var(--border-color); background: var(--bg-card);
  cursor: pointer; transition: all 0.2s;
  user-select: none;
  color: var(--text-primary);
}
.day-chip:hover { border-color: var(--brand-orange); color: var(--brand-orange); }
.day-chip.active { background: var(--brand-orange); border-color: var(--brand-orange); color: #fff; box-shadow: 0 2px 8px rgba(217,119,6,0.25); }
.day-count { margin: 8px 0 0; font-size: 13px; color: var(--text-muted); font-weight: 500; }

.location-options { display: flex; gap: 10px; }
.location-card { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 18px 12px; border: 1.5px solid var(--border-color); border-radius: 12px; cursor: pointer; transition: all 0.2s; background: var(--bg-card); position: relative; }
.location-card:hover { border-color: var(--brand-orange); }
.location-card.active { border-color: var(--brand-orange); background: var(--brand-orange-subtle); box-shadow: 0 2px 8px rgba(217,119,6,0.12); }
.multi-hint { font-size: 12px; color: var(--text-muted); font-weight: 400; }
.loc-icon { font-size: 28px; margin-bottom: 4px; }
.loc-label { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.check-mark { position: absolute; top: 6px; right: 6px; width: 18px; height: 18px; border-radius: 50%; background: var(--brand-orange); color: #fff; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; }

.step-actions { display: flex; gap: 12px; margin-top: 24px; }
.back-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 15px; border: 1.5px solid var(--border-color); background: var(--bg-card); cursor: pointer; font-weight: 600; }
.back-btn:hover { border-color: var(--brand-orange); color: var(--brand-orange); }
.generate-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 16px; font-weight: 600; background: var(--color-success); border: none; color: #fff; cursor: pointer; }
.generate-btn:hover:not(:disabled) { background: var(--color-success-deep); }
.generate-btn:disabled { background: var(--bg-subtle); cursor: not-allowed; }
</style>
