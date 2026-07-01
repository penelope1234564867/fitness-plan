# 健身计划生成系统重构设计 v2

> Pipeline + Map-Reduce 架构，前端参与训练分化决策，后端提速 3-5 倍

---

## 1. 现状问题

### 1.1 当前架构（ReActAgent 并行）

```
PlanRequest
  ├──→ ScheduleAgent (ReActAgent, max_steps=6)
  ├──→ ExerciseAgent (ReActAgent, max_steps=8)
  └──→ PlanAgent (SimpleAgent)
```

### 1.2 核心痛点

| 问题 | 原因 | 影响 |
|------|------|------|
| **慢** | ReActAgent 每步一次 LLM 调用，ExerciseAgent 最多 8 步 = 20-40s | 用户体验差 |
| **黑盒** | 用户不知道训练分化依据 | 缺乏信任和参与感 |
| **结果不合理** | 没有先规划再搜索，肌肉 ID 硬编码不全 | 动作组合逻辑混乱 |
| **输出格式不匹配** | ExerciseAgent 输出 `[{...}]`，但 `plan_service.py` 期望 `{"exercises": [...]}` | 数据丢失 |

---

## 2. 目标架构：Pipeline + Map-Reduce

```
┌─────────────────────────────────────────────────────────┐
│                      Pipeline (3阶段串行)                 │
├───────────┬──────────────────┬──────────────────────────┤
│  阶段①     │    阶段②          │    阶段③                 │
│  训练分化   │    动作搜索       │    计划组装              │
│  规划      │    Map-Reduce    │    LLM 整合              │
│           │                  │                          │
│  用户参与   │    代码并发       │    结果格式化            │
│  前端交互   │    API 调用      │    输出校验              │
└───────────┴──────────────────┴──────────────────────────┘
                    │
      ┌─────────────┴─────────────┐
      │ 此架构比 ReActAgent       │
      │ LLM 调用次数：8+ → 2-3   │
      │ 总耗时：20-40s → 5-10s   │
      └───────────────────────────┘
```

### 2.1 为何选择此架构

- **Pipeline**：三个阶段职责清晰、依赖明确，适合"先规划→再执行→后组装"的业务逻辑
- **Map-Reduce**：搜索多个肌群的动作是完全独立的，天然可并发，大幅降低搜索延迟
- **LLM 只干两件事**：规划训练分化 + 格式化输出。搜索和执行全交给代码

---

## 3. 阶段①：训练分化规划（前端交互 + LLM）

### 3.1 流程图

```
用户填基本信息 ──→ 显示分化选项 ──→ 用户选择/自定义 ──→ 预览确认
(目标/经验/天数)    (推荐高亮)       (可选微调)        (日历视图)
```

### 3.2 预设分化方案

每个方案包含：**名称 + 原理 + 适合人群 + 每日肌群分布 + 推荐标签**

#### 方案卡片设计

```
┌──────────────────────────────────────────────────┐
│  ● 推拉腿分化 (PPL)                    ← 推荐    │
│                                                  │
│  📋 原理：推类动作一天，拉类一天，腿一天            │
│  适合增肌，每周 3 天训练                          │
│                                                  │
│  ┌──── 周一 ────┬──── 周三 ────┬──── 周五 ────┐  │
│  │ 主要：胸部   │ 主要：背部   │ 主要：腿部    │  │
│  │ 辅助：三头   │ 辅助：二头   │ 辅助：腹肌    │  │
│  │ 类型：推类   │ 类型：拉类   │ 类型：下肢    │  │
│  └──────────────┴──────────────┴──────────────┘  │
│                                                  │
│  [选择此方案]                                     │
└──────────────────────────────────────────────────┘
```

#### 完整方案列表

| 方案 | 天数 | 适用目标 | 训练频率/肌群 |
|------|------|----------|--------------|
| 🏆 **推拉腿 (PPL)** | 3天 | 增肌 | 胸/肩/三头 → 背/二头 → 腿/腹 |
| **上下肢分化** | 4天 | 增肌/塑形 | 上肢 → 下肢 → 上肢 → 下肢 |
| **全身训练** | 2-3天 | 新手/减脂 | 每次全身主要肌群 |
| **推拉腿+上下肢** | 5天 | 高级增肌 | PPL + 上肢 + 下肢 |
| **自定义分化** | 任意 | 灵活 | 用户自选肌群组合 |

