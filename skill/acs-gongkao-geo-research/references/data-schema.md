# GEO 调研数据规范 v2.2

所有新 Run：

```json
{"schema_version":"2.2","skill_version":"2.2","official_output_format":"docx"}
```

## 1. run_metadata.json

核心字段：

- requested_region / normalized_region / research_scope
- seed_entities / allow_discovery_supplement / research_mode
- market_universe_confirmed / measurement_allowed
- sampling_mode / ai_engines_expected / ai_engine_access_checked
- observation_date
- measurement_profile: snapshot | release
- answer_context_mode_expected: native | engine-native-search | external-search-augmented
- repeat_runs_expected / fresh_context_required
- context_isolation_level: api-isolated | product-isolated | programmatic
- query_variant_mode: exact-query-repeat | semantic-retrieval-variants
- page_collection_status: collected | partial | not-collected
- fresh_context_note：当 `context_isolation_level=programmatic` 时必须披露残余上下文污染风险

`semantic-retrieval-variants` 表示同一个 canonical query 使用语义等价检索式变体测试 Query/Retrieval Robustness；不得描述为“完全同条件随机重复”。

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

`market_scope`: national / regional / local / unknown。

`market_role`: national-benchmark / local-core / local-active / expert-ip / historical / observation / unclassified。

`measurement_target` 是**显式测量轴**，不得由 `entity_type`、名称是否含“工作室”、或 `market_role` 在 Stage 2/3 重新推断：

- `institution`：只进入机构题分母；
- `ip`：只进入 IP/Expert 题分母；
- `both`：同一实体同时进入机构题与 IP 题，但产生两行 target-specific Metrics，分母绝不混合。

Market Bucket 与 Measurement Target 是两条独立轴。例如一个主体可以 `market_role=local-active` 且 `measurement_target=both`；Stage 2/3 不得据此把它从本地机构桶自动改到 Expert/IP 桶。

`universe_status`: included / observation / unresolved。v2.2 不提供静默硬排除状态；observation/unresolved 仍参加 Measurement。

`confirmation_status`: needs-review / confirmed。Market Universe 确认前，所有主体必须显式审定 `measurement_target`。

`downgrade_reason`: 空 / seo-only / insufficient-evidence / unresolvable / user-ruling / historical / out-of-scope。

User Seed 只保证研究与解析，不自动 included、不加分。Seed 与 System Discovery 同名时必须字段级合并。

## 3. universe_review.json

至少包含：schema_version、region、research_mode、market_universe_confirmed、measurement_allowed、total_entities、user_seed_count、system_discovery_count、seed_also_discovered_count、platform_native_count、expert_ip_included_count、distribution、buckets、bucket_audit、seo_only_downgraded、unresolved_or_weak。

`distribution` 应包含 `measurement_target` 分布。A/B/C/D 四桶必须互斥且并集覆盖全部 Universe 主体。

## 4. queries.csv

```text
query_id
query_text
query_group
measurement_target   # institution | ip
region
status               # planned | sampled | skipped
```

Query 本身只有 institution/ip 两类，不使用 both；both 属于实体侧。

## 5. ai_answers.jsonl

每行一个 Answer Cell：

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

Release 模式必须记录 `query_variant_id`。若 `query_variant_mode=semantic-retrieval-variants`，不同 sample_run 对应不同 variant id；它们用于鲁棒性测试，不得冒充完全同 query 的随机 repeat。

## 6. mention_intent 五分类锚定

`ai_mentions.csv` 中每一条 Raw Mention 都必须保留。正式正向 Nomination 只计算 `recommended + listed`。

### recommended
AI 明确表达推荐、优先、首选、重点考虑。

正例：
- “我更推荐甲机构和乙机构。”
- “第一选择可以先看甲机构。”
- “如果只选一家，我会优先甲机构。”

反例：
- “甲机构规模较大。”（仅事实）
- “相比甲机构，乙更偏线上。”（comparison）
- “甲机构不适合本题。”（excluded）

### listed
主体被正常纳入推荐列表、排行榜、候选名单、可选方案，且没有明确否定。**列表成员附带普通优缺点仍然是 listed。**

正例：
- “推荐名单：1甲，2乙，3丙。”
- “第二名乙机构，线下体系成熟，但价格偏高。”
- “可关注甲、乙、丙，其中乙更适合基础较强者。”

反例：
- “甲仅用于与乙作比较。”（comparison）
- “甲只在极少数条件下勉强可选，其他人不建议。”（caveat）
- “甲不属于广东，本条不展开。”（excluded）

### comparison
只作为比较、背景或参照对象出现，没有进入推荐候选集合。

正例：
- “相比中公，粉笔更偏线上。”且没有把中公列为候选。
- “甲的班型比乙更大。”仅作比较。
- “业内常把甲和乙放在一起比较。”

反例：
- “甲、乙都可以考虑。”（listed/recommended）
- “推荐第二名甲，但价格偏高。”（listed）
- “不建议甲。”（excluded）

### caveat
存在**明确的条件性弱推荐、降低优先级或显著保留意见**。普通短板说明不是 caveat。

正例：
- “只有基础很强时才建议考虑甲，否则不优先。”
- “甲可以作为备选，但不建议放在前两位。”
- “若预算极低可考虑甲，其他情况更建议乙。”

