# Fitness Plan — 项目概要

> 每次启动自动加载。不要问我「要不要读代码」，直接按此文件理解项目。

## 项目定位
AI 健身计划生成器。多 Agent 协作 + wger MCP 集成，根据用户目标/经验/偏好生成个性化训练计划。

**技术栈：**
- 后端: Python FastAPI + HelloAgents 框架 + SQLAlchemy (SQLite)
- 前端: Vue 3 + TypeScript + Pinia + Vite + Ant Design Vue
- 第三方: wger (开源健身数据库 MCP 服务)
- 部署: uvicorn (backend) + vite (frontend), 分离运行

## 目录结构

```
C:\Users\18194\Desktop\fitness-plan\
├── CLAUDE.md              ← 这个文件，项目级上下文（每次启动自动加载）
├── README.md              ← 已更新，不再引用已删除的 Agent
├── 0-docs/                ← 设计文档/开发计划（历史存档，仅供参考）
├── backend/
│   ├── run.py             → 启动入口: uvicorn app.api.main:app（端口 8000）
│   ├── requirements.txt   → hello-agents, fastapi, sqlalchemy, httpx 等
│   ├── .env               → API keys, LLM 配置
│   ├── app/
│   │   ├── config.py      → Settings (端口/LLM/key/CORS)
│   │   ├── database.py    → SQLAlchemy 初始化
│   │   ├── models/
│   │   │   ├── orm_models.py → 数据库表模型（users, workout_plans, plan_days 等）
│   │   │   └── schemas.py    → Pydantic 请求/响应 schema
│   │   ├── api/
│   │   │   ├── main.py    → FastAPI app + CORS + 路由注册（含 Windows GBK 兼容）
│   │   │   └── routes/
│   │   │       ├── fitness.py → /api/fitness/*（生成/查询计划）
│   │   │       ├── record.py  → /api/record/*（打卡记录）
│   │   │       ├── user.py    → /api/user/*（用户偏好资料）
│   │   │       └── wger.py    → /api/wger/*（wger 动作查询）
│   │   ├── agents/
│   │   │   ├── plan_agent.py      → 核心：训练计划组装器（热身→无氧→有氧→拉伸）
│   │   │   ├── exercise_agent.py  → wger MCP 动作搜索 Agent
│   │   │   └── test_mcp.py        → MCP 测试
│   │   ├── engine/                ← 健身科学引擎（核心业务逻辑）
│   │   │   ├── generator.py          → 训练计划生成
│   │   │   ├── adaptive_adjustment.py → 自适应调整（基于用户反馈）
│   │   │   ├── progressive_overload.py → 渐进超负荷计算
│   │   │   ├── exercise_rotation.py   → 动作轮换算法
│   │   │   ├── exercise_cache.py      → wger 动作本地缓存
│   │   │   └── mesocycle_manager.py   → 中周期管理
│   │   └── services/
│   │       ├── llm_service.py   → LLM 调用（OpenAI 兼容 API）
│   │       ├── plan_service.py  → 计划业务逻辑编排
│   │       └── wger_service.py  → wger 服务封装
│   ├── fitness.db           → SQLite 数据库文件
│   └── memory/              → 会话跟踪文件（非 Memory 系统）
├── frontend/
│   ├── package.json
│   ├── vite.config.ts       → Vite 配置
│   ├── vitest.config.ts     → 测试配置
│   └── src/
│       ├── main.ts          → Vue 入口
│       ├── App.vue          → 根组件
│       ├── views/
│       │   ├── OnboardingGuide.vue → 三步引导（个人→目标→日程）
│       │   ├── SetupWizard.vue     → 引导设置（简化版）
│       │   ├── MainPage.vue        → 日历主页（核心页面）
│       │   ├── GeneratingPlan.vue  → 生成计划等待页（SSE 流式）
│       │   └── ProfilePage.vue     → 用户资料页
│       ├── components/
│       │   ├── NavBar.vue          → 顶部导航栏（共享 Header 布局）
│       │   ├── CalendarPanel.vue   → 日历面板
│       │   ├── DayCell.vue         → 单日单元格
│       │   ├── DailyPlanPanel.vue  → 日计划详情
│       │   ├── ExerciseRow.vue     → 单动作行（checkbox 打卡）
│       │   ├── ExerciseDrawer.vue  → 动作详情 Drawer
│       │   ├── StepCard{Personal,Goal,Schedule}.vue → 引导步骤
│       │   ├── TodayCard.vue       → 今日概览
│       │   ├── CycleInfo.vue       → 周期信息
│       │   └── AIChatPanel.vue     → AI 对话面板
│       ├── stores/
│       │   ├── user.ts       → Pinia: 用户状态
│       │   ├── workout.ts    → Pinia: 训练状态
│       │   └── cycle.ts      → Pinia: 周期状态
│       ├── services/
│       │   ├── api.ts        → Axios HTTP 客户端（baseURL: /api）
│       │   └── sse.ts        → SSE 流式响应
│       └── types/index.ts    → TypeScript 类型定义
├── wger-mcp-server/          ← 独立 wger MCP 服务器（Python）
└── test/                     → 端到端测试脚本
```

## 关键架构信息

### 运行方式
- **后端**: `cd backend && python run.py` → http://localhost:8000 (Swagger: /docs)
- **前端**: `cd frontend && npm run dev` → http://localhost:5173
- **测试**: `cd backend && python ../test/06_plan_agent_assembly.py`（或 07, 08）

### 数据流
1. 前端引导页收集用户信息（个人资料→目标→日程）
2. 调用 `POST /api/fitness/generate-plan` 触发计划生成
3. 后端 PlanService 编排：
   - exercise_agent 从 wger 查询动作
   - plan_agent 按科学标准组装（热身→无氧→有氧→拉伸）
   - engine/ 模块做渐进超负荷/自适应调整/动作轮换
4. 结果存入 SQLite + SSE 流式返回前端
5. 用户通过日历页查看/勾选打卡

### 路由前缀
所有 API 以 `/api` 开头:
- `GET  /api/fitness/plans` — 获取计划列表
- `POST /api/fitness/generate-plan` — 生成计划（SSE 流式）
- `PUT  /api/record/exercise/{id}` — 打卡某动作
- `POST /api/user/profile` — 保存用户资料
- `GET  /api/wger/exercises` — 从 wger 搜索动作

### 当前开发状态（2026-07）
- ✅ 单界面模式、日历主页、打卡清单、动作 Drawer、共享 Header 布局
- ✅ wger MCP 集成、健身科学引擎（渐进超负荷/动作轮换/中周期管理）
- ✅ 三步引导（个人→目标→日程）、SSE 流式生成
- ⏳ 持续迭代中

## 常见误区（避免踩坑）
- `0-docs/` 下的 plan 文档是**历史记录**，不代表当前架构
- `backend/memory/` 是会话跟踪文件，**不是** Memory 系统
- README.md 已更新，之前提到已删除的 Agent（DietAgent/ScheduleAgent 等）

## 常用命令
```bash
cd backend && python run.py          # 启动后端
cd frontend && npm run dev            # 启动前端
cd frontend && npm test               # 前端测试
cd backend && python ../test/06_...   # 运行 E2E 测试
```
