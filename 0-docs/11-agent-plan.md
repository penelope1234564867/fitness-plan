# Agent 系统实现计划

**Goal:** 用 HelloAgents 框架构建真 Agent 系统（CoachAgent/ProgrammerAgent/AnalystAgent），实现「用户画像→个性化选动作→每周自动调整」闭环

**Architecture:** 3 个 Agent（ReActAgent / PlanAndSolveAgent / ReflectionAgent）+ 1 个纯函数组装器（PlanAssembler），PlanService 直接编排

**Tech Stack:** Python FastAPI + HelloAgents + SQLAlchemy (SQLite) + wger MCP

## 全局约束

- 使用 HelloAgents 的 Agent 类，不自己造框架
- Agent = LLM + Planning + Memory + Tools
- 热身/有氧/拉伸不走 LLM，用 PlanAssembler 纯函数
- PlanService 是总协调者，Agent 是执行单元
- SSE 流式返回推理过程

---

## 架构总览

```
┌──────────────────────────────────────┐
│  wger MCP Server (独立进程)          │
│  python wger-mcp-server/server.py    │
│  端口 8100 (SSE 传输)                │
└────────────┬─────────────────────────┘
             │ MCP 协议 (HTTP + SSE)
┌────────────▼─────────────────────────┐
│  backend (FastAPI, 端口 8000)        │
│                                       │
│  WgerMCPClient ← 启动时连接 MCP      │
│       ↓                              │
│  tools.py (Agent 工具注册中心)        │
│       ↓                              │
│  ProgrammerAgent / CoachAgent / ...  │
└──────────────────────────────────────┘
```

## 文件结构

```
backend/app/
├── agents/
│   ├── __init__.py             ← 🩹 增加导出
│   ├── tools.py                ← 🆕 Agent Tool 注册中心（调 WgerMCPClient）
│   ├── coach_agent.py          ← 🆕 CoachAgent (PlanAndSolveAgent)
│   ├── programmer_agent.py     ← 🆕 ProgrammerAgent (ReActAgent)
│   ├── analyst_agent.py        ← 🆕 AnalystAgent (ReflectionAgent)
│   ├── plan_assembler.py       ← 🆕 纯函数组装每日训练
│   ├── exercise_agent.py       ← 已有
│   └── plan_agent.py           ← 🗑️ 删除
├── services/
│   ├── plan_service.py         ← 大改：Agent 编排
│   └── wger_mcp_client.py     ← 🆕 MCP 客户端（连接 wger MCP 服务器）
├── engine/                     ← 已有，基本不动
└── api/routes/
    └── fitness.py              ← 🩹 小改

wger-mcp-server/
├── wger_mcp_server.py          ← 🩹 添加 SSE 传输支持
└── run_mcp_server.py           ← 🆕 启动脚本（指定端口和传输方式）
```

---

### Task 0: wger MCP 服务器 + 客户端

**目标：** 让 wger MCP 作为独立进程运行，后端通过 MCP 协议调用它。

**方案：** MCP 服务器用 SSE 传输（HTTP 协议），后端通过 `mcp` 客户端库连接。

- [ ] **Step 0.1: 创建 MCP 服务器启动脚本**

```python
# wger-mcp-server/run_mcp_server.py
"""启动 wger MCP 服务器（SSE 模式，独立进程）。

用法: python run_mcp_server.py [--port 8100]
"""
import sys, argparse
from wger_mcp_server import mcp

def main():
    parser = argparse.ArgumentParser(description="启动 wger MCP 服务器")
    parser.add_argument("--port", type=int, default=8100, help="监听端口")
    args = parser.parse_args()

    print(f"🚀 wger MCP 服务器启动于 http://localhost:{args.port} (SSE)")
    sys.stdout.flush()

    # FastMCP SSE 模式
    mcp.run(transport="sse", port=args.port)

if __name__ == "__main__":
    main()
```

- [ ] **Step 0.2: 验证 MCP 服务器可启动**

```bash
cd wger-mcp-server
python run_mcp_server.py --port 8100 &
# 输出应为: 🚀 wger MCP 服务器启动于 http://localhost:8100 (SSE)
```

- [ ] **Step 0.3: 创建后端 MCP 客户端**

