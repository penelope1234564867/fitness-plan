# 肌肉悬浮 tooltip 设计文档

> 日期：2026-07-01
> 状态：已定稿

---

## 概述

在肌肉分布图上增加悬浮交互：用户将鼠标悬停在人体 SVG 的某块肌肉区域时，跟随鼠标显示该肌肉的中文名称。

---

## 需求

1. 鼠标悬停在肌肉上 → 显示中文名 tooltip
2. tooltip 跟随鼠标光标移动
3. 鼠标离开肌肉 → tooltip 消失
4. 无需点击交互
5. 只显示中文名（无需英文）

---

## 实现方案

### 方案：DOM 事件注入（选用）

利用 `vue-human-muscle-anatomy` 渲染出的 SVG `<path>` 元素自带 `id` 属性（如 `id="biceps"`、`id="chest"`），在组件挂载后通过 DOM query 找到这些 path 元素，动态添加 `mouseenter`/`mousemove`/`mouseleave` 事件监听器。

### 为什么不选其他方案

| 方案 | 说明 | 结论 |
|------|------|------|
| 透明覆盖层 | 用 div 覆盖 SVG，计算各肌肉 bounding rect | ❌ 矩形区域精度差，实现复杂 |
| 提 PR 给上游 | 等上游库加 hover 事件支持 | ❌ 周期太长 |
| **DOM 事件注入** | 直接给 SVG path 加事件监听，聚焦在 `MuscleDiagram.vue` 内部 | **✅ 选用** |

---

## 详细设计

### 肌肉中文名映射表

```typescript
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

### 组件结构

```
MuscleDiagram.vue
├── .diagram-body (position: relative)     ← ref: diagramRef
│   ├── HumanAnatomy (第三方组件)
│   │   └── SVG paths (id="biceps", id="chest", ...)
│   └── .muscle-tooltip (position: absolute, v-if="hoveredMuscle")
└── <style> ...
```

### 事件绑定逻辑

```
onMounted
  → nextTick (等待 HumanAnatomy 渲染完成)
  → attachHoverListeners()
    → diagramRef.querySelectorAll('path[id]')
    → 对每个 path:
        - 跳过 MUSCLE_NAME_CN 中没有的 (如 outline)
        - path.style.cursor = 'pointer'
        - mouseenter → hoveredMuscle = MUSCLE_NAME_CN[path.id]
        - mousemove  → 计算 tooltip 在 diagram-body 内的相对坐标
        - mouseleave → hoveredMuscle = ''

MutationObserver (childList + subtree)
  → HumanAnatomy 重建时重新 attach 事件 (如 gender 切换)
```

### Tooltip 样式

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
}
```

### Tooltip 定位

- 相对于 `.diagram-body` 容器绝对定位
- X = mouse.clientX - container.left + 12（鼠标右偏）
- Y = mouse.clientY - container.top - 10（鼠标上偏）
- `pointer-events: none` 确保 tooltip 不阻挡鼠标事件

---

## 文件改动清单

| 文件 | 改动 |
|------|------|
| `frontend/src/components/MuscleDiagram.vue` | **新增** — 肌肉映射表、DOM 事件注入、tooltip UI |

**无需改动：**
- 后端：无变化
- store：无变化
- 类型定义：无变化
- 其他组件：无变化

---

## 验证方式

1. 启动前端
2. 观察左下角肌肉分布图
3. 鼠标悬浮在各肌肉上 → 跟随鼠标显示中文名
4. 移到非肌肉区域（轮廓线、背景）→ tooltip 消失
5. 鼠标在肌肉间移动 → 名称即时切换
6. 悬浮在不同肌肉（正面/背面）→ 均正常显示
