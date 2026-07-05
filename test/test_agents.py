"""Agent 系统集成测试

测试计划文档 11-plan.md 中的完整 Agent 链路。

测试内容:
  1. CoachAgent.analyze_user()      — 用户画像分析
  2. ProgrammerAgent.select_exercises() — 动作搜索 + 精选（调 wger）
  3. PlanAssembler.assemble_one_day() — 组装每日训练
  4. CoachAgent.add_reasoning()     — 教练备注
  5. AnalystAgent.analyze_week_checkins() — 打卡分析

用法:
  cd backend
  python ../test/test_agents.py
  或运行单个测试:
  python ../test/test_agents.py 3  (只跑第 3 项)
"""

import sys
import os
import json
import time

# 把 backend 加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ["PYTHONIOENCODING"] = "utf-8"


def print_header(title: str):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(ok: bool, msg: str = ""):
    prefix = "✅" if ok else "❌"
    print(f"  {prefix} {msg}")


# ═══════════════════════════════════════════════════════════════
#  测试 1: CoachAgent 用户画像分析
# ═══════════════════════════════════════════════════════════════

def test_coach_analyze_user():
    """CoachAgent 分析用户信息生成画像总结。"""
    from app.agents.coach_agent import CoachAgent

    # 模拟 InitPlanRequest
    class MockRequest:
        goal = "增肌"
        experience_level = "新手"
        workout_location = "居家"
        days_per_week = 3
        height = 175
        weight = 70
        age = 25
        gender = "male"
        city = "上海"

    coach = CoachAgent()
    t0 = time.time()
    profile = coach.analyze_user(MockRequest())
    elapsed = time.time() - t0

    print_header("测试 1: CoachAgent.analyze_user()")
    print(f"  耗时: {elapsed:.1f}s")
    print(f"  输出:")
    print(json.dumps(profile, ensure_ascii=False, indent=4))

    assert isinstance(profile, dict), "返回值必须是 dict"
    assert "profile_summary" in profile, "必须包含 profile_summary"
    assert "training_phase" in profile, "必须包含 training_phase"
    assert "focus_points" in profile, "必须包含 focus_points"
    assert "precautions" in profile, "必须包含 precautions"
    print_result(True, f"画像: {profile['profile_summary']}")
    return profile


# ═══════════════════════════════════════════════════════════════
#  测试 2: ProgrammerAgent 选动作
# ═══════════════════════════════════════════════════════════════

def test_programmer_select():
    """ProgrammerAgent 从 wger 搜索并精选动作。"""
    from app.agents.programmer_agent import ProgrammerAgent
    from app.agents.coach_agent import CoachAgent

    # 先用 CoachAgent 获取画像
    class MockRequest:
        goal = "增肌"
        experience_level = "新手"
        workout_location = "居家"
        days_per_week = 3
        height = 175
        weight = 70
        age = 25
        gender = "male"
        city = "上海"

    coach = CoachAgent()
    profile = coach.analyze_user(MockRequest())

    prog = ProgrammerAgent()

    # 推日: 胸部(4) + 肩部(2) + 肱三头肌(5)
    muscle_ids = [4, 2, 5]

    print_header("测试 2: ProgrammerAgent.select_exercises()")
    print(f"  搜索肌群: {muscle_ids} (胸+肩+三头)")
    print(f"  用户画像: {profile.get('profile_summary', '')}")
    print(f"  目标: 增肌, 经验: 新手, 地点: 居家")

    t0 = time.time()
    selected = prog.select_exercises(
        muscle_ids=muscle_ids,
        profile=profile,
        goal="增肌",
        experience="新手",
        location="居家",
        per_group=2,
    )
    elapsed = time.time() - t0

    print(f"  耗时: {elapsed:.1f}s")
    print(f"  选中 {len(selected)} 个动作:")
    for i, ex in enumerate(selected):
        has_img = "📷" if ex.get("image_url") else "  "
        print(f"    {i+1}. [{ex['wger_id']}] {ex['name']} {has_img}")
        print(f"       肌群ID={ex.get('muscle_id')}, 器材={ex.get('equipment', [])}")

    assert isinstance(selected, list), "返回值必须是 list"
    assert len(selected) > 0, "至少选出一个动作"
    assert "wger_id" in selected[0], "每个动作必须有 wger_id"
    print_result(True, f"成功选出 {len(selected)} 个动作")
    return selected, profile


# ═══════════════════════════════════════════════════════════════
#  测试 3: PlanAssembler 组装
# ═══════════════════════════════════════════════════════════════

