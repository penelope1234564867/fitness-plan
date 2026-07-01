<template>
  <a-drawer
    :open="visible"
    :title="exerciseName"
    placement="right"
    :width="500"
    :closable="true"
    :mask-closable="true"
    :keyboard="true"
    @close="$emit('close')"
    class="exercise-drawer"
  >
    <div v-if="exercise" class="drawer-body">
      <!-- ═══ 图片区 ═══ -->
      <div class="image-area">
        <!-- 骨架屏（仅首次无图时显示） -->
        <a-skeleton v-if="loadingLocal && displayImages.length === 0" active :paragraph="{ rows: 1 }" :title="false">
          <div class="skeleton-block"></div>
        </a-skeleton>

        <!-- 轮播（多图） -->
        <a-carousel v-else-if="displayImages.length > 1">
          <div v-for="(img, i) in displayImages" :key="i" class="carousel-slide">
            <img :src="img" :alt="`${exerciseName} - ${i + 1}`" />
          </div>
        </a-carousel>

        <!-- 单图 -->
        <img v-else-if="displayImages.length === 1" :src="displayImages[0]" :alt="exerciseName" class="single-img" />

        <!-- 无图占位 -->
        <div v-else class="no-image-placeholder">
          <span>{{ exerciseName.charAt(0) }}</span>
        </div>
      </div>

      <!-- ═══ 标签行 ═══ -->
      <div class="tags-row">
        <a-tag v-if="wgerMuscleGroup" color="blue">{{ wgerMuscleGroup }}</a-tag>
        <a-tag v-for="eq in wgerEquipmentList" :key="eq" color="orange">{{ eq }}</a-tag>
        <a-tag v-if="exercise.exercise?.difficulty" color="green">
          {{ '★'.repeat(exercise.exercise.difficulty) }}
        </a-tag>
      </div>

      <!-- ═══ 主动肌 ═══ -->
      <div v-if="wgerPrimaryMuscles.length > 0" class="muscle-section">
        <div class="muscle-section-label">🎯 主动肌</div>
        <div class="muscle-list">
          <div v-for="m in wgerPrimaryMuscles" :key="m.id" class="muscle-item">
            <span class="muscle-en">{{ m.name_en }}</span>
            <span v-if="m.name_cn" class="muscle-cn">{{ m.name_cn }}</span>
          </div>
        </div>
      </div>

      <!-- ═══ 辅助肌 ═══ -->
      <div v-if="wgerSecondaryMuscles.length > 0" class="muscle-section">
        <div class="muscle-section-label">🤝 辅助肌</div>
        <div class="muscle-list">
          <div v-for="m in wgerSecondaryMuscles" :key="m.id" class="muscle-item">
            <span class="muscle-en">{{ m.name_en }}</span>
            <span v-if="m.name_cn" class="muscle-cn">{{ m.name_cn }}</span>
          </div>
        </div>
      </div>

      <!-- ═══ 训练参数 ═══ -->
      <div class="info-card">
        <div class="info-row">
          <span class="info-label">⚙️ 训练量</span>
          <span class="info-value">{{ volumeText }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">🏋️ 重量</span>
          <span class="info-value">{{ weightText }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">⏱️ 组间休息</span>
          <span class="info-value">{{ exercise.rest_seconds ? `${exercise.rest_seconds}秒` : '—' }}</span>
        </div>
      </div>

      <!-- ═══ 动作描述 ═══ -->
      <div v-if="displayDescription" class="desc-section">
        <div class="desc-label">📝 动作描述</div>
        <p class="desc-text">{{ displayDescription }}</p>
      </div>

      <!-- ═══ 操作按钮 ═══ -->
      <div class="action-buttons">
        <a-button
          type="primary"
          block
          size="large"
          :class="exercise._completed ? 'btn-undo' : 'btn-done'"
          @click="$emit('toggle')"
        >
          {{ exercise._completed ? '↩ 取消完成' : '✅ 标记完成' }}
        </a-button>
        <a-button
          v-if="!exercise._completed"
          block
          size="large"
          class="btn-heavy"
          @click="$emit('tooHeavy')"
        >
          😰 太重了，下次减轻
        </a-button>
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ExerciseSlot } from '@/types'
import { fetchExerciseDetail } from '@/services/api'
import { useWorkoutStore } from '@/stores/workout'

const props = defineProps<{
  visible: boolean
  exercise: ExerciseSlot | null
}>()

defineEmits<{
  close: []
  toggle: []
  tooHeavy: []
}>()

const workoutStore = useWorkoutStore()

const loadingLocal = ref(false)
const displayImages = ref<string[]>([])
const displayDescription = ref('')
const wgerPrimaryMuscles = ref<{id: number; name_en: string; name_cn: string}[]>([])
const wgerSecondaryMuscles = ref<{id: number; name_en: string; name_cn: string}[]>([])
const wgerEquipmentList = ref<string[]>([])
const wgerMuscleGroup = ref('')

const exerciseName = computed(() => props.exercise?.exercise_name || '动作详情')

const volumeText = computed(() => {
  if (!props.exercise) return '—'
  const e = props.exercise
  if (e.phase_type === 'warmup' || e.phase_type === 'stretch') {
    return `${e.target_reps}秒`
  }
  return `${e.target_sets}组 × ${e.target_reps}次`
})

const weightText = computed(() => {
  if (!props.exercise) return '—'
  const e = props.exercise
  if (e.weight_suggestion) return e.weight_suggestion
  if (e.weight_kg > 0) return `${e.weight_kg}kg`
  return '—'
})

watch(
  () => props.visible,
  async (isOpen) => {
    if (!isOpen || !props.exercise) return

    // 重置
    displayImages.value = []
    displayDescription.value = ''
    wgerPrimaryMuscles.value = []
    wgerSecondaryMuscles.value = []
    wgerEquipmentList.value = []
    wgerMuscleGroup.value = ''
    loadingLocal.value = false

    // 第一步：从本地 exercise 数据的 image_url 提取，立即显示
    const localImages = props.exercise.exercise?.image_url
      ? props.exercise.exercise.image_url.split(',').map(s => s.trim()).filter(Boolean)
      : []
    if (localImages.length > 0) {
      displayImages.value = localImages
    }

    // 本地已有数据（降级用）
    if (props.exercise.exercise?.description) {
      displayDescription.value = props.exercise.exercise.description
    }
    wgerMuscleGroup.value = props.exercise.exercise?.muscle_group || ''
    const localEq = props.exercise.exercise?.equipment
    if (localEq) {
      wgerEquipmentList.value = localEq.split(',').map(s => s.trim()).filter(Boolean)
    }

    // 第二步：有 wgerId 时，异步获取 wger 高清图 + 全部肌肉/器材详情
    if (props.exercise.wger_id) {
      loadingLocal.value = true
      try {
        const detail = await fetchExerciseDetail(props.exercise.wger_id)
        if (detail.images && detail.images.length > 0) {
          displayImages.value = detail.images
        }
        if (detail.description) {
          displayDescription.value = detail.description
        }
        // 用 wger API 返回的详细数据覆盖本地
        if (detail.primary_muscles) {
          wgerPrimaryMuscles.value = detail.primary_muscles
          workoutStore.activePrimaryMuscles = detail.primary_muscles
        }
        if (detail.secondary_muscles) {
          wgerSecondaryMuscles.value = detail.secondary_muscles
          workoutStore.activeSecondaryMuscles = detail.secondary_muscles
        }
        if (detail.equipment_list) wgerEquipmentList.value = detail.equipment_list
        if (detail.muscle_group) wgerMuscleGroup.value = detail.muscle_group
      } catch {
        // wger 请求失败，保留本地数据不报错
      } finally {
        loadingLocal.value = false
      }
    }
  },
)

// 关闭时重置
watch(
  () => props.visible,
  (isOpen) => {
    if (!isOpen) {
      displayImages.value = []
      displayDescription.value = ''
      wgerPrimaryMuscles.value = []
      wgerSecondaryMuscles.value = []
      wgerEquipmentList.value = []
      wgerMuscleGroup.value = ''
      workoutStore.activePrimaryMuscles = []
      workoutStore.activeSecondaryMuscles = []
      loadingLocal.value = false
      document.body.style.overflow = ''
    }
  },
)
</script>

<style scoped>
.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ══════════════════════════════════════════
   图片区
   ══════════════════════════════════════════ */
.image-area {
  border-radius: 12px;
  overflow: hidden;
  background: #f5f5f5;
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* — a-carousel 轮播 — */
.carousel-slide {
  height: 280px;
  display: flex !important;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
}
.carousel-slide img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* — 单张图 — */
.single-img {
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  display: block;
  background: #f5f5f5;
}

/* — 无图占位 — */
.no-image-placeholder {
  width: 100%;
  height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f97316, #fb923c);
  font-size: 64px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.3);
  border-radius: 12px;
}

/* — 骨架屏 — */
.skeleton-block {
  width: 100%;
  height: 260px;
  background: #f0f0f0;
  border-radius: 12px;
}

/* ══════════════════════════════════════════
   标签行
   ══════════════════════════════════════════ */
.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* ══════════════════════════════════════════
   肌群展示
   ══════════════════════════════════════════ */
.muscle-section {
  background: #fafafa;
  border-radius: 12px;
  padding: 14px 16px;
}

.muscle-section-label {
  font-size: 13px;
  font-weight: 600;
  color: #888;
  margin-bottom: 10px;
}

.muscle-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.muscle-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 10px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
}

