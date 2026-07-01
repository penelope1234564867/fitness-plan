<template>
  <div class="muscle-diagram">
    <div class="diagram-header">
      <span class="diagram-title">💪 肌肉分布</span>
    </div>

    <div class="diagram-body" ref="diagramRef">
      <HumanAnatomy
        :gender="gender || 'male'"
        :selected-primary-muscle-groups="primaryGroups"
        :selected-secondary-muscle-groups="secondaryGroups"
        primary-highlight-color="#fb923c"
        secondary-highlight-color="#fdba74"
        default-muscle-color="#e5e5e5"
        background-color="#ffffff"
        :primary-opacity="0.8"
        :secondary-opacity="0.5"
      />

      <!-- 肌肉悬浮提示 -->
      <div
        v-if="hoveredMuscle"
        class="muscle-tooltip"
        :style="{
          left: tooltipX + 'px',
          top: tooltipY + 'px',
        }"
      >
        {{ hoveredMuscle }}
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
import { HumanMuscleAnatomy as HumanAnatomy } from '@lucawahlen/vue-human-muscle-anatomy'

const props = defineProps<{
  gender?: 'male' | 'female'
  primaryMuscles?: { id: number; name_en: string; name_cn: string }[]
  secondaryMuscles?: { id: number; name_en: string; name_cn: string }[]
}>()

// ── 悬浮 tooltip 状态 ──

const diagramRef = ref<HTMLElement | null>(null)
const hoveredMuscle = ref('')
const tooltipX = ref(0)
const tooltipY = ref(0)

/** 给 SVG 肌肉 path 绑定 hover 事件 */
function attachHoverListeners() {
  const container = diagramRef.value
  if (!container) return
  const paths = container.querySelectorAll<SVGPathElement>('path[id]')
  paths.forEach(path => {
    const id = path.id
    if (!MUSCLE_NAME_CN[id]) return
    // 避免重复绑定（MutationObserver 可能多次触发）
    if ((path as any)._muscleHoverAttached) return
    ;(path as any)._muscleHoverAttached = true

    path.style.cursor = 'pointer'
    path.addEventListener('mouseenter', () => {
      hoveredMuscle.value = MUSCLE_NAME_CN[id]
    })
    path.addEventListener('mousemove', (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      tooltipX.value = e.clientX - rect.left + 12
      tooltipY.value = e.clientY - rect.top - 10
    })
    path.addEventListener('mouseleave', () => {
      hoveredMuscle.value = ''
    })
  })
}

/**
 * wger 肌肉 ID → vue-human-muscle-anatomy 肌群名映射
 */
const WGER_TO_MUSCLE_GROUP: Record<number, string> = {
  1:  'biceps',       // 肱二头肌
  2:  'frontDelts',   // 三角肌（默认前束，推类为主）
  3:  'lowerBack',    // 竖脊肌
  4:  'chest',        // 胸大肌
  5:  'triceps',      // 肱三头肌
  6:  'abs',          // 腹肌
  7:  'adductors',   // 内收肌
  8:  'glutes',       // 臀大肌
  9:  'traps',        // 斜方肌
  10: 'quads',        // 股四头肌
  11: 'hamstrings',   // 腘绳肌
  12: 'lats',         // 背阔肌
  13: 'calves',       // 小腿
  14: 'forearms',     // 前臂
}

/** SVG path id → 中文名映射（vue-human-muscle-anatomy 的肌群名 → 中文） */
const MUSCLE_NAME_CN: Record<string, string> = {
  chest:        '胸大肌',
  lats:         '背阔肌',
  traps:        '斜方肌',
  lowerBack:    '竖脊肌',
  frontDelts:   '三角肌前束',
  sideDelts:    '三角肌中束',
  rearDelts:    '三角肌后束',
  triceps:      '肱三头肌',
  biceps:       '肱二头肌',
  forearms:     '前臂',
  abs:          '腹肌',
  obliques:     '腹外斜肌',
  glutes:       '臀大肌',
  quads:        '股四头肌',
  hamstrings:   '腘绳肌',
  adductors:    '内收肌',
  abductors:    '外展肌',
  calves:       '小腿',
  neck:         '颈部',
  rotatorCuffs: '肩袖肌群',
}

/** 将 wger 肌肉列表转为 vue-human-muscle-anatomy 肌群名数组 */
function toGroups(muscles: { id: number }[]): string[] {
  return muscles
    .map(m => WGER_TO_MUSCLE_GROUP[m.id])
    .filter(Boolean) // 去掉无法映射的
}

const primaryGroups = computed(() => toGroups(props.primaryMuscles || []))
const secondaryGroups = computed(() => toGroups(props.secondaryMuscles || []))

// ── 挂载后绑定悬浮事件 ──

onMounted(async () => {
  await nextTick()
  attachHoverListeners()
})

// HumanAnatomy 可能因 gender 切换等重建 DOM，用 MutationObserver 兜底
let observer: MutationObserver | null = null
onMounted(() => {
  if (!diagramRef.value) return
  observer = new MutationObserver(() => {
    attachHoverListeners()
  })
  observer.observe(diagramRef.value, { childList: true, subtree: true })
})
onUnmounted(() => {
  observer?.disconnect()
})

</script>

<style scoped>
.muscle-diagram {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  border: 1px solid #e8e8e8;
  padding: 12px;
  margin-top: auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.diagram-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.diagram-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}

.diagram-body {
  display: flex;
  justify-content: center;
  padding: 4px 0;
  overflow: hidden;
  position: relative;  /* tooltip 定位锚点 */
}

.muscle-tooltip {
  position: absolute;
  z-index: 10;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 6px;
  white-space: nowrap;
  pointer-events: none;
  transition: opacity 0.15s;
  line-height: 1.4;
}
</style>
