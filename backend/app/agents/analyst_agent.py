"""AnalystAgent — 打卡数据分析 + 调整决策

使用 HelloAgents 的 ReflectionAgent（带反思能力）。
负责分析用户打卡数据，判断是否需要调整训练计划。

职责：
  - analyze_week_checkins() → 分析一周打卡数据（完成率、RPE趋势）
  - determine_adjustments() → 判断需要何种调整
  - detect_anomalies() → 检测异常模式（连续缺席、RPE突变等）
"""

import json
from typing import List, Optional

from hello_agents import ReflectionAgent
from sqlalchemy.orm import Session

from app.services.llm_service import get_llm
from app.engine.adaptive_adjustment import analyze_slot, analyze_week
from app.models.orm_models import Day, ExerciseSlot


# ── 系统提示词 ──────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个训练数据分析师（Analyst）。
你的职责是分析训练打卡数据，识别模式和问题，给出调整建议。

你会反思分析数据中的趋势、异常和潜在问题，
然后基于证据给出具体的训练调整建议。

你的风格：数据驱动、客观、具体。"""


# ── 分析提示词 ──────────────────────────────────────────────

ANALYSIS_PROMPT = """分析以下一周的训练打卡数据。

用户画像: {profile_summary}

周数据分析:
- 完成率: {completion_rate}%（{completed_slots}/{total_slots} 个动作完成打卡）
- 高 RPE 动作（RPE≥9）: {high_rpe_count} 个
- 平均 RPE: {avg_rpe}
- 训练天数: {trained_days}/{total_days}

各动作详情:
{slot_details}

