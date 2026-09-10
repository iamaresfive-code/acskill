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

`universe_status`: included / observation / excluded / unresolved。

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
distribution
buckets
bucket_audit
seo_only_downgraded
unresolved_or_weak
message
```

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
