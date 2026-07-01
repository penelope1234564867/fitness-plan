# 后端重构实施计划

> **目标：** 从旧 JSON blob 方案改为周期化训练引擎
> **范围：** 只改后端，前端不动
> **设计依据：** `0-docs/fitness-engine-design.md` + `0-docs/10-table.md`
> **验证原则：** 每一步可查库、可 curl、可确认数据一致性

---

## 文件清单

### 新建
| 文件 | 用途 |
|------|------|
| `backend/app/engine/__init__.py` | 引擎包 |
| `backend/app/engine/exercise_cache.py` | wger 懒加载缓存 |
| `backend/app/engine/progressive_overload.py` | 双渐进规则 |
| `backend/app/engine/adaptive_adjustment.py` | RPE 自适应调整 |
| `backend/app/engine/exercise_rotation.py` | 动作轮换 |
| `backend/app/engine/mesocycle_manager.py` | 中周期切换 |
| `backend/app/engine/generator.py` | 周计划生成编排器 |

### 修改
| 文件 | 改动 |
|------|------|
| `backend/app/api/routes/fitness.py` | 删旧接口 + 加新接口 |
| `backend/app/api/routes/record.py` | 整体废弃 |
| `backend/app/api/main.py` | 注册新路由 |
| `backend/app/services/llm_service.py` | 加新 prompt |
| `backend/app/services/plan_service.py` | 标记废弃，保留 SSE 流式逻辑供 generator 复用 |
| `backend/app/database.py` | 清理 init_db |

### 已就绪（不动）
- `backend/app/models/orm_models.py` ✓
- `backend/app/models/schemas.py` ✓

---

## 验证命令速查（全链路一致性检查）

所有任务完成后，用一个 sqlite3 命令就能看清全貌：

```bash
# ===== 库级别：确认所有表存在 =====
sqlite3 backend/fitness.db ".tables"

# ===== 行级别：确认各表数据量 =====
sqlite3 backend/fitness.db "
SELECT 'macrocycle', COUNT(*) FROM macrocycle
UNION ALL SELECT 'mesocycle', COUNT(*) FROM mesocycle
UNION ALL SELECT 'week', COUNT(*) FROM week
UNION ALL SELECT 'day', COUNT(*) FROM day
UNION ALL SELECT 'exercise_slot', COUNT(*) FROM exercise_slot
UNION ALL SELECT 'exercise', COUNT(*) FROM exercise;
"

# ===== 周期一致性检查 =====
# 查每个 macrocycle → mesocycle → week → day → slot 的链条是否完整
sqlite3 backend/fitness.db "
SELECT
  m.id AS macrocycle_id, m.goal,
  ms.id AS mesocycle_id, ms.phase, ms.week_count,
  w.id AS week_id, w.week_number,
  d.id AS day_id, d.day_order, d.day_label,
  es.id AS slot_id, es.phase_type, es.target_sets, es.target_reps
FROM macrocycle m
JOIN mesocycle ms ON ms.macrocycle_id = m.id
JOIN week w ON w.mesocycle_id = ms.id
JOIN day d ON d.week_id = w.id
JOIN exercise_slot es ON es.day_id = d.id
LIMIT 30;
"

# ===== FK 完整性检查：所有 slot 的 exercise_id 指向真实存在动作 =====
sqlite3 backend/fitness.db "
SELECT COUNT(*) AS broken_fks FROM exercise_slot es
LEFT JOIN exercise e ON e.id = es.exercise_id
WHERE e.id IS NULL;
"
```

---

## 各任务详解

---

### Task 1: Engine 基础设施 + wger 缓存

**文件：** 新建 `backend/app/engine/__init__.py`、`backend/app/engine/exercise_cache.py`

**内容：**
- `__init__.py`：空文件，标记为包
- `exercise_cache.py`：提供 `search_and_cache(muscle_group, db) -> List[Exercise]`，搜索 wger 并写入本地 exercise 表

**验证：**

```bash
# 导入测试
cd backend && python -c "from app.engine.exercise_cache import search_and_cache; print('OK')"

# 试搜一个肌肉群，观察 exercise 表被写入
sqlite3 fitness.db "SELECT COUNT(*) FROM exercise;"
```

