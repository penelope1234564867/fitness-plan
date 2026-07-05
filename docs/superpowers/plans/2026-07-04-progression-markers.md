# 训练变化标记 + 动作进阶显示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在每日计划中看到动作的渐进和替换关系：周间显示↑重量/+次数，跨周期显示"旧动作→新动作"的进阶路径，同时显示建议重量。

**Architecture:** 后端diff_calculator已有prev_exercise_name逻辑，需补充prev_phase；programmer_agent prompt增加weight_kg输出；generator.py写入重量；前端ExerciseRow.vue增加副标题行和重量显示。

**Tech Stack:** Python FastAPI + SQLAlchemy (backend), Vue 3 + TypeScript + Pinia (frontend)

## Global Constraints

- All backend DB queries must use SQLAlchemy ORM, not raw SQL
- Frontend types in `frontend/src/types/index.ts`, all new fields added to `ExerciseSlot` interface
- API response format: existing fields unchanged, new fields (`prev_exercise_name`, `prev_phase`, `prev_target_sets`) added
- No new npm packages
- No new database tables

---

### Task 1: 后端 diff 补充 prev_phase + prev_target_sets

**Files:**
- Modify: `backend/app/engine/diff_calculator.py` (already has prev_exercise_name, add prev_phase + prev_target_sets)
- Modify: `backend/app/api/routes/fitness.py` (get_day_detail → pass prev_phase through)
- Test: `test/debug_diff.py` (quick verification)

**Interfaces:**
- `compute_slot_diffs(current_slots, prev_week_id, db)` returns `{slot_id: {change_type, weight_diff, prev_weight_kg, prev_target_reps, prev_exercise_name, prev_phase, prev_target_sets}}`
- `get_day_detail()` response slots now include prev_phase and prev_target_sets

- [ ] **Step 1: 修改 diff_calculator.py 加入 prev_phase + prev_target_sets**

```python
# 在第2步中，增加 prev_phase 获取和 prev_target_sets 记录
prev_by_exercise[eid] = {
    "weight_kg": ...,
    "target_reps": ...,
    "exercise_name": ...,
    "muscle_group": muscle_group,
    "target_sets": getattr(slot, "target_sets", 0) or 0,  # 新增
    "day_of_week": day.day_of_week,
}

# prev_by_muscle_group 同理补充 target_sets

# 在第3步 results 中加入新字段
results[slot.id] = {
    "change_type": ...,
    "weight_diff": ...,
    "prev_weight_kg": ...,
    "prev_target_reps": ...,
    "prev_exercise_name": prev_name,
    "prev_phase": prev_phase,  # 需要传入
    "prev_target_sets": prev.get("target_sets", 0) if prev else 0,
}
```

`compute_slot_diffs` 需要新增 `prev_phase` 参数：

```python
def compute_slot_diffs(
    current_slots: list,
    prev_week_id: int,
    db: Session,
    prev_phase: str = "",
) -> Dict[int, Dict]:
    # ... existing code ...
    # 在 new_exercise 分支中使用 prev_phase
    results[slot.id] = {
        ...
        "prev_phase": prev_phase,
    }
    # 在已匹配分支中也设置 prev_phase
    results[slot.id] = {
        ...
        "prev_phase": prev_phase,
    }
```

- [ ] **Step 2: 修改 fitness.py get_day_detail() 传入 prev_phase**

```python
# 在找到 prev_week 后，获取其 mesocycle phase
prev_phase = ""
if prev_week:
    prev_meso = db.query(orm_models.Mesocycle).filter(
        orm_models.Mesocycle.id == prev_week.mesocycle_id
    ).first()
    prev_phase = prev_meso.phase if prev_meso else ""

# 调用 diff 时传入
diffs = compute_slot_diffs(slots_orm, prev_week_id, db, prev_phase=prev_phase)

# 响应中增加新字段
slot_dict["prev_exercise_name"] = diffs[sid].get("prev_exercise_name", "")
slot_dict["prev_phase"] = diffs[sid].get("prev_phase", "")
slot_dict["prev_target_sets"] = diffs[sid].get("prev_target_sets", 0)
```

- [ ] **Step 3: 修改前端 types/index.ts 补充新字段**

```typescript
export interface ExerciseSlot {
  // ... existing fields ...
  
  // ── 变化标记（来自后端） ──
  change_type: ChangeType
  weight_diff: number
  prev_weight_kg: number
  prev_target_reps: number
  prev_exercise_name: string      // 新增
  prev_phase: string              // 新增
  prev_target_sets: number        // 新增
}
```

- [ ] **Step 4: 快速验证**

Run: `python -c "from app.engine.diff_calculator import compute_slot_diffs; print('import ok')"`
Expected: no error

- [ ] **Step 5: Commit**

```bash
git add backend/app/engine/diff_calculator.py backend/app/api/routes/fitness.py frontend/src/types/index.ts
git commit -m "feat: diff 补充 prev_phase + prev_target_sets 字段"
```

---

### Task 2: AI 生成建议重量

**Files:**
- Modify: `backend/app/agents/programmer_agent.py` (select_from_pool prompt 增加 weight_kg 输出)
- Modify: `backend/app/engine/generator.py` (_write_slots 写入 weight_kg)

- [ ] **Step 1: 修改 programmer_agent.py select_from_pool prompt 增加建议重量输出**

