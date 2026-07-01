# Pipeline 架构端到端测试计划

> **对于执行代理:** 使用此计划进行分步骤实现与验证。步骤使用复选框 (`- [ ]`) 跟踪进度。

**目标:** 验证 Pipeline（ExerciseAgent 搜索+精选 → PlanAgent 组装）在真实 wger API 下能否跑通 PPL 输入 → 完整周计划

**架构:** ExerciseAgent（搜索wger → 器材过滤 → LLM精选每个肌群3-4个动作）→ PlanAgent（1次LLM调用组装周计划）。全部共2次LLM调用。

**测试栈:** Python, httpx, hello_agents(LLM), wger.de API, ThreadPoolExecutor

**当前测试文件:** `test/04_ppl_pipeline_e2e.py`

---

## 全局约束

- 所有 wger API 调用使用 `https://wger.de/api/v2/exerciseinfo/` 端点
- 语言参数固定 `language=2`（英文），LLM做中文翻译
- 器材过滤：新手器材白名单 `[7, 8, 4, 5, 6, 11]`（自重/卧推凳/瑜伽垫/瑞士球/引体杆/弹力带）
- wger API 无需 API Key
- 搜索并发度：ThreadPoolExecutor 最多 10 个 worker

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `test/01_wger_muscles.py` | 查看 wger 肌群列表（已完成） |
| `test/02_wger_search_exercises.py` | 搜索 PPL 各肌群动作，看 API 返回格式（已完成） |
| `test/03_filter_by_equipment.py` | 测试按器材过滤的可行性（已完成） |
| `test/04_ppl_pipeline_e2e.py` | **主测试**：完整 Pipeline 端到端（建设中） |
| `test/05_exercise_agent_precise.py` | ExerciseAgent 精选逻辑专项测试（新增） |
| `test/06_plan_agent_assembly.py` | PlanAgent 组装逻辑专项测试（新增） |

---

### Task 1: 重构 `test/04_ppl_pipeline_e2e.py` — 改进精选逻辑

**文件:**
- Modify: `test/04_ppl_pipeline_e2e.py`

**接口:**
- Consumes: `MUSCLES` 肌群ID映射, `PPL_SPLIT` 分化定义, `EQUIPMENT_FILTER` 器材白名单
- Produces: 精选后的动作列表（每个肌群3-4个）

**当前问题:** 精选逻辑 `select_exercises_per_muscle()` 只按器材类型去重，没有考虑动作是否适合用户（比如给新手选了 Dragon-flag、Archer Pull Up 等高级动作）。应该改用 **LLM 精选**。

- [ ] **Step 1: 新增 LLM 精选函数 `llm_select_exercises()`**

在 `04_ppl_pipeline_e2e.py` 中找到 `select_exercises_per_muscle()` 函数，在其下方增加 LLM 精选函数：

```python
EXERCISE_SELECT_PROMPT = """你是一个专业健身教练。请根据用户信息，从每个肌群的动作中选出最适合的 {per_group} 个。

## 用户信息
- 目标：{goal}
- 经验水平：{experience}
- 训练地点：{location}
- 训练分化：{split_name}

## 各肌群可用动作
{grouped_exercises}

## 选择规则
1. 每个肌群选 {per_group} 个，不要多选
2. {experience} 优先选固定器械和自重动作，避免爆发力动作
3. 选择的动作之间要有区分度（不同器材、不同动作模式）
4. 返回 JSON，格式：{{"selected": [{{"wger_id": 123, "reason": "选择理由"}}, ...]}}
"""


def llm_select_exercises(grouped_exercises: dict, goal: str, experience: str, location: str, per_group=3) -> list:
    """LLM从每个肌群中精选最适合的动作"""
    # 格式化分组数据
    id_to_name = {v: k for k, v in MUSCLES.items()}
    group_texts = []
    for mid, exs in grouped_exercises.items():
        muscle_name = id_to_name.get(mid, str(mid))
        ex_list = ", ".join(f"[{ex['wger_id']}] {ex['name']}" for ex in exs)
        group_texts.append(f"  {muscle_name}(ID={mid}): {ex_list}")
    grouped_text = "\n".join(group_texts)

    prompt = EXERCISE_SELECT_PROMPT.format(
        per_group=per_group,
        goal=goal, experience=experience, location=location,
        split_name="PPL（推/拉/腿）",
        grouped_exercises=grouped_text,
    )

    llm = get_llm()
    response = llm.invoke([{"role": "user", "content": prompt}], timeout=30)

    text = response.content if not isinstance(response, str) else response
    # 提取 JSON
    try:
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            result = json.loads(text[start:end].strip())
        else:
            result = json.loads(text)
        selected_ids = {item["wger_id"] for item in result.get("selected", [])}
        # 从原始分组数据中提取选中的动作
        selected = []
        for mid, exs in grouped_exercises.items():
            for ex in exs:
                if ex["wger_id"] in selected_ids:
                    selected.append(ex)
        return selected
    except (json.JSONDecodeError, ValueError, KeyError):
        # 解析失败时回退到代码精选
        return select_exercises_per_muscle(grouped_exercises, max_per=per_group)
```