def test_plan_assembler(selected=None, profile=None):
    """PlanAssembler 组装一天完整训练计划。"""
    from app.agents.plan_assembler import assemble_one_day
    from app.agents.coach_agent import CoachAgent
    from app.agents.programmer_agent import ProgrammerAgent

    # 如果没有传入参数，先跑测试 2
    if selected is None or profile is None:
        sel, prof = test_programmer_select()
        selected = sel
        profile = prof

    day_spec = {
        "day": "第1天 · 推",
        "focus": "胸部 + 肩部 + 三头",
        "day_label": "推",
        "muscle_ids": [4, 2, 5],
    }

    print_header("测试 3: PlanAssembler.assemble_one_day()")
    print(f"  训练日: {day_spec['day']}")
    print(f"  输入: {len(selected)} 个精选动作")

    t0 = time.time()
    day_plan = assemble_one_day(day_spec, selected, "增肌", "新手", "居家")
    elapsed = time.time() - t0

    print(f"  耗时: {elapsed:.1f}s")
    print(f"  热身: {len(day_plan['warmup'])} 个动作")
    for ex in day_plan["warmup"]:
        print(f"    - {ex['name']} {ex.get('sets',1)}x{ex.get('reps',0)}")

    print(f"  主项: {len(day_plan['main'])} 个动作")
    for ex in day_plan["main"]:
        print(f"    [{ex.get('wger_id','?')}] {ex['name']} — {ex.get('sets',3)}x{ex.get('reps',10)}")

    print(f"  有氧: {day_plan.get('cardio', {}).get('name', '无')}")
    print(f"  拉伸: {len(day_plan['stretch'])} 个动作")
    for ex in day_plan["stretch"]:
        print(f"    - {ex['name']}")

    assert isinstance(day_plan, dict), "返回值必须是 dict"
    assert "warmup" in day_plan, "必须包含 warmup"
    assert "main" in day_plan, "必须包含 main"
    assert len(day_plan["main"]) > 0, "必须有主项动作"
    print_result(True, f"组装完成：{len(day_plan['main'])} 主项 + {len(day_plan['warmup'])} 热身")
    return day_plan, profile


# ═══════════════════════════════════════════════════════════════
#  测试 4: CoachAgent 教练备注
# ═══════════════════════════════════════════════════════════════

def test_coach_reasoning(day_plan=None, profile=None):
    """CoachAgent 为动作添加教练备注。"""
    from app.agents.coach_agent import CoachAgent

    if day_plan is None or profile is None:
        dp, prof = test_plan_assembler()
        day_plan = dp
        profile = prof

    coach = CoachAgent()

    print_header("测试 4: CoachAgent.add_reasoning()")
    print(f"  为 {len(day_plan['main'])} 个主项生成教练备注...")

    t0 = time.time()
    result = coach.add_reasoning(day_plan, profile, "增肌")
    elapsed = time.time() - t0

    print(f"  耗时: {elapsed:.1f}s")
    for ex in result["main"]:
        coach_says = ex.get("coach_says", "（无备注）")
        print(f"    [{ex['name']}] 教练说: {coach_says}")

    print_result(True, "备注生成完成")
    return result


# ═══════════════════════════════════════════════════════════════
#  测试 5: AnalystAgent 打卡分析
# ═══════════════════════════════════════════════════════════════

def test_analyst():
    """AnalystAgent 分析打卡数据。"""
    from app.agents.analyst_agent import AnalystAgent
    from app.database import SessionLocal, init_db
    from app.models import orm_models

    init_db()
    db = SessionLocal()

    analyst = AnalystAgent()
    profile = {"profile_summary": "新手减脂"}

    # 找最新一周的数据
    week = db.query(orm_models.Week).order_by(
        orm_models.Week.id.desc()
    ).first()

    if not week:
        print_header("测试 5: AnalystAgent (跳过 - 无训练数据)")
        print_result(False, "数据库中没有 Week 数据，请先 init-plan")
        db.close()
        return

    days = db.query(orm_models.Day).filter(
        orm_models.Day.week_id == week.id
    ).order_by(orm_models.Day.day_order).all()

    for d in days:
        d.slots = db.query(orm_models.ExerciseSlot).filter(
            orm_models.ExerciseSlot.day_id == d.id
        ).all()

    print_header("测试 5: AnalystAgent.analyze_week_checkins()")
    print(f"  分析周: week_id={week.id}, week_number={week.week_number}")
    print(f"  训练日: {len(days)} 天, 总 slots: {sum(len(d.slots or []) for d in days)} 个")

    t0 = time.time()
    analysis = analyst.analyze_week_checkins(days, profile)
    elapsed = time.time() - t0

    print(f"  耗时: {elapsed:.1f}s")
    print(f"  整体评价: {analysis.get('overall_assessment', '')}")
    print(f"  调整建议: {analysis.get('adjustment_suggestion', '')}")
    print(f"  关键发现:")
    for f in analysis.get("key_findings", []):
        print(f"    - {f}")

    adjustments = analyst.determine_adjustments(analysis)
    print(f"  调整类型: {adjustments.get('type', '')}")
    print(f"  需要减载: {adjustments.get('deload_needed', False)}")

    anomalies = analyst.detect_anomalies(days)
    print(f"  异常检测: {len(anomalies)} 项")
    for a in anomalies:
        print(f"    [{a.get('severity','')}] {a.get('description','')}")

    db.close()
    print_result(True, "分析完成")
    return analysis


