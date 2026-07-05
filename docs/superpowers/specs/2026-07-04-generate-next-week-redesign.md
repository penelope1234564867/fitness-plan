# generate_next_week 重构设计

> 2026-07-04 | 状态：草稿

## 背景与问题

当前 `generate_next_week()` 的核心问题是：它不是在"生成"下一周，而是在"复制"上一周。

### 已确认的 6 个问题

| # | 问题 | 严重程度 | 位置 |
|---|------|---------|------|
| 1 | `generate_next_week` 遍历 `prev_day.slots` 直接复制，不调 LLM、不搜 wger、不走 `assemble_one_day` | **致命** | `generator.py:543-570` |
| 2 | 中周期边界轮换代码 `int.get()` 必定崩溃 | **致命** | `generator.py:547-550` |
| 3 | 热身 8-10 个硬编码，无 AI，每周一样 | **高** | `plan_assembler.py:160-173` |
| 4 | 不读用户历史数据，只读前一周 | **中** | `generator.py:425-428` |
| 5 | N+1 查询导致性能问题 | **中** | `generator.py:426-427` |
| 6 | `generate_next_week` 和 `generate_init_week` 架构不对称 | **中** | 整体架构 |

### 核心设计决策

采用**方桁 A：中周期级缓存 + 每周 LLM 从池里选**

```
中周期开始 → wger 搜 20-30 个/肌群 → 缓存到本地库
中周期内   → 每周 LLM 从缓存池选不同的动作组合 + AI 热身拉伸
中周期结束 → 刷新缓存池
```

---

## 1. 数据库变更

### 1.1 新增表 `mesocycle_exercise_pool`

记录中周期内缓存在本地的 wger 动作。

```sql
CREATE TABLE mesocycle_exercise_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mesocycle_id INTEGER NOT NULL,
    wger_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    target_muscle TEXT,
    muscle_group_id INTEGER,
    equipment TEXT,
    image_url TEXT,
    description TEXT,
    difficulty INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mesocycle_id) REFERENCES mesocycles(id)
);

CREATE INDEX idx_pool_mesocycle ON mesocycle_exercise_pool(mesocycle_id);
CREATE INDEX idx_pool_muscle ON mesocycle_exercise_pool(muscle_group_id);
```

### 1.2 扩展 `UserCurrentState`

新增字段存储用户压缩历史，用于 LLM 精选时参考。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `avg_completion_rate` | REAL | 0.0 | 历史平均完成率 |
| `rpe_trend` | TEXT | 'stable' | 'rising' \| 'stable' \| 'falling' |
| `consecutive_weeks_completed` | INTEGER | 0 | 连续完整打卡周数 |
| `exercise_blacklist` | TEXT | '[]' | JSON 数组，RPE 持续高的动作名 |
| `weekly_progress` | TEXT | '[]' | JSON 数组，每周汇总 |
| `pool_loaded` | INTEGER | 0 | 当前中周期缓存池是否已加载 |

**`weekly_progress` 格式：**
```json
[
    {"week": 1, "completion_rate": 0.85, "avg_rpe": 7.2},
    {"week": 2, "completion_rate": 0.90, "avg_rpe": 7.5}
]
```

**`exercise_blacklist` 更新规则：** 连续 2 周某动作 RPE≥9 → 加入黑名单；连续 2 周 RPE≤5 → 移出黑名单。

---

## 2. 整体数据流

### 2.1 `generate_next_week()` 重构流程

```
generate_next_week(current_week, db, event_queue)
  │
  ├── 0. 查询中周期 + UserCurrentState（用户压缩历史）
  │
  ├── 1. 读取前一周 days+slots（同上）
  ├── 2. adaptive analyze_week()（同上）
  │
  ├── 3. 中周期切换判断（同上）
  │     ├── 切换 → 创建新 Mesocycle
  │     │         ├── 从 wger 搜索并填充缓存池（并行）
  │     │         └── 动作轮换（修复 bug）
  │     └── 不切换 → 使用已有缓存池
  │
  ├── 4. 创建新 Week（同上，骨架周或新建）
  │
  ├── 5. 构建排除列表（上周已选动作）
  │
  ├── 6. 从缓存池为每天构建候选数据
  │     └── 每个训练日：查对应肌群的缓存动作
  │
  ├── 7. 并行 LLM 精选 + 组装（每 天 独 立）
  │     ├── ProgrammerAgent.select_from_pool(candidates, exclude, user_state)
  │     ├── LLM 生成热身（针对主项动作）
  │     ├── LLM 排序主项
  │     ├── 有氧收尾（根据目标）
  │     └── LLM 生成拉伸（针对主项动作）
  │
  ├── 8. 自适应分析 + 双渐进调整重量/次数
  │     └── 沿用 analyze_week + calc_next_week_params
  │
  ├── 9. 串行写库（_write_slots 复用）
  │
  └── 10. 更新 UserCurrentState（压缩历史）
```