```python
# backend/app/services/wger_mcp_client.py
"""wger MCP 客户端 — 通过 MCP 协议调用 wger MCP 服务器。

用法:
    client = WgerMCPClient()
    await client.connect()
    exercises = await client.search_exercises(muscle="胸部", limit=5)
    await client.close()
"""
import json, logging
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client

logger = logging.getLogger(__name__)

MCP_SERVER_URL = "http://localhost:8100/sse"


class WgerMCPClient:
    """wger MCP 客户端，管理连接生命周期。"""

    def __init__(self, server_url: str = MCP_SERVER_URL):
        self.server_url = server_url
        self.session: ClientSession | None = None
        self._ctx = None

    async def connect(self):
        """连接到 wger MCP 服务器。"""
        logger.info(f"[WgerMCP] 连接 {self.server_url}")
        self._ctx = sse_client(url=self.server_url)
        read, write = await self._ctx.__aenter__()
        self.session = await ClientSession(read, write).__aenter__()
        await self.session.initialize()
        logger.info("[WgerMCP] 连接成功")

    async def close(self):
        """关闭连接。"""
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if self._ctx:
            await self._ctx.__aexit__(None, None, None)
            self._ctx = None
        logger.info("[WgerMCP] 已断开")

    async def search_exercises(
        self,
        muscle: int | None = None,
        query: str | None = None,
        equipment: int | None = None,
        category: int | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """搜索训练动作。"""
        if not self.session:
            raise RuntimeError("MCP 未连接，请先调用 connect()")

        args = {"limit": limit}
        if muscle is not None: args["muscle"] = muscle
        if query is not None: args["query"] = query
        if equipment is not None: args["equipment"] = equipment
        if category is not None: args["category"] = category

        result = await self.session.call_tool("wger_search_exercises", args)
        raw = result.content[0].text if result.content else "[]"
        return json.loads(raw).get("exercises", [])

    async def get_exercise_detail(self, exercise_id: int) -> dict:
        """获取动作详情。"""
        if not self.session:
            raise RuntimeError("MCP 未连接")
        result = await self.session.call_tool("wger_get_exercise_details", {"exercise_id": exercise_id})
        raw = result.content[0].text if result.content else "{}"
        return json.loads(raw)

    async def list_muscles(self) -> list[dict]:
        """列出所有肌群。"""
        if not self.session: raise RuntimeError("MCP 未连接")
        result = await self.session.call_tool("wger_list_muscles", {})
        return json.loads(result.content[0].text) if result.content else []

    async def list_equipment(self) -> list[dict]:
        """列出所有器材。"""
        if not self.session: raise RuntimeError("MCP 未连接")
        result = await self.session.call_tool("wger_list_equipment", {})
        return json.loads(result.content[0].text) if result.content else []


# ── 全局单例 ──
_mcp_client: WgerMCPClient | None = None


async def get_mcp_client() -> WgerMCPClient:
    """获取 MCP 客户端单例（懒连接）。"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = WgerMCPClient()
        await _mcp_client.connect()
    return _mcp_client


async def close_mcp_client():
    """关闭 MCP 客户端（应用关闭时调用）。"""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None
```

- [ ] **Step 0.4: 在 main.py 中注册 MCP 客户端生命周期**

```python
# backend/app/api/main.py
# 在 create_app() 附近添加：

from app.services.wger_mcp_client import get_mcp_client, close_mcp_client

@app.on_event("startup")
async def startup_mcp():
    """应用启动时连接 wger MCP 服务器。"""
    try:
        await get_mcp_client()
        logger.info("✅ wger MCP 客户端已连接")
    except Exception as e:
        logger.warning(f"⚠️ wger MCP 连接失败（服务器未启动？）: {e}")

@app.on_event("shutdown")
async def shutdown_mcp():
    """应用关闭时断开 MCP。"""
    await close_mcp_client()
    logger.info("wger MCP 客户端已断开")
```

- [ ] **Step 0.5: 验证 MCP 客户端可用**

```bash
# 启动 MCP 服务器（终端 1）
cd wger-mcp-server && python run_mcp_server.py --port 8100

# 验证客户端连接（终端 2）
cd backend && python -c "
import asyncio
from app.services.wger_mcp_client import get_mcp_client
async def test():
    c = await get_mcp_client()
    ex = await c.search_exercises(muscle=4, limit=3)  # 4=胸部
    print(f'搜索到 {len(ex)} 个动作')
    for e in ex[:3]: print(f'  - {e.get(\"name\")}')
loop = asyncio.new_event_loop()
loop.run_until_complete(test())
"
```

Expected:
```
搜索到 3 个动作
  - Bench Press
  - Dumbbell Bench Press
  - ...
```

- [ ] **Step 0.6: 更新 tools.py 改调 MCP 客户端**

```python
# backend/app/agents/tools.py — search_exercises 和 get_exercise_detail 改为调 MCP
import json
from app.services.wger_mcp_client import get_mcp_client

async def search_exercises(muscle: str, equipment: str = "", experience: str = "", limit: int = 10) -> list:
    """从 wger MCP 搜索动作。
    
    通过 MCP 协议调独立进程的 wger MCP 服务器。
    """
    client = await get_mcp_client()
    
    # 中文肌群名 → wger ID（临时映射，后续可加强）
    muscle_map = {"胸部": 4, "肩部": 2, "背部": 12, "腿部": 10,
                  "臀部": 8, "腹部": 6, "二头": 1, "三头": 5,
                  "小腿": 13, "全身": 0}
    muscle_id = None
    for k, v in muscle_map.items():
        if k in muscle:
            muscle_id = v
            break
    
    # 器材映射
    equip_map = {"哑铃": 3, "杠铃": 1, "自重": 8, "弹力带": 7,
                 "壶铃": 4, "器械": 10}
    equip_id = None
    for k, v in equip_map.items():
        if k in equipment:
            equip_id = v
            break
    
    results = await client.search_exercises(
        muscle=muscle_id,
        equipment=equip_id,
        limit=limit,
    )
    
    # 如果有经验筛选，在 Python 层过滤（MCP 不支持经验参数）
    if experience == "新手":
        results = [r for r in results if _is_beginner_friendly(r)]
    
    return results


def _is_beginner_friendly(ex: dict) -> bool:
    """判断动作是否适合新手（简单启发式）。"""
    name = (ex.get("name", "") or "").lower()
    # 排除明显不适合新手的动作
    advanced_keywords = ["snatch", "clean", "jerk", "muscle-up", "pistol",
                         "handstand", "planche", "flag", "ring"]
    for kw in advanced_keywords:
        if kw in name:
            return False
    return True


async def get_exercise_detail(wger_id: int) -> dict:
    """通过 MCP 获取动作详情。"""
    client = await get_mcp_client()
    detail = await client.get_exercise_detail(wger_id)
    return detail
```

