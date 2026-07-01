# Fitness Plan 🏋️

AI 健身计划生成器 — 基于 HelloAgents 框架 + wger MCP 集成 + Vue 3 前端。

多 Agent 协作，根据用户目标、经验水平和偏好生成个性化训练计划。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python FastAPI + HelloAgents + SQLAlchemy/SQLite |
| 前端 | Vue 3 + TypeScript + Pinia + Vite + Ant Design Vue |
| 健身数据 | wger (开源健身数据库 MCP 服务) |
| LLM | OpenAI 兼容 API |

## 快速开始

```bash
# 后端
cd backend && python run.py
# → http://localhost:8000 （Swagger: /docs）

# 前端（另开终端）
cd frontend && npm run dev
# → http://localhost:5173
```

## 项目结构

详见 [CLAUDE.md](CLAUDE.md)（项目级上下文，Claude Code 启动时自动加载）

## 状态

🚧 开发中。当前基于健身科学引擎（渐进超负荷/动作轮换/中周期管理）+ 单界面日历模式。
