"""Step 2: 搜索 PPL 各肌群的真实动作"""

import httpx
import json
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')

WGER_BASE = "https://wger.de/api/v2"

# PPL 涉及的全部肌群 ID
PPL_MUSCLES = {
    4:  "胸大肌 (Chest)",
    2:  "前三角肌 (Shoulders)",
    5:  "肱三头肌 (Triceps)",
    12: "背阔肌 (Lats)",
    1:  "肱二头肌 (Biceps)",
    10: "股四头肌 (Quads)",
    11: "股二头肌 (Hamstrings)",
    8:  "臀大肌 (Glutes)",
    6:  "腹直肌 (Abs)",
}

def search_muscle(muscle_id: int, name: str, limit: int = 5):
    """搜索单个肌群的动作"""
    params = {
        "format": "json",
        "language": 2,
        "muscles": muscle_id,
        "limit": limit,
    }
    t0 = time.time()
    resp = httpx.get(f"{WGER_BASE}/exerciseinfo/", params=params, timeout=30)
    t = time.time() - t0
    data = resp.json()
    exercises = data.get("results", [])

    print(f"\n  [{name}] (ID={muscle_id}) — 共 {data['count']} 个动作, 耗时 {t:.1f}s")

    for ex in exercises[:limit]:
        # 提取英文名
        ex_name = ""
        for tr in ex.get("translations", []):
            if tr.get("language") == 2:
                ex_name = tr.get("name", "")
                break
        if not ex_name and ex.get("translations"):
            ex_name = ex["translations"][0].get("name", "")

        # 提取图片
        img = ""
        for i in ex.get("images", []):
            if isinstance(i, dict) and i.get("image"):
                img = i["image"]
                break

        print(f"    ├ ID {ex.get('id'):4d}  {ex_name[:40]:40s}")
        if img:
            print(f"    └ [img] {img[:70]}")
    return exercises


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  PPL 训练 — 各肌群动作搜索")
    print(f"{'='*60}")

    all_results = {}

    # 串行搜索每个肌群（方便看每个肌群有什么动作）
    for mid, mname in PPL_MUSCLES.items():
        all_results[mid] = search_muscle(mid, mname)

    print(f"\n{'='*60}")
    print(f"  共搜索 {len(PPL_MUSCLES)} 个肌群")
    print(f"  总动作数: {sum(len(v) for v in all_results.values())}")
    print(f"{'='*60}")

# PPL 
# 端到端测试（输入 PPL → 并发搜 wger → 按新手过滤 → LLM 组装出周计划）？