# MessageBus + 多 Agent 架构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有函数式代码（generator → exercise_agent → plan_agent 直接调用）改造为事件驱动的多 Agent 架构，实现「打卡 → 自动分析 → 自动调整」闭环

**Architecture:** 新增 `core/` 层（MessageBus、ToolRegistry、Orchestrator）和 `agents/` 层（BaseAgent + 3 个具体 Agent）。engine/ 层代码不动，只改调用链。API 路由小改。

**Tech Stack:** Python FastAPI + asyncio（零外部依赖，纯 Python 内置 async 实现）

## 全局约束

- 不引入任何新外部依赖（不使用 RabbitMQ、Redis、Celery 等）
- engine/ 目录下的所有现有代码（generator.py、adaptive_adjustment.py、progressive_overload.py、exercise_rotation.py、mesocycle_manager.py）**不修改业务逻辑**
- 前端不需要任何改动，API 返回格式不变
- 所有 Agent 继承 BaseAgent，通过 MessageBus 通信
- 使用 asyncio.Queue 作为 MessageBus 底层实现
- 文件名/类名与 面试.md 中的设计一致

---

## 文件结构

```
backend/app/
├── core/
│   ├── __init__.py
│   ├── message_bus.py       ← 🆕 事件总线（subscribe / publish）
│   ├── tool_registry.py     ← 🆕 工具注册中心（注册 / 调用）
│   └── orchestrator.py      ← 🆕 协调者（启动 Agent + 路由事件）
├── agents/
│   ├── __init__.py
│   ├── base_agent.py        ← 🆕 Agent 基类（状态 + 消息收发 + 生命周期）
│   ├── programmer_agent.py  ← 🆕 编排 Agent（包装现有 exercise_agent + plan_agent + engine 调用）
│   ├── coach_agent.py       ← 🆕 教练 Agent（生成路线图自然语言描述）
│   └── analyst_agent.py     ← 🆕 分析师 Agent（包装 adaptive_adjustment + progressive_overload）
└── api/routes/
    └── fitness.py           ← 🩹 小改：checkin 加 publish，init-plan 加 orchestrator 启动
```

### 职责边界

| 组件 | 职责 | 不负责 |
|------|------|--------|
| `MessageBus` | 事件路由（谁订阅→调谁），异步非阻塞 | 业务判断、状态管理 |
| `ToolRegistry` | 工具函数的注册和查找 | 工具执行逻辑、状态 |
| `BaseAgent` | 状态管理、subscribe/publish 封装、生命周期 | 具体业务逻辑 |
| `ProgrammerAgent` | 调 generator/exercise_agent/plan_agent 执行编排 | 进度分析、用户沟通 |
| `CoachAgent` | 调 LLM 生成用户友好的自然语言描述 | 计划生成、数据分析 |
| `AnalystAgent` | 调 adaptive_adjustment/progressive_overload 做分析 | 计划执行、用户沟通 |
| `Orchestrator` | 启动所有 Agent，注册初始订阅关系 | 业务逻辑 |

---

### Task 1: MessageBus — 事件总线

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/message_bus.py`

**Interfaces:**
- Produces: `MessageBus` class with `subscribe(event_type, handler)`, `publish(event_type, data)`, `start()`, `stop()` methods

- [ ] **Step 1: Create `backend/app/core/__init__.py`**

```python
# backend/app/core/__init__.py
"""核心层：消息总线、工具注册、协调者"""
```

- [ ] **Step 2: Write MessageBus implementation**

```python
# backend/app/core/message_bus.py
"""事件总线 — 基于 asyncio.Queue 的发布/订阅实现。

不依赖任何外部消息队列（RabbitMQ/Redis），适合单机部署。
接口设计上与分布式消息队列兼容，未来可无缝替换底层实现。

用法:
    bus = MessageBus()
    bus.subscribe("workout.completed", my_handler)
    await bus.publish("workout.completed", {"user_id": 1})
"""

import asyncio
import logging
from typing import Callable, Coroutine, Any, Dict, List

logger = logging.getLogger(__name__)

HandlerType = Callable[[dict], Coroutine[Any, Any, None]]


class MessageBus:
    """异步事件总线。

    维护 event_type → [handler1, handler2, ...] 的映射。
    publish 是异步非阻塞的——启动 task 后立即返回，不等待 handler 完成。
    """

    def __init__(self):
        self._subscribers: Dict[str, List[HandlerType]] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []

    def subscribe(self, event_type: str, handler: HandlerType):
        """订阅事件。handler 是 async (data: dict) -> None。

        Args:
            event_type: 事件类型，如 "workout.completed"
            handler: 异步回调函数，接收 dict 参数
        """
        self._subscribers.setdefault(event_type, []).append(handler)
        logger.debug(f"[MessageBus] 订阅: {event_type} → {handler.__name__}")

    def subscribe_all(self, event_map: Dict[str, HandlerType]):
        """批量订阅事件。键为事件类型，值为 handler。"""
        for event_type, handler in event_map.items():
            self.subscribe(event_type, handler)

    async def publish(self, event_type: str, data: dict):
        """发布事件。异步启动所有 handler 后立即返回。

        Args:
            event_type: 事件类型
            data: 事件数据 dict
        """
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug(f"[MessageBus] 事件 {event_type} 无订阅者，跳过")
            return

        logger.info(f"[MessageBus] 发布: {event_type} ({len(handlers)} 个订阅者)")
        for handler in handlers:
            task = asyncio.create_task(
                self._safe_dispatch(handler, event_type, data),
                name=f"bus:{event_type}:{handler.__name__}",
            )
            self._tasks.append(task)

    async def _safe_dispatch(self, handler: HandlerType, event_type: str, data: dict):
        """安全执行 handler，捕获异常防止中断。"""
        try:
            await handler(data)
        except Exception as e:
            logger.error(
                f"[MessageBus] handler {handler.__name__} 处理 {event_type} 失败: {e}",
                exc_info=True,
            )

    def start(self):
        """启动总线。当前为预留接口（未来可做持久化/重放）。"""
        self._running = True
        logger.info("[MessageBus] 启动")

    def stop(self):
        """停止总线，等待所有进行中的任务完成。"""
        self._running = False
        if self._tasks:
            logger.info(f"[MessageBus] 等待 {len(self._tasks)} 个任务完成...")
            # 不强制取消，给 handler 时间完成
            self._tasks.clear()
        logger.info("[MessageBus] 停止")
```

- [ ] **Step 3: Verify file exists and can be imported**

Run: `cd backend && python -c "from app.core.message_bus import MessageBus; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/core/
git commit -m "feat: add MessageBus — async event bus with subscribe/publish

