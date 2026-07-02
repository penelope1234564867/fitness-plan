"""wger 数据服务

封装 wger REST API 调用逻辑，供 exercise_agent.py 和 wger 代理接口共用。
"""

import re
import httpx
from typing import Optional, Dict, Any, List

WGER_BASE = "https://wger.de/api/v2"


def search_exercises(
    muscle: Optional[int] = None,
    query: Optional[str] = None,
    equipment: Optional[int] = None,
    category: Optional[int] = None,
    limit: int = 10,
    language: int = 2,
) -> list:
    """搜索 wger 训练动作，返回解析后的动作列表。

    Args:
        muscle: 目标肌群 ID
        query: 关键词搜索
        equipment: 器材 ID
        category: 分类 ID
        limit: 返回数量（1-50）
        language: 语言 ID（2=中文）

    Returns:
        解析后的动作字典列表，每个字典包含 id/name/description 等
    """
    api_params: Dict[str, Any] = {
        "format": "json",
        "language": language,
        "limit": min(limit, 50),
    }
    if query:
        api_params["search"] = query
    if muscle:
        api_params["muscles"] = muscle
    if equipment:
        api_params["equipment"] = equipment
    if category:
        api_params["category"] = category

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(f"{WGER_BASE}/exerciseinfo/", params=api_params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        print(f"[wger] search_exercises(muscle={muscle}) 请求失败: {e}")
        return []

    exercises = []
    for ex in data.get("results", []):
        name = ""
        desc = ""
        for t in ex.get("translations", []):
            if t.get("language") == language:
                name = t.get("name", "")
                desc = t.get("description", "")
                break
        if not name and ex.get("translations"):
            name = ex["translations"][0].get("name", "")

        target_muscle = ""
        for m in ex.get("muscles", []):
            if isinstance(m, dict):
                mid = m.get("id")
                name_en = m.get("name_en", m.get("name", ""))
                target_muscle = MUSCLE_CN.get(mid, name_en)
                break

        image_url = ""
        for img in ex.get("images", []):
            if isinstance(img, dict) and img.get("image"):
                image_url = img["image"]
                break

        # 提取分类作 muscle_group（中文优先）
        muscle_group = ""
        category = ex.get("category", {})
        if isinstance(category, dict):
            cat_name = category.get("name", "")
            muscle_group = CATEGORY_CN.get(cat_name.strip().lower(), cat_name)

        # 清理 HTML 标签
        desc_clean = re.sub(r"<[^>]+>", "", desc).strip()

        exercises.append({
            "wger_id": ex.get("id"),
            "id": ex.get("id"),
            "name": name,
            "target_muscle": target_muscle,
            "image_url": image_url,
            "description": desc_clean,
            "muscle_group": muscle_group,
        })

    return exercises[:50]


# ═══════════════════════════════════════════════════════════════
#  中文化映射表
# ═══════════════════════════════════════════════════════════════

# wger 分类（category）英文名 → 中文名
CATEGORY_CN = {
    "chest": "胸部", "shoulders": "肩部", "arms": "手臂",
    "legs": "腿部", "back": "背部", "core": "核心",
    "full body": "全身", "cardio": "有氧", "stretching": "拉伸",
    "abs": "腹部", "calves": "小腿", "biceps": "二头肌",
    "triceps": "三头肌", "forearms": "前臂", "glutes": "臀部",
    "hamstrings": "腘绳肌", "lats": "背阔肌", "lower back": "下背部",
    "neck": "颈部", "quadriceps": "股四头肌", "traps": "斜方肌",
}

# wger 器材（equipment）英文名 → 中文名
EQUIPMENT_CN = {
    "barbell": "杠铃", "dumbbell": "哑铃", "kettlebell": "壶铃",
    "body weight": "自重", "machine": "器械", "cable": "绳索",
    "none (bodyweight exercise)": "自重",
    "none (no equipment)": "自重", "no equipment": "自重",
    "band": "弹力带", "foam roll": "泡沫轴", "bench": "长凳",
    "medicine ball": "药球", "gym mat": "瑜伽垫",
    "e-z curl bar": "曲杆杠铃", "ez barbell": "曲杆杠铃",
    "olympic barbell": "奥林匹克杠铃", "trap bar": "六角杠铃",
    "svend": "斯文夹胸器",
    "weight plate": "杠铃片", "incline bench": "上斜长凳",
    "pull-up bar": "引体向上杆", "parallel bars": "双杠",
    "swiss ball": "健身球", "bosu ball": "波速球",
    "step": "踏板", "box": "跳箱",
    "suspension": "悬挂训练带", "trx": "悬挂训练带",
    "roller": "滚轴", "wheel roller": "健腹轮",
    "bag": "沙袋", "punching bag": "沙袋",
    "sled": "雪橇", "parallette": "俯卧撑架",
    "resistance band": "阻力带", "loop band": "环形弹力带",
    "treadmill": "跑步机", "exercise bike": "健身车",
    "elliptical": "椭圆机", "rower": "划船机",
    "ski erg": "滑雪测功仪", "bike": "单车",
    "sled machine": "雪橇机", "smith machine": "史密斯机",
    "hack squat": "哈克深蹲机", "leg press": "腿举机",
    "pec deck": "蝴蝶机", "pulley": "滑轮",
    "lat pulldown": "高位下拉机", "row machine": "划船机",
    "calf machine": "提踵机", "ab bench": "腹肌板",
    "hyperextension": "背脊凳", "dip bar": "双杠臂屈伸架",
    "neck machine": "颈部训练器", "grip trainer": "握力器",
    "ankle weights": "脚踝负重", "vest": "负重背心",
}

# 肌肉 ID → 中文名映射（与 wger API v2 实际肌肉表严格对齐）
MUSCLE_CN = {
    1: "肱二头肌",      # Biceps brachii
    2: "三角肌",        # Anterior deltoid (Shoulders)
    3: "前锯肌",        # Serratus anterior
    4: "胸大肌",        # Pectoralis major (Chest)
    5: "肱三头肌",      # Triceps brachii
    6: "腹直肌",        # Rectus abdominis (Abs)
    7: "腓肠肌",        # Gastrocnemius (Calves)
    8: "臀大肌",        # Gluteus maximus (Glutes)
    9: "斜方肌",        # Trapezius
    10: "股四头肌",     # Quadriceps femoris (Quads)
    11: "腘绳肌",       # Biceps femoris (Hamstrings)
    12: "背阔肌",       # Latissimus dorsi (Lats)
    13: "肱肌",         # Brachialis
    14: "腹外斜肌",     # Obliquus externus abdominis
    15: "比目鱼肌",     # Soleus
}


def _extract_muscles(muscle_list: list) -> list:
    """从 wger 肌肉对象数组中提取结构化的肌肉列表。"""
    result = []
    for m in muscle_list:
        if isinstance(m, dict):
            mid = m.get("id")
            name_en = m.get("name") or m.get("name_en", "")
            result.append({
                "id": mid,
                "name_en": name_en,
                "name_cn": MUSCLE_CN.get(mid, ""),
            })
    return result


def get_exercise_detail(wger_id: int) -> dict:
    """获取单个动作的详情（图片列表 + 描述 + 肌群等元信息）。

    wger 没有 /exerciseinfo/{id} 独立端点，
    改为通过 search 按 id 过滤：exerciseinfo/?id={wger_id}&limit=1

    Args:
        wger_id: wger 动作 ID

    Returns:
        包含 images, description, target_muscle, equipment 等的字典
    """

    with httpx.Client(timeout=15.0, follow_redirects=True) as client:
        resp = client.get(
            f"{WGER_BASE}/exerciseinfo/",
            params={"format": "json", "id": wger_id, "limit": 1},
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return {"images": [], "description": ""}

    ex = results[0]

    # ── 第 1 步：提取所有元数据 ──────────────────────────

    # 图片
    images = []
    for img in ex.get("images", []):
        if isinstance(img, dict) and img.get("image"):
            images.append(img["image"])

    # 动作名（中文优先）
    name = ""
    for t in ex.get("translations", []):
        if t.get("language") == 2:
            name = t.get("name", "")
            break
    if not name:
        name = ex.get("name", "")

    # 目标肌群（中文优先）
    target_muscle = ""
    for m in ex.get("muscles", []):
        if isinstance(m, dict):
            mid = m.get("id")
            name_en = m.get("name", m.get("name_en", ""))
            target_muscle = MUSCLE_CN.get(mid, name_en)
            break

    # 器材（中文映射）
    equipment_list = []
    for eq in ex.get("equipment", []):
        if isinstance(eq, dict) and eq.get("name"):
            eq_name = eq["name"]
            equipment_list.append(EQUIPMENT_CN.get(eq_name.strip().lower(), eq_name))
    equipment = ", ".join(equipment_list)

    # 分类（中文映射）
    category = ex.get("category", {})
    if isinstance(category, dict):
        cat_name = category.get("name", "")
        muscle_group = CATEGORY_CN.get(cat_name.strip().lower(), cat_name)
    else:
        muscle_group = ""

    # 全部主动肌和辅助肌
    primary_muscles = _extract_muscles(ex.get("muscles", []))
    secondary_muscles = _extract_muscles(ex.get("muscles_secondary", []))

    primary_names = [m["name_cn"] or m["name_en"] for m in primary_muscles]
    secondary_names = [m["name_cn"] or m["name_en"] for m in secondary_muscles]

    # ── 第 2 步：提取 wger 原始描述（可能很短）─────────
    raw_desc = ""
    for t in ex.get("translations", []):
        if t.get("language") == 2:
            raw_desc = t.get("description", "")
            break
    if not raw_desc and ex.get("translations"):
        raw_desc = ex["translations"][0].get("description", "")
    raw_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()

    # ── 第 3 步：用 LLM 生成详尽准确的中文描述 ──────────
    description = raw_desc  # 兜底
    needs_generate = (
        not raw_desc
        or len(raw_desc) < 80
        or not re.search(r'[一-鿿]', raw_desc)
    )

    if needs_generate:
        try:
            from app.services.llm_service import get_fast_llm
            llm = get_fast_llm()

            # 构建上下文
            ctx_parts = [f"动作名称：{name}"]
            if primary_names:
                ctx_parts.append(f"目标肌群（主动肌）：{'、'.join(primary_names)}")
            if secondary_names:
                ctx_parts.append(f"辅助肌群：{'、'.join(secondary_names)}")
            if equipment:
                ctx_parts.append(f"所需器材：{equipment}")
            if muscle_group:
                ctx_parts.append(f"动作分类：{muscle_group}")

            # 如果有原始描述（哪怕英文），也提供给 LLM 参考
            if raw_desc:
                ctx_parts.append(f"\n参考信息：\n{raw_desc}")

            context = "\n".join(ctx_parts)

            sys_msg = {
                "role": "system",
                "content": (
                    "你是一名专业的健身教练和运动科学专家。请根据提供的动作信息，"
                    "生成一份详尽、准确的中文动作描述。要求：\n"
                    "1. 用词专业准确（使用标准的健身/解剖学中文术语）\n"
                    "2. 包含一步步的动作要领（起始姿势 → 动作过程 → 呼吸节奏）\n"
                    "3. 指出常见错误和如何避免\n"
                    "4. 说明锻炼的肌肉及其功能\n"
                    "5. 如果参考信息中有英文描述，将其融合进来，不要遗漏关键信息\n"
                    "6. 如果是热身/拉伸动作，重点说明拉伸的肌群和注意事项\n"
                    "7. 总字数 150-300 字\n"
                    "8. 格式要求：分 2-4 个短段落，每段不超过 3 行，重要术语用「」括起来，"
                    "不要 markdown 语法，不要标题，不要列表编号\n"
                    "9. 只输出描述文本，不要额外说明"
                ),
            }
            user_msg = {
                "role": "user",
                "content": f"请根据以下信息生成该动作的详细中文描述：\n\n{context}",
            }

            generated = ""
            for chunk in llm.stream_invoke([sys_msg, user_msg], max_tokens=2048):
                generated += chunk
            if generated.strip():
                description = generated.strip()

                # 持久化：回写 Exercise 缓存表
                try:
                    from app.database import SessionLocal
                    from app.models.orm_models import Exercise
                    ex_db = SessionLocal()
                    try:
                        cached = ex_db.query(Exercise).filter(
                            Exercise.wger_id == wger_id
                        ).first()
                        if cached:
                            cached.description = description
                            ex_db.commit()
                    finally:
                        ex_db.close()
                except Exception as e2:
                    print(f"[wger] 描述回写缓存失败 (wger_id={wger_id}): {e2}")
        except Exception as e:
            print(f"[wger] 描述生成失败 (wger_id={wger_id}): {e}")
            # 保持 raw_desc 作为兜底

    return {
        "name": name,
        "images": images[:3],
        "description": description,
        "target_muscle": target_muscle,
        "equipment": equipment,
        "muscle_group": muscle_group,
        "primary_muscles": primary_muscles,
        "secondary_muscles": secondary_muscles,
        "equipment_list": equipment_list,
    }


def list_categories() -> list:
    """列出 wger 动作分类。"""
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        resp = client.get(f"{WGER_BASE}/exercisecategory/", params={"format": "json"})
        resp.raise_for_status()
        data = resp.json()
    return [{"id": c["id"], "name": c["name"]} for c in data.get("results", [])]


def list_muscles() -> list:
    """列出 wger 肌群。"""
    with httpx.Client(timeout=10.0, follow_redirects=True) as client:
        resp = client.get(f"{WGER_BASE}/muscle/", params={"format": "json"})
        resp.raise_for_status()
        data = resp.json()
    return [
        {"id": m["id"], "name": m.get("name", ""), "name_en": m.get("name_en", "")}
        for m in data.get("results", [])
    ]
