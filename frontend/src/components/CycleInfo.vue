<template>
  <div class="cycle-info">
    <div class="cycle-header">
      <span class="cycle-icon">🎯</span>
      <span class="cycle-phase">{{ phaseLabel }}</span>
      <span v-if="isDeload" class="deload-badge">🔄 恢复为主</span>
    </div>

    <div class="cycle-progress">
      <span class="progress-text">第{{ weekNumber }}周 / 共{{ totalWeeks }}周</span>
      <div class="progress-bar-bg">
        <div
          class="progress-bar-fill"
          :style="{ width: completionRate + '%' }"
          :class="{
            'fill-complete': completionRate >= 100,
            'fill-partial': completionRate > 0 && completionRate < 100,
          }"
        />
      </div>
      <span class="progress-pct">{{ completionRate }}%</span>
    </div>

    <div class="cycle-footer">
      <span class="checkin-hint">
        {{ isWeekComplete ? '✅ 本周训练全部完成' : `📋 已完成 ${completionRate}%` }}
      </span>
      <button
        class="generate-btn"
        :disabled="!isWeekComplete"
        :title="isWeekComplete ? '生成下周计划' : '还有训练未打卡'"
        @click="$emit('generate')"
      >
        ⚡ 生成下周
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  phaseLabel: string
  weekNumber: number
  totalWeeks: number
  completionRate: number
  isWeekComplete: boolean
  isDeload?: boolean
}>()

defineEmits<{
  generate: []
}>()
</script>

<style scoped>
.cycle-info {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.cycle-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.cycle-icon { font-size: 20px; }
.cycle-phase { font-size: 16px; font-weight: 700; color: #1a1a1a; }
.deload-badge { font-size: 11px; color: #f97316; background: #fff7ed; padding: 2px 8px; border-radius: 8px; }

.cycle-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.progress-text { font-size: 12px; color: #888; white-space: nowrap; }
.progress-bar-bg {
  flex: 1; height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden;
}
.progress-bar-fill {
  height: 100%; border-radius: 4px;
  transition: width 0.4s ease;
  background: #f97316;
}
.progress-bar-fill.fill-complete { background: #22c55e; }
.progress-bar-fill.fill-partial { background: linear-gradient(90deg, #f97316, #fb923c); }
.progress-pct { font-size: 13px; font-weight: 700; color: #1a1a1a; min-width: 32px; text-align: right; }

.cycle-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.checkin-hint { font-size: 12px; color: #888; }
.generate-btn {
  padding: 6px 16px;
  border-radius: 20px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  transition: all 0.2s;
  white-space: nowrap;
}
.generate-btn:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(249,115,22,0.35); transform: translateY(-1px); }
.generate-btn:disabled { background: #d9d9d9; color: #999; cursor: not-allowed; }
</style>
