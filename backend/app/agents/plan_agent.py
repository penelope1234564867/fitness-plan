"""Plan 组装器 — 按科学标准编排当天完整训练

流程：动态热身 → 无氧主项 → 有氧收尾(可选) → 对应肌群静态拉伸

依据：ACSM 指南 + 2024 系统性综述
- 热身：动态拉伸优先（提升表现、降低受伤风险），禁止静态拉伸
- 无氧：复合动作 → 孤立动作
- 有氧：根据目标决定是否包含
- 拉伸：只拉伸当天训练的肌群，静态保持 15-30 秒
"""

import json
from typing import List, Dict, Any, Optional


# ── 动态热身模板（通用，不分目标，5-8 分钟） ────────────────

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

# 按训练日侧重选择不同的热身组合
WARMUP_SELECTION = {
    "推": {
        "优先": ["肩部环绕", "手臂前后画圈", "手腕脚踝活动"],
        "全身": ["开合跳", "高抬腿", "胯下击掌", "后踢腿"],
        "动态": ["弓步转体", "侧弓步", "抱膝提踵"],
    },
    "拉": {
        "优先": ["肩部环绕", "手臂前后画圈", "抱膝提踵"],
        "全身": ["开合跳", "高抬腿", "胯下击掌", "后踢腿"],
        "动态": ["弓步转体", "侧弓步", "手腕脚踝活动"],
    },
    "腿": {
        "优先": ["高抬腿", "后踢腿", "弓步转体", "侧弓步"],
        "全身": ["开合跳", "胯下击掌", "肩部环绕"],
        "动态": ["抱膝提踵", "手臂前后画圈", "手腕脚踝活动"],
    },
    "全身": {
        "优先": ["开合跳", "高抬腿", "肩部环绕", "弓步转体"],
        "全身": ["后踢腿", "胯下击掌"],
        "动态": ["侧弓步", "手臂前后画圈", "抱膝提踵", "手腕脚踝活动"],
    },
    "default": {
        "优先": ["开合跳", "肩部环绕", "高抬腿", "弓步转体"],
        "全身": ["胯下击掌", "后踢腿"],
        "动态": ["侧弓步", "手臂前后画圈", "抱膝提踵", "手腕脚踝活动"],
    },
}


# ── 有氧收尾（根据目标） ────────────────────────────────

CARDIO_FINISHER = {
    "减脂": {
        "name": "慢跑",
        "suggestion": "跑步机慢跑 20 分钟，心率保持在最大心率的 60-70%",
        "duration_minutes": 20,
        "intensity": "中等",
    },
    "增肌": {
        "name": "爬坡快走",
        "suggestion": "跑步机坡度 8-12，速度 4-5 km/h，10 分钟",
        "duration_minutes": 10,
        "intensity": "低",
    },
    "塑形": {
        "name": "椭圆机",
        "suggestion": "椭圆机 15 分钟，阻力适中，保持稳定节奏",
        "duration_minutes": 15,
        "intensity": "中等",
    },
    "保持健康": {
        "name": "慢走",
        "suggestion": "慢走 10 分钟，自然放松",
        "duration_minutes": 10,
        "intensity": "低",
    },
}

# 如果不需要有氧（增肌场景可选），设为 None
CARDIO_OPTIONAL_GOALS = ["增肌", "保持健康"]


# ── 静态拉伸映射（肌群 → 拉伸动作） ────────────────────────

