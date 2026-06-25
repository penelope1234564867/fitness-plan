<template>
  <div class="progress-container">
    <div class="progress-card">
      <div class="progress-icon">⚡</div>
      <h3 class="progress-title">AI 正在为你生成计划</h3>

      <a-progress
        :percent="progress"
        status="active"
        :stroke-color="{
          '0%': '#f97316',
          '100%': '#22c55e',
        }"
        :stroke-width="12"
        class="progress-bar"
      />

      <p class="progress-status">{{ status }}</p>

      <div class="steps-indicator">
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="step-dot"
          :class="{ active: progress >= step.threshold, done: progress >= step.doneThreshold }"
        >
          <span class="step-check">{{ progress >= step.doneThreshold ? '✓' : i + 1 }}</span>
          <span class="step-label">{{ step.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  progress: number
  status: string
}>()

const steps = [
  { label: '分析目标', threshold: 10, doneThreshold: 30 },
  { label: '搜索动作', threshold: 30, doneThreshold: 50 },
  { label: '编排日程', threshold: 50, doneThreshold: 70 },
  { label: '生成计划', threshold: 70, doneThreshold: 90 },
  { label: '完成', threshold: 90, doneThreshold: 100 },
]
</script>

<style scoped>
.progress-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}
.progress-card {
  text-align: center;
  max-width: 480px;
  width: 100%;
  padding: 48px 32px;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08);
  animation: fadeIn 0.5s ease-out;
}
.progress-icon { font-size: 56px; margin-bottom: 16px; display: block; animation: pulse 1.5s infinite; }
.progress-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0 0 24px 0; }
.progress-bar { margin-bottom: 12px; }
.progress-status { font-size: 14px; color: #f97316; font-weight: 500; margin: 0 0 32px 0; }
.steps-indicator { display: flex; justify-content: space-between; gap: 4px; }
.step-dot { display: flex; flex-direction: column; align-items: center; gap: 6px; flex: 1; }
.step-check {
  width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; font-size: 12px; font-weight: 600;
  background: #f0f0f0; color: #ccc; transition: all 0.3s;
}
.step-dot.active .step-check { background: #f97316; color: #fff; }
.step-dot.done .step-check { background: #22c55e; color: #fff; }
.step-label { font-size: 11px; color: #999; white-space: nowrap; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
</style>
