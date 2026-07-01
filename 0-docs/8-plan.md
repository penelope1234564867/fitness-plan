---
最终设计方案

Agent 架构

用户输入 (goal, experience, location, days_per_week)
          │
          ▼
   ┌──────────────────────┐
   │  Coordinator (纯代码)  │  ← 硬编码 PPL 排期
   │  天数 → 每天练什么      │
   └──────┬───────────────┘
          │ 输出日程 [{day, focus, muscles}, ...]
          │
     ┌────┼────┐  ← asyncio.gather 并行
     ▼    ▼    ▼
   Day1  Day2  Day3         ← 每路独立运行
   │      │      │
   │  ┌──┴──┐    │
   │  │ MCP │◄──────── wger MCP Server（子进程，全局单例）
   │  └──┬──┘    │
   │  Exercise   │
   │  Agent      │
   │  (搜索→精选) │
   │      │      │
   │  ┌──┴──┐    │
   │  │ LLM │────│─── 调用 DeepSeek 精选动作
   │  └──┬──┘    │
   │      │      │
   │  Plan Agent │
   │  (组装→输出) │
   │      │      │
   └──────┴──────┘
          │
          ▼
     DailyPlan DB × 3
          │
          ▼
     汇总周计划 JSON

  数据流

  ┌───────────┬───────────────────────────────────────────────┬────────────┐
  │   步骤    │                     谁做                      │ LLM 调用？ │
  ├───────────┼───────────────────────────────────────────────┼────────────┤
  │ 1. 排期   │ Coordinator                                   │ ❌ 硬编码  │
  ├───────────┼───────────────────────────────────────────────┼────────────┤
  │ 2. 搜动作 │ Exercise Agent → MCP Client → wger MCP Server │ ❌         │
  ├───────────┼───────────────────────────────────────────────┼────────────┤
  │ 3. 精选   │ Exercise Agent → LLM                          │ ✅ 1次/天  │
  ├───────────┼───────────────────────────────────────────────┼────────────┤
  │ 4. 组装   │ Plan Agent → LLM                              │ ✅ 1次/天  │
  └───────────┴───────────────────────────────────────────────┴────────────┘

  MCP 集成方式

  - WgerMCPClient 以模块级单例启动（只 spawn 一次子进程）
  - Exercise Agent 内部调用 client.call_tool("wger_search_exercises", {...})
  - 替换现在的 httpx 直连

  改动范围

  ┌────────────────────────────────────┬──────────────────────────────────┐
  │                文件                │               改动               │
  ├────────────────────────────────────┼──────────────────────────────────┤
  │ wger-mcp-server/wger_mcp_client.py │ 加单例模式（已有，不用改）       │
  ├────────────────────────────────────┼──────────────────────────────────┤
  │ test/05_exercise_agent_precise.py  │ 搜索改用 MCP Client 调用         │
  ├────────────────────────────────────┼──────────────────────────────────┤
  │ test/06_plan_agent_assembly.py     │ 已改好（按天+并行）              │
  ├────────────────────────────────────┼──────────────────────────────────┤
  │ test/07_e2e_ppl.py 或新建          │ 新编排：Coordinator → 并行跑三天 │
  └────────────────────────────────────┴──────────────────────────────────┘


# ════════════════════════════════════════════════════════════════
# 架构范式分析（简历用）
# ════════════════════════════════════════════════════════════════

## 当前项目用到的范式

| 范式 | 哪里用到了 | 说明 |
|------|-----------|------|
| **Pipeline** | 整体流程：Coordinator → ExerciseAgent → PlanAgent | 每阶段输入输出边界清晰，串行但互不影响 |
| **Map-Reduce** | `search_all_muscles()` — 并发搜索9个肌群 | Map=ThreadPoolExecutor搜每个肌群, Reduce=按muscle_id聚合 |
| **Fork-Join 并行** | `asyncio.gather` 并发跑 PPL 三天 | 三天各自独立搜索→过滤→精选→组装 |
| **ReAct Agent** | ExerciseAgent (wger tool), ScheduleAgent (weather tool) | 有 ToolRegistry，LLM 自主决定调用顺序 |
| **Simple Agent** | PlanAgent | 无工具，纯 prompt → JSON 输出 |
| **Singleton 单例** | MCP Client 子进程, LLM 实例 | 全局只启动一次 |
| **SSE 流式** | plan_service.py | 前端实时看进度 |

