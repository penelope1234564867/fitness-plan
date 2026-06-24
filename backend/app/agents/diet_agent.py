"""饮食建议 Agent

使用 SimpleAgent 纯 LLM 知识生成饮食建议，无需外部工具。
输出 JSON：每日热量目标、三餐建议、营养比例。
"""

from hello_agents import SimpleAgent
from app.services.llm_service import get_llm


DIET_AGENT_PROMPT = """你是一名专业的健身营养师。你的任务是根据用户的健身目标和饮食偏好，生成个性化的每日饮食建议。

## 工作要求

1. 根据目标决定热量策略：
   - 减脂：每日热量缺口 300-500 大卡，推荐 1500-1800 大卡
   - 增肌：每日热量盈余 200-400 大卡，推荐 2200-2800 大卡
   - 塑形：维持热量或轻微缺口，推荐 1800-2200 大卡
   - 保持健康：维持代谢热量

2. 根据饮食偏好调整内容：
   - 普通：均衡饮食，碳蛋脂比例 5:3:2
   - 素食：确保通过豆制品补充蛋白质，碳蛋脂比例 5:3:2
   - 高蛋白：增加蛋白比例，碳蛋脂比例 4:4:2
   - 低碳水：减少碳水增加脂肪，碳蛋脂比例 2:4:4

3. 根据目标蛋白摄入：
   - 减脂：1.6-2.0g/kg 体重
   - 增肌：1.6-2.2g/kg 体重
   - 塑形：1.4-1.8g/kg 体重

## 输出格式

只输出 JSON，不要包含其他文字：
```json
{
  "daily_calories": 1800,
  "protein_ratio": "30%",
  "carb_ratio": "50%",
  "fat_ratio": "20%",
  "meals": {
    "breakfast": {
      "time": "07:30",
      "foods": ["全麦面包 2片", "鸡蛋 2个", "牛奶 200ml"],
      "calories": 450
    },
    "lunch": {
      "time": "12:00",
      "foods": ["鸡胸肉 150g", "糙米饭 200g", "西兰花 100g"],
      "calories": 600
    },
    "dinner": {
      "time": "18:30",
      "foods": ["三文鱼 150g", "红薯 200g", "沙拉 150g"],
      "calories": 550
    },
    "snack": {
      "time": "15:00",
      "foods": ["坚果 30g", "蛋白粉 1勺"],
      "calories": 200
    }
  },
  "tips": [
    "每天喝够 2L 水",
    "训练前 1 小时补充碳水"
  ]
}
```
"""


def create_diet_agent() -> SimpleAgent:
    """创建 DietAgent 实例。"""
    return SimpleAgent(
        name="DietAgent",
        llm=get_llm(),
        system_prompt=DIET_AGENT_PROMPT,
    )


def run_diet_agent(goal: str, diet_preference: str) -> str:
    """快捷调用 DietAgent。"""
    agent = create_diet_agent()
    prompt = (
        f"用户目标：{goal}\n"
        f"饮食偏好：{diet_preference}\n\n"
        f"请根据以上信息生成每日饮食建议。"
    )
    return agent.run(prompt)