---

### Task 2: 渐进超负荷引擎

**文件：** 新建 `backend/app/engine/progressive_overload.py`

**核心逻辑：**

```python
def calc_next_week_params(prev_slot, phase: str) -> dict:
    reached_max = prev_slot.actual_reps >= prev_slot.target_reps_max
    if reached_max:
        new_weight = prev_slot.weight_kg + _weight_increment(phase)
        new_reps = _rep_lower_bound(phase)
    else:
        new_weight = prev_slot.weight_kg
        new_reps = min(prev_slot.target_reps + 1, prev_slot.target_reps_max)
    return {"target_sets": ..., "target_reps": new_reps, "target_reps_max": ..., "weight_kg": new_weight}
```

**验证（无数据库，纯函数测试）：**

```bash
cd backend && python -c "
from app.engine.progressive_overload import calc_next_week_params

# 模拟一个达到次数上限的 slot
class FakeSlot:
    actual_reps = 12
    target_reps_max = 12
    weight_kg = 10.0
    target_sets = 3

result = calc_next_week_params(FakeSlot(), 'hypertrophy')
print(result)
# 预期：weight_kg=11.25, target_reps=8（加重量回到下限）
assert result['weight_kg'] == 11.25, f'weight fail: {result}'
assert result['target_reps'] == 8, f'reps fail: {result}'
print('渐进超负荷测试通过')
"
```

---

### Task 3: 自适应调整引擎

**文件：** 新建 `backend/app/engine/adaptive_adjustment.py`

**核心逻辑：**

```python
def analyze_slot(slot) -> dict:
    # RPE ≤ 5 且全部完成 → increase_weight
    # RPE ≤ 7 且达到次数上限 → increase_reps
    # RPE ≥ 9 → reduce_intensity
    # RPE 10 或备注含"疼" → swap_exercise
    # 默认 → keep

def analyze_week(days: list) -> dict:
    # 统计 high_rpe_ratio / no_checkin_ratio / needs_deload
```

**验证：**

```bash
cd backend && python -c "
from app.engine.adaptive_adjustment import analyze_slot, analyze_week

class FakeSlot:
    def __init__(self, rpe, actual_sets, target_sets, actual_reps, target_reps_max, notes=''):
        self.rpe = rpe
        self.actual_sets = actual_sets
        self.target_sets = target_sets
        self.actual_reps = actual_reps
        self.target_reps_max = target_reps_max
        self.notes = notes

# RPE=5 且全部完成 → 应建议加重量
r = analyze_slot(FakeSlot(5, 3, 3, 12, 12))
assert r['action'] == 'increase_weight', f'预期加重量，实际{r}'

# RPE=9 → 应建议降强度
r = analyze_slot(FakeSlot(9, 3, 3, 12, 12))
assert r['action'] == 'reduce_intensity', f'预期降强度，实际{r}'

# 备注含"疼" → 替换动作
r = analyze_slot(FakeSlot(7, 3, 3, 12, 12, notes='膝盖有点疼'))
assert r['action'] == 'swap_exercise', f'预期替换，实际{r}'

print('自适应调整引擎测试通过')
"
```

---

### Task 4: 动作轮换引擎

**文件：** 新建 `backend/app/engine/exercise_rotation.py`

**核心逻辑：** 给定一批 exercise_slot，沿变式链移动到下一个难度级别。

**验证：**

```bash
cd backend && python -c "
# 先往 exercise 和 exercise_variation 表写测试数据
sqlite3 fitness.db \"
INSERT OR IGNORE INTO exercise (id, wger_id, name, muscle_group) VALUES
(1, 101, '跪姿俯卧撑', 'chest'),
(2, 102, '标准俯卧撑', 'chest'),
(3, 103, '宽距俯卧撑', 'chest');
INSERT OR IGNORE INTO exercise_variation (series_name, exercise_id, sort_order) VALUES
('俯卧撑系列', 1, 1),
('俯卧撑系列', 2, 2),
('俯卧撑系列', 3, 3);
\"
# 测试轮换
python -c \"
from app.database import SessionLocal
from app.engine.exercise_rotation import rotate_for_new_mesocycle

db = SessionLocal()
result = rotate_for_new_mesocycle([type('FS',(),{'exercise_id':1,'exercise':type('E',(),{'id':1})})()], db)
print(f'轮换结果: {result}')
# 预期：exercise_id=2（从跪姿轮到标准）
assert result[0]['exercise_id'] == 2
db.close()
print('动作轮换测试通过')
\"
"
```

