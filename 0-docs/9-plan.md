# 9. 将测试架构整合进主项目

## 一、当前架构 vs 目标架构

### 当前（plan_service.py）

```
ExerciseAgent (ReAct + MCP wger)
ScheduleAgent (ReAct + 天气)       ← 并行
        ↓
PlanAgent (Simple, 整合)
        ↓
存库 + SSE 推送进度
```

问题：
- ExerciseAgent 用 ReAct（LLM 自己决定调什么工具），慢且不可控
- ScheduleAgent 查询天气 → 但 PPL 分化是硬编码的，天气对室内训练意义不大
- PlanAgent 作为第三阶段，LLM 可能丢字段 → 需要 `_inject_exercise_fields` 补救
- 没有流式输出 LLM 内容，前端只能看到 "进度消息" 看不到实际生成过程

### 目标（Pipeline + Map-Reduce）

```
用户输入 (goal, experience, location, days_per_week)
          │
          ▼
   ┌──────────────────┐
   │  Coordinator     │   ← 纯代码
   │  天数 → PPL 排期  │
   └──────┬───────────┘
          │ schedule [{day, focus, muscles}, ...]
          │
     ┌────┼────┐ 并行 (Map)
     ▼    ▼    ▼
   Day1  Day2  Day3
   │      │      │
   ├── exercise_agent  ── 搜索 → 过滤 → LLM精选  (test/05)
   ├── plan_agent      ── LLM组装 warmup/main/cooldown  (test/06)
   │
          │
          ▼
   ┌──────────────────┐
   │  Reduce          │   ← 校验 + 归并 + 补充 warmup/cooldown 模板
   └──────┬───────────┘
          │ final_plan
          ▼
      存库 + SSE 推送进度 + 流式 exercise_done 逐个动作推送
```

优势：
- 无 Agent 调度开销，直接函数调用
- 三天独立互不影响，天然并行
- LLM 输出逐字流式推送前端
- 不需要 `_inject_exercise_fields`（组装阶段直接保留 wger_id）

---

## 二、核心决策

### 决策 1：ScheduleAgent 是否需要保留？

**结论：去掉 ScheduleAgent。**

原因：
- PPL 分化和周几无关，硬编码即可
- 天气查询对"室内/户外"选择有意义，但当前项目主力训练在健身房，天气不重要
- 减少一次 LLM 调用，省 ~15s

后续如果需要天气功能，可以在前端加一个天气 widget，独立于计划生成流程。

### 决策 2：ExerciseAgent (ReAct) 是否保留？

**结论：两个 agent 都重写，分工明确：**

**核心原则：选动作 ≠ 排计划，所以两个 agent 都要保留。**

| | `exercise_agent.py` | `plan_agent.py` |
|---|---|---|
| **来源** | test/05_exercise_agent_precise.py | test/06_plan_agent_assembly.py |
| **职责** | **选什么动作** | **怎么排计划** |
| 输入 | 肌群 ID 列表 | 精选出的动作列表 |
| 做的事 | 搜索 wger → 按器材过滤 → LLM 选最优 | LLM 编排 warmup/main/cooldown 顺序 |
| 输出 | `[{name, wger_id, target_muscle}, ...]` | `{warmup:[], main:[], cooldown:[]}` |
| 有无 ReAct | ❌ 删除 | ❌ 没有（一直是直接函数） |
| 单天调用顺序 | ⏩ 第一步跑 | ⏩ 第二步跑（接 exercise_agent 的结果） |

```
# 单天数据流：
exercise_agent.search_all_muscles(muscle_ids)
    → 扁平动作列表
exercise_agent.filter_by_equipment(list, experience)
    → 过滤后列表
exercise_agent.llm_select(filtered, goal, exp, loc)
    → [{name:"卧推", wger_id:123, ...}, {name:"飞鸟", ...}, ...]
        ↓ 传给
plan_agent.assemble_one_day(day_spec, selected, goal, exp, loc)
    → {warmup:[...], main:[...], cooldown:[...]}  ← 当天完整计划
```

### 决策 3：前端生成体验 — 专用"直播间"界面

**结论：新增独立生成页面 `GeneratingPlan.vue`，三天并行实时流式展示，让用户看着计划"长出来"。**

**核心思路**：生成计划是在线最耗时的操作（~30-60s），必须给用户提供"有内容可看"的等待体验，而非进度条干等。

#### 3.1 新增 SSE event 类型

后端 SSE 协议扩展（不破坏现有 event）：

| Event | 说明 | 数据格式 |
|-------|------|---------|
| `progress` | 进度/搜索阶段消息 | `{"day":0, "phase":"search", "text":"正在查询股四头肌(2/4)..."}` |
| `llm_stream` | LLM 流式输出片段 | `{"day":1, "phase":"select", "chunk":"{\\"selected\\":"}` |
| `exercise_done` | 单个动作生成完毕 | `{"day":0, "exercise":{"name":"卧推","sets":4,"reps":8,"wger_id":123}}` |
| `day_done` | 某天计划生成完成 | `{"day":0, "focus":"胸部+肩部+三头", "main_count":5}` |
| `done` | 全部完成（已有） | `{"id": 123, "weekly_plans": [...]}` |

**为什么加 `exercise_done`**：`llm_stream` 发的是原始 JSON 片段，前端拼接后可能会在 chunk 边界断开导致 `JSON.parse` 失败。`exercise_done` 在 LLM 返回完整 JSON 后解析好再逐条推，前端直接 push 到列表，完全不用碰 JSON 解析。

