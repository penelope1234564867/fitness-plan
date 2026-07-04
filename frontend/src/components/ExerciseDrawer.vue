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

        <!-- 多图展示（a-carousel 有渲染 bug 改用首图+缩略点切换） -->
        <div v-else-if="displayImages.length > 1" class="multi-image-area">
          <img :src="displayImages[activeImageIndex]" :alt="exerciseName" class="multi-image-main" @click="cycleImage()" />
          <div class="image-thumbs">
            <span
              v-for="(img, i) in displayImages" :key="i"
              class="thumb-dot"
              :class="{ active: i === activeImageIndex }"
              @click="activeImageIndex = i"
            ></span>
          </div>
        </div>

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
            <span class="muscle-cn-only">{{ m.name_cn || m.name_en }}</span>
          </div>
        </div>
      </div>

      <!-- ═══ 辅助肌 ═══ -->
      <div v-if="wgerSecondaryMuscles.length > 0" class="muscle-section">
        <div class="muscle-section-label">🤝 辅助肌</div>
        <div class="muscle-list">
          <div v-for="m in wgerSecondaryMuscles" :key="m.id" class="muscle-item">
            <span class="muscle-cn-only">{{ m.name_cn || m.name_en }}</span>
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
          <span class="info-label">⏱️ 组间休息</span>
          <span class="info-value">{{ exercise.rest_seconds ? `${exercise.rest_seconds}秒` : '—' }}</span>
        </div>
      </div>

      <!-- ═══ 动作描述 ═══ -->
      <div v-if="displayDescription" class="desc-section">
        <div class="desc-label">📝 动作描述</div>
        <p class="desc-text">{{ displayDescription }}</p>
      </div>

      <!-- ═══ AI 加载中（wger 请求未完成时显示） ═══ -->
      <div v-if="loadingLocal" class="ai-loading-section">
        <a-spin :spinning="true" size="large">
          <div class="ai-loading-content">
            <div class="ai-loading-icon">🤖</div>
            <div class="ai-loading-text">AI 正在生成详细描述…</div>
          </div>
        </a-spin>
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
const activeImageIndex = ref(0)
/** 自动轮播定时器 */
const autoSlideTimer = ref<ReturnType<typeof setInterval> | null>(null)
/** 防止同一 wger_id 重复请求：记录当前正在请求的 id */
const fetchingWgerId = ref<number | null>(null)

function startAutoSlide() {
  stopAutoSlide()
  if (displayImages.value.length > 1) {
    autoSlideTimer.value = setInterval(() => {
      activeImageIndex.value = (activeImageIndex.value + 1) % displayImages.value.length
    }, 3000)
  }
}

function stopAutoSlide() {
  if (autoSlideTimer.value !== null) {
    clearInterval(autoSlideTimer.value)
    autoSlideTimer.value = null
  }
}

function cycleImage() {
  if (displayImages.value.length > 1) {
    activeImageIndex.value = (activeImageIndex.value + 1) % displayImages.value.length
  }
}
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
    activeImageIndex.value = 0
    // 注意：fetchingWgerId 不在这重置，让防重逻辑生效
    // 只在关闭 drawer 时由 close handler 重置

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
      // 防止同一 wger_id 重复请求
      if (fetchingWgerId.value === props.exercise.wger_id) return
      fetchingWgerId.value = props.exercise.wger_id
      loadingLocal.value = true
      try {
        const detail = await fetchExerciseDetail(props.exercise.wger_id)
        if (detail.images && detail.images.length > 0) {
          displayImages.value = detail.images
          startAutoSlide()
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
  { immediate: true },
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
      activeImageIndex.value = 0
      stopAutoSlide()
      fetchingWgerId.value = null
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
  background: var(--bg-subtle);
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.06);
}

/* — 单张图 — */
.single-img {
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  display: block;
  background: var(--bg-subtle);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-sizing: border-box;
}

/* — 多图展示 — */
.multi-image-area {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.multi-image-main {
  width: 100%;
  max-height: 280px;
  object-fit: contain;
  display: block;
  background: var(--bg-subtle);
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.2s;
  border: 1px solid var(--border-color);
  box-sizing: border-box;
}
.multi-image-main:hover { opacity: 0.85; }
.image-thumbs {
  display: flex;
  gap: 6px;
  padding: 4px 0;
}
.thumb-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-color);
  cursor: pointer;
  transition: all 0.2s;
}
.thumb-dot.active { background: var(--brand-orange); transform: scale(1.3); }
.thumb-dot:hover { background: var(--brand-orange-light); }

/* — 无图占位 — */
.no-image-placeholder {
  width: 100%;
  height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--brand-orange), var(--brand-orange-light));
  font-size: 64px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.3);
  border-radius: 12px;
}

/* — 骨架屏 — */
.skeleton-block {
  width: 100%;
  height: 260px;
  background: var(--bg-subtle);
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
  background: var(--bg-hover);
  border-radius: 12px;
  padding: 14px 16px;
}

.muscle-section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
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
  background: var(--bg-card);
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
}

.muscle-cn-only {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ══════════════════════════════════════════
   训练参数卡片
   ══════════════════════════════════════════ */
.info-card {
  background: var(--bg-hover);
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
  color: var(--text-muted);
  min-width: 80px;
  flex-shrink: 0;
}

.info-value {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.info-divider {
  height: 1px;
  background: var(--border-color);
  margin: 2px 0;
}

/* ══════════════════════════════════════════
   动作描述
   ══════════════════════════════════════════ */
.desc-section {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px;
}

.desc-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.desc-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  margin: 0;
  white-space: pre-line;
}

/* ══════════════════════════════════════════
   AI 加载中
   ══════════════════════════════════════════ */
.ai-loading-section {
  background: var(--bg-hover);
  border-radius: 12px;
  padding: 32px 16px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.ai-loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.ai-loading-icon {
  font-size: 28px;
  animation: ai-pulse 1.5s ease-in-out infinite;
}
.ai-loading-text {
  font-size: 13px;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}
@keyframes ai-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
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
  background: var(--color-success);
  border: none;
  border-radius: 12px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}
.btn-done:hover {
  background: var(--color-success-deep);
}

.btn-undo {
  background: var(--text-secondary);
  border: none;
  border-radius: 12px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
}

.btn-heavy {
  border-color: var(--brand-orange);
  color: var(--brand-orange);
  border-radius: 12px;
  height: 44px;
  font-size: 14px;
}
.btn-heavy:hover {
  background: var(--brand-orange-subtle);
  border-color: var(--brand-orange);
  color: var(--brand-orange);
}

/* ══════════════════════════════════════════
   覆盖 a-drawer 标题字体
   ══════════════════════════════════════════ */
:deep(.ant-drawer-header-title) {
  font-weight: 700;
  font-size: 18px;
}
</style>
