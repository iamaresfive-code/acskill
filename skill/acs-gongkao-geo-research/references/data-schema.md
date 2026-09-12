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

`run_metadata.json` 属配置/契约/迁移状态层；旧 Run 经 `configure_measurement.py` 更新该文件是允许的。它不属于冻结 Raw Sampling Evidence，不能因为 metadata 可更新就改写 `ai_answers.jsonl`、`mentions_raw.json` 或采样日志。

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

### 2.2 `both` 的人工判定规则

`both` 是 entity-level 的人工审核结论，不能由 `cross_target_ai_signal`、`hybrid_signal`、`entity_type=studio/person`、名称形式或“工作室”等关键词自动推出。

品牌型 Entity 只有同时满足以下条件时才可判为 `both`：

1. institution 入口本身成立，可作为机构/品牌对象独立应对机构类问题；
2. IP 类问题中存在具名个人被 AI 作为独立推荐对象，而不是仅出现在机构师资页或从属介绍中；
3. 该具名个人与当前品牌存在明确归属关系，且证据足以支持其构成该品牌的 IP 入口；
4. 该具名个人未作为另一 canonical Entity 单列；若已单列，应优先保持品牌 `institution`、个人 `ip`，避免同一现实对象双重计分；
5. Reviewer 必须在 `evidence_basis` / `reviewer_reason` 记录 institution 与 IP 两个入口以及反双重计分检查。

反之，机构在 IP 类问题中被提及、名称含“工作室”、主体被标记为 person/studio、或 raw mention 跨 institution/ip，都只属于 review signal，不足以单独支持 `both`。

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

基础字段：

```text
entity_id
canonical_name
aliases
measurement_target
market_scope
operating_region
resolution_status
source_answer_ids
source_result_ids
notes
```

Target 规则：

- `resolution_status=unresolved`：`measurement_target` 只允许 `institution | ip`，表示发现来源轨道，不进入正式 Metrics；
- `resolution_status=resolved`：`measurement_target` 允许 `institution | ip | both`，是正式 entity-level measurement target；
- Target Closure 后可附加：

```text
reviewed_measurement_target      # institution | ip | both；必须与 resolved measurement_target 一致
measurement_target_review_status # confirmed
measurement_target_review_source # measurement_target_audit.csv
```

对 resolved emergent，Metrics / Robustness / Report 使用最终 entity target；当它为 `both` 时，必须在 institution/IP 两个 channel 各产生一条独立轨道。`reviewed_measurement_target` 是审计 provenance，不得与 canonical `measurement_target` 漂移。

## 11. ai_metrics.csv

**一行 = entity_id × measurement_target。** Universe 与 resolved AI-emergent 的 Hybrid `both` 都必须两行。

核心字段：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。Institution 与 IP 分母禁止混合。

Release Target Closure Validator 会构造完整 reviewed entity×target 集合，并同时拦截：缺行与多余未授权行。基础 Measurement Validator 同样按 effective entity target 展开 resolved emergent `both` 并核验 target-specific denominator。

### 11.1 measurement_qa_summary.json

诊断/交接报告不要手抄中间统计。最终 Annotation / Target / Citation / Robustness 落盘后运行：

```bash
python3 scripts/build_measurement_qa_summary.py <run-dir>
```

其中 `mention_intent_distribution`、`metrics_target_distribution` 等直接从最终持久化产物计算，用于避免 QA 修正后报告数字仍停留在修正前版本。Report Validator 会再次对账 `report_model.json` / `measurement_qa_summary.json` 与最终 `ai_mentions.csv` / `ai_metrics.csv`。

## 12. Variant / Repeat Robustness

```bash
python3 scripts/compute_variant_robustness.py <run-dir>
```

产出：`variant_robustness.csv`、`query_set_similarity.csv`、`robustness_summary.json`。

`positive_persistence_3of3_rate` 只表示“至少一次正向命中的 entity×query 中，三个 variant/run 全部正向命中的比例”，**不是 Overall Repeat Stability**。同时必须报告 0/N、1/N…N/N Hit Pattern、Pairwise Positive-set Jaccard、Exact Set Match。

若使用 semantic variants，必须披露 variant evidence status；legacy-reconstructed 不得包装成原生记录。Resolved AI-emergent `both` 必须在 institution/IP 两个 target 上分别进入 robustness 计算。