- [ ] **Step 0.7: Commit**

```bash
git add wger-mcp-server/run_mcp_server.py backend/app/services/wger_mcp_client.py backend/app/api/main.py
git commit -m "feat: add wger MCP server (SSE) + backend MCP client

- MCP 服务器作为独立进程运行，SSE 传输
- WgerMCPClient 管理连接生命周期
- 后端启动时自动连接 MCP 服务器
- 面试展示点：MCP 协议 + 独立进程架构

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 1: tools.py — 所有 Agent 共用的工具

**Create:** `backend/app/agents/tools.py`

```python
# backend/app/agents/tools.py
import logging
from hello_agents import ToolRegistry

logger = logging.getLogger(__name__)
agent_registry = ToolRegistry()


async def search_exercises(muscle: str, equipment: str = "", experience: str = "", limit: int = 10) -> list:
    """从 wger 搜索动作。"""
    from app.services.wger_service import search_by_criteria
    return await search_by_criteria(muscle=muscle, equipment=equipment, experience=experience, limit=limit)


async def get_exercise_detail(wger_id: int) -> dict:
    """获取动作详情。"""
    from app.services.wger_service import fetch_exercise_detail
    return await fetch_exercise_detail(wger_id)


def save_week_plan(week_data: dict) -> dict:
    """保存周计划到数据库。"""
    from app.database import SessionLocal
    from app.models.orm_models import Week, Day, ExerciseSlot, Mesocycle
    db = SessionLocal()
    try:
        meso = db.query(Mesocycle).filter(Mesocycle.id == week_data["mesocycle_id"]).first()
        if not meso:
            raise ValueError(f"Mesocycle {week_data['mesocycle_id']} 不存在")
        week = Week(mesocycle_id=meso.id, week_number=week_data["week_number"], status="active")
        db.add(week); db.flush()
        day_ids = []
        for idx, dd in enumerate(week_data.get("days", [])):
            day = Day(week_id=week.id, day_order=idx+1, day_of_week=idx+1, day_label=dd.get("day_label",""), focus=dd.get("focus",""))
            db.add(day); db.flush(); day_ids.append(day.id)
            for si, sd in enumerate(dd.get("slots", [])):
                db.add(ExerciseSlot(day_id=day.id, phase_type=sd.get("phase_type","main"), sort_order=si+1,
                    wger_id=sd.get("wger_id"), exercise_name=sd.get("exercise_name",""),
                    target_sets=sd.get("target_sets",3), target_reps=sd.get("target_reps",10),
                    weight_kg=sd.get("weight_kg",0), weight_suggestion=sd.get("reasoning",""),
                    rest_seconds=sd.get("rest_seconds",60), coach_note=sd.get("coach_note","")))
        db.commit()
        return {"week_id": week.id, "day_ids": day_ids, "status": "ok"}
    except: db.rollback(); raise
    finally: db.close()


def get_checkin_data(week_id: int) -> dict:
    """读取一周打卡数据。"""
    from app.database import SessionLocal
    from app.models.orm_models import Week, Day, ExerciseSlot
    db = SessionLocal()
    try:
        week = db.query(Week).filter(Week.id == week_id).first()
        if not week: return {"days": []}
        days_data = []
        for day in db.query(Day).filter(Day.week_id == week_id).order_by(Day.day_order).all():
            slots = db.query(ExerciseSlot).filter(ExerciseSlot.day_id == day.id).order_by(ExerciseSlot.sort_order).all()
            days_data.append({"day_id": day.id, "date": str(day.date or ""), "day_label": day.day_label or "",
                "is_completed": bool(day.is_completed), "rpe_score": day.rpe_score,
                "slots": [{"exercise_name": s.exercise_name, "target_sets": s.target_sets,
                    "actual_sets": s.actual_sets, "target_reps": s.target_reps, "actual_reps": s.actual_reps,
                    "actual_weight_kg": s.actual_weight_kg, "rpe": s.rpe, "phase_type": s.phase_type} for s in slots]})
        return {"week_id": week_id, "week_number": week.week_number, "days": days_data}
    finally: db.close()


def get_historical_trend(user_id: int = 1) -> dict:
    """获取历史趋势。"""
    from app.database import SessionLocal
    from app.models.orm_models import Week, Day, Mesocycle, Macrocycle
    db = SessionLocal()
    try:
        macro = db.query(Macrocycle).filter(Macrocycle.status == "active").order_by(Macrocycle.id.desc()).first()
        if not macro: return {"weeks": []}
        meso_ids = [m.id for m in db.query(Mesocycle).filter(Mesocycle.macrocycle_id == macro.id).all()]
        weeks_data = []
        for w in db.query(Week).filter(Week.mesocycle_id.in_(meso_ids)).order_by(Week.week_number).all():
            days = db.query(Day).filter(Day.week_id == w.id).all()
            total = len(days) or 1
            completed = sum(1 for d in days if d.is_completed)
            rpes = [d.rpe_score for d in days if d.rpe_score]
            weeks_data.append({"week_number": w.week_number, "completion_rate": round(completed/total, 2),
                "avg_rpe": round(sum(rpes)/len(rpes), 1) if rpes else 0,
                "completed_days": completed, "total_days": len(days)})
        return {"weeks": weeks_data}
    finally: db.close()


