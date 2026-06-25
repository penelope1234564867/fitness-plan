<template>
  <a-drawer
    :open="visible"
    :title="exercise?.name || '动作详情'"
    placement="right"
    :width="380"
    @close="$emit('close')"
  >
    <div v-if="exercise" class="drawer-content">
      <div class="drawer-image">
        <img
          v-if="exercise.imageUrl"
          :src="exercise.imageUrl"
          :alt="exercise.name"
        />
        <div v-else class="drawer-image-placeholder">
          <span>{{ exercise.name.charAt(0) }}</span>
        </div>
      </div>

      <div class="drawer-info">
        <div class="drawer-info-row">
          <span class="drawer-info-label">🎯 目标肌群</span>
          <span class="drawer-info-value">{{ exercise.targetMuscle || '全身' }}</span>
        </div>
        <div class="drawer-info-row">
          <span class="drawer-info-label">⚙️ 训练量</span>
          <span class="drawer-info-value">
            <template v-if="exercise.duration">{{ exercise.duration }}秒</template>
            <template v-else>{{ exercise.sets }}组 × {{ exercise.reps }}次</template>
            <template v-if="exercise.weight"> · {{ exercise.weight }}</template>
          </span>
        </div>
        <div class="drawer-info-row">
          <span class="drawer-info-label">📌 状态</span>
          <span class="drawer-info-value" :class="exercise.completed ? 'status-done' : ''">
            {{ exercise.completed ? '✅ 已完成' : '⏳ 未完成' }}
          </span>
        </div>

        <div v-if="exercise.description" class="drawer-desc-section">
          <span class="drawer-info-label">📝 动作描述</span>
          <p class="drawer-desc">{{ exercise.description }}</p>
        </div>
      </div>

      <div class="drawer-actions">
        <a-button
          type="primary"
          block
          size="large"
          :class="exercise.completed ? 'btn-undo' : 'btn-done'"
          @click="$emit('toggle')"
        >
          {{ exercise.completed ? '↩ 取消完成' : '✅ 标记完成' }}
        </a-button>
        <a-button
          v-if="!exercise.completed && !exercise.tooHeavy"
          block
          size="large"
          class="btn-heavy"
          @click="$emit('tooHeavy')"
        >
          😰 太重了，下次减轻
        </a-button>
        <div v-if="exercise.tooHeavy" class="too-heavy-note">
          已记录「太重了」，下次将调整重量
        </div>
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import type { ExerciseState } from '@/types'

defineProps<{
  visible: boolean
  exercise: ExerciseState | null
}>()

defineEmits<{
  close: []
  toggle: []
  tooHeavy: []
}>()
</script>

<style scoped>
.drawer-image { margin-bottom: 20px; border-radius: 12px; overflow: hidden; background: #f5f5f5; }
.drawer-image img { width: 100%; height: 220px; object-fit: cover; display: block; }
.drawer-image-placeholder {
  width: 100%; height: 220px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #f97316, #fb923c);
  font-size: 64px; font-weight: 700; color: rgba(255,255,255,0.3);
}
.drawer-info { display: flex; flex-direction: column; gap: 16px; }
.drawer-info-row { display: flex; flex-direction: column; gap: 4px; }
.drawer-info-label { font-size: 13px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
.drawer-info-value { font-size: 16px; font-weight: 600; color: #1a1a1a; }
.drawer-info-value.status-done { color: #22c55e; }
.drawer-desc-section { margin-top: 8px; }
.drawer-desc { font-size: 14px; line-height: 1.7; color: #555; margin: 8px 0 0 0; }
.drawer-actions { display: flex; flex-direction: column; gap: 10px; margin-top: 24px; }
.btn-done { background: #22c55e; border: none; border-radius: 12px; height: 48px; font-size: 16px; font-weight: 600; }
.btn-done:hover { background: #16a34a; }
.btn-undo { background: #666; border: none; border-radius: 12px; height: 48px; font-size: 16px; font-weight: 600; }
.btn-heavy { border-color: #f97316; color: #f97316; border-radius: 12px; height: 44px; font-size: 14px; }
.btn-heavy:hover { background: #fff7ed; border-color: #f97316; color: #f97316; }
.too-heavy-note { text-align: center; font-size: 13px; color: #f97316; background: #fff7ed; padding: 10px; border-radius: 10px; }
</style>
