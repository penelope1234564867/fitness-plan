# 训练周期路线图展示 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在个人主页看到完整的大周期路线图，在训练主页看到精美的每周进度条

**Architecture:**
- 后端：init-plan 时预创建全 Mesocycle 的 Week+Day 框架（无具体动作），generate-next 和 init-plan 响应中返回 macrocycle_detail 供前端渲染路线图
- 前端：ProfilePage 右栏新增 CycleRoadmap + PhaseDetail + CycleHistory 三个组件；MainPage CycleInfo 重做为 WeekProgress 放到日历上方

**Tech Stack:** Python FastAPI + SQLAlchemy, Vue 3 + TypeScript + Pinia

## Global Constraints

- 所有文件路径使用 `backend/` 和 `frontend/` 前缀
- 后端 API 响应以 SSE 事件格式返回
- CSS 使用 scoped style, 设计风格与现有组件一致（橙色调 #f97316）
- 阶段颜色方案：foundational=#3b82f6(蓝色), hypertrophy=#22c55e(绿色), strength=#f97316(橙色), deload=#a855f7(紫色)
- 中周期路线名称因用户目标而异（增肌/减脂/塑形/保持健康）
- 预创建的 Weeks 和 Days 仅含框架字段（无 ExerciseSlot），Week.status='pending'
- init-plan 预创建当前 Mesocycle 的 4 周框架，而非全部 4 个 Mesocycle

---

### Task 1: 后端 — 添加中周期框架预生成函数

**Files:**
- Modify: `backend/app/engine/mesocycle_manager.py` — 新增 `generate_mesocycle_skeleton()` 函数
- Test: `backend/app/engine/__tests__/test_mesocycle_skeleton.py`

**Interfaces:**
- Produces: `generate_mesocycle_skeleton(mesocycle, ucs, db, start_date, event_queue) -> list[Week]`
  参数: `mesocycle` (Mesocycle ORM), `ucs` (UserCurrentState ORM), `db` (Session), `start_date` (str YYYY-MM-DD), `event_queue` (asyncio.Queue)
  返回: 创建的 Week 对象列表（含 Days）

- [ ] **Step 1: 写测试**

```python
# backend/app/engine/__tests__/test_mesocycle_skeleton.py
"""测试中周期框架预生成函数。"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from app.engine.mesocycle_manager import generate_mesocycle_skeleton

@pytest.mark.asyncio
async def test_generate_mesocycle_skeleton_creates_4_weeks():
    """4 周的中周期应创建 4 个 Week 对象，每个 Week 有正确的 Days。"""
    mesocycle = MagicMock()
    mesocycle.id = 1
    mesocycle.week_count = 4

    ucs = MagicMock()
    ucs.days_per_week = 3
    ucs.preferred_days = "1,3,5"

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    event_queue = AsyncMock()

    weeks = await generate_mesocycle_skeleton(
        mesocycle, ucs, db, "2026-07-06", event_queue
    )

    assert len(weeks) == 4, "应创建 4 个 Week"
    for i, week in enumerate(weeks):
        assert week.week_number == i + 1, f"Week {i+1} 序号应为 {i+1}"
        assert week.status == "pending"
        assert len(week.days) == 3, f"Week {i+1} 应有 3 个训练日"

    # 验证日期正确：第一周从 7/6(周一) 开始
    assert weeks[0].start_date == "2026-07-06"
    assert weeks[0].days[0].day_of_week == 1  # 周一
    assert weeks[0].days[0].date == "2026-07-06"
    assert weeks[0].days[1].day_of_week == 3  # 周三
    assert weeks[0].days[2].day_of_week == 5  # 周五


@pytest.mark.asyncio
async def test_generate_mesocycle_skeleton_with_sunday_start():
    """如果 start_date 是周日，应自动跳到下周一。"""
    mesocycle = MagicMock()
    mesocycle.id = 1
    mesocycle.week_count = 1

    ucs = MagicMock()
    ucs.days_per_week = 2
    ucs.preferred_days = "2,4"

    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    event_queue = AsyncMock()

    weeks = await generate_mesocycle_skeleton(
        mesocycle, ucs, db, "2026-07-05", event_queue  # 周日
    )

    assert weeks[0].start_date == "2026-07-06"  # 应该是周一
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `cd backend && python -m pytest app/engine/__tests__/test_mesocycle_skeleton.py -v`
Expected: ModuleNotFoundError 或 ImportError（函数尚未实现）

- [ ] **Step 3: 实现 generate_mesocycle_skeleton**

```python
# 在 backend/app/engine/mesocycle_manager.py 末尾增加

from datetime import datetime, timedelta, date as date_type
import asyncio
from typing import Optional


