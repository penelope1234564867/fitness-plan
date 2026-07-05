"""Task Manager — 后台异步任务管理（替代 SSE 长连接）

解决 Render 100s 超时问题：
  1. POST /generate-task  → 50ms 返回 task_id
  2. GET  /generate-task/{id} → 轮询进度（爱跑多久跑多久）
  3. 后台 asyncio.Task 慢慢生成，不依赖长连接

用法:
  task_id = await store.create(request)
  asyncio.create_task(run_generation(task_id, request))
  status = await store.get(task_id)  # 轮询
"""

import uuid
import asyncio
import traceback
from datetime import datetime
from typing import Optional

from app.models.schemas import InitPlanRequest
from app.engine.generator import generate_init_week
from app.models.orm_models import (
    Macrocycle, Mesocycle, UserCurrentState, User,
)
from app.database import SessionLocal


class TaskStore:
    """内存任务存储（单进程可用）。"""

    def __init__(self):
        self._tasks: dict[str, dict] = {}

    async def create(self, request: InitPlanRequest) -> str:
        task_id = uuid.uuid4().hex[:12]
        self._tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "phase": "",
            "text": "等待开始...",
            "logs": [],
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        return task_id

    async def get(self, task_id: str) -> Optional[dict]:
        task = self._tasks.get(task_id)
        if task:
            return {**task, "logs": task["logs"][-50:]}
        return None

    async def add_log(self, task_id: str, phase: str, text: str, progress: int = None):
        if task_id not in self._tasks:
            return
        t = self._tasks[task_id]
        t["phase"] = phase
        t["text"] = text
        if progress is not None:
            t["progress"] = progress
        t["updated_at"] = datetime.now().isoformat()
        t["logs"].append({
            "time": datetime.now().isoformat(),
            "phase": phase,
            "text": text,
            "progress": t["progress"],
        })


store = TaskStore()


async def run_generation(task_id: str, request: InitPlanRequest):
    """后台执行 init-plan 生成逻辑。"""
    t = store._tasks[task_id]
    t["status"] = "running"
    await store.add_log(task_id, "init", "🚀 开始生成训练计划...", 0)

    db = SessionLocal()
    event_queue: asyncio.Queue = asyncio.Queue()

    # SSE 事件 → task store 的消费者
    async def consume_events():
        while True:
            event, data = await event_queue.get()
            if event == "__END__":
                break
            if event == "progress":
                p = data.get("progress")
                await store.add_log(
                    task_id, data.get("phase", ""),
                    data.get("text", ""),
                    p if isinstance(p, (int, float)) else None,
                )
            elif event == "day_done":
                await store.add_log(
                    task_id, "day_done",
                    f"✅ 第{data.get('day')}天 ({data.get('focus', '')}) "
                    f"完成 — {data.get('main_count', 0)} 个主项",
                )

    consumer = asyncio.create_task(consume_events())

    try:
        req = request

        # ── 1. 创建 Macrocycle ──
        await store.add_log(task_id, "init", "🎯 创建大周期...", 3)
        macrocycle = Macrocycle(goal=req.goal, status="active")
        db.add(macrocycle)
        db.flush()

        # ── 2. 创建第一个 Mesocycle ──
        await store.add_log(task_id, "init", "📋 创建中周期...", 5)
        first_phase = "foundational"
        if req.experience_level in ("中级", "高级"):
            first_phase = "hypertrophy"
        mesocycle = Mesocycle(
            macrocycle_id=macrocycle.id,
            phase=first_phase,
            week_count=4,
            sort_order=1,
            status="active",
        )
        db.add(mesocycle)
        db.flush()

        # ── 3. 创建/更新 UserCurrentState ──
        ucs = db.query(UserCurrentState).first()
        if not ucs:
            ucs = UserCurrentState(
                experience_level=req.experience_level,
                workout_location=req.workout_location,
                days_per_week=req.days_per_week,
                preferred_days=req.preferred_days,
                current_mesocycle_id=mesocycle.id,
            )
            db.add(ucs)
        else:
            ucs.experience_level = req.experience_level
            ucs.workout_location = req.workout_location
            ucs.days_per_week = req.days_per_week
            ucs.preferred_days = req.preferred_days
            ucs.current_mesocycle_id = mesocycle.id
        db.flush()

        # ── 4. 保存用户个人信息 ──
        user_record = db.query(User).first()
        if not user_record:
            user_record = User(
                height=req.height,
                weight=req.weight,
                age=req.age,
                gender=req.gender,
                goal=req.goal,
                experience=req.experience_level,
                workout_location=req.workout_location,
                city=req.city or "",
            )
            db.add(user_record)
        else:
            if req.height is not None:
                user_record.height = req.height
            if req.weight is not None:
                user_record.weight = req.weight
            if req.age is not None:
                user_record.age = req.age
            if req.gender is not None:
                user_record.gender = req.gender
            user_record.goal = req.goal
            user_record.experience = req.experience_level
            user_record.workout_location = req.workout_location
            if req.city:
                user_record.city = req.city
        db.flush()

        # ── 5. 生成第 1 周 ──
        await store.add_log(task_id, "generate", "📡 开始生成第 1 周计划...", 15)
        user_info = {}
        if req.height is not None:
            user_info["height"] = req.height
        if req.weight is not None:
            user_info["weight"] = req.weight
        if req.age is not None:
            user_info["age"] = req.age
        if req.gender is not None:
            user_info["gender"] = req.gender

        week = await generate_init_week(
            macrocycle, mesocycle, ucs, db, event_queue,
            user_info=user_info,
            start_date=getattr(req, "start_date", None),
        )

        # ── 6. 预创建第 2~4 周骨架 ──
        try:
            from app.engine.mesocycle_manager import generate_mesocycle_skeleton
            skeleton_weeks = await generate_mesocycle_skeleton(
                mesocycle, ucs, db,
                start_date=getattr(req, "start_date", None) or week.start_date,
                event_queue=event_queue,
                start_week=2,
            )
            await store.add_log(
                task_id, "skeleton",
                f"📅 预创建了 {len(skeleton_weeks)} 周框架", 92,
            )
        except Exception as e:
            print(f"[TaskManager] 中周期框架预创建失败: {e}")

        # ── 7. 提交 ──
        db.commit()

        await store.add_log(task_id, "done", "✅ 第 1 周计划生成完成！", 100)
        t = store._tasks[task_id]
        t["status"] = "done"
        t["progress"] = 100
        t["updated_at"] = datetime.now().isoformat()
        # 不要把整个 Week ORM 对象存进去，前端会从 DB 重新读取

    except Exception as e:
        db.rollback()
        traceback.print_exc()
        t = store._tasks[task_id]
        t["status"] = "error"
        t["error"] = str(e)
        t["updated_at"] = datetime.now().isoformat()
        await store.add_log(task_id, "error", f"❌ {str(e)}")
    finally:
        await event_queue.put(("__END__", None))
        await consumer
        db.close()
