"""动作搜索 Agent

使用 ReActAgent + ToolRegistry 检索 wger 真实训练动作。
输出 JSON 数组，每个动作包含 name / target_muscle / sets / reps / image_url 等字段。
"""

from typing import Optional, List, Dict, Any
from hello_agents import ReActAgent
from hello_agents.tools import ToolRegistry
from hello_agents.tools import Tool, ToolParameter, ToolResponse
from app.services.llm_service import get_llm
import httpx
import json

WGER_BASE = "https://wger.de/api/v2"


# ── WgerSearchTool ─────────────────────────────────────
# 将 wger REST API 封装为 ToolRegistry 可用的 Tool
# 注意：不经过 MCP Server 子进程，直接调 REST API

class WgerSearchTool(Tool):
    """搜索 wger 训练动作的工具。"""

    def __init__(self):
        super().__init__(
            name="wger_search_exercises",
            description="搜索 wger 健身数据库中的真实训练动作，支持按肌群/器材/关键词搜索",
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="muscle", type="int", description="目标肌群ID (4=胸, 1=二头, 2=三头, 6=腹肌, 10=股四头)", required=False),
            ToolParameter(name="query", type="string", description="关键词搜索 (如 bench press, squat)", required=False),
            ToolParameter(name="equipment", type="int", description="器材ID (3=哑铃, 1=杠铃, 8=弹力带)", required=False),
            ToolParameter(name="category", type="int", description="分类ID (11=Chest, 10=Abs, 15=Cardio)", required=False),
            ToolParameter(name="limit", type="int", description="返回数量(1-50)", required=False, default=10),
        ]

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        """同步执行搜索。"""
        try:
            results = self._search(parameters)
            return ToolResponse(status="SUCCESS", text=results)
        except Exception as e:
            return ToolResponse(
                status="ERROR",
                text=f"搜索动作失败: {type(e).__name__}: {e}",
                error_info={"type": type(e).__name__, "message": str(e)},
            )

    async def arun(self, parameters: Dict[str, Any]) -> ToolResponse:
        """异步执行搜索。"""
        return self.run(parameters)

    def _search(self, params: Dict[str, Any]) -> str:
        """实际调用 wger API 搜索动作。"""
        api_params = {"format": "json", "language": 2, "limit": min(params.get("limit", 10), 50)}
        if params.get("query"):
            api_params["search"] = params["query"]
        if params.get("muscle"):
            api_params["muscles"] = params["muscle"]
        if params.get("equipment"):
            api_params["equipment"] = params["equipment"]
        if params.get("category"):
            api_params["category"] = params["category"]

        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(f"{WGER_BASE}/exerciseinfo/", params=api_params)
            resp.raise_for_status()
            data = resp.json()

        exercises = []
        for ex in data.get("results", []):
            name = ""
            desc = ""
            for t in ex.get("translations", []):
                if t.get("language") == 2 or t.get("language", {}).get("id") == 2:
                    name = t.get("name", "")
                    desc = t.get("description", "")
                    break
            if not name and ex.get("translations"):
                name = ex["translations"][0].get("name", "")

            target_muscle = ""
            for m in ex.get("muscles", []):
                if isinstance(m, dict):
                    target_muscle = m.get("name_en", m.get("name", ""))
                    break

            image_url = ""
            for img in ex.get("images", []):
                if isinstance(img, dict) and img.get("image"):
                    image_url = img["image"]
                    break

            exercises.append({
                "id": ex.get("id"),
                "name": name,
                "target_muscle": target_muscle,
                "image_url": image_url,
                "description": desc[:200] if desc else "",
            })

        return json.dumps({
            "total": data.get("count", 0),
            "count": len(exercises),
            "exercises": exercises[:50],
        }, ensure_ascii=False)


class WgerListCategoriesTool(Tool):
    """列出 wger 动作分类。"""
    def __init__(self):
        super().__init__(name="wger_list_categories", description="列出所有训练动作分类（如 Chest、Abs、Legs）")

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(f"{WGER_BASE}/exercisecategory/", params={"format": "json"})
                resp.raise_for_status()
                data = resp.json()
            items = [{"id": c["id"], "name": c["name"]} for c in data.get("results", [])]
            return ToolResponse(status="SUCCESS", text=json.dumps(items, ensure_ascii=False))
        except Exception as e:
            return ToolResponse(status="ERROR", text=f"获取分类失败: {e}")


