<template>
  <div
    class="day-cell"
    :class="[
      status,
      {
        today: isToday,
        selected: isSelected,
        hasPlan: !!focusIcon,
        'adjacent-month': !isCurrentMonth,
        'reschedule-source': rescheduleState === 'source',
        'reschedule-target-available': rescheduleState === 'target-available',
        'reschedule-target-occupied': rescheduleState === 'target-occupied',
        'reschedule-target-expired': rescheduleState === 'target-expired',
      },
    ]"
    @click="onClick"
  >
    <span class="day-number">{{ day }}</span>
    <span v-if="focusIcon && status !== 'rest'" class="day-icon" :title="focusLabel">{{ focusIcon }}</span>
    <span v-else-if="status === 'rest'" class="day-icon rest-icon" title="休息日">☕</span>
    <span v-if="phaseColor" class="phase-dot" :style="{ background: phaseColor }" />
    <span v-if="rescheduleState === 'target-available'" class="reschedule-badge">空闲</span>
    <span v-if="rescheduleState === 'source'" class="reschedule-badge source-badge">移动此日</span>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  day: number
  date: string
  focusIcon?: string
  focusLabel?: string
  isToday: boolean
  isCurrentMonth?: boolean
  isSelected?: boolean
  status: 'rest' | 'pending' | 'partial' | 'completed' | 'missed' | 'future'
  phaseColor?: string
  rescheduleState?: 'source' | 'target-available' | 'target-occupied' | 'target-expired'
}>()

const emit = defineEmits<{ click: [date: string] }>()

function onClick() {
  // 非本月日期，除非有训练数据，否则不可点击
  if (props.isCurrentMonth || props.focusIcon || props.status === 'completed') {
    emit('click', props.date)
  }
}
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
  gap: 2px;
  position: relative;
}
.day-cell:hover { background: #fff7ed; }

.day-cell.today {
  border: 2px solid #f97316;
  font-weight: 700;
}

.day-number { font-size: 14px; font-weight: 600; color: #333; line-height: 1; }
.day-icon { font-size: 16px; line-height: 1; }

.rest-icon { opacity: 0.5; font-size: 14px; }
.phase-dot { position: absolute; bottom: 2px; right: 2px; width: 5px; height: 5px; border-radius: 50%; }

/* 状态颜色（仅文字，无底色） */
.day-cell.completed .day-number { color: #f97316; }
.day-cell.partial .day-number { color: #f97316; }
.day-cell.missed .day-number { color: #ef4444; }
.day-cell.future { opacity: 0.5; }
.day-cell.rest .day-number { color: #aaa; }

/* 没有计划的日期：无边框 */
.day-cell:not(.hasPlan):not(.today) { cursor: default; }

/* ═══ 跨月日期 ═══ */
.day-cell.adjacent-month { background: transparent; }
.day-cell.adjacent-month .day-number { color: #bbb; font-size: 12px; }
.day-cell.adjacent-month:hover { background: #fff7ed; }
.day-cell.adjacent-month.today { border: 2px solid #f97316; }
.day-cell.adjacent-month.today .day-number { color: #f97316; font-size: 14px; }
/* 非本月但有计划的日期 */
.day-cell.adjacent-month.hasPlan { background: #f5f5f5; }
.day-cell.adjacent-month.hasPlan .day-number { color: #888; }
.day-cell.adjacent-month.hasPlan:hover { background: #fff7ed; }
.day-cell.adjacent-month.completed .day-number { color: #f97316; }

/* ═══ 调整模式 ═══ */
.day-cell.reschedule-source {
  border-color: #f97316;
  box-shadow: 0 0 0 2px #f97316, 0 0 12px rgba(249,115,22,0.3);
  animation: pulse-source 1.5s ease-in-out infinite;
}
@keyframes pulse-source {
  0%, 100% { box-shadow: 0 0 0 2px #f97316, 0 0 12px rgba(249,115,22,0.3); }
  50% { box-shadow: 0 0 0 4px #f97316, 0 0 20px rgba(249,115,22,0.5); }
}

.day-cell.reschedule-target-available {
  background: #f0fdf4;
  border-color: #22c55e;
  cursor: pointer !important;
}
.day-cell.reschedule-target-available:hover {
  background: #dcfce7;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(34,197,94,0.25);
}

.day-cell.reschedule-target-occupied {
  opacity: 0.4;
  cursor: not-allowed !important;
}
.day-cell.reschedule-target-expired {
  opacity: 0.3;
  cursor: not-allowed !important;
  background: repeating-linear-gradient(45deg, transparent, transparent 3px, #f5f5f5 3px, #f5f5f5 6px);
}
.day-cell.reschedule-target-expired:hover {
  background: repeating-linear-gradient(45deg, transparent, transparent 3px, #f5f5f5 3px, #f5f5f5 6px);
  border-color: transparent;
  transform: none;
  box-shadow: none;
}

.reschedule-badge {
  position: absolute;
  top: 1px;
  right: 1px;
  font-size: 8px;
  padding: 0 4px;
  border-radius: 6px;
  line-height: 14px;
  font-weight: 700;
  white-space: nowrap;
  pointer-events: none;
}
.reschedule-badge.source-badge {
  background: #f97316;
  color: #fff;
  bottom: 1px;
  top: auto;
  right: 1px;
  font-size: 7px;
  padding: 0 3px;
}
.day-cell.reschedule-target-available .reschedule-badge {
  background: #22c55e;
  color: #fff;
}
</style>
