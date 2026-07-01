"""Step 3: 测试按器材过滤能否区分新手/中级/高级动作"""

import httpx
import json
import sys

WGER_BASE = "https://wger.de/api/v2"

# wger 器材 ID → 中文名
EQUIPMENT_NAMES = {
    1: "杠铃", 3: "哑铃", 4: "瑜伽垫", 5: "瑞士球",
    6: "引体向上杆", 7: "自重", 8: "卧推凳", 9: "上斜凳",
    10: "壶铃", 11: "EZ杠",
}

# 按经验划分的器材白名单
EXPERIENCE_FILTER = {
    "新手": [7, 8, 4, 5, 6],    # 自重/卧推凳/瑜伽垫/瑞士球/引体杆
    "中级": [1, 3, 7, 8, 6],    # 加杠铃/哑铃
    "高级": [],                   # 不限器材
}

def list_equipment():
    """先列出 wger 所有器材"""
    resp = httpx.get(f"{WGER_BASE}/equipment/", params={"format": "json"}, timeout=30)
    data = resp.json()
    print(f"\nwger 器材列表:")
    for e in data.get("results", []):
        print(f"  ID {e['id']:2d}: {e['name']}")


def search_and_check(muscle_id: int, muscle_name: str):
    """搜索一个肌群的动作，查看每个动作的器材要求"""
    params = {"format": "json", "language": 2, "muscles": muscle_id, "limit": 30}
    resp = httpx.get(f"{WGER_BASE}/exerciseinfo/", params=params, timeout=30)
    data = resp.json()

    print(f"\n{'='*60}")
    print(f"  {muscle_name} (ID={muscle_id}) -- wger 共 {data['count']} 个")
    print(f"{'='*60}")

    results = []
    for ex in data.get("results", []):
        # 取名称
        name = ""
        for tr in ex.get("translations", []):
            if tr.get("language") == 2:
                name = tr.get("name", "")
                break
        if not name and ex.get("translations"):
            name = ex["translations"][0].get("name", "")

        # 取器材
        equip_ids = []
        equip_names = []
        for e in ex.get("equipment", []):
            if isinstance(e, dict):
                equip_ids.append(e.get("id", 0))
                equip_names.append(e.get("name", "?"))
            else:
                equip_ids.append(e)
        if not equip_ids:
            equip_ids = [0]
            equip_names.append("无器材")

        results.append({
            "name": name,
            "wger_id": ex.get("id"),
            "equip_ids": equip_ids,
            "equip_names": equip_names,
            "equip_text": ", ".join(equip_names),
        })

    # 打印前 15 个动作及其器材
    for r in results[:15]:
        name_clean = r["name"][:50] if r["name"] else "(无名称)"
        print(f"  ID {r['wger_id']:4d} {name_clean:40s} | 器材: {r['equip_text']}")

    # 模拟按经验过滤
    print(f"\n  == 各经验级别可用动作数:")
    for level, equip_list in EXPERIENCE_FILTER.items():
        filtered = [r for r in results if not equip_list or any(eid in equip_list for eid in r["equip_ids"]) or r["equip_ids"] == [0]]
        # 也包含无器材的动作（自重类的）
        filtered = [r for r in results if
            r["equip_ids"] == [0] or  # 无器材限制
            not equip_list or         # 不限
            any(eid in equip_list for eid in r["equip_ids"])
        ]
        print(f"    {level}: {len(filtered)}/{len(results)} 个动作可用")


if __name__ == "__main__":
    # 查一遍器材表
    list_equipment()

    # 测试 3 个关键肌群：胸、背、腿
    search_and_check(4, "Chest（胸部）")
    search_and_check(12, "Lats（背部）")
    search_and_check(10, "Quads（股四头）")
