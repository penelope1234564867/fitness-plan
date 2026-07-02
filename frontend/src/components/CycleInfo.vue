<template>
  <div class="week-progress">
    <div class="wp-top">
      <div class="wp-phase">
        <span class="wp-phase-icon">{{ phaseIcon }}</span>
        <span class="wp-phase-label">{{ phaseLabel }}</span>
        <span class="wp-week-info">· 第{{ weekNumber }}周/共{{ totalWeeks }}周</span>
      </div>
      <span class="wp-pct">{{ completionRate }}%</span>
    </div>

    <div class="wp-bar">
      <div class="wp-bar-bg">
        <div class="wp-bar-fill" :style="{ width: completionRate + '%' }" />
      </div>
    </div>

    <div class="wp-bottom">
      <div class="wp-stats">
        <span class="wp-stat">📋 本周 {{ completedDays }}/{{ totalDays }} 天已完成</span>
        <span v-if="nextPhase" class="wp-next">下一步 → {{ nextPhase }}</span>
      </div>
      <button
        class="wp-generate-btn"
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
import { computed } from 'vue'

const props = defineProps<{
  phaseLabel: string
  weekNumber: number
  totalWeeks: number
  completionRate: number
  isWeekComplete: boolean
  completedDays: number
  totalDays: number
  nextPhase?: string
  isDeload?: boolean
}>()

defineEmits<{ generate: [] }>()

const phaseIcon = computed(() => {
  if (props.isDeload) return '🔄'
  const map: Record<string, string> = {
    '基础适应期': '🌱', '肌肥大期': '🔥', '燃脂强化期': '🔥',
    '塑形雕刻期': '✨', '综合维持期': '💪', '力量提升期': '💪',
    '代谢提升期': '⚡', '紧致提升期': '💎', '活跃恢复期': '🧘',
  }
  return map[props.phaseLabel] ?? '💪'
})
</script>

<style scoped>
.week-progress {
  background: #fff;
  border-radius: 16px;
  padding: 16px 18px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
.wp-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.wp-phase { display: flex; align-items: center; gap: 6px; }
.wp-phase-icon { font-size: 18px; }
.wp-phase-label { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.wp-week-info { font-size: 12px; color: #888; font-weight: 400; }
.wp-pct { font-size: 18px; font-weight: 800; color: #1a1a1a; }
.wp-bar { margin-bottom: 12px; }
.wp-bar-bg { height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden; }
.wp-bar-fill { height: 100%; border-radius: 5px; background: linear-gradient(90deg, #f97316, #fb923c); transition: width 0.5s ease; }
.wp-bottom { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.wp-stats { display: flex; flex-direction: column; gap: 2px; }
.wp-stat { font-size: 12px; color: #888; }
.wp-next { font-size: 11px; color: #f97316; font-weight: 500; }
.wp-generate-btn { padding: 7px 18px; border-radius: 20px; border: none; font-size: 13px; font-weight: 600; cursor: pointer; background: linear-gradient(135deg, #f97316, #fb923c); color: #fff; transition: all 0.2s; white-space: nowrap; flex-shrink: 0; }
.wp-generate-btn:hover:not(:disabled) { box-shadow: 0 4px 12px rgba(249,115,22,0.35); transform: translateY(-1px); }
.wp-generate-btn:disabled { background: #d9d9d9; color: #999; cursor: not-allowed; }
</style>