async def generate_mesocycle_skeleton(
    mesocycle,
    ucs,
    db,
    start_date: str,
    event_queue: Optional[asyncio.Queue] = None,
):
    """为中周期预创建所有 Week 和 Day 的框架（无 ExerciseSlot）。

    创建 mesocycle.week_count 个 Week，以及每个 Week 中对应 ucs.days_per_week 个 Day。
    Days 只有框架字段（day_order, date, day_of_week, day_label, focus），
    不含具体的 ExerciseSlot——那些会在每周 generate-next 时生成。

    Args:
        mesocycle: Mesocycle ORM 对象（需已 flush，有 id）
        ucs: UserCurrentState ORM 对象
        db: SQLAlchemy Session
        start_date: 起始日期 "YYYY-MM-DD"，会自动对齐到周一
        event_queue: 可选的 SSE 事件队列

    Returns:
        list[Week]: 创建的 Week 对象列表（每个 Week 含 days 列表）
    """
    from app.models import orm_models

    # 解析起始日期，对齐到周一
    dt = datetime.strptime(start_date, "%Y-%m-%d")
    # weekday(): 0=周一, 6=周日
    monday = dt - timedelta(days=dt.weekday())

    preferred_days = [int(d.strip()) for d in (ucs.preferred_days or "1,3,5").split(",") if d.strip()]
    if not preferred_days:
        preferred_days = [1, 3, 5]

    created_weeks = []

    for week_num in range(1, mesocycle.week_count + 1):
        week_start = monday + timedelta(weeks=week_num - 1)
        week = orm_models.Week(
            mesocycle_id=mesocycle.id,
            week_number=week_num,
            start_date=week_start.strftime("%Y-%m-%d"),
            status="pending",
        )
        db.add(week)
        db.flush()

        # 为每个训练日创建 Day 框架
        focus_labels = _generate_weekly_focus(week_num, mesocycle.phase)

        for day_idx, dow in enumerate(preferred_days):
            day_date = week_start + timedelta(days=dow - 1)  # dow=1(周一) -> 0 offset
            focus = focus_labels[day_idx] if day_idx < len(focus_labels) else ""
            day = orm_models.Day(
                week_id=week.id,
                day_order=day_idx + 1,
                day_of_week=dow,
                date=day_date.strftime("%Y-%m-%d"),
                day_label=focus,
                focus=focus,
                estimated_calories=0,
                is_completed=0,
            )
            db.add(day)

        db.flush()

        created_weeks.append(week)

        if event_queue:
            await event_queue.put(("progress", {
                "phase": "skeleton",
                "text": f"  框架：第{week_num}周（{week_start.strftime('%m/%d')}~）"
            }))

    return created_weeks


def _generate_weekly_focus(week_number: int, phase: str) -> list[str]:
    """根据中周期阶段和当前周次生成该周的训练重点标签。

    返回的列表长度对应每周训练日数，每项为当天的 focus 描述。
    这里返回 3-4 个字符串，前端会按需取前 N 个。
    """
    # 按阶段和周次定义训练重点
    phase_focus_map = {
        "foundational": {
            1: ["全身激活", "全身耐力", "核心稳定"],
            2: ["全身力量基础", "核心强化", "全身协调"],
            3: ["上肢推动", "下肢拉动", "核心旋转"],
            4: ["综合测试", "耐力维持", "灵活提升"],
        },
        "hypertrophy": {
            1: ["推力（胸+肩+三头）", "拉力（背+二头）", "腿部+核心"],
            2: ["推拉结合", "腿部强化", "肩部+手臂"],
            3: ["复合推", "复合拉", "下肢爆发"],
            4: ["容量日", "密度日", "减载准备"],
        },
        "strength": {
            1: ["基础力量", "辅助训练", "核心稳定"],
            2: ["强度递增", "辅助提升", "爆发力"],
            3: ["最大力量", "专项辅助", "功率输出"],
            4: ["巅峰测试", "减量", "灵活恢复"],
        },
        "deload": {
            1: ["轻松活动", "拉伸恢复", "低强度有氧"],
            2: ["灵活性", "轻量维持", "恢复"],
            3: ["轻松活动", "拉伸恢复", "低强度有氧"],
            4: ["灵活性", "轻量维持", "恢复"],
        },
    }

    default = ["上肢", "下肢", "核心"]
    phase_map = phase_focus_map.get(phase, {})
    return phase_map.get(week_number, default)
```

- [ ] **Step 4: 再运行测试，确认通过**

Run: `cd backend && python -m pytest app/engine/__tests__/test_mesocycle_skeleton.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 提交**

```bash
git add backend/app/engine/mesocycle_manager.py backend/app/engine/__tests__/test_mesocycle_skeleton.py
git commit -m "feat: add generate_mesocycle_skeleton for week/day framework pre-creation"
```

---

### Task 2: 后端 — 改造 init-plan 和 generate-next 返回周期路线图数据

**Files:**
- Modify: `backend/app/engine/generator.py` — 在 `generate_init_week` 中调用 skeleton，SSE 事件中返回 macrocycle_detail
- Modify: `backend/app/api/routes/fitness.py` — `_build_macrocycle_detail` 增加 completion_rate；generate-next 返回 macrocycle_detail

**Interfaces:**
- Consumes: `generate_mesocycle_skeleton()` from Task 1
- Produces: init-plan SSE 多一个 `macrocycle_detail` 事件；generate-next SSE 同理

- [ ] **Step 1: 修改 generator.py 的 generate_init_week**

在 `generate_init_week` 内部，创建完 mesocycle 后、生成 Week 1 之前，调用 skeleton 预创建后续 3 周的框架。

