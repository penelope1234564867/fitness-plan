<template>
  <div class="cycle-history">
    <h4 class="history-title">阶段完成情况</h4>
    <div class="history-list">
      <div v-for="seg in segments" :key="seg.phase" class="history-item" :class="[seg.status]">
        <span class="history-icon">{{ seg.status === 'completed' ? '✅' : seg.status === 'active' ? '⏳' : '⬜' }}</span>
        <div class="history-body">
          <div class="history-top">
            <span class="history-label">{{ seg.label }}</span>
            <span class="history-pct" :style="{ color: getPhaseColor(seg.phase, seg.color) }">
              {{ seg.status === 'completed' ? seg.completionRate + '%' : seg.status === 'active' ? '进行中' : '即将到来' }}
            </span>
          </div>
          <div class="history-weeks">
            <span v-for="w in seg.weeks" :key="w.week_number" class="week-chip" :class="weekChipClass(w)">{{ w.week_number }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PhaseSegment, WeekSummary } from '@/types'
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

defineProps<{
  segments: PhaseSegment[]
}>()

function weekChipClass(w: WeekSummary): Record<string, boolean> {
  return {
    'completed': w.status === 'completed' || (w.completion_rate ?? 0) >= 100,
    'partial': (w.completion_rate ?? 0) > 0 && (w.completion_rate ?? 0) < 100,
    'active': w.status === 'active',
  }
}
</script>

<style scoped>
.cycle-history { background: var(--bg-card); border-radius: 14px; padding: 16px; border: 1px solid var(--border-subtle); }
.history-title { font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0 0 12px 0; }
.history-list { display: flex; flex-direction: column; gap: 10px; }
.history-item { display: flex; gap: 10px; align-items: flex-start; padding: 8px; border-radius: 10px; transition: background 0.2s; }
.history-item:hover { background: var(--bg-hover); }
.history-item.pending { opacity: 0.5; }
.history-icon { font-size: 16px; line-height: 1.4; }
.history-body { flex: 1; min-width: 0; }
.history-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.history-label { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.history-pct { font-size: 12px; font-weight: 600; }
.history-weeks { display: flex; gap: 4px; flex-wrap: wrap; }
.week-chip { width: 22px; height: 22px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; background: var(--bg-subtle); color: var(--text-muted); }
.week-chip.completed { background: var(--color-success); color: #fff; }
.week-chip.partial { background: var(--brand-orange-subtle); color: var(--brand-orange); }
.week-chip.active { border: 2px solid var(--brand-orange); color: var(--brand-orange); background: var(--bg-card); }
</style>
