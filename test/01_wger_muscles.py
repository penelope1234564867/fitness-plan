"""Step 1: 查看 wger 数据库有哪些肌群"""

import httpx
import json

WGER_BASE = "https://wger.de/api/v2"

def list_muscles():
    resp = httpx.get(f"{WGER_BASE}/muscle/", params={"format": "json", "limit": 100})
    data = resp.json()

    print(f"\n{'='*60}")
    print(f"  wger 肌群列表（共 {data['count']} 个）")
    print(f"{'='*60}")
    print(f"  {'ID':>3}  {'拉丁名':30s} {'英文名':15s}")
    print(f"  {'─'*3}  {'─'*30} {'─'*15}")
    for m in data.get("results", []):
        name_en = m.get("name_en", "") or "—"
        print(f"  {m['id']:3d}  {m['name']:30s} {name_en:15s}")
    print()

if __name__ == "__main__":
    list_muscles()
