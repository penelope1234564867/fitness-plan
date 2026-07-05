# 周期路线图整合组件 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ProfilePage 右侧 3 个冗余组件合并为 1 个整合组件，支持按目标切换不同文案

**Architecture:** 新建 CycleRoadmapNew.vue 替代 CycleRoadmap + PhaseDetail + PhaseVerticalList。通过 props 接收 RoadmapData 和 goal，内部实现 5 个信息块。说明文案按 goal 索引，点击阶段胶囊切换。

**Tech Stack:** Vue 3 + TypeScript + Pinia

**Global Constraints:**
- 不改后端数据模型（macrocycle.goal + mesocycle.phase 已够用）
- 不改 MainPage 布局
- 说明文案全部用大白话，不加专业术语

---

### Task 1: 补充 PHASE_DESCRIPTIONS 数据

**Files:**
- Modify: `frontend/src/types/index.ts` — 在 PHASE_COLORS 后面追加 PHASE_DESCRIPTIONS 常量

**Interfaces:**
- Consumes: 已有的 `PHASE_LABEL_MAP` 结构（目标→阶段名映射）
- Produces: `PHASE_DESCRIPTIONS` 常量，`Record<string, Record<string, { title: string; desc: string }>>`

- [ ] **Step 1: 打开 types/index.ts，定位到 PHASE_COLORS 后面**

- [ ] **Step 2: 追加 PHASE_DESCRIPTIONS 数据**

在 `export const PHASE_COLORS` 后面，添加：

```typescript
/** 各目标各阶段的大白话说明（做什么 + 达到什么目标） */
export const PHASE_DESCRIPTIONS: Record<string, Record<string, { title: string; description: string }>> = {
  '增肌': {
    foundational: { title: '🤔 这个阶段练什么？', description: '用比较轻的重量先把动作学标准，重点练深蹲、卧推这些基础动作。这个阶段不用着急上大重量，先把姿势练对，以后的训练才能不受伤、效果更好。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '用中等重量每组做 8-12 下，做到最后几下感觉吃力就对了。这样能给肌肉足够的刺激，让它变大变厚。每次要尝试比上周多做一下或者多加一点点重量，才能持续进步。' },
    strength: { title: '🤔 这个阶段练什么？', description: '加重重量减少次数，每组做 4-6 下。目标是让神经更高效地调动肌肉，举起更重的重量。这阶段练出来的不只是肌肉，更是实打实的力量增长。' },
    deload: { title: '🤔 这个阶段练什么？', description: '重量减轻一半，运动量也减少，让身体彻底恢复。连续练了几个月，身体和神经都很疲劳。这一周就是让身体「充充电」，休息好了下一轮才能练得更好。' },
  },
  '减脂': {
    foundational: { title: '🤔 这个阶段练什么？', description: '用比较轻的重量先把动作学标准，重点练深蹲、卧推这些基础动作。这个阶段即使吃得少一点，身体也能同时长肌肉和减脂肪。先把姿势练对，后面才能全力燃脂。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '用中等偏重的重量每组做 8-12 下，配合有氧运动。这样可以一边消耗热量一边给肌肉足够的刺激，不会因为少吃而掉肌肉。这个阶段最关键的是多吃蛋白质（肉蛋奶），才能保住练出来的肌肉。' },
    strength: { title: '🤔 这个阶段练什么？', description: '一周里有几天练重一点、有几天练轻一点，配合高强度间歇运动来突破瓶颈。如果减脂速度变慢了，这就说明身体适应了，需要通过变化来重新激活代谢。太累的时候可以安排一两天正常吃饭补充能量。' },
    deload: { title: '🤔 这个阶段练什么？', description: '运动量减半，重量也减轻，让身体彻底放松恢复。连续减脂好几个月，身体和神经都很疲劳。这一周就是让身体「充充电」，休息好了下一轮减脂效果才会更好。' },
  },
  '塑形': {
    foundational: { title: '🤔 这个阶段练什么？', description: '用比较轻的重量先把动作学标准，把全身各部位都练一遍。这个阶段重点是找到肌肉发力的感觉，为后续的雕刻塑形打好基础。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '中等重量每组做 10-15 下，重点打磨肩部、背部、臀腿这些部位。目标是让肌肉线条更好看，体态更挺拔。注意动作质量比重量更重要。' },
    strength: { title: '🤔 这个阶段练什么？', description: '增加训练强度，复合动作和孤立动作搭配练。这个阶段要练出全身的紧致感，让肌肉轮廓更明显，皮肤看起来更紧实有弹性。' },
    deload: { title: '🤔 这个阶段练什么？', description: '运动量减半，重点是拉伸和放松。让肌肉和关节好好恢复，下一轮练起来效果更好。' },
  },
  '保持健康': {
    foundational: { title: '🤔 这个阶段练什么？', description: '从最简单的运动开始，主要以适应为主。不用追求强度，重点是让身体养成规律运动的习惯。每周练 2-3 次比一次练很猛更重要。' },
    hypertrophy: { title: '🤔 这个阶段练什么？', description: '保持中等强度的训练，全身各部位都练到。这个阶段不求突破，主要是维持现有的力量和体能水平，让运动成为生活的一部分。' },
    strength: { title: '🤔 这个阶段练什么？', description: '以轻松愉快的运动为主，增加一些户外活动和有氧运动。保持身体活跃度，享受运动带来的好心情，不给自己太大压力。' },
    deload: { title: '🤔 这个阶段练什么？', description: '减少运动量，做一些简单的拉伸和散步。让身体休息一下，为下一轮训练做准备。' },
  },
}
```