---

### Task 5: 中周期管理器

**文件：** 新建 `backend/app/engine/mesocycle_manager.py`

**核心逻辑：**

```python
PHASE_ORDER = ["foundational", "hypertrophy", "strength"]

def decide_next_phase(current_phase, completion_rate) -> str:
    # <60% → 重复
    # deload → hypertrophy（下一轮）
    # foundational → hypertrophy → strength → deload

def needs_deload_this_week(week_data) -> bool:
    # RPE≥9 的比例 >50% 时提前减载
```

**验证：**

```bash
cd backend && python -c "
from app.engine.mesocycle_manager import decide_next_phase, needs_deload_this_week

# foundational完成后→hypertrophy
assert decide_next_phase('foundational', 0.8) == 'hypertrophy'
# 完成率不够→重复
assert decide_next_phase('foundational', 0.5) == 'foundational'
# strength完成后→deload
assert decide_next_phase('strength', 0.8) == 'deload'
# deload完成后→开始下一轮
assert decide_next_phase('deload', 1.0) == 'hypertrophy'
# RPE偏高→需要减载
assert needs_deload_this_week({'needs_deload': True}) == True

print('中周期管理器测试通过')
"
```

---

### Task 6: 周计划生成编排器

**文件：** 新建 `backend/app/engine/generator.py`

**包含两个接口：**
- `generate_init_week(macrocycle, mesocycle, user_state, db, emit)` → 首次生成第 1 周
- `generate_next_week(current_week, db, emit)` → 基于上周打卡生成下一周

内部调 Task 1-5 的模块 + 旧的 `exercise_agent` 和 `plan_agent` 完成动作搜索和筛选。

**验证（全链路数据一致性检查）：**

```bash
# 启动服务器
cd backend && python run.py &
sleep 3

# 1. 初始化大周期 + 第 1 周
curl -s -X POST http://localhost:8000/api/fitness/init-plan \
  -H "Content-Type: application/json" \
  -d '{"goal":"增肌","experience_level":"新手","workout_location":"居家","days_per_week":3}'

# 2. 查库验证周期链条
sqlite3 fitness.db "
SELECT 'macrocycle', id, goal, status FROM macrocycle
UNION ALL
SELECT 'mesocycle', id, phase, status FROM mesocycle
UNION ALL
SELECT 'week', id, week_number, status FROM week;
"

# 检查要点：
#   - macrocycle 有 1 条，goal="增肌"，status="active"
#   - mesocycle 有 1 条，phase="foundational"
#   - week 有 1 条，week_number=1

# 3. 查 daily 完整性
sqlite3 fitness.db "
SELECT d.day_order, d.day_label, d.focus, COUNT(es.id) AS slot_count
FROM day d
LEFT JOIN exercise_slot es ON es.day_id = d.id
WHERE d.week_id = (SELECT id FROM week ORDER BY id DESC LIMIT 1)
GROUP BY d.id
ORDER BY d.day_order;
"

# 检查要点：
#   - 3 天，day_order=1,2,3
#   - 每天都有 slot_count > 0
#   - day_label 为推/拉/腿

# 4. 查每个 slot 的 exercise 引用
sqlite3 fitness.db "
SELECT es.id, es.phase_type, es.target_sets, es.target_reps, e.name AS exercise_name
FROM exercise_slot es
JOIN exercise e ON e.id = es.exercise_id
WHERE es.day_id IN (SELECT id FROM day WHERE week_id = (SELECT id FROM week ORDER BY id DESC LIMIT 1))
ORDER BY es.day_id, es.sort_order;
"
# 检查要点：
#   - 每个 phase_type 合理（warmup/main/cooldown）
#   - exercise_name 不为空（FK 正确）
```

