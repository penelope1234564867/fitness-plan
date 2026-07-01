# 按天生成 PPL 计划 — 测试方案

## 思路

一天一天独立生成，三天并行执行。

## 流程

```
Day1(推): 搜[胸,肩,三头,前锯肌] → LLM精选 → LLM组装 → 存DB
Day2(拉): 搜[背,二头,斜方肌,肱肌] → LLM精选 → LLM组装 → 存DB
Day3(腿): 搜[腿前,腿后,臀,腹,小腿,比目鱼肌,腹外斜肌] → LLM精选 → LLM组装 → 存DB

三天用 asyncio.gather 并发跑
```

## 测试文件

新建 `test/08_e2e_day_by_day.py`，包含：

1. `generate_one_day()` — 搜当天肌群 → 精选 → 组装 → 返回 day JSON
2. `run_e2e()` — 并发跑三天，汇总结果
3. 先不存 DB，用内存 dict 存，验证能跑通

## 改动

- 05 的 `test_split` 按天调用（只传当天的 muscle_ids）
- 06 的 prompt 改成只组装 1 天（去掉 weekly_plans 层级）
- 用 asyncio 并发，不是 ThreadPoolExecutor
