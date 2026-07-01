<template>
  <a-drawer
    :open="visible"
    :title="exercise?.name || '动作详情'"
    placement="right"
    :width="380"
    @close="$emit('close')"
  >
    <div v-if="exercise" class="drawer-content">
      <!-- 图片区：骨架屏或真实图片 -->
      <div class="drawer-image">
        <a-skeleton v-if="loadingImage" active :paragraph="{ rows: 1 }" :title="false">
          <div class="skeleton-image-block"></div>
        </a-skeleton>
        <template v-else>
          <img
            v-if="displayImages.length > 0"
            :src="displayImages[0]"
            :alt="exercise.name"
          />
          <div v-else-if="exercise.imageUrl" class="drawer-image-fit">
            <img :src="exercise.imageUrl" :alt="exercise.name" />
          </div>
          <div v-else class="drawer-image-placeholder">
            <span>{{ exercise.name.charAt(0) }}</span>
          </div>
        </template>
      </div>

      <!-- 第二张图片（如果有） -->
      <div v-if="displayImages.length > 1" class="drawer-image-secondary">
        <img :src="displayImages[1]" :alt="`${exercise.name} 侧视图`" />
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

        <div class="drawer-desc-section">
          <span class="drawer-info-label">📝 动作描述</span>
          <a-skeleton v-if="loadingImage" active :paragraph="{ rows: 3 }" :title="false" />
          <p v-else class="drawer-desc">{{ displayDescription || exercise.description || '暂无描述' }}</p>
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
import { ref, watch } from 'vue'
import type { ExerciseState } from '@/types'
import { fetchExerciseDetail } from '@/services/api'

const props = defineProps<{
  visible: boolean
  exercise: ExerciseState | null
}>()

defineEmits<{
  close: []
  toggle: []
  tooHeavy: []
}>()

const loadingImage = ref(false)
const displayImages = ref<string[]>([])
const displayDescription = ref('')

watch(
  () => props.visible,
  async (isOpen) => {
    if (!isOpen || !props.exercise) return

    // 先清空旧数据
    displayImages.value = []
    displayDescription.value = ''

    // 如果有 wgerId，异步加载真实图片和描述
    if (props.exercise.wgerId) {
      loadingImage.value = true
      try {
        const detail = await fetchExerciseDetail(props.exercise.wgerId)
        displayImages.value = detail.images || []
        displayDescription.value = detail.description || ''
      } catch {
        // 失败时 fallback 到已有字段，不报错
        displayImages.value = []
        displayDescription.value = ''
      } finally {
        loadingImage.value = false
      }
    } else if (props.exercise.imageUrl) {
      // 没有 wgerId 但有 imageUrl，直接用
      displayImages.value = [props.exercise.imageUrl]
    }
  },
)

// 关闭时重置状态
watch(
  () => props.visible,
  (isOpen) => {
    if (!isOpen) {
      displayImages.value = []
      displayDescription.value = ''
      loadingImage.value = false
    }
  },
)
</script>

<style scoped>
.drawer-image { margin-bottom: 16px; border-radius: 12px; overflow: hidden; background: #f5f5f5; }
.drawer-image img,
.drawer-image-fit img { width: 100%; height: 220px; object-fit: cover; display: block; }
.drawer-image-secondary {
  margin-bottom: 16px; border-radius: 12px; overflow: hidden; background: #f5f5f5;
}
.drawer-image-secondary img { width: 100%; height: 140px; object-fit: cover; display: block; }
.drawer-image-placeholder {
  width: 100%; height: 220px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #f97316, #fb923c);
  font-size: 64px; font-weight: 700; color: rgba(255,255,255,0.3);
}
.skeleton-image-block {
  width: 100%; height: 220px; background: #f0f0f0; border-radius: 12px;
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
