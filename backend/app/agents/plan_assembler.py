"""PlanAssembler — 训练计划组装器（AI 热身 + AI 拉伸）

职责：按科学标准编排当天完整训练
流程：AI 热身（针对主项） → 无氧主项 → 有氧收尾(可选) → AI 拉伸（针对主项）

2026-07-04 重构：
  - _select_warmup → generate_warmup（LLM 根据主项生成针对性热身）
  - _select_stretches → generate_stretch（LLM 根据主项生成针对性拉伸）
  - 保留硬编码模板作为 LLM 失败时的兜底
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger("plan_assembler")

# ── Session 级缓存：相同主项组合 → 热身+拉伸结果 ──────────
_warmup_stretch_cache = {}


# ── 英文动作名 → 中文翻译（常见 wger 动作）─────────────────
# 兜底用：当 LLM 没有翻译或排序失败时，保证至少常见动作有中文名
_EXERCISE_EN_TO_CN = {
    # 腹部/核心
    "Leg Raises, Lying": "仰卧举腿",
    "Sit Up Elbow Thrust": "卷腹肘击",
    "Crunches": "卷腹",
    "Reverse Crunches": "反向卷腹",
    "Russian Twist": "俄罗斯转体",
    "Plank": "平板支撑",
    "Side Plank": "侧平板支撑",
    "Bicycle Crunch": "空中蹬车卷腹",
    "V-Up": "V字卷腹",
    "Leg Raise": "举腿",
    "Hanging Leg Raise": "悬垂举腿",
    "Ab Crunch Machine": "卷腹机",
    "Cable Crunch": "绳索卷腹",
    "Ab Roller": "健腹轮",
    "Jackknife": "折叠卷腹",
    "Heel Touch": "脚后跟触底卷腹",
    "Dead Bug": "死虫式",
    "Bird Dog": "鸟狗式",
    # 胸部
    "Bench Press": "卧推",
    "Dumbbell Bench Press": "哑铃卧推",
    "Incline Bench Press": "上斜卧推",
    "Decline Bench Press": "下斜卧推",
    "Chest Fly": "飞鸟",
    "Cable Crossover": "绳索夹胸",
    "Push Up": "俯卧撑",
    "Push-ups": "俯卧撑",
    "Dumbbell Fly": "哑铃飞鸟",
    "Machine Press": "器械推胸",
    # 背部
    "Lat Pull Down": "高位下拉",
    "Pull Up": "引体向上",
    "Pull-ups": "引体向上",
    "Barbell Row": "杠铃划船",
    "Dumbbell Row": "哑铃划船",
    "Seated Row": "坐姿划船",
    "Deadlift": "硬拉",
    "Romanian Deadlift": "罗马尼亚硬拉",
    "T-Bar Row": "T杠划船",
    "Face Pull": "面拉",
    # 肩部
    "Shoulder Press": "肩推",
    "Overhead Press": "过头推举",
    "Lateral Raise": "侧平举",
    "Front Raise": "前平举",
    "Rear Delt Fly": "反向飞鸟",
    "Arnold Press": "阿诺德推举",
    "Upright Row": "直立划船",
    # 肱二头肌
    "Bicep Curl": "二头弯举",
    "Hammer Curl": "锤式弯举",
    "Concentration Curl": "集中弯举",
    "Preacher Curl": "牧师凳弯举",
    "Cable Curl": "绳索弯举",
    # 肱三头肌
    "Tricep Pushdown": "三头下压",
    "Overhead Tricep Extension": "颈后臂屈伸",
    "Skull Crusher": "仰卧臂屈伸",
    "Dips": "双杠臂屈伸",
    "Close Grip Bench Press": "窄距卧推",
    # 腿部
    "Squat": "深蹲",
    "Goblet Squat": "高脚杯深蹲",
    "Front Squat": "前蹲",
    "Leg Press": "腿举",
    "Lunges": "箭步蹲",
    "Walking Lunge": "行走箭步蹲",
    "Leg Extension": "腿屈伸",
    "Leg Curl": "腿弯举",
    "Calf Raise": "提踵",
    "Hip Thrust": "臀推",
    "Glute Bridge": "臀桥",
    "Step Up": "上台阶",
    # 其他
    "Kettlebell Swing": "壶铃摇摆",
    "Burpee": "波比跳",
    "Mountain Climber": "登山者",
    "Jumping Jack": "开合跳",
    "Farmer's Walk": "农夫行走",
}


def _ensure_chinese_name(name: str) -> str:
    """确保动作名为中文。如果检测到英文名，尝试翻译。

    检测规则：
      - 如果名字里包含中文字符 → 已经是中文，直接返回
      - 如果名字全是英文/数字 → 从字典翻译，找不到则保留原名
    """
    if not name:
        return name
    # 如果有中文字符，认为是中文名
    if re.search(r'[一-鿿]', name):
        return name
    # 尝试字典翻译
    if name in _EXERCISE_EN_TO_CN:
        return _EXERCISE_EN_TO_CN[name]
    # 尝试大小写不敏感匹配
    name_lower = name.lower().strip()
    for en, cn in _EXERCISE_EN_TO_CN.items():
        if en.lower() == name_lower:
            return cn
    # 兜底：保留原名（但标记为英文）
    return name


# ── 动态热身模板（兜底/备用） ──────────────────────────────

DYNAMIC_WARMUP = [
    {"name": "开合跳", "sets": 2, "reps": 15, "instruction": "手脚同步打开再收回"},
    {"name": "肩部环绕", "sets": 1, "reps": 10, "instruction": "向前向后各绕 10 圈"},
    {"name": "手臂前后画圈", "sets": 1, "reps": 10, "instruction": "由小到大画圈"},
    {"name": "高抬腿", "sets": 2, "reps": 15, "instruction": "膝盖抬高至腰部，保持核心收紧"},
    {"name": "弓步转体", "sets": 1, "reps": 8,  "instruction": "前腿弓步同时上半身向同侧转"},
    {"name": "侧弓步", "sets": 1, "reps": 8,  "instruction": "向侧方迈步屈膝，另一腿伸直"},
    {"name": "抱膝提踵", "sets": 1, "reps": 8,  "instruction": "单腿抱膝上提，同时另一脚踮起"},
    {"name": "后踢腿", "sets": 2, "reps": 15, "instruction": "脚跟尽量踢到臀部"},
    {"name": "手腕脚踝活动", "sets": 1, "reps": 10, "instruction": "转动手腕和脚踝各 10 圈"},
    {"name": "胯下击掌", "sets": 2, "reps": 15, "instruction": "抬腿至胯高，双手在大腿下击掌"},
]

WARMUP_SELECTION = {
    "推": {"优先": ["肩部环绕", "手臂前后画圈", "手腕脚踝活动"],
           "全身": ["开合跳", "高抬腿", "胯下击掌", "后踢腿"],
           "动态": ["弓步转体", "侧弓步", "抱膝提踵"]},
    "拉": {"优先": ["肩部环绕", "手臂前后画圈", "抱膝提踵"],
           "全身": ["开合跳", "高抬腿", "胯下击掌", "后踢腿"],
           "动态": ["弓步转体", "侧弓步", "手腕脚踝活动"]},
    "腿": {"优先": ["高抬腿", "后踢腿", "弓步转体", "侧弓步"],
           "全身": ["开合跳", "胯下击掌", "肩部环绕"],
           "动态": ["抱膝提踵", "手臂前后画圈", "手腕脚踝活动"]},
    "全身": {"优先": ["开合跳", "高抬腿", "肩部环绕", "弓步转体"],
             "全身": ["后踢腿", "胯下击掌"],
             "动态": ["侧弓步", "手臂前后画圈", "抱膝提踵", "手腕脚踝活动"]},
    "default": {"优先": ["开合跳", "肩部环绕", "高抬腿", "弓步转体"],
                "全身": ["胯下击掌", "后踢腿"],
                "动态": ["侧弓步", "手臂前后画圈", "抱膝提踵", "手腕脚踝活动"]},
}

# ── 有氧收尾（同旧版） ─────────────────────────────────────

CARDIO_FINISHER = {
    "减脂": {"name": "慢跑", "suggestion": "跑步机慢跑 20 分钟，心率保持在最大心率的 60-70%",
             "duration_minutes": 20, "intensity": "中等"},
    "增肌": {"name": "爬坡快走", "suggestion": "跑步机坡度 8-12，速度 4-5 km/h，10 分钟",
             "duration_minutes": 10, "intensity": "低"},
    "塑形": {"name": "椭圆机", "suggestion": "椭圆机 15 分钟，阻力适中，保持稳定节奏",
             "duration_minutes": 15, "intensity": "中等"},
    "保持健康": {"name": "慢走", "suggestion": "慢走 10 分钟，自然放松",
                 "duration_minutes": 10, "intensity": "低"},
}
CARDIO_OPTIONAL_GOALS = ["增肌", "保持健康"]

# ── 静态拉伸映射（兜底/备用） ───────────────────────────────

MUSCLE_STRETCHES = {4: [{"name": "门框胸大肌拉伸", "instruction": "单手扶门框，身体向前倾，保持 20 秒，换边"},
                         {"name": "背后双手合十", "instruction": "背后双手合十，指尖向上，保持 15 秒"}],
                    2: [{"name": "交叉臂肩部拉伸", "instruction": "手臂水平交叉胸前，另一手辅助固定，保持 20 秒，换边"},
                        {"name": "肩部后侧拉伸", "instruction": "手臂横过胸前，对侧手辅助向身体拉，保持 15 秒"}],
                    5: [{"name": "三头肌颈后拉伸", "instruction": "举手过顶屈肘，另一手辅助轻拉肘部，保持 20 秒，换边"}],
                    12: [{"name": "婴儿式背部拉伸", "instruction": "跪姿，双手前伸，臀部坐脚跟，背部放松，保持 20 秒"},
                         {"name": "猫牛式脊柱活动", "instruction": "四足跪姿，交替弓背和塌腰，各做 5 次"}],
                    1: [{"name": "二头肌拉伸", "instruction": "手臂侧平举，掌心向上，另一手轻压手指向后，保持 15 秒，换边"}],
                    10: [{"name": "站立股四头肌拉伸", "instruction": "单腿站立，同侧手握脚踝拉向臀部，保持 20 秒，换边"}],
                    11: [{"name": "坐姿腘绳肌拉伸", "instruction": "坐姿，一腿伸直，另一腿弯曲，身体向前倾，保持 20 秒，换边"}],
                    8: [{"name": "坐姿臀部拉伸（4字拉伸）", "instruction": "坐姿，一脚踝放另一膝上，身体前倾，保持 20 秒，换边"},
                        {"name": "仰卧臀部拉伸", "instruction": "仰卧，屈膝，一脚踝放另一膝上，双手抱腿向胸口拉，保持 20 秒"}],
                    6: [{"name": "眼镜蛇式腹部拉伸", "instruction": "俯卧，双手撑地推起上半身，腹部贴地，保持 15 秒"}],
                    13: [{"name": "小腿推墙拉伸", "instruction": "弓步靠墙，后腿伸直脚跟踩地，保持 20 秒，换边"}]}

FOCUS_TO_MUSCLE_IDS = {
    "胸部": 4, "肩部": 2, "肱三头肌": 5,
    "背部": 12, "肱二头肌": 1,
    "股四头肌": 10, "腘绳肌": 11, "臀部": 8,
    "腹部": 6, "小腿": 13,
}

ALL_STRETCHES_CACHE = {}
MUSCLE_NAME_TO_STRETCHES = {}


def _build_stretch_cache():
    """构建中文肌群名 → 拉伸动作的缓存。"""
    if ALL_STRETCHES_CACHE:
        return
    for mid, stretches in MUSCLE_STRETCHES.items():
        for name in [k for k, v in FOCUS_TO_MUSCLE_IDS.items() if v == mid]:
            MUSCLE_NAME_TO_STRETCHES[name] = stretches
        ALL_STRETCHES_CACHE[mid] = stretches


# ═══════════════════════════════════════════════════════════════
#  AI 热身 + AI 拉伸（新增）
# ═══════════════════════════════════════════════════════════════

WARMUP_STRETCH_PROMPT = """你是一个专业健身教练。根据今天的主项动作，生成针对性的热身和拉伸。