def register_all_tools():
    agent_registry.register("search_exercises", search_exercises, "从 wger 搜索动作")
    agent_registry.register("get_exercise_detail", get_exercise_detail, "获取动作详情")
    agent_registry.register("save_week_plan", save_week_plan, "保存周计划到数据库")
    agent_registry.register("get_checkin_data", get_checkin_data, "读取一周打卡数据")
    agent_registry.register("get_historical_trend", get_historical_trend, "获取历史趋势数据")
    return agent_registry
```

**验证:** `cd backend && python -c "from app.agents.tools import register_all_tools; r=register_all_tools(); print(f'OK: {len(r.list_tools())} tools')"`

---

### Task 2: plan_assembler.py — 纯函数训练组装器

**Create:** `backend/app/agents/plan_assembler.py`

纯函数，从原 plan_agent.py 提取，去除所有 LLM 调用。

```python
# backend/app/agents/plan_assembler.py
from typing import Optional

DYNAMIC_WARMUP = {
    "开合跳": {"sets": 2, "reps": 15, "instruction": "手脚同步打开再收回"},
    "肩部环绕": {"sets": 1, "reps": 10, "instruction": "向前向后各绕 10 圈"},
    "高抬腿": {"sets": 2, "reps": 15, "instruction": "膝盖抬高至腰部"},
    "弓步转体": {"sets": 1, "reps": 8, "instruction": "前腿弓步同时上半身向同侧转"},
    "侧弓步": {"sets": 1, "reps": 8, "instruction": "向侧方迈步屈膝"},
    "抱膝提踵": {"sets": 1, "reps": 8, "instruction": "单腿抱膝上提"},
    "后踢腿": {"sets": 2, "reps": 15, "instruction": "脚跟尽量踢到臀部"},
    "手腕脚踝活动": {"sets": 1, "reps": 10, "instruction": "转动手腕和脚踝"},
    "胯下击掌": {"sets": 2, "reps": 15, "instruction": "抬腿至胯高，双手在大腿下击掌"},
}

WARMUP_BY_FOCUS = {
    "推": {"prior": ["肩部环绕", "手腕脚踝活动"], "general": ["开合跳", "高抬腿", "胯下击掌", "后踢腿"], "dynamic": ["弓步转体", "侧弓步", "抱膝提踵"]},
    "拉": {"prior": ["肩部环绕", "抱膝提踵"], "general": ["开合跳", "高抬腿", "胯下击掌", "后踢腿"], "dynamic": ["弓步转体", "侧弓步", "手腕脚踝活动"]},
    "腿": {"prior": ["高抬腿", "后踢腿", "弓步转体", "侧弓步"], "general": ["开合跳", "胯下击掌", "肩部环绕"], "dynamic": ["抱膝提踵", "手腕脚踝活动"]},
    "default": {"prior": ["开合跳", "肩部环绕", "高抬腿", "弓步转体"], "general": ["胯下击掌", "后踢腿"], "dynamic": ["侧弓步", "抱膝提踵", "手腕脚踝活动"]},
}

CARDIO_OPTIONS = {
    "减脂": {"name": "慢跑", "duration": 20, "intensity": "中等", "suggestion": "跑步机慢跑 20 分钟"},
    "增肌": {"name": "爬坡快走", "duration": 10, "intensity": "低", "suggestion": "跑步机坡度 8-12，10 分钟"},
    "塑形": {"name": "椭圆机", "duration": 15, "intensity": "中等", "suggestion": "椭圆机 15 分钟"},
    "保持健康": {"name": "慢走", "duration": 10, "intensity": "低", "suggestion": "慢走 10 分钟"},
}
CARDIO_OPTIONAL_GOALS = ["增肌", "保持健康"]

MUSCLE_STRETCHES = {
    "胸部": [{"name": "门框胸大肌拉伸", "instruction": "单手扶门框，身体前倾，保持 20 秒"}],
    "肩部": [{"name": "交叉臂肩部拉伸", "instruction": "手臂水平交叉胸前，保持 20 秒"}],
    "肱三头肌": [{"name": "三头肌颈后拉伸", "instruction": "举手过顶屈肘，轻拉肘部，保持 20 秒"}],
    "背部": [{"name": "婴儿式背部拉伸", "instruction": "跪姿双手前伸，臀部坐脚跟，保持 20 秒"}],
    "肱二头肌": [{"name": "二头肌拉伸", "instruction": "手臂侧平举掌心向上，轻压手指向后，保持 15 秒"}],
    "股四头肌": [{"name": "站立股四头肌拉伸", "instruction": "单腿站立，手握脚踝拉向臀部，保持 20 秒"}],
    "腘绳肌": [{"name": "坐姿腘绳肌拉伸", "instruction": "坐姿一腿伸直，身体前倾，保持 20 秒"}],
    "臀部": [{"name": "坐姿 4 字拉伸", "instruction": "坐姿一脚踝放另一膝上，身体前倾，保持 20 秒"}],
    "腹部": [{"name": "眼镜蛇式腹部拉伸", "instruction": "俯卧双手撑地推起上半身，保持 15 秒"}],
}

def assemble_one_day(day_label: str, focus: str, main_exercises: list, goal: str) -> dict:
    return {
        "day_label": day_label, "focus": focus,
        "warmup": _select_warmup(day_label),
        "main": main_exercises,
        "cardio": _select_cardio(goal),
        "stretch": _select_stretches(focus),
    }