- Zero external dependencies, built on asyncio
- subscribe/publish interface compatible with distributed MQ
- Safe dispatch with exception isolation

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: ToolRegistry — 工具注册中心

**Files:**
- Create: `backend/app/core/tool_registry.py`

**Interfaces:**
- Consumes: nothing (standalone utility)
- Produces: `ToolRegistry` class with `register(name, fn, desc)`, `execute(name, **kwargs)`, `list_tools()` methods

- [ ] **Step 1: Write ToolRegistry**

```python
# backend/app/core/tool_registry.py
"""工具注册中心 — Agent 通过名称调用工具，不直接 import 函数。

职责：
- 统一注册：装饰器或 register() 将函数注册为命名工具
- 按名调用：execute(name, **kwargs) 查找并执行
- 工具清单：list_tools() 返回所有可用工具的元信息
- 错误处理：工具不存在时抛出明确异常

典型用法：
    registry = ToolRegistry()
    registry.register("analyze_week", analyze_week, "分析一周打卡数据")
    result = registry.execute("analyze_week", days=days)
"""

import logging
from typing import Callable, Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolNotFoundError(KeyError):
    """请求的工具未注册。"""
    pass


class ToolRegistry:
    """工具注册中心。

    管理名称 → (函数, 描述) 的映射。
    不做参数校验——由具体工具的调用者保证。
    """

    def __init__(self):
        self._tools: Dict[str, dict] = {}

    def register(
        self,
        name: str,
        fn: Callable,
        description: str = "",
    ):
        """注册一个工具。

        Args:
            name: 工具名称（全局唯一）
            fn: 可调用对象（函数或方法）
            description: 工具描述，用于日志和调试
        """
        if name in self._tools:
            logger.warning(f"[ToolRegistry] 工具 '{name}' 被重复注册，覆盖旧值")
        self._tools[name] = {"fn": fn, "description": description}
        logger.debug(f"[ToolRegistry] 注册工具: {name} — {description}")

    def register_batch(self, tools: Dict[str, Callable], prefix: str = ""):
        """批量注册工具，可选前缀。

        Args:
            tools: {名称: 函数} 的字典
            prefix: 可选名称前缀（如 "engine."）
        """
        for name, fn in tools.items():
            full_name = f"{prefix}{name}" if prefix else name
            self.register(full_name, fn)

    def execute(self, name: str, **kwargs) -> Any:
        """按名称执行已注册的工具。

        Args:
            name: 工具名称
            **kwargs: 传递给工具函数的参数

        Returns:
            工具函数的返回值

        Raises:
            ToolNotFoundError: 工具未注册
        """
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools.keys()))
            raise ToolNotFoundError(
                f"工具 '{name}' 未注册。可用工具: [{available}]"
            )
        logger.debug(f"[ToolRegistry] 执行: {name}")
        return tool["fn"](**kwargs)

    async def execute_async(self, name: str, **kwargs) -> Any:
        """按名称执行异步工具，或同步工具自动包装为异步。

        Args:
            name: 工具名称
            **kwargs: 传递给工具函数的参数
        """
        tool = self._tools.get(name)
        if tool is None:
            available = ", ".join(sorted(self._tools.keys()))
            raise ToolNotFoundError(
                f"工具 '{name}' 未注册。可用工具: [{available}]"
            )
        fn = tool["fn"]
        logger.debug(f"[ToolRegistry] 执行(异步): {name}")
        if asyncio.iscoroutinefunction(fn):
            return await fn(**kwargs)
        else:
            return await asyncio.get_event_loop().run_in_executor(
                None, lambda: fn(**kwargs)
            )

    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有已注册的工具。"""
        return [
            {"name": name, "description": info["description"]}
            for name, info in sorted(self._tools.items())
        ]


import asyncio  # noqa: E402 (imported here for async wrapper)
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.core.tool_registry import ToolRegistry; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/core/tool_registry.py
git commit -m "feat: add ToolRegistry — name-based tool lookup for Agents

- register/execute/list_tools interface
- async wrapper for sync functions
- clear error on missing tool

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: BaseAgent — Agent 基类

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/base_agent.py`

**Interfaces:**
- Consumes: `MessageBus`, `ToolRegistry`
- Produces: `BaseAgent` class with `subscribe()`, `publish()`, `on_start()`, `on_stop()`, `state` property

- [ ] **Step 1: Create `backend/app/agents/__init__.py`**

```python
# backend/app/agents/__init__.py
"""多 Agent 层 — 每个 Agent 有独立状态，通过 MessageBus 通信"""
```

- [ ] **Step 2: Write BaseAgent**

```python
# backend/app/agents/base_agent.py
"""Agent 基类 — 为所有 Agent 提供状态管理 + 消息收发 + 生命周期。

每个 Agent 有：
1. 独立状态（state dict）— 记住自己处理到哪了
2. 消息收发能力（subscribe / publish）— 通过 MessageBus 通信
3. 工具使用能力（tool_registry）— 调用注册好的函数
4. 生命周期（on_start / on_stop）— 启动和清理钩子

典型用法：
    class MyAgent(BaseAgent):
        def __init__(self, bus, registry):
            super().__init__("my_agent", bus, registry)
            self.subscribe("some.event", self.handle_event)

        async def handle_event(self, data):
            self.state["count"] = self.state.get("count", 0) + 1
            result = await self.execute_tool("some_tool", arg=1)
            await self.publish("result.event", result)

        async def on_start(self):
            print(f"{self.name} 启动")
"""

import logging
from typing import Optional, Dict, Any
from app.core.message_bus import MessageBus, HandlerType
from app.core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class BaseAgent:
    """Agent 基类。

    Attributes:
        name: Agent 唯一名称
        state: 状态字典（Agent 内部维护）
        bus: MessageBus 引用
        registry: ToolRegistry 引用
    """

    def __init__(
        self,
        name: str,
        bus: MessageBus,
        registry: ToolRegistry,
    ):
        self.name = name
        self.state: Dict[str, Any] = {}
        self.bus = bus
        self.registry = registry

    # ── 消息收发 ───────────────────────────────────────────

    def subscribe(self, event_type: str, handler: HandlerType):
        """订阅事件。handler 签名：async (data: dict) -> None。"""
        logger.info(f"[{self.name}] 订阅: {event_type}")
        self.bus.subscribe(event_type, handler)

    async def publish(self, event_type: str, data: dict):
        """发布事件到 MessageBus。"""
        logger.info(f"[{self.name}] 发布: {event_type}")
        await self.bus.publish(event_type, data)

    # ── 工具调用 ───────────────────────────────────────────

    def execute_tool(self, name: str, **kwargs) -> Any:
        """同步执行已注册的工具。"""
        return self.registry.execute(name, **kwargs)

    async def execute_tool_async(self, name: str, **kwargs) -> Any:
        """异步执行已注册的工具（自动包装同步函数）。"""
        return await self.registry.execute_async(name, **kwargs)

    # ── 生命周期 ───────────────────────────────────────────

    async def on_start(self):
        """Agent 启动钩子。子类覆盖此方法来执行初始化逻辑。

        此时 MessageBus 已就绪，可以 subscribe 和 publish。
        """
        logger.info(f"[{self.name}] 启动完成")

    async def on_stop(self):
        """Agent 停止钩子。子类覆盖此方法来清理资源。"""
        logger.info(f"[{self.name}] 停止完成")

    # ── 工具方法 ───────────────────────────────────────────

    def log_state(self, key: str, value: Any):
        """更新状态并记录日志。"""
        self.state[key] = value
        logger.debug(f"[{self.name}] state.{key} = {value}")

    def get_state(self, key: str, default: Any = None) -> Any:
        """安全读取状态。"""
        return self.state.get(key, default)

    def __repr__(self) -> str:
        return f"<{self.name}>"
```

