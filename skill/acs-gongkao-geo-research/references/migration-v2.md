# v1.1 → v2.0 迁移说明

v2.0 是架构升级，不是对旧数据的字段改名。旧报告可保留原样；只有补齐可审计数据后才能声明 Schema 2.0。

1. 保留原 `queries.csv`，逐条补 `query_purpose`；旧泛词不能默认都视为 Measurement，需根据当时用途重判。
2. 从原始搜索记录重建 `query_results.csv`。没有逐题结果时不得反推或编造命中。
3. 将候选发现过程写入 `candidate_pool.csv`；若历史运行没有两轮发现记录，标记为 legacy，不伪造。
4. 把品牌、公司、老师和别名拆入 `entities.csv`；多对多关系写入 `entity_relations.csv`。
5. `scores.csv` 的 `role` 迁移为 `inclusion_basis`：Candidate→discovered，Specified 需按实际情形判为 user-requested 或 owned-forced，Benchmark→benchmark。
6. 补 `score_details.json`，逐维写理由和证据/查询编号。
7. 为重复 URL 补结构化复核字段；正文证据编号改为 `E\d+`。
8. 添加 v2 机器字段，重新生成 HTML 并跑严格门禁。

无法重建原始查询日志时，最稳妥的做法是保留 v1.1 报告并重新开展一次 v2 调查，不把旧汇总数伪装成可复算的 v2 数据。