训练日: {day_label} — {focus}
目标: {goal}
经验: {experience}
地点: {location}

今天的主项动作:
{main_exercises_text}

要求：
1. **热身（4-5 个动作）**：
   - 必须与主项肌群和动作模式相关
   - 包含 1-2 个动态拉伸 + 2-3 个专项热身组
   - 每个动作含 "name", "sets", "reps", "instruction"

2. **拉伸（3-4 个动作）**：
   - 只拉伸主项涉及的肌群
   - 静态保持 15-30 秒
   - 每个动作含 "name", "instruction"

只输出 JSON（不要 markdown 代码块）：
{{
  "warmup": [
    {{"name": "动作名", "sets": 2, "reps": 10, "instruction": "执行说明"}}
  ],
  "stretch": [
    {{"name": "拉伸名", "instruction": "保持 20 秒"}}
  ]
}}"""


def _build_warmup_stretch_prompt(
    main_exercises: List[dict],
    day_spec: dict,
    goal: str,
    experience: str,
    location: str,
) -> str:
    """构建热身+拉伸 LLM prompt。"""
    ex_text = "\n".join(
        f"  [{ex.get('wger_id', '?')}] {ex.get('name', '')} — {ex.get('target_muscle', '未知肌群')}"
        for ex in main_exercises
    )
    day_label = day_spec.get("day_label", "")
    focus = day_spec.get("focus", "")
    return WARMUP_STRETCH_PROMPT.format(
        day_label=day_label,
        focus=focus,
        goal=goal,
        experience=experience,
        location=location,
        main_exercises_text=ex_text,
    )


def _cache_key(main_exercises: List[dict]) -> str:
    """为热身+拉伸结果构建缓存 key（基于主项动作名+顺序）。"""
    names = [ex.get("name", "") for ex in main_exercises]
    return "|".join(names)


def generate_warmup_stretch(
    main_exercises: List[dict],
    day_spec: dict,
    goal: str,
    experience: str,
    location: str,
) -> tuple:
    """LLM 根据当天主项动作生成热身和拉伸。

    一次 LLM 调用返回两个结果（共享 prompt，减少调用次数）。

    Returns:
        tuple: (warmup_list, stretch_list)
            warmup_list: [{"name", "sets", "reps", "instruction"}, ...]
            stretch_list: [{"name", "instruction"}, ...]
    """
    # 检查缓存
    ckey = _cache_key(main_exercises)
    if ckey in _warmup_stretch_cache:
        logger.info(f"[PlanAssembler] 命中热身+拉伸缓存: {ckey[:40]}...")
        return _warmup_stretch_cache[ckey]

    try:
        from app.services.llm_service import get_fast_llm

        prompt = _build_warmup_stretch_prompt(
            main_exercises, day_spec, goal, experience, location,
        )
        llm = get_fast_llm()
        collected = []
        for chunk in llm.stream_invoke(
            [{"role": "user", "content": prompt + "\n\n只输出纯 JSON，不要 markdown 代码块。"}],
            max_tokens=4096,
        ):
            collected.append(chunk)
        text = "".join(collected).strip()
        text = text.replace("```json", "").replace("```", "").strip()

        result = json.loads(text)
        warmup = result.get("warmup", [])
        stretch = result.get("stretch", [])

        # 校验格式
        if not isinstance(warmup, list):
            warmup = []
        if not isinstance(stretch, list):
            stretch = []

        # 写入缓存
        _warmup_stretch_cache[ckey] = (warmup, stretch)

        return warmup, stretch

    except Exception as e:
        logger.warning(f"[PlanAssembler] AI 热身+拉伸生成失败: {e}，使用兜底模板")
        return None, None


def _select_warmup(day_label: str) -> list:
    """（兜底）根据训练日类型选择动态热身动作。"""
    plan = WARMUP_SELECTION.get(day_label, WARMUP_SELECTION["default"])
    warmup_list = []
    seen = set()
    for category in ["优先", "全身", "动态"]:
        for name in plan.get(category, []):
            if name not in seen:
                seen.add(name)
                ex = next((e for e in DYNAMIC_WARMUP if e["name"] == name), None)
                if ex:
                    warmup_list.append(dict(ex))
    return warmup_list


def _select_stretches(focus: str) -> list:
    """（兜底）根据训练日 focus 选择对应的静态拉伸。"""
    _build_stretch_cache()
    stretches = []
    seen = set()
    parts = [p.strip() for p in focus.replace("＋", "+").split("+")]
    for part in parts:
        stretch_list = MUSCLE_NAME_TO_STRETCHES.get(part, [])
        for s in stretch_list:
            if s["name"] not in seen:
                seen.add(s["name"])
                stretches.append(dict(s))
    return stretches


def _select_cardio(goal: str) -> Optional[dict]:
    """根据目标选择有氧收尾。"""
    finisher = CARDIO_FINISHER.get(goal)
    if not finisher:
        return None
    return dict(finisher)


def _build_llm_prompt(selected_exercises: List[dict], day_spec: dict,
                       goal: str, experience: str, location: str,
                       user_desc: str = "") -> str:
    """构建 LLM 编排主项动作的 prompt。"""
    ex_text = "\n".join(
        f"  [{ex['wger_id']}] {ex['name']} — {ex.get('target_muscle', '未知肌群')}"
        for ex in selected_exercises
    )
    rep_ranges = {
        "新手": "每组 10-12 次，3 组，选中等重量",
        "中级": "每组 8-12 次，3-4 组，选 70-80% 1RM",
        "高级": "每组 6-12 次，3-5 组，选 75-85% 1RM",
    }
    rep_guide = rep_ranges.get(experience, rep_ranges["中级"])

    personalized = ""
    if user_desc:
        personalized = f"\n用户信息: {user_desc}\n请根据用户的体能和身体条件选择合适的组次数和重量。"

    prompt = f"""你是一个专业健身教练。请将以下动作按训练顺序排列。