def _select_warmup(day_label: str) -> list:
    focus_key = next((kw for kw in WARMUP_BY_FOCUS if kw in day_label), "default")
    plan = WARMUP_BY_FOCUS.get(focus_key, WARMUP_BY_FOCUS["default"])
    result, seen = [], set()
    for cat in ["prior", "general", "dynamic"]:
        for name in plan.get(cat, []):
            if name not in seen and name in DYNAMIC_WARMUP:
                seen.add(name)
                result.append({"name": name, **DYNAMIC_WARMUP[name], "phase_type": "warmup"})
    return result

def _select_cardio(goal: str) -> Optional[dict]:
    if goal in CARDIO_OPTIONAL_GOALS: return None
    c = CARDIO_OPTIONS.get(goal)
    return {**c, "phase_type": "cardio"} if c else None

def _select_stretches(focus: str) -> list:
    result, seen = [], set()
    for part in focus.replace("＋","+").replace("+"," ").split():
        for mname, ms in MUSCLE_STRETCHES.items():
            if mname in part:
                for s in ms:
                    if s["name"] not in seen:
                        seen.add(s["name"]); result.append({**s, "phase_type": "stretch"})
    return result
```

---

### Task 3: CoachAgent — 用户画像 + 教练备注

**Create:** `backend/app/agents/coach_agent.py`

Agent 类型：PlanAndSolveAgent。记忆：SemanticMemory + WorkingMemory。无工具。

```python
# backend/app/agents/coach_agent.py
import json, logging
from hello_agents import PlanAndSolveAgent
from hello_agents.memory import SemanticMemory, WorkingMemory, MemoryConfig
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

class CoachAgent:
    def __init__(self):
        self.llm = get_llm()
        self.semantic_memory = SemanticMemory(MemoryConfig(capacity=100, namespace="coach_semantic"))
        self.working_memory = WorkingMemory(MemoryConfig(capacity=20, namespace="coach_working"))

    async def analyze_user(self, raw_data: dict) -> dict:
        agent = PlanAndSolveAgent(name="coach_analyzer", llm=self.llm,
            system_prompt="分析用户资料输出结构化JSON画像。维度：经验、器械、限制、训练建议。")
        result = await agent.run(f"用户资料：{json.dumps(raw_data, ensure_ascii=False)}")
        profile = self._extract_json(result)
        self.semantic_memory.save({"type": "user_profile", "data": profile})
        self.working_memory.save({"current_user_profile": profile})
        return profile

    async def add_reasoning(self, day_plan: dict, profile: dict) -> dict:
        agent = PlanAndSolveAgent(name="coach_reasoning", llm=self.llm,
            system_prompt="为每个主项动作写教练备注。JSON格式：{\"main\":[{\"name\":str,\"coach_note\":str}]}")
        result = await agent.run(f"画像：{json.dumps(profile, ensure_ascii=False)}\n计划：{json.dumps(day_plan.get('main',[]), ensure_ascii=False)}")
        notes = self._extract_json(result).get("main", [])
        note_map = {n.get("name"): n.get("coach_note", "") for n in notes}
        for ex in day_plan.get("main", []):
            ex["coach_note"] = note_map.get(ex.get("name", ""), "")
        return day_plan

    async def generate_week_summary(self, analyst_report: dict) -> str:
        agent = PlanAndSolveAgent(name="coach_summary", llm=self.llm,
            system_prompt="写周总结，鼓励+具体+建设性。")
        return await agent.run(f"本周数据：{json.dumps(analyst_report, ensure_ascii=False)}")

    async def generate_phase_description(self, phase: str, goal: str) -> str:
        agent = PlanAndSolveAgent(name="coach_phase", llm=self.llm,
            system_prompt="用2-3句话解释训练阶段的意义。")
        desc = await agent.run(f"阶段：{phase}，目标：{goal}")
        self.semantic_memory.save({"type": "phase_description", "phase": phase, "description": desc})
        return desc

    def _extract_json(self, text: str) -> dict:
        text = text.strip()
        if "```" in text: text = text.split("```")[-2] if text.count("```")>=2 else text
        s, e = text.find("{"), text.rfind("}")
        if s>=0 and e>=0: text = text[s:e+1]
        try: return json.loads(text)
        except: return {}
```

---

### Task 4: ProgrammerAgent — 计划编排 Agent

**Create:** `backend/app/agents/programmer_agent.py`

Agent 类型：ReActAgent。记忆：WorkingMemory + EpisodicMemory。工具：search_exercises, get_exercise_detail, save_week_plan

```python
# backend/app/agents/programmer_agent.py
import json, logging
from hello_agents import ReActAgent
from hello_agents.memory import WorkingMemory, EpisodicMemory, MemoryConfig
from app.services.llm_service import get_llm
from app.agents.tools import agent_registry
from app.agents.plan_assembler import assemble_one_day

logger = logging.getLogger(__name__)

PPL = {
    3: [{"day_label":"推日","focus":"胸部+肩部+三头"},{"day_label":"拉日","focus":"背部+二头"},{"day_label":"腿日","focus":"腿部+臀部+腹部"}],
    4: [{"day_label":"推日","focus":"胸部+肩部+三头"},{"day_label":"拉日","focus":"背部+二头"},{"day_label":"腿日","focus":"腿部+臀部"},{"day_label":"全身日","focus":"全身+腹部"}],
    5: [{"day_label":"推日(主)","focus":"胸部+肩部+三头"},{"day_label":"拉日(主)","focus":"背部+二头"},{"day_label":"腿日","focus":"腿部+臀部+腹部"},{"day_label":"推日(辅)","focus":"肩部+三头"},{"day_label":"拉日(辅)","focus":"二头+背部"}],
    6: [{"day_label":"推日(重)","focus":"胸部+肩部+三头"},{"day_label":"拉日(重)","focus":"背部+二头"},{"day_label":"腿日(重)","focus":"腿部+臀部"},{"day_label":"推日(轻)","focus":"胸部+肩部+三头"},{"day_label":"拉日(轻)","focus":"背部+二头"},{"day_label":"腿日(轻)","focus":"腿部+腹部"}],
}

