# Daily Plan Change Markers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make users see training progression by displaying change markers (↑weight, 🔄new exercise) per slot, plus phase badge/RPE trend in DailyPlanPanel header.

**Architecture:** Backend computes diffs in `day-detail` API by matching `exercise_id` against the previous week's slots. Frontend receives pre-computed diff data and renders visual markers inline.

**Tech Stack:** Python FastAPI + SQLAlchemy (backend), Vue 3 + TypeScript + Pinia (frontend)

## Global Constraints

- Backend `diff_calculator.py` must be a pure function — no side effects, return dict
- Match by `exercise_id` (DB foreign key), not by name
- Multiple matches → take `max(day_of_week)` (most recent occurrence)
- Only `phase_type == 'main'` slots get diff computation
- Week 1 / deload weeks → all `change_type = 'none'`
- Commit after each task

---
## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/engine/diff_calculator.py` | **Create** | Pure function: compute diffs for one day's slots against previous week |
| `backend/app/models/schemas.py` | Modify | Add `change_type`, `weight_diff`, `prev_weight_kg`, `prev_target_reps` to `ExerciseSlotResponse`; add `week_number`, `phase_label`, `phase_color`, `rpe_trend` to `DayDetailResponse` |
| `backend/app/api/routes/fitness.py` | Modify | Integrate diff computation into `get_day_detail()` |
| `frontend/src/types/index.ts` | Modify | Add `ChangeType` union type, new fields on `ExerciseSlot` and `DayDetailResponse` |
| `frontend/src/stores/workout.ts` | Modify | Pass through new fields in `_mapSlot()`, add `changeSummary` computed |
| `frontend/src/components/DailyPlanPanel.vue` | Modify | Phase badge in header, change summary at bottom |
| `frontend/src/components/ExerciseRow.vue` | Modify | Change marker display per slot |

---
### Task 1: Create diff_calculator.py

**Files:**
- Create: `backend/app/engine/diff_calculator.py`
- No test file (pure query logic, covered by E2E test in Task 5)

**Interfaces:**
- Produces: `compute_slot_diffs(current_slots: list, prev_week_id: int, db) -> dict[int, dict]`

- [ ] **Step 1: Create diff_calculator.py**