---

### Task 7: 更新 LLM Service

**文件：** 修改 `backend/app/services/llm_service.py`

新增两个 prompt 常量：`INIT_PHASE_PROMPT` 和 `INIT_WORKOUT_SPLIT_PROMPT`。

**验证：**

```bash
cd backend && python -c "
from app.services.llm_service import get_fast_llm
from app.services.llm_service import INIT_PHASE_PROMPT  # 确认可导入

prompt = INIT_PHASE_PROMPT.format(goal='增肌', experience='新手', days_per_week=3)
print(f'Prompt 模板:\n{prompt}')
# 不实际调 LLM，只确认模板格式正确
"
```

---

### Task 8: 重写健身路由

**文件：** 修改 `backend/app/api/routes/fitness.py`

**删除的旧接口：**
- `POST /generate` → 被 `init-plan` 替代
- `POST /record` → 表已删
- `GET /records` → 表已删
- `GET /stats` → 表已删

**保留的旧接口：**
- `GET /plans` → 看旧数据
- `GET /plan/{plan_id}` → 看旧数据

**新增的新接口：**

| 接口 | 用途 | 关键字段 |
|------|------|---------|
| `POST /init-plan` | 初始化 + 第 1 周 | SSE 流 |
| `POST /generate-next` | 生成本周 | SSE 流 |
| `GET /current-week` | 当前周详情 | Week + Days + Slots + Exercise |
| `GET /macrocycles` | 大周期列表 | id, goal, status |
| `GET /macrocycle/{id}` | 大周期详情（嵌套所有子数据） | |
| `POST /checkin` | 打卡 | DayCheckin |
| `GET /current-state` | 当前状态 | |
| `PUT /current-state` | 改当前状态 | experience/location/days |

**验证——每个接口独立验证：**

```bash
# ===== init-plan（见 Task 6）=====
# 同 Task 6 验证

# ===== current-week =====
curl -s http://localhost:8000/api/fitness/current-week | python -m json.tool
# 检查返回结构：id, week_number, days[].slots[].exercise

# ===== macrocycles =====
curl -s http://localhost:8000/api/fitness/macrocycles | python -m json.tool
# 预期：[{"id":1, "goal":"增肌", "status":"active", ...}]

# ===== macrocycle/{id} =====
curl -s http://localhost:8000/api/fitness/macrocycle/1 | python -m json.tool
# 预期：嵌套 mesocycles → weeks → days → slots → exercise

# ===== checkin =====
# 先查到当前周的 day_id 和 slot_id
DAY_ID=$(sqlite3 fitness.db "SELECT id FROM day WHERE week_id=(SELECT id FROM week ORDER BY id DESC LIMIT 1) LIMIT 1;")
SLOT_ID=$(sqlite3 fitness.db "SELECT id FROM exercise_slot WHERE day_id=$DAY_ID AND phase_type='main' LIMIT 1;")
curl -s -X POST http://localhost:8000/api/fitness/checkin \
  -H "Content-Type: application/json" \
  -d "{\"day_id\":$DAY_ID,\"is_completed\":true,\"rpe_score\":7,\"exercises\":[{\"slot_id\":$SLOT_ID,\"actual_sets\":3,\"actual_reps\":10,\"rpe\":7}]}"
echo ""
# 查库验证 actual_* 字段已填入
sqlite3 fitness.db "SELECT id, actual_sets, actual_reps, rpe FROM exercise_slot WHERE id=$SLOT_ID;"
# 预期：actual_sets=3, actual_reps=10, rpe=7

# ===== current-state =====
curl -s http://localhost:8000/api/fitness/current-state
# 预期：当前动态配置

# ===== update current-state =====
curl -s -X PUT http://localhost:8000/api/fitness/current-state \
  -H "Content-Type: application/json" \
  -d '{"experience_level":"中级","days_per_week":4}'
# 查库验证
sqlite3 fitness.db "SELECT experience_level, days_per_week FROM user_current_state;"

# ===== generate-next =====
# 先打卡标记上周完成
curl -s -X POST http://localhost:8000/api/fitness/generate-next

# 查库验证生成了新的一周
sqlite3 fitness.db "
SELECT w.id, w.week_number, w.status, COUNT(d.id) AS day_count
FROM week w
LEFT JOIN day d ON d.week_id = w.id
GROUP BY w.id
ORDER BY w.id;
"
# 预期：应该有 2 行（第 1 周 + 第 2 周）
# week_number 从 1 变为 2
```

