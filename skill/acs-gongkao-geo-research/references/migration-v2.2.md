# v2.1.1 / early v2.2 → current v2.2 迁移说明

v2.2 是方法论升级，不是简单字段补丁。迁移时必须保持**原始采样证据不被为了过 Validator 而改写**。

## 保留
- User-specified 不加分；
- Evidence 分级与去重；
- IP 与机构分开；
- Observation / unresolved 不静默消失；
- Report Model；
- strict validation 思路。

## 替换
- Candidate Freeze → Market Universe Confirmation；
- Web Proxy Recall → AI Answer Measurement；
- 混合总榜 → 全国 / 本土 / IP 分榜；
- 公开网页五维“GEO总分” → GEO Asset Readiness；
- HTML/PDF/DOCX 三 Renderer → Single DOCX Renderer。

## 新增
- Seed-first Preflight；
- market_scope / market_role / explicit measurement_target；
- ai_answers.jsonl / ai_mentions.csv；
- serp_results / serp_mentions / page_mentions 物理分离；
- Annotation Blind Recheck 与 Resolution Audit 分离；
- Variant Robustness；
- 实体级 Citation Audit；
- Golden Reality Check 后验发布门禁。

## 1. 旧 Run 缺 measurement_target

旧 `market_universe.csv` 若没有 `measurement_target`，不得再按 `entity_type=studio/person` 自动推断。执行：

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 逐行填写 new_explicit_target / evidence_basis / reviewer_reason / review_status=confirmed
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

`measurement_target` 允许 `institution / ip / both`。`hybrid_signal`、`institution_evidence`、`ip_evidence`、`cross_target_ai_signal` 只是 Reviewer 提醒，**不能自动赋值 both**。若 `hybrid_signal=true`，必须写 `reviewer_reason` 说明为什么最终选择 institution/ip/both。

Market Bucket 与 Measurement Target 是两条独立轴；迁移 target 不得重写 A/B/C/D Market Bucket。

## 2. 旧 Run 缺 query_variant_id

### 原则

**不要为了通过 release Validator 修改冻结的 `ai_answers.jsonl`。**

新采样应在原 Answer Cell 内原生记录 `query_variant_id`；但对历史 Run，在字段尚未存在时使用 sidecar：

```bash
python3 scripts/prepare_answer_variant_manifest.py <run-dir>
```

输出：

```text
answer_variant_manifest.csv
answer_variant_manifest_summary.json
```

每行至少记录：

```text
answer_id
query_id
engine
model
sample_run
query_variant_id
evidence_status       # native-recorded | legacy-reconstructed
assignment_basis
notes
```

如果原 Answer 已有 `query_variant_id`，sidecar 标记 `native-recorded`；如果历史 Run 缺字段，则按 `sample_run + run_metadata.query_variant_mode` 做**迁移侧写**，标记 `legacy-reconstructed`。

`legacy-reconstructed` 只能表示“根据历史协议恢复的 variant 身份”，**不得描述成当时逐 Cell 已原生记录真实变体检索式**。

`validation_measurement.py` 与 `compute_variant_robustness.py` 会优先使用 raw Answer 的原生字段，缺失时读取 sidecar；两者冲突时直接报错。

## 3. Intent Annotation 与 Citation 必须分链

旧流程把 Citation 字段交给普通 Intent Reviewer 顺手填写，容易在全量重标时把实体级引用丢失。当前流程强制拆开：

```bash
python3 scripts/prepare_annotation_tasks.py <run-dir>
# Reviewer 只判 intent / match_method / entity_correct
python3 scripts/apply_annotation_labels.py <run-dir>

python3 scripts/prepare_citation_audit.py <run-dir>
# Reviewer 独立核验实体级 citation linkage
python3 scripts/apply_citation_audit.py <run-dir>

python3 scripts/compute_ai_metrics.py <run-dir>
```

`apply_annotation_labels.py` 会把 citation 字段重置为空/false；这不是“没有引用”，而是要求 Citation 必须经过独立 audit 后才能进入 Metrics。

`citation_audit.csv` 每条 mention 记录：Answer 原始 citations、最终 linked refs、link basis、review status。`linked_citation_refs` 必须真实存在于该 Answer Cell citations；没有实体级链接时也必须写 `link_basis`，防止静默全零。

Release Run 中，只要原 Answer 存在 citations，就必须有完整 `citation_audit.csv` 与 `citation_audit_summary.json`，并与 `ai_mentions.csv` 同步，否则 strict Validator 报错。

## 4. 旧 semantic variants 的解释边界

如果历史 Run 因搜索缓存而使用语义等价检索式，但当时没有逐 Cell 保存实际变体文本，可迁移 `query_variant_id`，但必须披露：

```text
query_variant_mode = semantic-retrieval-variants
variant evidence = legacy-reconstructed
```

这批数据测的是 Query/Retrieval Robustness，不是 Pure Model Repeatability。不要事后虚构“实际变体 query 文本”。

## 5. 推荐迁移顺序

```bash
# 1. 复制旧 Run；原始 handoff ZIP / raw files 保持只读
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 完成 target audit
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>

# 2. 为 legacy Answer 建 variant sidecar，不改 ai_answers.jsonl
python3 scripts/prepare_answer_variant_manifest.py <run-dir>

# 3. 全量重建 Annotation
python3 scripts/prepare_annotation_tasks.py <run-dir>
# Reviewer 完成 annotation_labels.csv
python3 scripts/apply_annotation_labels.py <run-dir>

# 4. 独立 Citation Audit
python3 scripts/prepare_citation_audit.py <run-dir>
# Reviewer 完成 citation_audit.csv
python3 scripts/apply_citation_audit.py <run-dir>

# 5. 重新计算
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
```

迁移前后必须保存 raw hash manifest，确认 `ai_answers.jsonl / mentions_raw.json / queries.csv / sampling_logs` 等冻结原始资产未被改写。

## 6. 测试纪律

`test_v22.py` 只有在**第三方依赖确实缺失**时才允许 DOCX/图表集成测试 SKIP。AssertionError、Validator failure、RuntimeError 等真实失败必须向上抛出并让进程非 0 退出；禁止用宽泛 `except Exception` 把真实失败伪装成 SKIP。