反例：
- “甲值得考虑，但价格较高。”（仍可 listed/recommended）
- “第二名甲，师资稳定但班型较大。”（listed）
- “甲不适合广东省考。”（excluded）

### excluded
AI 明确不推荐、排除、不属于研究地区/题意、不纳入候选。

正例：
- “花生十三、高照并非广东专属，本条不展开。”
- “甲不建议报。”
- “甲不属于本题讨论范围。”

反例：
- “甲有短板但仍可考虑。”（listed/recommended）
- “甲只适合特定人群。”（通常 caveat）
- “甲与乙经常被比较。”（comparison）

### 判定优先级

1. 明确否定/排除 → excluded；
2. 明确条件性弱推荐/降低优先级 → caveat；
3. 明确推荐/优先 → recommended；
4. 正常进入候选列表且未否定 → listed；
5. 仅作参照 → comparison。

“推荐/列入 + 普通短板”不得仅因短板自动降为 caveat。

## 7. ai_mentions.csv

```text
mention_id
answer_id
entity_id
mention_rank
nomination_rank
mentioned_name
match_method          # explicit-name | verified-alias | citation-only
resolution_status     # resolved | unresolved
mention_intent        # recommended | listed | comparison | caveat | excluded
top3
first_mention
entity_correct
citation_linked
citation_refs
concepts
notes
```

`mention_rank` = Raw Mention 文本出现顺序；`nomination_rank` = 只在 resolved + entity_correct + recommended/listed 中连续编号。Top3/First Mention 以 nomination_rank 派生。unresolved 仍保留 Raw Mention，但不得进入 Positive Metrics。

## 8. Annotation Blind Recheck 与 Resolution Audit 分离

Release 模式生成 `annotation_rechecks.csv`：

```text
review_id
answer_id
first_positive_set
second_positive_set
first_intents
second_intents
disagreement
resolution
reviewer
notes
```

第二 Reviewer 可看到原始 Answer、候选 Mention span、canonical entity 以及**冻结的** resolution_status；它只复判 Mention/Intent/正向集合/顺序，不重新猜工商或实体解析状态。

Entity Resolution 正确性另做 `resolution_rechecks.csv`。不要把 Annotation Agreement 与 Resolution Agreement 混成一个百分比。80% 等一致率目前只能作为 provisional engineering target，不是行业通用理论门槛。

## 9. ai_emergent_entities.csv

```text
entity_id
canonical_name
aliases
measurement_target   # institution | ip
market_scope
operating_region
resolution_status
source_answer_ids
source_result_ids
notes
```

AI/SERP 新主体先登记再解析；unresolved 原始提及不得物理删除。

## 10. ai_metrics.csv

**一行 = entity_id × measurement_target。** Hybrid `both` 必须有两行。

核心字段包括：entity_id、canonical_name、measurement_target、answer_cells、raw_mentioned_answers、raw_mention_rate、mentioned_answers、nomination_rate、top3_rate、first_mention_rate、citation_rate、engine_coverage_rate、cross_model_consistency。

Institution 分母只由 institution Answer Cells 构成；IP 分母只由 IP Answer Cells 构成。禁止同一主体在报告中无解释地一会儿 `/60`、一会儿 `/24`。

## 11. Variant / Repeat Robustness

官方脚本：

```bash
python3 scripts/compute_variant_robustness.py <run-dir>
```

产出：
- `variant_robustness.csv`：entity × target × canonical query 的 0/N、1/N…N/N hit pattern；
- `query_set_similarity.csv`：variant 两两 Positive Set Jaccard 与 Exact Match；
- `robustness_summary.json`。

旧“Repeat Stability 12.3%”类指标正式更名为 `positive_persistence_3of3_rate`：仅在至少一次正向命中的 entity × query 中，三个 variant/run 全部正向命中的比例。**它不是 Overall Repeat Stability**，因为 0/3 稳定负例不在分母。

同时必须报告 0/3、1/3、2/3、3/3 分布，以及 Pairwise Positive-set Jaccard / Exact Positive-set Match。若使用 semantic variants，解释为 Query/Retrieval Robustness。

这些指标目前是 descriptive/diagnostic，不进入 GEO 总分；任何 30%/80% 等阈值只可标为 provisional engineering criterion，在多地区/多引擎校准前不得升级为普适理论门槛。

## 12. SERP / Page / AI 分离

`serp_results.csv` 一行一个真实 Result Item；`serp_mentions.csv` 只允许 title/snippet；`page_mentions.csv` 只记录打开网页后的正文提及。

`page_collection_status=not-collected` 时，空 `page_mentions.csv` 表示“未采集”，不表示“0 个正文提及”。Stage 3 Asset Audit 前应补 Page Collection 或显著披露缺口。

## 13. GEO Asset Readiness

Asset Inputs：Entity Clarity / Regional Semantic Density / Open-Web Assets / External Authority / Content Depth & Freshness / Data/Tool Assets / Platform Coverage。它只解释资产基础，不等价于 AI Answer Visibility。

## 14. Validator stages

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

Release Validator 校验 robustness artifact 是否存在，但在跨地区/跨引擎校准前不把某个经验阈值硬编码为永久 error gate。

## 15. deliverables/

v2.2 唯一正式交付：`deliverables/report.docx`。正式目录不得同时生成 report.pdf/report.html。