.muscle-en {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.muscle-cn {
  font-size: 13px;
  color: #999;
}

/* ══════════════════════════════════════════
   训练参数卡片
   ══════════════════════════════════════════ */
.info-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.info-label {
  font-size: 13px;
  font-weight: 600;
  color: #888;
  min-width: 80px;
  flex-shrink: 0;
}

.info-value {
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
}

.info-divider {
  height: 1px;
  background: #e8e8e8;
  margin: 2px 0;
}

/* ══════════════════════════════════════════
   动作描述
   ══════════════════════════════════════════ */
.desc-section {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 16px;
}

.desc-label {
  font-size: 13px;
  font-weight: 600;
  color: #888;
  margin-bottom: 8px;
}

.desc-text {
  font-size: 14px;
  line-height: 1.7;
  color: #555;
  margin: 0;
}

/* ══════════════════════════════════════════
   操作按钮
   ══════════════════════════════════════════ */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 4px;
}

.btn-done {
  background: #22c55e;
  border: none;
  border-radius: 12px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}
.btn-done:hover {
  background: #16a34a;
}

.btn-undo {
  background: #666;
  border: none;
  border-radius: 12px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}

.btn-heavy {
  border-color: #f97316;
  color: #f97316;
  border-radius: 12px;
  height: 44px;
  font-size: 14px;
}
.btn-heavy:hover {
  background: #fff7ed;
  border-color: #f97316;
  color: #f97316;
}

/* ══════════════════════════════════════════
   覆盖 a-drawer 标题字体
   ══════════════════════════════════════════ */
:deep(.ant-drawer-header-title) {
  font-weight: 700;
  font-size: 18px;
}
</style>