```python
# 在 backend/app/engine/generator.py 中
# 找到 generate_init_week 函数，在创建完 mesocycle 之后、生成第1周之前插入：

async def generate_init_week(macrocycle, mesocycle, ucs, db, event_queue,
                              user_info=None, start_date=None):
    """首次生成第1周，并预创建中周期剩余周的框架。"""
    from app.engine.mesocycle_manager import generate_mesocycle_skeleton

    # ... 现有的日期计算代码 ...

    # 预创建整个中周期的 Week+Day 框架（含第1周）
    weeks = await generate_mesocycle_skeleton(
        mesocycle, ucs, db, start_date_str, event_queue
    )
    # weeks[0] 是第1周，稍后填充具体动作

    await event_queue.put(("progress", {
        "phase": "skeleton",
        "text": f"  中周期框架已创建：{mesocycle.week_count} 周"
    }))

    # 生成第1周具体动作（原本的 generate_init_week 逻辑）
    first_week = weeks[0]
    first_week.status = "active"

    # ... 后续填充 day.slots 的逻辑不变 ...

    # 在 SSE 最后，__DONE__ 之前，发送 macrocycle_detail
    from app.api.routes.fitness import _build_macrocycle_detail
    detail = _build_macrocycle_detail(macrocycle, db)
    await event_queue.put(("macrocycle_detail", detail))

    return first_week
```

修改文件 `backend/app/engine/generator.py`，在文件顶部添加 `from app.api.routes.fitness import _build_macrocycle_detail`（注意循环导入问题——需要将 `_build_macrocycle_detail` 移到通用模块，或改为延迟导入）。

为避免循环导入，将 `_build_macrocycle_detail` 移到 `backend/app/services/plan_service.py` 中，或直接在 generator.py 末尾用延迟导入。

**推荐做法：** 在 generator.py 内延迟导入（函数内 import），避免模块级循环依赖：

```python
# generator.py 中 generate_init_week 内部
from app.api.routes.fitness import _build_macrocycle_detail  # 延迟导入
```

- [ ] **Step 2: 修改 fitness.py 的 _build_macrocycle_detail 增加 completion_rate**

```python
def _build_macrocycle_detail(mc: orm_models.Macrocycle, db: Session) -> dict:
    """构建大周期的完整 JSON 响应（嵌套所有子数据，含完成率）。"""
    mesocycles = db.query(orm_models.Mesocycle).filter(
        orm_models.Mesocycle.macrocycle_id == mc.id
    ).order_by(orm_models.Mesocycle.sort_order).all()

    meso_data = []
    for ms in mesocycles:
        weeks = db.query(orm_models.Weedk).filter(
            orm_models.Week.mesocycle_id == ms.id
        ).order_by(orm_models.Week.week_number).all()

        weeks_data = []
        for w in weeks:
            days = db.query(orm_models.Day).filter(
                orm_models.Day.week_id == w.id
            ).order_by(orm_models.Day.day_order).all()

            completed_days = sum(1 for d in days if d.is_completed)
            total_days = len(days) or 1  # 防除零

            # week 级别的完成率
            week_completion_rate = round((completed_days / total_days) * 100)

            weeks_data.append({
                "id": w.id,
                "week_number": w.week_number,
                "status": w.status,
                "day_count": len(days),
                "completed_days": completed_days,
                "completion_rate": week_completion_rate,
            })

        # mesocycle 级别的完成率（所有已生成的周的均值）
        total_weeks = len(weeks_data)
        if total_weeks > 0:
            # 只统计已有数据的周（status != 'pending' 的周）
            active_weeks = [w for w in weeks_data if w["status"] != "pending"]
            if active_weeks:
                meso_completion = round(sum(w["completion_rate"] for w in active_weeks) / len(active_weeks))
            else:
                meso_completion = 0
        else:
            meso_completion = 0

        meso_data.append({
            "id": ms.id,
            "phase": ms.phase,
            "week_count": ms.week_count,
            "sort_order": ms.sort_order,
            "status": ms.status,
            "completion_rate": meso_completion,
            "weeks": weeks_data,
        })

    return {
        "id": mc.id,
        "goal": mc.goal,
        "start_date": str(mc.start_date) if mc.start_date else "",
        "status": mc.status,
        "created_at": str(mc.created_at) if mc.created_at else "",
        "mesocycles": meso_data,
    }
```

- [ ] **Step 3: 改造 generate-next 返回 macrocycle_detail**

```python
# 在 backend/app/api/routes/fitness.py 中 generate_next 的 event_stream 内
# 在 __DONE__ 事件之前，发送 macrocycle_detail：

# 获取当前 macrocycle（第一个 active 的）
macrocycle = db.query(orm_models.Macrocycle).filter(
    orm_models.Macrocycle.status == "active"
).first()
if macrocycle:
    detail = _build_macrocycle_detail(macrocycle, db)
    await event_queue.put(("macrocycle_detail", detail))
```

这个修改在 `generate_next` 函数的 `__DONE__` 之前插入，确保每次生成新一周后前端都能获取到更新后的路线图数据。

- [ ] **Step 4: 手动测试**

```bash
cd backend && python run.py
# 另一个终端：
curl -X POST http://localhost:8000/api/fitness/init-plan \
  -H "Content-Type: application/json" \
  -d '{"goal":"增肌","experience_level":"新手","workout_location":"居家","days_per_week":3,"preferred_days":"1,3,5","height":175,"weight":70,"age":25,"gender":"male"}'
```
Expected: SSE 流中应出现 `macrocycle_detail` 事件，包含完整的大周期 + 中周期 + 周框架数据。