class ProgrammerAgent:
    def __init__(self):
        self.llm = get_llm()
        self.working_memory = WorkingMemory(MemoryConfig(capacity=20, namespace="prog_working"))
        self.episodic_memory = EpisodicMemory(MemoryConfig(capacity=50, namespace="prog_episodic"))

    async def generate_initial_week(self, profile: dict, days_per_week: int) -> dict:
        days_spec = PPL.get(days_per_week, PPL[3])
        agent = ReActAgent(name="programmer_init", llm=self.llm, tool_registry=agent_registry,
            system_prompt="""你是健身计划编排师。步骤：1.理解用户画像 2.对每个训练日搜合适动作 3.定组次数。组次数：新手3×10-12，中级3-4×8-12，高级4-5×6-12。输出JSON：{"reasoning":"说明","days":[{"day_label":"","focus":"","main":[{"name":"","wger_id":0,"target_sets":3,"target_reps":10,"rest_seconds":60,"reasoning":""}]}]}""",
            max_steps=15)
        result = await agent.run(f"画像：{json.dumps(profile, ensure_ascii=False)}\n方案：{json.dumps(days_spec, ensure_ascii=False)}")
        ao = self._extract_json(result)
        week_data = {"days": [], "week_number": 1}
        for d in ao.get("days", []):
            week_data["days"].append(assemble_one_day(d["day_label"], d["focus"], d.get("main",[]), profile.get("goal","增肌")))
        self.working_memory.save({"last_week": 1})
        return {"week_data": week_data, "reasoning": ao.get("reasoning","")}

    async def generate_next_week(self, prev_plan: dict, report: dict, profile: dict) -> dict:
        agent = ReActAgent(name="programmer_next", llm=self.llm, tool_registry=agent_registry,
            system_prompt="基于前一周生成下一周。规则：完成率≥90%加量，70-90%保持，<70%减量。RPE持续高减载。", max_steps=10)
        result = await agent.run(f"画像：{json.dumps(profile)}\n前一周：{json.dumps(prev_plan)}\n分析：{json.dumps(report)}")
        ao = self._extract_json(result)
        wn = (prev_plan.get("week_number",0) or 0) + 1
        wd = {"days":[], "week_number": wn}
        for d in ao.get("days",[]):
            wd["days"].append(assemble_one_day(d["day_label"], d["focus"], d.get("main",[]), profile.get("goal","增肌")))
        return {"week_data": wd, "reasoning": ao.get("reasoning","")}

    def _extract_json(self, text):
        text = text.strip()
        if "```" in text: text = text.split("```")[-2] if text.count("```")>=2 else text
        s, e = text.find("{"), text.rfind("}")
        if s>=0 and e>=0: text = text[s:e+1]
        try: return json.loads(text)
        except: return {"days":[]}
```

---

### Task 5: AnalystAgent — 打卡分析 Agent

**Create:** `backend/app/agents/analyst_agent.py`

Agent 类型：ReflectionAgent。记忆：EpisodicMemory。工具：get_checkin_data, get_historical_trend

```python
# backend/app/agents/analyst_agent.py
import json, logging
from hello_agents import ReflectionAgent
from hello_agents.memory import EpisodicMemory, MemoryConfig
from app.services.llm_service import get_fast_llm
from app.agents.tools import agent_registry

logger = logging.getLogger(__name__)

class AnalystAgent:
    def __init__(self):
        self.llm = get_fast_llm()
        self.episodic_memory = EpisodicMemory(MemoryConfig(capacity=50, namespace="analyst_episodic"))

    async def analyze_week(self, week_id: int) -> dict:
        data = agent_registry.execute("get_checkin_data", week_id=week_id)
        trend = agent_registry.execute("get_historical_trend", user_id=1)
        if not data.get("days"):
            return {"completion_rate":0, "suggestion":"no_data", "detail":"无打卡数据"}
        agent = ReflectionAgent(name="analyst", llm=self.llm, max_iterations=2,
            system_prompt="""分析一周打卡。建议：progressive_overload(≥90%)/maintain(70-90%)/deload(<70%或RPE高)/swap_exercises。
输出JSON：{"completion_rate":float,"avg_rpe":float,"rpe_trend":"","needs_deload":bool,"suggestion":"","detail":"","swap_candidates":[]}""")
        result = await agent.run(f"本周：{json.dumps(data)}\n历史：{json.dumps(trend)}")
        report = self._extract_json(result)
        report["week_number"] = data.get("week_number", 0)
        self.episodic_memory.save({"type":"weekly_analysis","week_number":report["week_number"],"report":report})
        return report

    def _extract_json(self, text):
        text = text.strip()
        if "```" in text: text = text.split("```")[-2] if text.count("```")>=2 else text
        s, e = text.find("{"), text.rfind("}")
        if s>=0 and e>=0: text = text[s:e+1]
        try: return json.loads(text)
        except: return {"completion_rate":0, "suggestion":"unknown"}