**与当前的关键区别：**
- 第 5-7 步取代了当前第 521-570 行的"遍历 prev_day.slots 复制"
- 自适应分析（第 8 步）不再作用于复制出来的 slot，而是作用于 LLM 新选的动作——但参考上周的 RPE 数据来设定初始重量
- 第 10 步结束后更新压缩历史

### 2.2 `generate_init_week()` 调整

- 在第 1 周生成完后，**自动填充缓存池**（复用已搜索的 wger 结果）
- 这样第 2 周调用 `generate_next_week` 时直接读池，不用再搜 wger

---

## 3. 缓存池管理（新增模块）

### 3.1 `PoolManager` — 缓存池操作

新建 `backend/app/engine/exercise_pool.py`：

```python
class PoolManager:
    """中周期缓存池管理——增删查。"""

    @staticmethod
    def refresh_pool(mesocycle_id: int, all_muscle_ids: list, db: Session) -> int:
        """从中周期所有目标肌群的 wger 缓存中填充池子。
        
        从 Exercise 表（已缓存的 wger 动作）中，
        按肌群挑选 20-30 个/肌群写入 mesocycle_exercise_pool。
        
        Returns:
            int: 写入的动作总数
        """

    @staticmethod
    def get_candidates(
        mesocycle_id: int,
        muscle_ids: list,
        exclude_names: list = None,
        db: Session = None,
    ) -> list:
        """获取该天的候选动作列表。"""

    @staticmethod
    def get_used_exercise_names(mesocycle_id: int, week_number: int, db: Session) -> set:
        """获取中周期内本周之前已用过的动作名集合。"""
        # 用于构建排除列表，虽然 LLM 自然多样性，但排除列表可作为辅助
```

### 3.2 填充时机

| 时机 | 动作 |
|------|------|
| `init-plan` 完成后 | 将已搜索的 wger 结果写入缓存池 |
| 中周期切换时 | 从 Exercise 表（wger 缓存）刷新缓存池 |
| 中周期内 | 只读不写 |

**从 wger 搜索结果到缓存池的链路：**

```
wger API → Exercise 表（wger_id 去重缓存） → 按肌群取 20-30 个 → 缓存池
```

第一次 init 时 wger 结果已缓存在 Exercise 表，中周期刷新时直接读 Exercise 表，不重复调 wger。

---

## 4. AI 热身 + AI 拉伸（重写 `plan_assembler.py`）

### 4.1 新增 `generate_warmup()` 

```python
def generate_warmup(
    main_exercises: list,
    user_state: dict,
    goal: str,
    location: str,
) -> list:
    """LLM 根据当天主项动作生成 4-5 个针对性热身。

    输入示例：["杠铃卧推", "哑铃飞鸟", "坐姿肩推"]
    输出示例：
    [
        {"name": "肩部环绕", "sets": 2, "reps": 10, "instruction": "..."},
        {"name": "胸椎活动", "sets": 1, "reps": 8,  "instruction": "..."},
        {"name": "弹力带扩胸", "sets": 2, "reps": 12, "instruction": "..."},
        {"name": "空杆卧推热身组", "sets": 2, "reps": 8, "instruction": "..."},
    ]
    
    约束：
    - 4-5 个动作
    - 必须与主项肌群和动作模式相关
    - 包含 1-2 个动态拉伸 + 2-3 个专项热身组
    - 用 get_fast_llm()（快速模型）
    """
```

### 4.2 新增 `generate_stretch()`

```python
def generate_stretch(
    main_exercises: list,
    user_state: dict,
) -> list:
    """LLM 根据当天主项动作生成 3-4 个针对性静态拉伸。

    输入示例：["杠铃卧推", "哑铃飞鸟", "坐姿肩推"]
    输出示例：
    [
        {"name": "门框胸大肌拉伸", "instruction": "单手扶门框，身体向前倾，保持20秒"},
        {"name": "三头肌颈后拉伸", "instruction": "举手过顶屈肘，另一手辅助轻拉"},
        {"name": "站姿肩部前束拉伸", "instruction": "手臂后伸，另一手辅助固定"},
    ]
    """
```

### 4.3 `assemble_one_day()` 调整

