# 多 Agent 并发策略

默认使用 `single-agent`。

只有用户确实让多个 Agent 同时读取或维护同一个知识库时，才启用 `multi-agent`。

## 核心原则

> Multiple readers, single writer.

允许多个只读任务并行，但同一时刻只有一个写执行者。

## 推荐状态

`state.json` 可记录：

- mode；
- status: idle / active；
- writer_id；
- task_id；
- task_summary；
- started_at；
- target_scope；
- handoff_from；
- updated_at。

## 写锁

写入前检查状态。另一执行者正常持锁时不得并行覆盖。

## 故障接管

只有可核实原执行者无法继续时才接管。接管先只读核对原任务、目标、已完成修改和未完成项。

接管只继承原授权范围，不得扩大任务。

## Handoff

交接信息应最小化但足够继续：任务边界、事实边界、目标文件、已完成项、待处理项、关键冲突。

## 普通用户

不需要开启本功能。单 Agent 是 v1.0 默认和推荐模式。
