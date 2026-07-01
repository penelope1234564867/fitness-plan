# 日历重构设计文档

> 日期：2026-07-01
> 状态：已定稿

---

## 问题

1. **每周显示相同计划** — 日历用 `day_of_week` 匹配单周数据，导致所有周一相同
2. **无法查看历史** — 前端只存 `currentWeek`，切换月份后无数据
3. **无法翻看未来** — 已生成的未来周无法展示
4. **跨月周截断** — 6月末到7月初的同一周被切分显示不完整

## 解决方案概览

给 `Day` 加上具体日期字段，让每天的训练与日历日期固定绑定。实施后日历可基于日期范围查询，显示历史、当前、未来已生成的所有计划。

---

## 一、数据模型改动

### Week 表
```python
# 新增
start_date = Column(String(10))  # "YYYY-MM-DD"，本周一的日期
```

### Day 表
```python
# 新增（代替 day_of_week 推导）
date = Column(String(10))  # "YYYY-MM-DD"，具体训练日期
```

### Macrocycle 表
```python
# start_date 已有但可能为空，确保生成时写入
start_date = Column(String(20))  # 保证非空，大周期起始周一
```

### 生成日期规则

- 首次生成：用户传入起始日期（默认为本周一）
- `Macrocycle.start_date` = 起始日期
- `Week.start_date` = `Macrocycle.start_date + (week_number - 1) * 7`
- `Day.date` = `Week.start_date + (day_of_week - 1)`
- 跨月周：Day 有具体日期，按 date 查询天然支持跨月

### 调整训练日的逻辑

现有 `PUT /api/fitness/day/{id}/reschedule` 改造：
- 同步更新 `day_of_week` 和 `date`
- 检查冲突：同一 `week_id` 内不能有重复 `day_of_week`
- 日期计算：新 date = `Week.start_date + (新 day_of_week - 1)`

---

## 二、API 设计

### 新增：日历网格轻量数据

```
GET /api/fitness/calendar-data?from=YYYY-MM-DD&to=YYYY-MM-DD

Response:
[
  {
    "date": "2026-07-01",
    "has_plan": true,
    "day_status": "pending",         // pending / completed / future
    "focus": "胸部+肩部+三头",       // 训练主题
    "mesocycle_phase": "hypertrophy" // 所属中周期阶段
  },
  ...
]
```

**说明：**
- 数据量极小（一个月最多 31 条）
- `has_plan: false` 的日期只返回 date + false，其他字段省略
- 前端以此渲染日历格子

### 新增：点击日期的详情

```
GET /api/fitness/day-detail?date=YYYY-MM-DD

Response:
{
  "date": "2026-07-01",
  "day_status": "pending",         // pending / completed / future / no_plan
  "day_label": "推",
  "focus": "胸部+肩部+三头",
  "week_id": 3,
  "mesocycle_phase": "hypertrophy",
  "is_rest_day": false,
  "has_plan": true,
  "slots": [
    {
      "id": 45,
      "phase_type": "main",
      "sort_order": 1,
      "wger_id": 123,
      "exercise_name": "杠铃卧推",
      "target_sets": 4,
      "target_reps": 10,
      "target_reps_max": 12,
      "weight_kg": 40.0,
      "weight_suggestion": "40kg",
      "rest_seconds": 90,
      "actual_sets": 0,       // 未打卡时为 0
      "actual_reps": 0,
      "actual_weight_kg": 0,
      "rpe": 0,
      "notes": "",
      "exercise": { ... }
    }
  ],
  "warmup": [...],
  "main": [...],
  "cardio": {...} | null,
  "stretch": [...]
}
```

**说明：**
- 历史和未来都能查（只要已经生成）
- 未打卡时 `actual_*` 字段返回 0
- `day_status` 为 `no_plan` 时返回空内容

### 修改：调整日期的 reschedule API

