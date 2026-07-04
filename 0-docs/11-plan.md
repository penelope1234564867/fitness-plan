
  让我把整个链路重新梳理一遍，你看看对不对劲。
   
  ---
  完整的计划生成 → 执行 → 反馈 链路

  第一步：初始生成（用户填完资料后）

  用户填了个人资料（身高/体重/年龄/性别/目标/经验/地点/日程）
          ↓
      [CoachAgent] 分析用户画像
          ↓ 输出：用户画像总结
            - "新手，目标增肌，居家训练（只有哑铃），每周 3 天"
            - "注意事项：新手优先学动作模式，不要上重量"
          ↓
      [ProgrammerAgent] 制定 16 周路线图 + 第 1 周详细计划
          ├── 从 wger 搜索适合用户的动作（按照经验+器械+目标）
          ├── 选定每个训练日的动作组合
          ├── 计算组次数（根据经验和目标）
          └── 输出：路线图 + 周计划 JSON
          ↓
      [PlanAgent] 组装每日训练
          ├── 热身（不是固定模板，而是根据当天训练肌群定制）
          ├── 主项（按复合→孤立排列）
          ├── 有氧（根据目标）
          └── 拉伸（针对当天练的肌群）
          ↓
      前端展示：推理过程（C）+ 路线图 + 第 1 周详情（A）

  第二步：每周循环（用户练了一周后）

      用户打卡完成一周
          ↓
      [AnalystAgent] 分析打卡数据
          ├── 完成率？每个动作的 RPE？有没有跳过？
          └── 判断：正常加量 / 需要换动作 / 需要减载
          ↓
      [ProgrammerAgent] 执行调整
          ├── 正常 → 下一周渐进超负荷（+重量 / +次数）
          ├── RPE 太高 → 换类似动作
          └── 疲劳累积 → 插入减载周
          ↓
      [CoachAgent] 生成周总结
          ├── "本周完成率 100%，下周卧推从 20kg → 25kg"
          └── 展示在 UI 上

  ---
  关键问题

  现在的问题是：当前代码里这个链路断在哪？

  1. exercise_agent 选动作太随机——wger 搜一堆出来，但没根据用户个人情况做推理筛选
  2. plan_agent 的热身/有氧/拉伸全是硬编码模板——谁练都是一样的动作
  3. 打卡完就完了——AnalystAgent/ProgrammerAgent/CoachAgent 根本不存在，没有任何分析调整
  4. generator.py 的渐进超负荷代码写了但没人调——链条没接上

  所以需要重建的不只是"3 个调整 Agent"，而是完整链路。你觉得这个链路设计合理吗？哪一步你特别在意？

    设计第一部分：Agent 系统架构
     
  先说清楚"怎么实现"——代码层面怎么组织、谁干什么。
  
  Agent 职责重定义
     
  我把原来的 5 个东西重新规划为 3 个 Agent + 1 个组装器：

  ┌─────────────────────────────┬──────────────────────────────────────────────────────┬───────────────────────────────────────────────┐
  │            名称             │                         职责                         │                   对应原有                    │
  ├─────────────────────────────┼──────────────────────────────────────────────────────┼───────────────────────────────────────────────┤
  │ CoachAgent 🆕               │ 用户画像分析、生成周总结、动作备注（所有"人话"部分） │ 部分新写                                      │
  ├─────────────────────────────┼──────────────────────────────────────────────────────┼───────────────────────────────────────────────┤
  │ ProgrammerAgent 🆕          │ 选动作、排组次数、执行渐进超负荷、动作轮换、减载     │ 合并旧的 exercise_agent + plan_agent 部分逻辑 │
  ├─────────────────────────────┼──────────────────────────────────────────────────────┼───────────────────────────────────────────────┤
  │ AnalystAgent 🆕             │ 分析打卡数据、判断是否需要调整                       │ 新写                                          │
  ├─────────────────────────────┼──────────────────────────────────────────────────────┼───────────────────────────────────────────────┤
  │ PlanAssembler（不是 Agent） │ 组装每日训练（热身/主项/有氧/拉伸），纯函数，无 LLM  │ 复用 plan_agent.py 的模板逻辑 + 改造          │
  └─────────────────────────────┴──────────────────────────────────────────────────────┴───────────────────────────────────────────────┘

  文件结构

  backend/app/
  ├── agents/
  │   ├── coach_agent.py       ← 🆕 用户画像 + 周总结 + 备注生成
  │   ├── programmer_agent.py  ← 🆕 选动作 + 调组次数 + 渐进超负荷
  │   └── analyst_agent.py     ← 🆕 打卡分析 + 调整判断
  ├── engine/
  │   ├── generator.py         ← 已有，要改（调 Agent 而非直接调 exercise_agent）
  │   ├── plan_agent.py        ← 已有，改名为 plan_assembler.py（纯组装）
  │   ├── adaptive_adjustment.py ← 已有，基本不动
  │   ├── progressive_overload.py ← 已有，ProgrammerAgent 调用
  │   └── exercise_rotation.py ← 已有，ProgrammerAgent 调用
  ├── services/
  │   ├── plan_service.py      ← 已有，大改（编排 Agent 流程）
  │   └── llm_service.py       ← 已有
  └── api/routes/
      └── fitness.py           ← 小改

  关键设计决策

  不用 MessageBus。 去年那个方案的 MessageBus + ToolRegistry + Orchestrator 太重了，对于当前的单用户场景，直接函数调用 + asyncio 队列就够用。等你觉得需要多用户并发再说。

  Agent 不通过事件通信，而是 PlanService 直接编排：
  # 伪代码 —— PlanService 是总指挥
  async def generate_plan(request):
      # 1. CoachAgent 分析用户
      profile = await coach_agent.analyze_user(request)

      # 2. ProgrammerAgent 根据画像选动作
      exercises = await programmer_agent.select_exercises(profile)

      # 3. PlanAssembler 组装每日训练
      day_plan = plan_assembler.assemble(exercises, profile)

      # 4. CoachAgent 加备注
      day_plan = await coach_agent.add_reasoning(day_plan, profile)

      return day_plan

  这样简单直接，Agent 就是有 LLM 调用能力的 Service，不需要事件总线。


