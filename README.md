# Fitness Plan 🏋️

基于多智能体架构和 wger MCP 集成的 AI 健身计划生成器。

多 AI Agent 协作，根据用户目标、经验水平和偏好生成个性化训练计划。

## 架构

- **ExerciseAgent** (ReActAgent) — 从 wger 数据库搜索真实训练动作
- **DietAgent** (SimpleAgent) — 生成饮食建议
- **ScheduleAgent** (ReActAgent) — 查询天气并编排训练日程
- **TrainerAgent** (SimpleAgent) — 汇总所有输出为完整计划
- **PlanReviewAgent** (ReflectionAgent) — 自我审查并优化计划

## 状态

🚧 项目正在积极开发中。参见 [docs/plan.md](docs/plan.md) 了解当前进度。