```
PUT /api/fitness/day/{id}/reschedule
Body: { "day_of_week": 5 }
# 服务端自动计算新 date = Week.start_date + (new_day_of_week - 1)
# 返回 409 Conflict 如果目标 day_of_week 已被占用
```

---

## 三、后端改动

### 生成器 `generator.py`

- `generate_init_week()`:
  - 接收 `start_date` 参数（默认本周一）
  - `Week.start_date = start_date`
  - `Day.date = start_date + (day_of_week - 1)` 给每个 Day

- `generate_next_week()`:
  - `new_week.start_date = old_week.start_date + 7`
  - 同样给每个 Day 分配具体日期

### 路由 `fitness.py`

- 新增 `GET /calendar-data` → 查询指定日期范围的所有 Day，返回轻量数组
- 新增 `GET /day-detail` → 查某天的完整训练内容（含 slots + exercise）
- 改造 reschedule → 同步更新 `date` + 冲突检查

---

## 四、前端改动

### 类型定义 `types/index.ts`
```
新增: CalendarEntry (date, has_plan, day_status, focus, ...)
新增: DayDetailResponse (完整某天数据)
```

### API 服务 `services/api.ts`
```
新增: fetchCalendarData(from, to) → CalendarEntry[]
新增: fetchDayDetail(date) → DayDetailResponse
```

### CycleStore `stores/cycle.ts`
```
新增状态:
  - calendarEntries: Map<string, CalendarEntry>  // date → entry
  - calendarRange: { start, end }                // 日历可翻范围
  
新增 action:
  - fetchCalendarData(from, to) → 加载指定范围
  - initCalendarRange() → 从 Macrocycle 数据推算可翻范围
  
修改:
  - fetchCurrentWeek 成功后自动加载当月日历数据
  - initPlan 成功后自动加载日历数据
```

### WorkoutStore `stores/workout.ts`
```
修改:
  - currentDay 不再从 cycleStore.currentWeek 推导
  - 改为 selectedDate 变化时调用 fetchDayDetail 获取当日数据
  - 增加 dayDetail 状态存储单日完整数据
```

### CalendarPanel `components/CalendarPanel.vue`
```
新增:
  - 翻月时自动调用 cycleStore.fetchCalendarData()
  - 限制可翻范围（min: macrocycle.start, max: 最后一个已生成周 + 1月）
  - 无计划的日期显示灰色

修改:
  - getCellStatus() 从 calendarEntries 读取状态
  - getFocusIcon() 从 calendarEntries 读取
  - 跨月周的格子不再被截断（数据来自已加载的 calendarEntries）
```

### DailyPlanPanel `components/DailyPlanPanel.vue`
```
修改:
  - 选日期时从 dayDetail API 获取数据
  - 不再直接从 cycleStore.currentWeek 推导
  - 历史已完成数据展示 actual_* 字段
```

---

## 五、日历范围规则

| 场景 | 范围 |
|------|------|
| 起始点 | 大周期的 `start_date`（第一个训练周周一） |
| 终点 | 大周期最后一个已生成中周期的最后一周末 |
| 过去方向 | 不能翻到 `start_date` 之前 |
| 未来方向 | 可以翻，超出已生成范围显示「暂无计划」 |
| 跨月周 | Day 有具体 date，不截断 |

---

## 六、迁移策略

因为已有用户数据（`Week` 没有 `start_date`，`Day` 没有 `date`），需要：

1. **数据库迁移脚本**：扫描现有 `Week.generated_at` 推算 `start_date`
2. **数据库迁移脚本**：用 `Week.start_date + (day_of_week - 1)` 回填 `Day.date`
3. **回填逻辑**：在迁移脚本中处理，不对历史数据做破坏性修改

---

## 七、不涉及的范围

- 不改变打卡逻辑（`POST /checkin` 保持不变）
- 不改变渐进超负荷/动作轮换/中周期管理等引擎逻辑
- 不改变 user/profile 相关逻辑
- 不改变 NavBar / CycleInfo / ExerciseDrawer 等 UI 组件
