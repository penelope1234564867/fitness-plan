"""Step 7: PPL 端到端 Pipeline（ExerciseAgent → PlanAgent）

串联流程:
  05_exercise_agent_precise.py 精选动作
  → 06_plan_agent_assembly.py 组装周计划
"""

import sys, os, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

# ── 导入 05 和 06（用 importlib，文件名以数字开头不能直接 import）──
import importlib.util

def _import_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

mod_exercise = _import_from_path("exercise_agent",
    os.path.join(os.path.dirname(__file__), "05_exercise_agent_precise.py"))
mod_plan = _import_from_path("plan_agent",
    os.path.join(os.path.dirname(__file__), "06_plan_agent_assembly.py"))

SPLITS = mod_exercise.SPLITS
test_split = mod_exercise.test_split
test_plan_assembly = mod_plan.test_plan_assembly


def run_ppl_pipeline(goal, experience, location):
    """PPL 端到端：ExerciseAgent → PlanAgent"""
    print(f"\n{'='*60}")
    print(f"  PPL 端到端 Pipeline")
    print(f"  用户: {goal} / {experience} / {location} / 一周3练")
    print(f"{'='*60}")

    t_total = time.time()

    # ── Step 1: ExerciseAgent 精选动作 ──
    print(f"\n{'─'*40}")
    print(f"  [Step 1] ExerciseAgent 精选动作")
    print(f"{'─'*40}")
    t0 = time.time()
    selected = test_split("ppl", goal=goal, experience=experience, location=location)
    t1 = time.time() - t0
    print(f"  ✅ 精选完成: {len(selected)} 个动作, 耗时 {t1:.1f}s")

    if not selected:
        print("  ❌ 没有选到任何动作，终止")
        return None

    # ── Step 2: PlanAgent 组装周计划 ──
    print(f"\n{'─'*40}")
    print(f"  [Step 2] PlanAgent 组装周计划")
    print(f"{'─'*40}")

    ppl_schedule = [
        {"day": "第1天", "focus": "胸部 + 肩部 + 三头"},
        {"day": "第2天", "focus": "背部 + 二头"},
        {"day": "第3天", "focus": "腿部 + 臀部 + 腹部"},
    ]

    t0 = time.time()
    plan = test_plan_assembly(
        goal=goal, experience=experience, location=location,
        split_name="PPL（推/拉/腿）",
        schedule=ppl_schedule,
        exercises=selected,
    )
    t2 = time.time() - t0
    total_time = time.time() - t_total

    if plan:
        print(f"\n{'='*60}")
        print(f"  🎉 Pipeline 运行成功!")
        print(f"  精选: {len(selected)} 个动作 ({t1:.1f}s)")
        print(f"  组装: {t2:.1f}s")
        print(f"  总计: {total_time:.1f}s")
        print(f"{'='*60}")
    else:
        print(f"\n{'='*60}")
        print(f"  ❌ Pipeline 失败: PlanAgent 组装出错")
        print(f"{'='*60}")

    return plan


if __name__ == "__main__":
    # ════════════════════════════════════════
    #   ← 在这里修改用户信息
    # ════════════════════════════════════════
    plan = run_ppl_pipeline(
        goal="增肌",
        experience="新手",
        location="健身房",
    )

    if plan:
        # 打印完整计划
        print(f"\n{'='*60}")
        print(f"  [完整周计划]")
        print(f"{'='*60}")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
