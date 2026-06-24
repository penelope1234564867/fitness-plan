"""计划审查 Agent

使用 ReflectionAgent 对生成的训练计划进行自我审查和修正。
不需要外部工具，只做内容审查。
最大迭代 2 轮。
"""

from hello_agents import ReflectionAgent
from app.services.llm_service import get_llm


PLAN_REVIEW_PROMPTS = {
    "initial": """你是一名严格的健身计划质量审核员。请审查以下训练计划的完整性和格式正确性。

检查清单：
1. 是否包含 weekly_plans 数组且不为空
2. 每天是否有 warmup、main、cooldown 数组
3. 每个动作是否包含 name、sets、reps、image_url 字段
4. 是否包含 diet 字段（含 daily_calories、meals）

训练计划：
{input}

请返回 JSON 格式审查结果：
{"valid": true/false, "issues": ["问题1", "问题2"], "plan": 原样输出训练计划}
""",

    "reflect": """请仔细检查以下训练计划的合理性：

审查清单：
1. ❓ 同一肌群是否间隔至少 48 小时？（如周一练胸，周二不应再练胸）
2. ❓ 大肌群（胸/背/腿）是否安排在小肌群（手臂/肩）之前？
3. ❓ 每周是否有至少 1 天完全休息日？
4. ❓ 天气状况与训练地点是否匹配？（下雨天不应安排户外有氧）
5. ❓ 饮食建议与训练目标是否一致？（减脂期应控制热量，增肌期应高蛋白）

训练计划：
{plan_content}

请逐一检查以上清单。如果没有问题，回答"无需改进"。
如果有问题，列出问题并给出修改建议。

格式要求：
{"has_issues": true/false, "issues": [{"desc": "问题描述", "fix": "修改建议"}], "suggestions": "总体改进建议"}
""",

    "refine": """请根据以下反馈意见修正训练计划：

反馈意见：
{feedback}

上一版计划：
{last_version}

请输出修正后的完整训练计划（JSON 格式，不要包含其他文字）。
""",
}


def create_plan_review_agent() -> ReflectionAgent:
    """创建 PlanReviewAgent 实例。"""
    agent = ReflectionAgent(
        name="PlanReviewAgent",
        llm=get_llm(),
        prompts=PLAN_REVIEW_PROMPTS,
        max_reflections=2,  # 最多 2 轮迭代
    )
    return agent


def run_plan_review(plan_content: str) -> str:
    """快捷调用 PlanReviewAgent。"""
    agent = create_plan_review_agent()
    return agent.run(plan_content)
