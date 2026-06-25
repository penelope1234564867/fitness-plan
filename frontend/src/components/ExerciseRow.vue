<template>
  <div class="exercise-row" :class="{ completed: exercise.completed, tooHeavy: exercise.tooHeavy }">
    <div class="exercise-check" @click="$emit('toggle')">
      <div class="checkbox" :class="{ checked: exercise.completed }">
        <span v-if="exercise.completed">✓</span>
      </div>
    </div>

    <div class="exercise-info" @click.stop="$emit('showDetail')">
      <span class="exercise-name">{{ exercise.name }}</span>
      <span class="exercise-detail">
        <template v-if="exercise.duration">{{ exercise.duration }}秒</template>
        <template v-else>{{ exercise.sets }}组×{{ exercise.reps }}次</template>
        <template v-if="exercise.weight"> · {{ exercise.weight }}</template>
      </span>
    </div>

    <div class="exercise-actions">
      <a-tooltip title="这个重量太重了，下次减轻">
        <a-button
          v-if="!exercise.completed && !exercise.tooHeavy"
          size="small"
          class="heavy-btn"
          @click.stop="$emit('tooHeavy')"
        >
          😰 太重了
        </a-button>
      </a-tooltip>
      <span v-if="exercise.tooHeavy" class="too-heavy-tag">已记录，下次减轻</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ExerciseState } from '@/types'

defineProps<{ exercise: ExerciseState }>()
defineEmits<{ toggle: []; tooHeavy: []; showDetail: [] }>()
</script>

<style scoped>
.exercise-row { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 12px; background: #fff; border: 1px solid #f0f0f0; transition: all 0.2s ease; }
.exercise-row:hover { border-color: #f97316; box-shadow: 0 2px 8px rgba(249,115,22,0.08); }
.exercise-row.completed { background: #f0fdf4; border-color: #22c55e; }
.exercise-row.tooHeavy { background: #fef2f2; border-color: #f97316; }
.exercise-check { cursor: pointer; padding: 4px; }
.checkbox { width: 24px; height: 24px; border-radius: 50%; border: 2px solid #d9d9d9; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700; transition: all 0.2s; color: transparent; }
.checkbox:hover { border-color: #f97316; }
.checkbox.checked { background: #22c55e; border-color: #22c55e; color: #fff; }
.exercise-info { flex: 1; display: flex; flex-direction: column; gap: 2px; cursor: pointer; }
.exercise-name { font-size: 15px; font-weight: 600; color: #1a1a1a; }
.exercise-row.completed .exercise-name { color: #22c55e; text-decoration: line-through; }
.exercise-detail { font-size: 13px; color: #888; }
.exercise-actions { flex-shrink: 0; }
.heavy-btn { border-radius: 12px; font-size: 12px; border-color: #f97316; color: #f97316; }
.heavy-btn:hover { background: #fff7ed; border-color: #f97316; color: #f97316; }
.too-heavy-tag { font-size: 12px; color: #f97316; font-weight: 500; background: #fff7ed; padding: 2px 10px; border-radius: 10px; white-space: nowrap; }
</style>