请输出 JSON 格式（不要 markdown 代码块）：
{{
  "overall_assessment": "整体评价, 一句话",
  "key_findings": ["2-3 个关键发现"],
  "issues_detected": ["检测到的问题，如'某动作 RPE 持续偏高'"],
  "adjustment_suggestion": "keep / increase / swap / deload",
  "adjustment_reason": "调整理由, 30字内",
  "next_week_intensity": "maintain / increase / decrease",
  "specific_actions": [
    {{"action": "increase_weight", "slot_ids": [1, 2], "reason": "..."}},
    ...
  ]
}}"""


# ═══════════════════════════════════════════════════════════════
#  AnalystAgent 类
# ═══════════════════════════════════════════════════════════════

class AnalystAgent:
    """数据分析 Agent — 分析打卡 + 调整决策。

    同步方法设计，由调用方决定执行上下文。
    """

    def __init__(self):
        self._agent = ReflectionAgent(
            name="AnalystAgent",
            llm=get_llm(),
            system_prompt=SYSTEM_PROMPT,
        )

    # ═══════════════════════════════════════════════════════════
    #  公开方法
    # ═══════════════════════════════════════════════════════════

    def analyze_week_checkins(self, days: List[Day], profile: dict) -> dict:
        """分析一周打卡数据。

        Args:
            days: 本周所有 Day 对象（含 slots 关系）
            profile: 用户画像

        Returns:
            dict: 包含各项指标和分析结论
        """
        # 1. 用 engine 的自适应分析做基础统计
        week_analysis = analyze_week(days)

        # 2. 收集每个 slot 的详细分析
        all_slots = []
        for day in days:
            if hasattr(day, "slots") and day.slots:
                slot_analyses = []
                for slot in day.slots:
                    sa = analyze_slot(slot)
                    slot_analyses.append({
                        "slot_id": slot.id,
                        "name": slot.exercise_name,
                        "phase_type": slot.phase_type,
                        "rpe": getattr(slot, "rpe", 0) or 0,
                        "actual_sets": getattr(slot, "actual_sets", 0) or 0,
                        "target_sets": getattr(slot, "target_sets", 3),
                        "action": sa["action"],
                        "reason": sa["reason"],
                    })
                all_slots.append({
                    "day_label": day.day_label,
                    "focus": day.focus,
                    "is_completed": day.is_completed,
                    "rpe_score": getattr(day, "rpe_score", 0) or 0,
                    "slots": slot_analyses,
                })

        # 3. 计算衍生指标
        total_slots = len([s for d in all_slots for s in d["slots"]])
        completed_slots = sum(
            1 for d in all_slots for s in d["slots"]
            if s["actual_sets"] > 0
        )
        high_rpe_count = sum(
            1 for d in all_slots for s in d["slots"]
            if s["rpe"] >= 9
        )
        all_rpes = [s["rpe"] for d in all_slots for s in d["slots"] if s["rpe"] > 0]
        avg_rpe = round(sum(all_rpes) / len(all_rpes), 1) if all_rpes else 0
        trained_days = sum(1 for d in all_slots if d["is_completed"])

        # 4. 构建 slot 详情文本
        slot_lines = []
        for day_data in all_slots:
            slot_lines.append(f"\n  📅 {day_data['day_label']} ({day_data['focus']})")
            for s in day_data["slots"]:
                slot_lines.append(
                    f"    [{s['phase_type']}] {s['name']} — "
                    f"RPE={s['rpe']}, 完成 {s['actual_sets']}/{s['target_sets']} 组, "
                    f"建议={s['action']}"
                )

        # 5. LLM 综合反思分析
        prompt = ANALYSIS_PROMPT.format(
            profile_summary=profile.get("profile_summary", ""),
            completion_rate=round(completed_slots / max(total_slots, 1) * 100),
            completed_slots=completed_slots,
            total_slots=total_slots,
            high_rpe_count=high_rpe_count,
            avg_rpe=avg_rpe,
            trained_days=trained_days,
            total_days=len(all_slots),
            slot_details="\n".join(slot_lines),
        )

        text = self._agent.run(input_text=prompt).strip()
        analysis = self._parse_json(text, {
            "overall_assessment": "数据分析完成",
            "key_findings": [],
            "issues_detected": [],
            "adjustment_suggestion": "keep",
            "adjustment_reason": "",
            "next_week_intensity": "maintain",
            "specific_actions": [],
        })

        # 合并 engine 分析结果
        analysis["completion_rate"] = week_analysis["completion_rate"]
        analysis["high_rpe_ratio"] = week_analysis["high_rpe_ratio"]
        analysis["needs_deload"] = week_analysis["needs_deload"]
        analysis["no_checkin_ratio"] = week_analysis["no_checkin_ratio"]
        analysis["avg_rpe"] = avg_rpe
        analysis["day_details"] = all_slots

        return analysis

    def determine_adjustments(self, analysis: dict) -> dict:
        """基于分析结果判断具体调整方案。

        Args:
            analysis: analyze_week_checkins 返回的分析结果

        Returns:
            dict: {adjustments: [...], deload_needed: bool, summary: str}
        """
        suggestion = analysis.get("adjustment_suggestion", "keep")
        needs_deload = analysis.get("needs_deload", False)
        completion_rate = analysis.get("completion_rate", 0)

        adjustments = {
            "deload_needed": needs_deload,
            "type": suggestion,
            "reason": analysis.get("adjustment_reason", ""),
            "specific_actions": analysis.get("specific_actions", []),
        }

        # 基于数据的兜底逻辑
        if needs_deload:
            adjustments["type"] = "deload"
            adjustments["reason"] = "高 RPE 比例过高或打卡率过低，建议减载"
        elif completion_rate < 0.3:
            adjustments["type"] = "review"
            adjustments["reason"] = "打卡完成率偏低，需与用户沟通"

        return adjustments

    def detect_anomalies(self, days: List[Day]) -> List[dict]:
        """检测异常模式。

        Args:
            days: 本周所有 Day 对象

        Returns:
            List[dict]: [{type, severity, description}, ...]
        """
        anomalies = []

        # 检测连续缺席
        consecutive_missed = 0
        for day in days:
            if not day.is_completed:
                consecutive_missed += 1
            else:
                consecutive_missed = 0
        if consecutive_missed >= 3:
            anomalies.append({
                "type": "consecutive_miss",
                "severity": "high",
                "description": f"连续 {consecutive_missed} 天未打卡",
            })

        # 统计 RPE 趋势
        all_slots = []
        for day in days:
            if hasattr(day, "slots") and day.slots:
                all_slots.extend(day.slots)

        if all_slots:
            high_rpe_slots = [s for s in all_slots if (getattr(s, "rpe", 0) or 0) >= 9]
            if len(high_rpe_slots) > len(all_slots) * 0.5:
                anomalies.append({
                    "type": "high_rpe_pattern",
                    "severity": "medium",
                    "description": f"{len(high_rpe_slots)}/{len(all_slots)} 动作 RPE≥9，整体强度过高",
                })

        return anomalies

    # ═══════════════════════════════════════════════════════════
    #  内部方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _parse_json(text: str, default: dict) -> dict:
        """安全解析 LLM 返回的 JSON。"""
        text = text.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            print(f"  ⚠️ AnalystAgent JSON 解析失败，使用默认值")
            return default