`snapshot` profile 不强制存在 Robustness artifacts；`release` 强制存在。但任何 profile 只要主动运行 robustness，就必须提供原生或 sidecar `query_variant_id`，不得由代码暗中构造 variant fallback。

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

Report 层收口：

```bash
python3 scripts/score_assets.py <run-dir>
python3 scripts/generate_charts.py <run-dir>
python3 scripts/build_report_model.py <run-dir>
python3 scripts/generate_report_docx.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage report --strict
python3 scripts/qa_report_docx.py <run-dir>
python3 scripts/test_v22.py
```

Release Validator 检查：target-specific denominator、effective query variant、sidecar identity/evidence、context isolation、Annotation Recheck、Citation Audit、Robustness artifacts、**Universe + resolved emergent Target Closure**、以及**高风险 Entity Resolution Recheck**。

任何 30%/80% 等经验阈值在多地区/多引擎校准前只可作为 diagnostic，不作为永久理论 gate。

## 15. 测试纪律

`test_v22.py` 只有第三方依赖确实缺失时才允许 DOCX/图表集成测试 SKIP。AssertionError、Validator failure、RuntimeError 等必须让测试失败并返回非 0；禁止宽泛捕获后伪装成 SKIP。

Target Closure 聚焦回归：

```bash
python3 scripts/test_stage24.py
```

`test_v22.py` 会调用该聚焦回归。覆盖 resolved emergent `both`、双 target Metrics 与双分母、Robustness 双轴、unresolved emergent 不进 metrics、未审 Target release gate、Target Audit Universe+emergent coverage、Resolution Audit gate、substring suspicion、Report/QA 最终 Intent counts、snapshot robustness policy。

## 16. deliverables/

v2.2 唯一正式交付：`deliverables/report.docx`。正式目录不得同时生成 report.pdf/report.html。

## 17. Report Layer 数据契约

Report Layer 是独立于 Measurement 的一层，回答「为什么机器可能认识这个主体」。完整链路：

```text
report_research_manifest.csv   （本轮新增公开网页证据，唯一证据源）
   ↓
asset_inputs.csv               （7 维资产评分 + 证据引用 + unknown 声明）
   ↓
asset_scores.csv               （加权资产成熟度 + Tier + 证据统计）
   ↓
concept_ownership.csv          （概念绑定：绑定类型 + 强度 + 来源 + 依据）
   ↓
analysis.json                  （事实/指标/代理指标/推断/建议 五层分离）
   ↓
report_model.json              （build_report_model.py 从最终持久化产物构建）
   ↓
deliverables/report.docx       （generate_report_docx.py 唯一渲染器）
```

**Report Entity Identity 与 Measurement Target 是不同维度。** Report Layer 的主体集合 =
`market_universe.csv` 中 `universe_status=included` 的主体 ∪ `ai_emergent_entities.csv` 中
`resolution_status=resolved` 的主体。`measurement_target=both` 的主体只产生**一行**资产记录，
不得因为同时具有 institution / ip 两条 Measurement 轨道而拆成两个品牌资产主体。
每个正式主体必须有明确状态——可以整行都是 unknown，但不得因为资料不足而静默丢行。

Report Layer 工作**不得回写** Market Universe，也不得把报告研究过程中新发现的实体
静默并入当前 Metrics / Universe；只能作为 report-layer observation 记录。

### 17.1 report_research_manifest.csv

本轮新增公开网页证据的唯一存储位置。**不得混入历史 AI Sampling Raw Evidence**
（`ai_answers.jsonl` / `mentions_raw.json` / `queries.csv` / `serp_results.csv` / `sampling_logs/*`）。

```text
evidence_id           # RR0001 形式，Run 内唯一
entity_id
entity_name
field                 # identity | official_website | official_social_account | regional_content
                      # | course_or_tool_asset | recent_content | contact_or_conversion
                      # | authoritative_reference | third_party_mention | concept_binding
source_url            # 真实检索结果或已打开页面地址；不得凭记忆拼写
source_title
source_grade          # A1 政府/高校/监管 | A2 第一方官网或官方账号 | B 稳定实名平台 | C 营销榜单/聚合
source_owner          # owned | third-party
platform              # official-site | wechat-mp | douyin | xiaohongshu | bilibili | zhihu
                      # | baijiahao | sohu | news-media | gov-edu | job-board | aggregator | other
domain
region_relevant       # true | false | unknown
recency_months        # 页面真实可见的发布时间距今月数；看不到日期必须留空，不得猜
content_type          # homepage | course-page | article | profile | directory | news | video | qa | job | other
access_status         # found | blocked | indexed-only | ambiguous | not-found
url_http_status       # 独立核验得到的 HTTP 状态码或错误码
url_content_hash      # 抓取正文 SHA256 前 16 位（快照元数据）
observed_at           # ISO 日期
concept / binding_type / strength / basis / source_type   # 仅 field=concept_binding 时填写
notes
```