class WgerListMusclesTool(Tool):
    """列出 wger 肌群。"""
    def __init__(self):
        super().__init__(name="wger_list_muscles", description="列出所有肌群（含英文名和 ID）")

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(f"{WGER_BASE}/muscle/", params={"format": "json"})
                resp.raise_for_status()
                data = resp.json()
            items = [{"id": m["id"], "name": m.get("name", ""), "name_en": m.get("name_en", "")}
                     for m in data.get("results", [])]
            return ToolResponse(status="SUCCESS", text=json.dumps(items, ensure_ascii=False))
        except Exception as e:
            return ToolResponse(status="ERROR", text=f"获取肌群失败: {e}")


# ── Agent Prompt ────────────────────────────────────────

EXERCISE_AGENT_PROMPT = """你是一名专业的健身动作设计专家。你的任务是根据用户的健身目标、经验水平和训练地点，搜索并推荐合适的训练动作。

## 可用工具

1. **wger_search_exercises** — 搜索 wger 数据库中的真实训练动作
   - 参数：muscle（肌群ID）、query（关键词）、equipment（器材ID）、limit（数量）
   - 返回：动作名称、目标肌群、教学图片URL、描述
   - 使用前先查肌肉ID：胸=4, 背=12, 腿=9, 肩=13, 手臂=8, 腹肌=10
   - 器材ID：杠铃=1, 哑铃=3, 自重=7

2. **wger_list_categories** — 查看可用的训练分类

3. **wger_list_muscles** — 查看可用的肌群列表

## 工作要求

1. 每个动作必须使用 wger_search_exercises 从真实数据库获取，不要编造
2. 根据用户经验水平决定组数次数：
   - 新手：2-3组，10-12次
   - 中级：3-4组，8-12次
   - 高级：4-5组，6-10次
3. 根据目标决定休息时间和重量建议：
   - 减脂：休息30-45秒，中等重量高次数
   - 增肌：休息60-90秒，大重量中次数
   - 塑形：休息45-60秒，中低重量多次数
4. 每次训练包含 4-6 个动作

## 输出格式

你必须返回 JSON 格式，不要包含其他文字：
```json
[
  {
    "name": "动作名称",
    "target_muscle": "目标肌群",
    "category": "力量/有氧",
    "sets": 3,
    "reps": 12,
    "rest_seconds": 60,
    "weight_suggestion": "中等重量 (8-12RM)",
    "description": "动作描述",
    "image_url": "https://wger.de/..."
  }
]
```

搜索不到真实动作时才使用常见的训练动作作为备选。
"""


# ── ExerciseAgent ───────────────────────────────────────

def create_exercise_agent() -> ReActAgent:
    """创建 ExerciseAgent 实例。"""
    registry = ToolRegistry()
    registry.register_tool(WgerSearchTool())
    registry.register_tool(WgerListCategoriesTool())
    registry.register_tool(WgerListMusclesTool())

    agent = ReActAgent(
        name="ExerciseAgent",
        llm=get_llm(),
        tool_registry=registry,
        system_prompt=EXERCISE_AGENT_PROMPT,
        max_steps=8,
    )
    return agent


# ── 快捷调用 ────────────────────────────────────────────

def run_exercise_agent(goal: str, experience: str, location: str, days: int) -> str:
    """快捷调用 ExerciseAgent。"""
    agent = create_exercise_agent()
    prompt = (
        f"用户目标：{goal}\n"
        f"经验水平：{experience}\n"
        f"训练地点：{location}\n"
        f"每周天数：{days}\n\n"
        f"请为以上用户搜索合适的训练动作，每个动作必须从 wger 数据库获取真实数据。"
        f"一天训练安排 4-6 个动作。{days} 天需要覆盖不同的肌群组合。"
    )
    return agent.run(prompt)