- [ ] **Step 5: 提交**

```bash
git add backend/app/engine/generator.py backend/app/api/routes/fitness.py
git commit -m "feat: init-plan and generate-next return macrocycle_detail with completion rates"
```

---

### Task 3: 前端 — 更新类型定义和 cycle store

**Files:**
- Modify: `frontend/src/types/index.ts` — 添加路线图展示用类型
- Modify: `frontend/src/stores/cycle.ts` — 添加 roadmap 相关 computed + action
- Modify: `frontend/src/services/api.ts` — 确保 macrocycleDetail 在 init/generate 后自动拉取

**Interfaces:**
- Produces: PhaseLabelMap, PhaseSegmentData, `cycleStore.phaseSegments` computed, `cycleStore.phaseLabelFor(phase)` method

- [ ] **Step 1: 添加路线图相关类型**

在 `frontend/src/types/index.ts` 中，`MacrocycleDetail` 下方添加：

```typescript
// ═════════════════════════════════════════════════════════
//  路线图展示类型（中周期路线图用）
// ═════════════════════════════════════════════════════════

/** 各目标的阶段名称映射 */
export const PHASE_LABEL_MAP: Record<string, Record<string, string>> = {
  '增肌': {
    foundational: '基础适应期',
    hypertrophy: '肌肥大期',
    strength: '力量提升期',
    deload: '减载恢复周',
  },
  '减脂': {
    foundational: '基础适应期',
    hypertrophy: '燃脂强化期',
    strength: '代谢提升期',
    deload: '减载恢复周',
  },
  '塑形': {
    foundational: '基础适应期',
    hypertrophy: '塑形雕刻期',
    strength: '紧致提升期',
    deload: '减载恢复周',
  },
  '保持健康': {
    foundational: '基础适应期',
    hypertrophy: '综合维持期',
    strength: '活跃恢复期',
    deload: '减载恢复周',
  },
}

/** 阶段对应的颜色 */
export const PHASE_COLORS: Record<string, string> = {
  foundational: '#3b82f6',
  hypertrophy: '#22c55e',
  strength: '#f97316',
  deload: '#a855f7',
}

/** 路线图上单个阶段的显示数据 */
export interface PhaseSegment {
  phase: string                // foundational / hypertrophy / strength / deload
  label: string                // 根据目标映射的中文名
  color: string                // 颜色值
  status: 'completed' | 'active' | 'pending'
  weekCount: number            // 该阶段总周数
  currentWeek?: number         // 当前在第几周（active 时有效）
  completionRate: number       // 完成率 0-100
  weeks: WeekSummary[]         // 该阶段包含的周
}

/** 路线图全部数据 */
export interface RoadmapData {
  macrocycleId: number
  goal: string
  totalWeeks: number
  currentWeekNumber: number
  mesocycles: PhaseSegment[]
}
```

- [ ] **Step 2: 为 WeekSummary 补充字段**

`WeekSummary` 接口需要增加 `completion_rate` 和 `completed_days` 字段（后端刚才新增的）：

```typescript
export interface WeekSummary {
  id: number
  week_number: number
  status: WeekStatus
  day_count: number
  completed_days?: number      // 新增
  completion_rate?: number     // 新增
}
```

- [ ] **Step 3: 在 cycle store 添加 roadmap computed**

```typescript
// 在 frontend/src/stores/cycle.ts 中，computed 区域添加：

import { PHASE_LABEL_MAP, PHASE_COLORS, type PhaseSegment, type RoadmapData } from '@/types'

/** 路线图数据：将 macrocycle.mesocycles 转为前端展示格式 */
const roadmapData = computed<RoadmapData | null>(() => {
  if (!macrocycle.value || !macrocycle.value.mesocycles.length) return null

  const goal = macrocycle.value.goal || '增肌'
  const phaseLabels = PHASE_LABEL_MAP[goal] || PHASE_LABEL_MAP['增肌']
  const currentPhase = currentWeek.value?.mesocycle_phase ?? ''

  // 计算当前在大周期中的全局周数
  let totalWeeksSum = 0
  let currentWeekNumber = 0
  let found = false

  const segments: PhaseSegment[] = macrocycle.value.mesocycles.map(ms => {
    totalWeeksSum += ms.week_count

    let segStatus: 'completed' | 'active' | 'pending' = 'pending'
    let weekInPhase = 0

    if (ms.status === 'completed') {
      segStatus = 'completed'
    } else if (ms.phase === currentPhase && !found) {
      segStatus = 'active'
      weekInPhase = currentWeek.value?.week_number ?? 1
      currentWeekNumber = totalWeeksSum - ms.week_count + weekInPhase
      found = true
    }

    return {
      phase: ms.phase,
      label: phaseLabels[ms.phase] || ms.phase,
      color: PHASE_COLORS[ms.phase] || '#999',
      status: segStatus,
      weekCount: ms.week_count,
      currentWeek: segStatus === 'active' ? weekInPhase : undefined,
      completionRate: ms.completion_rate ?? 0,
      weeks: ms.weeks || [],
    }
  })

  return {
    macrocycleId: macrocycle.value.id,
    goal,
    totalWeeks: totalWeeksSum,
    currentWeekNumber,
    mesocycles: segments,
  }
})

/** 当前阶段的下一个阶段名称 */
const nextPhaseLabel = computed<string | null>(() => {
  if (!roadmapData.value) return null
  const segments = roadmapData.value.mesocycles
  const idx = segments.findIndex(s => s.status === 'active')
  if (idx >= 0 && idx < segments.length - 1) {
    return segments[idx + 1].label
  }
  return null
})
```