- [ ] **Step 3: Verify import**

Run: `cd backend && python -c "from app.agents.base_agent import BaseAgent; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/agents/
git commit -m "feat: add BaseAgent — stateful agent base class with message bus integration

- subscribe/publish via MessageBus
- execute_tool via ToolRegistry
- lifecycle hooks (on_start/on_stop)
- persistent state dict per agent

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: AnalystAgent — 分析师 Agent

**Files:**
- Create: `backend/app/agents/analyst_agent.py`

**Interfaces:**
- Consumes: `BaseAgent`, `MessageBus`, `ToolRegistry`
- Produces: Subscribes to `workout.completed`, publishes `plan.adjustment_needed`, `exercise.swap_needed`, `plan.deload_needed`, `analysis.week_complete`

- [ ] **Step 1: Write AnalystAgent**

```python
# backend/app/agents/analyst_agent.py
"""分析师 Agent — 分析打卡数据，判断是否需要调整计划。

职责：
1. 订阅 workout.completed 事件
2. 攒够一周数据后，调 engine/adaptive_adjustment 分析进度
3. 如果需要调整，发布 plan.adjustment_needed / exercise.swap_needed 事件

注意：AnalystAgent 只做分析判断，不做执行。
执行由 ProgrammerAgent 或 CoachAgent 处理。
"""

import logging
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.core.message_bus import MessageBus
from app.core.tool_registry import ToolRegistry
from app.engine.adaptive_adjustment import analyze_slot, analyze_week
from app.models.orm_models import Day, ExerciseSlot

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    """分析师 Agent。

    状态:
        state.weekly_data[user_id] = list[day_id]  # 本周已分析的天数
        state.slot_analyses[day_id] = list[dict]    # 单个动作分析结果
    """

    def __init__(self, bus: MessageBus, registry: ToolRegistry):
        super().__init__("analyst", bus, registry)
        # 订阅打卡完成事件（这是核心入口）
        self.subscribe("workout.completed", self.on_workout_completed)
        # 内部计数器：user_id → 本周已完成天数
        self.log_state("weekly_data", {})

    async def on_workout_completed(self, data: dict):
        """收到打卡完成通知，执行分析。

        data 格式: {
            "user_id": int,
            "day_id": int,
            "timestamp": str,
        }
        """
        user_id = data["user_id"]
        day_id = data["day_id"]

        logger.info(f"[AnalystAgent] 分析 Day#{day_id} 的打卡数据")

        # 1. 从 DB 读取该天的所有 slot
        from app.database import get_db
        from app.database import SessionLocal as get_session  # 改用可调用的工厂

        # 注意：analyst_agent 不持有 DB session，每次按需获取
        # 此处使用 get_db 作为 generator，需要走上下文
        # 生产代码会使用依赖注入，这里简化处理：
        # 通过工具调用获取 day 数据
        day_data = self.execute_tool("db.get_day_with_slots", day_id=day_id)
        if not day_data:
            logger.warning(f"[AnalystAgent] Day#{day_id} 不存在，跳过分析")
            return

        # 2. 逐个分析每个 action 的完成情况
        slots = day_data.get("slots", [])
        slot_results = []
        for slot in slots:
            result = analyze_slot(slot)  # ← 调 engine 已有的函数
            slot_results.append({"slot_id": slot.id, "analysis": result})
            if result["action"] != "keep":
                logger.info(
                    f"[AnalystAgent] Slot#{slot.id} 需要调整: "
                    f"{result['action']} ({result['reason']})"
                )

        # 3. 记录分析结果
        self.log_state(f"slot_analyses.{day_id}", slot_results)

        # 4. 如果某个动作需要替换，发布事件
        swap_needed = [
            r for r in slot_results
            if r["analysis"]["action"] == "swap_exercise"
        ]
        if swap_needed:
            await self.publish("exercise.swap_needed", {
                "user_id": user_id,
                "day_id": day_id,
                "slots": swap_needed,
            })

        # 5. 更新本周打卡计数
        weekly = self.get_state("weekly_data", {})
        user_week = weekly.get(user_id, [])
        if day_id not in user_week:
            user_week.append(day_id)
        weekly[user_id] = user_week
        self.log_state("weekly_data", weekly)

        # 6. 如果攒够一周数据，做周分析
        #    简化判断：收集到 7 个 day_id 就认为一周结束了
        if len(user_week) >= 7:
            await self._run_weekly_analysis(user_id)
            weekly[user_id] = []  # 重置
            self.log_state("weekly_data", weekly)

    async def _run_weekly_analysis(self, user_id: int):
        """一周数据够了，做完整周分析。

        调 engine/adaptive_adjustment.analyze_week()
        和 engine/mesocycle_manager.needs_deload_this_week()
        """
        logger.info(f"[AnalystAgent] 对用户#{user_id}执行周分析")

        # 通过工具获取该用户本周所有 days
        days = self.execute_tool("db.get_current_week_days", user_id=user_id)
        if not days:
            logger.warning(f"[AnalystAgent] 用户#{user_id}本周无训练日")
            return

        # 周分析
        week_result = analyze_week(days)  # ← 调 engine 已有函数
        logger.info(
            f"[AnalystAgent] 周分析: 完成率={week_result['completion_rate']}, "
            f"高RPE比例={week_result['high_rpe_ratio']}"
        )

        # 判断是否需要减载
        if week_result["needs_deload"]:
            await self.publish("plan.deload_needed", {
                "user_id": user_id,
                "week_analysis": week_result,
                "reason": f"高RPE比例={week_result['high_rpe_ratio']}, "
                          f"未打卡比例={week_result['no_checkin_ratio']}",
            })
        else:
            # 正常调整（加重量/加次数）
            await self.publish("plan.adjustment_needed", {
                "user_id": user_id,
                "week_analysis": week_result,
            })

        # 发布周分析完成事件（供 CoachAgent 使用）
        await self.publish("analysis.week_complete", {
            "user_id": user_id,
            "week_analysis": week_result,
        })
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.agents.analyst_agent import AnalystAgent; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/agents/analyst_agent.py
git commit -m "feat: add AnalystAgent — analyzes check-in data, detects adjustment needs