#### 推荐算法逻辑

```
if days == 2:     推荐 "全身训练"
if days == 3:
    if goal == "增肌":   推荐 "推拉腿 PPL"
    if goal == "减脂":   推荐 "全身训练"
    if experience == "新手": 推荐 "全身训练"
if days == 4:     推荐 "上下肢分化"
if days == 5:     推荐 "推拉腿+上下肢"
```

### 3.3 自定义分化交互（选项组合式）

用户通过下拉菜单+点选完成，不写文字：

```
自定义训练分化

每周 [3天]

第 1 天
  主要肌群: [▼胸部 ▼]
  辅助肌群: [+三头肌 ▼] [+前三角肌 ▼]
  动作偏好: [复合为主 ▼]

第 2 天
  主要肌群: [▼背部 ▼]
  辅助肌群: [+二头肌 ▼]
  动作偏好: [复合为主 ▼]

第 3 天
  主要肌群: [▼腿部 ▼]
  辅助肌群: [+腹肌 ▼]
  动作偏好: [混合 ▼]

[+ 添加训练日] [重置]
```

**肌群下拉选项**：胸部、背部、肩部、腿部、肱二头肌、肱三头肌、腹部、臀部、小腿

**动作偏好选项**：复合为主（推荐）、孤立为主、混合

**后端接收格式**：
```json
{
  "template": "custom",
  "days": [
    {"main_muscle": "胸部", "accessory_muscles": ["三头肌", "前三角肌"], "preference": "compound"},
    {"main_muscle": "背部", "accessory_muscles": ["二头肌"], "preference": "compound"},
    {"main_muscle": "腿部", "accessory_muscles": ["腹肌"], "preference": "mixed"}
  ]
}
```

### 3.4 后端 API 扩展

```python
# 新增端点
POST /api/v1/fitness/training-splits
  Request: { goal, experience_level, days_per_week }
  Response: { splits: [{ id, name, description, days, is_recommended, daily_breakdown }] }

POST /api/v1/fitness/confirm-split
  Request: { session_id, split_id | custom_split }
  Response: { split_confirmed: true, daily_focus: [...] }
```

### 3.5 接口对接

现有 `PlanRequest` 扩展 `split` 字段：

```python
class PlanRequest(BaseModel):
    goal: str
    experience_level: str
    workout_location: str
    days_per_week: int = 3
    duration_weeks: int = 4
    city: Optional[str] = ""
    notes: Optional[str] = ""
    training_split: Optional[dict] = None  # 新增：用户选的分化方案
```

前端在生成计划前多一步：显示分化选项 → 用户选择 → 再提交生成请求。

---

## 4. 阶段②：动作搜索（Map-Reduce）

### 4.1 架构

```
阶段①输出的 daily_focus
  [
    {"day": "周一", "focus": "胸部+三头", "muscles": {"primary": ["胸"], "secondary": ["三头"]}},
    {"day": "周三", "focus": "背部+二头", "muscles": {"primary": ["背"], "secondary": ["二头"]}},
    ...
  ]
            │
            ▼
  ┌─────────────────────────────────────┐
  │         Map 阶段（全并发）            │
  │                                     │
  │  异步任务池 (asyncio.gather)         │
  │  ┌──────────┐   ┌──────────┐       │
  │  │ 搜胸肌    │   │ 搜三头肌  │       │
  │  │ API 1.2s │   │ API 1.1s │       │
  │  └──────────┘   └──────────┘       │
  │  ┌──────────┐   ┌──────────┐       │
  │  │ 搜背部    │   │ 搜二头肌  │       │
  │  │ API 1.3s │   │ API 1.0s │       │
  │  └──────────┘   └──────────┘       │
  └──────────────┬─────────────────────┘
                 │ 等待所有 API 返回
                 ▼
  ┌─────────────────────────────────────┐
  │         Reduce 阶段                  │
  │  合并 + 去重 + 按设备过滤            │
  │  输出去重后的动作池                   │
  └─────────────────────────────────────┘
```

### 4.2 肌群→wger ID 映射

```python
MUSCLE_TO_WGER_ID = {
    "胸部": 4, "chest": 4,
    "背部": 12, "back": 12,
    "肩部": [2, 3],  # 前束+中束
    "腿部": [10, 11],  # 股四+股二
    "臀部": 8,
    "肱二头肌": 1, "二头": 1,
    "肱三头肌": 14, "三头": 14,
    "腹部": 7, "腹肌": 7,
    "小腿": [6, 15],
}
```

