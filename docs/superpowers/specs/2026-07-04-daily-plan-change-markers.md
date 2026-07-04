# 每日计划内嵌周期变化标记 — 设计文档

## 概述

后端已实现渐进超负荷、动作轮换、RPE 自适应调整、中周期阶段切换，但前端每日计划看起来天天一样，用户感知不到变化。本设计在 DailyPlanPanel 中直接展示变化信号，让用户一眼看到当前阶段、动作变化及原因。

## 核心思路

后端在 `day-detail` API 中**顺带计算每个动作与上周同动作的对比差异**，返回变化标记（增重/增次/新动作/减重/无变化），前端直接渲染。

匹配规则：按 `exercise_id`（数据库外键）匹配上周所有天 → 取最近一次出现的数据做对比基准。

## API 变更

### `GET /api/fitness/day-detail?date=YYYY-MM-DD`

#### 新增顶级字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `week_number` | int | 当前是第几周（从 1 开始） |
| `phase_label` | str | 阶段中文名：如"肌肥大期" |
| `phase_color` | str | 阶段颜色：如 `#22c55e` |
| `rpe_trend` | str | RPE 趋势：`rising` / `stable` / `falling` |

#### ExerciseSlot 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `change_type` | str | `none` / `increased_weight` / `increased_reps` / `decreased_weight` / `new_exercise` / `same` |
| `weight_diff` | float | 重量差值（千克，正=加重，负=减重） |
| `prev_weight_kg` | float | 上周该动作的重量 |
| `prev_target_reps` | int | 上周该动作的目标次数 |

#### 判断规则

```
对当天每个 main 动作 slot:
  1. 查上一周 week_number-1 的所有天中同 exercise_id 的 slot
  2. 有多个匹配 → 取 day_of_week 最大的（最近一次）
  3. 无匹配 → change_type = "new_exercise"
  4. 有匹配:
     - weight_kg > prev_weight_kg → "increased_weight"
     - weight_kg < prev_weight_kg → "decreased_weight"
     - weight_kg == prev_weight_kg 且 target_reps > prev_target_reps → "increased_reps"
     - 完全一样 → "same"
  5. 第 1 周/减载周无上周数据 → 全部 "none"
```

## 后端改动

### 新增文件：`backend/app/engine/diff_calculator.py`

负责从上周数据中为当天每个动作计算 diff 标记。纯函数，无副作用。

```python
def compute_slot_diffs(current_slots: list, prev_week_id: int, db: Session) -> dict:
    """返回 {slot_id: {change_type, weight_diff, prev_weight_kg, prev_target_reps}}"""
```

### 修改文件：`backend/app/api/routes/fitness.py`

`get_day_detail()` 函数中，查到当天数据后：
1. 从 `week_id` 推算上一周 `week_id`
2. 调用 `compute_slot_diffs()` 获取对比数据
3. 合并到响应中

同时从 `UserCurrentState` 读取 `rpe_trend` 一并返回。

### 修改文件：`backend/app/models/schemas.py`

新增 `SlotDiffResponse` 或直接扩展现有 `ExerciseSlotResponse`。

## 前端改动

### 修改文件：`frontend/src/types/index.ts`

- `DayDetailResponse` 新增 `week_number`、`phase_label`、`phase_color`、`rpe_trend`
- `ExerciseSlot` 新增 `change_type`、`weight_diff`、`prev_weight_kg`、`prev_target_reps`
- 新增 `ChangeType` 类型定义

### 修改文件：`frontend/src/components/DailyPlanPanel.vue`

1. **Header 增加阶段标识**

```
【before】
7月13日 周一          推胸

【after】
🔥 肌肥大期 · 第 3 周    7月13日 周一    推胸
📈 RPE 趋势：上升中
```

2. **底部增加"本周变化摘要"**

```
📊 变化摘要：3 个动作加重 | 1 个新动作 | 2 个保持
```

### 修改文件：`frontend/src/components/ExerciseRow.vue`

在 exercise-detail 右侧显示变化标记：

| change_type | 显示 |
|-------------|------|
| `increased_weight` | `↑2.5kg`（绿色） |
| `increased_reps` | `+2次`（绿色） |
| `decreased_weight` | `⬇5kg`（橙色） |
| `new_exercise` | `🔄 新动作`（蓝色） |
| `same` / `none` | 不显示 |

### 修改文件：`frontend/src/stores/workout.ts`

- `_mapSlot()` 中保留后端传来的 change_type 等字段
- 新增 computed `changeSummary`：汇总当天变化类型数量

## UI 效果示意

```
┌─────────────────────────────────────────┐
│ 🔥 肌肥大期 · 第3周    📈 RPE 趋势：上升中 │
│ 7月13日 周一               [推胸]        │
│                                         │
│ 💪 主训练                                │
│ □ 杠铃卧推  4×10  40kg  ↑2.5kg   [RPE 7] │
│ □ 高位下拉  3×12  35kg  🔄 新动作  [RPE 6] │
│ □ 哑铃飞鸟  3×12  12kg         ✔ [RPE 7] │
│ □ 坐姿划船  3×10  30kg  +2次    😊 [RPE 4] │
│ □ 绳索下压  3×12  15kg  ⬇5kg   😰 [RPE 9] │
│                                         │
│ 📊 变化摘要：2个加重 | 1个新动作 | 1个保持  │
│                                         │
│ [📝 提交打卡]                            │
└─────────────────────────────────────────┘
```

## 边界情况

| 场景 | 处理方式 |
|------|---------|
| 第 1 周（无上周） | 所有 change_type = `none`，不显示标记 |
| 减载周 | 与第 1 周相同处理 |
| 上周没打卡但有数据 | 仍然用上周的计划参数（`target_*`）做对比 |
| 上周同名但不同 exercise_id | 按 `exercise_id` 匹配，不按名字，不会误匹配 |
| 多个匹配 | 取最近一天（`max(day_of_week)`） |
