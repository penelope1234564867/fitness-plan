<template>
  <div class="today-card" @click="$emit('start')">
    <div class="today-left">
      <span class="today-badge">今日</span>
      <div class="today-info">
        <span class="today-label">{{ focusLabel }}</span>
        <span class="today-desc">{{ progressText }}</span>
      </div>
    </div>
    <div class="today-right">
      <a-button type="primary" size="large" shape="round" class="start-btn" @click.stop="$emit('start')">
        {{ status === 'completed' ? '查看详情' : '开始训练' }}
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  focusLabel: string
  status: 'rest' | 'pending' | 'partial' | 'completed' | 'missed'
  progressText: string
}>()

defineEmits<{ start: [] }>()
</script>

<style scoped>
.today-card {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(135deg, #fff7ed, #fff);
  border: 2px solid #f97316;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.25s ease;
}
.today-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(249,115,22,0.2);
}
.today-left { display: flex; align-items: center; gap: 14px; }
.today-badge {
  padding: 4px 12px; border-radius: 20px;
  background: #f97316; color: #fff;
  font-size: 12px; font-weight: 700;
}
.today-info { display: flex; flex-direction: column; gap: 2px; }
.today-label { font-size: 16px; font-weight: 700; color: #1a1a1a; }
.today-desc { font-size: 13px; color: #888; }
.start-btn {
  background: linear-gradient(135deg, #f97316, #fb923c);
  border: none; box-shadow: 0 4px 12px rgba(249,115,22,0.3);
  font-weight: 600;
}
.start-btn:hover { box-shadow: 0 6px 16px rgba(249,115,22,0.4); }
</style>