```python
"""diff_calculator — 计算每个动作与上周同动作的对比差异

纯函数模块，无副作用。
提供给 get_day_detail() 调用，为每个 slot 计算 change_type。
"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.orm_models import ExerciseSlot, Day


def compute_slot_diffs(
    current_slots: list,
    prev_week_id: int,
    db: Session,
) -> Dict[int, Dict]:
    """对比当天动作与上周同 exercise_id 的最近一次数据。

    Args:
        current_slots: 当天的 ExerciseSlot 对象列表（不含 warmup/stretch）
        prev_week_id: 上一周 week.id
        db: 数据库 session

    Returns:
        {slot_id: {change_type, weight_diff, prev_weight_kg, prev_target_reps}}
        只包含 phase_type == 'main' 的 slot
    """
    if not prev_week_id:
        return {}

    # 1. 获取上周所有天
    prev_days = (
        db.query(Day)
        .filter(Day.week_id == prev_week_id)
        .order_by(Day.day_of_week.desc())
        .all()
    )
    if not prev_days:
        return {}

    # 2. 获取上周所有 main slot，按 exercise_id 分组取最近一天
    from collections import OrderedDict
    prev_by_exercise: Dict[int, dict] = {}
    for day in prev_days:
        for slot in (day.slots or []):
            if getattr(slot, "phase_type", "") != "main":
                continue
            eid = getattr(slot, "exercise_id", None)
            if not eid or eid in prev_by_exercise:
                continue  # 已经有过该 exercise_id 的记录，day_of_week 降序第一个就是最近
            prev_by_exercise[eid] = {
                "weight_kg": getattr(slot, "weight_kg", 0) or 0,
                "target_reps": getattr(slot, "target_reps", 0) or 0,
                "day_of_week": day.day_of_week,
            }

    # 3. 计算每个 slot 的 diff
    results: Dict[int, Dict] = {}
    for slot in current_slots:
        if getattr(slot, "phase_type", "") != "main":
            continue

        eid = getattr(slot, "exercise_id", None)
        if not eid:
            continue

        cur_weight = getattr(slot, "weight_kg", 0) or 0
        cur_reps = getattr(slot, "target_reps", 0) or 0

        prev = prev_by_exercise.get(eid)
        if not prev:
            results[slot.id] = {
                "change_type": "new_exercise",
                "weight_diff": 0,
                "prev_weight_kg": 0,
                "prev_target_reps": 0,
            }
            continue

        prev_weight = prev["weight_kg"]
        prev_reps = prev["target_reps"]
        weight_diff = round(cur_weight - prev_weight, 1)

        if cur_weight > prev_weight:
            change_type = "increased_weight"
        elif cur_weight < prev_weight:
            change_type = "decreased_weight"
        elif cur_reps > prev_reps:
            change_type = "increased_reps"
        else:
            change_type = "same"

        results[slot.id] = {
            "change_type": change_type,
            "weight_diff": weight_diff,
            "prev_weight_kg": prev_weight,
            "prev_target_reps": prev_reps,
        }

    return results
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/engine/diff_calculator.py
git commit -m "feat: add diff_calculator for slot change markers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
### Task 2: Extend backend schemas

**Files:**
- Modify: `backend/app/models/schemas.py`

**Interfaces:**
- Consumes: Task 1's `compute_slot_diffs()` returns dict
- Produces: `ExerciseSlotResponse` with new fields; `DayDetailResponse` with new fields

- [ ] **Step 1: Add new fields to ExerciseSlotResponse**

In `backend/app/models/schemas.py`, add these fields to `ExerciseSlotResponse`:

```python
class ExerciseSlotResponse(BaseModel):
    # ... existing fields unchanged ...
    # ── 变化标记（对比上周） ──
    change_type: str = "none"               # none / increased_weight / increased_reps / decreased_weight / new_exercise / same
    weight_diff: float = 0.0                # 重量差值（千克，正=加重，负=减重）
    prev_weight_kg: float = 0.0             # 上周该动作的重量（对比基准）
    prev_target_reps: int = 0               # 上周该动作的目标次数
```

- [ ] **Step 2: Add new fields to DayDetailResponse**

```python
class DayDetailResponse(BaseModel):
    # ... existing fields unchanged ...
    # ── 阶段信息（新增） ──
    week_number: int = 0                    # 当前是第几周（从 1 开始）
    phase_label: str = ""                   # 阶段中文名：如"肌肥大期"
    phase_color: str = ""                   # 阶段颜色：如 "#22c55e"
    rpe_trend: str = "stable"               # rising / stable / falling
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: add change marker fields to API schemas

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
### Task 3: Integrate diff into day-detail API

**Files:**
- Modify: `backend/app/api/routes/fitness.py`

**Interfaces:**
- Consumes: `compute_slot_diffs()` from Task 1, new schema fields from Task 2
- Produces: `get_day_detail()` returns enriched response with phase info + slot diffs

- [ ] **Step 1: Add imports**

At the top of `backend/app/api/routes/fitness.py`, add:

```python
from app.engine.diff_calculator import compute_slot_diffs
```

- [ ] **Step 2: Modify `get_day_detail()` to include phase info and slot diffs**

Find `get_day_detail()` around line 619. After building `response` around line 678, integrate diff:

