<template>
  <div class="step-card">
    <h2 class="step-title">🎯 你的目标</h2>
    <p class="step-desc">你想达到什么样的效果？</p>

    <div class="goal-grid">
      <div v-for="g in goals" :key="g.value" class="goal-card" :class="{ active: localGoal === g.value }" @click="localGoal = g.value">
        <span class="goal-icon">{{ g.icon }}</span>
        <span class="goal-label">{{ g.label }}</span>
        <span class="goal-desc">{{ g.desc }}</span>
      </div>
    </div>

    <div class="step-actions">
      <a-button size="large" class="back-btn" @click="$emit('prev')">← 上一步</a-button>
      <a-button type="primary" size="large" class="next-btn" :disabled="!localGoal" @click="$emit('next', localGoal)">
        下一步
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ data: string }>()
const emit = defineEmits<{ prev: []; next: [value: string] }>()
const localGoal = ref(props.data)
const goals = [
  { value: '减脂', icon: '🔥', label: '减脂', desc: '降低体脂率' },
  { value: '增肌', icon: '💪', label: '增肌', desc: '增加肌肉量' },
  { value: '塑形', icon: '✨', label: '塑形', desc: '雕刻身体线条' },
  { value: '保持健康', icon: '🌿', label: '保持健康', desc: '维持运动习惯' },
]
</script>

<style scoped>
.step-title { font-size: 20px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px 0; }
.step-desc { font-size: 14px; color: #888; margin: 0 0 24px 0; }
.goal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.goal-card {
  display: flex; flex-direction: column; align-items: center; padding: 24px 12px;
  border: 1.5px solid #e8e8e8; border-radius: 12px; cursor: pointer;
  transition: all 0.2s ease; background: #fff;
}
.goal-card:hover { border-color: #f97316; }
.goal-card.active { border-color: #f97316; background: #fff7ed; box-shadow: 0 2px 8px rgba(249,115,22,0.12); }
.goal-icon { font-size: 32px; margin-bottom: 6px; }
.goal-label { font-size: 16px; font-weight: 700; color: #1a1a1a; }
.goal-desc { font-size: 12px; color: #999; margin-top: 2px; }
.step-actions { display: flex; gap: 12px; margin-top: 24px; }
.back-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 15px; }
.next-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 16px; font-weight: 600; background: #f97316; border: none; }
.next-btn:hover { background: #ea580c; }
.next-btn:disabled { background: #d9d9d9; }
</style>