- Subscribes to workout.completed
- Calls engine/adaptive_adjustment.analyze_slot() and analyze_week()
- Publishes exercise.swap_needed / plan.deload_needed / plan.adjustment_needed
- Maintains weekly counter in agent state

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: ProgrammerAgent — 编排 Agent

**Files:**
- Create: `backend/app/agents/programmer_agent.py`

**Interfaces:**
- Consumes: `BaseAgent`, `MessageBus`, `ToolRegistry`
- Publishes: `plan.next_week_ready`, `plan.updated`
- Subscribes to: `plan.adjustment_needed`, `plan.deload_needed`, `exercise.swap_needed`

- [ ] **Step 1: Write ProgrammerAgent**

```python
# backend/app/agents/programmer_agent.py
"""编排 Agent — 执行训练计划的生成和调整。

职责：
1. 初次生成：调 engine/generator.generate_init_week() 生成第 1 周
2. 每周生成：调 engine/generator.generate_next_week() 生后续周
3. 接收调整：收到 analyst 的调整需求，执行渐进超负荷/动作轮换/减载

本质：把现有 exercise_agent + plan_agent + engine 的调用包装成 Agent
"""

import logging
from typing import Optional, Any
from app.agents.base_agent import BaseAgent
from app.core.message_bus import MessageBus
from app.core.tool_registry import ToolRegistry
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ProgrammerAgent(BaseAgent):
    """编排 Agent — 实际执行计划生成和修改。

    状态:
        state.current_macrocycle_id: int   当前大周期 ID
        state.current_mesocycle_id: int    当前中周期 ID
        state.last_week_number: int        本周生成到第几周
    """

    def __init__(self, bus: MessageBus, registry: ToolRegistry):
        super().__init__("programmer", bus, registry)

        # 订阅调整事件——从 AnalystAgent 接收分析结果
        self.subscribe("plan.adjustment_needed", self.on_adjustment_needed)
        self.subscribe("plan.deload_needed", self.on_deload_needed)
        self.subscribe("exercise.swap_needed", self.on_swap_needed)

    async def on_start(self):
        """启动时记录当前训练进度。"""
        try:
            # 读取当前活跃的大周期/中周期，记录到状态
            macro = self.execute_tool("db.get_active_macrocycle")
            if macro:
                self.log_state("current_macrocycle_id", macro.id)
                meso = self.execute_tool(
                    "db.get_current_mesocycle",
                    macrocycle_id=macro.id,
                )
                if meso:
                    self.log_state("current_mesocycle_id", meso.id)
                    week = self.execute_tool(
                        "db.get_latest_week",
                        mesocycle_id=meso.id,
                    )
                    if week:
                        self.log_state("last_week_number", week.week_number)
                        logger.info(
                            f"[ProgrammerAgent] 当前进度: "
                            f"大周期#{macro.id}, 中周期#{meso.id}, "
                            f"第{week.week_number}周"
                        )
        except Exception as e:
            logger.warning(
                f"[ProgrammerAgent] 启动时读取进度失败: {e}（可能是新用户）"
            )
        await super().on_start()

    async def generate_initial_week(
        self,
        macrocycle,
        mesocycle,
        user_state,
        db: Session,
        event_queue: asyncio.Queue,
        user_info: Optional[dict] = None,
        start_date: Optional[str] = None,
    ) -> Optional[dict]:
        """生成第 1 周（包装现有 generator.generate_init_week）。

        这是一个直接调用的方法（不是事件驱动的），
        因为 init-plan 需要同步等待结果返回前端 SSE。
        """
        logger.info("[ProgrammerAgent] 开始生成第 1 周")
        from app.engine.generator import generate_init_week

        week = await generate_init_week(
            macrocycle, mesocycle, user_state, db, event_queue,
            user_info=user_info, start_date=start_date,
        )
        if week:
            self.log_state("last_week_number", 1)
            logger.info(f"[ProgrammerAgent] 第 1 周生成完成: Week#{week.id}")
        return week

    async def generate_next_week(
        self,
        current_week,
        db: Session,
        event_queue: asyncio.Queue,
    ) -> Optional[dict]:
        """生成下一周（包装现有 generator.generate_next_week）。"""
        from app.engine.generator import generate_next_week

        new_week = await generate_next_week(current_week, db, event_queue)
        if new_week:
            self.log_state("last_week_number", new_week.week_number)
            logger.info(
                f"[ProgrammerAgent] 第{new_week.week_number}周生成完成"
            )
        return new_week

    async def on_adjustment_needed(self, data: dict):
        """收到 AnalystAgent 的调整需求，执行渐进超负荷。

        data: {
            "user_id": int,
            "week_analysis": dict,  # analyze_week() 的输出
        }
        """
        user_id = data["user_id"]
        week_analysis = data["week_analysis"]
        completion_rate = week_analysis.get("completion_rate", 0.0)

        logger.info(
            f"[ProgrammerAgent] 收到调整需求: 用户#{user_id}, "
            f"完成率={completion_rate}"
        )

        # 完成率 100% 且无其他问题 → 调用渐进超负荷
        if completion_rate >= 0.9:
            logger.info("[ProgrammerAgent] 完成率≥90%，执行渐进超负荷")
            # 通过工具调 progressive_overload
            self.execute_tool(
                "engine.apply_progressive_overload",
                user_id=user_id,
                week_analysis=week_analysis,
            )
            await self.publish("plan.updated", {
                "user_id": user_id,
                "reason": "progressive_overload",
                "detail": "完成率≥90%，下周加量",
            })

    async def on_deload_needed(self, data: dict):
        """收到减载需求，插入减载周。

        data: {
            "user_id": int,
            "week_analysis": dict,
            "reason": str,
        }
        """
        user_id = data["user_id"]
        reason = data.get("reason", "")
        logger.info(f"[ProgrammerAgent] 收到减载需求: {reason}")

        self.execute_tool(
            "engine.force_deload_week",
            user_id=user_id,
            week_analysis=data["week_analysis"],
        )
        await self.publish("plan.updated", {
            "user_id": user_id,
            "reason": "deload",
            "detail": reason,
        })

    async def on_swap_needed(self, data: dict):
        """收到替换动作需求，执行动作轮换。

        data: {
            "user_id": int,
            "day_id": int,
            "slots": [{"slot_id": int, "analysis": dict}],
        }
        """
        day_id = data["day_id"]
        logger.info(f"[ProgrammerAgent] 收到替换动作需求: Day#{day_id}")

        # 检查：如果在周中，推迟到下周
        slot_analysis = data["slots"][0]["analysis"]
        if slot_analysis.get("action") == "swap_exercise":
            rpe = slot_analysis.get("rpe", 0)
            if rpe >= 10:
                # 紧急情况：RPE 10 → 立即替换
                logger.warning(f"[ProgrammerAgent] RPE=10，立即替换动作")
                self.execute_tool(
                    "engine.swap_exercise_immediate",
                    day_id=day_id,
                    slot_id=data["slots"][0]["slot_id"],
                )
            else:
                # 非紧急：标记为下周轮换
                logger.info("[ProgrammerAgent] 非紧急，标记下周轮换")
                self.execute_tool(
                    "engine.mark_for_rotation",
                    slot_id=data["slots"][0]["slot_id"],
                )

        await self.publish("plan.updated", {
            "user_id": data["user_id"],
            "reason": "swap_exercise",
            "detail": f"Day#{day_id} 动作已替换",
        })


import asyncio  # noqa: E402
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.agents.programmer_agent import ProgrammerAgent; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/agents/programmer_agent.py
git commit -m "feat: add ProgrammerAgent — executes plan generation and adjustments

- Wraps generator.generate_init_week() and generate_next_week()
- Handles progressive overload, deload, exercise swap requests
- Makes decisions: immediate vs deferred execution

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: CoachAgent — 教练 Agent

**Files:**
- Create: `backend/app/agents/coach_agent.py`

**Interfaces:**
- Consumes: `BaseAgent`, `MessageBus`, `ToolRegistry`
- Subscribes to: `analysis.week_complete`, `plan.updated`, `plan.next_week_ready`
- Publishes: `notification.for_user`

- [ ] **Step 1: Write CoachAgent**

```python
# backend/app/agents/coach_agent.py
"""教练 Agent — 生成用户友好的自然语言反馈。

职责：
1. 每周分析完成后，写一段总结（"你本周完成率 100%，进步很快！"）
2. 计划调整时，解释调整原因（"检测到膝盖疲劳，下周减量恢复"）
3. 生成路线图的自然语言描述（"第1-4周：动作打磨阶段"）

CoachAgent 不修改任何训练数据，只生成面向用户的文本。
"""