#### 3.2 前端新页面：GeneratingPlan.vue

新建 `frontend/src/views/GeneratingPlan.vue`，取代原有的 GeneratingProgress 弹窗/进度条逻辑。

**页面布局（三天横向一排）**：

```
┌─────────────────────────────────────────────────────────────────────┐
│  📅 正在生成你的 PPL 训练计划                                       │
│  ⏱ 已用时 18s  |  已完成 1/3 天                                   │
│                                                                     │
│  ┌─ Day 1 · 推 ──────────┐  ┌─ Day 2 · 拉 ──────────┐  ┌─ Day 3 · 腿 ──────────┐
│  │ 🟢 搜索    ✅ 15个    │  │ 🟢 搜索    ✅ 12个    │  │ 🔵 搜索中...          │
│  │ 🟢 精选    ✅ 最优6   │  │ 🟡 精选中...  ⏳      │  │                        │
│  │ 🔄 组装中...  3/10   │  │                        │  │                        │
│  │ ──────────────────── │  │ ──────────────────── │  │ ──────────────────── │
│  │ ☐ 卧推 4×8          │  │ ☐ 等待中...          │  │ ☐ 等待中...          │
│  │ ☐ 哑铃飞鸟 3×12     │  │ ☐ 等待中...          │  │ ☐ 等待中...          │
│  │ ☐ 等待中...          │  │ ☐ 等待中...          │  │ ☐ 等待中...          │
│  │ ☐ 等待中...          │  │ ☐ 等待中...          │  │ ☐ 等待中...          │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
└─────────────────────────────────────────────────────────────────────┘
```

**交互说明**：
- 三天卡片 **横向一排**（flex row），等宽三列
- 每张卡片内部纵向：阶段状态行 → 分割线 → 动作列表
- 动作列表逐条流式插入，带淡入动画
- 当天生成完后卡片边框变绿，显示 ✅

**状态 & 阶段图标**：
```
🔵 等待中 → 🟡 进行中 → 🟢 已完成

每天内部小阶段：
  🔵 搜索中     → 🟢 搜索完成 ✅
  🟡 精选中     → 🟢 精选完成 ✅
  🟡 组装中     → 🟢 组装完成 ✅
```

#### 3.3 路由与跳转逻辑

```
OnboardingGuide.vue Step 3 提交
       ↓
router.push('/generating')    ← 新的生成页面
       ↓
GeneratingPlan.vue 打开 SSE 连接
       ↓ (生成完成)
router.push('/home')
```

**路由注册**：`/generating` → `GeneratingPlan.vue`

#### 3.4 状态管理

在 `workout.ts` store 中新增生成相关状态：

```typescript
// workout.ts store 新增
const generatingState = reactive({
  status: 'idle' as 'idle' | 'connecting' | 'generating' | 'done' | 'error',
  elapsed: 0,
  days: [
    { day: '推', focus: '胸+肩+三头', status: 'waiting', phase: '',
      exercises: [{ name: '', sets: 0, reps: 0, completed: false }] },
    { day: '拉', focus: '背+二头', status: 'waiting', phase: '',
      exercises: [] },
    { day: '腿', focus: '腿+臀+腹', status: 'waiting', phase: '',
      exercises: [] },
  ],
})
```

---

## 三、架构范式

### 3.1 Pipeline 架构

将整个生成流程定义为 **严格分阶段的数据流管道**，每个阶段有明确的输入/输出类型，阶段之间通过数据转换连接，不共享状态。

```
输入: (goal, experience, location, days_per_week)
  │
  ├─ Stage 1 ─ Coordinator ──────────────────────────  纯函数
  │  输入: days_per_week
  │  输出: schedule[{day, focus, muscles, desc}, ...]
  │  规则: 硬编码 PPL 分化表查找，无 LLM
  │
  ├─ Stage 2 ─ Fan-Out (Pipeline per Day) ───────────  可并行
  │  输入: schedule[]
  │  ┌─ 2a. Search  ─── wger API 搜索肌群 → 扁平动作列表
  │  ├─ 2b. Filter  ─── 按器材/经验过滤
  │  ├─ 2c. Select  ─── LLM 精选最优动作 (JSON)
  │  └─ 2d. Assemble ── LLM 组装当天训练 (JSON)
  │  输出: per_day_plan[]
  │
  ├─ Stage 3 ─ Fan-In (Reduce) ─────────────────────  串行
  │  输入: per_day_plan[]
  │  步骤: validate → merge → build_weekly_structure
  │  输出: final_plan (含 weekly_plans)
  │
  └─ Stage 4 ─ Persist ─────────────────────────────  串行
     输入: final_plan
     步骤: save to db → SSE done
     输出: plan_id
```

**Pipeline 规则**：
- **数据单向流动**：前一阶段的输出是后一阶段的输入，没有反向依赖
- **阶段内原子化**：每个阶段要么全部成功，要么可重试（LLM 阶段有重试逻辑）
- **阶段间解耦**：修改某个阶段的实现（如 Search 换成缓存查询）不影响其他阶段
- **可观测性**：每个阶段的起止都通过 SSE 通知前端，便于调试

### 3.2 Map-Reduce 范式

三天并行生成的本质是 Map-Reduce：

