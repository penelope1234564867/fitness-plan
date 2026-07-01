"""列出 wger 所有器材（标准列表 + 动作中出现的器材）"""
import httpx, time
from collections import Counter

WGER_BASE = "https://wger.de/api/v2"
client = httpx.Client(timeout=15, follow_redirects=True)

# ── 1. 标准器材列表 ──
print("=" * 60)
print("一、标准器材列表 (/api/v2/equipment/)")
print("=" * 60)
r = client.get(f"{WGER_BASE}/equipment/")
standard = {}
for eq in r.json().get("results", []):
    standard[eq["id"]] = eq["name"]
    print(f"  ID={eq['id']:5d}  {eq['name']}")

# ── 2. 扫动作找出所有出现的器材 ID ──
print(f"\n{'='*60}")
print(f"二、扫描动作中出现的器材")
print(f"{'='*60}")

appeared = {}
appeared_counter = Counter()
total_ex = 0

for page in range(1, 6):  # 只扫 5 页
    for retry in range(3):
        try:
            resp = client.get(f"{WGER_BASE}/exerciseinfo/", params={
                "format": "json", "limit": 50, "page": page,
                "language": 2, "status": 2
            })
            data = resp.json()
            break
        except Exception as e:
            if retry < 2:
                time.sleep(2)
                continue
            print(f"  第{page}页跳过: {e}")
            data = {"results": []}
            break

    results = data.get("results", [])
    if not results:
        break
    total_ex += len(results)
    for ex in results:
        for e in ex.get("equipment", []):
            eid = e.get("id") if isinstance(e, dict) else e
            ename = e.get("name") if isinstance(e, dict) else ""
            if eid not in appeared:
                appeared[eid] = ename
            appeared_counter[eid] += 1
    if not data.get("next"):
        break

print(f"  共扫 {total_ex} 个动作\n")

# ── 3. 合并输出 ──
all_ids = sorted(set(list(standard.keys()) + list(appeared.keys())))
print(f"{'ID':>6}  {'出现':>5}  {'来源':>4}  {'器材名称'}")
print("-" * 55)
for eid in all_ids:
    count = appeared_counter.get(eid, 0)
    name = standard.get(eid, appeared.get(eid, "?"))
    source = "标准" if eid in standard else "仅动作"
    print(f"{eid:>6}  {count:>5}  {source:>4}  {name}")

# ── 4. 汇总 ──
unknown = sorted(set(appeared.keys()) - set(standard.keys()))
print(f"\n{'='*60}")
print(f"  标准器材: {len(standard)} 个")
print(f"  动作中出现的器材 ID: {len(appeared)} 个")
print(f"  其中未在标准列表中的: {len(unknown)} 个")
for eid in unknown:
    print(f"    ID={eid}  (出现 {appeared_counter[eid]} 次)")
print(f"{'='*60}")
