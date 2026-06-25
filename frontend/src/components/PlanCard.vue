<template>
  <a-card class="plan-card" :bordered="false">
    <template #title>
      <div class="card-title">
        <span>{{ workout.day }}</span>
        <a-tag color="orange">{{ workout.focus }}</a-tag>
        <span v-if="workout.estimated_calories" class="calories">🔥 {{ workout.estimated_calories }} kcal</span>
      </div>
    </template>

    <!-- 热身 -->
    <div v-if="workout.warmup && workout.warmup.length" class="workout-section">
      <div class="section-label warmup-label">🔥 热身</div>
      <ExerciseItem
        v-for="(ex, i) in workout.warmup"
        :key="'warmup-' + i"
        :exercise="ex"
      />
    </div>

    <!-- 主训练 -->
    <div v-if="workout.main && workout.main.length" class="workout-section">
      <div class="section-label main-label">💪 主训练</div>
      <ExerciseItem
        v-for="(ex, i) in workout.main"
        :key="'main-' + i"
        :exercise="ex"
      />
    </div>

    <!-- 冷身 -->
    <div v-if="workout.cooldown && workout.cooldown.length" class="workout-section">
      <div class="section-label cooldown-label">🧘 冷身</div>
      <ExerciseItem
        v-for="(ex, i) in workout.cooldown"
        :key="'cooldown-' + i"
        :exercise="ex"
      />
    </div>

    <div v-if="!workout.warmup?.length && !workout.main?.length && !workout.cooldown?.length" class="empty-section">
      <a-empty description="暂无训练内容" />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { DailyWorkout } from '@/types'
import ExerciseItem from './ExerciseItem.vue'

defineProps<{
  workout: DailyWorkout
}>()
</script>

<style scoped>
.plan-card {
  border-radius: 12px;
  margin-bottom: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.plan-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.card-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 16px;
  font-weight: 600;
}
.calories {
  margin-left: auto;
  font-size: 14px;
  color: #ff7a00;
}
.workout-section {
  margin-bottom: 12px;
}
.section-label {
  font-size: 14px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 6px;
  margin-bottom: 8px;
  display: inline-block;
}
.warmup-label { background: #fff7e6; color: #d46b08; }
.main-label { background: #f0f5ff; color: #1d39c4; }
.cooldown-label { background: #f6ffed; color: #389e0d; }
.empty-section {
  padding: 20px;
  text-align: center;
}
</style>
