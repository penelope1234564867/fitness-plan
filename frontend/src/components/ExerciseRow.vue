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
import type { ExerciseSlot, RPEQuick } from '@/types'

defineProps<{ exercise: ExerciseSlot }>()
defineEmits<{
  toggle: []
  'set-rpe-quick': [value: RPEQuick]
  'show-detail': []
}>()
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
</style>
