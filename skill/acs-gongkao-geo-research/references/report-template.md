# v2.2 Word 咨询报告结构

唯一正式文件：`report.docx`。

建议 16–24 页，根据主体数量自然变化，不为页数注水。

1. 封面
2. 研究概览 / KPI
3. Executive Summary
4. Market Universe：本次到底研究谁
5. Measurement Protocol：引擎、context mode、profile、repeat runs、fresh context、采样日期
6. 全国品牌在本地区的 AI GEO
7. 本土 / 区域机构 AI GEO
8. Expert / IP GEO
9. AI-visible Observation / Emergent competitors
10. Concept Ownership Map
11. GEO Asset Readiness
12. 重点主体诊断
13. 区域进入策略
14. 90 天 GEO 工程
15. Appendix / Research Audit

主榜不混合 national / local / IP；Observation / emergent 单列。

AI 表格优先列：

- 命中次数 / Answer Cells（如 `5/60`）；
- Nomination Rate；
- Top3 Rate；
- First Mention Rate；
- Citation Rate；
- Engine Coverage Rate；
- Cross-model Consistency（单引擎显示 N.A.）；
- 资产成熟度。

正式报告不能只显示百分比而隐藏样本量。尤其 snapshot / single-engine 下，`5/20` 与 `3/20` 的差异不得包装成稳定排名。

报告每个 AI 可见度章节必须显式披露：

```text
measurement_profile
sampling_mode
answer_context_mode_expected
repeat_runs_expected
fresh_context_required
observation_date / sampled_at range
```

若为 `external-search-augmented`，标题或脚注必须写“外部检索增强”；若为 `snapshot` 或 `single-engine`，必须写“单引擎/单时点快照”，不得表述成跨模型共识。

长解释放诊断卡，不塞入超宽表。
