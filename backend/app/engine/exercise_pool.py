"""中周期缓存池管理 — PoolManager

缓存池是 spec 的核心设计：
  中周期开始 → wger 搜 20-30 个/肌群 → 缓存到本地池
  中周期内   → 每周 LLM 从缓存池选不同的动作组合
  中周期结束 → 刷新缓存池

数据流：
  wger API → Exercise 表（wger_id 去重缓存） → 按肌群取 20-30 个 → 缓存池
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.orm_models import MesocycleExercisePool, Exercise

logger = logging.getLogger("exercise_pool")

# ── wger 肌肉 ID → 中文肌群名 ──────────────────────────────

_MUSCLE_ID_TO_GROUP = {
    1: "肱二头肌",
    2: "肩部",
    3: "前臂",
    4: "胸部",
    5: "肱三头肌",
    6: "腹肌",
    7: "前锯肌",
    8: "臀部",
    9: "斜方肌",
    10: "股四头肌",
    11: "腘绳肌",
    12: "背部",
    13: "小腿",
    14: "三角肌后束",
}


def _muscle_id_to_group(muscle_id: int) -> str:
    """wger 肌肉 ID → 中文肌群名。"""
    return _MUSCLE_ID_TO_GROUP.get(muscle_id, "")


# ── wger category 英文名 → 中文肌群名 ─────────────────────
# 用于兜底搜索时反过来匹配 Exercise 表已有的英文分类名
_CATEGORY_EN_TO_CN = {
    "chest": "胸部", "shoulders": "肩部", "triceps": "肱三头肌",
    "biceps": "肱二头肌", "back": "背部", "arms": "手臂",
    "legs": "腿部", "quads": "股四头肌", "hamstrings": "腘绳肌",
    "glutes": "臀部", "abs": "腹肌", "core": "核心",
    "calves": "小腿", "forearms": "前臂", "traps": "斜方肌",
    "lats": "背阔肌", "lower back": "下背部", "full body": "全身",
}


class PoolManager:
    """中周期缓存池管理——增删查。"""

    @staticmethod
    def refresh_pool(
        mesocycle_id: int,
        all_muscle_ids: List[int],
        db: Session,
    ) -> int:
        """从中周期所有目标肌群的 Exercise 表中填充池子。

        从 Exercise 表（已缓存的 wger 动作）中，
        按肌群挑选 20-30 个/肌群写入 mesocycle_exercise_pool。

        Args:
            mesocycle_id: 当前中周期 ID
            all_muscle_ids: 该中周期涉及的所有 wger 肌群 ID 列表
            db: 数据库 session

        Returns:
            int: 写入的动作总数
        """
        # 先清空旧数据
        db.query(MesocycleExercisePool).filter(
            MesocycleExercisePool.mesocycle_id == mesocycle_id,
        ).delete()
        db.flush()

        total = 0
        for muscle_id in all_muscle_ids:
            # 从 Exercise 表查询该肌群的动作（最多 30 个）
            group_name = _muscle_id_to_group(muscle_id)
            if not group_name:
                continue

            exercises = _query_exercise_by_group(db, muscle_id, group_name)

            if not exercises:
                # 兜底：从 wger API 直接拉取并创建 Exercise 记录
                exercises = _fetch_from_wger_for_pool(muscle_id, group_name, db)

            for ex in exercises:
                if not ex.wger_id:
                    continue
                # 检查是否已存在
                existing = (
                    db.query(MesocycleExercisePool)
                    .filter(
                        MesocycleExercisePool.mesocycle_id == mesocycle_id,
                        MesocycleExercisePool.wger_id == ex.wger_id,
                    )
                    .first()
                )
                if existing:
                    continue

                pool_entry = MesocycleExercisePool(
                    mesocycle_id=mesocycle_id,
                    wger_id=ex.wger_id,
                    name=ex.name,
                    target_muscle=ex.target_muscle,
                    muscle_group_id=muscle_id,
                    equipment=ex.equipment,
                    image_url=ex.image_url,
                    description=ex.description,
                    difficulty=ex.difficulty,
                )
                db.add(pool_entry)
                total += 1

            db.flush()

        logger.info(f"[PoolManager] 刷新缓存池: mesocycle={mesocycle_id}, 共 {total} 个动作")
        return total

    @staticmethod
    def get_candidates(
        mesocycle_id: int,
        muscle_ids: List[int],
        exclude_names: Optional[List[str]] = None,
        db: Optional[Session] = None,
    ) -> list:
        """获取该天的候选动作列表。

        从缓存池中按肌群查找，排除已用的动作名。

        Args:
            mesocycle_id: 当前中周期 ID
            muscle_ids: 该天训练的肌群 ID 列表
            exclude_names: 需要排除的动作名称列表（上周已选）
            db: 数据库 session

        Returns:
            list: [{"wger_id", "name", "target_muscle", "muscle_group_id",
                     "equipment", "image_url", "description", "difficulty"}, ...]
        """
        if not db or not muscle_ids:
            return []

        # 查询缓存池中该肌群的所有动作
        entries = (
            db.query(MesocycleExercisePool)
            .filter(
                MesocycleExercisePool.mesocycle_id == mesocycle_id,
                MesocycleExercisePool.muscle_group_id.in_(muscle_ids),
            )
            .all()
        )

        if not entries:
            logger.info(
                f"[PoolManager] 缓存池为空: mesocycle={mesocycle_id}, "
                f"muscle_ids={muscle_ids}"
            )
            return []

        # 构建候选列表
        exclude_set = set(exclude_names or [])
        candidates = []
        seen_wger_ids = set()

        for entry in entries:
            if not entry.wger_id or entry.wger_id in seen_wger_ids:
                continue
            if entry.name in exclude_set:
                continue

            seen_wger_ids.add(entry.wger_id)
            candidates.append({
                "wger_id": entry.wger_id,
                "name": entry.name,
                "target_muscle": entry.target_muscle or _muscle_id_to_group(entry.muscle_group_id or 0),
                "muscle_group_id": entry.muscle_group_id,
                "equipment": entry.equipment or "",
                "image_url": entry.image_url or "",
                "description": entry.description or "",
                "difficulty": entry.difficulty or 1,
            })

        logger.info(
            f"[PoolManager] get_candidates: mesocycle={mesocycle_id}, "
            f"muscle_ids={muscle_ids}, candidates={len(candidates)}"
        )
        return candidates

    @staticmethod
    def get_used_exercise_names(
        mesocycle_id: int,
        week_number: int,
        db: Session,
    ) -> set:
        """获取中周期内本周之前已用过的动作名集合。

        用于构建排除列表，辅助 LLM 保持多样性。

        Args:
            mesocycle_id: 中周期 ID
            week_number: 当前周号（不含该周）
            db: 数据库 session

        Returns:
            set: 已用过的动作名集合
        """
        from app.models.orm_models import Week, Day, ExerciseSlot

        used_names = set()
        weeks = (
            db.query(Week)
            .filter(
                Week.mesocycle_id == mesocycle_id,
                Week.week_number < week_number,
            )
            .all()
        )

        for w in weeks:
            for day in w.days:
                for slot in day.slots:
                    if slot.phase_type == "main" and slot.exercise_name:
                        used_names.add(slot.exercise_name)

        return used_names


# ═══════════════════════════════════════════════════════════════
#  兜底查询 + wger 回源
# ═══════════════════════════════════════════════════════════════


def _query_exercise_by_group(db: Session, muscle_id: int, group_name: str) -> list:
    """用多种命名约定查询 Exercise 表。

    因为历史上 `muscle_group` 可能存的是中文（"胸部"）或英文（"chest"），
    这里尝试多种写法。
    """
    # 1. 精确中文名
    exercises = (
        db.query(Exercise)
        .filter(Exercise.muscle_group == group_name)
        .limit(30)
        .all()
    )
    if exercises:
        return exercises

    # 2. 精确 target_muscle（中文）
    exercises = (
        db.query(Exercise)
        .filter(Exercise.target_muscle == group_name)
        .limit(30)
        .all()
    )
    if exercises:
        return exercises

    # 3. 英文 category 名 → 中文的反查
    #    Exercise.muscle_group = "chest" → 找 muscle_id=4 时用 "chest"
    for en_name, cn_name in _CATEGORY_EN_TO_CN.items():
        if cn_name == group_name:
            exercises = (
                db.query(Exercise)
                .filter(Exercise.muscle_group == en_name)
                .limit(30)
                .all()
            )
            if exercises:
                return exercises
            break

    # 4. 英文名查 target_muscle
    for en_name, cn_name in _CATEGORY_EN_TO_CN.items():
        if cn_name == group_name:
            exercises = (
                db.query(Exercise)
                .filter(Exercise.target_muscle == en_name)
                .limit(30)
                .all()
            )
            if exercises:
                return exercises
            break

    return []


def _fetch_from_wger_for_pool(muscle_id: int, group_name: str, db: Session) -> list:
    """当 Exercise 表找不到该肌群数据时，直接从 wger API 回源拉取。

    流程：
      1. 调 wger API 按肌群搜索
      2. 对每个返回的动作，创建 Exercise 记录（wger_id 去重）
      3. 返回 Exercise ORM 对象列表

    Returns:
        List[Exercise]: 该肌群的 Exercise 对象列表
    """
    try:
        from app.services.wger_service import search_exercises

        raw = search_exercises(muscle=muscle_id, limit=30)
        if not raw:
            return []

        results = []
        for item in raw:
            wger_id = item.get("wger_id") or item.get("id")
            if not wger_id:
                continue

            # 去重
            existing = db.query(Exercise).filter(Exercise.wger_id == wger_id).first()
            if existing:
                results.append(existing)
                continue

            ex = Exercise(
                wger_id=wger_id,
                name=item.get("name", ""),
                target_muscle=group_name,
                muscle_group=group_name,
                equipment=item.get("equipment", ""),
                description=item.get("description", ""),
                image_url=item.get("image_url", ""),
                difficulty=1,
            )
            db.add(ex)
            db.flush()
            results.append(ex)

        logger.info(
            f"[PoolManager] wger 回源: muscle_id={muscle_id}({group_name}), "
            f"获取 {len(results)} 个动作"
        )
        return results

    except Exception as e:
        logger.warning(
            f"[PoolManager] wger 回源失败: muscle_id={muscle_id}({group_name}): {e}"
        )
        return []
