# GEO 调研数据规范 v2.2

所有新 Run：

```json
{"schema_version":"2.2","skill_version":"2.2","official_output_format":"docx"}
```

## 1. run_metadata.json

核心字段：requested_region / normalized_region / research_scope、seed_entities、allow_discovery_supplement、research_mode、market_universe_confirmed、measurement_allowed、sampling_mode、ai_engines_expected、ai_engine_access_checked、observation_date、measurement_profile、answer_context_mode_expected、repeat_runs_expected、fresh_context_required、context_isolation_level、query_variant_mode、page_collection_status、fresh_context_note。

Target Closure 相关字段：
- `measurement_target_reviewed`
- `measurement_target_review_source`
- `resolved_emergent_target_reviewed`
- `resolved_emergent_target_review_count`
- `resolved_emergent_both_count`

`query_variant_mode` 只允许：
- `exact-query-repeat`
- `semantic-retrieval-variants`

第二种只能解释为 Query/Retrieval Robustness，不能称严格同条件随机重复。

## 2. market_universe.csv

```text
entity_id
canonical_name
aliases
entity_type
measurement_target   # institution | ip | both
user_seed
discovery_origin
market_scope
operating_region
market_role
activity_status
platform_native
salience_basis
universe_status
confirmation_status
downgrade_reason
notes
```

Market Bucket 与 Measurement Target 是两条独立轴。`measurement_target` 不得由 `entity_type`、名称是否含“工作室”或 Stage 2 AI Recall 静默推断。

- `institution`：只进入机构题分母；
- `ip`：只进入 IP/Expert 题分母；
- `both`：同一实体分别产生 institution 与 ip 两行 target-specific Metrics，分母绝不混合。

`universe_status`: included / observation / unresolved。Seed 只保证研究与解析，不自动 included、不加分。

### 2.1 measurement_target_audit.csv

