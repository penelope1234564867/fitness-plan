# 肌肉悬浮 Tooltip 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 鼠标悬浮在肌肉分布图的肌肉区域时，跟随鼠标显示中文肌肉名 tooltip。

**Architecture:** 纯前端 DOM 事件注入方案。在 `MuscleDiagram.vue` 内部，组件挂载后通过 `querySelectorAll('path[id]')` 找到 SVG 肌肉路径，动态添加 `mouseenter`/`mousemove`/`mouseleave` 事件；tooltip 用绝对定位 div 跟随鼠标。

**Tech Stack:** Vue 3 + TypeScript + `vue-human-muscle-anatomy`

**涉及文件：** 仅 `frontend/src/components/MuscleDiagram.vue`

---

### Task 1: MuscleDiagram.vue 增加悬浮 tooltip

**Files:**
- Modify: `frontend/src/components/MuscleDiagram.vue`

**实现说明：** 只改这一个组件。新增三块内容：
1. 肌肉中文名映射表 `MUSCLE_NAME_CN`
2. DOM 事件注入逻辑（`attachHoverListeners` + `onMounted` + `MutationObserver`）
3. 模板 tooltip + 样式

- [ ] **Step 1: 在 `<script>` 中添加肌肉中文名映射和数据响应式变量**

在 `WGER_TO_MUSCLE_GROUP` 后面新增：

```typescript
/** SVG path id → 中文名映射（vue-human-muscle-anatomy 的肌群名 → 中文） */
const MUSCLE_NAME_CN: Record<string, string> = {
  chest:        '胸大肌',
  lats:         '背阔肌',
  traps:        '斜方肌',
  lowerBack:    '竖脊肌',
  frontDelts:   '三角肌前束',
  sideDelts:    '三角肌中束',
  rearDelts:    '三角肌后束',
  triceps:      '肱三头肌',
  biceps:       '肱二头肌',
  forearms:     '前臂',
  abs:          '腹肌',
  obliques:     '腹外斜肌',
  glutes:       '臀大肌',
  quads:        '股四头肌',
  hamstrings:   '腘绳肌',
  adductors:    '内收肌',
  abductors:    '外展肌',
  calves:       '小腿',
  neck:         '颈部',
  rotatorCuffs: '肩袖肌群',
}
```

在 `const props = defineProps<...>()` 后面、`WGER_TO_MUSCLE_GROUP` 前面新增响应式变量和 DOM 事件方法：

```typescript
// ── 悬浮 tooltip 状态 ──

const diagramRef = ref<HTMLElement | null>(null)
const hoveredMuscle = ref('')
const tooltipX = ref(0)
const tooltipY = ref(0)

/** 给 SVG 肌肉 path 绑定 hover 事件 */
function attachHoverListeners() {
  const container = diagramRef.value
  if (!container) return
  const paths = container.querySelectorAll<SVGPathElement>('path[id]')
  paths.forEach(path => {
    const id = path.id
    if (!MUSCLE_NAME_CN[id]) return
    // 避免重复绑定（MutationObserver 可能多次触发）
    if ((path as any)._muscleHoverAttached) return
    ;(path as any)._muscleHoverAttached = true

    path.style.cursor = 'pointer'
    path.addEventListener('mouseenter', () => {
      hoveredMuscle.value = MUSCLE_NAME_CN[id]
    })
    path.addEventListener('mousemove', (e: MouseEvent) => {
      const rect = container.getBoundingClientRect()
      tooltipX.value = e.clientX - rect.left + 12
      tooltipY.value = e.clientY - rect.top - 10
    })
    path.addEventListener('mouseleave', () => {
      hoveredMuscle.value = ''
    })
  })
}
```

别忘了同时新增 `onMounted` 和 `onUnmounted` 的 import（如果文件里还没有的话）。检查文件顶部是否有 `import { computed } from 'vue'` — 需要改为：

```typescript
import { computed, ref, onMounted, onUnmounted, nextTick } from 'vue'
```

- [ ] **Step 2: 在 `onMounted` 中初始化事件绑定 + MutationObserver 兜底**

在 `toGroups` 函数和 `primaryGroups`/`secondaryGroups` computed 的后面、`</script>` 之前新增：

```typescript
// ── 挂载后绑定悬浮事件 ──

onMounted(async () => {
  await nextTick()
  attachHoverListeners()
})

// HumanAnatomy 可能因 gender 切换等重建 DOM，用 MutationObserver 兜底
let observer: MutationObserver | null = null
onMounted(() => {
  if (!diagramRef.value) return
  observer = new MutationObserver(() => {
    attachHoverListeners()
  })
  observer.observe(diagramRef.value, { childList: true, subtree: true })
})
onUnmounted(() => {
  observer?.disconnect()
})
```

- [ ] **Step 3: 添加 tooltip 模板**

修改 `<template>`，在 `.diagram-body` div 内、`<HumanAnatomy />` 下方新增 tooltip：

```html
<div class="diagram-body" ref="diagramRef">
  <HumanAnatomy
    :gender="gender || 'male'"
    :selected-primary-muscle-groups="primaryGroups"
    :selected-secondary-muscle-groups="secondaryGroups"
    primary-highlight-color="#fb923c"
    secondary-highlight-color="#fdba74"
    default-muscle-color="#e5e5e5"
    background-color="#ffffff"
    :primary-opacity="0.8"
    :secondary-opacity="0.5"
  />

  <!-- 肌肉悬浮提示 -->
  <div
    v-if="hoveredMuscle"
    class="muscle-tooltip"
    :style="{
      left: tooltipX + 'px',
      top: tooltipY + 'px',
    }"
  >
    {{ hoveredMuscle }}
  </div>
</div>
```

关键点：
- `.diagram-body` 加了 `ref="diagramRef"`
- tooltip 在 `.diagram-body` 内部（利用它的 `position: relative` 做定位锚点）

- [ ] **Step 4: 添加 tooltip 样式**

在 `<style scoped>` 末尾新增：

```css
.muscle-tooltip {
  position: absolute;
  z-index: 10;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 6px;
  white-space: nowrap;
  pointer-events: none;
  transition: opacity 0.15s;
  line-height: 1.4;
}
```

同时确认 `.diagram-body` 有 `position: relative`（它已经有了 `display: flex` 等，需要追加）：

```css
.diagram-body {
  display: flex;
  justify-content: center;
  padding: 4px 0;
  overflow: hidden;
  position: relative;  /* tooltip 定位锚点 */
}
```

- [ ] **Step 5: 验证编译通过**

```bash
cd /c/Users/18194/Desktop/fitness-plan/frontend
npx vue-tsc --noEmit 2>&1 | head -20
```

Expected: 无类型错误（或仅与本次改动无关的已知错误）

- [ ] **Step 6: 提交**

```bash
cd /c/Users/18194/Desktop/fitness-plan
git add frontend/src/components/MuscleDiagram.vue
git commit -m "feat: 肌肉悬浮 tooltip - hover 显示中文名

- 新增 MUSCLE_NAME_CN 映射表（SVG path id → 中文名）
- DOM 事件注入：mouseenter/mousemove/mouseleave
- MutationObserver 兜底 DOM 重建
- tooltip 跟随鼠标 + pointer-events: none

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