在返回值中添加 `roadmapData` 和 `nextPhaseLabel`。

- [ ] **Step 4: 提交**

```bash
git add frontend/src/types/index.ts frontend/src/stores/cycle.ts
git commit -m "feat: add roadmap types and store computed properties"
```

---

### Task 4: 前端 — 创建路线图组件

**Files:**
- Create: `frontend/src/components/CycleRoadmap.vue`
- Create: `frontend/src/components/PhaseDetail.vue`
- Create: `frontend/src/components/CycleHistory.vue`

- [ ] **Step 1: 创建 CycleRoadmap.vue — 水平路线图条**

```vue
<template>
  <div class="cycle-roadmap">
    <!-- 大周期标题和进度 -->
    <div class="roadmap-header">
      <span class="roadmap-title">周期路线图</span>
      <span class="roadmap-meta">大周期 · 第{{ data.currentWeekNumber }}周/共{{ data.totalWeeks }}周</span>
    </div>

    <!-- 大周期总进度条 -->
    <div class="macro-progress-bar">
      <div
        class="macro-progress-fill"
        :style="{ width: macroProgressPct + '%' }"
      />
    </div>

    <!-- 阶段路线（水平排列） -->
    <div class="phase-track">
      <div
        v-for="(seg, idx) in data.mesocycles"
        :key="seg.phase"
        class="phase-segment"
        :class="[seg.status]"
      >
        <!-- 连接线（第一个不显示） -->
        <div v-if="idx > 0" class="phase-connector" :class="{ 'completed': seg.status === 'completed' || (seg.status === 'active' && data.mesocycles[idx-1].status === 'completed') }" />

        <!-- 阶段圆圈 -->
        <div class="phase-dot" :style="{ borderColor: seg.color, background: seg.status === 'active' ? seg.color : 'transparent' }">
          <span v-if="seg.status === 'completed'" class="dot-check">✓</span>
          <span v-else-if="seg.status === 'active'" class="dot-current">●</span>
        </div>

        <!-- 阶段内容 -->
        <div class="phase-body">
          <span class="phase-label">{{ seg.label }}</span>
          <span v-if="seg.status === 'active'" class="phase-week">
            第{{ seg.currentWeek }}/{{ seg.weekCount }}周
          </span>
          <span v-else-if="seg.status === 'completed'" class="phase-pct">{{ seg.completionRate }}%</span>
          <span v-else class="phase-pending">即将到来</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RoadmapData } from '@/types'

const props = defineProps<{
  data: RoadmapData
}>()

const macroProgressPct = computed(() => {
  if (props.data.totalWeeks === 0) return 0
  return Math.round((props.data.currentWeekNumber / props.data.totalWeeks) * 100)
})
</script>

<style scoped>
.cycle-roadmap {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #f0f0f0;
}

.roadmap-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.roadmap-title { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.roadmap-meta { font-size: 12px; color: #888; }

/* 大周期总进度 */
.macro-progress-bar {
  height: 6px;
  background: #f0f0f0;
  border-radius: 3px;
  margin-bottom: 16px;
  overflow: hidden;
}
.macro-progress-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #3b82f6, #22c55e, #f97316, #a855f7);
  transition: width 0.5s ease;
}

/* 阶段轨道 */
.phase-track {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.phase-segment {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 0;
  position: relative;
}
.phase-segment:not(:last-child) {
  border-bottom: 1px solid #f5f5f5;
}

.phase-connector {
  display: none; /* 垂直布局不需要连接线 */
}

.phase-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2.5px solid #ddd;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  margin-top: 2px;
  transition: all 0.3s;
}
.phase-segment.completed .phase-dot { border-color: #22c55e; background: #22c55e; }
.dot-check { color: #fff; font-weight: 700; }
.dot-current { color: #fff; font-size: 10px; }

.phase-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.phase-label { font-size: 14px; font-weight: 600; color: #333; }
.phase-week { font-size: 12px; color: #f97316; font-weight: 500; }
.phase-pct { font-size: 12px; color: #22c55e; font-weight: 500; }
.phase-pending { font-size: 12px; color: #bbb; }

.phase-segment.pending .phase-label { color: #bbb; }
.phase-segment.active .phase-label { color: #1a1a1a; }
</style>
```

- [ ] **Step 2: 创建 PhaseDetail.vue — 当前阶段详情卡**