在 prompt 中增加：

```
选完动作后，根据用户经验水平为每个动作输出建议重量：
- 新手 (beginner): 空杆或最轻哑铃 (5-10kg)，直接显示"空杆"或"10kg"
- 中级 (intermediate): 中小重量 (15-30kg)
- 有经验 (advanced): 中高重量 (30-60kg)

如：
  {"wger_id": 123, "name": "杠铃卧推", "sets": 3, "reps": 8, "rest_seconds": 75, "weight_kg": 20.0}
  
重量单位为 kg，双向动作/单边动作为每边重量。
```

同时修改 JSON 输出格式说明加入 `weight_kg` 字段。

- [ ] **Step 2: 修改 _write_slots 写入 weight_kg**

`_write_slots` 中主项写入 weight_kg 已经存在（line 949: `weight_kg=ex.get("weight_kg", 0.0)`），LLM 返回的 weight_kg 自然会被写入。只需确认即可。

- [ ] **Step 3: 验证 LLM 输出含 weight_kg**

Run: 通过 API 生成新的一周，检查 exercise_slot 中 weight_kg 字段不为 0

- [ ] **Step 4: Commit**

```bash
git add backend/app/agents/programmer_agent.py backend/app/engine/generator.py
git commit -m "feat: AI 生成计划时输出建议重量"
```

---

### Task 3: 前端副标题 + 重量显示

**Files:**
- Modify: `frontend/src/components/ExerciseRow.vue`

- [ ] **Step 1: 修改 ExerciseRow.vue 显示副标题和重量**

在 exercise-name 下方添加副标题行：

```vue
<!-- 动作信息 -->
<div class="exercise-info" @click.stop="$emit('show-detail')">
  <span class="exercise-name">{{ exercise.exercise_name }}</span>
  <!-- 副标题：动作替换/进阶信息 -->
  <span v-if="subtitleText" class="exercise-subtitle">
    {{ subtitleText }}
  </span>
  <!-- 动作参数 -->
  <span class="exercise-detail">
    ...existing code...
  </span>
</div>
```

新增 computed：

```typescript
const subtitleText = computed(() => {
  const ct = props.exercise.change_type
  const prevName = props.exercise.prev_exercise_name
  const prevPhase = props.exercise.prev_phase
  
  // 跨中周期替换：⤴ 基础期: 哑铃卧推 3×10
  if (ct === 'new_exercise' && prevName && prevPhase) {
    const phaseLabel = PHASE_LABEL_MAP[userGoal.value]?.[prevPhase] || prevPhase
    const prevSets = props.exercise.prev_target_sets
    const prevReps = props.exercise.prev_target_reps
    const prevText = prevSets && prevReps ? `${prevSets}×${prevReps}` : ''
    return `⤴ ${phaseLabel}: ${prevName}${prevText ? ' ' + prevText : ''}`
  }
  
  // 同中周期替换：⤴ 上周: 坐姿划船 3×10
  if (ct === 'new_exercise' && prevName) {
    const prevSets = props.exercise.prev_target_sets
    const prevReps = props.exercise.prev_target_reps
    const prevText = prevSets && prevReps ? `${prevSets}×${prevReps}` : ''
    return `⤴ 上周: ${prevName}${prevText ? ' ' + prevText : ''}`
  }
  
  return ''
})
```

在 exercise-detail 中增加重量显示：

```vue
<template v-else>
  {{ exercise.target_sets }}组×{{ exercise.target_reps }}次
  <template v-if="exercise.weight_kg">{{ exercise.weight_kg }}kg</template>
  <template v-if="exercise.rest_seconds"> rest={{ exercise.rest_seconds }}s</template>
</template>
```

新增 CSS：

```css
.exercise-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

- [ ] **Step 2: 确认 PrevPhase 的中文名能用**

在 ExerciseRow.vue 引入 `PHASE_LABEL_MAP`：

```typescript
import { PHASE_LABEL_MAP } from '@/types'
```

但 PHASE_LABEL_MAP 需要知道用户目标（增肌/减脂等），可以通过 props 或者从 store 获取。最简单的方案：从 workout store 或 cycle store 获取。

假设 CycleStore 有 `goal` 属性，或者直接在组件内从 Pinia store 取。

- [ ] **Step 3: 前端验证**

Run: `cd frontend && npm test` 确保测试通过
Run: 启动前端，查看每日计划动作行显示是否正常

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ExerciseRow.vue
git commit -m "feat: 动作行显示副标题 + 重量"
```

---

### Task 4: 端到端验证

**Files:**
- Test: 全链路验证

- [ ] **Step 1: 重启后端，生成新一周**

```bash
# 在 backend 目录
python run.py
# 调用 API
curl -X POST http://localhost:8000/api/fitness/generate-next
```

- [ ] **Step 2: 查看 API 响应**

```bash
curl http://localhost:8000/api/fitness/day-detail?date=<new_date>
# 验证 change_type, prev_exercise_name, prev_phase, weight_kg 字段
```

- [ ] **Step 3: 前端查看**

打开 http://localhost:5173，查看新生成的训练日，确认：
- 动作行右上角变化标记
- 动作名下方副标题
- 重量显示

- [ ] **Step 4: 修复发现的问题**

如有 bug，修复后重新验证

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: 全链路验证通过"
```
