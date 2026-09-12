# v2.2 Word 咨询报告结构

唯一正式文件：`report.docx`。

建议 16–24 页，根据主体数量自然变化，不为页数注水。

1. 封面
2. 研究概览 / KPI
3. Executive Summary
4. Market Universe：本次到底研究谁
5. Measurement Protocol：引擎、context mode、context isolation、query variant mode、profile、采样日期
6. 全国品牌在本地区的 AI GEO
7. 本土 / 区域机构 AI GEO
8. Expert / IP GEO
9. AI-visible Observation / Emergent competitors
10. Query / Retrieval Robustness
11. Concept Ownership Map
12. GEO Asset Readiness
13. 重点主体诊断
14. 区域进入策略
15. 90 天 GEO 工程
16. Appendix / Research Audit

主榜不混合 national / local / IP；Observation / emergent 单列。**Market Bucket 由 Stage 1 冻结，Stage 2/3 不得因 entity_type 或 measurement_target 重新分桶。** Hybrid `measurement_target=both` 可在同一主体下展示 institution/ip 两套 target-specific metrics。

AI 表格优先列：

- Measurement Target；
- 命中次数 / Answer Cells（如 `5/60`）；
- Nomination Rate；
- Top3 Rate；
- First Mention Rate；
- Citation Rate；
- Engine Coverage Rate；
- Cross-model Consistency（单引擎显示 N.A.）；
- 资产成熟度。

正式报告不能只显示百分比而隐藏样本量。禁止同一主体无解释地一处 `/60`、另一处 `/24`；Hybrid 必须明确区分 institution 与 ip 两行/两套指标。

## Robustness 区块

正式 release 至少呈现：

- `positive_persistence_3of3_rate`；
- 0/N、1/N、2/N、N/N Hit Pattern；
- Pairwise Positive-set Jaccard；
- Exact Positive-set Match Rate。

`positive_persistence_3of3_rate` **不得写成 Overall Repeat Stability**。如果 `query_variant_mode=semantic-retrieval-variants`，标题必须写“Query/Retrieval Robustness（查询/检索鲁棒性）”，不能写成“模型重复稳定性”。

## 强制方法披露

每个 AI 可见度章节必须显式披露：

```text
measurement_profile
sampling_mode
answer_context_mode_expected
context_isolation_level
query_variant_mode
repeat_runs_expected
fresh_context_required
fresh_context_note（若 programmatic）
page_collection_status
observation_date / sampled_at range
```

若为 `external-search-augmented`，标题或脚注必须写“外部检索增强”。若为 `single-engine`，必须明确“单引擎”。若为 `programmatic` context isolation，必须明确“程序性隔离，不等同 API 级物理重置”。

`page_collection_status=not-collected` 时，不能把空 `page_mentions.csv` 表述成“网页正文 0 提及”。

## 语言纪律

当数据仍属单引擎、低鲁棒性或 semantic variants 时，可写：

- “在本次协议下正向提名率最高”；
- “在本次固定题池/单引擎/外部检索增强条件下未形成正向召回”；
- “该差异尚不足以证明稳定领先”。

禁止写：

- “真实第一”；
- “广东 GEO 第一”（若无足够跨模型/跨时点证据）；
- “AI 都不认识”；
- “所有模型都不会推荐”。

长解释放诊断卡，不塞入超宽表。