```
┌─────────────────────────────────────────────────────────────────┐
│  MAP (三天独立并行)                                               │
│                                                                 │
│  Day1(推)                                                       │
│    ├── exercise_agent: search → filter → llm_select  (test/05) │
│    └── plan_agent:     assemble_one_day               (test/06) │  🡐  asyncio.gather
│  Day2(拉) ── exercise_agent → plan_agent                        │     return_exceptions=True
│  Day3(腿) ── exercise_agent → plan_agent                        │
│                                                                 │
└──────────────────────────┬──────────────────────────────────────┘
                           ↓ per_day_plan[]
┌──────────────────────────┴──────────────────────────────────────┐
│  REDUCE (汇总归并)                                                │
│                                                                 │
│  validate: 过滤失败的天（Exception），有效天数 > 0 才继续           │
│  merge:    {weekly_plans: [{week: 1, days: [...]}]}             │
│  enrich:   补充 warmup/cooldown 模板                             │
│  output:   完整计划 → Save                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Map 阶段**（三天并行）：
```python
# map: 每个 day 独立跑完整 Pipeline
tasks = [run_one_day(day, i) for i, day in enumerate(schedule)]
per_day_plans = await asyncio.gather(*tasks)  # 三天同时进行
```

**Reduce 阶段**（汇总）：
```python
# reduce: 收集 → 校验 → 归并 → 输出
def reduce_to_weekly_plan(per_day_plans: list, schedule: list) -> dict:
    # 1. Validate — 每空检查
    for i, plan in enumerate(per_day_plans):
        assert len(plan["main"]) > 0, f"Day{i} 无主要动作"
    
    # 2. Merge — 组装成周结构
    days = []
    for i, plan in enumerate(per_day_plans):
        days.append({
            "day": schedule[i]["day"],
            "focus": schedule[i]["focus"],
            **plan  # warmup, main, cooldown
        })
    
    # 3. Output
    return {
        "weekly_plans": [{
            "week": 1,
            "days": days
        }]
    }
```

**为何 Map-Reduce 适合此处**：
| 特性 | 在本项目中的体现 |
|------|----------------|
| 数据分片 | 三天天然是互不依赖的数据分片 |
| 无副作用 | 每个 day 的生成不依赖其他 day 的结果 |
| 可线性扩展 | 3 天 → 增加到 6 天只需加分片，无需改流程 |
| 容错隔离 | 某天 LLM 调用失败，不影响其他天的结果 |
| Shuffle 阶段 | 不需要——days 天然是独立 Key |
| Combine | 不需要——每个 day 内部已经组装完成 |

**错误处理策略**：
- **Map 错误**（某天失败）→ 重试该天最多 2 次，仍失败则跳过（返回 partial 计划）
- **Reduce 错误**（汇总失败）→ 整个计划失败，前端显示错误
- **LLM 超时**（Select/Assemble 阶段）→ 退回到 Backup prompt（不依赖 LLM，用规则模板填充）

### 3.3 范式在代码中的体现

`plan_service.py` 中编排两个 agent 完成 Pipeline + Map-Reduce：

```python
# plan_service.py — generate_plan_stream()

from agents import exercise_agent, plan_agent

# ── Stage 1: Coordinator ──────────────────────────  纯函数
schedule = get_ppl_schedule(days_per_week)
on_llm_chunk(0, "coordinator", "")

# ── Stage 2: Map (三天并行) ──────────────────────  可并行
async def run_one_day(day_spec, day_index):
    """单天 Pipeline: exercise_agent → plan_agent"""
    # exercise_agent: 搜索 → 过滤 → 精选
    grouped = await asyncio.to_thread(
        exercise_agent.search_all_muscles, day_spec["muscles"])
    filtered = exercise_agent.filter_by_equipment(grouped, experience)
    selected = exercise_agent.llm_select(filtered, goal, experience, location)

    # plan_agent: 组装当天
    day_plan = plan_agent.assemble_one_day(
        day_spec, selected, goal, experience, location)
    return day_plan

tasks = [run_one_day(day, i) for i, day in enumerate(schedule)]
# return_exceptions=True 确保某天失败不取消其他天
per_day_plans = await asyncio.gather(*tasks, return_exceptions=True)

# ── Stage 3: Reduce ──────────────────────────────  串行
# 过滤掉失败的天，保留成功的天
valid_plans = [p for p in per_day_plans if not isinstance(p, Exception)]
final_plan = reduce_to_weekly_plan(valid_plans, schedule)

# ── Stage 4: Persist ─────────────────────────────
save_plan(final_plan)
```

---

## 四、改动清单

### 后端改动（5 个文件）

| # | 文件 | 改动 |
|---|------|------|
| 1 | **重写** `backend/app/agents/exercise_agent.py` | 从 test/05 搬搜索/过滤/精选逻辑代替旧 ReAct：`MUSCLES`, `search_all_muscles`, `filter_by_equipment`, `llm_select`, `_invoke_json_llm`；删除所有 ReAct 代码 |
| 2 | **重写** `backend/app/agents/plan_agent.py` | 从 test/06 搬单天组装逻辑：组装 prompt, `assemble_one_day()`；删除旧整合逻辑 |
| 3 | **修改** `backend/app/services/plan_service.py` | 重写 `generate_plan_stream()`：去掉 ScheduleAgent，编排 exercise_agent + plan_agent 三天并行；增加 `llm_stream` 和 `day_done` SSE 事件 |
| 4 | **修改** `backend/app/services/llm_service.py` | 无需大改，`get_fast_llm()` 已就绪 |
| 5 | **删除** `backend/app/agents/schedule_agent.py` | 不再需要 |

### 前端改动（4 个文件）

| # | 文件 | 改动 |
|---|------|------|
| 1 | **新增** `frontend/src/views/GeneratingPlan.vue` | 专用生成页面：三天横向卡片 + SSE 流式展示 |
| 2 | **修改** `frontend/src/router/index.ts` | 注册 `/generating` 路由 |
| 3 | **修改** `frontend/src/views/OnboardingGuide.vue` | Step 3 提交后改为 `router.push('/generating')`，不再直接开 SSE |
| 4 | **删除** `frontend/src/components/GeneratingProgress.vue` | 被 GeneratingPlan.vue 取代 |

---

## 五、后端详细设计

### 职责速查（防混淆）

| 文件 | 做的事 | 不做的事 |
|------|--------|---------|
| `exercise_agent.py` | 搜动作、过滤、**选**最优 | 不编排顺序、不生成 warmup/cooldown |
| `plan_agent.py` | 接收精选结果、**排**成完整一天 | 不搜索、不选动作 |
| `plan_service.py` | 编排 3 天并行、调上面两个、SSE 推送 | 没有业务逻辑，只做编排 |

```
单天调用链：exercise_agent (搜索→过滤→精选) → plan_agent (组装) → 返回当天计划
```

### 5.1 exercise_agent.py（重写）

```
backend/app/agents/exercise_agent.py
```
职责：搜索肌群 → 过滤 → LLM 精选最优动作

**删除**：所有 ReAct 相关代码（`tools` dict, `_parse_exercise_args`, `run` loop, `react_prompt` 等）

**新增**：以下内容从 **test/05** 搬运：

```python
"""Exercise 精选器 — 搜索 + 过滤 + LLM 选择最优动作"""

