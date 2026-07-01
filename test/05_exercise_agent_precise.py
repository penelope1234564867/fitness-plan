"""Step 5: ExerciseAgent 精选逻辑专项测试

验证：接收训练分化 → 搜索wger → 过滤 → LLM精选 → 输出稳定动作列表
"""

import sys, os, json, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
from app.services.llm_service import get_fast_llm  # 精选用轻量模型

import httpx
WGER_BASE = "https://wger.de/api/v2"
httpx_client = httpx.Client(timeout=30)

# ── wger 全部 15 个肌群 ──
MUSCLES = {
    "胸大肌":         4,
    "三角肌(肩)":     2,
    "肱三头肌":       5,
    "背阔肌":        12,
    "肱二头肌":       1,
    "股四头肌(腿前)": 10,
    "腘绳肌(腿后)":   11,
    "臀大肌":         8,
    "腹直肌":         6,
    "前锯肌":         3,
    "斜方肌":         9,
    "肱肌":          13,
    "腹外斜肌":      14,
    "腓肠肌(小腿)":   7,
    "比目鱼肌":      15,
}

# PPL / 上下肢 / 全身 三种分化预设
SPLITS = {
    "ppl": {
        "name": "PPL（推/拉/腿）",
        "days": 3,
        "per_group": 3,
        "schedule": [
            {"day": "第1天", "focus": "胸部 + 肩部 + 三头",           "muscles": [4, 2, 5, 3]},
            {"day": "第2天", "focus": "背部 + 二头 + 斜方肌",        "muscles": [12, 1, 13, 9]},
            {"day": "第3天", "focus": "腿 + 臀 + 腹 + 小腿",         "muscles": [10, 11, 8, 6, 14, 7, 15]},
        ]
    },
}

# 用户等级器材过滤
# 注：wger 没有独立的"固定器械"分类，所以不硬过滤，
#     靠 LLM prompt 按经验水平做智能选择
EQUIPMENT_FILTER = {
    "新手": [],   # 全部通过，LLM 会优先选固定器械和自重
    "中级": [],   # 全部通过
    "高级": [],   # 全部通过
}

def search_all_muscles(muscle_ids):
    """Map-Reduce 搜索所有肌群，返回分组 dict（每次随机取 15 个）"""
    from concurrent.futures import ThreadPoolExecutor
    def search_one(mid):
        # 多取一些，再随机挑 15 个，避免每次结果完全一样
        resp = httpx_client.get(
            f"{WGER_BASE}/exerciseinfo/",
            params={"format": "json", "language": 2, "muscles": mid, "limit": 30, "status": 2}
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
        random.shuffle(results)
        return results[:15]

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


# 按经验水平的选动作指引
EXPERIENCE_GUIDE = {
    "新手": "优先选择固定器械和自重动作，可以少量使用哑铃。避免杠铃、爆发力动作（如抓举、引体向上）、复杂自由重量动作和高难度复合动作。",
    "中级": "可以使用哑铃、杠铃等自由重量，适当加入中等难度复合动作（如卧推、深蹲）。可以包含少量爆发力动作。",
    "高级": "不限制器械类型，可以包含爆发力动作（如抓举、高翻）、高难度复合动作和高级训练技巧。",
}


def _invoke_json_llm(llm, prompt, max_tokens=4096, verbose=False):
    """调用 LLM，流式输出，最后返回完整纯 JSON 文本"""
    json_prompt = prompt + "\n\n只输出纯 JSON，不要 markdown 代码块，不要多余文字。"
    if verbose:
        print(f"\n  ── LLM 输入 ──")
        print(f"  prompt 长度: {len(prompt)} 字符, 约 {len(prompt)//4} tokens")
        print(f"  ────────────")
        print(f"\n  ── LLM 流式输出 ──")

    collected = []
    for chunk in llm.stream_invoke(
        [{"role": "user", "content": json_prompt}],
        max_tokens=max_tokens,
    ):
        if verbose:
            print(chunk, end="", flush=True)
        collected.append(chunk)

    text = "".join(collected)

    if verbose:
        print(f"\n  ── 流式输出结束 (共 {len(text)} 字符) ──")
        if not text:
            print("  ⚠️ 返回为空，可能是模型/API 问题")

    # 清理首尾空白和多余逗号
    text = text.strip().rstrip(",")
    return text


SELECT_PROMPT = """你是一个专业健身教练。从每个肌群选出最适合的 {per_group} 个动作。

用户: 目标={goal}, 经验={experience}, 地点={location}
训练分化: {split_name}

可用动作:
{grouped_data}

选动作规则:
{experience_guide}

要求:
1. 每个肌群选 {per_group} 个，不多选
2. 同天训练的不同肌群间动作要有区分度（不同器材/模式）
3. 只输出 JSON: {{"selected": [{{"wger_id": 123, "muscle_id": 4}}, ...]}}
   不要 markdown 代码块，不要多余文字
"""


def llm_select(grouped, goal, experience, location, split_name, per_group=3, verbose=False):
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
        experience_guide=EXPERIENCE_GUIDE.get(experience, EXPERIENCE_GUIDE["中级"]),
    )

    if verbose:
        print(f"\n  ── LLM 输入 ──")
        print(f"  prompt 长度: {len(prompt)} 字符, 约 {len(prompt)//4} tokens")
        print(f"  共 {sum(len(v) for v in grouped.values())} 个候选动作")
        print(f"  ────────────")

    llm = get_fast_llm()
    text = _invoke_json_llm(llm, prompt, verbose=verbose)

    try:
        result = json.loads(text)
        raw_selected = result.get("selected", [])
        selected_ids = {(item["wger_id"], item["muscle_id"]) for item in raw_selected}

        if verbose:
            print(f"\n  ── 解析结果 ──")
            print(f"  LLM 返回了 {len(raw_selected)} 条")
            print(f"  去重后 (wger_id, muscle_id) 集合:")
            for sid in sorted(selected_ids):
                print(f"    ({sid[0]}, muscle={sid[1]})")
            print(f"  ──────────────")

    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠️ LLM返回解析失败: {e}")
        print(f"  ⚠️ 原始响应前 500 字: {text[:500]}")
        print(f"  ⚠️ 使用代码回退")
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

    if verbose:
        print(f"\n  ── 最终匹配结果 ──")
        print(f"  从 grouped 中匹配到 {len(selected)} 个动作")
        for ex in selected[:5]:
            equip_str = "自重" if not ex.get("equipment") else str(ex["equipment"])
            print(f"    [{ex['wger_id']}] {ex['name'][:40]} | muscle={ex['muscle_id']} | 器材: {equip_str}")
        if len(selected) > 5:
            print(f"    ... 共 {len(selected)} 个")
        print(f"  ─────────────────")

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
    selected = llm_select(filtered, goal, experience, location, split["name"], per, verbose=True)
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
    test_split("ppl", "增肌", "新手", "健身房")
