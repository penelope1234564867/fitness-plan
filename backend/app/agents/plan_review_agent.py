"""计划审查 Agent

使用 ReflectionAgent 对生成的训练计划进行自我审查和修正。
不需要外部工具，只做内容审查。默认最多 2 轮反思迭代。
"""

from hello_agents import ReflectionAgent
from app.services.llm_service import get_llm


SYSTEM_PROMPT = """你是一名严格的健身计划质量审核员。你的工作是审查训练计划，发现并修正问题。

## 审查清单（必须逐一检查）

1. 同一肌群是否间隔至少 48 小时？（如周一练胸，周二不应再练胸）
2. 大肌群（胸/背/腿）是否安排在小肌群（手臂/肩）之前？
3. 每周是否有至少 1 天完全休息日？
4. 天气状况与训练地点是否匹配？（下雨天不应安排户外有氧）
5. 饮食建议与训练目标是否一致？（减脂期应控制热量，增肌期应高蛋白）
6. 每个动作是否包含 name、sets、reps 字段
7. 计划是否包含 weekly_plans 且不为空

## 输出格式

如果有问题，输出修正后的完整计划（JSON 格式）。
如果没有问题，回复"无需改进"。
"""


def create_plan_review_agent() -> ReflectionAgent:
    """创建 PlanReviewAgent 实例。"""
    agent = ReflectionAgent(
        name="PlanReviewAgent",
        llm=get_llm(),
        system_prompt=SYSTEM_PROMPT,
        max_iterations=2,
    )
    return agent


def run_plan_review(plan_content: str) -> str:
    """快捷调用 PlanReviewAgent。"""
    agent = create_plan_review_agent()
    return agent.run(plan_content)
