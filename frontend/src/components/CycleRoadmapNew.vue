<template>
  <div class="cycle-roadmap-new">
    <!-- 第1行：我在哪 + 倒计时 -->
    <div class="cr-top">
      <div class="cr-phase">
        <span class="cr-icon">{{ activePhaseIcon }}</span>
        <span class="cr-name">{{ activePhaseLabel }}</span>
        <span class="cr-week">第 {{ data.currentWeekNumber }}/{{ data.totalWeeks }} 周</span>
      </div>
      <div class="cr-countdown">
        <div class="cr-countdown-label">⏳ 剩余</div>
        <div class="cr-countdown-num">{{ remainingWeeks }} 周</div>
      </div>
    </div>

    <!-- 大周期进度条（已按周数显示真实进度） -->
    <div class="cr-bar-wrap">
      <div class="cr-bar-header">
        <span>📊 大周期进度</span>
        <span>{{ data.currentWeekNumber }}/{{ data.totalWeeks }}</span>
      </div>
      <div class="cr-bar">
        <div
          v-for="(piece, idx) in barPieces"
          :key="idx"
          class="cr-bar-seg"
          :style="{
            width: piece.width,
            background: piece.bg,
            borderRadius: piece.radius,
          }"
        />
      </div>
    </div>

    <!-- 阶段时间线（可点击） -->
    <div class="cr-phases">
      <button
        v-for="(seg, idx) in data.mesocycles"
        :key="seg.phase"
        class="cr-phase-btn"
        :class="{
          'active-tab': activeTab === seg.phase,
          'is-current': seg.status === 'active',
        }"
        :style="{
          borderRadius:
            idx === 0 ? '8px 0 0 8px' :
            idx === data.mesocycles.length - 1 ? '0 8px 8px 0' : '0',
        }"
        @click="selectPhase(seg.phase)"
      >
        <span class="cr-pb-icon" :class="{ dim: seg.status === 'pending' }">
          {{ phaseIcon(seg.phase) }} {{ seg.label }}
        </span>
        <span class="cr-pb-weeks">{{ seg.weekCount }} 周</span>
        <span class="cr-pb-status" :class="seg.status">
          <template v-if="seg.status === 'completed'">✅ 已完成</template>
          <template v-else-if="seg.status === 'active'">◉ 第{{ seg.currentWeek }}/{{ seg.weekCount }}周</template>
          <template v-else>即将到来</template>
        </span>
      </button>
    </div>

    <!-- 本周训练 + 下一阶段 -->
    <div class="cr-cards">
      <div class="cr-sub-card">
        <div class="cr-sub-label">✅ 本周训练</div>
        <div class="cr-sub-value">{{ completedDays }}/{{ totalDays }}</div>
        <div class="cr-sub-hint">{{ totalDays - completedDays > 0 ? '还剩 ' + (totalDays - completedDays) + ' 天' : '全部完成 🎉' }}</div>
      </div>
      <div class="cr-sub-card">
        <div class="cr-sub-label">🧭 下一阶段</div>
        <div class="cr-sub-value next">{{ nextPhaseLabel || '即将完成 🎉' }}</div>
        <div v-if="nextPhaseLabel" class="cr-sub-hint cal">{{ nextPhaseEstimate }}</div>
      </div>
    </div>

    <!-- 阶段说明区（点击切换） -->
    <div class="cr-desc">
      <div class="cr-desc-title">{{ currentDescription.title }}</div>
      <div class="cr-desc-text">{{ currentDescription.description }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { RoadmapData } from '@/types'
import { PHASE_DESCRIPTIONS, PHASE_LABEL_MAP } from '@/types'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

function getPhaseColor(phase: string, lightColor: string): string {
  if (!themeStore.isDark) return lightColor
  const darkMap: Record<string, string> = {
    foundational: '#60a5fa',
    hypertrophy: '#4ade80',
    strength: '#fb923c',
    deload: '#c084fc',
  }
  return darkMap[phase] || lightColor
}

const props = defineProps<{
  data: RoadmapData
  goal: string
  completedDays: number
  totalDays: number
  nextPhaseLabel?: string
}>()

// 默认选中当前进行中的阶段
const activeTab = ref<string>(
  props.data.mesocycles.find(s => s.status === 'active')?.phase
    ?? props.data.mesocycles[0]?.phase
    ?? '',
)

const phaseIcons: Record<string, string> = {
  foundational: '🌱',
  hypertrophy: '🔥',
  strength: '💪',
  deload: '🔄',
}

function phaseIcon(phase: string): string {
  return phaseIcons[phase] ?? '💪'
}

/** 当前进行中的阶段（始终不变） */
const currentActiveSegment = computed(() =>
  props.data.mesocycles.find(s => s.status === 'active')
    ?? props.data.mesocycles[0],
)

/** 当前选中的阶段 */
const selectedSegment = computed(() =>
  props.data.mesocycles.find(s => s.phase === activeTab.value)
    ?? props.data.mesocycles[0],
)

/** 当前进行中的阶段图标 */
const activePhaseIcon = computed(() => {
  const seg = currentActiveSegment.value
  return phaseIcon(seg?.phase ?? '')
})

/** 当前进行中的阶段名称（始终显示你当前是什么阶段） */
const activePhaseLabel = computed(() => {
  const seg = currentActiveSegment.value
  if (!seg) return ''
  const labels = PHASE_LABEL_MAP[props.goal] || PHASE_LABEL_MAP['增肌']
  return labels[seg.phase] || seg.label
})

/** 当前进行中的阶段剩余周数 */
const remainingWeeks = computed(() => {
  const seg = currentActiveSegment.value
  if (!seg) return 0
  if (seg.status === 'pending') return seg.weekCount
  if (seg.status === 'completed') return 0
  return (seg.weekCount - (seg.currentWeek ?? 1)) + 1
})

/** 阶段说明文案 */
const currentDescription = computed(() => {
  const goal = (props.goal && PHASE_DESCRIPTIONS[props.goal]) ? props.goal : '增肌'
  const phase = activeTab.value || 'foundational'
  const descMap = PHASE_DESCRIPTIONS[goal]
  return descMap[phase] ?? descMap['foundational']
})

/** 下一阶段预计时间 */
const nextPhaseEstimate = computed(() => {
  const activeSeg = props.data.mesocycles.find(s => s.status === 'active')
  if (!activeSeg) return ''
  const remaining = (activeSeg.weekCount - (activeSeg.currentWeek ?? 1)) + 1
  if (remaining <= 1) return '下周开始'
  return `约 ${remaining} 周后`
})

/** 进度条分段（活跃阶段按已完成周数拆为"已上色 + 灰色"两部分） */
interface BarPiece { width: string; bg: string; radius: string }
const barPieces = computed(() => {
  const pieces: BarPiece[] = []
  const total = props.data.totalWeeks
  const cycles = props.data.mesocycles

  for (const seg of cycles) {
    if (seg.status === 'active') {
      // currentWeek 是 1-based
      const cw = seg.currentWeek ?? 1
      const fullyDone = Math.max(0, cw - 1)       // 已完整完成的周数
      const inProgress = 1                         // 当前正在进行的这周
      const remaining = seg.weekCount - cw         // 还没到的未来周数

      if (fullyDone > 0) {
        pieces.push({ width: (fullyDone / total * 100) + '%', bg: getPhaseColor(seg.phase, seg.color), radius: '' })
      }
      // 当前周：半透明显示"进行中"
      pieces.push({ width: (inProgress / total * 100) + '%', bg: getPhaseColor(seg.phase, seg.color) + '40', radius: '' })
      if (remaining > 0) {
        pieces.push({ width: (remaining / total * 100) + '%', bg: '#e8e8e8', radius: '' })
      }
    } else {
      pieces.push({
        width: (seg.weekCount / total * 100) + '%',
        bg: seg.status === 'completed' ? getPhaseColor(seg.phase, seg.color) : 'var(--bg-subtle)',
        radius: '',
      })
    }
  }

  // 首尾圆角
  if (pieces.length > 0) {
    pieces[0].radius = '5px 0 0 5px'
    pieces[pieces.length - 1].radius = '0 5px 5px 0'
  }
  return pieces
})

function selectPhase(phase: string) {
  activeTab.value = phase
}
</script>

<style scoped>
.cycle-roadmap-new {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 18px;
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
}

/* ── 第1行：我在哪 + 倒计时 ── */
.cr-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.cr-phase { display: flex; align-items: center; gap: 6px; }
.cr-icon { font-size: 22px; }
.cr-name { font-size: 16px; font-weight: 800; color: var(--text-primary); }
.cr-week { font-size: 12px; color: var(--text-muted); font-weight: 400; }
.cr-countdown { text-align: right; }
.cr-countdown-label { font-size: 11px; color: var(--text-muted); }
.cr-countdown-num { font-size: 20px; font-weight: 800; color: var(--brand-orange); }

/* ── 大周期进度条 ── */
.cr-bar-wrap { margin-bottom: 16px; }
.cr-bar-header { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); margin-bottom: 4px; }
.cr-bar { height: 10px; background: var(--bg-subtle); border-radius: 5px; overflow: hidden; display: flex; }
.cr-bar-seg { height: 100%; transition: all 0.3s; }

