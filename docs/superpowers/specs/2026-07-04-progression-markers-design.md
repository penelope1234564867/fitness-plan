# 训练变化标记 + 动作进阶显示

> **Status:** Approved  
> **Design date:** 2026-07-04  
> **Goal:** 让用户在看每日训练计划时，一眼看出这周和上周、这个中周期和上个中周期的区别

## 改动概述

三块改动：

1. **变化标记** — 每个主项动作右上角显示变化标签（↑重量/+次数/⬇减载）
2. **动作进阶副标题** — 动作被替换时，在动作名下用小字显示"从哪来"
3. **建议重量** — AI 生成计划时根据用户经验输出建议重量，界面显示

## 1. 变化标记（右上角标签）

| 场景 | 标签 | 颜色 |
|------|------|------|
| 同一动作，重量增加 | `↑2.5kg` | 绿色 |
| 同一动作，次数增加 | `+3次` | 绿色 |
| 减载降重 | `⬇5kg` | 橙色 |
| 同一动作，无变化 | 不显示 | — |

## 2. 动作进阶副标题（动作名下方小字）

**跨中周期替换：**
```
□ 杠铃卧推              3组×8次   40kg   rest=75s
  ⤴ 基础期: 哑铃卧推 3×10
```

**同中周期内替换：**
```
□ 俯身划船              3组×8次   35kg   rest=75s
  ⤴ 上周: 坐姿划船 3×10
```

**第一次出现的新动作：** 不显示副标题

### 数据来源

- `diff_calculator.py` 返回 `prev_exercise_name`（上周同名/同肌群动作名）
- 如果是跨中周期，API 响应中附带 `prev_phase`（上周期阶段名）
- 前端 `ExerciseRow.vue` 根据 `prev_exercise_name` 和 `prev_phase` 显示副标题

## 3. 建议重量

**后端 `select_from_pool()` 的 LLM prompt：** 要求 LLM 根据用户经验水平为每个动作输出建议重量（weight_kg）

- 新手：空杆或最轻重量
- 中级：中小重量
- 有经验：中高重量

> "哑铃卧推" → 新手建议 10kg/边，有经验 20kg/边

空杆要显示为空杆，不隐藏。

**界面：** ExerciseRow.vue 在动作行显示 weight_kg，格式：
```
3组×8次   40kg   rest=75s
```

## 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/app/engine/diff_calculator.py` | 新动作按同肌群找上周旧动作，返回 prev_exercise_name + prev_phase |
| `backend/app/agents/programmer_agent.py` | select_from_pool prompt 增加建议重量输出 |
| `backend/app/engine/generator.py` | _write_slots() 写入 weight_kg（LLM 建议值） |
| `frontend/src/components/ExerciseRow.vue` | 显示变化标记 + 副标题行 + 重量 |
| `frontend/src/types/index.ts` | 类型补充 prev_exercise_name, prev_phase |
