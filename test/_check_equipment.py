"""查 wger 所有器材及其在动作中的出现频率"""
import httpx, json
from collections import Counter

WGER_BASE = "https://wger.de/api/v2"
client = httpx.Client(timeout=15)

# 1. 先看器材列表
print("=" * 50)
print("wger 器材列表")
print("=" * 50)
resp = client.get(f"{WGER_BASE}/equipment/")
for eq in resp.json().get("results", []):
    print(f"  ID={eq['id']}: {eq['name']}")

# 2. 搜大量动作，统计每种器材出现次数
print("\n" + "=" * 50)
print("各器材在实际动作中的出现频率")
print("=" * 50)

equip_counter = Counter()
total = 0
for page in range(1, 20):  # 搜 20 页
    resp = client.get(f"{WGER_BASE}/exerciseinfo/", params={
        "format": "json", "limit": 50, "page": page, "language": 2, "status": 2
    })
    data = resp.json()
    results = data.get("results", [])
    if not results:
        break
    for ex in results:
        for e in ex.get("equipment", []):
            if isinstance(e, dict) and e.get("id"):
                equip_counter[e["id"]] += 1
        total += 1
    if not data.get("next"):
        break

print(f"共搜索 {total} 个动作\n")
for eq_id, count in sorted(equip_counter.items(), key=lambda x: -x[1]):
    print(f"  器材 ID={eq_id}: 出现 {count} 次")

# 3. 总结哪些可能是"固定器械"（根据名称不是杠铃哑铃弹力带那些的）
machine_like = {2, 8, 9}  # SZ-Bar, Bench, Incline bench 也不算固定器械
print("\n" + "=" * 50)
print("建议分类")
print("=" * 50)
print("  固定器械: 除了杠铃/哑铃/壶铃/弹力带/自重/引体杆/瑜伽垫/瑞士球 之外的器材")
free_weights = {1, 3, 10, 2}  # Barbell, Dumbbell, Kettlebell, SZ-Bar
bodyweight_stuff = {4, 5, 6, 7, 11}  # Gym mat, Swiss Ball, Pull-up bar, Bodyweight, Resistance band
fixed_machines = set(eq["id"] for eq in resp.json().get("results", [])) - free_weights - bodyweight_stuff
print(f"  自由器械: {sorted(free_weights)}")
print(f"  自重/辅助: {sorted(bodyweight_stuff)}")
print(f"  其他(可能含固定器械): {sorted(fixed_machines)}")
