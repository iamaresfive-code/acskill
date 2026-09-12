# acs-gongkao-geo-research v2.2

> 公考行业 GEO 竞争研究 Skill：先确认研究谁，再测 AI 到底提不提，最后用公开资产解释原因。

正式输出固定为 Word：`deliverables/report.docx`。

## 核心结构

1. **Market Universe**：User Seed + 系统发现 + 市场显著性审核；
2. **AI Answer Measurement**：固定无品牌题真实采样；
3. **GEO Asset Readiness**：公开资产解释层。

Market Bucket 与 Measurement Target 是两条独立轴：

```text
measurement_target = institution | ip | both
```

`both` 产生 institution / ip 两套 Metrics，但不能反向改变 Stage 1 A/B/C/D Market Bucket。

## Stage 1：Target Review

新旧 Run 均应显式审定 target：

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 填 new_explicit_target / evidence_basis / reviewer_reason / confirmed
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

`hybrid_signal`、organization/IP evidence、cross-target raw mentions 只是 Reviewer 提醒，**不自动赋值 both**；hybrid 行必须解释最终判断。

## Stage 2：Measurement Contract

先真实探测可用 AI / AI Search 引擎，再配置：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine \
  --context-mode external-search-augmented \
  --profile release \
  --repeat-runs 3 \
  --fresh-context \
  --context-isolation programmatic \
  --query-variant-mode semantic-retrieval-variants \
  --page-collection-status not-collected \
  --observation-date YYYY-MM-DD
```

`external-search-augmented` 只能解释为外部检索增强下的 AI Answer Visibility；`semantic-retrieval-variants` 只能解释为 Query/Retrieval Robustness。

## Legacy Variant Migration：不改 Raw Answer

新采样应原生记录 `query_variant_id`。历史 Run 缺字段时不要改写冻结的 `ai_answers.jsonl`，使用：

```bash
python3 scripts/prepare_answer_variant_manifest.py <run-dir>
```

生成 `answer_variant_manifest.csv`：

- `native-recorded`：原 Answer 本身已记录；
- `legacy-reconstructed`：根据 sample_run + run-level variant mode 做可审计迁移侧写。

Validator 与 Robustness 都读取同一套 effective variant；raw 与 sidecar 冲突直接报错。legacy-reconstructed 不得包装成原采样时已逐 Cell 保存真实变体检索词。

## Annotation Pipeline

```bash
python3 scripts/prepare_annotation_tasks.py <run-dir>
# Reviewer 只判 intent / match_method / entity_correct
python3 scripts/apply_annotation_labels.py <run-dir>
```

只有 explicit-name/verified-alias + resolved + entity_correct + recommended/listed 才进入 Nomination。

榜单成员附带普通短板仍然是 `listed`；只有明确条件性弱推荐/降优先级才是 `caveat`。

## Citation Pipeline：与 Intent 独立

Intent Reviewer 不负责 Citation。`apply_annotation_labels.py` 会清空 citation linkage，之后必须运行：

```bash
python3 scripts/prepare_citation_audit.py <run-dir>
# Reviewer 核验实体级 citation refs
python3 scripts/apply_citation_audit.py <run-dir>
```

Release Answer Cells 只要存在 citations，就必须完成 `citation_audit.csv + citation_audit_summary.json`。不能因为“回答整体有引用”把所有品牌标 true，也不能因为重标 Intent 而把 Citation Rate 静默归零。

## Metrics 与 Robustness

```bash
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
```

`ai_metrics.csv` 一行 = `entity_id × measurement_target`。Hybrid both 必须两行。

透明输出：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。

Robustness 输出：
- positive_persistence_3of3_rate；
- 0/N…N/N Hit Pattern；
- Pairwise Positive-set Jaccard；
- Exact Positive-set Match。

`positive_persistence_3of3_rate` 不是 Overall Repeat Stability。

## Recheck

Annotation Blind Recheck 与 Resolution Audit 分离。Answer Cells >=10 时 Annotation Recheck 至少 20%。一致率阈值目前只是 diagnostic/provisional，不是行业理论标准。

## Validator

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

Release Validator 会检查 target-specific denominator、variant sidecar、context isolation、Annotation Recheck、Citation Audit、Robustness artifacts 等。

## 测试纪律

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

只有真正缺少 `matplotlib/python-docx` 等第三方依赖时，DOCX/图表集成测试才允许明确 SKIP。AssertionError、Validator failure、RuntimeError 必须 FAIL / 非0退出，不能伪装成 SKIP。

## 发布纪律

Synthetic Test 全绿不等于发布。正式 v2.2 仍需广东、天津、山东真实地区回归；当前 Draft 不直接 merge main。

报告中禁止把单引擎、检索增强、低鲁棒性结果写成“真实第一”“所有 AI 都不认识”“GEO 为零”。

详细数据合同见 `references/data-schema.md`，方法边界见 `references/methodology.md`，旧 Run 迁移见 `references/migration-v2.2.md`。
