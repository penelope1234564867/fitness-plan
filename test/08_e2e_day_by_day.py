"""Step 8: 按天生成 PPL 计划 - 并行测试

三天独立并行跑，各自：搜索 → 精选 → 组装
"""
import sys, os, json, time, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

# 复用 05 和 06 的代码
import importlib.util
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

mod5 = _load("ex", os.path.join(os.path.dirname(__file__), "05_exercise_agent_precise.py"))
mod6 = _load("pl", os.path.join(os.path.dirname(__file__), "06_plan_agent_assembly.py"))

# ── PPL 三天定义（直接复用 05 的 SPLITS）──
PPL_DAYS = mod5.SPLITS["ppl"]["schedule"]  # 第1/2/3天

# ── 单天组装 prompt（比 06 的周计划简单得多）──
DAY_ASSEMBLY_PROMPT = """你是一个专业健身教练。用以下动作组装当天训练计划。

用户: 目标={goal}, 经验={experience}, 地点={location}, 分化={split_name}
当天: {day_focus}

可用动作:
{exercises}

要求:
1. 5-6 个主训练动作，复合→孤立顺序
2. 组数次数按 {experience} 标准
3. 配 2 个热身 + 1 个冷身
4. 所有动作从可用动作中选取，保留 wger_id
5. 动作名用中文
6. 只输出纯 JSON，不要 markdown

格式:
{{"day": "{day_label}", "focus": "{focus}",
  "warmup": [{{"name": "动作", "sets": 2, "reps": 15}}],
  "main": [{{"name": "动作", "target_muscle": "肌群", "sets": 3, "reps": 12, "rest_seconds": 60, "wger_id": 123, "exercise_type": "compound"}}],
  "cooldown": [{{"name": "拉伸", "sets": 2, "reps": 30}}]
}}
"""


def assemble_one_day(day, exercises, goal, experience, location, split_name):
    """组装单天计划"""
    ex_texts = [f"  [{ex['wger_id']}] {ex['name']}" for ex in exercises]
    ex_text = "\n".join(ex_texts)

    prompt = DAY_ASSEMBLY_PROMPT.format(
        goal=goal, experience=experience, location=location,
        split_name=split_name,
        day_focus=f"  {day['day']}: {day['focus']}",
        day_label=day['day'], focus=day['focus'],
        exercises=ex_text,
    )

    llm = mod5.get_fast_llm()
    text = mod5._invoke_json_llm(llm, prompt, max_tokens=8192)
    return json.loads(text)


def generate_one_day(day, goal, experience, location):
    """生成单天计划：搜索 → 过滤 → 精选 → 组装"""
    print(f"\n  ▶ 开始 {day['day']}: {day['focus']}")

    # 1. 只搜当天的肌群
    t0 = time.time()
    grouped = mod5.search_all_muscles(day["muscles"])
    total = sum(len(v) for v in grouped.values())
    print(f"    搜索: {total} 个动作, {time.time()-t0:.1f}s")

    # 2. 过滤（现为空的，全部通过）
    filtered = mod5.filter_by_equipment(grouped, experience)
    after = sum(len(v) for v in filtered.values())
    print(f"    过滤: {total} → {after}")

    # 3. LLM 精选（每肌群 3 个）
    per = mod5.SPLITS["ppl"]["per_group"]  # 3
    t0 = time.time()
    selected = mod5.llm_select(filtered, goal, experience, location,
                               mod5.SPLITS["ppl"]["name"], per)
    print(f"    精选: {len(selected)} 个动作, {time.time()-t0:.1f}s")

    if not selected:
        print(f"    ⚠️ 没有选到动作")
        return None

    # 4. LLM 组装当天计划
    t0 = time.time()
    day_plan = assemble_one_day(day, selected, goal, experience, location, "PPL")
    print(f"    组装完成: {len(day_plan.get('main',[]))} 个主动作, {time.time()-t0:.1f}s")

    return day_plan


async def run_e2e(goal, experience, location):
    """并发跑三天"""
    print(f"\n{'='*60}")
    print(f"  PPL 按天生成 - 并行测试")
    print(f"  用户: {goal} / {experience} / {location}")
    print(f"{'='*60}")

    t_total = time.time()

    # 并发跑三天
    tasks = [
        asyncio.to_thread(generate_one_day, day, goal, experience, location)
        for day in PPL_DAYS
    ]
    results = await asyncio.gather(*tasks)

    # 汇总
    print(f"\n{'='*60}")
    print(f"  结果汇总")
    print(f"{'='*60}")
    all_days = []
    for i, (day, result) in enumerate(zip(PPL_DAYS, results)):
        if result:
            all_days.append(result)
            main_count = len(result.get("main", []))
            print(f"  ✅ {day['day']} ({day['focus']}): {main_count} 个主动作")
        else:
            print(f"  ❌ {day['day']} ({day['focus']}): 失败")

    total_time = time.time() - t_total
    print(f"\n  总耗时: {total_time:.1f}s")
    print(f"{'='*60}")

    return all_days


if __name__ == "__main__":
    result = asyncio.run(run_e2e(
        goal="增肌",
        experience="新手",
        location="健身房",
    ))

    if result:
        print(f"\n{'='*60}")
        print(f"  完整计划")
        print(f"{'='*60}")
        print(json.dumps({"weekly_plans": [{"week": 1, "days": result}]},
                         ensure_ascii=False, indent=2))
