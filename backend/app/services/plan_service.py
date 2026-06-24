"""健身计划服务 - 核心编排层

串行编排 5 个 Agent 的协作流程：
  1. ExerciseAgent → 获取训练动作
  2. DietAgent → 生成饮食建议
  3. ScheduleAgent → 查天气 + 编排日程
  4. TrainerAgent → 汇总完整计划
  5. PlanReviewAgent → 自我审查修正

最终计划存入 FitnessPlan 表。
"""

import json
import traceback
from sqlalchemy.orm import Session
from app.models.schemas import PlanRequest
from app.models.orm_models import FitnessPlan
from app.agents.exercise_agent import run_exercise_agent
from app.agents.diet_agent import run_diet_agent
from app.agents.schedule_agent import run_schedule_agent
from app.agents.trainer_agent import run_trainer_agent
from app.agents.plan_review_agent import run_plan_review


class FitnessPlanService:
    """健身计划生成服务。"""

    @staticmethod
    def generate_plan(request: PlanRequest, db: Session) -> dict:
        """生成健身计划的完整流程。

        Args:
            request: 用户输入的 PlanRequest
            db: SQLAlchemy 数据库会话

        Returns:
            包含计划 ID 和内容的字典
        """
        user_info = (
            f"目标：{request.goal}\n"
            f"经验：{request.experience_level}\n"
            f"地点：{request.workout_location}\n"
            f"每周训练：{request.days_per_week} 天\n"
            f"计划周期：{request.duration_weeks} 周\n"
            f"饮食偏好：{request.diet_preference}\n"
            f"城市：{request.city or '未指定'}\n"
            f"备注：{request.notes or '无'}"
        )

        print(f"\n{'='*50}")
        print(f"[PlanService] 开始生成训练计划")
        print(f"[PlanService] 用户信息: {request.goal} | {request.experience_level} | {request.workout_location}")

        # Step 1: ExerciseAgent - 获取训练动作
        print(f"\n[ExerciseAgent] 开始搜索训练动作...")
        try:
            exercises_result = run_exercise_agent(
                goal=request.goal,
                experience=request.experience_level,
                location=request.workout_location,
                days=request.days_per_week,
            )
            print(f"[ExerciseAgent] 完成，结果长度: {len(exercises_result)} 字符")
        except Exception as e:
            print(f"[ExerciseAgent] 失败: {e}")
            exercises_result = "[]"
            traceback.print_exc()

        # Step 2: DietAgent - 生成饮食建议
        print(f"\n[DietAgent] 生成饮食建议...")
        try:
            diet_result = run_diet_agent(
                goal=request.goal,
                diet_preference=request.diet_preference,
            )
            print(f"[DietAgent] 完成")
        except Exception as e:
            print(f"[DietAgent] 失败: {e}")
            diet_result = '{"daily_calories": 2000, "meals": {}, "tips": []}'
            traceback.print_exc()

        # Step 3: ScheduleAgent - 查天气 + 编排日程
        print(f"\n[ScheduleAgent] 查询天气，编排日程...")
        try:
            schedule_result = run_schedule_agent(
                goal=request.goal,
                location=request.workout_location,
                days=request.days_per_week,
                city=request.city or "",
            )
            print(f"[ScheduleAgent] 完成")
        except Exception as e:
            print(f"[ScheduleAgent] 失败: {e}")
            schedule_result = '{"schedule": [], "weather_summary": "天气数据不可用"}'
            traceback.print_exc()

        # Step 4: TrainerAgent - 汇总完整计划
        print(f"\n[TrainerAgent] 汇总完整计划...")
        try:
            trainer_result = run_trainer_agent(
                user_info=user_info,
                exercises_result=exercises_result,
                diet_result=diet_result,
                schedule_result=schedule_result,
            )
            print(f"[TrainerAgent] 完成，结果长度: {len(trainer_result)} 字符")
        except Exception as e:
            print(f"[TrainerAgent] 失败: {e}")
            trainer_result = "{}"
            traceback.print_exc()

        # Step 5: PlanReviewAgent - 自我审查修正
        print(f"\n[PlanReviewAgent] 第 1 轮审查...")
        try:
            reviewed = run_plan_review(trainer_result)
            print(f"[PlanReviewAgent] 审查完成，计划已修正")
            final_plan = reviewed
        except Exception as e:
            print(f"[PlanReviewAgent] 失败: {e}")
            final_plan = trainer_result
            traceback.print_exc()

        # 解析并清理 JSON
        final_plan = _extract_json(final_plan)
        print(f"\n[PlanService] 最终计划生成完成")

        # 存入数据库
        try:
            plan = FitnessPlan(
                goal=request.goal,
                experience_level=request.experience_level,
                workout_location=request.workout_location,
                days_per_week=request.days_per_week,
                duration_weeks=request.duration_weeks,
                diet_preference=request.diet_preference,
                notes=request.notes or "",
                plan_content=json.dumps(final_plan, ensure_ascii=False),
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
            print(f"[PlanService] 计划已存入数据库，ID: {plan.id}")
        except Exception as e:
            print(f"[PlanService] 数据库写入失败: {e}")
            traceback.print_exc()
            db.rollback()
            return {"id": 0, "error": str(e), "plan_content": final_plan}

        return {
            "id": plan.id,
            "goal": plan.goal,
            "experience_level": plan.experience_level,
            "workout_location": plan.workout_location,
            "days_per_week": plan.days_per_week,
            "duration_weeks": plan.duration_weeks,
            **final_plan,
        }


def _extract_json(text: str) -> dict:
    """从 Agent 输出中提取 JSON 对象。

    Agent 可能输出包含 ```json ... ``` 标记或多余文字，
    此函数提取第一个 JSON 对象。
    """
    # 尝试提取 ```json ... ``` 代码块
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start) if "```" in text[start:] else len(text)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start) if "```" in text[start:] else len(text)
        text = text[start:end].strip()

    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试提取第一个 { ... }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end + 1])
        except json.JSONDecodeError:
            pass

    # 最后兜底
    return {"raw_output": text, "error": "无法解析为 JSON"}