- [ ] **Step 2: 修改主流程，用 LLM 精选替代代码精选**

找到主流程中调用 `select_exercises_per_muscle()` 的地方，替换为 `llm_select_exercises()`：

```python
    # 每个肌群精选 3 个（用 LLM）
    per_group = 3  # 3天PPL，每个肌群给 3 个选择
    selected = llm_select_exercises(filtered_groups, goal, experience, location, per_group)
    print(f"\n[阶段4] LLM 精选: 共 {len(selected)} 个（每个肌群选 {per_group} 个）")
```

- [ ] **Step 3: 增加精选质量的校验**

在打印精选结果后，增加一个简单的校验，检查是否有明显不合理的选择：

```python
    # 校验精选结果
    suspicious = []
    for ex in selected:
        # 检查是否有动作名包含"Muscle up"但肌群不是胸/背等新手友好动作
        name_lower = ex.get("name", "").lower()
        if "muscle up" in name_lower or "dragon" in name_lower:
            suspicious.append(ex)
    if suspicious:
        print(f"        ⚠️ 可能有不适合新手的动作:")
        for ex in suspicious:
            print(f"          [{ex['wger_id']}] {ex['name']}")
```

- [ ] **Step 4: 运行测试**

```bash
cd C:\Users\18194\Desktop\fitness-plan\backend
PYTHONIOENCODING=utf-8 python ..\test\04_ppl_pipeline_e2e.py
```

预期结果：
- [阶段2] 搜到 ~135 个动作，耗时 < 5s
- [阶段3] 过滤后 ~80 个动作
- [阶段4] LLM 精选 27 个动作（9肌群×3个），不应出现 Dragon-flag、Muscle up 等不适合新手的动作
- [阶段5] LLM 组装完成，输出完整周计划

---

### Task 2: 分离 ExerciseAgent 测试脚本

**文件:**
- Create: `test/05_exercise_agent_precise.py`

**接口:**
- Consumes: `goal`, `experience`, `location`, `days`, `split_name`
- Produces: 精选后的动作列表（含 wger_id, name, equipment, target_muscle）

**目标:** 独立测试 ExerciseAgent 的搜索+过滤+精选流程，不依赖 PlanAgent

- [ ] **Step 1: 创建 `test/05_exercise_agent_precise.py`**

