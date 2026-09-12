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

### AI-emergent 兼容与规范化

早期 `ai_emergent_entities.csv` 的 `measurement_target` 常只有单一 `institution/ip`。当前迁移流程保留原值直到 Reviewer 完成 Target Closure；一旦 `resolution_status=resolved` 且 audit 被 apply，最终 reviewed target 会直接写回：

```text
measurement_target               # institution | ip | both；resolved entity 的正式口径
reviewed_measurement_target      # 同步保存，作为 review provenance
measurement_target_review_status # confirmed
measurement_target_review_source # measurement_target_audit.csv
```

对 resolved emergent，`measurement_target` 与 `reviewed_measurement_target` 必须一致。若 Reviewer 判 `both`，两列都写 `both`，Metrics / Robustness / Report 分别产生 institution 与 ip 两条轨道。

`both` 仍然必须是人工证据结论，而不是信号自动推断。品牌型 emergent 只有在 institution 入口成立、IP 类问题中存在具名个人作为独立推荐对象、该个人与品牌归属关系明确、且该个人未作为另一 canonical Entity 单列时，才可判为 `both`。如果个人已经单列 Entity，应优先拆成品牌 `institution` + 个人 `ip`，避免双重计分。cross-target mention、`hybrid_signal`、studio/person 类型或名称形式仅用于提示 Reviewer。

对 `resolution_status=unresolved` 的 emergent，不做最终 entity-level hybrid 判定，`measurement_target` 仍只能是发现来源对应的单一 `institution/ip`，且不得进入正式 Metrics。

Release strict validation 会检查：全部 resolved emergent 已进入 Target Audit、reviewed target 已确认、registry target 与 audit 一致、以及最终 `ai_metrics.csv` 不多不少地覆盖 reviewed entity×target 集合。

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

### Snapshot / Robustness 协议

`snapshot` 不强制执行 Robustness；`release` 强制生成 Robustness artifacts。但如果任何 profile 主动执行 `compute_variant_robustness.py`，都必须有 native/sidecar `query_variant_id`。因此不存在“Validator snapshot 0/0，但 Robustness 靠隐藏 fallback 继续跑”的协议分叉：snapshot 可以不跑 robustness；一旦跑，variant evidence contract 与 release 相同。

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

其 `mention_intent_distribution`、`metrics_target_distribution`、Target Audit / Resolution Recheck / Citation / Robustness 摘要均直接从最终持久化产物计算。`build_report_model.py` 也直接从最终 `ai_mentions.csv` 计算 Intent Distribution；report validation 会把 Report Model / QA Summary 再与最终 `ai_mentions.csv`、`ai_metrics.csv` 对账，避免类似“QA 后 listed/comparison 已变化，但报告还保留修正前数字”的漂移。

## 7. run_metadata 是配置/契约层，不是冻结 Raw Sampling Evidence

旧 Run 首次迁移时，`configure_measurement.py` 会更新 `run_metadata.json`，用于记录当前 Measurement Contract（profile、context mode、repeat、variant mode、page collection status 等）。这是**允许的迁移操作**。

冻结 Raw Sampling Evidence 仍包括实际采样产生的原始资产，例如：

```text
ai_answers.jsonl
mentions_raw.json
queries.csv（若该 Run 已完成采样并作为 sampling contract 冻结）
sampling_logs / raw search traces / handoff ZIP 中的原始证据文件
```

`run_metadata.json` 属于配置/契约/迁移状态层，不应与上述 Raw Sampling Evidence 混为一谈。迁移前后仍应对真正冻结的 raw assets 保存 hash manifest；不能借“更新 metadata”之名改写 Answer 文本、Raw Mention 或原始采样日志。

## 8. 推荐迁移顺序

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

## 9. 测试纪律

`test_v22.py` 只有在**第三方依赖确实缺失**时才允许 DOCX/图表集成测试 SKIP。AssertionError、Validator failure、RuntimeError 等真实失败必须向上抛出并让进程非 0 退出；禁止用宽泛 `except Exception` 把真实失败伪装成 SKIP。

Stage 2.4 聚焦回归：

```bash
python3 scripts/test_stage24.py
```

并已由 `test_v22.py` 作为核心门禁调用。它覆盖：resolved emergent `both` 落盘与双 target Metrics、institution/IP 分母分离、Robustness 双轴、unresolved emergent 排除、resolved emergent 未审 Target Release FAIL、Universe+emergent audit coverage、Resolution Audit 缺失/未完成 gate、短名 `substring_suspicion`、最终 Report/QA Intent counts、snapshot robustness policy。
