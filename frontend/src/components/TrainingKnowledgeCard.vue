<template>
  <div class="knowledge-card">
    <div class="knowledge-header">
      <span class="knowledge-title">📖 科学训练知识</span>
    </div>
    <div class="knowledge-body">
      <!-- PPL -->
      <div class="section ppl-section">
        <div class="section-top">
          <div class="section-icon" style="background:linear-gradient(135deg,#f97316,#fb923c);">🏛️</div>
          <div>
            <div class="section-title">PPL 三分化训练</div>
            <div class="section-badge">推 · 拉 · 腿</div>
          </div>
        </div>
        <p class="section-desc">基于 <strong>PPL（Push / Pull / Legs）</strong> 三分化科学训练法，将训练日分为推力、拉力、腿部三个模块。</p>
        <div class="ppl-grid">
          <div class="ppl-item"><span class="ppl-icon">💥</span><span class="ppl-name">Push 推力</span><span class="ppl-detail">胸 · 肩 · 三头</span></div>
          <div class="ppl-item"><span class="ppl-icon">🏋️</span><span class="ppl-name">Pull 拉力</span><span class="ppl-detail">背 · 二头 · 后肩</span></div>
          <div class="ppl-item"><span class="ppl-icon">🦵</span><span class="ppl-name">Legs 腿部</span><span class="ppl-detail">臀 · 腿 · 核心</span></div>
        </div>
      </div>
      <!-- 周期化 -->
      <div class="section period-section">
        <div class="section-top">
          <div class="section-icon" style="background:linear-gradient(135deg,#22c55e,#4ade80);">🔄</div>
          <div>
            <div class="section-title">周期化训练</div>
            <div class="section-badge">四个阶段</div>
          </div>
        </div>
        <p class="section-desc">采用 <strong>线性周期化</strong> 模型，分四个阶段循序渐进。</p>
        <div class="phase-grid">
          <div class="phase-item"><span class="phase-name">🌱 基础适应</span><span class="phase-desc">低强度高容量，建神经适应</span></div>
          <div class="phase-item"><span class="phase-name">🔥 肌肥大</span><span class="phase-desc">中重量高次数，肌纤维增长</span></div>
          <div class="phase-item"><span class="phase-name">💪 力量提升</span><span class="phase-desc">大重量低次数，神经募集</span></div>
          <div class="phase-item"><span class="phase-name">🔄 减载恢复</span><span class="phase-desc">降训练量，为下周期储能</span></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-card {
  background: #fff;
  border-radius: 16px;
  padding: 14px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
}
.knowledge-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}
.knowledge-title {
  font-size: 13px;
  font-weight: 700;
  color: #1a1a1a;
}
.knowledge-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.section {
  border-radius: 10px;
  padding: 10px 12px;
}
.ppl-section { background: #fffdf5; border: 1px solid #fde68a; }
.period-section { background: #fafef5; border: 1px solid #bbf7d0; }
.section-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.section-icon {
  width: 24px; height: 24px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; flex-shrink: 0;
}
.section-title { font-size: 13px; font-weight: 700; color: #1a1a1a; line-height: 1.3; }
.section-badge { font-size: 10px; font-weight: 600; }
.ppl-section .section-badge { color: #f97316; }
.period-section .section-badge { color: #16a34a; }
.section-desc { font-size: 11px; color: #555; line-height: 1.6; margin: 0 0 7px; }
.ppl-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; }
.ppl-item {
  background: #fff7ed; border-radius: 6px; padding: 5px 4px;
  text-align: center; border: 1px solid #fde68a;
}
.ppl-icon { font-size: 14px; display: block; }
.ppl-name { font-size: 11px; font-weight: 600; color: #92400e; display: block; }
.ppl-detail { font-size: 9px; color: #b88a6a; display: block; }
.phase-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
.phase-item {
  background: #f0fdf4; border-radius: 6px; padding: 5px 8px; border: 1px solid #bbf7d0;
  display: flex; flex-direction: column;
}
.phase-name { font-size: 11px; font-weight: 600; color: #16a34a; }
.phase-item .phase-desc { font-size: 9px; color: #666; margin-top: 1px; }
</style>