---

### Task 9: 更新数据库初始化

**文件：** 修改 `backend/app/database.py`

去掉 `_add_column` 兼容代码，精简 `init_db()`。

**验证：**

```bash
cd backend && python -c "
from app.database import engine, Base
from app.models import orm_models
Base.metadata.create_all(bind=engine)
print('表创建/验证成功')
from sqlalchemy import inspect
tables = inspect(engine).get_table_names()
print(f'共 {len(tables)} 张表: {tables}')
# 预期：macrocycle, mesocycle, week, day, exercise_slot, exercise, exercise_variation, user_current_state, user, fitness_plan
"
```

---

### Task 10: 清理 main.py + record.py

**文件：**
- 删除 `backend/app/api/routes/record.py`
- 修改 `backend/app/api/main.py`：去掉 `record.router` 注册

**验证：**

```bash
# 旧的记录接口应返回 404
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/fitness/record
# 预期：404

curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/fitness/records
# 预期：404
```

---

## 全链路验收测试

以上所有任务完成后，执行一次完整验收：

```bash
cd backend && python run.py &
sleep 3

echo "=== 1. 初始化 ==="
curl -s -X POST http://localhost:8000/api/fitness/init-plan \
  -H "Content-Type: application/json" \
  -d '{"goal":"增肌","experience_level":"新手","workout_location":"居家","days_per_week":3}'
echo ""

echo "=== 2. 查当前周 ==="
curl -s http://localhost:8000/api/fitness/current-week | python -c "import sys,json; d=json.load(sys.stdin); print(f'第{d[\"week_number\"]}周, {len(d[\"days\"])}天')"

echo "=== 3. 查库 ==="
sqlite3 fitness.db "
SELECT m.id, m.goal, ms.phase, w.week_number, COUNT(d.id) AS days, COUNT(es.id) AS slots
FROM macrocycle m
JOIN mesocycle ms ON ms.macrocycle_id=m.id
JOIN week w ON w.mesocycle_id=ms.id
JOIN day d ON d.week_id=w.id
JOIN exercise_slot es ON es.day_id=d.id
GROUP BY m.id, ms.id, w.id;
"
echo ""

echo "=== 4. 打卡 ==="
DAY_ID=$(sqlite3 fitness.db "SELECT id FROM day LIMIT 1;")
SLOT_ID=$(sqlite3 fitness.db "SELECT id FROM exercise_slot WHERE phase_type='main' LIMIT 1;")
curl -s -X POST http://localhost:8000/api/fitness/checkin \
  -H "Content-Type: application/json" \
  -d "{\"day_id\":$DAY_ID,\"is_completed\":true,\"rpe_score\":7,\"exercises\":[{\"slot_id\":$SLOT_ID,\"actual_sets\":3,\"actual_reps\":10,\"rpe\":7}]}"

echo "=== 5. 生成下周 ==="
curl -s -X POST http://localhost:8000/api/fitness/generate-next

echo "=== 6. 确认周期一致性 ==="
sqlite3 fitness.db "
SELECT m.id, m.goal, ms.id, ms.phase, w.id, w.week_number
FROM macrocycle m
JOIN mesocycle ms ON ms.macrocycle_id=m.id
JOIN week w ON w.mesocycle_id=ms.id
ORDER BY m.id, ms.id, w.id;
"
echo ""
echo "=== 完成 ==="
```

---

## 执行顺序

```
Task 1  ──→ Task 2 ──→ Task 3 ──→ Task 4 ──→ Task 5
                                    │
          Task 6 (依赖 1-5) ◄────────┘
                                    │
          Task 7 (独立) ─────────────┤
                                    │
          Task 8 (依赖 6, 7) ◄──────┘
            │
          Task 9 (独立)
            │
          Task 10 (依赖 8, 9)
```
