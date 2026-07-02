<template>
  <div class="phase-detail">
    <div class="detail-header">
      <span class="detail-phase">{{ phaseLabel }}</span>
      <span v-if="phaseDescription" class="detail-badge" :style="{ background: color + '20', color }">
        {{ phaseDescription }}
      </span>
    </div>

    <div class="detail-progress">
      <div class="progress-row">
        <span class="progress-text">进度</span>
        <span class="progress-pct">{{ completionRate }}%</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill" :style="{ width: completionRate + '%', background: color }" />
      </div>
    </div>

    <div class="detail-info">
      <div class="info-item">
        <span class="info-label">当前周</span>
        <span class="info-value">{{ weekNumber }}/{{ totalWeeks }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">训练天数</span>
        <span class="info-value">{{ completedDays }}/{{ totalDays }}</span>
      </div>
      <div v-if="nextPhase" class="info-item">
        <span class="info-label">下一阶段</span>
        <span class="info-value next">→ {{ nextPhase }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  phaseLabel: string
  phaseDescription?: string
  color: string
  completionRate: number
  weekNumber: number
  totalWeeks: number
  completedDays: number
  totalDays: number
  nextPhase?: string
}>()
</script>

<style scoped>
.phase-detail { background: #fff; border-radius: 14px; padding: 16px; border: 1px solid #f0f0f0; }
.detail-header { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; }
.detail-phase { font-size: 16px; font-weight: 700; color: #1a1a1a; }
.detail-badge { font-size: 11px; padding: 2px 8px; border-radius: 8px; font-weight: 500; }
.detail-progress { margin-bottom: 14px; }
.progress-row { display: flex; justify-content: space-between; margin-bottom: 6px; }
.progress-text { font-size: 13px; color: #888; }
.progress-pct { font-size: 14px; font-weight: 700; color: #1a1a1a; }
.progress-track { height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.detail-info { display: flex; flex-direction: column; gap: 8px; }
.info-item { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #f5f5f5; }
.info-item:last-child { border-bottom: none; }
.info-label { font-size: 13px; color: #888; }
.info-value { font-size: 13px; font-weight: 600; color: #333; }
.info-value.next { color: #f97316; }
</style>
