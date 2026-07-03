<template>
  <div class="knowledge-card">
    <div class="knowledge-header">
      <span class="knowledge-title">📖 科学训练知识</span>
      <div class="knowledge-controls">
        <span class="slide-indicator">{{ currentSlide }}/{{ totalSlides }}</span>
        <span
          v-for="n in totalSlides" :key="n"
          class="dot"
          :class="{ active: currentSlide === n }"
          @click="goSlide(n)"
        />
      </div>
    </div>
    <div class="slides-container">
      <div class="slides-track" :style="{ transform: `translateX(-${(currentSlide - 1) * 100}%)` }">
        <!-- Slide 1: PPL -->
        <div class="slide">
          <div class="slide-icon-wrap" style="background:linear-gradient(135deg,#f97316,#fb923c);">
            <span>🏛️</span>
          </div>
          <div class="slide-title-row">
            <span class="slide-title">PPL 三分化训练</span>
            <span class="slide-badge">推 · 拉 · 腿</span>
          </div>
          <p class="slide-desc">
            本系统基于 <strong>PPL（Push / Pull / Legs）</strong> 三分化科学训练法——将训练日分为推力、拉力、腿部三个模块，
            每个模块针对特定肌群，确保每周每个部位得到足量刺激和充分恢复。
          </p>
          <div class="ppl-grid">
            <div class="ppl-item">
              <span class="ppl-icon">💥</span>
              <span class="ppl-name">Push 推力</span>
              <span class="ppl-detail">胸 · 肩 · 三头</span>
            </div>
            <div class="ppl-item">
              <span class="ppl-icon">🏋️</span>
              <span class="ppl-name">Pull 拉力</span>
              <span class="ppl-detail">背 · 二头 · 后肩</span>
            </div>
            <div class="ppl-item">
              <span class="ppl-icon">🦵</span>
              <span class="ppl-name">Legs 腿部</span>
              <span class="ppl-detail">臀 · 腿 · 核心</span>
            </div>
          </div>
        </div>
        <!-- Slide 2: 周期化 -->
        <div class="slide">
          <div class="slide-icon-wrap" style="background:linear-gradient(135deg,#22c55e,#4ade80);">
            <span>🔄</span>
          </div>
          <div class="slide-title-row">
            <span class="slide-title">周期化训练</span>
            <span class="slide-badge">四个阶段</span>
          </div>
          <p class="slide-desc">
            本系统采用 <strong>线性周期化</strong> 模型，将一个训练大周期分为四个循序渐进的阶段，
            每个阶段针对不同的训练适应目标，科学安排训练量与强度，避免平台期和过度训练。
          </p>
          <div class="phase-grid">
            <div class="phase-item">
              <span class="phase-icon">🌱</span>
              <span class="phase-name">基础适应期</span>
              <span class="phase-desc">建立神经适应与动作模式，低强度高容量</span>
            </div>
            <div class="phase-item">
              <span class="phase-icon">🔥</span>
              <span class="phase-name">肌肥大期</span>
              <span class="phase-desc">中等重量高次数，肌纤维横截面积最大化增长</span>
            </div>
            <div class="phase-item">
              <span class="phase-icon">💪</span>
              <span class="phase-name">力量提升期</span>
              <span class="phase-desc">大重量低次数，神经募集效率最大化</span>
            </div>
            <div class="phase-item">
              <span class="phase-icon">🔄</span>
              <span class="phase-name">减载恢复周</span>
              <span class="phase-desc">降低训练量，主动恢复，为下个周期储能</span>
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

function goSlide(n: number) {
  currentSlide.value = n
}

onMounted(() => {
  timer = setInterval(() => {
    currentSlide.value = currentSlide.value >= totalSlides ? 1 : currentSlide.value + 1
  }, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.knowledge-card {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border: 1px solid #f0f0f0;
}
.knowledge-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.knowledge-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}
.knowledge-controls {
  margin-left: auto;
  display: flex;
  gap: 6px;
  align-items: center;
}
.slide-indicator {
  font-size: 10px;
  color: #f97316;
  font-weight: 600;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e0e0e0;
  display: inline-block;
  cursor: pointer;
  transition: background 0.2s;
}
.dot.active {
  background: #f97316;
}
.slides-container {
  overflow: hidden;
  border-radius: 12px;
}
.slides-track {
  display: flex;
  transition: transform 0.4s ease;
}
.slide {
  min-width: 100%;
  padding: 14px;
  border-radius: 12px;
  box-sizing: border-box;
}
.slide:first-child {
  background: #fffdf5;
  border: 1px solid #fde68a;
}
.slide:last-child {
  background: #fafef5;
  border: 1px solid #bbf7d0;
}
.slide-icon-wrap {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-bottom: 10px;
}
.slide-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.slide-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}
.slide-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.slide:first-child .slide-badge {
  color: #f97316;
  background: #fff7ed;
}
.slide:last-child .slide-badge {
  color: #16a34a;
  background: #f0fdf4;
}
.slide-desc {
  font-size: 12px;
  color: #555;
  line-height: 1.7;
  margin: 0 0 10px;
}
.ppl-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}
.ppl-item {
  background: #fff7ed;
  border-radius: 8px;
  padding: 8px;
  text-align: center;
  border: 1px solid #fde68a;
}
.ppl-icon { font-size: 18px; display: block; margin-bottom: 2px; }
.ppl-name { font-size: 12px; font-weight: 700; color: #92400e; display: block; }
.ppl-detail { font-size: 10px; color: #b88a6a; display: block; }

.phase-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.phase-item {
  background: #f0fdf4;
  border-radius: 8px;
  padding: 8px;
  border: 1px solid #bbf7d0;
}
.phase-icon { font-size: 14px; display: block; margin-bottom: 2px; }
.phase-name { font-size: 12px; font-weight: 700; color: #16a34a; display: block; }
.phase-desc { font-size: 10px; color: #666; line-height: 1.5; display: block; margin-top: 2px; }
</style>