### 4.3 搜索逻辑

```python
async def search_exercises_for_split(daily_focus: list, location: str, goal: str) -> list:
    """Map-Reduce 搜索所有肌群的动作"""
    
    # ── Map：收集所有需要搜索的肌群 ──
    search_tasks = []
    for day in daily_focus:
        for muscle in day["muscles"]["primary"] + day["muscles"]["secondary"]:
            wger_ids = MUSCLE_TO_WGER_ID.get(muscle, [])
            if isinstance(wger_ids, int):
                wger_ids = [wger_ids]
            for wid in wger_ids:
                search_tasks.append(
                    search_single_muscle(wid, location, goal)
                )
    
    # ── 去重相同的搜索 ──
    unique_tasks = list(set(search_tasks))
    
    # ── 全并发执行 ──
    results = await asyncio.gather(*[task() for task in unique_tasks])
    
    # ── Reduce：合并去重 ──
    seen = set()
    exercise_pool = []
    for batch in results:
        for ex in batch:
            if ex["wger_id"] not in seen:
                seen.add(ex["wger_id"])
                exercise_pool.append(ex)
    
    return exercise_pool


async def search_single_muscle(wger_id: int, location: str, goal: str) -> list:
    """搜索单个肌群的动作（并发调用 wger API）"""
    # 通过 MCP Client 调用 wger MCP Server 的 search 工具
    equipment = location_to_equipment(location)
    result = await mcp_client.call_tool("wger_search_exercises", {
        "muscle": wger_id,
        "equipment": equipment,
        "limit": 10,
    })
    return parse_exercises(result)
```

### 4.4 地点→器材映射

```python
LOCATION_EQUIPMENT = {
    "健身房": None,        # 不限器材
    "居家": [7, 8, 4],     # 自重、弹力带、瑜伽垫
    "户外": [7],            # 自重为主
}
```

---

## 5. 阶段③：计划组装（1 次 LLM 调用）

### 5.1 输入

```python
{
  "user_info": {"goal": "增肌", "experience": "中级", "location": "健身房"},
  "schedule": [{"day": "周一", "focus": "胸部+三头", ...}, ...],
  "exercise_pool": [{"wger_id": 123, "name": "Barbell Bench Press", ...}, ...]
}
```

### 5.2 处理流程

阶段③ 用 `SimpleAgent`（**不是 ReActAgent**）一次 LLM 调用完成：

1. 接收训练分化 + 动作池
2. 为每个训练日分配 4-6 个动作
3. 按复合→孤立顺序排列
4. 根据目标/经验分配组数次数
5. 生成热身和冷身
6. 输出完整周计划

### 5.3 输出格式

```json
{
  "weekly_plans": [{
    "week": 1,
    "days": [{
      "day": "周一",
      "focus": "胸部 + 三头",
      "split_type": "push",   // 标注所属分化类型
      "warmup": [...],
      "main": [
        {
          "name": "Barbell Bench Press",
          "target_muscle": "Chest",
          "sets": 4,
          "reps": 10,
          "rest_seconds": 90,
          "weight_suggestion": "大重量 (6-10RM)",
          "wger_id": 123,
          "image_url": "https://...",
          "description": "Lie on a flat bench...",
          "exercise_type": "compound",   // 新增：复合/孤立
          "muscle_group": "primary"      // 新增：主要/辅助
        }
      ],
      "cooldown": [...]
    }]
  }]
}
```

---

## 6. 后端代码结构变化

### 6.1 新文件结构

```
backend/app/
  ├── agents/
  │   ├── exercise_agent.py    ← 删除（不再需要 ReActAgent）
  │   ├── plan_agent.py        ← 保留，简化（阶段③）
  │   ├── schedule_agent.py    ← 保留（天气查询）
  │   └── training_split.py    ← 新增！阶段①逻辑
  │
  ├── services/
  │   ├── plan_service.py      ← 改造（Pipeline 编排）
  │   ├── wger_service.py      ← 增强（Map-Reduce 批量搜索）
  │   └── split_service.py     ← 新增！分化推荐逻辑
  │
  ├── models/
  │   └── schemas.py           ← PlanRequest 扩展 split 字段
  │
  └── api/routes/
      └── fitness.py           ← 新增分化相关端点
```