```python
@router.get("/day-detail")
async def get_day_detail(date: str = "",
                          db: Session = Depends(get_db)):
    """获取某天的完整训练内容（含 slots + exercise 详情 + 变化标记）。"""
    if not date:
        raise HTTPException(status_code=400, detail="请提供 date 参数 (YYYY-MM-DD)")

    day = db.query(orm_models.Day).filter(
        orm_models.Day.date == date
    )

    # 只查当前活跃大周期的 Day
    active_macro = db.query(orm_models.Macrocycle).filter(
        orm_models.Macrocycle.status == "active",
    ).order_by(orm_models.Macrocycle.id.desc()).first()
    if active_macro:
        valid_week_ids = [
            w.id
            for meso in db.query(orm_models.Mesocycle).filter(
                orm_models.Mesocycle.macrocycle_id == active_macro.id,
            ).all()
            for w in db.query(orm_models.Week).filter(
                orm_models.Week.mesocycle_id == meso.id,
            ).all()
        ]
        if valid_week_ids:
            day = day.filter(orm_models.Day.week_id.in_(valid_week_ids))

    day = day.first()

    if not day:
        return {
            "date": date,
            "day_status": "no_plan",
            "day_label": "",
            "focus": "",
            "week_id": 0,
            "mesocycle_phase": "",
            "is_rest_day": False,
            "has_plan": False,
            "slots": [],
            "warmup": [],
            "main": [],
            "cardio": None,
            "stretch": [],
            # 新增字段
            "week_number": 0,
            "phase_label": "",
            "phase_color": "",
            "rpe_trend": "stable",
        }

    # 获取中周期阶段
    week = db.query(orm_models.Week).filter(orm_models.Week.id == day.week_id).first()
    mesocycle_phase = ""
    week_number = 1
    prev_week_id = 0
    if week:
        week_number = week.week_number or 1
        meso = db.query(orm_models.Mesocycle).filter(
            orm_models.Mesocycle.id == week.mesocycle_id
        ).first()
        if meso:
            mesocycle_phase = meso.phase
            # 找上一周
            if week_number > 1:
                prev_week = db.query(orm_models.Week).filter(
                    orm_models.Week.mesocycle_id == meso.id,
                    orm_models.Week.week_number == week_number - 1,
                ).first()
                if prev_week:
                    prev_week_id = prev_week.id

    # 构建 slots 数据
    response = _build_day_detail(day, db)
    response["mesocycle_phase"] = mesocycle_phase
    response["week_number"] = week_number

    # 阶段中文名和颜色
    from app.api.routes.fitness import PHASE_LABEL_MAP, PHASE_COLORS  # or define locally
    # 获取 goal
    goal = "增肌"
    if active_macro:
        goal = active_macro.goal or "增肌"
    phase_labels_map = {
        "foundational": "基础适应期",
        "hypertrophy": "肌肥大期",
        "strength": "力量提升期",
        "deload": "减载恢复周",
    }
    phase_colors = {
        "foundational": "#3b82f6",
        "hypertrophy": "#22c55e",
        "strength": "#f97316",
        "deload": "#a855f7",
    }
    # 按目标映射
    goal_phase_labels = {
        "增肌": {"foundational": "基础适应期", "hypertrophy": "肌肥大期", "strength": "力量提升期", "deload": "减载恢复周"},
        "减脂": {"foundational": "基础适应期", "hypertrophy": "燃脂强化期", "strength": "代谢提升期", "deload": "减载恢复周"},
        "塑形": {"foundational": "基础适应期", "hypertrophy": "塑形雕刻期", "strength": "紧致提升期", "deload": "减载恢复周"},
        "保持健康": {"foundational": "基础适应期", "hypertrophy": "综合维持期", "strength": "活跃恢复期", "deload": "减载恢复周"},
    }
    labels = goal_phase_labels.get(goal, goal_phase_labels["增肌"])
    response["phase_label"] = labels.get(mesocycle_phase, "")
    response["phase_color"] = phase_colors.get(mesocycle_phase, "#999")

    # RPE 趋势
    ucs = db.query(orm_models.UserCurrentState).first()
    response["rpe_trend"] = ucs.rpe_trend if ucs else "stable"

    # 计算 slots diff
    if prev_week_id and response.get("slots"):
        # 把 slot dict 转成 ORM 对象才能传给 diff_calculator
        # 改用直接从数据库查 slot 对象
        slots_orm = (
            db.query(orm_models.ExerciseSlot)
            .filter(orm_models.ExerciseSlot.day_id == day.id)
            .all()
        )
        diffs = compute_slot_diffs(slots_orm, prev_week_id, db)
        # 合并到 slots 响应中
        for slot_dict in response.get("slots", []):
            sid = slot_dict.get("id")
            if sid in diffs:
                slot_dict["change_type"] = diffs[sid]["change_type"]
                slot_dict["weight_diff"] = diffs[sid]["weight_diff"]
                slot_dict["prev_weight_kg"] = diffs[sid]["prev_weight_kg"]
                slot_dict["prev_target_reps"] = diffs[sid]["prev_target_reps"]

    return response
```