训练日: {day_spec.get('day', '')} — {day_spec.get('focus', '')}
目标: {goal}
经验: {experience}
地点: {location}{personalized}

可用动作:
{ex_text}

排序规则:
1. 复合动作（多关节）优先，孤立动作在后
2. 推类动作在前，拉类动作在后（如需）
3. {rep_guide}
4. 组之间休息 60-90 秒

要求:
- 返回 JSON: {{"main": [{{"name": "中文动作名", "sort_order": 1, "sets": 3, "reps": 10, "rest_seconds": 60, "wger_id": 123}}]}}
- **动作名必须用中文**：把英文名翻译成中文，如 "Flat Machine Press" → "平板器械推胸"，"Lat Pull Down" → "高位下拉"
- sort_order 从 1 开始递增
- 每个动作用一次，不要重复
- 只输出纯 JSON，不要 markdown 代码块"""
    return prompt


def assemble_one_day(
    day_spec: dict,
    selected_exercises: List[dict],
    goal: str,
    experience: str,
    location: str,
    user_desc: str = "",
    use_ai_warmup_stretch: bool = True,
) -> Optional[dict]:
    """按科学标准组装当天完整训练计划。

    返回结构:
    {day, focus,
     warmup: [{name, sets, reps, instruction}],
     main: [{name, target_muscle, sets, reps, rest_seconds, wger_id}],
     cardio: {name, suggestion, duration_minutes, intensity} | None,
     stretch: [{name, instruction}]}

    Args:
        day_spec: 当天规格，含 day, focus, day_label, muscle_ids
        selected_exercises: LLM 精选出的动作列表
        goal: 用户目标
        experience: 经验水平
        location: 训练地点
        user_desc: 用户个人信息描述
        use_ai_warmup_stretch: 是否使用 AI 生成热身+拉伸（默认 True）
    """
    day_label = day_spec.get("day_label", "")
    focus = day_spec.get("focus", "")

    # 1. 无氧主项（LLM 排顺序）—— 先执行，因为 AI 热身需要主项数据
    main = []
    if selected_exercises:
        if len(selected_exercises) >= 3:
            from app.services.llm_service import get_fast_llm
            prompt = _build_llm_prompt(selected_exercises, day_spec, goal, experience, location, user_desc)
            llm = get_fast_llm()
            try:
                collected = []
                for chunk in llm.stream_invoke(
                    [{"role": "user", "content": prompt + "\n\n只输出纯 JSON，不要 markdown 代码块。"}],
                    max_tokens=8192,
                ):
                    collected.append(chunk)
                text = "".join(collected).strip()
                text = text.replace("```json", "").replace("```", "").strip()
                result = json.loads(text)
                main = result.get("main", [])
                _img_map = {ex.get("wger_id"): ex.get("image_url", "") for ex in selected_exercises if ex.get("wger_id")}
                _muscle_map = {ex.get("wger_id"): ex.get("muscle_id") for ex in selected_exercises if ex.get("wger_id")}
                _tm_map = {ex.get("wger_id"): ex.get("target_muscle", "") for ex in selected_exercises if ex.get("wger_id")}
                for item in main:
                    wid = item.get("wger_id")
                    if wid:
                        if wid in _img_map:
                            item["image_url"] = _img_map[wid]
                        if wid in _muscle_map:
                            item["muscle_id"] = _muscle_map[wid]
                        if wid in _tm_map:
                            item["target_muscle"] = _tm_map[wid]
                    # 确保名字是中文（LLM 可能没翻译）
                    item["name"] = _ensure_chinese_name(item.get("name", ""))
            except Exception as e:
                print(f"  ⚠️ LLM 排序失败: {e}，使用原始顺序")
                main = [{"name": _ensure_chinese_name(ex["name"]), "target_muscle": ex.get("target_muscle", ""),
                         "sets": 3, "reps": 12, "rest_seconds": 60, "wger_id": ex.get("wger_id"),
                         "image_url": ex.get("image_url", "")}
                        for ex in selected_exercises]
        else:
            main = [{"name": _ensure_chinese_name(ex["name"]), "target_muscle": ex.get("target_muscle", ""),
                     "sets": 3, "reps": 12, "rest_seconds": 60, "wger_id": ex.get("wger_id"),
                     "image_url": ex.get("image_url", "")}
                    for ex in selected_exercises]

    # 2. AI 热身（针对主项）或兜底模板
    if use_ai_warmup_stretch and main:
        ai_warmup, ai_stretch = generate_warmup_stretch(
            main, day_spec, goal, experience, location,
        )
        if ai_warmup is not None and ai_stretch is not None:
            warmup = ai_warmup
            stretch = ai_stretch
        else:
            # AI 生成失败，使用兜底
            warmup = _select_warmup(day_label)
            stretch = _select_stretches(focus)
    else:
        warmup = _select_warmup(day_label)
        stretch = _select_stretches(focus)

    # 3. 有氧收尾（根据目标）
    cardio = _select_cardio(goal)

    return {
        "day": day_spec.get("day", ""),
        "focus": focus,
        "warmup": warmup,
        "main": main,
        "cardio": cardio,
        "stretch": stretch,
    }
