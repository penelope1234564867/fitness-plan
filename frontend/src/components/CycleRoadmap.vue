<template>
  <div class="cycle-roadmap">
    <div class="roadmap-header">
      <span class="roadmap-title">周期路线图</span>
      <span class="roadmap-meta">大周期 · 第{{ data.currentWeekNumber }}周/共{{ data.totalWeeks }}周</span>
    </div>

    <div class="macro-progress-bar">
      <div class="macro-progress-fill" :style="{ width: macroProgressPct + '%' }" />
    </div>

    <div class="phase-track">
      <div v-for="(seg, idx) in data.mesocycles" :key="seg.phase" class="phase-segment" :class="[seg.status]">
        <div v-if="idx > 0" class="phase-connector" :class="{ completed: seg.status === 'completed' || (seg.status === 'active' && data.mesocycles[idx-1].status === 'completed') }" />
        <div class="phase-dot" :style="{ borderColor: seg.color, background: seg.status === 'active' ? seg.color : 'transparent' }">
          <span v-if="seg.status === 'completed'" class="dot-check">✓</span>
          <span v-else-if="seg.status === 'active'" class="dot-current">●</span>
        </div>
        <div class="phase-body">
          <span class="phase-label">{{ seg.label }}</span>
          <span v-if="seg.status === 'active'" class="phase-week">第{{ seg.currentWeek }}/{{ seg.weekCount }}周</span>
          <span v-else-if="seg.status === 'completed'" class="phase-pct">{{ seg.completionRate }}%</span>
          <span v-else class="phase-pending">即将到来</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RoadmapData } from '@/types'

const props = defineProps<{ data: RoadmapData }>()

const macroProgressPct = computed(() => {
  if (props.data.totalWeeks === 0) return 0
  return Math.round((props.data.currentWeekNumber / props.data.totalWeeks) * 100)
})
</script>

<style scoped>
.cycle-roadmap { background: #fff; border-radius: 14px; padding: 16px; border: 1px solid #f0f0f0; }
.roadmap-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.roadmap-title { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.roadmap-meta { font-size: 12px; color: #888; }
.macro-progress-bar { height: 6px; background: #f0f0f0; border-radius: 3px; margin-bottom: 16px; overflow: hidden; }
.macro-progress-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #3b82f6, #22c55e, #f97316, #a855f7); transition: width 0.5s ease; }
.phase-track { display: flex; flex-direction: column; gap: 4px; }
.phase-segment { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; position: relative; }
.phase-segment:not(:last-child) { border-bottom: 1px solid #f5f5f5; }
.phase-dot { width: 22px; height: 22px; border-radius: 50%; border: 2.5px solid #ddd; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 12px; margin-top: 2px; transition: all 0.3s; }
.phase-segment.completed .phase-dot { border-color: #22c55e; background: #22c55e; }
.dot-check { color: #fff; font-weight: 700; }
.dot-current { color: #fff; font-size: 10px; }
.phase-body { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.phase-label { font-size: 14px; font-weight: 600; color: #333; }
.phase-week { font-size: 12px; color: #f97316; font-weight: 500; }
.phase-pct { font-size: 12px; color: #22c55e; font-weight: 500; }
.phase-pending { font-size: 12px; color: #bbb; }
.phase-segment.pending .phase-label { color: #bbb; }
.phase-segment.active .phase-label { color: #1a1a1a; }
</style>