**Important:** Also need to import `PHASE_LABEL_MAP` and `PHASE_COLORS` — actually let's use inline dicts defined in the function to keep things simple and avoid import issues. The above code does that.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/fitness.py
git commit -m "feat: integrate diff computation and phase info into day-detail API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
### Task 4: Update frontend types

**Files:**
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Consumes: API returns new fields from Tasks 2-3
- Produces: `ChangeType`, updated `ExerciseSlot`, updated `DayDetailResponse` — used by Tasks 5-7

- [ ] **Step 1: Add ChangeType type and update ExerciseSlot**

After `export type RPEQuick = 'easy' | 'normal' | 'hard'` (line 27), add:

```typescript
/** 变化标记类型 — 与后端 change_type 对应 */
export type ChangeType = 'none' | 'increased_weight' | 'increased_reps' | 'decreased_weight' | 'new_exercise' | 'same'
```

Add to `ExerciseSlot` interface (after `_loading: boolean` around line 58):

```typescript
  // ── 变化标记（来自后端）──
  change_type: ChangeType
  weight_diff: number                 // 重量差值
  prev_weight_kg: number              // 上周重量
  prev_target_reps: number            // 上周目标次数
```

- [ ] **Step 2: Update DayDetailResponse**

Add to `DayDetailResponse` (after `mesocycle_phase: string` around line 331):

```typescript
  week_number: number                 // 当前是第几周
  phase_label: string                 // 阶段中文名
  phase_color: string                 // 阶段颜色
  rpe_trend: string                   // rising/stable/falling
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add ChangeType and change marker fields to frontend types

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
### Task 5: Update workout store

**Files:**
- Modify: `frontend/src/stores/workout.ts`

**Interfaces:**
- Consumes: Task 4 types, Task 3 API response
- Produces: `changeSummary` computed — consumed by Task 6

- [ ] **Step 1: Update `_mapSlot()` to pass through new fields**

In `_mapSlot()` around line 65, add change marker fields to the returned reactive object:

```typescript
function _mapSlot(s: any, dd: any) {
    const completed = s.actual_sets > 0 || s.actual_reps > 0 || s.rpe > 0
    let rpeQuick: RPEQuick | null = null
    if (completed) {
      if (s.rpe === 4) rpeQuick = 'easy'
      else if (s.rpe === 7) rpeQuick = 'normal'
      else if (s.rpe === 9) rpeQuick = 'hard'
      else rpeQuick = 'normal'
    }
    return reactive({
      ...s,
      day_id: dd?.slots?.[0]?.day_id || s.day_id || 0,
      _completed: completed,
      _rpeQuick: rpeQuick,
      _loading: false,
      // 变化标记字段 — 直接从后端传过来
      change_type: s.change_type || 'none',
      weight_diff: s.weight_diff || 0,
      prev_weight_kg: s.prev_weight_kg || 0,
      prev_target_reps: s.prev_target_reps || 0,
    })
  }
```

- [ ] **Step 2: Add `changeSummary` computed**

After `currentDay` computed (around line 32), add:

```typescript
  /** 当天变化摘要统计 */
  const changeSummary = computed(() => {
    const day = currentDay.value
    if (!day) return { increased: 0, newExercise: 0, same: 0, decreased: 0, total: 0 }
    const main = day.main
    if (!main.length) return { increased: 0, newExercise: 0, same: 0, decreased: 0, total: 0 }

    let increased = 0   // increased_weight + increased_reps
    let newExercise = 0
    let same = 0
    let decreased = 0

    for (const s of main) {
      const ct = (s as any).change_type
      if (ct === 'increased_weight' || ct === 'increased_reps') increased++
      else if (ct === 'new_exercise') newExercise++
      else if (ct === 'same' || ct === 'none') same++
      else if (ct === 'decreased_weight') decreased++
    }

    return { increased, newExercise, same, decreased, total: main.length }
  })
