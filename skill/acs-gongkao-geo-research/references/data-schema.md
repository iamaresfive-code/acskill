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
- ai_engine_access_checked
- measurement_profile: snapshot | release
- answer_context_mode_expected: native | engine-native-search | external-search-augmented | pending
- repeat_runs_expected
- fresh_context_required
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
downgrade_reason
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

`downgrade_reason`：为空或以下枚举之一：`seo-only / insufficient-evidence / unresolvable / user-ruling / historical / out-of-scope`。`included` 主体不得保留 downgrade_reason；`seo_only_downgraded` 必须从这个结构化字段生成，禁止再靠 notes 中是否出现 “SEO” 字样判断。

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
  "sample_run":1,
  "context_id":"ctx-A001",
  "fresh_context":true,
  "answer_context_mode":"native",
  "sampled_at":"ISO8601",
  "response_text":"完整回答",
  "citations":[],
  "notes":""
}
```

## ai_emergent_entities.csv

Stage 2 中，如果真实 AI 回答或 SERP title/snippet 自然出现 **Stage 1 已确认 Market Universe 之外** 的机构/品牌/IP，不能静默忽略，也不能回写污染已确认主榜。继续沿用 `ai_emergent_entities.csv` 文件名以兼容 v2.2 现有链路，但它实际承担 **Stage 2 emergent registry（AI + SERP）**。先写入：

```text
entity_id
canonical_name
aliases
measurement_target   # institution | ip
market_scope          # national | regional | local | unknown
operating_region
resolution_status     # resolved | unresolved
source_answer_ids     # 用 | 分隔，可为空
source_result_ids     # 用 | 分隔，可为空，指向 serp_results.csv result_id
notes
```

- `source_answer_ids` 与 `source_result_ids` 至少一类非空；AI 新主体记录 Answer 来源，SERP 新主体记录 Result 来源，也可两者兼有；
- `resolved`：实体解析成立，可进入正式 `ai_metrics.csv`；
- `unresolved`：原始 mention / rank / 来源仍必须保留在 `ai_mentions.csv` 或 `serp_mentions.csv`，但不得进入正式 Nomination Metrics；
- emergent 主体只能在报告中单列，不自动进入 Stage 1 已确认的全国/本地/IP 主榜。

## ai_mentions.csv

```text
mention_id
answer_id
entity_id
mention_rank          # 原文所有实体提及的顺序，resolved/unresolved 都保留
nomination_rank       # 仅正向且已解析的有效 Nomination 连续编号 1..N
mentioned_name
match_method          # explicit-name | verified-alias | citation-only
resolution_status     # resolved | unresolved
mention_intent        # recommended | listed | comparison | caveat | excluded
top3
first_mention
entity_correct
citation_linked
citation_refs         # 用 | 分隔，必须逐条存在于该 Answer Cell 的 citations
concepts
notes
```

原始提及不等于正式 Nomination。正式 Nomination 必须同时满足：

1. `match_method` 为 `explicit-name` 或 `verified-alias`；
2. `resolution_status=resolved`；
3. `entity_correct=true`；
4. `mention_intent` 为 `recommended` 或 `listed`。

`comparison / caveat / excluded` 必须留在原始审计，但不进入 Nomination Rate。`Top3` / `First Mention` 以 `nomination_rank` 派生，不再用 raw `mention_rank` 直接计算。

`citation_linked=true` 必须是**实体级关联**：`citation_refs` 至少包含一条该 Answer Cell `citations` 中真实存在的 URL，且采样员已确认该引用指向该主体、其官方域，或足以明确绑定该实体的页面。不能因为“这个回答整体有引用”就把所有 mention 标 true。

`ai_metrics.csv` 另包含：

```text
raw_mention_rate
engine_coverage_rate
cross_model_consistency
```

其中：
- `engine_coverage_rate` = 至少提名过该主体的 AI 引擎数 / 实际采样引擎数；
- `cross_model_consistency` = 仅在至少 2 个引擎时计算；对“至少一个引擎提到该主体”的 Query，计算这些正向 Query × Engine Answer Cells 中实际提名该主体的比例。它不再等同于“每个引擎至少提过一次”。

### Measurement profile / Answer Context

`answer_context_mode` 必须三选一，并且一个 Run 内不得混用：

- `native`：模型原生、不额外联网/检索增强；
- `engine-native-search`：由该 AI 产品自身的联网/搜索模式产生回答；
- `external-search-augmented`：执行者先做外部 Web Search / RAG，再把检索上下文提供给模型。本模式测的是“外部检索增强后的 AI Answer Visibility”，不能包装成模型原生 Recall。

`measurement_profile`：

- `snapshot`：允许每个 query×engine 只采 1 次，用于方法压力测试/单时点快照；
- `release`：用于正式可发布测量。要求 `repeat_runs_expected >= 3`，每个 query×engine 必须有完整的 `sample_run=1..N`，且 `fresh_context_required=true`；每个 Answer Cell 使用唯一 `context_id`，禁止上下文串扰。

正式发布报告必须同时披露：`sampling_mode`、`answer_context_mode_expected`、`measurement_profile`、`repeat_runs_expected`、采样日期。单引擎或 snapshot 结果不得表述为跨模型稳定排名。

Stage 2 前建议用正式脚本写入这些字段：

```bash
python3 scripts/configure_measurement.py <run-dir> --engine actual-engine --context-mode native --profile release --repeat-runs 3 --fresh-context
```

该脚本不替你探测外部服务；执行者必须先真实验证引擎可用，只把实际可访问的引擎传入。

`Top3` 与 `First Mention` 的正式统计以 `nomination_rank` 派生；CSV 中对应布尔字段必须与有效正向提名顺序一致，否则 Validator 报错。

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

它不能进入 AI Nomination 或 SERP Result Item 计数。正文抓取是可选解释层；本轮若没有执行正文 fetch，允许保留只有表头的空表，但必须在报告/审计中注明“page layer 未采样”，不能把 snippet 推断成正文。

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