# 1. 常量
MUSCLES = {...}             # 肌群 ID 映射（从 test/05 搬）
EQUIPMENT_FILTER = {...}    # 经验→器材过滤（从 test/05 搬）
EXPERIENCE_GUIDE = {...}    # LLM 选动作指引
SELECT_PROMPT = "..."       # 精选 prompt（已压缩版）

# 2. 工具函数（从 test/05 搬运）
search_all_muscles(muscle_ids)       # 对各肌群搜索，合并去重
filter_by_equipment(grouped, exp)    # 按经验过滤器材
_invoke_json_llm(llm, prompt)        # 调用 LLM 返回 JSON

# 3. 精选函数
llm_select(grouped, goal, exp, loc)  # LLM 精选最优动作
```

注意：这里**不包含**组装逻辑（`assemble_one_day`, `DAY_ASSEMBLY_PROMPT`），组装由 `plan_agent.py` 负责。

### 5.2 plan_agent.py（重写）

```
backend/app/agents/plan_agent.py
```
职责：接收 exercise_agent 精选出的动作 → LLM 组装成当天完整计划（warmup/main/cooldown）

**删除**：旧整合逻辑（字段修复、跨天合并等）

**新增**：以下内容从 **test/06** 搬运：

```python
"""Plan 组装器 — 将精选动作编排成当天完整训练"""

# 1. 组装 prompt（从 test/06 搬）
ASSEMBLY_PROMPT = """你是一个专业健身教练。用以下动作组装当天的训练计划。
...
格式见 test/06_plan_agent_assembly.py"""

# 2. 核心函数
def assemble_one_day(day_spec, selected_exercises, goal, experience, location) -> dict:
    """接收精选动作列表，LLM 编排成 {warmup, main, cooldown}"""
    ...
```

### 5.3 plan_service.py — 重写 generate_plan_stream()

```
当前：38 行准备 → 并行 Agent → PlanAgent → 存库
改为：硬编码排期 → 三天并行（搜索→精选→组装，带流式）→ 汇总 → 存库
```

新的 SSE 序列：

```
event: progress
data: {"day":0, "phase":"search", "text":"开始生成 PPL 周计划..."}

event: progress
data: {"day":0, "phase":"search", "text":"正在搜索胸部动作(1/3)..."}
event: progress
data: {"day":0, "phase":"search", "text":"正在搜索肩部动作(2/3)..."}
event: progress
data: {"day":0, "phase":"search", "text":"正在搜索三头动作(3/3)..."}
event: progress
data: {"day":0, "phase":"search", "text":"搜索到 15 个动作"}
event: llm_stream
data: {"day":0, "phase":"select", "text":"{\"selected\": [...]"}
event: llm_stream
data: {"day":0, "phase":"assemble", "text":"{\\"warmup\\":[...]"}
event: exercise_done
data: {"day":0, "exercise":{"name":"卧推","sets":4,"reps":8,"wger_id":123}}
event: exercise_done
data: {"day":0, "exercise":{"name":"哑铃飞鸟","sets":3,"reps":12,"wger_id":456}}
event: exercise_done
data: {"day":0, "exercise":{"name":"臂屈伸","sets":3,"reps":12,"wger_id":789}}
event: day_done
data: {"day":0, "focus":"胸部+肩部+三头", "main_count":5}

event: progress
data: {"day":1, "phase":"search", "text":"正在搜索背部动作..."}
event: llm_stream
data: {"day":1, "phase":"select", ...}
event: exercise_done
data: {"day":1, "exercise":{"name":"引体向上","sets":4,"reps":8, ...}}
event: day_done
data: {"day":1, ...}

event: progress
data: {"day":2, ...}
event: exercise_done
data: {"day":2, ...}
event: day_done
data: {"day":2, ...}