对旧 Run、Hybrid/IP-led Brand、以及 resolved AI-emergent 主体统一运行：

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
```

关键字段：

```text
entity_id
canonical_name
entity_source          # universe | ai-emergent
resolution_status
stage1_market_role
market_bucket
entity_type
current_explicit_target
candidate_target
institution_evidence
ip_evidence
hybrid_signal
hybrid_signal_basis
cross_target_ai_signal
new_explicit_target
evidence_basis
reviewer_reason
changed
review_status
notes
```

Target Audit 必须覆盖：
- Market Universe 全体主体；
- `ai_emergent_entities.csv` 中全部 `resolution_status=resolved` 主体。

`hybrid_signal` 只是强制 Reviewer 注意 IP-led Brand / 工作室 / 品牌+老师入口 / 跨 target Raw Mention，不会自动赋值 `both`。若 `hybrid_signal=true`，应用前必须填写 `reviewer_reason`，说明为什么最终选择 institution/ip/both。

## 3. universe_review.json

A/B/C/D 四桶必须互斥且覆盖全部 Universe；distribution 应包含 measurement_target。补 target 不得改变已确认 Market Bucket。AI-emergent 不回写 Stage 1 Market Bucket。

## 4. queries.csv

```text
query_id
query_text
query_group
measurement_target   # institution | ip
region
status               # planned | sampled | skipped
```

Query 侧没有 `both`；both 只属于实体侧。

## 5. ai_answers.jsonl

新采样 Answer Cell 必须保存完整原文：

```json
{
  "answer_id":"A001",
  "query_id":"M01",
  "engine":"ChatGPT",
  "model":"...",
  "sample_run":1,
  "query_variant_id":"canonical",
  "context_id":"...",
  "fresh_context":true,
  "answer_context_mode":"external-search-augmented",
  "sampled_at":"ISO8601",
  "response_text":"完整原始回答",
  "citations":[],
  "notes":""
}
```

原始 Answer 是冻结证据。**不得为了通过新版 Validator 事后改写旧 `ai_answers.jsonl`。**

### 5.1 answer_variant_manifest.csv

历史 Run 若采样时还没有 `query_variant_id`，运行：

```bash
python3 scripts/prepare_answer_variant_manifest.py <run-dir>
```

生成 sidecar：

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

原 Answer 有字段时标 `native-recorded`；历史缺字段时按 `sample_run + query_variant_mode` 做迁移侧写并标 `legacy-reconstructed`。后者只是可审计迁移元数据，不代表当时逐 Cell 已记录真实变体搜索词。

Validator 与 `compute_variant_robustness.py` 优先读 raw Answer 的原生字段，缺失时读 sidecar；两者冲突直接报错。禁止静默 `run-{sample_run}` fallback。

## 6. mention_intent 五分类锚定

正式正向 Nomination 只计算 `recommended + listed`。

- `recommended`：明确推荐、优先、首选。
- `listed`：正常进入推荐列表/候选集合且未明确否定。**附带普通缺点仍然是 listed。**
- `comparison`：仅比较/背景参照，没有进入候选。
- `caveat`：明确条件性弱推荐、降低优先级或显著保留意见。
- `excluded`：明确不推荐、排除、不属于本题/地区。

判定优先级：明确否定/排除 → excluded；明确条件性弱推荐/降级 → caveat；明确推荐 → recommended；正常入榜未否定 → listed；仅参照 → comparison。

典型例：
- “第二名华图，体系成熟，但价格偏高。” → listed。
- “只有基础很强时才考虑甲，否则不优先。” → caveat。
- “甲不属于广东，本条不展开。” → excluded。

## 7. ai_mentions.csv 与 Annotation Tasks

```text
mention_id
answer_id
entity_id
mention_rank
nomination_rank
mentioned_name
match_method
resolution_status
mention_intent
top3
first_mention
entity_correct
citation_linked
citation_refs
concepts
notes
```

`mention_rank` 是 Raw Mention 顺序；`nomination_rank` 只在 explicit-name/verified-alias + resolved + entity_correct + recommended/listed 中连续编号。Top3/First Mention 从 nomination_rank 派生。

**Intent Annotation 不负责 Citation。** `apply_annotation_labels.py` 会把 citation 字段重置为空/false，随后必须走独立 Citation Audit。

`prepare_annotation_tasks.py` 对两字以内中文短名若与前后中文字符相连，会附：

```text
substring_suspicion=true
substring_suspicion_reason=...
```

这只是 Reviewer 风险提醒，不自动改变 `entity_correct`。例如「检索中公职……」中抽出的「中公」应进入人工复核，避免子串误匹配被算成正式提名。

## 8. Citation Audit：与 Intent Annotation 分链

流程：

```bash
python3 scripts/prepare_citation_audit.py <run-dir>
# Reviewer 审核实体级引用
python3 scripts/apply_citation_audit.py <run-dir>
```

`citation_audit.csv`：

```text
mention_id
answer_id
entity_id
canonical_name
answer_citation_count
candidate_citation_refs
linked_citation_refs
citation_linked
link_basis
review_status
notes
```

规则：
- candidate refs 必须等于该 Answer Cell 原始 citations；
- linked refs 必须真实存在于 candidate refs；
- 只有明确绑定该实体、其官方域或足以明确识别该实体的页面才可链接；
- 不能因为“回答整体有引用”把所有 mention 标 true；
- 也不能因为 Intent Reviewer 没填 citation 就静默归零；
- 没有实体级链接时也必须写 `link_basis`；
- Release Run 只要 Answer Cells 含 citations，就必须有完整 `citation_audit.csv` 和 `citation_audit_summary.json`，并同步回 `ai_mentions.csv`。

## 9. Annotation Blind Recheck 与 Entity Resolution Recheck

Release 使用 `annotation_rechecks.csv` 复核 Mention/Intent/Positive Set/顺序；Entity Resolution 另做 `resolution_rechecks.csv`，两者不得混算。

生成高风险 Resolution Recheck：

```bash
python3 scripts/prepare_resolution_rechecks.py <run-dir>
```

风险选择包括：AI-emergent、unresolved、verified-alias、citation-only、short-name-boundary。

`resolution_rechecks.csv` 字段：

```text
review_id
mention_id
answer_id
entity_id
canonical_name
mentioned_name
match_method
risk_flags
first_resolution_status
first_entity_correct
reviewer_resolution_status
reviewer_entity_correct
disagreement
resolution_outcome     # confirmed-existing | corrected-in-run | requires-upstream-fix
resolution
reviewer
review_status
notes
```

Release strict validation 要求全部当前风险 mention 被复核且 `review_status=confirmed`。如果 Reviewer 结论与当前 `ai_mentions.csv` 不一致，必须先修正当前 Run/上游映射再通过；不能只在审计表中记录“应该改”。`requires-upstream-fix` 会阻断 Release。

## 10. ai_emergent_entities.csv

AI/SERP 新主体先登记再解析；unresolved 原始提及不得删除。

兼容字段：

```text
entity_id
canonical_name
aliases
measurement_target              # legacy base target: institution | ip
market_scope
operating_region
resolution_status
source_answer_ids
source_result_ids
notes
```

Target Closure 后可增加：

```text
reviewed_measurement_target      # institution | ip | both，正式下游口径
measurement_target_review_status # confirmed
measurement_target_review_source # measurement_target_audit.csv
```

对 resolved emergent，Metrics / Robustness / Report 优先使用 `reviewed_measurement_target`。当它为 `both` 时，原 legacy `measurement_target` 保持单一 institution/ip 仅用于旧数据兼容，**不得作为最终测量口径**。

## 11. ai_metrics.csv

**一行 = entity_id × measurement_target。** Universe 与 resolved AI-emergent 的 Hybrid `both` 都必须两行。

核心字段：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。Institution 与 IP 分母禁止混合。

Release Target Closure Validator 会构造完整 reviewed entity×target 集合，并同时拦截：缺行与多余未授权行。

### 11.1 measurement_qa_summary.json

诊断/交接报告不要手抄中间统计。最终 Annotation / Target / Citation / Robustness 落盘后运行：

```bash
python3 scripts/build_measurement_qa_summary.py <run-dir>
```

其中 `mention_intent_distribution`、`metrics_target_distribution` 等直接从最终持久化产物计算，用于避免 QA 修正后报告数字仍停留在修正前版本。

## 12. Variant / Repeat Robustness

```bash
python3 scripts/compute_variant_robustness.py <run-dir>
```

产出：`variant_robustness.csv`、`query_set_similarity.csv`、`robustness_summary.json`。

`positive_persistence_3of3_rate` 只表示“至少一次正向命中的 entity×query 中，三个 variant/run 全部正向命中的比例”，**不是 Overall Repeat Stability**。同时必须报告 0/N、1/N…N/N Hit Pattern、Pairwise Positive-set Jaccard、Exact Set Match。

若使用 semantic variants，必须披露 variant evidence status；legacy-reconstructed 不得包装成原生记录。Reviewed AI-emergent `both` 必须在 institution/IP 两个 target 上分别进入 robustness 计算。

## 13. SERP / Page / AI 分离

`serp_results.csv` = 真实 Result Item；`serp_mentions.csv` 只允许 title/snippet；`page_mentions.csv` 只记录打开正文后的提及。

`page_collection_status=not-collected` 时空表表示“未采集”，不是正文 0 提及。

## 14. Release Validator 要点

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
python3 scripts/build_measurement_qa_summary.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
```

Release Validator 检查：target-specific denominator、effective query variant、sidecar identity/evidence、context isolation、Annotation Recheck、Citation Audit、Robustness artifacts、**Universe + resolved emergent Target Closure**、以及**高风险 Entity Resolution Recheck**。

任何 30%/80% 等经验阈值在多地区/多引擎校准前只可作为 diagnostic，不作为永久理论 gate。

## 15. 测试纪律

`test_v22.py` 只有第三方依赖确实缺失时才允许 DOCX/图表集成测试 SKIP。AssertionError、Validator failure、RuntimeError 等必须让测试失败并返回非 0；禁止宽泛捕获后伪装成 SKIP。

Target Closure 聚焦回归：

```bash
python3 scripts/test_stage24.py
```

覆盖 resolved emergent `both`、双 target Metrics、Target Closure gate、short-name Resolution Recheck、最终 QA summary。

## 16. deliverables/

v2.2 唯一正式交付：`deliverables/report.docx`。正式目录不得同时生成 report.pdf/report.html。