**计分门槛**：只有 `source_url` 非空且独立核验可达（HTTP 2xx，或被反爬拒绝但地址真实存在的
403/468/502）的证据行才参与 Asset / Concept 计分。404、域名不可达、重定向环等**不可核验**
证据行必须整行丢弃，不得计入任何分数；无 URL 的主张保留在 manifest 中作为发现记录，
`access_status` 记为 `indexed-only`，**不参与计分**。

## 18. Asset Readiness 评分口径

`asset_inputs.csv`：

```text
entity_id
canonical_name
entity_clarity                  # 0-25 或 unknown
regional_semantic_density       # 0-20 或 unknown
open_web_assets                 # 0-15 或 unknown
external_authority              # 0-15 或 unknown
content_depth_freshness         # 0-10 或 unknown
data_tool_assets                # 0-10 或 unknown
platform_coverage               # 0-5  或 unknown
evidence_refs                   # 竖线分隔的 manifest evidence_id
evidence_date
confidence                      # high | medium | low
unknown_fields                  # 竖线分隔的无证据维度名
notes
```

`asset_scores.csv` = asset_inputs + 计算结果：`asset_readiness`、`asset_tier`、
`asset_readiness_basis_weight`、`evidence_count`、`independent_domains`、`owned_source_dependency`。

### 18.1 核心原则：没有证据 ≠ 0 分

未取到证据的维度必须写 **`unknown`**（等价写作 `not-observed` / `insufficient-evidence`），
并同时登记进 `unknown_fields`：

- unknown 维度**不计入分母**；
- `asset_readiness = round(100 × 已证据化维度得分 / 已证据化维度满分, 2)`；
- `asset_readiness_basis_weight` = 已证据化维度的满分之和；
- 已证据化权重 < 50/100 时 Tier 记 **U（证据不足）**，不得据此判断主体「没有资产」；
- 完全未取到证据时 `asset_readiness` 留空、Tier 留空，**绝不写 0**。

**不得把「本次没有搜到」解释为「主体一定没有」。**

### 18.2 固定换算表（可由 manifest 复算）

| 维度 | 满分 | 判定 |
|---|---|---|
| entity_clarity | 25 | 第一方官网或官方账号可达=25；第一方地址存在但抓取被拒=18；仅有第三方可核验描述=10；无=unknown |
| regional_semantic_density | 20 | `region_relevant=true` 的可核验证据行 ≥3=20；=2=15；=1=8；=0=unknown |
| open_web_assets | 15 | 独立域名 ≥6=15；4-5=12；2-3=8；1=4；0=unknown |
| external_authority | 15 | 第三方 A1 ≥2=15；A1=1=11；B≥2=7；B=1=4；仅 C=2；无=unknown |
| content_depth_freshness | 10 | `recency_months≤12` 的证据行 ≥3=10；1-2=7；无带日期证据=unknown |
| data_tool_assets | 10 | course_or_tool_asset / course-page / video 类证据 ≥3=10；1-2=6；0=unknown |
| platform_coverage | 5 | 出现平台 ≥3=5；=2=3；=1=2；0=unknown |

Tier：≥85 S；≥75 A；≥65 B+；≥55 B；≥45 B-；否则 C；已证据化权重 <50 记 U。

## 19. Concept Ownership 绑定分级

```text
concept
entity_id
canonical_name
strength            # 1-10，必须落在 binding_type 对应区间
binding_type        # owned-declaration | high-frequency-public-binding
                    # | third-party-description | single-incidental-mention
basis               # 具体依据：该页面/账号如何把概念与主体绑定
source_url
source_type         # official-site | official-account | media | third-party-platform
observed_at
evidence_ids
notes
```

强度区间（强制）：`owned-declaration` 8-10；`high-frequency-public-binding` 6-8；
`third-party-description` 3-5；`single-incidental-mention` 1-2。

