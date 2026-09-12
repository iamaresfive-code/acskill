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
- resolved AI-emergent Target Closure；
- Golden Reality Check 后验发布门禁。

## 1. 旧 Run 缺 measurement_target / emergent target closure

旧 `market_universe.csv` 若没有 `measurement_target`，不得再按 `entity_type=studio/person` 自动推断。当前 Target Audit 同时覆盖：

- Market Universe 全体主体；
- `ai_emergent_entities.csv` 中全部 `resolution_status=resolved` 主体。

执行：

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 逐行填写 new_explicit_target / evidence_basis / reviewer_reason / review_status=confirmed
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
```

`measurement_target` 允许 `institution / ip / both`。`hybrid_signal`、`institution_evidence`、`ip_evidence`、`cross_target_ai_signal` 只是 Reviewer 提醒，**不能自动赋值 both**。若 `hybrid_signal=true`，必须写 `reviewer_reason` 说明为什么最终选择 institution/ip/both。

Market Bucket 与 Measurement Target 是两条独立轴；迁移 target 不得重写 A/B/C/D Market Bucket。

### AI-emergent 兼容字段

早期 `ai_emergent_entities.csv` 的 `measurement_target` 只能写单一 `institution/ip`。为避免破坏旧 Run，当前 apply 流程保留该兼容字段，并增加：

```text
reviewed_measurement_target       # institution | ip | both
measurement_target_review_status  # confirmed
measurement_target_review_source  # measurement_target_audit.csv
```

下游 Metrics / Robustness / Report **优先读取 `reviewed_measurement_target`**。因此 resolved emergent 也可以合法成为 `both`，并产生 institution 与 ip 两行 Metrics。

Release strict validation 会检查：全部 resolved emergent 已进入 Target Audit、reviewed target 已确认、以及最终 `ai_metrics.csv` 不多不少地覆盖 reviewed entity×target 集合。

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

Validator 与 `compute_variant_robustness.py` 会优先使用 raw Answer 的原生字段，缺失时读取 sidecar；两者冲突时直接报错。

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

## 4. Entity Resolution Recheck 与短名子串风险

Annotation Blind Recheck 不负责重新判断 canonical mapping。当前新增独立高风险 Resolution Audit：

```bash
python3 scripts/prepare_resolution_rechecks.py <run-dir>
```

它会选择以下 mention：

- AI-emergent；
- unresolved；
- verified-alias；
- citation-only；
- 两字以内中文短名与前后中文字符相连的 `short-name-boundary` 风险。

例如原文中的「检索中公职……」若被抽取成品牌「中公」，会被标记为 `short-name-boundary`，要求 Reviewer 明确复核 `entity_correct` 与 canonical mapping。

`resolution_rechecks.csv` 与 `annotation_rechecks.csv` 必须分开。Release strict validation 要求全部风险行完成独立复核；Reviewer 结论若与当前 `ai_mentions.csv` 不一致，不能只在审计表里“同意修改”，必须先修正上游/当前 Run 后再通过。

`prepare_annotation_tasks.py` 也会给相同短名风险增加 `substring_suspicion` 提示，但该提示不自动改标签。

## 5. 旧 semantic variants 的解释边界

如果历史 Run 因搜索缓存而使用语义等价检索式，但当时没有逐 Cell 保存实际变体文本，可迁移 `query_variant_id`，但必须披露：

```text
query_variant_mode = semantic-retrieval-variants
variant evidence = legacy-reconstructed
```

这批数据测的是 Query/Retrieval Robustness，不是 Pure Model Repeatability。不要事后虚构“实际变体 query 文本”。

## 6. 防止报告数字漂移

诊断/交接报告中的 Intent Distribution、Target 行数等必须来自**最终落盘文件**，不要继续复制 QA 修正前的中间统计。执行：

```bash
python3 scripts/build_measurement_qa_summary.py <run-dir>
```

生成：

```text
measurement_qa_summary.json
```

其 `mention_intent_distribution`、`metrics_target_distribution`、Target Audit / Resolution Recheck / Citation / Robustness 摘要均直接从最终持久化产物计算。`build_report_model.py` 也直接从最终 `ai_mentions.csv` 计算 Intent Distribution，避免类似“QA 后 listed/comparison 已变化，但报告还保留修正前数字”的漂移。

## 7. 推荐迁移顺序

```bash
# 1. 复制旧 Run；原始 handoff ZIP / raw files 保持只读
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 完成 Universe + resolved emergent Target Audit
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>

# 2. 为 legacy Answer 建 variant sidecar，不改 ai_answers.jsonl
python3 scripts/prepare_answer_variant_manifest.py <run-dir>

# 3. 如需全量重建 Annotation
python3 scripts/prepare_annotation_tasks.py <run-dir>
# Reviewer 完成 annotation_labels.csv
python3 scripts/apply_annotation_labels.py <run-dir>

# 4. 独立 Citation Audit
python3 scripts/prepare_citation_audit.py <run-dir>
# Reviewer 完成 citation_audit.csv
python3 scripts/apply_citation_audit.py <run-dir>

# 5. 独立 Entity Resolution Recheck
python3 scripts/prepare_resolution_rechecks.py <run-dir>
# Reviewer 完成 resolution_rechecks.csv；不重新判 intent

# 6. 重新计算并生成最终 QA summary
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
python3 scripts/build_measurement_qa_summary.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
```

迁移前后必须保存 raw hash manifest，确认 `ai_answers.jsonl / mentions_raw.json / queries.csv / sampling_logs` 等冻结原始资产未被改写。

## 8. 测试纪律

`test_v22.py` 只有在**第三方依赖确实缺失**时才允许 DOCX/图表集成测试 SKIP。AssertionError、Validator failure、RuntimeError 等真实失败必须向上抛出并让进程非 0 退出；禁止用宽泛 `except Exception` 把真实失败伪装成 SKIP。

Stage 2.4 新增聚焦回归：

```bash
python3 scripts/test_stage24.py
```

它专门覆盖：resolved emergent `both`、Target Audit apply、双分母 Metrics、Target Closure validator、短名 Resolution Recheck、最终 QA summary。
