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
- sampling_mode: multi-engine | limited-multi-engine | single-engine | asset-audit-only
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
- appendix
- kpis

## deliverables/

v2.2 唯一正式交付：

```text
deliverables/report.docx
```

正式目录不得同时生成 report.pdf / report.html。
