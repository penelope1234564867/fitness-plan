# Fitness Plan 🏋️

AI-powered fitness plan generator with multi-agent architecture and wger MCP integration.

Generates personalized training plans based on user goals, experience level, and preferences using a collaborative AI agent system.

## Architecture

- **ExerciseAgent** (ReActAgent) — Searches real exercises from wger database
- **DietAgent** (SimpleAgent) — Generates dietary recommendations
- **ScheduleAgent** (ReActAgent) — Checks weather and schedules workouts
- **TrainerAgent** (SimpleAgent) — Synthesizes all outputs into a complete plan
- **PlanReviewAgent** (ReflectionAgent) — Self-critiques and refines the plan

## Status

🚧 Project under active development. See [docs/plan.md](docs/plan.md) for current progress.