● 你说得太对了。我看看 HelloAgents 到底有什么……

  原来 HelloAgents 有这个多东西：

  FunctionCallAgent    ← 函数调用 Agent
  PlanAndSolveAgent    ← 先规划再执行的 Agent
  ReActAgent           ← 推理+行动 Agent
  ReflectionAgent      ← 带反思能力的 Agent
  ToolRegistry         ← 工具注册中心
  ToolChain            ← 工具链
  memory               ← 记忆系统

  我们一直只用了个 HelloAgentsLLM 当 HTTP 客户端用，HelloAgents 的 Agent 框架完全没用上。

  所以我刚才说的那些"Service 编排"全都不对。正确的做法应该是：

  真正的 Agent = HelloAgents 提供的 Agent 类 + 我们注册的 Tool + Memory

  让我重新设计：

  ---
  修正后的设计

  ┌──────────────────────────────────────────────────────────────┐
  │                    ProgrammerAgent                           │
  │  (ReActAgent — 推理 + 行动)                                   │
  │  工具: search_exercises, calc_overload, swap_exercise ...    │
  │  记忆: 当前训练进度、用户偏好                                   │
  └──────────────────────────────────────────────────────────────┘
                                ↕
  ┌──────────────────────┐  ┌────────────────────────────────────┐
  │    CoachAgent         │  │        AnalystAgent                │
  │  (PlanAndSolveAgent)  │  │  (ReflectionAgent — 会反思分析)    │
  │  工具: generate_summary│  │  工具: analyze_week, detect_pattern│
  │  记忆: 历史对话、用户反馈│  │  记忆: 每周分析结果               │
  └──────────────────────┘  └────────────────────────────────────┘
                                ↕
                      ┌──────────────────┐
                      │   PlanAssembler   │
                      │  (纯函数，非 Agent)│
                      │  热身/拉伸模板组装  │
                      └──────────────────┘

  生成计划的流程（调用关系）：

  用户点击「生成计划」
          ↓
  ProgrammerAgent (ReActAgent) 启动
    Step 1: 调用 search_exercises(wger) 搜索候选动作
    Step 2: 分析用户资料，筛选合适的动作
    Step 3: 计算组次数
    Step 4: 调用 PlanAssembler 组装每日训练
    Step 5: 调用 CoachAgent 生成推理备注
          ↓
  CoachAgent (PlanAndSolveAgent) 启动
    Step 1: 分析用户画像
    Step 2: 为每个动作生成「教练说」
    Step 3: 生成阶段路线图描述
          ↓
  返回前端 SSE（含推理过程）

  每周调整流程：
  用户完成打卡
          ↓
  AnalystAgent (ReflectionAgent) 启动
    Step 1: 读取本周打卡数据
    Step 2: 反思分析（完成率、RPE趋势、异常检测）
    Step 3: 判断：正常加量 / 换动作 / 减载
          ↓
  ProgrammerAgent 启动
    Step 1: 执行渐进超负荷 / 动作轮换 / 减载
    Step 2: 生成下周计划
          ↓
  CoachAgent 启动
    Step 1: 生成周总结 + 下周预览

  ---