/* ── 阶段胶囊 ── */
.cr-phases {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  background: var(--bg-hover);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}
.cr-phase-btn {
  flex: 1;
  text-align: center;
  padding: 10px 2px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  border-right: 1px solid var(--border-color);
  background: transparent;
  font-family: inherit;
}
.cr-phase-btn:last-child { border-right: none; }
.cr-phase-btn:hover { background: var(--brand-orange-subtle); }
.cr-phase-btn.active-tab { background: var(--brand-orange-subtle); box-shadow: inset 0 -2px 0 var(--brand-orange); }
.cr-pb-icon { font-size: 12px; font-weight: 600; display: block; }
.cr-pb-icon.dim { color: var(--text-muted); }
.cr-pb-weeks { font-size: 9px; color: var(--text-muted); display: block; margin: 1px 0; }
.cr-pb-status { font-size: 10px; display: block; }
.cr-pb-status.active { color: var(--brand-orange); font-weight: 500; }
.cr-pb-status.completed { color: var(--color-success); font-weight: 500; }
.cr-pb-status.pending { color: var(--text-muted); }

/* ── 卡片区 ── */
.cr-cards { display: flex; gap: 8px; margin-bottom: 12px; }
.cr-sub-card { flex: 1; background: var(--bg-hover); border-radius: 10px; padding: 10px; }
.cr-sub-label { font-size: 10px; color: var(--text-muted); margin-bottom: 4px; }
.cr-sub-value { font-size: 16px; font-weight: 800; color: var(--text-primary); }
.cr-sub-value.next { font-size: 14px; }
.cr-sub-hint { font-size: 10px; color: var(--brand-orange); margin-top: 2px; }
.cr-sub-hint.cal { color: var(--text-muted); }

/* ── 说明区 ── */
.cr-desc {
  background: linear-gradient(135deg, var(--brand-orange-subtle) 0%, #1f0f0f 100%);
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid #3d2e14;
  min-height: 72px;
  transition: all 0.3s ease;
}
:root .cr-desc { background: linear-gradient(135deg, #fef7e6 0%, #fff5f5 100%); border: 1px solid #ffe8cc; }
:root.dark .cr-desc { background: linear-gradient(135deg, #1a1505 0%, #1f0f0f 100%); border: 1px solid #3d2e14; }
.cr-desc-title { font-size: 13px; font-weight: 600; color: var(--brand-orange); margin-bottom: 6px; }
.cr-desc-text { font-size: 12px; color: var(--text-secondary); line-height: 1.7; border-top: 1px solid #3d2e14; padding-top: 6px; }
:root .cr-desc-text { border-top: 1px solid #ffe8cc; }
:root.dark .cr-desc-text { border-top: 1px solid #3d2e14; }
</style>
