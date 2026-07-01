"""Exercise 精选器 — 搜索 + 过滤 + LLM 选择最优动作

从 test/05_exercise_agent_precise.py 搬运，去掉 ReAct。
职责：按肌群搜索 wger → 器材过滤 → LLM 精选最优动作
"""

import json
import random
import httpx
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from app.services.llm_service import get_fast_llm

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

# 用户等级器材过滤（wger 没有独立"固定器械"分类，靠 LLM prompt 做智能选择）
EQUIPMENT_FILTER = {
    "新手": [],
    "中级": [],
    "高级": [],
}

# 按经验水平的选动作指引
EXPERIENCE_GUIDE = {
    "新手": "优先选择固定器械和自重动作，可以少量使用哑铃。避免杠铃、爆发力动作（如抓举、引体向上）、复杂自由重量动作和高难度复合动作。",
    "中级": "可以使用哑铃、杠铃等自由重量，适当加入中等难度复合动作（如卧推、深蹲）。可以包含少量爆发力动作。",
    "高级": "不限制器械类型，可以包含爆发力动作（如抓举、高翻）、高难度复合动作和高级训练技巧。",
}

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


def search_all_muscles(muscle_ids: List[int]) -> Dict[int, List[dict]]:
    """Map-Reduce 搜索所有肌群，返回 {muscle_id: [{wger_id, name, muscle_id, equipment}, ...]}"""
    def search_one(mid):
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


def filter_by_equipment(grouped: Dict[int, List[dict]], experience: str) -> Dict[int, List[dict]]:
    """按经验水平过滤器材。"""
    allowed = EQUIPMENT_FILTER.get(experience, [])
    if not allowed:
        return grouped
    result = {}
    for mid, exs in grouped.items():
        filtered = [ex for ex in exs if not ex.get("equipment") or all(e in allowed for e in ex["equipment"])]
        result[mid] = filtered
    return result


def _invoke_json_llm(llm, prompt: str, max_tokens: int = 4096, verbose: bool = False) -> str:
    """调用 LLM，流式收集，最后返回完整纯 JSON 文本。"""
    json_prompt = prompt + "\n\n只输出纯 JSON，不要 markdown 代码块，不要多余文字。"
    collected = []
    for chunk in llm.stream_invoke(
        [{"role": "user", "content": json_prompt}],
        max_tokens=max_tokens,
    ):
        if verbose:
            print(chunk, end="", flush=True)
        collected.append(chunk)
    text = "".join(collected)
    text = text.strip().rstrip(",")
\\
    
    
    if verbose:
        print(f"\n  ── 流式结束 (共 {len(text)} 字符) ──")

    return text


def llm_select(
    grouped: Dict[int, List[dict]],
    goal: str,
    experience: str,
    location: str,
    split_name: str = "",
    per_group: int = 3,
    verbose: bool = False,
    user_desc: str = "",
) -> List[dict]:
    """LLM 从候选动作中精选最优，返回 [{wger_id, name, muscle_id, equipment}, ...]"""
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

    # 如果有用户个人信息，追加到 prompt 中
    if user_desc:
        prompt += f"\n\n用户信息: {user_desc}\n请根据用户的体能水平选择合适的动作。体重大的人优先选择关节友好的动作（如器械代替自由重量），年龄大的用户注意避免高危动作。"

    if verbose:
        print(f"\n  ── LLM 精选输入: {len(prompt)} 字符, {sum(len(v) for v in grouped.values())} 个候选 ──")

    llm = get_fast_llm()
    text = _invoke_json_llm(llm, prompt, verbose=verbose)

    try:
        result = json.loads(text)
        raw_selected = result.get("selected", [])
        selected_ids = {(item["wger_id"], item["muscle_id"]) for item in raw_selected}
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠️ LLM 返回解析失败: {e}")
        # 降级：每个肌群取前 per_group 个
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
        print(f"  ── 精选结果: {len(selected)} 个动作 ──")

    return selected


def run_pipeline(
    muscle_ids: List[int],
    goal: str,
    experience: str,
    location: str,
    split_name: str = "",
    per_group: int = 3,
    verbose: bool = False,
) -> List[dict]:
    """快捷调用：搜索 → 过滤 → LLM 精选，返回精选动作列表。"""
    grouped = search_all_muscles(muscle_ids)
    filtered = filter_by_equipment(grouped, experience)
    selected = llm_select(filtered, goal, experience, location, split_name, per_group, verbose)
    return selected