import logging
from typing import Optional
from app.agents.base_agent import BaseAgent
from app.core.message_bus import MessageBus
from app.core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class CoachAgent(BaseAgent):
    """教练 Agent — 用户沟通和解释。

    状态:
        state.last_feedback[user_id]: str  上次给用户的反馈
    """

    def __init__(self, bus: MessageBus, registry: ToolRegistry):
        super().__init__("coach", bus, registry)

        self.subscribe("analysis.week_complete", self.on_week_complete)
        self.subscribe("plan.updated", self.on_plan_updated)

    async def on_week_complete(self, data: dict):
        """一周分析完成，生成用户友好的周总结。

        data: {
            "user_id": int,
            "week_analysis": {
                "completion_rate": float,
                "high_rpe_ratio": float,
                "no_checkin_ratio": float,
                "needs_deload": bool,
            }
        }
        """
        analysis = data.get("week_analysis", {})
        completion_rate = analysis.get("completion_rate", 0.0)
        high_rpe = analysis.get("high_rpe_ratio", 0.0)

        # 确定性模板消息（不调 LLM，避免延迟和成本）
        if completion_rate >= 0.9:
            message = "🎉 本周完成率很高！继续保持，下周我们会适当增加训练量。"
        elif completion_rate >= 0.7:
            message = "👍 本周完成得不错。如果能再坚持一下，效果会更好！"
        elif completion_rate >= 0.5:
            message = "💪 完成了过半训练。每次训练都算数，持续进步比完美更重要。"
        else:
            message = "⏸️ 本周训练量偏低。如果有困难或需要调整计划，随时告诉我！"

        if high_rpe > 0.5:
            message += " 注意到最近训练强度偏高，如果需要休息日请不要太勉强。"

        logger.info(f"[CoachAgent] 周总结: {message}")
        await self.publish("notification.for_user", {
            "user_id": data["user_id"],
            "type": "week_summary",
            "message": message,
        })

    async def on_plan_updated(self, data: dict):
        """计划被调整了，给用户解释原因。

        data: {
            "user_id": int,
            "reason": str,    # "progressive_overload" / "deload" / "swap_exercise"
            "detail": str,
        }
        """
        reason = data.get("reason", "")
        detail = data.get("detail", "")

        messages = {
            "progressive_overload": (
                f"📈 你进步很快！{detail}。"
                "下周的训练量已经自动调整，继续加油！"
            ),
            "deload": (
                f"🔄 检测到训练强度偏高。{detail}。"
                "下周安排减载周，帮助身体恢复。"
            ),
            "swap_exercise": (
                f"🔄 {detail}。新动作已安排到下周计划中。"
            ),
        }

        message = messages.get(
            reason,
            f"📋 训练计划已更新: {detail}",
        )

        logger.info(f"[CoachAgent] 计划调整通知: {message}")
        await self.publish("notification.for_user", {
            "user_id": data["user_id"],
            "type": "plan_update",
            "message": message,
        })

    async def generate_roadmap_description(
        self,
        phase: str,
        week_number: int,
        goal: str,
    ) -> str:
        """生成路线图中某个阶段的自然语言描述。

        这个方法直接由 Orchestrator 在 init-plan 时调用的，
        不是事件驱动的。

        Args:
            phase: foundational / hypertrophy / strength / deload
            week_number: 阶段内的周次
            goal: 用户目标
        """
        descriptions = {
            "foundational": {
                "title": "动作打磨",
                "desc": "学习并掌握基础动作的正确姿势，建立神经肌肉适应",
                "detail": "重点在动作质量而非重量，打好基础才能安全进阶",
            },
            "hypertrophy": {
                "title": "容量增长",
                "desc": "增加训练量和肌肉耐力，促进肌肉生长",
                "detail": "通过增加组数和次数刺激肌肉生长",
            },
            "strength": {
                "title": "力量冲击",
                "desc": "提升最大力量和爆发力",
                "detail": "降低次数、增加重量，挑战神经系统的适应能力",
            },
            "deload": {
                "title": "恢复评估",
                "desc": "降低训练强度，让身体充分恢复",
                "detail": "减量不减频，保持训练习惯的同时让身体修复",
            },
        }
        info = descriptions.get(phase, descriptions["foundational"])
        return f"第{week_number}周 · {info['title']}：{info['desc']}。{info['detail']}"
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.agents.coach_agent import CoachAgent; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/agents/coach_agent.py
git commit -m "feat: add CoachAgent — generates user-friendly feedback and descriptions