```python
"""Step 5: ExerciseAgent 精选逻辑专项测试

验证：接收训练分化 → 搜索wger → 过滤 → LLM精选 → 输出稳定动作列表
输出应满足：同用户每次跑，精选结果一致，无随机性
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
from app.services.llm_service import get_llm

import httpx
WGER_BASE = "https://wger.de/api/v2"
httpx_client = httpx.Client(timeout=30)

# ── 配置 ──
MUSCLES = {
    "胸": 4, "肩": 2, "三头": 5,
    "背": 12, "二头": 1,
    "腿前": 10, "腿后": 11, "臀": 8, "腹": 6,
}

# PPL / 上下肢 / 全身 三种分化预设
SPLITS = {
    "ppl": {
        "name": "PPL（推/拉/腿）",
        "days": 3,
        "per_group": 3,
        "schedule": [
            {"day": "第1天", "focus": "胸部 + 肩部 + 三头", "muscles": [4, 2, 5]},
            {"day": "第2天", "focus": "背部 + 二头",         "muscles": [12, 1]},
            {"day": "第3天", "focus": "腿部 + 臀部 + 腹部",  "muscles": [10, 11, 8, 6]},
        ]
    },
    "upper_lower": {
        "name": "上下肢分化",
        "days": 4,
        "per_group": 2,
        "schedule": [
            {"day": "第1天", "focus": "上肢（胸+背+肩+手臂）", "muscles": [4, 12, 2, 1, 5]},
            {"day": "第2天", "focus": "下肢（腿+臀+腹）",     "muscles": [10, 11, 8, 6]},
            {"day": "第3天", "focus": "上肢（胸+背+肩+手臂）", "muscles": [4, 12, 2, 1, 5]},
            {"day": "第4天", "focus": "下肢（腿+臀+腹）",     "muscles": [10, 11, 8, 6]},
        ]
    },
    "fullbody": {
        "name": "全身训练",
        "days": 3,
        "per_group": 2,
        "schedule": [
            {"day": "第1天", "focus": "全身A（推+腿）",   "muscles": [4, 2, 10, 8]},
            {"day": "第2天", "focus": "全身B（拉+腿+腹）", "muscles": [12, 1, 11, 6]},
            {"day": "第3天", "focus": "全身C（推+拉+肩）", "muscles": [4, 5, 12, 2]},
        ]
    },
}

EQUIPMENT_FILTER = {
    "新手": [7, 8, 4, 5, 6, 11],
    "中级": [1, 3, 7, 8, 6],
    "高级": [],
}

def search_all_muscles(muscle_ids):
    """Map-Reduce 搜索所有肌群，返回分组 dict"""
    from concurrent.futures import ThreadPoolExecutor
    def search_one(mid):
        resp = httpx_client.get(
            f"{WGER_BASE}/exerciseinfo/",
            params={"format": "json", "language": 2, "muscles": mid, "limit": 15, "status": 2}
        )
        results = []
        for ex in resp.json().get("results", []):
            name = ""
            for tr in ex.get("translations", []):
                if tr.get("language") == 2:
                    name = tr.get("name", "")
                    break
            if not name:
                continue
            equip_ids = [e["id"] for e in ex.get("equipment", []) if isinstance(e, dict) and e.get("id")]
            results.append({"wger_id": ex["id"], "name": name, "muscle_id": mid, "equipment": equip_ids})
        return results

    with ThreadPoolExecutor(max_workers=10) as pool:
        all_results = list(pool.map(search_one, muscle_ids))
    return dict(zip(muscle_ids, all_results))


def filter_by_equipment(grouped, experience):
    allowed = EQUIPMENT_FILTER.get(experience, [])
    if not allowed:
        return grouped
    result = {}
    for mid, exs in grouped.items():
        filtered = [ex for ex in exs if not ex.get("equipment") or all(e in allowed for e in ex["equipment"])]
        result[mid] = filtered
    return result


SELECT_PROMPT = """你是一个专业健身教练。请从每个肌群中选出最适合用户的 {per_group} 个动作。

用户: 目标={goal}, 经验={experience}, 地点={location}
训练分化: {split_name}

各肌群可用动作:
{grouped_data}

规则:
1. 每个肌群选 {per_group} 个
2. {experience} 优先选固定器械和自重动作，避免爆发力或高难度动作
3. 动作之间要有区分度（不同器材、不同平面）
4. 返回 JSON: {{"selected": [{{"wger_id": 123, "muscle_id": 4, "reason": "..."}}]}}
"""


def llm_select(grouped, goal, experience, location, split_name, per_group=3):
    """LLM精选每个肌群的动作"""
    id_to_name = {v: k for k, v in MUSCLES.items()}
    lines = []
    for mid, exs in grouped.items():
        if not exs:
            continue
        name = id_to_name.get(mid, str(mid))
        items = ", ".join(f"[{e['wger_id']}] {e['name']}" for e in exs)
        lines.append(f"  {name}(ID={mid}): {items}")

    prompt = SELECT_PROMPT.format(
        per_group=per_group, goal=goal, experience=experience,
        location=location, split_name=split_name,
        grouped_data="\n".join(lines),
    )

    llm = get_llm()
    resp = llm.invoke([{"role": "user", "content": prompt}], timeout=30)
    text = resp.content if not isinstance(resp, str) else resp

    try:
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        result = json.loads(text)
        selected_ids = {(item["wger_id"], item["muscle_id"]) for item in result.get("selected", [])}
    except (json.JSONDecodeError, KeyError):
        print(f"  ⚠️ LLM返回解析失败，使用代码回退")
        # 回退：每个肌群取前 N 个
        selected = []
        for mid, exs in grouped.items():
            for ex in exs[:per_group]:
                selected.append(ex)
        return selected

    selected = []
    for mid, exs in grouped.items():
        count = 0
        for ex in exs:
            if (ex["wger_id"], mid) in selected_ids and count < per_group:
                selected.append(ex)
                count += 1
    return selected


def test_split(split_key, goal, experience, location):
    """测试一种训练分化的精选流程"""
    split = SPLITS[split_key]
    muscle_ids = set()
    for day in split["schedule"]:
        muscle_ids.update(day["muscles"])
    muscle_ids = sorted(muscle_ids)

    print(f"\n{'='*60}")
    print(f"  测试: {split['name']} | {goal} | {experience} | {location}")
    print(f"{'='*60}")

    # 搜索
    t0 = time.time()
    grouped = search_all_muscles(muscle_ids)
    total = sum(len(v) for v in grouped.values())
    print(f"  搜索: {total} 个动作, {time.time()-t0:.1f}s")

    # 过滤
    filtered = filter_by_equipment(grouped, experience)
    after = sum(len(v) for v in filtered.values())
    print(f"  过滤: {total} → {after} 个")

    # LLM精选
    per = split["per_group"]
    t0 = time.time()
    selected = llm_select(filtered, goal, experience, location, split["name"], per)
    sel_time = time.time() - t0
    print(f"  精选: {len(selected)} 个动作 (每个肌群{per}个), LLM耗时 {sel_time:.1f}s")

    # 打印结果
    for ex in selected:
        equip_str = "自重" if not ex.get("equipment") else str(ex["equipment"])
        print(f"    [{ex['wger_id']}] {ex['name'][:40]} | 器材: {equip_str}")

    # 校验：检查每个肌群数量
    from collections import Counter
    counts = Counter(ex["muscle_id"] for ex in selected)
    for mid in muscle_ids:
        expected = per
        actual = counts.get(mid, 0)
        status = "OK" if actual == expected else f"少{expected-actual}个"
        if actual != expected:
            print(f"  ⚠️ 肌群 {mid}: 期望 {expected}, 实际 {actual}")

    return selected


if __name__ == "__main__":
    # 测试 3 种分化方案
    test_split("ppl", "增肌", "新手", "健身房")
    test_split("upper_lower", "塑形", "中级", "居家")
    test_split("fullbody", "减脂", "新手", "户外")
```