### 6.2 plan_service.py 新流程

```python
async def generate_plan_stream(request: PlanRequest, db: Session):
    """Pipeline 架构：规划 → 搜索 → 组装"""
    
    # ── 阶段①：训练分化规划（已由前端确认） ──
    yield _sse_event("progress", "📋 已确认训练分化方案")
    
    # ── 阶段②：Map-Reduce 并行搜索动作 ──
    yield _sse_event("progress", "🔍 正在搜索训练动作...")
    exercises = await map_reduce_search(
        request.training_split,
        request.workout_location,
        request.goal
    )
    
    # ── ScheduleAgent（查询天气，编排日程） ──
    yield _sse_event("progress", "☀️ 正在查询天气...")
    schedule = await run_schedule_agent(...)
    
    # ── 阶段③：组装周计划（1次LLM调用） ──
    yield _sse_event("progress", "📋 正在生成完整计划...")
    plan = await run_plan_agent(user_info, exercises, schedule)
    
    # ── 存库返回 ──
    yield _sse_event("done", json.dumps(plan))
```

### 6.3 执行速度对比

| 步骤 | 当前架构 | 新架构 | 提升 |
|------|---------|--------|------|
| LLM 调用次数 | 8-10 次 | 2-3 次 | **3-5x** |
| 搜索耗时 | 12-20s （串行） | 1-3s （并行） | **6x** |
| 总流程耗时 | 25-45s | 8-15s | **3x** |

---

## 7. 前端新增交互

### 7.1 页面流程

```
[填写信息页] ──→ [选择分页] ──→ [预览确认] ──→ [生成计划]
                  ↑ 新增         ↑ 新增
```

### 7.2 分化选择页组件结构

```
TrainingSplitSelector
  ├── SplitCard (× N 个预设方案)
  │     ├── 方案名称 + 推荐标签
  │     ├── 原理说明
  │     ├── 每日预览（3 天的小日历）
  │     └── 选择按钮
  │
  ├── CustomSplitBuilder（展开时显示）
  │     ├── DaySelector（每天一行）
  │     │     ├── MainMuscleDropdown
  │     │     ├── AccessoryMuscleMultiSelect
  │     │     └── PreferenceRadio
  │     └── AddDayButton
  │
  └── SelectedSplitPreview
        ├── 完整周历视图
        └── [确认并生成计划] 按钮
```

### 7.3 状态管理

```
选择前: 展示方案卡片，推荐高亮
选择中: 卡片展开，显示详细预览
自定义: 折叠面板展开，显示每日编辑
确认后: 预览周历，提交生成
```

---

## 8. 简历描述建议

> *重构健身计划生成系统，将 LLM 应用架构从 ReActAgent 范式升级为 Pipeline + Map-Reduce 架构*
>
> - **Pipeline 三阶段设计**：将生成流程拆分为「训练分化规划 → 动作搜索 → 计划组装」，每阶段职责单一
> - **Map-Reduce 并行搜索**：在动作搜索阶段通过 `asyncio.gather` 并发查询 wger API，搜索延迟降低 80%
> - **前端参与决策**：设计训练分化选择器，让用户参与计划制定，提升透明度和个性化
> - **性能提升**：LLM 调用从 8+ 次减少到 2-3 次，整体生成时间从 30s+ 降至 8-12s，提升约 3 倍

---

## 9. 实施步骤

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 1 | 前端：新增 TrainingSplitSelector 组件 + 分化选择页面 | `frontend/` |
| 2 | 前端：PlanRequest 扩展 split 字段 | `schemas.py` |
| 3 | 后端：新增 split_service.py（分化推荐逻辑） | `split_service.py` |
| 4 | 后端：新增 training_split.py（阶段①LLM逻辑） | `training_split.py` |
| 5 | 后端：改造 wger_service.py（Map-Reduce 批量搜索） | `wger_service.py` |
| 6 | 后端：改造 plan_service.py（Pipeline 编排） | `plan_service.py` |
| 7 | 后端：简化 plan_agent.py（阶段③只做组装） | `plan_agent.py` |
| 8 | 后端：删除旧的 exercise_agent.py 或大幅简化 | `exercise_agent.py` |
| 9 | 端到端测试 | — |
