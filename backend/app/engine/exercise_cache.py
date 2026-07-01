"""wger 动作懒加载缓存。

用到某个动作时，先查本地 exercise 表，没有再请求 wger 并自动缓存。
"""

import threading
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.orm_models import Exercise
from app.services.wger_service import search_exercises, get_exercise_detail
from app.database import SessionLocal

# SQLite 单写入者锁：防止并行缓存写入时 database is locked
_cache_write_lock = threading.Lock()


# wger 肌肉 ID 映射（英文名 → wger 数字 ID）
MUSCLE_ID_MAP = {
    "chest": 4,
    "shoulders": 2,
    "triceps": 5,
    "back": 12,
    "biceps": 1,
    "quadriceps": 10,
    "hamstrings": 11,
    "glutes": 8,
    "abdominals": 6,
    "core": 6,
    "calves": 13,
    "forearms": 14,
    "traps": 9,
    "adductors": 7,
    "lower_back": 3,
}

# wger 肌肉中文名 → 数字 ID（兼容旧代码）
MUSCLE_NAME_MAP = {
    "胸部": 4, "肩部": 2, "肱三头肌": 5,
    "背部": 12, "肱二头肌": 1,
    "股四头肌": 10, "腘绳肌": 11, "臀部": 8,
    "腹部": 6, "小腿": 13, "前臂": 14,
    "斜方肌": 9, "内收肌": 7, "竖脊肌": 3,
}


def _resolve_muscle_id(muscle: str) -> Optional[int]:
    """把肌肉名解析为 wger 数字 ID。"""
    if isinstance(muscle, int):
        return muscle
    muscle_lower = muscle.lower().strip()
    if muscle_lower in MUSCLE_ID_MAP:
        return MUSCLE_ID_MAP[muscle_lower]
    if muscle in MUSCLE_NAME_MAP:
        return MUSCLE_NAME_MAP[muscle]
    return None


def get_or_fetch_exercise(wger_id: int, db: Session) -> Optional[Exercise]:
    """按 wger_id 查本地 exercise 表，没有则从 wger 拉取并缓存。

    注意：使用独立 session 写入缓存，不会影响调用方传入的 db。

    Args:
        wger_id: wger 平台的 exercise ID
        db: 数据库 session

    Returns:
        Exercise 对象，拉取失败时返回 None
    """
    ex = db.query(Exercise).filter(Exercise.wger_id == wger_id).first()
    if ex:
        return ex

    # 使用独立 session 拉取并缓存，不污染调用方的 db
    cache_db = SessionLocal()
    try:
        data = get_exercise_detail(wger_id)
        if not data:
            return None

        ex = Exercise(
            wger_id=wger_id,
            name=data.get("name", ""),
            target_muscle=data.get("target_muscle", ""),
            muscle_group=data.get("muscle_group", ""),
            equipment=data.get("equipment", ""),
            description=data.get("description", ""),
            image_url=", ".join(data.get("images", [])) if data.get("images") else "",
            difficulty=data.get("difficulty", 1),
        )
        cache_db.add(ex)
        cache_db.commit()
        cache_db.refresh(ex)

        # 把新缓存的 exercise 合并到调用方 db
        return db.merge(ex)
    except Exception as e:
        print(f"[ExerciseCache] wger_id={wger_id} 拉取失败: {e}")
        cache_db.rollback()
        return None
    finally:
        cache_db.close()


def search_and_cache(
    muscle: str,
    db: Session,
    limit: int = 15,
) -> List[Exercise]:
    """按肌肉群从 wger 搜索动作，缓存到本地，返回本地记录列表。

    搜索时先查本地已有数据，再从 wger 补充新动作。
    注意：缓存写入使用独立 session，不会影响调用方传入的 db。

    Args:
        muscle: 肌肉英文名或数字 ID（如 "chest" 或 4）
        db: 数据库 session
        limit: 每个肌肉群最多返回多少个动作

    Returns:
        Exercise 对象列表
    """
    muscle_id = _resolve_muscle_id(muscle)

    # 如果解析不出数字 ID，返回空列表
    if muscle_id is None:
        print(f"[ExerciseCache] 无法解析肌肉: {muscle}")
        return []

    # 先查本地已缓存的该肌肉群动作
    local = db.query(Exercise).filter(
        Exercise.wger_id.isnot(None)
    ).limit(limit).all()

    if len(local) >= limit:
        return local

    # 本地不够，从 wger 搜（用数字 ID）
    try:
        results = search_exercises(muscle=muscle_id, limit=limit * 2)

        # 使用独立 session 写入缓存（加锁防 SQLite 并发写入冲突）
        cache_db = SessionLocal()
        try:
            new_count = 0
            with _cache_write_lock:
                for item in results:
                    wger_id = item.get("id")
                    if not wger_id:
                        continue
                    exists = cache_db.query(Exercise).filter(Exercise.wger_id == wger_id).first()
                    if not exists:
                        ex = Exercise(
                            wger_id=wger_id,
                            name=item.get("name", ""),
                            name_en=item.get("name", ""),
                            target_muscle=item.get("target_muscle", ""),
                            description=item.get("description", ""),
                            equipment="",
                        )
                        cache_db.add(ex)
                        new_count += 1

                if new_count > 0:
                    cache_db.commit()
        finally:
            cache_db.close()

    except Exception as e:
        print(f"[ExerciseCache] muscle_id={muscle_id} 搜索失败: {e}")
        # 不 rollback 调用方的 db

    # 返回本地库中所有动作
    return db.query(Exercise).filter(
        Exercise.wger_id.isnot(None)
    ).limit(limit).all()
