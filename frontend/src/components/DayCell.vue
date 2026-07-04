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
  background: var(--bg-card);
  gap: 2px;
  position: relative;
}
.day-cell:hover { background: var(--brand-orange-subtle); }

.day-cell.today {
  border: 2px solid var(--brand-orange);
  font-weight: 700;
}

.day-number { font-size: 14px; font-weight: 600; color: var(--text-primary); line-height: 1; }
.day-icon { font-size: 16px; line-height: 1; }

.rest-icon { opacity: 0.5; font-size: 14px; }
.phase-dot { position: absolute; bottom: 2px; right: 2px; width: 5px; height: 5px; border-radius: 50%; }

/* 状态颜色（仅文字，无底色） */
.day-cell.completed .day-number { color: var(--brand-orange); }
.day-cell.partial .day-number { color: var(--brand-orange); }
.day-cell.missed .day-number { color: var(--color-error); }
.day-cell.future { opacity: 0.5; }
.day-cell.rest .day-number { color: var(--text-muted); }

/* 没有计划的日期：无边框 */
.day-cell:not(.hasPlan):not(.today) { cursor: default; }

/* ═══ 跨月日期 ═══ */
.day-cell.adjacent-month { background: transparent; }
.day-cell.adjacent-month .day-number { color: var(--text-muted); font-size: 12px; }
.day-cell.adjacent-month:hover { background: var(--brand-orange-subtle); }
.day-cell.adjacent-month.today { border: 2px solid var(--brand-orange); }
.day-cell.adjacent-month.today .day-number { color: var(--brand-orange); font-size: 14px; }
/* 非本月但有计划的日期 */
.day-cell.adjacent-month.hasPlan { background: var(--bg-subtle); }
.day-cell.adjacent-month.hasPlan .day-number { color: var(--text-secondary); }
.day-cell.adjacent-month.hasPlan:hover { background: var(--brand-orange-subtle); }
.day-cell.adjacent-month.completed .day-number { color: var(--brand-orange); }

/* ═══ 调整模式 ═══ */
.day-cell.reschedule-source {
  border-color: var(--brand-orange);
  box-shadow: 0 0 0 2px var(--brand-orange), 0 0 12px rgba(217,119,6,0.3);
  animation: pulse-source 1.5s ease-in-out infinite;
}
@keyframes pulse-source {
  0%, 100% { box-shadow: 0 0 0 2px #d97706, 0 0 12px rgba(217,119,6,0.3); }
  50% { box-shadow: 0 0 0 4px #d97706, 0 0 20px rgba(217,119,6,0.5); }
}

.day-cell.reschedule-target-available {
  background: var(--color-success-subtle);
  border-color: var(--color-success);
  cursor: pointer !important;
}
.day-cell.reschedule-target-available:hover {
  background: var(--color-success-subtle);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(22,163,74,0.25);
}

.day-cell.reschedule-target-occupied {
  opacity: 0.4;
  cursor: not-allowed !important;
}
.day-cell.reschedule-target-expired {
  opacity: 0.3;
  cursor: not-allowed !important;
  background: repeating-linear-gradient(45deg, transparent, transparent 3px, var(--bg-subtle) 3px, var(--bg-subtle) 6px);
}
.day-cell.reschedule-target-expired:hover {
  background: repeating-linear-gradient(45deg, transparent, transparent 3px, var(--bg-subtle) 3px, var(--bg-subtle) 6px);
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
  background: var(--brand-orange);
  color: #fff;
  bottom: 1px;
  top: auto;
  right: 1px;
  font-size: 7px;
  padding: 0 3px;
}
.day-cell.reschedule-target-available .reschedule-badge {
  background: var(--color-success);
  color: #fff;
}
</style>
