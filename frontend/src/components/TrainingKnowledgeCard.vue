<template>
  <div class="knowledge-card">
    <div class="knowledge-header">
      <span>📖 科学训练知识</span>
      <div class="knowledge-controls">
        <span class="slide-num">{{ currentSlide }}/{{ totalSlides }}</span>
        <span v-for="n in totalSlides" :key="n"
          class="dot" :class="{ active: currentSlide === n }"
          @click="goSlide(n)" />
      </div>
    </div>
    <div class="slides-container">
      <div class="slides-track" :style="{ transform: `translateX(-${(currentSlide - 1) * 100}%)` }">
        <!-- 第1页：PPL -->
        <div class="slide ppl-slide">
          <div class="slide-icon" style="background:linear-gradient(135deg,#f97316,#fb923c);">🏛️</div>
          <div class="slide-title-row">
            <span class="slide-title">PPL 三分化训练</span>
            <span class="slide-tag">推 · 拉 · 腿</span>
          </div>
          <p class="slide-text">
            本系统基于 <strong>PPL（Push / Pull / Legs）</strong> 三分化科学训练法——将训练日分为推力、拉力、腿部三个模块，每个模块针对特定肌群，确保每周每个部位得到足量刺激和充分恢复。
          </p>
          <div class="ppl-grid">
            <div class="ppl-cell">
              <span class="ppl-emoji">💥</span>
              <span class="ppl-name">Push</span>
              <span class="ppl-detail">推力 · 胸肩三头</span>
            </div>
            <div class="ppl-cell">
              <span class="ppl-emoji">🏋️</span>
              <span class="ppl-name">Pull</span>
              <span class="ppl-detail">拉力 · 背和二头</span>
            </div>
            <div class="ppl-cell">
              <span class="ppl-emoji">🦵</span>
              <span class="ppl-name">Legs</span>
              <span class="ppl-detail">腿部 · 臀腿核心</span>
            </div>
          </div>
        </div>
        <!-- 第2页：周期化 -->
        <div class="slide period-slide">
          <div class="slide-icon" style="background:linear-gradient(135deg,#f97316,#fb923c);">🔄</div>
          <div class="slide-title-row">
            <span class="slide-title">周期化训练</span>
            <span class="slide-tag">四个阶段</span>
          </div>
          <p class="slide-text">
            本系统采用 <strong>线性周期化</strong> 模型，将一个训练大周期分为四个循序渐进的阶段，每个阶段针对不同的训练适应目标，科学安排训练量与强度，避免平台期和过度训练。
          </p>
          <div class="period-grid">
            <div class="period-cell">
              <span class="period-emoji">🌱</span>
              <span class="period-name">基础适应期</span>
              <span class="period-detail">低强度高容量，为后续阶段打基础</span>
            </div>
            <div class="period-cell">
              <span class="period-emoji">🔥</span>
              <span class="period-name">肌肥大期</span>
              <span class="period-detail">中等重量高次数，最大化增长</span>
            </div>
            <div class="period-cell">
              <span class="period-emoji">💪</span>
              <span class="period-name">力量提升期</span>
              <span class="period-detail">大重量低次数，神经募集最大化</span>
            </div>
            <div class="period-cell">
              <span class="period-emoji">🔄</span>
              <span class="period-name">减载恢复周</span>
              <span class="period-detail">降低训练量，主动恢复储能</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const totalSlides = 2
const currentSlide = ref(1)
let timer: ReturnType<typeof setInterval> | null = null

function goSlide(n: number) { currentSlide.value = n }

onMounted(() => {
  timer = setInterval(() => {
    currentSlide.value = currentSlide.value >= totalSlides ? 1 : currentSlide.value + 1
  }, 5000)
})

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.knowledge-card {
  background: var(--bg-card);
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: var(--shadow-card);
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}
.knowledge-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 14px;
}
.knowledge-controls {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}
.slide-num {
  font-size: 12px;
  color: var(--brand-orange);
  font-weight: 600;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--border-color);
  cursor: pointer;
  transition: background 0.2s;
}
.dot.active { background: var(--brand-orange); }

.slides-container { overflow: hidden; border-radius: 10px; }
.slides-track { display: flex; transition: transform 0.4s ease; }

.slide {
  min-width: 100%;
  padding: 16px;
  border-radius: 10px;
  box-sizing: border-box;
}
.slide { background: var(--brand-orange-subtle); border: 1px solid #3d2e14; }
:root .slide { background: #fffcf5; border: 1px solid #fde68a; }
:root.dark .slide { background: var(--brand-orange-subtle); border: 1px solid #3d2e14; }

.slide-icon {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; margin-bottom: 10px;
}
.slide-title-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.slide-title { font-size: 14px; font-weight: 700; color: var(--text-primary); }
.slide-tag {
  font-size: 12px; font-weight: 600; padding: 2px 8px;
  border-radius: 4px; color: var(--brand-orange); background: var(--brand-orange-subtle);
}
.slide-text {
  font-size: 13px; color: var(--text-secondary); line-height: 1.7;
  margin: 0 0 12px;
}

.ppl-grid, .period-grid {
  display: grid;
  gap: 6px;
}
.ppl-grid { grid-template-columns: 1fr 1fr 1fr; }
.period-grid { grid-template-columns: 1fr 1fr; }

.ppl-cell {
  background: var(--brand-orange-subtle); border-radius: 8px; padding: 8px 6px;
  text-align: center; border: 1px solid #3d2e14;
}
:root .ppl-cell { border: 1px solid #fde68a; }
:root.dark .ppl-cell { border: 1px solid #3d2e14; }
.ppl-emoji { font-size: 18px; display: block; margin-bottom: 2px; }
.ppl-name { font-size: 13px; font-weight: 700; color: var(--text-primary); display: block; }
.ppl-detail { font-size: 12px; color: var(--text-muted); display: block; margin-top: 1px; }

.period-cell {
  background: var(--brand-orange-subtle); border-radius: 8px; padding: 8px 10px;
  border: 1px solid #3d2e14;
}
:root .period-cell { border: 1px solid #fde68a; }
:root.dark .period-cell { border: 1px solid #3d2e14; }
.period-emoji { font-size: 16px; display: block; margin-bottom: 2px; }
.period-name { font-size: 13px; font-weight: 700; color: var(--text-primary); display: block; }
.period-detail { font-size: 12px; color: var(--text-muted); display: block; margin-top: 1px; }
</style>