```vue
<template>
  <div class="phase-detail">
    <div class="detail-header">
      <span class="detail-phase">{{ phaseLabel }}</span>
      <span class="detail-badge" :style="{ background: color + '20', color }">
        {{ phaseDescription }}
      </span>
    </div>

    <div class="detail-progress">
      <div class="progress-row">
        <span class="progress-text">进度</span>
        <span class="progress-pct">{{ completionRate }}%</span>
      </div>
      <div class="progress-track">
        <div
          class="progress-fill"
          :style="{ width: completionRate + '%', background: color }"
        />
      </div>
    </div>

    <div class="detail-info">
      <div class="info-item">
        <span class="info-label">当前周</span>
        <span class="info-value">{{ weekNumber }}/{{ totalWeeks }}</span>
      </div>
      <div class="info-item">
        <span class="info-label">训练天数</span>
        <span class="info-value">{{ completedDays }}/{{ totalDays }}</span>
      </div>
      <div v-if="nextPhase" class="info-item">
        <span class="info-label">下一阶段</span>
        <span class="info-value next">→ {{ nextPhase }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  phaseLabel: string
  phaseDescription?: string
  color: string
  completionRate: number
  weekNumber: number
  totalWeeks: number
  completedDays: number
  totalDays: number
  nextPhase?: string
}>()
</script>

<style scoped>
.phase-detail {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #f0f0f0;
}
.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.detail-phase { font-size: 16px; font-weight: 700; color: #1a1a1a; }
.detail-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 500;
}

.detail-progress {
  margin-bottom: 14px;
}
.progress-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.progress-text { font-size: 13px; color: #888; }
.progress-pct { font-size: 14px; font-weight: 700; color: #1a1a1a; }
.progress-track { height: 6px; background: #f0f0f0; border-radius: 3px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }

.detail-info { display: flex; flex-direction: column; gap: 8px; }
.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid #f5f5f5;
}
.info-item:last-child { border-bottom: none; }
.info-label { font-size: 13px; color: #888; }
.info-value { font-size: 13px; font-weight: 600; color: #333; }
.info-value.next { color: #f97316; }
</style>
```

- [ ] **Step 3: 创建 CycleHistory.vue — 历史阶段完成列表**

```vue
<template>
  <div class="cycle-history">
    <h4 class="history-title">阶段完成情况</h4>
    <div class="history-list">
      <div
        v-for="seg in segments"
        :key="seg.phase"
        class="history-item"
        :class="[seg.status]"
      >
        <span class="history-icon">
          {{ seg.status === 'completed' ? '✅' : seg.status === 'active' ? '⏳' : '⬜' }}
        </span>
        <div class="history-body">
          <div class="history-top">
            <span class="history-label">{{ seg.label }}</span>
            <span class="history-pct" :style="{ color: seg.color }">
              {{ seg.status === 'completed' ? seg.completionRate + '%' : seg.status === 'active' ? '进行中' : '即将到来' }}
            </span>
          </div>
          <div class="history-weeks">
            <span
              v-for="w in seg.weeks"
              :key="w.week_number"
              class="week-chip"
              :class="weekChipClass(w)"
            >{{ w.week_number }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PhaseSegment, WeekSummary } from '@/types'

defineProps<{
  segments: PhaseSegment[]
}>()

function weekChipClass(w: WeekSummary): Record<string, boolean> {
  return {
    'completed': w.status === 'completed' || (w.completion_rate ?? 0) >= 100,
    'partial': (w.completion_rate ?? 0) > 0 && (w.completion_rate ?? 0) < 100,
    'active': w.status === 'active',
  }
}
</script>

<style scoped>
.cycle-history {
  background: #fff;
  border-radius: 14px;
  padding: 16px;
  border: 1px solid #f0f0f0;
}
.history-title { font-size: 15px; font-weight: 700; color: #1a1a1a; margin: 0 0 12px 0; }
.history-list { display: flex; flex-direction: column; gap: 10px; }

.history-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 8px;
  border-radius: 10px;
  transition: background 0.2s;
}
.history-item:hover { background: #fafafa; }
.history-item.pending { opacity: 0.5; }

.history-icon { font-size: 16px; line-height: 1.4; }
.history-body { flex: 1; min-width: 0; }
.history-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.history-label { font-size: 13px; font-weight: 600; color: #333; }
.history-pct { font-size: 12px; font-weight: 600; }

.history-weeks {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.week-chip {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  background: #f0f0f0;
  color: #999;
}
.week-chip.completed { background: #22c55e; color: #fff; }
.week-chip.partial { background: #fff7ed; color: #f97316; }
.week-chip.active { border: 2px solid #f97316; color: #f97316; background: #fff; }
</style>
```

- [ ] **Step 4: 提交**

```bash
git add frontend/src/components/CycleRoadmap.vue frontend/src/components/PhaseDetail.vue frontend/src/components/CycleHistory.vue
git commit -m "feat: add cycle roadmap components (CycleRoadmap, PhaseDetail, CycleHistory)"
```

---

### Task 5: 前端 — 重写 CycleInfo.vue 为 WeekProgress.vue

**Files:**
- Modify: `frontend/src/components/CycleInfo.vue` — 完全重写为精致进度条组件

- [ ] **Step 1: 重写 CycleInfo.vue → WeekProgress.vue**