event: progress
data: {"text":"💾 保存计划中..."}
event: done
data: {"id": 123, "weekly_plans": [...]}
```

### 5.4 数据库结构

**无需改动。** `FitnessPlan.plan_content` 已经是 JSON 字段，新架构的输出格式与原来兼容：

```json
{
  "weekly_plans": [{
    "week": 1,
    "days": [
      {"day": "第1天", "focus": "胸部+肩部+三头", "warmup": [...], "main": [...], "cooldown": [...]},
      {"day": "第2天", "focus": "背部+二头", ...},
      {"day": "第3天", "focus": "腿部+臀部+腹部", ...}
    ]
  }]
}
```

---

## 六、前端详细设计

### 6.1 GeneratingPlan.vue — 核心逻辑

SSE 连接 + 三天卡片状态管理都在此页面内，OnboardingGuide.vue 只负责跳转。

```typescript
// GeneratingPlan.vue — SSE 事件处理
const days = reactive([
  { label: '推', focus: '胸部+肩部+三头', status: 'waiting', phase: '', exercises: [] as Exercise[] },
  { label: '拉', focus: '背部+二头',       status: 'waiting', phase: '', exercises: [] },
  { label: '腿', focus: '腿部+臀部+腹部',  status: 'waiting', phase: '', exercises: [] },
])
const elapsed = ref(0)
const errorMsg = ref('')
let retryCount = 0

function connectSSE() {
  const token = localStorage.getItem('token')
  const es = new EventSource(`${API_BASE}/fitness/plan/generate?token=${token}`)

  es.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    const day = days[data.day]
    if (day) {
      day.status = 'generating'
      day.phase = data.phase
    }
  })

  es.addEventListener('exercise_done', (e) => {
    const { day, exercise } = JSON.parse(e.data)
    days[day].exercises.push(exercise)   // ← 直接推入列表，触发响应式更新
  })

  es.addEventListener('day_done', (e) => {
    const data = JSON.parse(e.data)
    days[data.day].status = 'done'
  })

  es.addEventListener('done', (e) => {
    const plan = JSON.parse(e.data)
    workoutStore.setPlanFromSSE(plan)
    router.push('/home')
  })

  es.addEventListener('error', () => {
    retryCount++
    if (retryCount <= 3) {
      errorMsg.value = `连接断开，正在重连(${retryCount}/3)...`
      setTimeout(connectSSE, 2000)
    } else {
      errorMsg.value = '生成失败，请重试'
    }
  })
}
```

### 6.2 GeneratingPlan.vue — 模板结构

```html
<template>
  <div class="generating-plan">
    <!-- 顶部状态 -->
    <header class="gen-header">
      <h2>📅 正在生成你的 PPL 训练计划</h2>
      <span class="gen-meta">⏱ 已用时 {{ elapsed }}s | 已完成 {{ doneCount }}/{{ totalDays }} 天</span>
    </header>

    <!-- 错误提示（含重试按钮） -->
    <div v-if="errorMsg" class="gen-error">
      {{ errorMsg }}
      <button @click="retryCount=0; connectSSE()">重试</button>
    </div>

    <!-- 三天横向卡片 -->
    <div class="gen-cards">
      <div v-for="(day, i) in days" :key="i"
           class="gen-card" :class="[`status-${day.status}`]">
        <div class="card-header">
          <span class="day-icon">{{ statusIcon(day.status) }}</span>
          <span class="day-label">Day {{ i+1 }} · {{ day.label }}</span>
          <span class="day-focus">{{ day.focus }}</span>
        </div>
        <div class="card-phases">
          <span :class="phaseClass('search', day)">🔍 搜索</span>
          <span :class="phaseClass('select', day)">🎯 精选</span>
          <span :class="phaseClass('assemble', day)">🔧 组装</span>
        </div>
        <div class="card-exercises">
          <div v-for="ex in day.exercises" :key="ex.wger_id"
               class="exercise-item" v-motion-fade>
            ☐ {{ ex.name }} {{ ex.sets }}×{{ ex.reps }}
          </div>
          <div v-for="n in loadingSlots(day)" :key="'skeleton-'+n"
               class="exercise-skeleton">☐ 等待生成... ⏳</div>
        </div>
      </div>
    </div>
  </div>
</template>
```

**关键细节**：
- `exercise_done` 事件直接 `push` 到 `days[day].exercises`，触发 Vue 响应式更新 + 淡入动画
- 未生成的动作用骨架屏占位（`exercise-skeleton`），避免卡片空白抖动
- SSE 断连自动重试最多 3 次，超过则显示错误 + 重试按钮

**天数自适应**：`PPL_SPLITS` 支持 3/4/5/6 天，卡片需要响应式调整列数：

```css
.gen-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.gen-card {
  flex: 1 1 300px;    /* 最小 300px，多行自动折行 */
  max-width: 1fr;
}
/* 3 天 → 一行三列 | 4 天 → 2×2 | 5-6 天 → 3+3 或 3+2 自动折行 */
```

---

## 七、执行顺序

```
Step 1: 重写 exercise_agent.py（test/05 逻辑）
  ├─ 常量（MUSCLES, EQUIPMENT_FILTER, SELECT_PROMPT）
  ├─ search_all_muscles() + filter_by_equipment()
  ├─ llm_select()  ← LLM 精选最优动作
  └─ 删除所有 ReAct 代码

Step 1.5: 重写 plan_agent.py（test/06 逻辑）
  ├─ ASSEMBLY_PROMPT（组装 prompt）
  └─ assemble_one_day()  ← LLM 编排 warmup/main/cooldown

Step 2: 重写 plan_service.py
  ├─ 去掉 ScheduleAgent
  ├─ 编排 exercise_agent.select → plan_agent.assemble 三天并行
  └─ 增加 llm_stream / day_done SSE 事件

