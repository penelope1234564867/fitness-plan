
● 好的，我已经完整读完了所有相关代码。你的直觉完全正确——问题非常多。让我逐个拆解：
     
  ---
  问题 1（最严重）：generate_next_week 本质上是在"复制上周"而不是"生成下周"
     
  看 generator.py:543-570 的核心循环：
     
  # 第 521 行：遍历前一周的天
  for slot in prev_day.slots:   # ← 直接复制上周的每个 slot！
      ...
      new_slot = ExerciseSlot(
          exercise_name=slot.exercise_name,   # ← 同名
          phase_type=slot.phase_type,         # ← 同类型
          sort_order=slot.sort_order,         # ← 同顺序
          target_sets=params["target_sets"],  # 只改了组次重量
          target_reps=params["target_reps"],
          weight_kg=params["weight_kg"],
      )

  第 2 周和第 1 周是同样的动作，只有重量/次数微调。 没有调用 ProgrammerAgent、没有调用 assemble_one_day()、没有调用 wger_search()。所以：
  - ❌ 每周动作不会变
  - ❌ 没有热身/拉伸（只是上周的 warmup/stretch slot 被原样复制）
  - ❌ 没有 AI 精选

  ---
  问题 2（bug）：中周期边界动作轮换的代码必定崩溃

  exercise_rotation.py:93 返回：
  {"slot_id": slot.id, "old_exercise_id": old_id, "new_exercise_id": new_id}

  generator.py:482-483 构建：
  rotation_map = {r["slot_id"]: r["new_exercise_id"] for r in rotation_result}

  然后 547-550 行：
  rotation = rotation_map[slot.id]  # ← 这是一个 int！
  wger_id = rotation.get("wger_id")   # ← AttributeError: 'int' object has no attribute 'get'
  exercise_id = rotation.get("exercise_id")  # ← 同上

  int.get() 直接崩溃。 这个代码路径只要触发中周期切换就必挂。

  ---
  问题 3：热身动作都是硬编码，太多且无 AI 参与

  plan_assembler.py:160-173 的 _select_warmup()：

  "优先"组 + "全身"组 + "动态"组 → 去重 → 全返回

  每个训练日返回 8-10 个热身动作（DYNAMIC_WARMUP 一共 10 个，去掉完全重复的也有 8-9 个），而且每周都是同样的那套。完全没有：
  - 根据当天的具体动作来定制热身
  - AI 根据用户状态选择合适的热身
  - 根据阶段（增肌/减脂）调整热身强度

  ---
  问题 4：generate_next_week 不读用户历史数据

  目前只读 current_week（前一周）的打卡：
  prev_days = db.query(Day).filter(Day.week_id == current_week.id).order_by(Day.day_order).all()

  你要求的是——数据库里应该有一个"压缩后"的用户状态数据，比如：
  - 用户的运动能力趋势（RPE 是上升还是下降）
  - 动作偏好（哪些动作完成得好）
  - 伤病历史
  - 连续多周的进步曲线

  这样 generate_next_week 才能"了解用户是干什么的"。

  ---
  问题 5：性能问题

  问题 1 导致 generate_next_week 其实只是 DB 复制操作，按理说不应该卡。卡的原因可能是：

  - N+1 查询模式（第 426-427 行：先查 days，再逐天查 slots）
  - 前面 AnalystAgent 的 LLM 调用超时
  - 数据库事务冲突（同一个 session 里反复 flush()）

  ---
  问题 6：整体架构——generate_next_week 和 generate_init_week 严重不对称

  ┌──────────────────┬────────────────────────┬────────────────────┐
  │                  │   generate_init_week   │ generate_next_week │
  ├──────────────────┼────────────────────────┼────────────────────┤
  │ wger 搜索        │ ✅ 并行搜索所有肌群    │ ❌ 完全不搜索      │
  ├──────────────────┼────────────────────────┼────────────────────┤
  │ ProgrammerAgent  │ ✅ LLM 精选动作        │ ❌ 不调用          │
  ├──────────────────┼────────────────────────┼────────────────────┤
  │ assemble_one_day │ ✅ 热身+主项+有氧+拉伸 │ ❌ 不调用          │
  ├──────────────────┼────────────────────────┼────────────────────┤
  │ CoachAgent 备注  │ ✅                     │ ❌                 │
  ├──────────────────┼────────────────────────┼────────────────────┤
  │ 结果             │ 高质量的完整周         │ 复制上周的阉割版   │
  └──────────────────┴────────────────────────┴────────────────────┘

  ---
  要我继续推进到设计解决方桉的阶段吗？这个问题的整改涉及：

  1. 重新设计 generate_next_week 的数据流 — 让它像 init 那样走 wger + LLM + assemble
  2. 用户数据压缩存储 — 在数据库里维护"用户状态摘要"
  3. 热身 AI 化 — 根据当天动作动态生成热身
  4. 修复轮换 bug — 以及整个中周期切换逻辑
  5. 性能优化 — 修复 N+1、合并 DB 操作