当前顺序：
```
_select_warmup() → LLM 排序主项 → _select_cardio() → _select_stretches()
```

改为：
```
LLM 生成热身(主项) → LLM 排序主项 → _select_cardio() → LLM 生成拉伸(主项)
```

**性能：** 热身和拉伸共享一次快速 LLM 调用（同一个 prompt 返回两个结果），避免两次调用。

### 4.4 缓存策略

同一天相同的主项组合 → 缓存热身+拉伸结果。Session 级字典缓存，不清除，因为组合数量有限。

---

## 5. 修复中周期轮换 bug

### 5.1 问题定位

`generator.py:482-483`:
```python
rotation_map = {r["slot_id"]: r["new_exercise_id"] for r in rotation_result}
# rotation_map[slot.id] = int (exercise_id)
```

`generator.py:547-550`:
```python
rotation = rotation_map[slot.id]  # ← int
wger_id = rotation.get("wger_id")   # ← AttributeError
```

### 5.2 修复方案

```python
if slot.id in rotation_map:
    new_ex_id = rotation_map[slot.id]
    rotated_ex = db.query(Exercise).filter(Exercise.id == new_ex_id).first()
    if rotated_ex:
        wger_id = rotated_ex.wger_id
        exercise_id = rotated_ex.id
```

### 5.3 重构后的轮换流程

缓存池模式下，中周期切换时的`动作轮换`含义变了——不再需要"沿变式链前进一级"，而是：

1. 刷新缓存池（从 Exercise 表重新选 20-30 个/肌群）
2. 下周 LLM 自然从新池子里选不同的

所以 `rotate_slots_for_new_mesocycle` 可以保留作为后备（没有缓存池的数据时），但主要逻辑被缓存池刷新替代。

---

## 6. 用户数据压缩

### 6.1 更新时机

在 `generate_next_week()` 末尾调用 `_update_user_state()`：

```python
def _update_user_state(
    current_week: Week,
    week_analysis: dict,
    db: Session,
):
    """更新 UserCurrentState 的压缩历史字段。"""
    ucs = db.query(UserCurrentState).first()
    if not ucs:
        return
    
    # 更新 weekly_progress
    progress = json.loads(ucs.weekly_progress or "[]")
    progress.append({
        "week": current_week.week_number,
        "completion_rate": week_analysis["completion_rate"],
        "avg_rpe": week_analysis.get("avg_rpe", 0),
    })
    if len(progress) > 10:  # 只保留最近 10 周
        progress = progress[-10:]
    ucs.weekly_progress = json.dumps(progress, ensure_ascii=False)
    
    # 更新 RPE 趋势
    if len(progress) >= 2:
        recent = progress[-2:]
        if recent[1]["avg_rpe"] > recent[0]["avg_rpe"] + 0.5:
            ucs.rpe_trend = "rising"
        elif recent[1]["avg_rpe"] < recent[0]["avg_rpe"] - 0.5:
            ucs.rpe_trend = "falling"
        else:
            ucs.rpe_trend = "stable"
    
    # 更新平均完成率（移动平均）
    recent_cr = [p["completion_rate"] for p in progress[-4:]]
    ucs.avg_completion_rate = round(sum(recent_cr) / len(recent_cr), 2)
    
    # 检查是否连续完成
    if week_analysis["completion_rate"] >= 0.7:
        ucs.consecutive_weeks_completed += 1
    else:
        ucs.consecutive_weeks_completed = 0
```

### 6.2 更新黑名单

在 `analyze_week` 中检查每个 slot，标记 RPE≥9 的动作：

```python
def _update_blacklist(prev_days: list, db: Session):
    """更新 exercise_blacklist。"""
    ucs = db.query(UserCurrentState).first()
    if not ucs:
        return
    
    blacklist = json.loads(ucs.exercise_blacklist or "[]")
    high_rpe_exercises = set()
    
    for day in prev_days:
        for slot in day.slots:
            if (getattr(slot, "rpe", 0) or 0) >= 9:
                high_rpe_exercises.add(slot.exercise_name)
    
    # 如果某个动作已在黑名单中但这次 RPE 正常，移出
    # 如果某个动作连续出现，维持
    # 简化：只保留在 high_rpe_exercises 中的
    new_blacklist = [name for name in blacklist if name in high_rpe_exercises]
    for name in high_rpe_exercises:
        if name not in new_blacklist:
            # 首次出现，标记为"观察"而不是立即拉黑
            pass
    
    ucs.exercise_blacklist = json.dumps(new_blacklist, ensure_ascii=False)
```

---

## 7. ProgrammerAgent 扩展