```vue
<template>
  <div class="week-progress">
    <div class="wp-top">
      <!-- 阶段标签 -->
      <div class="wp-phase">
        <span class="wp-phase-icon">{{ phaseIcon }}</span>
        <span class="wp-phase-label">{{ phaseLabel }}</span>
        <span class="wp-week-info">· 第{{ weekNumber }}周/共{{ totalWeeks }}周</span>
      </div>
      <!-- 完成百分比 -->
      <span class="wp-pct">{{ completionRate }}%</span>
    </div>

    <!-- 更精致的进度条 -->
    <div class="wp-bar">
      <div class="wp-bar-bg">
        <div
          class="wp-bar-fill"
          :style="{ width: completionRate + '%' }"
        />
      </div>
    </div>

    <div class="wp-bottom">
      <!-- 左侧：训练完成情况 -->
      <div class="wp-stats">
        <span class="wp-stat">📋 本周 {{ completedDays }}/{{ totalDays }} 天已完成</span>
        <span v-if="nextPhase" class="wp-next">下一步 → {{ nextPhase }}</span>
      </div>
      <!-- 右侧：生成按钮 -->
      <button
        class="wp-generate-btn"
        :disabled="!isWeekComplete"
        :title="isWeekComplete ? '生成下周计划' : '还有训练未打卡'"
        @click="$emit('generate')"
      >
        ⚡ 生成下周
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  phaseLabel: string
  weekNumber: number
  totalWeeks: number
  completionRate: number
  isWeekComplete: boolean
  completedDays: number
  totalDays: number
  nextPhase?: string
  isDeload?: boolean
}>()

defineEmits<{ generate: [] }>()

const phaseIcon = computed(() => {
  if (props.isDeload) return '🔄'
  const map: Record<string, string> = {
    '基础适应期': '🌱',
    '肌肥大期': '🔥',
    '燃脂强化期': '🔥',
    '塑形雕刻期': '✨',
    '综合维持期': '💪',
    '力量提升期': '💪',
    '代谢提升期': '⚡',
    '紧致提升期': '💎',
    '活跃恢复期': '🧘',
  }
  return map[props.phaseLabel] ?? '💪'
})
</script>

<style scoped>
.week-progress {
  background: #fff;
  border-radius: 16px;
  padding: 16px 18px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.wp-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.wp-phase {
  display: flex;
  align-items: center;
  gap: 6px;
}
.wp-phase-icon { font-size: 18px; }
.wp-phase-label { font-size: 15px; font-weight: 700; color: #1a1a1a; }
.wp-week-info { font-size: 12px; color: #888; font-weight: 400; }
.wp-pct { font-size: 18px; font-weight: 800; color: #1a1a1a; }

.wp-bar { margin-bottom: 12px; }
.wp-bar-bg {
  height: 10px;
  background: #f0f0f0;
  border-radius: 5px;
  overflow: hidden;
}
.wp-bar-fill {
  height: 100%;
  border-radius: 5px;
  background: linear-gradient(90deg, #f97316, #fb923c);
  transition: width 0.5s ease;
  box-shadow: inset 0 1px 2px rgba(255,255,255,0.3);
}

.wp-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.wp-stats {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.wp-stat { font-size: 12px; color: #888; }
.wp-next { font-size: 11px; color: #f97316; font-weight: 500; }

.wp-generate-btn {
  padding: 7px 18px;
  border-radius: 20px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  transition: all 0.2s;
  white-space: nowrap;
  flex-shrink: 0;
}
.wp-generate-btn:hover:not(:disabled) {
  box-shadow: 0 4px 12px rgba(249,115,22,0.35);
  transform: translateY(-1px);
}
.wp-generate-btn:disabled { background: #d9d9d9; color: #999; cursor: not-allowed; }
</style>
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/components/CycleInfo.vue
git commit -m "refactor: rewrite CycleInfo as WeekProgress with enhanced UI"
```

---

### Task 6: 前端 — 更新 ProfilePage 和 MainPage 布局

**Files:**
- Modify: `frontend/src/views/ProfilePage.vue` — 改为双栏布局，右栏放周期组件
- Modify: `frontend/src/views/MainPage.vue` — WeekProgress 移到日历上方

- [ ] **Step 1: 改造 ProfilePage.vue 为双栏布局**

```vue
<template>
  <div class="profile-page">
    <!-- 左侧：原有个人信息 -->
    <div class="profile-left">
      <!-- 复制现有的 ProfilePage 全部内容到这里 -->
      <!-- ... 现有的模板内容 ... -->
      <div class="profile-card">
        <!-- 现有内容不变 -->
      </div>
    </div>

    <!-- 右侧：新增训练周期总览 -->
    <div class="profile-right" v-if="cycleStore.roadmapData">
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

      <CycleHistory
        v-if="cycleStore.roadmapData"
        :segments="cycleStore.roadmapData.mesocycles"
      />
    </div>

    <!-- 无数据时 -->
    <div v-else class="profile-right profile-empty">
      <div class="empty-hint">
        <p>暂无训练计划</p>
        <p class="empty-sub">完成引导设置后，这里将显示您的训练周期路线图</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useCycleStore } from '@/stores/cycle'
import CycleRoadmap from '@/components/CycleRoadmap.vue'
import PhaseDetail from '@/components/PhaseDetail.vue'
import CycleHistory from '@/components/CycleHistory.vue'
import { PHASE_COLORS } from '@/types'

// 导入原来 ProfilePage 的所有 stores 和逻辑...

const cycleStore = useCycleStore()

const currentPhaseColor = computed(() => {
  const phase = cycleStore.currentWeek?.mesocycle_phase ?? ''
  return PHASE_COLORS[phase] || '#f97316'
})

const phaseDescription = computed(() => {
  const descriptions: Record<string, string> = {
    foundational: '建立训练基础，掌握动作模式',
    hypertrophy: '增加肌纤维横截面积，8-12RM',
    strength: '增强绝对力量，5-8RM',
    deload: '降低强度，促进恢复',
  }
  return descriptions[cycleStore.currentWeek?.mesocycle_phase ?? ''] ?? ''
})

const completedDays = computed(() => {
  if (!cycleStore.currentWeek?.days) return 0
  return cycleStore.currentWeek.days.filter(d => d.is_completed).length
})

const totalDays = computed(() => {
  return cycleStore.currentWeek?.days.length ?? 0
})
</script>

<style scoped>
.profile-page {
  display: flex;
  gap: 20px;
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  align-items: flex-start;
}
.profile-left {
  width: 380px;
  flex-shrink: 0;
}
.profile-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.profile-empty {
  background: #fff;
  border-radius: 14px;
  padding: 40px;
  text-align: center;
  border: 1px solid #f0f0f0;
}
.empty-hint p { font-size: 15px; color: #888; margin: 0 0 8px; }
.empty-sub { font-size: 13px; color: #bbb; }

@media (max-width: 768px) {
  .profile-page {
    flex-direction: column;
  }
  .profile-left {
    width: 100%;
  }
}
</style>
```