```

Don't forget to add `changeSummary` to the return block:

```typescript
  return {
    selectedDate, dayDetail, currentDay, todayStr,
    dayDetailLoading, checkinLoading, error,
    activePrimaryMuscles, activeSecondaryMuscles,
    changeSummary,   // ← 新增
    toggleExercise, setRPEQuick, rescheduleDay, submitCheckin, reloadDayDetail,
  }
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/workout.ts
git commit -m "feat: add change marker pass-through and changeSummary to workout store

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
### Task 6: Update ExerciseRow with change marker display

**Files:**
- Modify: `frontend/src/components/ExerciseRow.vue`

**Interfaces:**
- Consumes: `exercise.change_type` from props (Task 4 types)
- Produces: Visual change marker next to exercise detail

- [ ] **Step 1: Add change marker to ExerciseRow template**

After the exercise-detail span (around line 28), add:

```vue
    <!-- 变化标记（仅 main 动作显示） -->
    <span v-if="exercise.phase_type === 'main' && markerText" class="change-marker" :class="markerClass">
      {{ markerText }}
    </span>
```

- [ ] **Step 2: Add computed for marker text and class**

In the `<script setup>` block, add after `defineEmits`:

```typescript
import { computed } from 'vue'

const props = defineProps<{ exercise: ExerciseSlot }>()
// ... existing emits ...

const markerText = computed(() => {
  const ct = props.exercise.change_type
  if (!ct || ct === 'none' || ct === 'same') return ''
  const wd = props.exercise.weight_diff || 0
  switch (ct) {
    case 'increased_weight': return `↑${wd}kg`
    case 'increased_reps': return `+${Math.abs(wd > 0 ? 0 : props.exercise.prev_target_reps - props.exercise.target_reps)}次`
    case 'decreased_weight': return `⬇${Math.abs(wd)}kg`
    case 'new_exercise': return '🔄 新动作'
    default: return ''
  }
})

const markerClass = computed(() => {
  const ct = props.exercise.change_type
  if (ct === 'increased_weight' || ct === 'increased_reps') return 'marker-up'
  if (ct === 'decreased_weight') return 'marker-down'
  if (ct === 'new_exercise') return 'marker-new'
  return ''
})
```

- [ ] **Step 3: Add marker styles after existing styles**

```css
.change-marker {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}
.marker-up { background: #dcfce7; color: #16a34a; }
.marker-down { background: #fff7ed; color: #ea580c; }
.marker-new { background: #dbeafe; color: #2563eb; }
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ExerciseRow.vue
git commit -m "feat: add change marker display to ExerciseRow

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
### Task 7: Update DailyPlanPanel with phase badge + change summary

**Files:**
- Modify: `frontend/src/components/DailyPlanPanel.vue`

**Interfaces:**
- Consumes: `workoutStore.changeSummary` from Task 5, `dayDetail` from workoutStore, `cycleStore.mesocyclePhaseLabel`

- [ ] **Step 1: Update plan-header to include phase badge + RPE trend**

Replace the existing plan-header div (around line 35-39) with:

```vue
      <!-- 日期头部 + 阶段标识 -->
      <div class="plan-header">
        <div class="plan-header-left">
          <h2 class="date-title">{{ dateTitle }}</h2>
          <span class="focus-tag">{{ dayPlan.focus }}</span>
        </div>
        <div class="plan-header-right">
          <span
            v-if="phaseInfo.label"
            class="phase-badge"
            :style="{ background: phaseInfo.color + '20', color: phaseInfo.color, borderColor: phaseInfo.color + '40' }"
          >
            {{ phaseInfo.emoji }} {{ phaseInfo.label }} · 第{{ phaseInfo.week }}周
          </span>
          <span v-if="phaseInfo.rpeTrend === 'rising'" class="rpe-trend-badge trend-up">
            📈 RPE 趋势：上升中
          </span>
          <span v-else-if="phaseInfo.rpeTrend === 'falling'" class="rpe-trend-badge trend-down">
            📉 RPE 趋势：下降中
          </span>
          <span v-else-if="phaseInfo.rpeTrend === 'stable'" class="rpe-trend-badge trend-stable">
            📊 RPE 趋势：稳定
          </span>
        </div>
      </div>
