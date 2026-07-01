#!/usr/bin/env python3
"""
Wger MCP Server — 健身数据服务

基于 wger.de 开放 API (https://wger.de/api/v2/) 构建的 MCP Server。
提供 7 个只读工具，无需 API Key。
所有工具返回 JSON 格式，供 Agent 程序化使用。

数据规模（实际测试）:
  - 训练动作: 859 个
  - 教学图片: 360 张
  - 演示视频: 78 个
  - 肌群: 15 个
  - 类别: 8 个
  - 器材: 11 种

启动方式:
  python wger-mcp-server/wger_mcp_server.py
"""

from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP

# ── Server 初始化 ────────────────────────────────────────────

mcp = FastMCP("wger_mcp")

# ── 常量 ────────────────────────────────────────────────────

WGER_BASE = "https://wger.de/api/v2"
DEFAULT_LIMIT = 20
MAX_LIMIT = 100


# ── 共享 HTTP 客户端 ───────────────────────────────────────


async def _get(endpoint: str, params: dict | None = None) -> dict:
    """统一的 wger API GET 请求。"""
    async with httpx.AsyncClient(timeout=15.0) as client:
        url = f"{WGER_BASE}/{endpoint}"
        req_params = {"format": "json"}
        if params:
            req_params.update(params)
        resp = await client.get(url, params=req_params, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()


def _format_exercise(ex: dict) -> dict:
    """将 wger exerciseinfo 条目映射为简洁字段。

    原始 API 返回包含 translations、muscles 等嵌套数组，
    这里提取最重要的字段供 Agent 使用。
    """
    # 提取英文翻译（language=2）
    name = ""
    desc = ""
    for t in ex.get("translations", []):
        if t.get("language") == 2 or t.get("language") == {"id": 2}:
            name = t.get("name", "")
            desc = t.get("description", "")
            break
    if not name and ex.get("translations"):
        name = ex["translations"][0].get("name", "")

    # 提取目标肌群（取第一个主要肌群的英文名）
    target_muscle = ""
    for m in ex.get("muscles", []):
        if isinstance(m, dict):
            target_muscle = m.get("name_en", m.get("name", ""))
            break

    # 提取分类
    category = ""
    if isinstance(ex.get("category"), dict):
        category = ex["category"].get("name", "")

    # 提取首张主图
    image_url = ""
    for img in ex.get("images", []):
        if isinstance(img, dict) and img.get("is_main"):
            image_url = img.get("image", "")
            break
    if not image_url and ex.get("images"):
        if isinstance(ex["images"][0], dict):
            image_url = ex["images"][0].get("image", "")

    return {
        "id": ex.get("id"),
        "wger_id": ex.get("id"),  # 兼容 plan_service 的字段名
        "name": name,
        "description": desc,
        "target_muscle": target_muscle,
        "category": category,
        "equipment": [e.get("name", "") for e in ex.get("equipment", []) if isinstance(e, dict)],
        "image_url": image_url,
    }


# ── 工具 1：list_categories ──────────────────────────────


@mcp.tool(
    name="wger_list_categories",
    annotations={
        "title": "列出动作分类",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wger_list_categories() -> str:
    """列出 wger 中所有训练动作分类（如 Abs、Chest、Legs 等）。

    用于在搜索动作前查看可用的分类选项。
    返回结果包含分类 ID 和名称，ID 可用于 search_exercises 的 category 参数。

    Returns:
        str: JSON 数组，每项包含 id（int）和 name（str）。
        示例: [{"id": 10, "name": "Abs"}, {"id": 8, "name": "Arms"}]
    """
    try:
        data = await _get("exercisecategory")
        items = [{"id": c["id"], "name": c["name"]} for c in data.get("results", [])]
        import json
        return json.dumps(items, ensure_ascii=False)
    except Exception as e:
        return f"Error: 获取分类失败 - {type(e).__name__}"


# ── 工具 2：list_muscles ────────────────────────────────


@mcp.tool(
    name="wger_list_muscles",
    annotations={
        "title": "列出所有肌群",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wger_list_muscles() -> str:
    """列出 wger 中所有肌群，含中英文名、正背面标识和解剖图 URL。

    返回的 ID 可用于 search_exercises 的 muscle 参数。
    图片 URL 可在前端展示肌群解剖图。

    Returns:
        str: JSON 数组，每项包含:
            - id (int): 肌群 ID
            - name (str): 拉丁名 (e.g. "Pectoralis major")
            - name_en (str): 英文名 (e.g. "Chest")
            - is_front (bool): 是否在身体正面
            - image_url_main (str): 主肌群 SVG 图 URL
            - image_url_secondary (str): 辅助肌群图 URL
    """
    try:
        data = await _get("muscle")
        items = [
            {
                "id": m["id"],
                "name": m.get("name", ""),
                "name_en": m.get("name_en", ""),
                "is_front": m.get("is_front", True),
                "image_url_main": m.get("image_url_main", ""),
                "image_url_secondary": m.get("image_url_secondary", ""),
            }
            for m in data.get("results", [])
        ]
        import json
        return json.dumps(items, ensure_ascii=False)
    except Exception as e:
        return f"Error: 获取肌群失败 - {type(e).__name__}"


# ── 工具 3：list_equipment ─────────────────────────────


@mcp.tool(
    name="wger_list_equipment",
    annotations={
        "title": "列出所有器材类型",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wger_list_equipment() -> str:
    """列出 wger 中所有器材类型（如 Barbell、Dumbbell、Bodyweight 等）。

    用于在搜索动作前查看可用的器材选项。
    返回的 ID 可用于 search_exercises 的 equipment 参数。

    Returns:
        str: JSON 数组，每项包含 id（int）和 name（str）。
    """
    try:
        data = await _get("equipment")
        items = [{"id": e["id"], "name": e["name"]} for e in data.get("results", [])]
        import json
        return json.dumps(items, ensure_ascii=False)
    except Exception as e:
        return f"Error: 获取器材类型失败 - {type(e).__name__}"


# ── 工具 4：search_exercises（核心工具） ────────────────


@mcp.tool(
    name="wger_search_exercises",
    annotations={
        "title": "搜索训练动作",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wger_search_exercises(
    query: Optional[str] = None,
    muscle: Optional[int] = None,
    equipment: Optional[int] = None,
    category: Optional[int] = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> str:
    """搜索 wger 中的训练动作。这是最核心的工具。

    按肌群、器材、关键词和分类的组合条件搜索训练动作。
    返回每个动作的名称、描述、目标肌群、分类、所需器材和教学图片 URL。

    参数说明:
        - query（推荐）：自然语言搜索，如 "bench press"、"dumbbell curl"、"bodyweight squat"
        - muscle：精确的肌群 ID 过滤，搭配 query 使用效果更好
        - equipment：器材 ID 过滤
        - category：分类 ID 过滤
        - limit/offset：分页控制

    使用建议:
        - 先通过 list_categories/list_muscles/list_equipment 获取可用的 ID
        - 先用少量条件搜索（如只传 muscle），找到合适的动作后再细化
        - query 参数支持模糊匹配，适合关键词搜索

    Returns:
        str: JSON 对象，包含:
            - total (int): 匹配总数
            - count (int): 当前页结果数
            - offset (int): 偏移量
            - exercises (list): 动作列表，每项包含:
                - id (int): 动作 ID
                - name (str): 动作名称（英文）
                - description (str): 动作描述（HTML 格式）
                - target_muscle (str): 目标肌群英文名
                - category (str): 分类名称
                - equipment (list[str]): 所需器材列表
                - image_url (str): 首张教学图片 URL（可能为空）
    """
    try:
        # 构建 wger API 查询参数
        api_params = {"language": 2}
        if query:
            api_params["search"] = query
        if muscle:
            api_params["muscles"] = muscle  # 注意是复数！
        if equipment:
            api_params["equipment"] = equipment
        if category:
            api_params["category"] = category
        api_params["limit"] = min(limit or DEFAULT_LIMIT, MAX_LIMIT)
        api_params["offset"] = offset or 0

        data = await _get("exerciseinfo", api_params)
        results = data.get("results", [])

        exercises = []
        for ex in results:
            formatted = _format_exercise(ex)
            if formatted["name"]:  # 只保留有名称的动作
                exercises.append(formatted)

        import json
        response = {
            "total": data.get("count", 0),
            "count": len(exercises),
            "offset": offset or 0,
            "exercises": exercises,
        }
        return json.dumps(response, ensure_ascii=False)

    except Exception as e:
        return f"Error: 搜索动作失败 - {type(e).__name__}: {e}"


# ── 工具 5：get_exercise_details ────────────────────────


@mcp.tool(
    name="wger_get_exercise_details",
    annotations={
        "title": "获取动作完整详情",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wger_get_exercise_details(exercise_id: int) -> str:
    """获取单个训练动作的完整详细信息。

    包括动作名称、详细描述（HTML）、目标肌群、辅助肌群、所需器材、
    教学图片和演示视频列表等完整数据。

    通常 search_exercises 返回的信息已经足够，
    只有在需要完整详情（如所有图片、视频、辅助肌群）时才调用此工具。

    Args:
        params: validated input containing exercise_id.

    Returns:
        str: JSON 对象，包含动作的所有字段数据。
    """
    try:
        data = await _get(f"exerciseinfo/{exercise_id}")
        import json
        return json.dumps(data, ensure_ascii=False, default=str)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: 动作 ID {exercise_id} 不存在"
        return f"Error: API 请求失败 (HTTP {e.response.status_code})"
    except Exception as e:
        return f"Error: 获取详情失败 - {type(e).__name__}"


# ── 工具 6：get_exercise_images ─────────────────────────


@mcp.tool(
    name="wger_get_exercise_images",
    annotations={
        "title": "获取动作教学图片",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wger_get_exercise_images(exercise_id: int) -> str:
    """获取指定训练动作的教学图片列表。

    返回所有关联图片及其缩略图 URL。
    图片为 PNG 格式的真人示范照。
    前端展示时推荐使用 image 字段的原图 URL。

    Args:
        params: validated input containing exercise_id.

    Returns:
        str: JSON 数组，每项包含:
            - id (int): 图片 ID
            - image (str): 原图 URL (PNG)
            - thumbnails (dict|None): 缩略图对象 {small, medium}
            - is_main (bool): 是否为主图
            - style (str): 图片风格
    """
    try:
        data = await _get("exerciseimage", {"exercise": exercise_id})
        import json

        images = [
            {
                "id": img["id"],
                "image": img.get("image", ""),
                "thumbnails": img.get("thumbnails"),
                "is_main": img.get("is_main", False),
            }
            for img in data.get("results", [])
        ]
        return json.dumps(images, ensure_ascii=False)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: 动作 ID {exercise_id} 不存在或没有图片"
        return f"Error: API 请求失败 (HTTP {e.response.status_code})"
    except Exception as e:
        return f"Error: 获取图片失败 - {type(e).__name__}"


# ── 工具 7：get_exercise_videos ─────────────────────────


@mcp.tool(
    name="wger_get_exercise_videos",
    annotations={
        "title": "获取动作演示视频",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def wger_get_exercise_videos(exercise_id: int) -> str:
    """获取指定训练动作的演示视频列表。

    视频为 MOV 格式，部分为 1080p/4K 画质。
    注意：并不是所有动作都有演示视频。

    Args:
        params: validated input containing exercise_id.

    Returns:
        str: JSON 数组，每项包含:
            - id (int): 视频 ID
            - video (str): 视频文件 URL (MOV)
            - duration (str): 时长（秒）
            - width (int): 视频宽度
            - height (int): 视频高度
    """
    try:
        data = await _get("video", {"exercise": exercise_id})
        import json

        videos = [
            {
                "id": v["id"],
                "video": v.get("video", ""),
                "duration": v.get("duration", ""),
                "width": v.get("width", 0),
                "height": v.get("height", 0),
            }
            for v in data.get("results", [])
        ]
        return json.dumps(videos, ensure_ascii=False)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Error: 动作 ID {exercise_id} 不存在或没有视频"
        return f"Error: API 请求失败 (HTTP {e.response.status_code})"
    except Exception as e:
        return f"Error: 获取视频失败 - {type(e).__name__}"


# ── 入口 ────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
