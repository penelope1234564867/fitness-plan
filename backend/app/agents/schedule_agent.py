"""日程编排 Agent

使用 ReActAgent + WeatherTool（高德天气）查询城市天气，
根据天气决定室内/户外训练，编排每周训练日程。
输出 JSON：每周每天的训练重点和地点建议。
"""

from typing import Optional, List, Dict, Any
from hello_agents import ReActAgent
from hello_agents.tools import ToolRegistry
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from app.services.llm_service import get_llm
from app.config import get_settings
import httpx
import json

AMAP_BASE = "https://restapi.amap.com/v3"


# ── WeatherTool ────────────────────────────────────────
# 高德天气查询工具

class WeatherTool(Tool):
    """查询城市天气的工具。"""

    def __init__(self):
        super().__init__(
            name="query_weather",
            description="查询指定城市的当前天气和未来天气预报，用于决定户外/室内训练",
        )
        self._api_key = ""

    def _get_key(self) -> str:
        """懒加载 API Key。"""
        if not self._api_key:
            self._api_key = get_settings().amap_api_key
        return self._api_key

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="city", type="string", description="城市名称（如 北京、上海、广州）", required=True),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        city = parameters.get("city", "")
        if not city:
            return ToolResponse(status="ERROR", text="请提供城市名称")

        key = self._get_key()
        if not key:
            # 没有 API Key 时返回模拟数据
            return ToolResponse(status="SUCCESS", text=json.dumps({
                "city": city,
                "weather": "未知（未配置天气 API Key）",
                "temperature": "未知",
                "advice": "建议室内训练",
            }, ensure_ascii=False))

        try:
            with httpx.Client(timeout=10.0) as client:
                # 查询城市区域码
                resp = client.get(f"{AMAP_BASE}/config/district", params={
                    "key": key, "keywords": city, "subdistrict": 0,
                })
                resp.raise_for_status()
                geo = resp.json()

                if geo.get("status") != "1" or not geo.get("districts"):
                    return ToolResponse(status="SUCCESS", text=json.dumps({
                        "city": city, "weather": "未知", "advice": "默认室内训练",
                    }, ensure_ascii=False))

                adcode = geo["districts"][0]["adcode"]

                # 查询天气
                resp = client.get(f"{AMAP_BASE}/weather/weatherInfo", params={
                    "key": key, "city": adcode, "extensions": "all",
                })
                resp.raise_for_status()
                weather = resp.json()

            if weather.get("status") != "1":
                return ToolResponse(status="SUCCESS", text=json.dumps({
                    "city": city, "weather": "未知", "advice": "建议室内训练",
                }, ensure_ascii=False))

            forecasts = weather.get("forecasts", [{}])[0]
            casts = forecasts.get("casts", [])

            result = {
                "city": forecasts.get("city", city),
                "province": forecasts.get("province", ""),
                "forecasts": [],
            }

            for cast in casts[:5]:  # 最多 5 天
                day_weather = cast.get("dayweather", "未知")
                night_weather = cast.get("nightweather", "未知")
                day_temp = cast.get("daytemp", "?")
                night_temp = cast.get("nighttemp", "?")
                wind = cast.get("daywind", "")

                # 判断是否适合户外
                is_rainy = any(w in day_weather + night_weather for w in ["雨", "雪", "霾"])
                is_extreme = any(w in day_weather for w in ["暴", "大"])
                is_cold = False
                try:
                    is_cold = int(day_temp) < 0
                except ValueError:
                    pass

                if is_rainy or is_extreme or is_cold:
                    location_advice = "室内训练"
                else:
                    location_advice = "户外训练"

                result["forecasts"].append({
                    "date": cast.get("date", ""),
                    "day_weather": day_weather,
                    "night_weather": night_weather,
                    "day_temp": f"{day_temp}°C",
                    "night_temp": f"{night_temp}°C",
                    "wind": wind,
                    "location_advice": location_advice,
                })

            return ToolResponse(status="SUCCESS", text=json.dumps(result, ensure_ascii=False))

        except Exception as e:
            return ToolResponse(status="SUCCESS", text=json.dumps({
                "city": city,
                "weather": "查询失败",
                "error": str(e),
                "advice": "建议室内训练作为备选",
            }, ensure_ascii=False))

    async def arun(self, parameters: Dict[str, Any]) -> ToolResponse:
        return self.run(parameters)


# ── Agent Prompt ────────────────────────────────────────

SCHEDULE_AGENT_PROMPT = """你是一名专业的训练日程编排教练。你的任务是根据用户信息和天气情况，编排每周的训练日程。

## 可用工具

1. **query_weather** — 查询指定城市未来几天的天气预报
   - 参数：city（城市名称）
   - 返回：每日天气、温度、是否适合户外训练

## 工作要求

1. 先使用 query_weather 查询天气
2. 根据天气决定训练地点：
   - 下雨/下雪/雾霾 → 室内训练
   - 天气良好 → 户外有氧/户外训练
3. 编排原则：
   - 同一肌群间隔至少 48 小时
   - 大肌群（腿/背/胸）安排在训练日前半段
   - 每次训练一个主要肌群 + 一个辅助肌群
   - 每周至少安排 1 天完全休息
   - 参考国际训练分化：推/拉/腿（PPL）或上下肢分化

## 输出格式

只输出 JSON，不要包含其他文字：
```json
{
  "schedule": [
    {
      "day": "周一",
      "focus": "胸部 + 三头",
      "location": "健身房",
      "workout_type": "力量训练"
    },
    {
      "day": "周二",
      "focus": "背部 + 二头",
      "location": "健身房",
      "workout_type": "力量训练"
    },
    {
      "day": "周三",
      "focus": "休息或低强度有氧",
      "location": "户外",
      "workout_type": "有氧"
    }
  ],
  "weather_summary": "本周天气良好，适合户外有氧。周三有雨，建议室内训练。"
}
```
"""


# ── ScheduleAgent ───────────────────────────────────────

def create_schedule_agent() -> ReActAgent:
    """创建 ScheduleAgent 实例。"""
    registry = ToolRegistry()
    registry.register_tool(WeatherTool())

    agent = ReActAgent(
        name="ScheduleAgent",
        llm=get_llm(),
        tool_registry=registry,
        system_prompt=SCHEDULE_AGENT_PROMPT,
        max_steps=6,
    )
    return agent


def run_schedule_agent(goal: str, location: str, days: int, city: str = "") -> str:
    """快捷调用 ScheduleAgent。"""
    agent = create_schedule_agent()
    prompt = (
        f"用户目标：{goal}\n"
        f"首选训练地点：{location}\n"
        f"每周天数：{days}\n"
        f"城市：{city if city else '未指定'}\n\n"
        f"请先查询天气，然后编排每周 {days} 天的训练日程。"
    )
    return agent.run(prompt)
