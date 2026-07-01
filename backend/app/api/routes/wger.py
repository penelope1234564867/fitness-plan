"""wger 代理接口

提供 GET /api/wger/exercise/{wger_id} 接口，
供前端按动作 ID 查询 wger 详情（图片列表 + 描述）。
带内存缓存，避免重复请求 wger 服务器。
"""

from fastapi import APIRouter, HTTPException
from app.services.wger_service import get_exercise_detail as _fetch_detail

router = APIRouter(prefix="/wger", tags=["wger 代理"])

# 简单内存缓存
_cache: dict[int, dict] = {}


@router.get("/exercise/{wger_id}")
async def get_exercise_detail(wger_id: int):
    """获取 wger 动作详情（图片列表 + 描述）。

    Args:
        wger_id: wger 数据库中的动作 ID

    Returns:
        包含 images 和 description 的 JSON
    """
    # 内存缓存命中
    if wger_id in _cache:
        return _cache[wger_id]

    try:
        result = _fetch_detail(wger_id)
        _cache[wger_id] = result
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"wger 请求失败: {str(e)}")