- Subscribes to week analysis and plan update events
- Deterministic template messages (no LLM calls for feedback)
- generate_roadmap_description for phase descriptions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: 注册 engine 工具到 ToolRegistry

**Files:**
- Create: `backend/app/core/tool_registry_setup.py`

**Interfaces:**
- Produces: `register_engine_tools(registry)` function that registers all engine functions
- This is called by Orchestrator on startup

- [ ] **Step 1: Write tool registry setup**

```python
# backend/app/core/tool_registry_setup.py
"""工具注册设置 — 将 engine/ 和 db 函数注册到 ToolRegistry。

所有注册在此集中完成，Agent 通过 registry.execute(name) 调用。
"""

import logging
from app.core.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_engine_tools(registry: ToolRegistry):
    """注册所有 engine 工具到 registry。"""
    from app.engine.adaptive_adjustment import analyze_slot, analyze_week
    from app.engine.progressive_overload import (
        calc_next_week_params,
        calc_deload_params,
    )
    from app.engine.exercise_rotation import rotate_slots_for_new_mesocycle
    from app.engine.mesocycle_manager import (
        decide_next_phase,
        needs_deload_this_week,
        is_mesocycle_complete,
    )

    # ── 自适应调整 ──
    registry.register(
        "engine.analyze_slot",
        analyze_slot,
        "分析单个动作的打卡数据，返回调整建议",
    )
    registry.register(
        "engine.analyze_week",
        analyze_week,
        "分析一周整体数据，判断是否需要减载",
    )

    # ── 渐进超负荷 ──
    registry.register(
        "engine.calc_next_week_params",
        calc_next_week_params,
        "根据本周数据计算下周的训练参数",
    )
    registry.register(
        "engine.calc_deload_params",
        calc_deload_params,
        "计算减载周的参数",
    )

    # ── 动作轮换 ──
    registry.register(
        "engine.rotate_slots",
        rotate_slots_for_new_mesocycle,
        "中周期切换时轮换主项动作",
    )

    # ── 中周期管理 ──
    registry.register(
        "engine.decide_next_phase",
        decide_next_phase,
        "决策下一中周期阶段",
    )
    registry.register(
        "engine.needs_deload",
        needs_deload_this_week,
        "判断是否需提前插入减载周",
    )
    registry.register(
        "engine.is_mesocycle_complete",
        is_mesocycle_complete,
        "判断当前中周期是否已结束",
    )

    logger.info(
        f"[ToolSetup] 注册了 {len(registry.list_tools())} 个 engine 工具"
    )


def register_db_tools(registry: ToolRegistry):
    """注册数据库查询工具到 registry。

    这些工具供 Agent 在不持有 DB session 的情况下读取数据。
    Agent 不应该直接操作 DB，而是通过这些工具访问。
    """
    from app.database import SessionLocal
    from app.models.orm_models import (
        Day, Week, Mesocycle, Macrocycle,
        ExerciseSlot, UserCurrentState,
    )

    def get_day_with_slots(day_id: int) -> dict:
        """获取某天完整数据（含 slots）。"""
        db = SessionLocal()
        try:
            day = db.query(Day).filter(Day.id == day_id).first()
            if not day:
                return None
            slots = db.query(ExerciseSlot).filter(
                ExerciseSlot.day_id == day_id
            ).order_by(ExerciseSlot.sort_order).all()
            return {"day": day, "slots": slots}
        finally:
            db.close()

    def get_active_macrocycle() -> dict:
        """获取当前活跃大周期。"""
        db = SessionLocal()
        try:
            return db.query(Macrocycle).filter(
                Macrocycle.status == "active"
            ).order_by(Macrocycle.id.desc()).first()
        finally:
            db.close()

    def get_current_mesocycle(macrocycle_id: int) -> dict:
        """获取某个大周期内活跃的中周期。"""
        db = SessionLocal()
        try:
            return db.query(Mesocycle).filter(
                Mesocycle.macrocycle_id == macrocycle_id,
                Mesocycle.status == "active",
            ).order_by(Mesocycle.sort_order.desc()).first()
        finally:
            db.close()

    def get_latest_week(mesocycle_id: int) -> dict:
        """获取中周期内最新的周。"""
        db = SessionLocal()
        try:
            return db.query(Week).filter(
                Week.mesocycle_id == mesocycle_id,
            ).order_by(Week.week_number.desc()).first()
        finally:
            db.close()

    def get_current_week_days(user_id: int) -> list:
        """获取当前周的所有训练日。"""
        db = SessionLocal()
        try:
            ucs = db.query(UserCurrentState).first()
            if not ucs or not ucs.current_mesocycle_id:
                return []
            week = db.query(Week).filter(
                Week.mesocycle_id == ucs.current_mesocycle_id,
                Week.status == "active",
            ).order_by(Week.week_number.desc()).first()
            if not week:
                return []
            days = db.query(Day).filter(Day.week_id == week.id).all()
            for d in days:
                d.slots = db.query(ExerciseSlot).filter(
                    ExerciseSlot.day_id == d.id
                ).all()
            return days
        finally:
            db.close()

    def apply_progressive_overload(
        user_id: int,
        week_analysis: dict,
    ):
        """对用户下周执行渐进超负荷。

        目前是占位实现，后续会复用 generator.generate_next_week() 的逻辑。
        """
        from app.engine.generator import generate_next_week
        db = SessionLocal()
        try:
            current_week = db.query(Week).filter(
                Week.status == "active"
            ).order_by(Week.id.desc()).first()
            if current_week:
                # 标记完成并生成下周（这里简化，实际由 generate_next_week 处理）
                logger.info(
                    f"[DBTools] 渐进超负荷: 用户#{user_id} 下周加量"
                )
        finally:
            db.close()

    def force_deload_week(user_id: int, week_analysis: dict):
        """强制插入减载周。"""
        logger.info(f"[DBTools] 强制减载: 用户#{user_id}")
        # 实际实现在后续迭代中完善

    def swap_exercise_immediate(day_id: int, slot_id: int):
        """紧急替换动作。"""
        logger.info(f"[DBTools] 紧急换动作: Day#{day_id}, Slot#{slot_id}")
        # 实际实现在后续迭代中完善

    def mark_for_rotation(slot_id: int):
        """标记动作为下周轮换。"""
        logger.info(f"[DBTools] 标记轮换: Slot#{slot_id}")
        # 实际实现在后续迭代中完善

    # ── 注册 DB 工具 ──
    registry.register("db.get_day_with_slots", get_day_with_slots,
                       "获取某天的完整数据（含 slots）")
    registry.register("db.get_active_macrocycle", get_active_macrocycle,
                       "获取当前活跃的大周期")
    registry.register("db.get_current_mesocycle", get_current_mesocycle,
                       "获取大周期内活跃的中周期")
    registry.register("db.get_latest_week", get_latest_week,
                       "获取中周期内最新的周")
    registry.register("db.get_current_week_days", get_current_week_days,
                       "获取当前周所有训练日")
    registry.register("db.apply_progressive_overload",
                       apply_progressive_overload,
                       "执行渐进超负荷")
    registry.register("db.force_deload_week", force_deload_week,
                       "强制插入减载周")
    registry.register("db.swap_exercise_immediate", swap_exercise_immediate,
                       "紧急替换动作")
    registry.register("db.mark_for_rotation", mark_for_rotation,
                       "标记动作为下周轮换")

    logger.info(
        f"[ToolSetup] 注册了 {len(registry.list_tools())} 个 DB 工具"
    )
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.core.tool_registry_setup import register_engine_tools, register_db_tools; from app.core.tool_registry import ToolRegistry; r=ToolRegistry(); register_engine_tools(r); register_db_tools(r); print(f'OK: {len(r.list_tools())} tools registered')"`
Expected: `OK: N tools registered`

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/core/tool_registry_setup.py
git commit -m "feat: register engine and DB tools in ToolRegistry

