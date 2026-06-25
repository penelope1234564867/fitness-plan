<template>
  <div class="exercise-item">
    <a-row :gutter="12" align="middle">
      <!-- 动作图片 -->
      <a-col :span="6">
        <div class="exercise-image-wrapper">
          <img
            :src="exercise.image_url || placeholderImage"
            :alt="exercise.name"
            class="exercise-image"
            @error="onImageError"
          />
          <div class="muscle-badge">{{ exercise.target_muscle || '全身' }}</div>
        </div>
      </a-col>
      <!-- 动作详情 -->
      <a-col :span="18">
        <div class="exercise-info">
          <h4 class="exercise-name">{{ exercise.name }}</h4>
          <div class="exercise-meta">
            <a-tag color="blue">{{ exercise.category || '力量训练' }}</a-tag>
            <span class="meta-item">🏋️ {{ exercise.sets }} 组</span>
            <span class="meta-item">🔁 {{ exercise.reps }} 次</span>
            <span v-if="exercise.weight_suggestion" class="meta-item">⚡ {{ exercise.weight_suggestion }}</span>
            <span v-if="exercise.rest_seconds" class="meta-item">⏱️ 休息 {{ exercise.rest_seconds }}s</span>
          </div>
          <p v-if="exercise.description" class="exercise-desc">{{ exercise.description }}</p>
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import type { ExerciseItem } from '@/types'

defineProps<{
  exercise: ExerciseItem
}>()

const placeholderImage = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="150"%3E%3Crect width="200" height="150" fill="%23f0f0f0"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="14" fill="%23999"%3E暂无图片%3C/text%3E%3C/svg%3E'

function onImageError(event: Event) {
  const img = event.target as HTMLImageElement
  img.src = placeholderImage
}
</script>

<style scoped>
.exercise-item {
  padding: 12px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
  margin-bottom: 8px;
  transition: all 0.2s ease;
}
.exercise-item:hover {
  background: #f0fdf4;
  border-color: #96c93d;
}
.exercise-image-wrapper {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
}
.exercise-image {
  width: 100%;
  height: 90px;
  object-fit: cover;
  border-radius: 8px;
}
.muscle-badge {
  position: absolute;
  bottom: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.65);
  color: white;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  white-space: nowrap;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.exercise-info { padding-left: 4px; }
.exercise-name {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
  color: #222;
}
.exercise-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.meta-item {
  font-size: 13px;
  color: #666;
}
.exercise-desc {
  font-size: 12px;
  color: #999;
  margin: 4px 0 0;
  line-height: 1.4;
}
</style>