# wger 数字肌肉 ID → 拉伸动作
MUSCLE_STRETCHES = {
    4: [   # 胸部
        {"name": "门框胸大肌拉伸", "instruction": "单手扶门框，身体向前倾，保持 20 秒，换边"},
        {"name": "背后双手合十", "instruction": "背后双手合十，指尖向上，保持 15 秒"},
    ],
    2: [   # 肩部（三角肌）
        {"name": "交叉臂肩部拉伸", "instruction": "手臂水平交叉胸前，另一手辅助固定，保持 20 秒，换边"},
        {"name": "肩部后侧拉伸", "instruction": "手臂横过胸前，对侧手辅助向身体拉，保持 15 秒"},
    ],
    5: [   # 肱三头肌
        {"name": "三头肌颈后拉伸", "instruction": "举手过顶屈肘，另一手辅助轻拉肘部，保持 20 秒，换边"},
    ],
    12: [  # 背部
        {"name": "婴儿式背部拉伸", "instruction": "跪姿，双手前伸，臀部坐脚跟，背部放松，保持 20 秒"},
        {"name": "猫牛式脊柱活动", "instruction": "四足跪姿，交替弓背和塌腰，各做 5 次"},
    ],
    1: [   # 肱二头肌
        {"name": "二头肌拉伸", "instruction": "手臂侧平举，掌心向上，另一手轻压手指向后，保持 15 秒，换边"},
    ],
    10: [  # 股四头肌
        {"name": "站立股四头肌拉伸", "instruction": "单腿站立，同侧手握脚踝拉向臀部，保持 20 秒，换边"},
    ],
    11: [  # 腘绳肌
        {"name": "坐姿腘绳肌拉伸", "instruction": "坐姿，一腿伸直，另一腿弯曲，身体向前倾，保持 20 秒，换边"},
    ],
    8: [   # 臀部/臀大肌
        {"name": "坐姿臀部拉伸（4字拉伸）", "instruction": "坐姿，一脚踝放另一膝上，身体前倾，保持 20 秒，换边"},
        {"name": "仰卧臀部拉伸", "instruction": "仰卧，屈膝，一脚踝放另一膝上，双手抱腿向胸口拉，保持 20 秒"},
    ],
    6: [   # 腹部
        {"name": "眼镜蛇式腹部拉伸", "instruction": "俯卧，双手撑地推起上半身，腹部贴地，保持 15 秒"},
    ],
    13: [  # 小腿
        {"name": "小腿推墙拉伸", "instruction": "弓步靠墙，后腿伸直脚跟踩地，保持 20 秒，换边"},
    ],
}

# 中文肌群名 → wger ID（和 generator.py 保持一致）
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


def _select_warmup(day_label: str) -> list:
    """根据训练日类型选择动态热身动作。"""
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
    """根据训练日 focus 选择对应的静态拉伸。"""
    _build_stretch_cache()
    stretches = []
    seen = set()
    # focus 格式如 "胸部 + 肩部 + 三头"
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
    # 可选目标允许跳过
    return dict(finisher)


def _build_llm_prompt(selected_exercises: List[dict], day_spec: dict,
                       goal: str, experience: str, location: str,
                       user_desc: str = "") -> str:
    """构建 LLM 编排主项动作的 prompt。"""
    ex_text = "\n".join(
        f"  [{ex['wger_id']}] {ex['name']} — {ex.get('target_muscle', '未知肌群')}"
        for ex in selected_exercises
    )
    # 经验水平对应的组次数标准
    rep_ranges = {
        "新手": "每组 10-12 次，3 组，选中等重量",
        "中级": "每组 8-12 次，3-4 组，选 70-80% 1RM",
        "高级": "每组 6-12 次，3-5 组，选 75-85% 1RM",
    }
    rep_guide = rep_ranges.get(experience, rep_ranges["中级"])

    # 添加用户个性化信息
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
        user_desc: 用户个人信息描述（身高/体重/年龄/性别）
    """
    day_label = day_spec.get("day_label", "")
    focus = day_spec.get("focus", "")

    # 1. 动态热身（确定性模板，不调 LLM）
    warmup = _select_warmup(day_label)

    # 2. 无氧主项（LLM 排顺序）
    main = []
    if selected_exercises:
        # 只有 3 个以上动作才调 LLM，否则直接用
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
                # 清理可能的 markdown 代码块标记
                text = text.replace("```json", "").replace("```", "").strip()
                result = json.loads(text)
                main = result.get("main", [])
            except Exception as e:
                print(f"  ⚠️ LLM 排序失败: {e}，使用原始顺序")
                main = [{"name": ex["name"], "target_muscle": ex.get("target_muscle", ""),
                         "sets": 3, "reps": 12, "rest_seconds": 60, "wger_id": ex.get("wger_id")}
                        for ex in selected_exercises]
        else:
            main = [{"name": ex["name"], "target_muscle": ex.get("target_muscle", ""),
                     "sets": 3, "reps": 12, "rest_seconds": 60, "wger_id": ex.get("wger_id")}
                    for ex in selected_exercises]

    # 3. 有氧收尾（根据目标）
    cardio = _select_cardio(goal)

    # 4. 静态拉伸（根据训练肌群）
    stretch = _select_stretches(focus)

    return {
        "day": day_spec.get("day", ""),
        "focus": focus,
        "warmup": warmup,
        "main": main,
        "cardio": cardio,
        "stretch": stretch,
    }
