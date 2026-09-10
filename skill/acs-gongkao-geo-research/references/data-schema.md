# GEO 调研数据规范 v2.2

所有新 Run：

```json
{"schema_version":"2.2","skill_version":"2.2","official_output_format":"docx"}
```

## run_metadata.json

核心字段：

- requested_region / normalized_region / research_scope
- seed_entities
- allow_discovery_supplement
- research_mode: scoped-geo-landscape | blind-discovery-scan
- market_universe_confirmed
- measurement_allowed
- sampling_mode: multi-engine | limited-multi-engine | single-engine | asset-audit-only | pending
- ai_engines_expected
- observation_date

## market_universe.csv

```text
entity_id
canonical_name
aliases
entity_type
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
notes
```

`market_scope`: national / regional / local / unknown。

`market_role`: national-benchmark / local-core / local-active / expert-ip / historical / observation / unclassified。

`universe_status`: included / observation / unresolved。

v2.2 不提供静默硬排除状态：
- `included`：进入正式 A/B/C 主榜；
- `observation`：Stage 1 不进入主榜，但仍参加 AI Answer Measurement；
- `unresolved`：实体/市场证据仍不足，继续保留并参加 Measurement，结果需谨慎解释。

若用户确认后明确不要研究某主体，应从 Market Universe 合同中移除并在确认记录/报告审计中说明；不要使用未定义的 `excluded` 状态让主体静默跳过 Measurement。

`confirmation_status`: needs-review / confirmed。

重要：User Seed 初次建池不能因为是 Seed 就自动获得 included；若尚未完成实体解析/市场核验，应为 unresolved + needs-review。

当 Seed 与 System Discovery 同名时，必须字段级合并，不能只保留 `user_seed=true` 后丢弃 Discovery 携带的 aliases / scope / role / salience_basis / notes。

## universe_review.json

Stage 1 的机器可审计确认材料。至少包含：

```text
schema_version
region
research_mode
market_universe_confirmed
measurement_allowed
total_entities
user_seed_count
user_seed_all_present
system_discovery_count
seed_also_discovered_count
platform_native_count
expert_ip_included_count
distribution
buckets
bucket_audit
seo_only_downgraded
unresolved_or_weak
message
```

`system_discovery_count` 只统计非 User Seed、由系统发现/平台发现进入 Universe 的主体；Seed 后续也被系统搜到时记入 `seed_also_discovered_count`，不重复算进 system discovery only。

`buckets` 必须精确为四个互斥集合：

```text
A_national_benchmarks
B_local_regional
C_expert_ip
D_observation_or_other
```

四个 bucket 不允许重叠，且并集必须等于 `market_universe.csv` 全部主体。

Market Universe 被 Agent / reviewer 修改后，使用：

```bash
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

## queries.csv

```text
query_id
query_text
query_group
measurement_target   # institution | ip
region
status               # planned | sampled | skipped
```

## ai_answers.jsonl

每行一个 JSON：

```json
{
  "answer_id":"A001",
  "query_id":"M01",
  "engine":"ChatGPT",
  "model":"...",
  "sampled_at":"ISO8601",
  "response_text":"完整回答",
  "citations":[],
  "notes":""
}
```

## ai_emergent_entities.csv

Stage 2 中，如果真实 AI 回答自然提到 **Stage 1 已确认 Market Universe 之外** 的机构/品牌/IP，不能静默忽略，也不能回写污染已确认主榜。先写入：

```text
entity_id
canonical_name
aliases
measurement_target   # institution | ip
market_scope          # national | regional | local | unknown
operating_region
resolution_status     # resolved | unresolved
source_answer_ids     # 用 | 分隔，必须指向真实 ai_answers.jsonl answer_id
notes
```

- `resolved`：canonical/alias 与来源 Answer 可核对，可进入 `ai_mentions.csv` 与 `ai_metrics.csv`；
- `unresolved`：仍保留审计，但不得伪装成已确认实体提名；
- AI-emergent 主体只能在报告中单列，不自动进入 Stage 1 已确认的全国/本地/IP 主榜。

## ai_mentions.csv

```text
mention_id
answer_id
entity_id
mention_rank
mentioned_name
match_method          # explicit-name | verified-alias | citation-only
top3
first_mention
entity_correct
citation_linked
concepts
notes
```

只有 explicit-name / verified-alias 进入 Nomination。

`ai_metrics.csv` 另包含：

```text
engine_coverage_rate
cross_model_consistency
```

其中：
- `engine_coverage_rate` = 至少提名过该主体的 AI 引擎数 / 实际采样引擎数；
- `cross_model_consistency` = 仅在至少 2 个引擎时计算；对“至少一个引擎提到该主体”的 Query，计算这些正向 Query × Engine Answer Cells 中实际提名该主体的比例。它不再等同于“每个引擎至少提过一次”。

`Top3` 与 `First Mention` 的正式统计以 `mention_rank` 派生；CSV 中对应布尔字段必须与 rank 一致，否则 Validator 报错。

## serp_results.csv

一行就是一个真实 Result Item：

```text
result_id
query_id
engine
rank
url
title
snippet
sampled_at
```

同一 query + engine + rank 只能一行。

## serp_mentions.csv

只允许 title/snippet 的显式提及：

```text
serp_mention_id
result_id
entity_id
matched_text
match_surface         # title | snippet | both
notes
```

## page_mentions.csv

网页正文内部提及：

```text
page_mention_id
result_id
entity_id
matched_text
page_url
notes
```

它不能进入 AI Nomination 或 SERP Result Item 计数。

## evidence.csv

```text
evidence_id
entity_id
source_url
source_title
source_grade
source_owner          # owned | independent | platform | unknown
claim_type
counting_scope
notes
```

## rechecks.csv

```text
recheck_id
sample_type           # ai-answer | serp
source_id
first_decision
second_decision
disagreement
resolution
recheck_by
notes
```

## asset_inputs.csv / asset_scores.csv

Asset Inputs 维度：

```text
entity_clarity
regional_semantic_density
open_web_assets
external_authority
content_depth_freshness
data_tool_assets
platform_coverage
```

`score_assets.py` 派生：asset_readiness / asset_tier / evidence_count / independent_domains / owned_source_dependency。

## concept_ownership.csv

```text
concept
entity_id
canonical_name
strength
evidence_ids
notes
```

## report_model.json

必须有：

- market_universe
- ai_visibility
- asset_readiness
- concept_map
- observation_group
- ai_visible_observation
- ai_emergent_entities
- ai_visible_emergent
- appendix
- kpis

AI-emergent 主体必须单列，不能自动并入 Stage 1 已确认的全国/本地/IP 主榜。

## Validator stages

```bash
# Stage 1：只校验 Universe，不要求 Measurement / Word
python3 scripts/validate_run.py <run-dir> --stage universe --strict

# Stage 2：Universe 已确认后，校验 AI/SERP/Recheck/Metrics
python3 scripts/validate_run.py <run-dir> --stage measurement --strict

# 最终：再校验 report_model + DOCX-only
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

默认不指定 `--stage` 时按 full 执行。

## deliverables/

v2.2 唯一正式交付：

```text
deliverables/report.docx
```

正式目录不得同时生成 report.pdf / report.html。