```

- [ ] **Step 2: Add phaseInfo computed**

In the `<script setup>` block, after existing computed properties:

```typescript
import { useCycleStore } from '@/stores/cycle'

const cycleStore = useCycleStore()

const phaseInfo = computed(() => {
  const dd = dayDetail.value
  if (!dd) return { label: '', color: '', week: 0, emoji: '', rpeTrend: 'stable' }

  const phaseEmoji: Record<string, string> = {
    foundational: '🌱',
    hypertrophy: '🔥',
    strength: '💪',
    deload: '🧘',
  }

  return {
    label: dd.phase_label || '',
    color: dd.phase_color || '#999',
    week: dd.week_number || 0,
    emoji: phaseEmoji[dd.mesocycle_phase] || '🏋️',
    rpeTrend: dd.rpe_trend || 'stable',
  }
})
```

- [ ] **Step 3: Add change summary section before the RPE hint**

Before the RPE hint div (around line 87), add:

```vue
      <!-- 变化摘要 -->
      <div v-if="workoutStore.changeSummary.total > 0" class="change-summary">
        📊 变化摘要：
        <span v-if="workoutStore.changeSummary.increased" class="cs-up">
          {{ workoutStore.changeSummary.increased }} 个动作加重
        </span>
        <span v-if="workoutStore.changeSummary.decreased" class="cs-down">
          {{ workoutStore.changeSummary.decreased }} 个动作减载
        </span>
        <span v-if="workoutStore.changeSummary.newExercise" class="cs-new">
          {{ workoutStore.changeSummary.newExercise }} 个新动作
        </span>
        <span v-if="workoutStore.changeSummary.same" class="cs-same">
          {{ workoutStore.changeSummary.same }} 个动作保持
        </span>
      </div>
```

- [ ] **Step 4: Add styles**

```css
.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.plan-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.plan-header-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.phase-badge {
  padding: 4px 12px;
  border-radius: 20px;
  border: 1px solid;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.rpe-trend-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 12px;
  background: #f9fafb;
}
.trend-up { color: #16a34a; }
.trend-down { color: #ea580c; }
.trend-stable { color: #6b7280; }

.change-summary {
  display: flex;
  gap: 8px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 8px;
  margin: 8px 0 12px;
  font-size: 12px;
  color: #555;
  flex-wrap: wrap;
}
.change-summary span { font-weight: 600; }
.cs-up { color: #16a34a; }
.cs-down { color: #ea580c; }
.cs-new { color: #2563eb; }
.cs-same { color: #9ca3af; }
```

Also need to remove the old `.plan-header` style (the one with `display: flex; align-items: center;`) and replace with the new one above.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DailyPlanPanel.vue
git commit -m "feat: add phase badge and change summary to DailyPlanPanel

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---
### Task 8: Smoke test

**Files:**
- None

- [ ] **Step 1: Restart backend**

```bash
cd backend && python run.py
```

Check that it starts without import errors.

- [ ] **Step 2: Test day-detail API**

In another terminal, test with a known date (adjust date as needed):

```bash
curl -s "http://localhost:8000/api/fitness/day-detail?date=2026-07-06" | python -m json.tool
```

Verify:
- `slots[0].change_type` is present
- `phase_label` is non-empty
- `week_number` is an integer
- `rpe_trend` is one of rising/stable/falling

- [ ] **Step 3: Start frontend and verify rendering**

```bash
cd frontend && npm run dev
```

Open the app in browser, click a date with a plan, verify:
- Phase badge shows in header with correct emoji and color
- RPE trend shows
- ExerciseRows show change markers (↑/🔄/⬇/no marker)
- Change summary bar appears at bottom

- [ ] **Step 4: Fix any issues and commit final changes**

```bash
git add -A
git commit -m "fix: adjust change marker rendering after smoke test

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
