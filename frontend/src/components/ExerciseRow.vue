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
        <template v-if="exercise.phase_type === 'warmup'">
          {{ exercise.target_reps }}次
        </template>
        <template v-else-if="exercise.phase_type === 'stretch'">
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
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s ease;
}
.exercise-row:hover { border-color: var(--brand-orange); }
.exercise-row.completed { background: var(--color-success-subtle); border-color: var(--color-success); }
.exercise-row.rpe-easy { background: var(--color-info-subtle); border-color: var(--color-info); }
.exercise-row.rpe-hard { background: var(--color-error-subtle); border-color: var(--color-error); }

.exercise-check { cursor: pointer; padding: 2px; }
.checkbox {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid var(--border-color);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 700;
  transition: all 0.2s; color: transparent;
}
.checkbox:hover { border-color: var(--brand-orange); }
.checkbox.checked { background: var(--color-success); border-color: var(--color-success); color: #fff; }

.exercise-info { flex: 1; display: flex; flex-direction: column; gap: 2px; cursor: pointer; min-width: 0; }
.exercise-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.exercise-row.completed .exercise-name { color: var(--color-success); text-decoration: line-through; }
.exercise-detail { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.rpe-buttons { display: flex; gap: 2px; flex-shrink: 0; }
.rpe-btn {
  width: 28px; height: 28px; border-radius: 50%;
  border: 1px solid var(--border-color); background: var(--bg-card);
  font-size: 14px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.15s; padding: 0; line-height: 1;
}
.rpe-btn:hover { transform: scale(1.15); }
.rpe-btn-easy.active { background: var(--color-info-subtle); border-color: var(--color-info); }
.rpe-btn-normal.active { background: var(--color-success-subtle); border-color: var(--color-success); }
.rpe-btn-hard.active { background: var(--color-error-subtle); border-color: var(--color-error); }

.change-marker {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}
.marker-up { background: var(--color-success-subtle); color: var(--color-success-deep); }
.marker-down { background: var(--brand-orange-subtle); color: var(--brand-orange-deep); }
.marker-new { background: var(--color-info-subtle); color: var(--color-info-deep); }
</style>
