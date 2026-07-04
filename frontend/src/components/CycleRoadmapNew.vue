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
        pieces.push({ width: (fullyDone / total * 100) + '%', bg: seg.color, radius: '' })
      }
      // 当前周：半透明显示"进行中"
      pieces.push({ width: (inProgress / total * 100) + '%', bg: seg.color + '40', radius: '' })
      if (remaining > 0) {
        pieces.push({ width: (remaining / total * 100) + '%', bg: '#e8e8e8', radius: '' })
      }
    } else {
      pieces.push({
        width: (seg.weekCount / total * 100) + '%',
        bg: seg.status === 'completed' ? seg.color : '#e8e8e8',
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
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

/* ── 第1行：我在哪 + 倒计时 ── */
.cr-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.cr-phase { display: flex; align-items: center; gap: 6px; }
.cr-icon { font-size: 22px; }
.cr-name { font-size: 16px; font-weight: 800; color: #1a1a1a; }
.cr-week { font-size: 12px; color: #888; font-weight: 400; }
.cr-countdown { text-align: right; }
.cr-countdown-label { font-size: 11px; color: #888; }
.cr-countdown-num { font-size: 20px; font-weight: 800; color: #f97316; }

/* ── 大周期进度条 ── */
.cr-bar-wrap { margin-bottom: 16px; }
.cr-bar-header { display: flex; justify-content: space-between; font-size: 11px; color: #888; margin-bottom: 4px; }
.cr-bar { height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden; display: flex; }
.cr-bar-seg { height: 100%; transition: all 0.3s; }

/* ── 阶段胶囊 ── */
.cr-phases {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #eee;
}
.cr-phase-btn {
  flex: 1;
  text-align: center;
  padding: 10px 2px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  border-right: 1px solid #eee;
  background: transparent;
  font-family: inherit;
}
.cr-phase-btn:last-child { border-right: none; }
.cr-phase-btn:hover { background: #fff7ed; }
.cr-phase-btn.active-tab { background: #fff7ed; box-shadow: inset 0 -2px 0 #f97316; }
.cr-pb-icon { font-size: 12px; font-weight: 600; display: block; }
.cr-pb-icon.dim { color: #999; }
.cr-pb-weeks { font-size: 9px; color: #888; display: block; margin: 1px 0; }
.cr-pb-status { font-size: 10px; display: block; }
.cr-pb-status.active { color: #f97316; font-weight: 500; }
.cr-pb-status.completed { color: #22c55e; font-weight: 500; }
.cr-pb-status.pending { color: #bbb; }

/* ── 卡片区 ── */
.cr-cards { display: flex; gap: 8px; margin-bottom: 12px; }
.cr-sub-card { flex: 1; background: #f9f9f9; border-radius: 10px; padding: 10px; }
.cr-sub-label { font-size: 10px; color: #888; margin-bottom: 4px; }
.cr-sub-value { font-size: 16px; font-weight: 800; color: #1a1a1a; }
.cr-sub-value.next { font-size: 14px; }
.cr-sub-hint { font-size: 10px; color: #f97316; margin-top: 2px; }
.cr-sub-hint.cal { color: #888; }

/* ── 说明区 ── */
.cr-desc {
  background: linear-gradient(135deg, #fef7e6 0%, #fff5f5 100%);
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid #ffe8cc;
  min-height: 72px;
  transition: all 0.3s ease;
}
.cr-desc-title { font-size: 13px; font-weight: 600; color: #d97706; margin-bottom: 6px; }
.cr-desc-text { font-size: 12px; color: #555; line-height: 1.7; border-top: 1px solid #ffe8cc; padding-top: 6px; }
</style>