```

---

### Task 6: PlanService — Agent 编排总指挥 + fitness.py 改造

**Modify:** `backend/app/services/plan_service.py` + `backend/app/api/routes/fitness.py`

```python
# backend/app/services/plan_service.py
import json, asyncio, logging
from app.agents import CoachAgent, ProgrammerAgent, AnalystAgent
from app.agents.tools import register_all_tools
from app.models import orm_models

logger = logging.getLogger(__name__)
register_all_tools()


async def generate_plan(req, db, event_queue: asyncio.Queue):
    """Agent 编排生成计划。SSE 流式。"""
    coach = CoachAgent()
    programmer = ProgrammerAgent()

    try:
        # Step 1: CoachAgent 画像
        await event_queue.put(("progress", {"agent":"coach","step":"analyzing","text":"🤔 正在分析你的个人情况..."}))
        raw = {"height":req.height,"weight":req.weight,"age":req.age,"gender":req.gender,"goal":req.goal,
               "experience_level":req.experience_level,"workout_location":req.workout_location,"days_per_week":req.days_per_week}
        profile = await coach.analyze_user(raw)
        await event_queue.put(("progress", {"agent":"coach","step":"profile_done","text":f"📋 {profile.get('summary','')}"}))

        # Step 2: ProgrammerAgent 生成
        await event_queue.put(("progress", {"agent":"programmer","step":"searching","text":"🔍 正在从动作库筛选最适合你的动作..."}))
        result = await programmer.generate_initial_week(profile, req.days_per_week)
        if result.get("reasoning"):
            await event_queue.put(("reasoning", {"agent":"programmer","content":result["reasoning"]}))
        week_data = result["week_data"]
        await event_queue.put(("progress", {"agent":"programmer","step":"plan_ready","text":f"📅 第1周编排完成：{len(week_data['days'])}个训练日"}))

        # Step 3: CoachAgent 备注
        await event_queue.put(("progress", {"agent":"coach","step":"adding_notes","text":"💬 正在为每个动作写教练指导..."}))
        for i, day in enumerate(week_data.get("days",[])):
            week_data["days"][i] = await coach.add_reasoning(day, profile)
            await event_queue.put(("day_done", {"day":i+1,"focus":day.get("focus",""),"main_count":len(day.get("main",[]))}))

        # Step 4: 保存
        from app.agents.tools import agent_registry
        save_r = agent_registry.execute("save_week_plan", week_data={
            "mesocycle_id": req.mesocycle_id, "week_number": 1,
            "days": [_day_to_slots(d) for d in week_data.get("days",[])]})
        await event_queue.put(("progress", {"agent":"system","step":"saved","text":f"✅ 已保存 (Week#{save_r['week_id']})"}))

        # Step 5: 构建响应
        from app.engine.generator import _build_week_response as bwr
        week_db = db.query(orm_models.Week).filter(orm_models.Week.id == save_r["week_id"]).first()
        response = bwr(week_db, db) if week_db else {}
        mc = db.query(orm_models.Macrocycle).filter(orm_models.Macrocycle.status=="active").first()
        md = _build_macrocycle_detail(mc, db) if mc else {}
        await event_queue.put(("macrocycle_detail", md))
        await event_queue.put(("__DONE__", response))
    except Exception as e:
        logger.exception("[PlanService] 失败")
        await event_queue.put(("error", {"text":f"生成失败: {str(e)}"}))
    finally:
        await event_queue.put(("__END__", None))


def _day_to_slots(day: dict) -> dict:
    slots = []
    for w in day.get("warmup",[]):
        slots.append({"phase_type":"warmup","exercise_name":w["name"],"target_sets":w.get("sets",1),"target_reps":w.get("reps",10),"reasoning":w.get("instruction","")})
    for m in day.get("main",[]):
        slots.append({"phase_type":"main","wger_id":m.get("wger_id"),"exercise_name":m.get("name",""),
            "target_sets":m.get("target_sets",3),"target_reps":m.get("target_reps",10),
            "weight_kg":m.get("weight_kg",0),"rest_seconds":m.get("rest_seconds",60),
            "coach_note":m.get("coach_note",""),"reasoning":m.get("reasoning","")})
    c = day.get("cardio")
    if c: slots.append({"phase_type":"cardio","exercise_name":c["name"],"target_sets":1,"target_reps":c.get("duration_minutes",15),"coach_note":c.get("suggestion","")})
    for s in day.get("stretch",[]):
        slots.append({"phase_type":"stretch","exercise_name":s["name"],"target_sets":1,"target_reps":1,"coach_note":s.get("instruction","")})
    return {"day_label":day.get("day_label",""),"focus":day.get("focus",""),"slots":slots}