- [ ] **Step 2: 运行测试**

```bash
cd C:\Users\18194\Desktop\fitness-plan\backend
PYTHONIOENCODING=utf-8 python ..\test\05_exercise_agent_precise.py
```

预期：
- 3 种分化方案全部跑通
- 每种方案精选的动作数量正确（PPL=27, 上下肢=20, 全身=12）
- 没有出现明显不适合该经验水平的动作
- 总耗时 < 30s

---

### Task 3: 分离 PlanAgent 组装测试脚本

**文件:**
- Create: `test/06_plan_agent_assembly.py`

**接口:**
- Consumes: 精选后动作列表（18-27个）, 训练分化, 用户目标/经验
- Produces: 完整周计划 JSON

**目标:** 独立测试 PlanAgent 的组装逻辑，输入固定的动作列表，验证输出稳定性

- [ ] **Step 1: 创建 `test/06_plan_agent_assembly.py`**

```python
"""Step 6: PlanAgent 组装逻辑专项测试

验证：接收精选好的动作列表 → 1次LLM调用 → 输出完整周计划
输出应包含：warmup/main/cooldown, wger_id保留, 中文名称
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
from app.services.llm_service import get_llm


ASSEMBLY_PROMPT = """你是一个专业健身教练。请将以下动作组装成一份周训练计划。

## 用户信息
- 目标：{goal}
- 经验水平：{experience}
- 训练地点：{location}
- 训练分化：{split_name}

## 训练日程
{schedule}

## 可用动作
{exercises}

## 要求
1. 每天安排 5-6 个主训练动作，按复合→孤立顺序排列
2. 组数次数按 {experience} 标准
3. 每天配 2 个热身和 1 个冷身
4. 所有主训练动作必须从可用动作中选取，保留 wger_id
5. 动作名称使用中文

## 输出格式（只输出 JSON）
{{
  "weekly_plans": [{{
    "week": 1,
    "days": [
      {{
        "day": "第1天",
        "focus": "训练重点",
        "warmup": [{{"name": "热身动作", "sets": 2, "reps": 15}}],
        "main": [
          {{"name": "动作名", "target_muscle": "肌群", "sets": 3, "reps": 12,
            "rest_seconds": 60, "wger_id": 123, "exercise_type": "compound"}}
        ],
        "cooldown": [{{"name": "拉伸", "sets": 2, "reps": 30}}]
      }}
    ]
  }}]
}}
"""


def test_plan_assembly(goal, experience, location, split_name, schedule, exercises):
    """测试 PlanAgent 组装"""
    schedule_text = "\n".join(f"  {d['day']}: {d['focus']}" for d in schedule)
    ex_texts = [f"  [{ex['wger_id']}] {ex['name']} (肌群ID: {ex['muscle_id']})" for ex in exercises]
    ex_text = "\n".join(ex_texts)

    prompt = ASSEMBLY_PROMPT.format(
        goal=goal, experience=experience, location=location,
        split_name=split_name, schedule=schedule_text, exercises=ex_text,
    )

    print(f"  发送 LLM: {len(prompt)} 字符, {len(prompt)//4} tokens")

    llm = get_llm()
    t0 = time.time()
    resp = llm.invoke([{"role": "user", "content": prompt}], timeout=60)
    t = time.time() - t0
    print(f"  LLM 耗时: {t:.1f}s")

    text = resp.content if not isinstance(resp, str) else resp

    # 解析 JSON
    try:
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            text = text[start:end].strip()
        plan = json.loads(text)

        # 校验
        days = plan.get("weekly_plans", [{}])[0].get("days", [])
        print(f"  输出: {len(days)} 天, 每天动作数:")
        for day in days:
            main_count = len(day.get("main", []))
            warmup_count = len(day.get("warmup", []))
            cooldown_count = len(day.get("cooldown", []))
            wger_ids = [ex.get("wger_id") for ex in day.get("main", [])]
            missing_id = [i for i in wger_ids if not i]
            print(f"    {day.get('day')}: main={main_count}, warmup={warmup_count}, cooldown={cooldown_count}")
            if missing_id:
                print(f"    ⚠️ 有 {len(missing_id)} 个动作缺少 wger_id")

        return plan
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  ❌ 解析失败: {e}")
        print(text[:500])
        return None


if __name__ == "__main__":
    # 模拟 ExerciseAgent 输出的精选动作
    mock_exercises = [
        {"wger_id": 1694, "name": "Flat Machine Press", "muscle_id": 4},
        {"wger_id": 926, "name": "Machine chest fly", "muscle_id": 4},
        {"wger_id": 1922, "name": "Seated Cable chest fly", "muscle_id": 4},
        {"wger_id": 1744, "name": "Machine Side Lateral Raises", "muscle_id": 2},
        {"wger_id": 957, "name": "Quadriped Arm and Leg Raise", "muscle_id": 2},
        {"wger_id": 1378, "name": "Cable Lateral Raises", "muscle_id": 2},
        {"wger_id": 660, "name": "Triceps Extensions on Cable", "muscle_id": 5},
        {"wger_id": 1509, "name": "Cable Tricep Kickback", "muscle_id": 5},
        {"wger_id": 245, "name": "Skullcrusher Dumbbells", "muscle_id": 5},
        {"wger_id": 355, "name": "Lat Pull Down", "muscle_id": 12},
        {"wger_id": 1283, "name": "Incline Chest-Supported Dumbbell Row", "muscle_id": 12},
        {"wger_id": 83, "name": "Bent Over Rowing", "muscle_id": 12},
        {"wger_id": 94, "name": "Biceps Curls With SZ-bar", "muscle_id": 1},
        {"wger_id": 1424, "name": "Biceps Curl Machine", "muscle_id": 1},
        {"wger_id": 1931, "name": "Dumbbell Curl", "muscle_id": 1},
        {"wger_id": 203, "name": "Dumbbell Goblet Squat", "muscle_id": 10},
        {"wger_id": 614, "name": "Squat Jumps", "muscle_id": 10},
        {"wger_id": 374, "name": "Leg Presses", "muscle_id": 10},
        {"wger_id": 1395, "name": "Crossbody Leg Swings", "muscle_id": 11},
        {"wger_id": 1437, "name": "Pin Squat", "muscle_id": 11},
        {"wger_id": 616, "name": "Squat Thrust", "muscle_id": 8},
        {"wger_id": 397, "name": "Low Box Squat", "muscle_id": 8},
        {"wger_id": 591, "name": "Sit-ups", "muscle_id": 6},
        {"wger_id": 377, "name": "Leg Raises, Lying", "muscle_id": 6},
        {"wger_id": 1409, "name": "Dragon-flag", "muscle_id": 6},
    ]

    ppl_schedule = [
        {"day": "第1天", "focus": "胸部 + 肩部 + 三头"},
        {"day": "第2天", "focus": "背部 + 二头"},
        {"day": "第3天", "focus": "腿部 + 臀部 + 腹部"},
    ]

    plan = test_plan_assembly(
        goal="增肌", experience="新手", location="健身房",
        split_name="PPL", schedule=ppl_schedule,
        exercises=mock_exercises,
    )

    if plan:
        print(f"\n{'='*60}")
        print(f"  组装成功!")
        print(json.dumps(plan, ensure_ascii=False, indent=2)[:2000])
```