概念绑定只能来自**可核验的公开内容绑定**：不得因为品牌名、行业常识或 Reviewer 印象自动赋权。
**单次第三方提及不得包装成强 Concept Ownership。**

## 20. analysis.json 五层分离

```json
{
  "schema_version": "2.2",
  "generated_from": { "...": "各最终产物行数" },
  "executive_summary": [],
  "facts": [], "metrics": [], "proxies": [], "inferences": [], "recommendations": [],
  "diagnoses": [], "strategy": [], "plan_90_days": [], "limitations": []
}
```

约束：

- `facts` / `metrics` / `proxies` / `inferences` / `recommendations` 五层**不得缺层**；
- 每层条目必须是 `{statement, basis}` 对象，两者都不得为空；
- `metrics` 条目还必须声明 `metric` 名称，且只能取自 `ai_metrics.csv` 的指标列、
  robustness 指标或资产维度名；
- **禁止把 GEO Visibility 指标写成真实市场份额或市场排名**；名词口径必须落在
  “本次协议下的可见度”；
- 统计数字必须由脚本从最终持久化产物实算，**不得手抄中间统计**。

## 21. Report Layer Validator 门禁

`validate_run.py <run-dir> --stage report --strict` 必须阻断空壳报告。以下错误码为强制项：

| 错误码 | 触发条件 |
|---|---|
| `empty-asset-readiness` | `asset_scores.csv` 缺失/只有表头/无有效数值，或 `report_model.asset_readiness` 为空 |
| `empty-concept-ownership` | `concept_ownership.csv` 缺失或无有效 Concept 数据，或 `report_model.concept_map` 为空 |
| `empty-analysis` | `analysis.json` 缺失，或 `executive_summary` / 五层 / `limitations` 为空，或条目缺 `statement`/`basis` |
| `empty-report-section` | `report_model` 的 `diagnoses` / `strategy` / `plan_90_days` / `risks` / `measurement_protocol` / `robustness` 为空，或 DOCX 缺核心章节、章节只有标题无正文 |
| `missing-report-docx` | `deliverables/report.docx` 不存在或无法作为 DOCX 打开 |
| `missing-report-chart` | `report_model.charts` 指向的图表文件不存在 |
| `asset-readiness-coverage` | asset_scores 未覆盖全部正式主体 |
| `asset-readiness-duplicate-entity` | 同一主体在 asset_scores 出现多行（both 不得拆成两个资产主体） |
| `asset-readiness-no-evidence` | 某维度有分数但没有任何 `evidence_refs`，评分无法从公开证据复算 |
| `asset-readiness-untraceable` | `evidence_refs` 指向 manifest 中不存在的证据 |
| `asset-readiness-unknown-mismatch` | 维度取值与 `unknown_fields` 声明不一致（缺证据却未声明 unknown） |
| `concept-ownership-untraceable` | 概念绑定缺 `source_url` / `basis` / `observed_at` / `binding_type` 等可核验字段 |
| `concept-strength-overstated` | `strength` 超出 `binding_type` 对应区间 |
| `placeholder-text` | DOCX 仍包含占位文案 |

**DOCX 核心章节门禁**：Validator 直接解析 `word/document.xml`，要求 15 个一级章节
（见 `generate_report_docx.py` 的 `REQUIRED_DOCX_SECTIONS`）全部存在，且每章标题之后
至少有一个非空正文段落、数据表格或图片；只有标题无正文即 FAIL。

渲染器本身也必须拒绝输出空壳：`generate_report_docx.py` 的 `_assert_complete()` 在关键
结构为空时直接抛错退出（exit 2），不再用占位文案兜底。

## 22. Report Layer 合成回归

`scripts/test_report_layer.py`（由 `scripts/test_v22.py` 调用）必须同时覆盖：

1. **负向**：Measurement 完整、Report Layer 为空的 Run →
   `validate_run.py --stage report --strict` **必须非 0**，且必须出现
   `empty-asset-readiness` / `empty-concept-ownership` / `empty-analysis` /
   `empty-report-section` / `missing-report-docx`；
2. **正向**：Report Layer 完整 fixture → **0 errors / 0 warnings / exit 0**；
3. **DOCX 章节空壳**：报告结构完整但某一级章节正文为空 → 必须 FAIL。
