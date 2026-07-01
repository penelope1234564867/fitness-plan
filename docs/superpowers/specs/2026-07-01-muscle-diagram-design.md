# 肌肉分布图设计文档

> 日期：2026-07-01
> 状态：已定稿

---

## 问题

点击动作后，Drawer 里只显示文本形式的肌群名称（`Biceps brachii (肱二头肌)`），缺少直观的视觉反馈——用户无法一眼看出该动作练了身体哪个部位。

---

## 目标

在主页左下角增加一个**可交互的人体肌肉分布图**，选中动作后自动高亮对应的肌肉区域。

---

## 设计方案

### 技术选型：`@lucawahlen/vue-human-muscle-anatomy`

**候选方案对比：**

| 方案 | 说明 | 结论 |
|------|------|------|
| 手绘精细 SVG Path | 可控性高，但需要美术功底 | ❌ 无专业美工 |
| `body-highlighter` | 框架无关，零依赖，带热力图 | ❌ 多边形轮廓，视觉简单 |
| **`@lucawahlen/vue-human-muscle-anatomy`** | **Vue 3 原生、TS 支持、男/女模型、手绘风格 SVG** | **✅ 选用** |

**选用理由：**
- Vue 3 + TypeScript 原生支持，与项目技术栈完全匹配
- 内置男/女两种人体模型（MuscleWiki 风格）
- 支持 primary / secondary 两组高亮（颜色 + 透明度可调）
- 零外部依赖，轻量
- 高亮效果美观（橙色系配色 + 透明度叠加）

---

### 布局位置

MainPage 左侧栏（`left-column`），在 CycleInfo 下方：

```
┌────────────────┐
│  CalendarPanel  │
├────────────────┤
│   CycleInfo     │
├────────────────┤
│ MuscleDiagram   │  ← 新增
│ [自动识别正/背面] │
│  人体 SVG 图     │
│  图例/肌肉名     │
└────────────────┘
```

---

### 数据流

```
用户点击动作 → ExerciseDrawer 打开
  → fetchExerciseDetail(wgerId) 调 wger API
    → 返回 primary_muscles / secondary_muscles（带 wger 肌肉 ID）
  → 写入 workoutStore.activePrimaryMuscles / activeSecondaryMuscles
    → MuscleDiagram 响应式更新
      → 根据 wger ID → vue-human-muscle-anatomy 肌群名映射表
      → 调用 HumanAnatomy 组件的 selectedPrimaryMuscleGroups / selectedSecondaryMuscleGroups
```

---

### wger ID 映射表

wger 的肌肉 ID 需要映射到 `vue-human-muscle-anatomy` 的肌群名：

| wger ID | 肌肉 | 中文 | `vue-human-muscle-anatomy` 映射 |
|---------|------|------|-------------------------------|
| 1 | Biceps brachii | 肱二头肌 | `biceps` |
| 2 | Deltoid (前束) | 三角肌前束 | `frontDelts` |
| 2 | Deltoid (后束) | 三角肌后束 | `rearDelts` |
| 3 | Erector spinae | 竖脊肌 | `lowerBack` |
| 4 | Pectoralis major | 胸大肌 | `chest` |
| 5 | Triceps brachii | 肱三头肌 | `triceps` |
| 6 | Rectus abdominis | 腹肌 | `abs` |
| 8 | Gluteus maximus | 臀大肌 | `glutes` |
| 9 | Trapezius | 斜方肌 | `traps` |
| 10 | Quadriceps | 股四头肌 | `quads` |
| 11 | Hamstrings | 腘绳肌 | `hamstrings` |
| 12 | Latissimus dorsi | 背阔肌 | `lats` |
| 13 | Calves | 小腿 | `calves` |
| 14 | Forearms | 前臂 | `forearms` |

**注意：** 三角肌（wger ID=2）需要根据动作类型判断是前束还是后束：
- 推类动作（卧推、肩推）→ `frontDelts`
- 拉类动作（划船、引体向上）→ `rearDelts`

---

### 视图切换逻辑（自动推荐）

- 动作主要激活背部肌肉（背阔肌、斜方肌、竖脊肌等）→ 自动切到背面
- 动作主要激活正面肌肉（胸肌、腹肌、股四头肌等）→ 自动切到正面
- 用户也可以手动点击按钮切换