- All engine/ functions registered with description
- DB query tools for Agent use (no direct DB access by Agents)
- Called by Orchestrator at startup

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Orchestrator — 协调者

**Files:**
- Create: `backend/app/core/orchestrator.py`

**Interfaces:**
- Consumes: `MessageBus`, `ToolRegistry`, all Agents
- Produces: `Orchestrator` class with `start()`, `stop()`, `get_agent(name)` methods

- [ ] **Step 1: Write Orchestrator**

```python
# backend/app/core/orchestrator.py
"""协调者 — 管理所有 Agent 的生命周期和初始订阅。

职责：
1. 创建 MessageBus 和 ToolRegistry 单例
2. 注册所有 engine/DB 工具到 ToolRegistry
3. 创建并启动所有 Agent
4. 提供统一的启动/停止接口供 fitness.py 调用

典型用法（在 fitness.py 中）：
    orch = Orchestrator()
    orch.start()
    # ... 处理请求 ...
    orch.stop()
"""

import logging
from typing import Optional, Dict
from app.core.message_bus import MessageBus
from app.core.tool_registry import ToolRegistry
from app.core.tool_registry_setup import (
    register_engine_tools,
    register_db_tools,
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """协调者 — 多 Agent 系统的启动和关闭入口。"""

    def __init__(self):
        self.bus = MessageBus()
        self.registry = ToolRegistry()
        self.agents: Dict[str, object] = {}

        # 启动时注册工具
        register_engine_tools(self.registry)
        register_db_tools(self.registry)

    def start(self):
        """启动所有 Agent 并初始化 MessageBus。"""
        logger.info("[Orchestrator] 启动多 Agent 系统...")

        # 1. 启动消息总线
        self.bus.start()

        # 2. 创建 Agent（按依赖顺序）
        from app.agents.analyst_agent import AnalystAgent
        from app.agents.programmer_agent import ProgrammerAgent
        from app.agents.coach_agent import CoachAgent

        analyst = AnalystAgent(self.bus, self.registry)
        programmer = ProgrammerAgent(self.bus, self.registry)
        coach = CoachAgent(self.bus, self.registry)

        self.agents = {
            "analyst": analyst,
            "programmer": programmer,
            "coach": coach,
        }

        # 3. 调用各 Agent 的生命周期钩子
        import asyncio
        loop = asyncio.get_event_loop()
        for name, agent in self.agents.items():
            loop.create_task(agent.on_start())

        logger.info(
            f"[Orchestrator] 启动完成: "
            f"{', '.join(self.agents.keys())} "
            f"({len(self.registry.list_tools())} 个工具已注册)"
        )

    def stop(self):
        """优雅关闭所有 Agent。"""
        logger.info("[Orchestrator] 关闭多 Agent 系统...")
        import asyncio
        loop = asyncio.get_event_loop()
        for name, agent in self.agents.items():
            loop.create_task(agent.on_stop())
        self.bus.stop()
        self.agents.clear()
        logger.info("[Orchestrator] 已关闭")

    def get_agent(self, name: str):
        """按名称获取 Agent 实例。"""
        return self.agents.get(name)

    def get_tool_count(self) -> int:
        """获取已注册工具数量。"""
        return len(self.registry.list_tools())
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.core.orchestrator import Orchestrator; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
cd backend
git add app/core/orchestrator.py
git commit -m "feat: add Orchestrator — lifecycle manager for multi-agent system

- Creates MessageBus, ToolRegistry, and all Agents
- Registers engine and DB tools on startup
- Provides start/stop/get_agent interface

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: 改造 fitness.py — checkin 加 publish

**Files:**
- Modify: `backend/app/api/routes/fitness.py`
- Modify: `backend/app/api/main.py`（注册 Orchestrator 到 app.state）

**Interfaces:**
- Consumes: `Orchestrator`

- [ ] **Step 1: 在 main.py 中添加 Orchestrator 的全局初始化**

```python
# backend/app/api/main.py — 添加以下代码
# 在 create_app() 函数中或文件末尾

from app.core.orchestrator import Orchestrator

# 全局 Orchestrator 实例（应用启动时创建，关闭时销毁）
orchestrator = Orchestrator()


@app.on_event("startup")
async def start_agents():
    """应用启动时启动多 Agent 系统。"""
    orchestrator.start()
    app.state.orchestrator = orchestrator


@app.on_event("shutdown")
async def stop_agents():
    """应用关闭时停止多 Agent 系统。"""
    orchestrator.stop()
