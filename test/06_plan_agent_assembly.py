"""Step 6: PlanAgent 按天组装（三天并行，各出各的）"""

import sys, os, json, time, asyncio, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

# ── 复用 05 的搜索/过滤/精选 ──
import importlib.util
mod5_path = os.path.join(os.path.dirname(__file__), "05_exercise_agent_precise.py")
spec = importlib.util.spec_from_file_location("ex05", mod5_path)
mod5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod5)

PPL_DAYS = mod5.SPLITS["ppl"]["schedule"]


# ── 单天组装 prompt ──
DAY_PROMPT = """你是一个专业健身教练。用以下动作组装当天的训练计划。

用户: 目标={goal}, 经验={experience}, 地点={location}
当天: {day_focus}

可用动作:
{exercises}

要求:
1. 5-6 个主训练动作，复合→孤立顺序
2. 组数次数按 {experience} 标准
3. 配 2 个热身 + 1 个冷身
4. 所有动作从可用动作中选取，保留 wger_id
5. 动作名用中文
6. 只输出纯 JSON，不要 markdown 代码块

格式:
{{"day": "{day_label}", "focus": "{focus}",
  "warmup": [{{"name": "动作", "sets": 2, "reps": 15}}],
  "main": [{{"name": "动作", "target_muscle": "肌群", "sets": 3, "reps": 12, "rest_seconds": 60, "wger_id": 123, "exercise_type": "compound"}}],
  "cooldown": [{{"name": "拉伸", "sets": 2, "reps": 30}}]
}}
"""


def generate_one_day(day, goal, experience, location):
    """生成单天：搜索 → 过滤 → 精选 → 组装，完成后直接打印"""
    label = f"{day['day']}({day['focus']})"
    t0 = time.time()

    # 1. 搜索（只搜当天的肌群）
    grouped = mod5.search_all_muscles(day["muscles"])
    filtered = mod5.filter_by_equipment(grouped, experience)
    total = sum(len(v) for v in filtered.values())

    # 2. LLM 精选
    per = mod5.SPLITS["ppl"]["per_group"]
    selected = mod5.llm_select(filtered, goal, experience, location,
                               mod5.SPLITS["ppl"]["name"], per)

    if not selected:
        print(f"\n  ❌ {label} 无可用动作")
        return None

    # 3. 组装当天
    ex_text = "\n".join(f"  [{ex['wger_id']}] {ex['name']}" for ex in selected)
    prompt = DAY_PROMPT.format(
        goal=goal, experience=experience, location=location,
        day_focus=f"  {day['day']}: {day['focus']}",
        day_label=day['day'], focus=day['focus'],
        exercises=ex_text,
    )

    llm = mod5.get_fast_llm()
    text = mod5._invoke_json_llm(llm, prompt, max_tokens=8192)
    plan = json.loads(text)

    elapsed = time.time() - t0
    main_count = len(plan.get("main", []))

    # ✅ 完成就打印，不等其他天
    lock = threading.Lock()
    with lock:
        print(f"\n{'='*60}")
        print(f"  ✅ {label} 完成 ({elapsed:.1f}s) — {main_count} 个主动作")
        print(f"{'='*60}")
        print(json.dumps(plan, ensure_ascii=False, indent=2))

    return plan


async def run_parallel(goal, experience, location):
    """三天并发跑，谁先跑完谁先输出"""
    print(f"\n  用户: {goal} / {experience} / {location} | PPL 三天并行")
    print(f"  {'='*50}")

    tasks = [
        asyncio.to_thread(generate_one_day, day, goal, experience, location)
        for day in PPL_DAYS
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(run_parallel(
        goal="增肌",
        experience="新手",
        location="健身房",
    ))