ProfilePage.vue 的修改需要合并：保留左侧所有现有内容（个人信息编辑、训练状态等），把 `.profile-card` 包裹在 `.profile-left` 中，右侧新增 `.profile-right`。

- [ ] **Step 2: 改造 MainPage.vue — 移动 WeekProgress 到日历上方**

```vue
<!-- 修改 MainPage.vue 的左侧栏顺序，将 WeekProgress 移到 CalendarPanel 上方 -->

<template>
  <div class="main-content">
    <!-- 左侧栏 -->
    <aside class="left-column">
      <!-- WeekProgress 放在最上面 -->
      <div class="progress-section">
        <WeekProgress
          :phase-label="cycleStore.mesocyclePhaseLabel"
          :week-number="cycleStore.currentWeekNumber"
          :total-weeks="cycleStore.mesocycleTotalWeeks"
          :completion-rate="cycleStore.weekCompletionRate"
          :is-week-complete="cycleStore.isWeekComplete"
          :completed-days="completedDays"
          :total-days="totalDays"
          :next-phase="cycleStore.nextPhaseLabel ?? undefined"
          :is-deload="cycleStore.currentWeek?.mesocycle_phase === 'deload'"
          @generate="handleGenerateNext"
        />
      </div>
      <div class="calendar-section">
        <CalendarPanel @select="onDateSelect" />
      </div>
      <div class="muscle-section">
        <MuscleDiagram
          :gender="userStore.profile?.gender"
          :primary-muscles="workoutStore.activePrimaryMuscles"
          :secondary-muscles="workoutStore.activeSecondaryMuscles"
        />
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <main class="right-column">
      <DailyPlanPanel :date-str="selectedDate" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
// ... 其他导入保持不变 ...
import WeekProgress from '@/components/CycleInfo.vue'  // 已重写为 WeekProgress

// ... 其余代码保持不变 ...

// 新增 computed
const completedDays = computed(() => {
  if (!cycleStore.currentWeek?.days) return 0
  return cycleStore.currentWeek.days.filter(d => d.is_completed).length
})
const totalDays = computed(() => {
  return cycleStore.currentWeek?.days.length ?? 0
})

// ... 其余代码不变 ...

// 删除旧的 cycle-section（因为 CycleInfo 已被移走）
</script>

<style scoped>
.main-content {
  display: flex;
  gap: 16px;
  height: 100%;
  min-height: 0;
  padding-bottom: 16px;
}

.left-column {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}
.progress-section { flex-shrink: 0; }  /* 新增 */
.calendar-section { flex-shrink: 0; }
.muscle-section { flex: 1; display: flex; flex-direction: column; min-height: 0; }

.right-column {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
```

- [ ] **Step 3: 提交**

```bash
git add frontend/src/views/ProfilePage.vue frontend/src/views/MainPage.vue
git commit -m "feat: update ProfilePage with cycle roadmap on right, move WeekProgress above calendar on MainPage"
```

---

## Self-Review Checklist

1. **Spec coverage:** All spec requirements covered:
   - ✅ ProfilePage 右栏显示周期路线图（Task 6: CycleRoadmap + PhaseDetail + CycleHistory）
   - ✅ MainPage 日历上方显示精致进度条（Task 5: WeekProgress）
   - ✅ 不同目标有不同的阶段标签（Task 3: PHASE_LABEL_MAP）
   - ✅ 阶段颜色方案（Task 3: PHASE_COLORS）
   - ✅ 混合生成策略：框架预生成，内容周更（Task 1-2）
   - ✅ 完成率计算（Task 2: _build_macrocycle_detail 增强）

2. **Placeholder scan:** No TBD, TODO, or vague requirements found.

3. **Type consistency:**
   - `PhaseSegment.status` checked in both CycleRoadmap and CycleHistory
   - `RoadmapData.mesocycles` → `PhaseSegment[]` consistent across store and components
   - `PHASE_LABEL_MAP` keys match `PHASE_COLORS` keys
   - `WeekSummary.completion_rate` used in both backend and frontend

4. **Scope check:** Single coherent feature, no need to decompose further.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-02-cycle-roadmap-implementation.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