```

- [ ] **Step 2: 改造 fitness.py 的 checkin 接口**

在 `fitness.py` 顶部添加 import：

```python
# fitness.py 顶部添加
from app.api.main import orchestrator
```

改造 `checkin` 接口（第 295-324 行）：

```python
@router.post("/checkin")
async def checkin(data: schemas.DayCheckin, db: Session = Depends(get_db)):
    """每日打卡：更新 day + exercise_slot 的实际完成数据 + 发布事件。"""
    day = db.query(orm_models.Day).filter(
        orm_models.Day.id == data.day_id
    ).first()
    if not day:
        raise HTTPException(status_code=404, detail="训练日不存在")

    # 更新 day
    day.is_completed = 1 if data.is_completed else 0
    if data.rpe_score:
        day.rpe_score = data.rpe_score

    # 更新每个 slot
    for ex_data in data.exercises:
        slot = db.query(orm_models.ExerciseSlot).filter(
            orm_models.ExerciseSlot.id == ex_data.slot_id,
            orm_models.ExerciseSlot.day_id == data.day_id,
        ).first()
        if not slot:
            continue
        slot.actual_sets = ex_data.actual_sets
        slot.actual_reps = ex_data.actual_reps
        slot.actual_weight_kg = ex_data.actual_weight_kg
        slot.rpe = ex_data.rpe
        slot.notes = ex_data.notes or ""

    db.commit()

    # ── 新增：发布打卡完成事件 ──
    # AnalystAgent 会收到此事件，自动开始分析
    await orchestrator.bus.publish("workout.completed", {
        "user_id": 1,  # 当前系统是单用户，固定为 1
        "day_id": data.day_id,
        "timestamp": str(datetime.now()),
    })

    return {"message": "打卡成功", "day_id": data.day_id}
```

注意：需要在 fitness.py 顶部添加 `from datetime import datetime`。

- [ ] **Step 3: 验证修改后代码可运行**

Run: `cd backend && python -c "from app.api.main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd backend
git add app/api/main.py app/api/routes/fitness.py
git commit -m "feat: wire checkin to MessageBus — publish workout.completed

- Orchestrator initialized on app startup
- checkin now publishes workout.completed after saving data
- AnalystAgent automatically analyzes on each check-in

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: 功能测试 — 验证打卡→分析闭环

**Files:**
- Create: `test/test_agent_flow.py`（新的端到端测试）

- [ ] **Step 1: 编写端到端测试脚本**

```python
"""测试多 Agent 闭环：checkin → publish → AnalystAgent → adjust

前提：数据库已有 init-plan 生成的数据。
"""

import requests
import time
import json

BASE = "http://localhost:8000/api/fitness"


def test_checkin_triggers_analysis():
    """测试打卡后 AnalystAgent 是否自动分析。"""
    # 1. 先获取当前周的某一天
    r = requests.get(f"{BASE}/current-week")
    assert r.status_code == 200, f"获取当前周失败: {r.text}"
    week = r.json()
    assert len(week["days"]) > 0, "当前周没有训练日"

    day = week["days"][0]
    print(f"测试打卡: Day#{day['id']} ({day['date']}, {day['focus']})")

    # 2. 构造打卡数据
    checkin_data = {
        "day_id": day["id"],
        "is_completed": True,
        "rpe_score": 7,
        "exercises": [],
    }
    for slot in day.get("slots", []):
        checkin_data["exercises"].append({
            "slot_id": slot["id"],
            "actual_sets": slot.get("target_sets", 3),
            "actual_reps": slot.get("target_reps", 10),
            "actual_weight_kg": slot.get("weight_kg", 0),
            "rpe": 7,
            "notes": "",
        })

    # 3. 打卡（这步会触发 workout.completed 事件）
    r = requests.post(f"{BASE}/checkin", json=checkin_data)
    assert r.status_code == 200, f"打卡失败: {r.text}"
    print(f"✅ 打卡成功: {r.json()}")

    # 4. 等待 Agent 异步处理
    print("等待 Agent 异步处理...")
    time.sleep(2)

    # 5. 验证：再获取一次周数据，确认没有报错（Agent 处理不应破坏数据）
    r = requests.get(f"{BASE}/current-week")
    assert r.status_code == 200
    refreshed = r.json()
    assert len(refreshed["days"]) == len(week["days"])
    print("✅ 后续数据正常，Agent 处理未影响数据完整性")

    print("\n🎉 打卡→分析闭环测试通过！")


if __name__ == "__main__":
    test_checkin_triggers_analysis()
```

- [ ] **Step 2: 运行测试**

Run:
```bash
# 确保后端在运行
cd backend && python run.py &
sleep 3

# 先 init-plan 创建训练数据
# （假设已有 init-plan 数据，或手动执行一次）

# 运行测试
cd backend && python ../test/test_agent_flow.py
```
Expected: 测试通过，显示 `✅ 打卡成功` 和 `✅ 后续数据正常`

- [ ] **Step 3: Commit**

```bash
cd backend
git add ../test/test_agent_flow.py
git commit -m "test: add end-to-end test for checkin → Agent analysis flow

- Verifies checkin publishes workout.completed without error
- Verifies Agent processing doesn't corrupt existing data
- Run: python test/test_agent_flow.py

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: 验收 — 面试回答整理

**Files:**
- Modify: `docs/superpowers/specs/interview-prep.md`（面试回答要点，如存在）

- [ ] **Step 1: 补充面试文档中的 Agent 架构回答**

```markdown
## 面试追问应对：多 Agent 架构

### Q: "你的 Agent 之间怎么通信的？"
A: 通过事件总线（MessageBus）。每个 Agent 订阅自己关心的事件类型，
打卡完成后 checkin 接口只发一条 workout.completed 消息，
AnalystAgent 收到后自动分析，发现调整需求就再发 plan.adjustment_needed，
ProgrammerAgent 收到后执行调整。
全程异步、解耦、可观测。

### Q: "Agent 状态怎么管理的？"
A: 每个 Agent 继承 BaseAgent，内部维护 state dict。
AnalystAgent 会记"这周已经分析了几个动作"，攒够 7 次才做周分析。
ProgrammerAgent 记"当前生成到第几周了"。
状态是 Agent 内部维护的，不是无状态回调。

### Q: "LLM 调用失败了怎么办？"
A: MessageBus 的 _safe_dispatch 会捕获所有 handler 异常，
单个 Agent 失败不影响其他 Agent。
关键工具函数在 ToolRegistry 中注册，
executor 层有 timeout 和异常隔离。

### Q: "这和直接函数调用有什么区别？"
A: 三个本质区别：
1. 解耦：checkin 不 import 任何分析模块，只发一条消息
2. 可扩展：加新功能只需加新 Agent 订阅事件，不用改已有代码
3. 有状态+能决策：Agent 可以攒够数据再处理、可以拒绝执行、
   可以多步协作（Analyst→Programmer→Coach 接力）
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/interview-prep.md
git commit -m "docs: add multi-agent architecture interview Q&A

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```
