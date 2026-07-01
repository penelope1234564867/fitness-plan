"""LLM服务模块"""

import os
import time
from hello_agents import HelloAgentsLLM
from ..config import get_settings

# ═══════════════════════════════════════════════════════════════
#  新引擎 Prompt 模板
# ═══════════════════════════════════════════════════════════════

INIT_PHASE_PROMPT = """你是一个专业的健身教练。根据用户的信息，选择最合适的第一个中周期阶段。

用户信息：
- 目标：{goal}
- 经验：{experience}
- 每周训练天数：{days_per_week}

阶段选项：
- foundational（基础适应期）：适合新手，高次数低强度，学习动作模式
- hypertrophy（肌肥大期）：适合有一定基础的用户，中等次数增肌

请只返回阶段名称（foundational 或 hypertrophy），不要多余文字。"""

INIT_WORKOUT_SPLIT_PROMPT = """根据以下信息选择分化方案：
- 每周训练天数：{days_per_week}
- 经验：{experience}

方案选项：
- ppl_3：推/拉/腿 三分化（适合3天/周）
- upper_lower_4：上下肢二分化（适合4天/周）
- ppl_5：推/拉/腿 + 弱项补充（适合5天/周）
- ppl_6：推/拉/腿 × 2（适合6天/周）

请只返回方案名称，不要多余文字。"""

# 全局LLM实例
_llm_instance = None
_fast_llm_instance = None


def get_llm() -> HelloAgentsLLM:
    """
    获取主LLM实例(单例模式) — 用于复杂推理任务（组装计划等）

    Returns:
        HelloAgentsLLM实例
    """
    global _llm_instance

    if _llm_instance is None:
        settings = get_settings()

        t0 = time.time()
        _llm_instance = HelloAgentsLLM()

        print(f"✅ LLM服务初始化成功 ({time.time()-t0:.1f}s)")

    return _llm_instance


def get_fast_llm() -> HelloAgentsLLM:
    """
    获取快速/轻量LLM实例(单例模式) — 用于简单决策任务（精选动作等）

    读取 FAST_LLM_MODEL_ID 环境变量，默认与主模型相同。
    可设置如 deepseek-chat / gpt-4o-mini 等更便宜的模型。

    Returns:
        HelloAgentsLLM实例（轻量模型）
    """
    global _fast_llm_instance

    if _fast_llm_instance is None:
        t0 = time.time()
        model_id = os.getenv("FAST_LLM_MODEL_ID") or os.getenv("LLM_MODEL_ID", "")
        _fast_llm_instance = HelloAgentsLLM(model=model_id)
        print(f"✅ 快速LLM服务初始化成功 ({time.time()-t0:.1f}s, model={model_id})")

    return _fast_llm_instance


def reset_llm():
    """重置LLM实例(用于测试或重新配置)"""
    global _llm_instance, _fast_llm_instance
    _llm_instance = None
    _fast_llm_instance = None

