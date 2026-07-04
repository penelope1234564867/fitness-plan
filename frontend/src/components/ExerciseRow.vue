<template>
  <div
    class="exercise-row"
    :class="{
      completed: exercise._completed,
      'rpe-easy': exercise._rpeQuick === 'easy',
      'rpe-hard': exercise._rpeQuick === 'hard',
    }"
  >
    <!-- 打勾 -->
    <div class="exercise-check" @click="$emit('toggle')">
      <div class="checkbox" :class="{ checked: exercise._completed }">
        <span v-if="exercise._completed">✓</span>
      </div>
    </div>

    <!-- 动作信息 -->
    <div class="exercise-info" @click.stop="$emit('show-detail')">
      <span class="exercise-name">{{ exercise.exercise_name }}</span>
      <span class="exercise-detail">
        <template v-if="exercise.phase_type === 'warmup' || exercise.phase_type === 'stretch'">
          {{ exercise.target_reps }}秒
        </template>
        <template v-else>
          {{ exercise.target_sets }}组×{{ exercise.target_reps }}次
        </template>
        <template v-if="exercise.weight_suggestion"> · {{ exercise.weight_suggestion }}</template>
      </span>
    </div>

    <!-- 变化标记（仅主项显示） -->
    <span v-if="exercise.phase_type === 'main' && markerText" class="change-marker" :class="markerClass">
      {{ markerText }}
    </span>

    <!-- RPE 快捷按钮（仅主项动作显示） -->
    <div v-if="exercise.phase_type === 'main'" class="rpe-buttons">
      <button
        class="rpe-btn rpe-btn-easy"
        :class="{ active: exercise._rpeQuick === 'easy' }"
        title="😊 太轻松 → 下周加重量"
        @click.stop="$emit('set-rpe-quick', 'easy')"
      >😊</button>
      <button
        class="rpe-btn rpe-btn-normal"
        :class="{ active: exercise._rpeQuick === 'normal' }"
        title="✔ 正常完成 → 下周加次数"
        @click.stop="$emit('set-rpe-quick', 'normal')"
      >✔</button>
      <button
        class="rpe-btn rpe-btn-hard"
        :class="{ active: exercise._rpeQuick === 'hard' }"
        title="😰 太重了 → 下周减量"
        @click.stop="$emit('set-rpe-quick', 'hard')"
      >😰</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ExerciseSlot, RPEQuick } from '@/types'

const props = defineProps<{ exercise: ExerciseSlot }>()
defineEmits<{
  toggle: []
  'set-rpe-quick': [value: RPEQuick]
  'show-detail': []
}>()

/** 变化标记文字 */
const markerText = computed(() => {
  const ct = props.exercise.change_type
  if (!ct || ct === 'none' || ct === 'same') return ''
  const wd = props.exercise.weight_diff || 0
  switch (ct) {
    case 'increased_weight': return `↑${wd}kg`
    case 'increased_reps': {
      const diff = props.exercise.target_reps - props.exercise.prev_target_reps
      return diff > 0 ? `+${diff}次` : ''
    }
    case 'decreased_weight': return `⬇${Math.abs(wd)}kg`
    case 'new_exercise': return '🔄 新动作'
    default: return ''
  }
})

const markerClass = computed(() => {
  const ct = props.exercise.change_type
  if (ct === 'increased_weight' || ct === 'increased_reps') return 'marker-up'
  if (ct === 'decreased_weight') return 'marker-down'
  if (ct === 'new_exercise') return 'marker-new'
  return ''
})
</script>

<style scoped>
.exercise-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #f0f0f0;
  transition: all 0.2s ease;
}
.exercise-row:hover { border-color: #f97316; }
.exercise-row.completed { background: #f0fdf4; border-color: #22c55e; }
.exercise-row.rpe-easy { background: #eff6ff; border-color: #3b82f6; }
.exercise-row.rpe-hard { background: #fef2f2; border-color: #ef4444; }

.exercise-check { cursor: pointer; padding: 2px; }
.checkbox {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid #d9d9d9;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  transition: all 0.2s; color: transparent;
}
.checkbox:hover { border-color: #f97316; }
.checkbox.checked { background: #22c55e; border-color: #22c55e; color: #fff; }

.exercise-info { flex: 1; display: flex; flex-direction: column; gap: 2px; cursor: pointer; min-width: 0; }
.exercise-name { font-size: 14px; font-weight: 600; color: #1a1a1a; }
.exercise-row.completed .exercise-name { color: #22c55e; text-decoration: line-through; }
.exercise-detail { font-size: 12px; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.rpe-buttons { display: flex; gap: 2px; flex-shrink: 0; }
.rpe-btn {
  width: 28px; height: 28px; border-radius: 50%;
  border: 1px solid #e5e5e5; background: #fff;
  font-size: 14px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s; padding: 0; line-height: 1;
}
.rpe-btn:hover { transform: scale(1.15); }
.rpe-btn-easy.active { background: #dbeafe; border-color: #3b82f6; }
.rpe-btn-normal.active { background: #dcfce7; border-color: #22c55e; }
.rpe-btn-hard.active { background: #fecaca; border-color: #ef4444; }

.change-marker {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}
.marker-up { background: #dcfce7; color: #16a34a; }
.marker-down { background: #fff7ed; color: #ea580c; }
.marker-new { background: #dbeafe; color: #2563eb; }
</style>