Step 3: 前端 — GeneratingPlan.vue + 路由
  ├─ 新增 GeneratingPlan.vue（生成直播间）
  ├─ 注册 /generating 路由
  ├─ OnboardingGuide 提交后跳转 /generating
  └─ 删除 GeneratingProgress.vue

Step 4: 测试
  ├─ pytest test/05_exercise_agent_precise.py   # 验证搜索精选
  ├─ pytest test/06_plan_agent_assembly.py      # 验证组装
  ├─ 启动后端 + 前端
  └─ 浏览器验证 SSE 流式效果
```

---

## 八、Phase / Tools / Skills Map

每个阶段标注**技术亮点**（简历用）和**验收条件**（干完确认没漏）。

### Phase 1：exercise_agent 核心

| 项目 | 内容 |
|------|------|
| **涉及文件** | `backend/app/agents/exercise_agent.py` |
| **搬自** | `test/05_exercise_agent_precise.py` |
| **工具/API** | wger MCP（搜索）、FastAPI `to_thread`（同步转异步） |
| **技术亮点** | Map-Reduce 按肌群并发搜索 → 合并去重；LLM 精选而非硬编码规则 |
| **简历关键词** | MCP 协议集成 · 确定性 Pipeline · LLM 结构化输出 |

**验收条件**：
- [x] `MUSCLES`, `EQUIPMENT_FILTER`, `SELECT_PROMPT` 常量从 test/05 搬运完毕
- [x] `search_all_muscles()` 对多肌群并发搜索，返回合并去重结果
- [x] `filter_by_equipment()` 按经验（新手/中级/高级）正确过滤器材
- [x] `llm_select()` 调用 LLM 返回 `[{name, wger_id, target_muscle}]` 格式
- [x] 所有 ReAct 代码（`tools` dict, `run` loop, `react_prompt` 等）已删除
- [ ] `pytest test/05_exercise_agent_precise.py` 通过

### Phase 2：plan_agent 核心

| 项目 | 内容 |
|------|------|
| **涉及文件** | `backend/app/agents/plan_agent.py` |
| **搬自** | `test/06_plan_agent_assembly.py` |
| **工具/API** | LLM 结构化输出（JSON mode） |
| **技术亮点** | 单 prompt 生成完整一天（warmup + main + cooldown），保留 wger_id |
| **简历关键词** | Prompt 工程 · 结构化生成 · 组装编排 |

**验收条件**：
- [x] `ASSEMBLY_PROMPT` 从 test/06 搬运，保留 wger_id 约束
- [x] `assemble_one_day()` 接收精选动作列表，返回 `{warmup:[], main:[], cooldown:[]}`
- [x] 输出 JSON 字段完整（name, sets, reps, rest_seconds, wger_id, exercise_type）
- [x] 旧整合逻辑（字段修复、跨天合并等）已删除
- [ ] `pytest test/06_plan_agent_assembly.py` 通过

### Phase 3：plan_service 编排 + SSE

| 项目 | 内容 |
|------|------|
| **涉及文件** | `backend/app/services/plan_service.py` |
| **工具/API** | FastAPI SSE (`StreamingResponse`)、`asyncio.gather` |
| **技术亮点** | Pipeline + Map-Reduce 编排；`return_exceptions=True` 容错；结构化 SSE 协议 |
| **简历关键词** | SSE 流式 · 容错设计 · 编排层抽象 |

**验收条件**：
- [x] `generate_plan_stream()` 调用 `get_ppl_schedule()` → 三天并行 agent → Reduce 汇总
- [x] 使用 `asyncio.gather(..., return_exceptions=True)`，失败的天被跳过而非取消其他天
- [x] SSE 事件完整：`progress` → `llm_stream` → `exercise_done` → `day_done` → `done`
- [x] `ScheduleAgent` 调用已移除
- [ ] 启动后端后 `curl` SSE 端点能收到完整事件序列

### Phase 4：GeneratingPlan.vue 前端

| 项目 | 内容 |
|------|------|
| **涉及文件** | `frontend/src/views/GeneratingPlan.vue`, `router/index.ts`, `OnboardingGuide.vue`, `workout.ts` |
| **工具** | Vue 3 Composition API, EventSource (SSE) |
| **技术亮点** | 流式渲染（`exercise_done` → push 触发响应式）；骨架屏占位；SSE 断连重试 |
| **简历关键词** | 实时 UI · SSE 客户端 · 流式渲染 · 体验优化 |

**验收条件**：
- [x] `/generating` 路由注册成功
- [x] OnboardingGuide Step 3 提交后跳转到 `/generating`
- [x] 三天卡片横向排列，各自独立显示阶段状态
- [x] `exercise_done` 事件到达后，动作带淡入动画插入列表
- [x] SSE 断开后显示重试提示，3 次失败后显示"生成失败，请重试"按钮
- [x] 生成完成后自动跳转到 `/home`
- [x] 原有 `GeneratingProgress.vue` 已删除

### Phase 5：清理 + 测试

| 项目 | 内容 |
|------|------|
| **涉及文件** | `schedule_agent.py`（删除） |
| **工具** | pytest |
| **技术亮点** | LLM mock 测试（Mock LLM 返回固定 JSON，不真实调用） |
| **简历关键词** | 测试策略 · Mock 外部依赖 |

**验收条件**：
- [x] `schedule_agent.py` 已删除
- [ ] 新建 `tests/test_exercise_agent.py`：覆盖 search → filter → select 链
- [ ] 新建 `tests/test_plan_agent.py`：覆盖 assemble 正常/空输入
- [ ] 新建 `tests/test_plan_service.py`：覆盖 SSE 事件序列、部分失败场景
- [ ] LLM 调用使用 mock，不依赖真实 API
- [ ] `pytest` 全部通过

### Phase 6（Bonus）：部署 + README

| 项目 | 内容 |
|------|------|
| **工具** | Docker, fly.io / Railway |
| **技术亮点** | 容器化部署 |
| **简历关键词** | DevOps · CI/CD |

**验收条件**：
- [ ] `Dockerfile` + `docker-compose.yml`（后端 + 前端）
- [ ] 部署到 fly.io / Railway，公网可访问
- [ ] README.md 含架构图、快速启动、技术栈说明
- [ ] 30s 演示 GIF

---

## 九、涉及文件总表

| 操作 | 文件路径 | 说明 |
|------|---------|------|
| 🔄 重写 | `backend/app/agents/exercise_agent.py` | 搜索+过滤+精选（test/05 逻辑） |
| 🔄 重写 | `backend/app/agents/plan_agent.py` | 单天组装（test/06 逻辑） |
| 🔄 重写 | `backend/app/services/plan_service.py` | 新编排流程 |
| ✅ 新增 | `frontend/src/views/GeneratingPlan.vue` | 生成直播间页面 |
| 🔄 修改 | `frontend/src/router/index.ts` | 注册 `/generating` 路由 |
| 🔄 修改 | `frontend/src/views/OnboardingGuide.vue` | 提交后跳转 `/generating` |
| 🔄 修改 | `frontend/src/stores/workout.ts` | 新增 generating 状态 |
| ❌ 删除 | `frontend/src/components/GeneratingProgress.vue` | 被 GeneratingPlan 取代 |
| ❌ 删除 | `backend/app/agents/schedule_agent.py` | 不再需要 |
| ⏸️ 保留 | `backend/app/services/llm_service.py` | 已就绪，无需改动 |
| ⏸️ 保留 | `test/05_exercise_agent_precise.py` | 保留作为单元测试 |
| ⏸️ 保留 | `test/06_plan_agent_assembly.py` | 保留作为单元测试 |
| ⏸️ 保留 | `test/08_e2e_day_by_day.py` | 保留作为集成测试 |


## 十、PPL 分化详解（Coordinator 核心）

### 10.1 经典 PPL 分化

PPL（Push / Pull / Legs）是国际最经典的训练分化之一。核心原则：
- **同一肌群 48 小时间隔**（推日用三头，拉日不再重复）
- **大复合动作优先**（卧推 > 飞鸟，深蹲 > 腿屈伸）
- **PPL 天然适配 3/4/5/6 天**

### 10.2 按每周天数分化

#### 3天/周（最经典 PPL）

| 天 | 训练内容 | 目标肌群 | 动作示例 |
|----|---------|---------|---------|
| Day 1 **推** | 胸部 + 肩部 + 三头 | 胸大肌、三角肌、肱三头肌 | 卧推、推举、臂屈伸 |
| Day 2 **拉** | 背部 + 二头 + 斜方肌 | 背阔肌、菱形肌、肱二头肌 | 划船、引体、弯举 |
| Day 3 **腿** | 股四头 + 腘绳肌 + 臀 + 腹 | 股四、股二、臀大肌、腹直肌 | 深蹲、硬拉、举腿 |

肌群完全不重叠，保证 48h 恢复。练一休一。

#### 4天/周（PPL + 补充日）

| 天 | 训练内容 | 目标肌群 | 说明 |
|----|---------|---------|------|
| Day 1 **推** | 胸部 + 肩部 + 三头 | 胸大肌、三角肌、肱三头肌 | 正常推日 |
| Day 2 **拉** | 背部 + 二头 + 斜方肌 | 背阔肌、菱形肌、肱二头肌 | 正常拉日 |
| Day 3 **腿** | 股四头 + 腘绳肌 + 臀 | 股四、股二、臀大肌 | 正常腿日 |
| Day 4 **全身** | 推(轻) + 拉(轻) + 腹 | 胸、背、腹 | 容量减半，加腹肌 |

第 4 天是"补充日"——从推和拉各挑 2 个动作（轻重量高次数），加上腹肌训练，不重复大重量。

#### 5天/周（PPL + 弱项强化）

| 天 | 训练内容 | 侧重 |
|----|---------|------|
| Day 1 **推(主)** | 胸部（大重量）+ 肩部 + 三头 | 力量为主 5-8RM |
| Day 2 **拉(主)** | 背部（大重量）+ 二头 | 力量为主 5-8RM |
| Day 3 **腿** | 股四头 + 腘绳肌 + 臀 + 腹 | 完整腿日 |
| Day 4 **推(辅)** | 肩部(弱项) + 三头 + 胸(轻) | 增肌容量，侧重弱势肌群 |
| Day 5 **拉(辅)** | 二头(弱项) + 斜方肌 + 背(轻) | 增肌容量，侧重弱势肌群 |

**原理**：推和拉各出现 2 次（一次主力量，一次辅容量），腿只 1 次（腿恢复最慢）。

#### 6天/周（PPL × 2）

| 天 | 训练内容 | 侧重 |
|----|---------|------|
| Day 1 **推(重)** | 胸部 + 肩部 + 三头 | 大重量 5-8RM |
| Day 2 **拉(重)** | 背部 + 二头 | 大重量 5-8RM |
| Day 3 **腿(重)** | 股四头 + 腘绳肌 + 臀 | 大重量 5-8RM |
| Day 4 **推(轻)** | 胸部 + 肩部 + 三头 | 增肌容量 10-15RM |
| Day 5 **拉(轻)** | 背部 + 二头 | 增肌容量 10-15RM |
| Day 6 **腿(轻)** | 腿 + 腹 + 小腿 | 增肌容量 10-15RM |

**原理**：同一肌群两次训练间隔刚好 48h。第二次用不同强度和 reps 范围，避免过度训练。

### 10.3 Coordinator 数据结构

```python
PPL_SPLITS = {
    "ppl_3": {  # 3天/周
        "name": "PPL（推/拉/腿）",
        "days": 3,
        "per_group": 3,  # 每组肌群选几个动作（3天每组3个，4+天每组2个，避免总动作过多）
        "schedule": [
            {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "desc": "训练胸大肌、三角肌和肱三头肌，以推类复合动作为主"},
            {"day": "第2天 · 拉", "focus": "背部 + 二头", "muscles": [12, 1], "desc": "训练背阔肌、菱形肌和肱二头肌，以拉类复合动作为主"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部 + 腹部", "muscles": [10, 11, 8, 6], "desc": "训练股四头肌、腘绳肌、臀大肌和腹部"},
        ],
    },
    "ppl_4": {  # 4天/周
        "name": "PPL + 全身补充",
        "days": 4,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "desc": "力量日：胸肩三头推类复合动作"},
            {"day": "第2天 · 拉", "focus": "背部 + 二头", "muscles": [12, 1], "desc": "力量日：背和二头拉类复合动作"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部", "muscles": [10, 11, 8], "desc": "力量日：下肢综合训练"},
            {"day": "第4天 · 全身", "focus": "全身轻量 + 腹部", "muscles": [4, 12, 6], "desc": "补充日：轻重量全身训练，侧重腹部肌群"},
        ],
    },
    "ppl_5": {  # 5天/周
        "name": "PPL + 弱项强化",
        "days": 5,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推(主)", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5], "desc": "主推日：大重量复合动作，5-8RM力量训练"},
            {"day": "第2天 · 拉(主)", "focus": "背部 + 二头", "muscles": [12, 1], "desc": "主拉日：大重量复合动作，5-8RM力量训练"},
            {"day": "第3天 · 腿", "focus": "腿部 + 臀部 + 腹部", "muscles": [10, 11, 8, 6], "desc": "完整腿日：股四、腘绳、臀大肌和腹部"},
            {"day": "第4天 · 推(辅)", "focus": "肩部 + 三头 + 胸部轻量", "muscles": [2, 5, 4], "desc": "辅助推日：肩和三头强化，胸部轻容量"},
            {"day": "第5天 · 拉(辅)", "focus": "二头 + 斜方肌 + 背部轻量", "muscles": [1, 9, 12], "desc": "辅助拉日：二头和斜方肌强化，背部轻容量"},
        ],
    },
    "ppl_6": {  # 6天/周
        "name": "PPL × 2（重量+容量）",
        "days": 6,
        "per_group": 2,
        "schedule": [
            {"day": "第1天 · 推(重)", "focus": "胸部 + 肩部 + 三头（大重量）", "muscles": [4, 2, 5], "desc": "大重量推日：5-8RM力量训练"},
            {"day": "第2天 · 拉(重)", "focus": "背部 + 二头（大重量）", "muscles": [12, 1], "desc": "大重量拉日：5-8RM力量训练"},
            {"day": "第3天 · 腿(重)", "focus": "腿部 + 臀部（大重量）", "muscles": [10, 11, 8], "desc": "大重量腿日：5-8RM力量训练"},
            {"day": "第4天 · 推(轻)", "focus": "胸部 + 肩部 + 三头（增肌容量）", "muscles": [4, 2, 5], "desc": "容量推日：10-15RM增肌训练"},
            {"day": "第5天 · 拉(轻)", "focus": "背部 + 二头（增肌容量）", "muscles": [12, 1], "desc": "容量拉日：10-15RM增肌训练"},
            {"day": "第6天 · 腿(轻)", "focus": "腿部 + 腹部（增肌容量）", "muscles": [10, 11, 6], "desc": "容量腿日：10-15RM增肌训练，加腹部"},
        ],
    },
}
```

### 10.4 前端展示 PPL 说明

在 OnboardingGuide 的 Step 3（选择天数后），显示当前选择的天数对应的 PPL 分化说明：

```
选 3天 → 显示：
「PPL（推/拉/腿）经典分化
  📅 第1天 推：胸部 + 肩部 + 三头
  📅 第2天 拉：背部 + 二头
  📅 第3天 腿：腿部 + 臀部 + 腹部」

选 4天 → 显示：
「PPL + 全身补充
  📅 第1天 推：胸部 + 肩部 + 三头
  📅 第2天 拉：背部 + 二头
  📅 第3天 腿：腿部 + 臀部
  📅 第4天 全身：全身轻量 + 腹部」
  （以此类推）
```

实现方式：前端预置 `PPL_SPLITS` 的简化版（只含名称和日程描述），根据用户选的 `days_per_week` 实时渲染。

也可以在生成完成后，在 `MainPage.vue` 的日历上方加一行小提示：
```
📋 当前计划：PPL（推/拉/腿）| 每周 3 天 | 周一三五
```

### 10.5 Coordinator 接收 days_per_week → 输出 schedule

```python
def get_ppl_schedule(days_per_week: int) -> dict:
    """根据用户每周天数返回对应的 PPL 分化方案"""
    key = f"ppl_{days_per_week}"
    if key not in PPL_SPLITS:
        key = "ppl_3"  # 默认回退
    return PPL_SPLITS[key]
```
