<template>
  <div
    class="day-cell"
    :class="[status, { today: isToday, hasPlan: !!focusIcon }]"
    @click="$emit('click', date)"
  >
    <span class="day-number">{{ day }}</span>
    <span v-if="focusIcon && status !== 'rest'" class="day-icon">{{ focusIcon }}</span>
    <span v-else-if="status === 'rest'" class="day-icon rest-icon">☕</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  day: number
  date: string
  focusIcon?: string
  isToday: boolean
  status: 'rest' | 'pending' | 'partial' | 'completed' | 'missed' | 'future'
}>()

defineEmits<{ click: [date: string] }>()
</script>

<style scoped>
.day-cell {
  aspect-ratio: 1;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #fff;
  border: 1px solid transparent;
  gap: 2px;
  position: relative;
}
.day-cell:hover {
  background: #fff7ed;
  border-color: #f97316;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(249,115,22,0.15);
}

.day-cell.today {
  border-color: #f97316;
  box-shadow: 0 0 0 2px #f97316;
  font-weight: 700;
}
.day-cell.today:hover { box-shadow: 0 0 0 2px #f97316, 0 4px 12px rgba(249,115,22,0.2); }

.day-number { font-size: 14px; font-weight: 600; color: #333; line-height: 1; }
.day-icon { font-size: 16px; line-height: 1; }

.rest-icon { opacity: 0.5; font-size: 14px; }

/* 状态颜色 */
.day-cell.completed { background: #f0fdf4; }
.day-cell.completed .day-number { color: #22c55e; }
.day-cell.partial { background: #fff7ed; }
.day-cell.partial .day-number { color: #f97316; }
.day-cell.missed { background: #fef2f2; }
.day-cell.missed .day-number { color: #ef4444; }
.day-cell.future { opacity: 0.5; }
.day-cell.future:hover { opacity: 0.8; }
.day-cell.rest .day-number { color: #aaa; }

/* 没有计划的日期 */
.day-cell:not(.hasPlan):not(.today) { cursor: default; }
.day-cell:not(.hasPlan):not(.today):hover { background: #fff; border-color: transparent; transform: none; box-shadow: none; }
</style>