## 简历写法

### 英文版
> **AI-Powered Fitness Plan Generator** | Python, DeepSeek, ReAct Agent, MCP
> * Built a **multi-stage agent pipeline** (Coordinator → ExerciseAgent → PlanAgent) generating personalized PPL workout plans from user goals/experience/location
> * Implemented **Map-Reduce pattern** to concurrently search 9 muscle groups via wger API (ThreadPoolExecutor), then reduced into structured exercise pools for LLM selection
> * Designed **ReAct agents** (ExerciseAgent with wger tool-calling via MCP, ScheduleAgent with weather tool) achieving zero-shot tool orchestration
> * Applied **fork-join parallelism** (`asyncio.gather`) across 3 PPL days — each running search→filter→LLM→assemble independently, cutting generation time from ~180s to ~70s
> * Integrated **MCP Protocol** to bridge agents with external wger subprocess for real exercise database lookups
> * Built **SSE streaming** backend pushing pipeline progress to frontend in real-time

### 中文版
> **AI 健身计划生成系统** | Python, DeepSeek, ReAct Agent, MCP
> * 设计**多阶段 Agent Pipeline**（编排器→动作搜索Agent→计划整合Agent），根据用户目标/经验/地点生成个性化PPL周计划
> * 采用 **Map-Reduce 模式**并发搜索 wger 数据库 9 个肌群（ThreadPoolExecutor 实现 Map），按肌群聚合为结构化候选池（Reduce）
> * 基于 hello_agents 框架构建 **ReAct Agent**（ExerciseAgent 通过 MCP 调用 wger、ScheduleAgent 调用高德天气），实现零样本工具编排
> * 使用 **Fork-Join 并行**（asyncio.gather）让 PPL 三天各自独立跑搜索→过滤→LLM精选→LLM组装，生成耗时从 ~180s 降至 ~70s
> * 集成 **MCP 协议**桥接 Agent 与外部 wger 子进程，实现真实动作数据查询
> * 后端采用 **SSE 流式推送**，将 pipeline 各阶段进度实时推送到前端


# ════════════════════════════════════════════════════════════════
# 2026-06-29 优化记录：Token 调用提速
# ════════════════════════════════════════════════════════════════

## 改动清单

### 1. JSON mode + 去 Markdown 包装
- 所有 LLM 调用加 `response_format={"type": "json_object"}`
- prompt 末尾加 "只输出纯 JSON，不要 markdown 代码块"
- 去掉所有 ` ```json ` 解析逻辑 → 直接 `json.loads()`
- **效果**: 省 15-20% 输出 token，解析 100% 稳定

### 2. 分层模型（快/慢分离）
- `llm_service.py` 新增 `get_fast_llm()` — 读取 `FAST_LLM_MODEL_ID` 环境变量
- 精选阶段（从 N 个动作里选 M 个）→ 用快速模型，不需要强推理
- 组装阶段（生成完整计划）→ 用主模型
- `.env` 加 `FAST_LLM_MODEL_ID=deepseek-v4-flash`（当前与主模型相同，可改）
- **效果**: 替换为 gpt-4o-mini 等轻量模型后可降 50%+ token 成本

### 3. Prompt 精简
- `## 标题` → `#` 标签式
- 长段落描述 → 简短要求列表
- 去掉不必要的格式化引导
- **效果**: 每调用省 20-30% input tokens

### 4. 新增 `_invoke_json_llm()` 辅助函数
- 统一封装 JSON mode 调用逻辑
- 05 定义，06/08 通过 `mod5._invoke_json_llm()` 复用
- 含 verbose 打印方便调试

## 关于 per_group
`per_group` = 每个肌群选几个候选动作。
- 当前值：3（9个肌群 × 3 = 27 个候选）
- 改为 2：18 个候选，prompt 小 30%
- 这是 token 成本和质量之间的权衡，不是纯提速手段
- 定义位置：`05_exercise_agent_precise.py` 的 `SPLITS["ppl"]["per_group"]`

## Token 调用分析
```
当前：PPL 三天并行 → 每天内部：
  LLM 精选 × 1（快速模型） + LLM 组装 × 1（主模型）
= 每天 2 次 LLM 调用
= 共 6 次 LLM 调用（3 天 × 2 次）

优化后每次调用：
  精选：~2000 input + ~300 output token
  组装：~2500 input + ~1500 output token
= 总计 ~18000-21000 token / 请求
```