- [ ] **Step 3: 验证编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: 没有类型错误（PHASE_DESCRIPTIONS 类型与 PHASE_LABEL_MAP 兼容）

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add PHASE_DESCRIPTIONS for 4 goals x 4 phases in plain Chinese"
```

---

### Task 2: 新建 CycleRoadmapNew.vue 整合组件

**Files:**
- Create: `frontend/src/components/CycleRoadmapNew.vue`

**Interfaces:**
- Consumes: `PHASE_COLORS`、`PHASE_DESCRIPTIONS`（来自 types）、`RoadmapData` 类型（已在 types 中）
- Props: `data: RoadmapData`, `goal: string`, `completedDays: number`, `totalDays: number`, `nextPhaseLabel?: string`

- [ ] **Step 1: 创建整合组件文件**

完整组件代码：

```vue
<template>
  <div class="cycle-roadmap-new">
    <!-- 第1行：我在哪 + 倒计时 -->
    <div class="cr-top">
      <div class="cr-phase">
        <span class="cr-icon">{{ activePhaseIcon }}</span>
        <span class="cr-name">{{ activePhaseLabel }}</span>
        <span class="cr-week">第 {{ data.currentWeekNumber }}/{{ data.totalWeeks }} 周</span>
      </div>
      <div class="cr-countdown">
        <div class="cr-countdown-label">⏳ 剩余</div>
        <div class="cr-countdown-num">{{ remainingWeeks }} 周</div>
      </div>
    </div>

    <!-- 大周期进度条 -->
    <div class="cr-bar-wrap">
      <div class="cr-bar-header">
        <span>📊 大周期进度</span>
        <span>{{ data.currentWeekNumber }}/{{ data.totalWeeks }}</span>
      </div>
      <div class="cr-bar">
        <div
          v-for="(seg, idx) in data.mesocycles"
          :key="seg.phase"
          class="cr-bar-seg"
          :class="{ active: seg.status === 'active', completed: seg.status === 'completed' }"
          :style="{
            width: (seg.weekCount / data.totalWeeks) * 100 + '%',
            background: seg.status === 'pending' ? '#e8e8e8' : seg.color,
            borderRadius:
              idx === 0 ? '5px 0 0 5px' :
              idx === data.mesocycles.length - 1 ? '0 5px 5px 0' : '0',
          }"
        />
      </div>
    </div>

    <!-- 阶段时间线（可点击胶囊） -->
    <div class="cr-phases">
      <button
        v-for="(seg, idx) in data.mesocycles"
        :key="seg.phase"
        class="cr-phase-btn"
        :class="{
          'active-tab': activeTab === seg.phase,
          'is-active': seg.status === 'active',
          'is-completed': seg.status === 'completed',
          'is-pending': seg.status === 'pending',
        }"
        :style="{
          borderRadius:
            idx === 0 ? '8px 0 0 8px' :
            idx === data.mesocycles.length - 1 ? '0 8px 8px 0' : '0',
        }"
        @click="selectPhase(seg.phase)"
      >
        <span class="cr-pb-icon" :class="{ dim: seg.status === 'pending' }">
          {{ phaseIcon(seg.phase) }} {{ seg.label }}
        </span>
        <span class="cr-pb-weeks">{{ seg.weekCount }} 周</span>
        <span class="cr-pb-status" :class="seg.status">
          <template v-if="seg.status === 'completed'">✅ 已完成</template>
          <template v-else-if="seg.status === 'active'">◉ 第{{ seg.currentWeek }}/{{ seg.weekCount }}周</template>
          <template v-else>即将到来</template>
        </span>
      </button>
    </div>

    <!-- 本周训练 + 下一阶段 -->
    <div class="cr-cards">
      <div class="cr-sub-card">
        <div class="cr-sub-label">✅ 本周训练</div>
        <div class="cr-sub-value">{{ completedDays }}/{{ totalDays }}</div>
        <div class="cr-sub-hint">{{ totalDays - completedDays > 0 ? '还剩 ' + (totalDays - completedDays) + ' 天' : '全部完成 🎉' }}</div>
      </div>
      <div class="cr-sub-card">
        <div class="cr-sub-label">🧭 下一阶段</div>
        <div class="cr-sub-value next">{{ nextPhaseLabel || '即将完成 🎉' }}</div>
        <div v-if="nextPhaseLabel" class="cr-sub-hint estimate">{{ nextPhaseEstimate }}</div>
      </div>
    </div>

    <!-- 阶段说明区（点击切换） -->
    <div class="cr-desc">
      <div class="cr-desc-title">{{ currentDescription.title }}</div>
      <div class="cr-desc-text">{{ currentDescription.description }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { RoadmapData } from '@/types'
import { PHASE_DESCRIPTIONS, PHASE_LABEL_MAP } from '@/types'

const props = defineProps<{
  data: RoadmapData
  goal: string
  completedDays: number
  totalDays: number
  nextPhaseLabel?: string
}>()

// 当前激活的阶段（默认选中当前进行中的阶段）
const activeTab = ref<string>(props.data.mesocycles.find(s => s.status === 'active')?.phase ?? props.data.mesocycles[0]?.phase ?? '')

const phaseIcons: Record<string, string> = {
  foundational: '🌱',
  hypertrophy: '🔥',
  strength: '💪',
  deload: '🔄',
}

function phaseIcon(phase: string): string {
  return phaseIcons[phase] ?? '💪'
}

/** 当前选中的阶段的数据 */
const selectedSegment = computed(() =>
  props.data.mesocycles.find(s => s.phase === activeTab.value) ?? props.data.mesocycles[0],
)

/** 当前选中阶段的图标 */
const activePhaseIcon = computed(() => phaseIcon(activeTab.value))

/** 当前选中阶段的显示名 */
const activePhaseLabel = computed(() => {
  const seg = selectedSegment.value
  const labels = PHASE_LABEL_MAP[props.goal] || PHASE_LABEL_MAP['增肌']
  return labels[seg.phase] || seg.label
})

/** 当前阶段的剩余周数 */
const remainingWeeks = computed(() => {
  const seg = selectedSegment.value
  if (seg.status === 'pending') return seg.weekCount
  if (seg.status === 'completed') return 0
  return (seg.weekCount - (seg.currentWeek ?? 1)) + 1
})

/** 阶段说明文案 */
const currentDescription = computed(() => {
  const goal = props.goal || '增肌'
  const phase = activeTab.value || 'foundational'
  const descMap = PHASE_DESCRIPTIONS[goal] || PHASE_DESCRIPTIONS['增肌']
  return descMap[phase] ?? descMap['foundational']
})

/** 下一阶段预计开始时间 */
const nextPhaseEstimate = computed(() => {
  const activeSeg = props.data.mesocycles.find(s => s.status === 'active')
  if (!activeSeg) return ''
  const remaining = (activeSeg.weekCount - (activeSeg.currentWeek ?? 1)) + 1
  if (remaining <= 1) return '下周开始'
  return `约 ${remaining} 周后`
})

function selectPhase(phase: string) {
  activeTab.value = phase
}
</script>

<style scoped>
.cycle-roadmap-new {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

/* 第1行 */
.cr-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.cr-phase { display: flex; align-items: center; gap: 6px; }
.cr-icon { font-size: 22px; }
.cr-name { font-size: 16px; font-weight: 800; color: #1a1a1a; }
.cr-week { font-size: 12px; color: #888; font-weight: 400; }
.cr-countdown { text-align: right; }
.cr-countdown-label { font-size: 11px; color: #888; }
.cr-countdown-num { font-size: 20px; font-weight: 800; color: #f97316; }

/* 大周期进度条 */
.cr-bar-wrap { margin-bottom: 16px; }
.cr-bar-header { display: flex; justify-content: space-between; font-size: 11px; color: #888; margin-bottom: 4px; }
.cr-bar { height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden; display: flex; }
.cr-bar-seg { height: 100%; transition: all 0.3s; }
.cr-bar-seg.completed { opacity: 1; }
.cr-bar-seg.active { opacity: 1; }

/* 阶段胶囊 */
.cr-phases { display: flex; gap: 0; margin-bottom: 16px; background: #fafafa; border-radius: 8px; overflow: hidden; border: 1px solid #eee; }
.cr-phase-btn { flex: 1; text-align: center; padding: 10px 2px; cursor: pointer; transition: all 0.2s; border: none; background: transparent; font-family: inherit; border-right: 1px solid #eee; }
.cr-phase-btn:last-child { border-right: none; }
.cr-phase-btn:hover { background: #fff7ed; }
.cr-phase-btn.active-tab { background: #fff7ed; box-shadow: inset 0 -2px 0 #f97316; }
.cr-pb-icon { font-size: 12px; font-weight: 600; display: block; }
.cr-pb-icon.dim { color: #999; }
.cr-pb-weeks { font-size: 9px; color: #888; display: block; margin: 1px 0; }
.cr-pb-status { font-size: 10px; display: block; }
.cr-pb-status.active { color: #f97316; font-weight: 500; }
.cr-pb-status.completed { color: #22c55e; font-weight: 500; }
.cr-pb-status.pending { color: #bbb; }

/* 卡片区 */
.cr-cards { display: flex; gap: 8px; margin-bottom: 12px; }
.cr-sub-card { flex: 1; background: #f9f9f9; border-radius: 10px; padding: 10px; }
.cr-sub-label { font-size: 10px; color: #888; margin-bottom: 4px; }
.cr-sub-value { font-size: 16px; font-weight: 800; color: #1a1a1a; }
.cr-sub-value.next { font-size: 14px; }
.cr-sub-hint { font-size: 10px; color: #f97316; margin-top: 2px; }
.cr-sub-hint.estimate { color: #888; }

/* 说明区 */
.cr-desc {
  background: linear-gradient(135deg, #fef7e6 0%, #fff5f5 100%);
  border-radius: 10px;
  padding: 12px 14px;
  border: 1px solid #ffe8cc;
  min-height: 72px;
  transition: all 0.3s ease;
}
.cr-desc-title { font-size: 13px; font-weight: 600; color: #d97706; margin-bottom: 6px; }
.cr-desc-text { font-size: 12px; color: #555; line-height: 1.7; border-top: 1px solid #ffe8cc; padding-top: 6px; }
</style>
```

- [ ] **Step 2: 验证文件创建成功**

```bash
ls -la frontend/src/components/CycleRoadmapNew.vue
```

Expected: 文件存在，非空

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CycleRoadmapNew.vue
git commit -m "feat: add CycleRoadmapNew consolidated component"
```

---

### Task 3: 修改 ProfilePage.vue

**Files:**
- Modify: `frontend/src/views/ProfilePage.vue`

- [ ] **Step 1: 替换 import 和 template**

将：
```vue
import CycleRoadmap from '@/components/CycleRoadmap.vue'
import PhaseDetail from '@/components/PhaseDetail.vue'
import PhaseVerticalList from '@/components/PhaseVerticalList.vue'
```

改为：
```vue
import CycleRoadmapNew from '@/components/CycleRoadmapNew.vue'
```

将 template 中：
```vue
<template v-if="cycleStore.roadmapData">
  <CycleRoadmap :data="cycleStore.roadmapData" />
  <PhaseDetail
    :phase-label="cycleStore.mesocyclePhaseLabel || ''"
    :phase-description="phaseDescription"
    :color="currentPhaseColor"
    :completion-rate="cycleStore.weekCompletionRate"
    :week-number="cycleStore.currentWeekNumber"
    :total-weeks="cycleStore.mesocycleTotalWeeks"
    :completed-days="completedDays"
    :total-days="totalDays"
    :next-phase="cycleStore.nextPhaseLabel ?? undefined"
  />
  <PhaseVerticalList :segments="cycleStore.roadmapData.mesocycles" />
</template>
```

替换为：
```vue
<template v-if="cycleStore.roadmapData">
  <CycleRoadmapNew
    :data="cycleStore.roadmapData"
    :goal="cycleStore.macrocycle?.goal || '增肌'"
    :completed-days="completedDays"
    :total-days="totalDays"
    :next-phase-label="cycleStore.nextPhaseLabel ?? undefined"
  />
</template>
```

- [ ] **Step 2: 删除不再需要的 computed**

在 script 中，删除不再使用的：
```typescript
const currentPhaseColor = computed(() => { ... })
const phaseDescription = computed(() => { ... })
```

这些已经被整合组件自己处理了。

- [ ] **Step 3: 验证编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: 没有类型错误

- [ ] **Step 4: 确认 UI 正确渲染**

启动前后端，访问 ProfilePage，确认：
1. 右侧只显示 1 个整合组件，不再有 3 个组件堆叠
2. 5 个信息块正确显示
3. 点击阶段胶囊切换说明文字
4. 说明文案与用户目标匹配

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/ProfilePage.vue
git commit -m "feat: replace 3 cycle components with CycleRoadmapNew on ProfilePage"
```

---

### Task 4: 清理旧组件文件

**Files:**
- Delete: `frontend/src/components/CycleRoadmap.vue`
- Delete: `frontend/src/components/PhaseDetail.vue`
- Delete: `frontend/src/components/PhaseVerticalList.vue`
- Delete: `frontend/src/components/CycleHistory.vue`（可选，未在其他地方引用也删除）

- [ ] **Step 1: 确认不再被引用**

```bash
cd frontend && grep -r "CycleRoadmap\|PhaseDetail\|PhaseVerticalList" src/ --include="*.vue" --include="*.ts"
```

Expected: 只出现我们刚替换的 ProfilePage.vue 中的引用（已替换为 CycleRoadmapNew）

- [ ] **Step 2: 删除旧文件**

```bash
rm frontend/src/components/CycleRoadmap.vue
rm frontend/src/components/PhaseDetail.vue
rm frontend/src/components/PhaseVerticalList.vue
```

- [ ] **Step 3: 验证编译**

```bash
cd frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: 没有报错（无引用丢失）

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove deprecated CycleRoadmap, PhaseDetail, PhaseVerticalList"
```
