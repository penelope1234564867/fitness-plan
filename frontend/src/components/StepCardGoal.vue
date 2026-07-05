<template>
  <div class="step-card">
    <h2 class="step-title">🎯 你的健身目标</h2>
    <p class="step-desc">选一个最符合你当前需求的目标</p>

    <div class="goal-grid">
      <div
        v-for="g in goals"
        :key="g.value"
        class="goal-card"
        :class="{ active: selected === g.value }"
        @click="selected = g.value"
      >
        <span class="goal-icon">{{ g.icon }}</span>
        <span class="goal-label">{{ g.label }}</span>
        <span class="goal-desc">{{ g.desc }}</span>
      </div>
    </div>

    <div class="step-actions">
      <a-button class="back-btn" @click="$emit('prev')">上一步</a-button>
      <a-button type="primary" class="next-btn" :disabled="!selected" @click="$emit('next', selected)">
        下一步
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ data: string }>()
defineEmits<{ prev: []; next: [goal: string] }>()
const selected = ref(props.data || '')

const goals = [
  { value: '减脂', icon: '🔥', label: '减脂', desc: '降低体脂率' },
  { value: '增肌', icon: '💪', label: '增肌', desc: '增加肌肉量' },
  { value: '塑形', icon: '✨', label: '塑形', desc: '雕刻身体线条' },
  { value: '保持健康', icon: '🌿', label: '保持健康', desc: '维持运动习惯' },
]
</script>

<style scoped>
.step-card { }
.step-title { font-size: 20px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px 0; }
.step-desc { font-size: 14px; color: var(--text-muted); margin: 0 0 24px 0; }
.goal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.goal-card {
  display: flex; flex-direction: column; align-items: center; padding: 24px 12px;
  border: 1.5px solid var(--border-color); border-radius: 12px; cursor: pointer;
  transition: all 0.2s ease; background: var(--bg-card);
}
.goal-card:hover { border-color: var(--brand-orange); }
.goal-card.active { border-color: var(--brand-orange); background: var(--brand-orange-subtle); box-shadow: 0 2px 8px rgba(217,119,6,0.12); }
.goal-icon { font-size: 32px; margin-bottom: 6px; }
.goal-label { font-size: 16px; font-weight: 700; color: var(--text-primary); }
.goal-desc { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.step-actions { display: flex; gap: 12px; margin-top: 24px; }
.back-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 15px; }
.next-btn { flex: 1; height: 48px; border-radius: 12px; font-size: 16px; font-weight: 600; background: var(--brand-orange); border: none; }
.next-btn:hover { background: var(--brand-orange-deep); }
.next-btn:disabled { background: var(--bg-subtle); }
</style>
