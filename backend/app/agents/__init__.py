"""智能体模块

Agent 系统架构（2026-07 重构）:

┌──────────────────────────────────────────────┐
│              PlanService                      │
│  (编排器 — 直接函数调用，无事件总线)           │
├──────────────────────────────────────────────┤
│  CoachAgent       → PlanAndSolveAgent         │
│  ProgrammerAgent  → ReActAgent                │
│  AnalystAgent     → ReflectionAgent            │
│  PlanAssembler    → 纯函数（无 LLM）           │
└──────────────────────────────────────────────┘

调用链路:
  用户请求 → PlanService → CoachAgent(画像) → ProgrammerAgent(选动作)
    → PlanAssembler(组装) → CoachAgent(备注) → 返回
"""

# 新 Agent 类
from .coach_agent import CoachAgent
from .programmer_agent import ProgrammerAgent
from .analyst_agent import AnalystAgent

# 纯函数组装器
from . import plan_assembler

# 旧模块（向后兼容）
from . import exercise_agent
from . import plan_agent

__all__ = [
    "CoachAgent",
    "ProgrammerAgent",
    "AnalystAgent",
    "plan_assembler",
    "exercise_agent",
    "plan_agent",
]