`vue-human-muscle-anatomy` 的 HumanAnatomy 组件**不直接支持前/背切换**——它在同一个 SVG 中渲染所有肌肉（正/背面肌肉按不同 ID 区分）。所以视图切换逻辑由我们自己的 `MuscleDiagram.vue` 封装实现：
- 正面肌肉高亮 → 显示正面说明
- 背面肌肉高亮 → 自动切换到背面视图
- 通过 CSS 控制只显示正面或背面的肌肉组

**简化方案：** 由于 `vue-human-muscle-anatomy` 的 SVG 包含完整的人体（正+背面），我们不再做视图切换，直接展示完整视图，所有高亮肌肉自然可见。

---

### 高亮配色

沿用现有设计文档的配色方案：

| 类型 | 颜色 | 用途 |
|------|------|------|
| 默认肌肉 | `#e5e5e5`（浅灰） | 未激活的肌肉 |
| 主动肌 (primary) | `#fb923c`（橙色） | 主要发力的肌肉 |
| 辅助肌 (secondary) | `#fdba74`（浅橙） | 辅助发力的肌肉 |
| 主动肌透明度 | 0.8 | 半透明叠加 |
| 辅助肌透明度 | 0.5 | 更透明 |

---

## 组件设计

### `MuscleDiagram.vue`（重写）

**Props:**

```typescript
{
  primaryMuscles: { id: number; name_en: string; name_cn: string }[]
  secondaryMuscles: { id: number; name_en: string; name_cn: string }[]
}
```

**内部逻辑：**
1. 将 wger ID 映射为 `vue-human-muscle-anatomy` 的肌群名
2. 调用 `HumanAnatomy` 组件渲染
3. 显示图例（当前高亮肌肉中英文名）

**模板结构：**

```html
<div class="muscle-diagram">
  <header>
    <span>💪 肌肉分布</span>
  </header>
  
  <HumanAnatomy
    gender="male"
    :selected-primary-muscle-groups="primaryGroups"
    :selected-secondary-muscle-groups="secondaryGroups"
    primary-highlight-color="#fb923c"
    secondary-highlight-color="#fdba74"
    default-muscle-color="#e5e5e5"
    background-color="#ffffff"
    :primary-opacity="0.8"
    :secondary-opacity="0.5"
  />

  <!-- 图例 -->
  <div v-if="activeMuscles.length > 0" class="legend">
    ...
  </div>
</div>
```

---

## 集成改动

### 需要改动的文件

| 文件 | 改动 |
|------|------|
| `frontend/src/components/MuscleDiagram.vue` | **重写**——使用 `vue-human-muscle-anatomy` 替换手绘 SVG |
| `frontend/src/views/MainPage.vue` | 左侧栏加 MuscleDiagram（CycleInfo 下方） |
| `frontend/src/stores/workout.ts` | 加 `activePrimaryMuscles` / `activeSecondaryMuscles` 状态 |
| `frontend/src/components/ExerciseDrawer.vue` | wger 数据到达时写入 store，关闭时清空 |

### 无需改动的文件

- 后端 API 不变（`GET /api/wger/exercise/{id}` 已返回 `primary_muscles`、`secondary_muscles`）
- 类型定义不变（`ExerciseSlot` 已有嵌套 `exercise` 对象）

---

## 状态与未来规划

### 本期完成
- [ ] 使用 `vue-human-muscle-anatomy` 替换手绘 SVG
- [ ] wger ID → 肌群名映射
- [ ] 肌肉高亮联动（选中动作自动亮）
- [ ] 图例显示肌肉名

### 未来可做
- [ ] **自动视图推荐**——根据肌肉是正面/背面自动调整展示
- [ ] **点击交互**——点击肌肉图上的区域，显示相关动作列表
- [ ] **训练记录热力图**——显示哪些肌肉最近练过、训练频率

---

## 验证方式

1. 启动后端 + 前端
2. 点击 7月1日的某个动作
3. 验证左下角肌肉图显示对应高亮
4. 关闭 Drawer → 高亮清除
5. 点击不同动作 → 高亮切换