def _build_macrocycle_detail(mc, db) -> dict:
    from app.models.orm_models import Mesocycle, Week, Day
    mesos = db.query(Mesocycle).filter(Mesocycle.macrocycle_id==mc.id).order_by(Mesocycle.sort_order).all()
    existing = {ms.phase: ms for ms in mesos}
    meso_data = []
    for idx, phase in enumerate(["foundational","hypertrophy","strength","deload"]):
        if phase in existing:
            ms = existing[phase]; weeks_data = []
            for w in db.query(Week).filter(Week.mesocycle_id==ms.id).order_by(Week.week_number).all():
                days = db.query(Day).filter(Day.week_id==w.id).all()
                comp = sum(1 for d in days if d.is_completed)
                weeks_data.append({"id": w.id, "week_number": w.week_number, "status": w.status,
                    "day_count": len(days), "completed_days": comp, "completion_rate": round(comp/(len(days) or 1)*100)})
            aw = [w for w in weeks_data if w["status"]!="pending"]
            meso_data.append({"id": ms.id, "phase": ms.phase, "week_count": ms.week_count,
                "sort_order": ms.sort_order, "status": ms.status,
                "completion_rate": round(sum(w["completion_rate"] for w in aw)/len(aw)) if aw else 0, "weeks": weeks_data})
        else:
            meso_data.append({"id": -(idx+1), "phase": phase, "week_count": 4, "sort_order": idx+1, "status": "pending", "completion_rate": 0, "weeks": []})
    return {"id": mc.id, "goal": mc.goal, "status": mc.status, "mesocycles": meso_data}


async def on_checkin(day_id: int):
    """打卡后触发。一周全完成→启动分析+生成下周。"""
    from app.database import SessionLocal
    from app.models.orm_models import Day, Week
    db = SessionLocal()
    try:
        day = db.query(Day).filter(Day.id==day_id).first()
        if not day: return
        week = db.query(Week).filter(Week.id==day.week_id).first()
        if not week: return
        all_done = all(d.is_completed for d in db.query(Day).filter(Day.week_id==week.id).all())
        if not all_done: return
        logger.info(f"Week#{week.id} 全部完成，启动分析")
        asyncio.create_task(_run_weekly_cycle(week.id))
    finally: db.close()


async def _run_weekly_cycle(week_id: int):
    analyst = AnalystAgent(); programmer = ProgrammerAgent(); coach = CoachAgent()
    report = await analyst.analyze_week(week_id)
    await coach.generate_week_summary(report)
    if report.get("suggestion") in ("progressive_overload","maintain"):
        from app.agents.tools import agent_registry
        prev = agent_registry.execute("get_checkin_data", week_id=week_id)
        profile = {}
        try:
            pd = coach.semantic_memory.query("user_profile", limit=1)
            if pd: profile = pd[0].get("data", {})
        except: pass
        nw = await programmer.generate_next_week(prev, report, profile)
        from app.database import SessionLocal
        from app.models.orm_models import Mesocycle
        db = SessionLocal()
        try:
            meso = db.query(Mesocycle).filter(Mesocycle.status=="active").first()
            if meso:
                agent_registry.execute("save_week_plan", week_data={
                    "mesocycle_id": meso.id, "week_number": nw["week_data"]["week_number"],
                    "days": [_day_to_slots(d) for d in nw["week_data"].get("days",[])]})
                logger.info("下一周已自动生成")
        finally: db.close()
    logger.info(f"每周循环完成: {report.get('suggestion','?')}")
```

**fitness.py 修改：**

在 checkin 接口的 `db.commit()` 之后添加：
```python
from app.services.plan_service import on_checkin as plan_on_checkin
asyncio.create_task(plan_on_checkin(data.day_id))
```

在 init_plan 接口中（创建完 mesocycle 后），用 PlanService 替代直接调 generator：
```python
req.mesocycle_id = mesocycle.id
from app.services.plan_service import generate_plan as agent_generate_plan
await agent_generate_plan(req, db, event_queue)
# 跳过原有 generator.generate_init_week 调用
```

---

### Task 7: 前端适配 — SSE 推理过程展示

**Modify:** `frontend/src/views/GeneratingPlan.vue`

在 `<script>` 中添加：
```typescript
const reasoningSteps = ref<Array<{agent: string, content: string}>>([])

// 在 SSE 事件处理中：
if (eventType === 'reasoning') {
  reasoningSteps.value.push({
    agent: data.agent || 'system',
    content: data.content || '',
  })
}
```

在 `<template>` 中添加推理展示区域：
```vue
<div v-if="reasoningSteps.length" style="margin-top:16px;padding:12px;background:#f5f5f5;border-radius:12px;max-height:200px;overflow-y:auto">
  <div v-for="(step, i) in reasoningSteps" :key="i" style="padding:6px 8px;border-left:3px solid #f97316;margin-bottom:6px;background:#fff;border-radius:0 8px 8px 0;font-size:13px">
    <span style="color:#f97316;font-weight:600;font-size:11px">{{ step.agent }}</span>
    <p style="margin:2px 0 0;color:#555">{{ step.content }}</p>
  </div>
</div>
```

---

### Task 8: 清理旧代码

**Delete:** `backend/app/agents/plan_agent.py`

```bash
cd backend && grep -r "plan_agent" app/ --include="*.py" | grep -v __pycache__ || echo "无引用"
git rm app/agents/plan_agent.py
git commit -m "refactor: remove deprecated plan_agent.py"
```

---

### 更新 `__init__.py`

```python
# backend/app/agents/__init__.py
from app.agents.coach_agent import CoachAgent
from app.agents.programmer_agent import ProgrammerAgent
from app.agents.analyst_agent import AnalystAgent
```

---

## 执行顺序

1. **Task 1** (tools.py) — 基础依赖
2. **Task 2** (plan_assembler.py) — 可并行
3. **Task 3** (CoachAgent) — 依赖 Task 1
4. **Task 4** (ProgrammerAgent) — 依赖 Task 1+2
5. **Task 5** (AnalystAgent) — 依赖 Task 1
6. **Task 6** (PlanService + fitness.py) — 依赖 3/4/5
7. **Task 7** (前端) — 可并行
8. **Task 8** (清理) — 最后
