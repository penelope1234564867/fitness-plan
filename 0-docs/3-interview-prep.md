# 中小厂 AI 应用开发面试 — 项目准备清单

> 目标：用「AI 智能健身助手」这个项目，让中小厂面试官觉得「这人来了就能干活」

---

## 一、项目现状评分

| 维度 | 当前分数 | 目标分数 | 差距 |
|------|---------|---------|------|
| 技术复杂度（多 Agent + MCP） | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ 已达标 |
| 工程完整性（全栈） | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🟡 缺测试 + Docker |
| 可演示性（README + 截图） | ⭐⭐ | ⭐⭐⭐⭐ | 🔴 缺 README 和截图 |
| AI 应用深度 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🟡 缺自适应反馈闭环 |
| 代码规范性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 🟡 需 lint + CI |

---

## 二、P0 — 必须做（入场券）

### 1. Docker 一键部署

**为什么重要：** 小公司面试官最怕招到「代码跑不起来」的人。你发 GitHub 链接过去，他 `git clone && docker-compose up` 就能看到效果，直接加分。

**做法：**
```
fitness-plan/
├── docker-compose.yml     # 编排 backend + frontend
├── backend/
│   └── Dockerfile         # Python 镜像
└── frontend/
    └── Dockerfile         # Nginx 静态文件 / Node 开发
```

**面试话术：**
> "项目根目录执行 docker-compose up 就能跑起来，前后端都容器化了。面试官你随时可以 clone 下来试。"

### 2. pytest 单元测试

**为什么重要：** 中小厂没有大厂的测试基础设施，他们特别看重你自己会写测试。

**做法：**
```
backend/
└── tests/
    ├── test_api.py          # 6 个 API 路由的 smoke test
    ├── test_exercise_agent.py
    ├── test_diet_agent.py
    └── test_plan_service.py
```

**最低要求：**
- 6 个 API 端点各有一个 200 测试
- generate_plan 至少测返回格式
- `pytest` 全绿

**面试话术：**
> "每个 Agent 和 API 路由都有单元测试覆盖，确保改代码不会破坏已有功能。"

### 3. GitHub Actions CI

**做法：** `.github/workflows/ci.yml`

```yaml
- run: pip install -r requirements.txt
- run: pytest
- run: npm install && npm run build
```

**面试话术：**
> "每次 push 自动跑测试和构建，保证主分支一直是可部署状态。"

---

## 三、P1 — 建议做（拉开差距）

### 4. README 配截图

**这是面试官第一眼看到的东西，比代码本身还重要。**

README 必须包含：
```
# 💪 AI 智能健身助手

一句话：输入目标 → AI 多智能体协作 → 个性化训练计划 → 打勾记录

## 技术亮点（面试官专看这块）
- ✅ 三种 Agent 范式混用（Simple + ReAct + Reflection）
- ✅ 自建 Wger MCP Server（MCP 协议实操）
- ✅ AI 自动质量审查（ReflectionAgent）
- ✅ Docker 一键部署

## 快速启动
docker-compose up

## 架构图
[图片]

## 截图
[图片1: 三步引导] [图片2: 日历主页] [图片3: 打勾清单]
```

### 5. 自适应调整功能

这是最能体现「AI 应用」区别于「普通 CRUD」的功能。

**用户说「太重了」→ 系统记录 → 下次生成计划时自动减轻重量**

**面试话术：**
> "用户说深蹲太重了，我记下来。下次 AI 生成计划时，这个动作的重量会自动调整。这不是写死的 if-else，是真正的 AI 自适应闭环。"

### 6. 架构图

不要用文字描述架构，**画一张图**。

用 excalidraw / draw.io / figma 画：
```
用户 → 前端(Vue3) → API(FastAPI) → 服务层 → Agent 编排
                                            ├── ExerciseAgent → Wger MCP
                                            ├── DietAgent → LLM
                                            ├── ScheduleAgent → 天气 MCP
                                            ├── TrainerAgent → 汇总
                                            └── PlanReviewAgent → 审查
                                            → SQLite DB
```

**面试话术：**
> "这是我的项目架构图，5 个 Agent 按流水线串行执行..."

---

## 四、面试时怎么聊这个项目

### 自我介绍话术（30 秒）

> "我做了一个 AI 健身计划助手。用户输入身高体重和目标，5 个 AI Agent 协作生成个性化训练计划，还能打勾记录、自动减轻重量。用了三种 Agent 范式，自建了 Wger 健身数据 MCP Server。项目已 Docker 化，提交流水线自动测试。"

### 常见问题准备

| 面试官问 | 你答 |
|---------|------|
| 为什么用多 Agent？ | 单一 Agent prompt 太长容易混乱，拆开每个职责清晰，单独可重试 |
| MCP 是什么？ | AI 调外部工具的标准协议，类似 USB — 统一了工具和 AI 的连接方式 |
| 为什么不用 LangChain？ | 太重，HelloAgents 只有 1000 行代码，我能看懂全貌 |
| 最大挑战？ | Wger MCP 字段映射的 bug，自建 Server 解决；ReflectionAgent 让质量提升 80% |
| 这个项目你做了什么？ | 从零搭建的，从数据库设计到前端日历到 AI 编排全是自己做的 |

---

## 五、P2 — 有时间再补

| 项目 | 原因 |
|------|------|
| ESLint + Prettier | 说明你注重代码规范 |
| 结构化 LLM 日志 | 能追踪每次 AI 调用的输入输出，方便 debug |
| TypeScript 类型全覆盖 | 减少运行时错误 |
| 离线 PWA | 健身应用没网也能看计划，加分但非必须 |

---

## 六、总结一句话

> **P0 决定能不能过简历筛选，P1 决定面试能不能聊出亮点，P2 是锦上添花。**

先把 Docker + 测试 + CI 搞定，你就已经超过 80% 的面试者了。
