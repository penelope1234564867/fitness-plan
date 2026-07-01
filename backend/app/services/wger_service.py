"""wger 数据服务

封装 wger REST API 调用逻辑，供 exercise_agent.py 和 wger 代理接口共用。
"""

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

    import re

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
                target_muscle = m.get("name_en", m.get("name", ""))
                break

        image_url = ""
        for img in ex.get("images", []):
            if isinstance(img, dict) and img.get("image"):
                image_url = img["image"]
                break

        # 清理 HTML 标签
        desc_clean = re.sub(r"<[^>]+>", "", desc).strip()

        exercises.append({
            "wger_id": ex.get("id"),
            "id": ex.get("id"),
            "name": name,
            "target_muscle": target_muscle,
            "image_url": image_url,
            "description": desc_clean,
        })

    return exercises[:50]


def get_exercise_detail(wger_id: int) -> dict:
    """获取单个动作的详情（图片列表 + 描述）。

    wger 没有 /exerciseinfo/{id} 独立端点，
    改为通过 search 按 id 过滤：exerciseinfo/?id={wger_id}&limit=1

    Args:
        wger_id: wger 动作 ID

    Returns:
        包含 images 和 description 的字典
    """
    import re

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

    # 提取图片
    images = []
    for img in ex.get("images", []):
        if isinstance(img, dict) and img.get("image"):
            images.append(img["image"])

    # 提取描述（去 HTML 标签）
    description = ""
    for t in ex.get("translations", []):
        if t.get("language") == 2:  # 中文
            description = t.get("description", "")
            break
    if not description and ex.get("translations"):
        description = ex["translations"][0].get("description", "")
    # 清理 HTML 标签
    description = re.sub(r"<[^>]+>", "", description).strip()

    return {
        "images": images[:3],
        "description": description,
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
