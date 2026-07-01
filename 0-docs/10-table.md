# 9 张表

## 新表（8 张）

### 1. macrocycle — 大周期
只存目标，不管细节。

| 字段 | 说明 |
|------|------|
| id | PK |
| user_id | FK→user |
| goal | 减脂/增肌/塑形 |
| start_date | |
| status | active / completed / paused |

### 2. user_current_state — 当前状态（随时可改）

| 字段 | 说明 |
|------|------|
| id | PK |
| user_id | FK→user，唯一 |
| experience_level | 新手/中级/高级 |
| workout_location | 居家/健身房/户外 |
| days_per_week | 每周练几天 |
| current_mesocycle_id | FK→mesocycle，删了自动置空 |

### 3. mesocycle — 中周期

| 字段 | 说明 |
|------|------|
| id | PK |
| macrocycle_id | FK，级联删除 |
| phase | foundational / hypertrophy / strength / deload |
| week_count | 几周（默认 4，减载是 1） |
| sort_order | 第几个中周期 |
| status | active / completed / pending |

### 4. week — 小周期（每周）

| 字段 | 说明 |
|------|------|
| id | PK |
| mesocycle_id | FK，级联删除 |
| week_number | 在中周期里的第几周（1-4） |
| status | pending / active / completed / skipped |
| generated_at | 该周何时生成的 |

### 5. day — 训练日

| 字段 | 说明 |
|------|------|
| id | PK |
| week_id | FK，级联删除 |
| day_order | 第几个训练日（1/2/3），不是星期几 |
| day_label | 推 / 拉 / 腿 |
| focus | 胸部+肩部+三头 |
| estimated_calories | |
| is_completed | 0/1 |
| completed_date | 实际哪天练的 |
| rpe_score | 当天整体难度 |

### 6. exercise_slot — 动作安排 + 打卡

| 字段 | 说明 |
|------|------|
| id | PK |
| day_id | FK，级联删除 |
| exercise_id | FK→exercise |
| phase_type | warmup / main / cooldown |
| sort_order | 排序 |
| target_sets | 计划组数 |
| target_reps | 计划次数 |
| target_reps_max | 双渐进次数上限 |
| weight_kg | 数字（给引擎算） |
| weight_suggestion | 文字（展示用，"自重"） |
| rest_seconds | 组间休息 |
| actual_sets | 实际组数 |
| actual_reps | 实际次数 |
| actual_weight_kg | 实际重量 |
| rpe | 难度 1-10 |
| notes | 备注 |

### 7. exercise — 动作库（用才缓存）

| 字段 | 说明 |
|------|------|
| id | PK |
| wger_id | wger 的 ID，唯一 |
| name | 动作名 |
| target_muscle | 具体肌肉（股四头肌） |
| muscle_group | 肌肉群（chest/back/legs） |
| movement_pattern | 动作模式（push/pull/squat） |
| category | strength / cardio |
| equipment | bodyweight / dumbbell |
| description | 描述 |
| image_url | 图片 |
| difficulty | 1-5 |

### 8. exercise_variation — 变式链

| 字段 | 说明 |
|------|------|
| id | PK |
| series_name | 系列名（"俯卧撑系列"） |
| exercise_id | FK→exercise |
| sort_order | 从易到难排序 |

---

## 旧表（1 张，过渡用，不再写入）

### 9. fitness_plan — 旧计划

等数据迁移完了就可以删。
