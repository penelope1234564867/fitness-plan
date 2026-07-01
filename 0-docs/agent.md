     
  ---
  Agents 逻辑结构
   
                    ┌─────────────────────┐
                    │   plan_service.py   │ (编排层 - SSE 流式)
                    └──────┬──────┬───────┘
                           │ 并行 │
              ┌────────────┘      └────────────┐
              ▼                                 ▼
     ┌────────────────┐              ┌──────────────────┐
     │ exercise_agent │              │ schedule_agent   │
     │ (ReActAgent)   │              │ (ReActAgent)     │
     │ 搜索 wger 动作 │              │ 查天气→排日程    │
     │ wger API 工具  │              │ 高德天气工具     │
     └───────┬────────┘              └────────┬─────────┘
              └────────────┬──────────────────┘
                           ▼
                ┌────────────────────┐
                │    plan_agent     │ ← SimpleAgent, 整合→周计划 JSON
                │  (替换了旧版      │
                │   TrainerAgent +  │
                │   PlanReviewAgent)│
                └────────┬───────────┘
                         ▼
                存入 FitnessPlan 表 (DB)

  实际生产流程只用 3 个 agent：exercise_agent → 并行 schedule_agent → plan_agent 汇总

  ---