# ═══════════════════════════════════════════════════════════════
#  完整链路测试
# ═══════════════════════════════════════════════════════════════

def test_full_pipeline():
    """完整链路：CoachAgent → ProgrammerAgent → PlanAssembler → CoachAgent。"""
    from app.agents.coach_agent import CoachAgent
    from app.agents.programmer_agent import ProgrammerAgent
    from app.agents.plan_assembler import assemble_one_day

    print_header("🧪 完整链路测试: CoachAgent → ProgrammerAgent → PlanAssembler → CoachAgent")
    overall_start = time.time()

    # Step 1: CoachAgent 画像
    print("\n  Step 1/4: CoachAgent 分析用户画像...")
    class MockRequest:
        goal = "增肌"
        experience_level = "新手"
        workout_location = "居家"
        days_per_week = 3
        height = 175
        weight = 70
        age = 25
        gender = "male"
        city = "上海"

    coach = CoachAgent()
    t0 = time.time()
    profile = coach.analyze_user(MockRequest())
    print(f"    ✅ 画像完成 ({time.time()-t0:.1f}s): {profile['profile_summary']}")
    for p in profile.get("precautions", []):
        print(f"    ⚠️  注意事项: {p}")

    # Step 2: ProgrammerAgent 选动作（推日）
    print("\n  Step 2/4: ProgrammerAgent 搜索 + 精选动作...")
    prog = ProgrammerAgent()
    t0 = time.time()
    selected = prog.select_exercises(
        muscle_ids=[4, 2, 5],
        profile=profile,
        goal="增肌",
        experience="新手",
        location="居家",
        per_group=3,
    )
    print(f"    ✅ 精选完成 ({time.time()-t0:.1f}s): {len(selected)} 个动作")
    for ex in selected:
        print(f"      [{ex['wger_id']}] {ex['name']}")

    # 如果选太少，加假数据测试后续步骤
    if len(selected) < 2:
        print("    ⚠️  wger 返回动作太少，补充测试数据...")
        selected.append({
            "wger_id": 999,
            "name": "俯卧撑",
            "muscle_id": 4,
            "equipment": [],
            "image_url": "",
        })

    # Step 3: PlanAssembler 组装
    print("\n  Step 3/4: PlanAssembler 组装每日训练...")
    day_spec = {
        "day": "第1天 · 推",
        "focus": "胸部 + 肩部 + 三头",
        "day_label": "推",
        "muscle_ids": [4, 2, 5],
    }
    t0 = time.time()
    day_plan = assemble_one_day(day_spec, selected, "增肌", "新手", "居家")
    print(f"    ✅ 组装完成 ({time.time()-t0:.1f}s)")
    print(f"      热身: {len(day_plan['warmup'])} 个")
    print(f"      主项: {len(day_plan['main'])} 个")
    print(f"      有氧: {day_plan.get('cardio',{}).get('name','无')}")
    print(f"      拉伸: {len(day_plan['stretch'])} 个")

    # Step 4: CoachAgent 教练备注
    print("\n  Step 4/4: CoachAgent 添加教练备注...")
    t0 = time.time()
    day_plan = coach.add_reasoning(day_plan, profile, "增肌")
    print(f"    ✅ 备注完成 ({time.time()-t0:.1f}s)")
    for ex in day_plan["main"]:
        cs = ex.get("coach_says", "（无）")
        print(f"      [{ex['name']}] 💬 {cs}")

    total = time.time() - overall_start
    print(f"\n  {'='*50}")
    print(f"  🎉 完整链路测试通过! 总耗时: {total:.1f}s")
    print(f"  {'='*50}")

    return True


# ═══════════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 解析命令行参数，支持指定运行哪个测试
    test_map = {
        "1": ("CoachAgent 画像分析", test_coach_analyze_user),
        "2": ("ProgrammerAgent 选动作", test_programmer_select),
        "3": ("PlanAssembler 组装", test_plan_assembler),
        "4": ("CoachAgent 教练备注", test_coach_reasoning),
        "5": ("AnalystAgent 打卡分析", test_analyst),
        "all": ("完整链路", test_full_pipeline),
    }

    args = sys.argv[1:]
    if not args or "all" in args:
        target = "all"
    else:
        target = args[0]

    if target == "all":
        test_full_pipeline()
    elif target in test_map:
        name, fn = test_map[target]
        print(f"\n   ▶ 运行测试 {target}: {name}")
        fn()
    else:
        print(f"用法: python test/test_agents.py [{'|'.join(test_map.keys())}]")
        print()
        print("  不传参数 = 跑完整链路 (all)")
        print("  python test/test_agents.py 3  = 只跑第 3 项 (PlanAssembler)")
        sys.exit(1)