当前 `select_exercises()` 从 wger 返回的候选列表里选。需要新增一个方法：

```python
def select_from_pool(
    self,
    candidates: list,
    user_profile: dict,
    goal: str,
    experience: str,
    location: str,
    user_desc: str,
    exclude_names: list = None,
    user_state: dict = None,
) -> list:
    """从本地缓存池中精选动作。
    
    相比 select_exercises：
    - 数据源是本地缓存池（mesocycle_exercise_pool），不调 wger
    - 传入 exclude_names（上周已选）
    - 传入 user_state（压缩历史），让 LLM 知道用户状态
    """
```

**Prompt 变化：** 在现有 prompt 基础上追加：
```
上周已选动作: [动作A， 动作B， ...]
用户历史: 平均完成率=85%， RPE 趋势=稳定， 连续完成=3周
请选择与上周不同的组合， 保持训练的多样性。
```

---

## 8. 性能优化

### 8.1 消除 N+1

当前：
```python
prev_days = db.query(Day).filter(Day.week_id == current_week.id).all()
for d in prev_days:
    d.slots = db.query(ExerciseSlot).filter(ExerciseSlot.day_id == d.id).all()
```

改为：
```python
prev_days = (
    db.query(Day)
    .filter(Day.week_id == current_week.id)
    .order_by(Day.day_order)
    .outerjoin(ExerciseSlot)
    .options(contains_eager(Day.slots))
    .all()
)
```

### 8.2 LLM 调用优化

| 调用 | 模型 | 预计耗时 |
|------|------|---------|
| ProgrammerAgent.select_from_pool | `get_fast_llm()` | ~3-5s |
| 热身+拉伸生成（同一次调用） | `get_fast_llm()` | ~2-4s |
| CoachAgent 备注 | `get_llm()` | 可异步 |

如果 `days_per_week=3`，每周生成的总 LLM 等待时间：3 × (4s + 3s) ≈ 21s，全部并行 → ~6-7s 实际等待。

---

## 9. 文件变更清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `app/models/orm_models.py` | 修改 | 新增 `MesocycleExercisePool` ORM，扩展 `UserCurrentState` |
| `app/engine/generator.py` | **重写** | 重构 `generate_next_week()` 核心流程 |
| `app/engine/exercise_pool.py` | **新建** | `PoolManager` 缓存池操作 |
| `app/engine/progressive_overload.py` | 微调 | 支持新 slot 设初始重量（参考上周 RPE） |
| `app/engine/exercise_rotation.py` | 微调 | 返回值格式修复，日志补充 |
| `app/engine/adaptive_adjustment.py` | 扩展 | 增加黑名单更新函数 |
| `app/agents/programmer_agent.py` | 扩展 | 新增 `select_from_pool()` 方法 |
| `app/agents/plan_assembler.py` | **重写** | `_select_warmup` → `generate_warmup`，`_select_stretches` → `generate_stretch` |
| `app/agents/analyst_agent.py` | 微调 | 增加 `completion_rate` 等指标的历史分析 |
| `app/services/plan_service.py` | 微调 | 编排逻辑适配新流程 |
| `app/api/routes/fitness.py` | 不变 | 路由层无需改动 |

---

## 10. 实现顺序建议

| 阶段 | 内容 | 估算 |
|------|------|------|
| **阶段 1** | 新增 `MesocycleExercisePool` 表 + ORM、扩展 `UserCurrentState` | 1 次 |
| **阶段 2** | 新建 `exercise_pool.py`（PoolManager）| 1 次 |
| **阶段 3** | 修复轮换 bug + 性能优化（N+1）| 1 次 |
| **阶段 4** | 重写 `plan_assembler.py`（AI 热身+拉伸）| 1-2 次 |
| **阶段 5** | 扩展 `ProgrammerAgent`（select_from_pool）| 1 次 |
| **阶段 6** | 重写 `generator.py` 核心流程 | 2-3 次 |
| **阶段 7** | 用户数据压缩（`_update_user_state`）| 1 次 |
| **阶段 8** | 集成测试 + 修复 | 1 次 |

推荐按阶段顺序实现，每个阶段可独立测试。

---

## 11. 未解决问题 / 待确认

1. **热身+拉伸的 LLM prompt 模板**：需要设计具体的 prompt 格式，确保输出稳定 JSON
2. **缓存池填充时机**：init-plan 完成后自动填充 vs lazy 填充（第一次 generate_next_week 时）
3. **`generate_init_week` 是否也要用 AI 热身拉伸？** 当前 init 已经用硬编码热身了，是否改为一致用 AI？