- [ ] **Step 2: 运行组装测试**

```bash
cd C:\Users\18194\Desktop\fitness-plan\backend
PYTHONIOENCODING=utf-8 python ..\test\06_plan_agent_assembly.py
```

预期：
- LLM 耗时 < 15s（因为输入就 25 个动作，prompt 很小）
- 输出 3 天完整计划
- 每天 5-6 个主训练动作
- 所有动作保留 wger_id
- 动作名称为中文

---

### Task 4: 运行完整端到端回归测试

**文件:**
- Run: `test/04_ppl_pipeline_e2e.py`

- [ ] **Step 1: 运行完整端到端测试**

```bash
cd C:\Users\18194\Desktop\fitness-plan\backend
PYTHONIOENCODING=utf-8 python ..\test\04_ppl_pipeline_e2e.py
```

- [ ] **Step 2: 验证输出**

检查输出是否满足:
- ✅ 搜索 < 5s
- ✅ 过滤后每个肌群有 5+ 个动作
- ✅ LLM 精选 27 个动作（9肌群×3）
- ✅ 没有不合理的动作（如 Dragon-flag 给新手）
- ✅ PlanAgent 组装成功，输出完整周计划
- ✅ 总耗时 < 60s

- [ ] **Step 3: 运行两次验证稳定性**

第二次运行应输出**类似但不等同**的结果（LLM有随机性），但精选的动作质量应一致。

---

## 执行顺序

```
Task 1: 重构 04_ppl_pipeline_e2e.py（增加LLM精选）
    ↓
Task 2: 创建 05_exercise_agent_precise.py（独立测试精选）
    ↓
Task 3: 创建 06_plan_agent_assembly.py（独立测试组装）
    ↓
Task 4: 回归测试 04_ppl_pipeline_e2e.py
```

## 验收标准

| 标准 | 要求 |
|------|------|
| wger API 联通 | exerciseinfo 正常返回，无需 API Key |
| 搜索速度 | 9肌群并发 < 5s |
| 过滤正确性 | 新手不会出现杠铃/哑铃动作 |
| 精选质量 | 无 Dragon-flag/Muscle up 类动作给新手 |
| 组装完整性 | 输出 3 天，每天 5-6 动作，含 wger_id |
| 整体耗时 | < 60s（对比原来 25-45s） |
