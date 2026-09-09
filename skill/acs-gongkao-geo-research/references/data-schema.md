# GEO 调研数据规范 v2.1

所有 CSV 使用 UTF-8；日期 `YYYY-MM-DD`，时间 ISO 8601。新运行必须声明 `Schema版本：2.1`。

## 标准运行目录

```text
run-dir/
├── run_metadata.json
├── queries.csv
├── query_results.csv
├── discovery_coverage.csv
├── candidate_pool.csv
├── entities.csv
├── entity_relations.csv
├── evidence.csv
├── scores.csv
├── score_details.json
├── ip_entities.csv
├── warning_resolutions.csv       # 有人工处置 warning 时可选
├── report_model.json
├── report.md                     # 人类可读正文源，不是正式交付物
├── charts/
│   ├── geo-score-ranking.svg
│   ├── authority-recall-matrix.svg
│   ├── dimension-heatmap.svg
│   └── candidate-funnel.svg
└── deliverables/
    └── report.{docx|pdf|html}     # 仅用户选择格式
```

## run_metadata.json

最少字段：

```json
{
  "schema_version": "2.1",
  "skill_version": "2.1",
  "run_status": "ready|preflight-incomplete|researching|frozen|rendered|complete",
  "region_confirmed": true,
  "specified_entities_confirmed": true,
  "output_format_confirmed": true,
  "requested_region": "广东",
  "normalized_region": "广东省",
  "region_type": "province|municipality|city|custom-region",
  "research_scope": ["广东省"],
  "requested_entities": [],
  "requested_output_format": ["pdf"],
  "observation_date": "2026-09-09",
  "sampling_mode": "public-web-proxy",
  "candidate_pool_frozen": true,
  "semantic_coverage_gate": true,
  "saturation_gate": true
}
```

`requested_output_format` 为数组是为了支持用户明确要求多个格式；通常只含一项。

## queries.csv

```text
query_id,query_text,query_type,query_purpose,measurement_target,discovery_channel,discovery_round,semantic_theme,theme,region,city,exam,sampled_channel,sampled_at,status,notes
```

- `query_type`: `generic|brand`
- `query_purpose`: `discovery|measurement|verification`
- `measurement_target`: `institution|ip`；非 Measurement 留空
- `measurement` 必须 `query_type=generic`
- 机构 Recall 分母只含 `generic + measurement + institution + sampled`
- IP Recall 分母只含 `generic + measurement + ip + sampled`
- `discovery_channel`: `user-query|exam-vertical|institutional|platform|expert-ip|entity-alias`
- `discovery_round`: `1|2|3...`
- `semantic_theme`: 当地真实语义主题，不得写死天津
- `status`: `planned|sampled|failed|skipped`

## query_results.csv

```text
result_id,query_id,entity_id,result_rank,source_url,source_title,matched_name,observed_at,channel,matched,counts_as_measurement_hit,notes
```

`counts_as_measurement_hit=true` 只有在对应 Query 是合法 Measurement 且 `matched=true` 时才可使用。

## discovery_coverage.csv

```text
region,discovery_channel,semantic_theme,required,query_count,result_count,eligible_candidates_found,status,notes
```

- `required`: `true|false`
- `status`: `covered|no-result-reviewed|partial|missing|not-applicable`
- Gate A 只允许全部 required 行为 `covered|no-result-reviewed`
- `no-result-reviewed` 表示该主题已实际检索、没有有效候选，但研究者完成了结果复核；不能用来跳过查询

## candidate_pool.csv

```text
candidate_id,entity_id,display_name,candidate_type,discovery_round,discovery_channel,discovery_query_id,discovery_result_id,first_seen_at,evidence_strength,user_specified,status,merged_into_entity_id,exclusion_reason,notes
```

最终状态：

`scored|evidence-insufficient|merged|excluded|unresolved`

- `user_specified=true` 的主体不得 `excluded` 后静默消失；如确认是跨区/非公考噪声，优先保留为 `unresolved` 或 `merged` 并解释
- `merged` 必填 `merged_into_entity_id`
- `excluded` 必填 `exclusion_reason`

## entities.csv

```text
entity_id,canonical_name,entity_type,aliases,legal_name,former_names,brand_name,official_domain,official_account,region,parent_entity_id,entity_status,disambiguation_notes,source_ids,notes
```

`entity_type`: `institution|brand|teacher|company|platform|exam|product|region`

短别名、常见词、历史同名必须写 `disambiguation_notes`。

## entity_relations.csv

```text
relation_id,source_entity_id,relation_type,target_entity_id,relation_status,valid_from,valid_to,evidence_ids,confidence,notes
```

关系类型可用：

`operated-by|brand-of|teaches-at|founded-by|formerly-known-as|alias-of|offers|located-in|appears-on|partner-of|other`

## evidence.csv

```text
evidence_id,entity_id,institution,query_id,query,query_type,source_title,source_url,source_domain,published_date,accessed_date,source_grade,independent,claim_type,concepts,duplicate_group,duplicate_reason,review_status,counting_scope,notes
```

- `evidence_id` 必须匹配 `E\d+`
- `source_grade`: `A1|A2|B|C`
- `claim_type`: `fact|institution-claim|proxy-metric|analysis`
- 同 URL 多用途复用必须结构化记录 duplicate 字段

## scores.csv

```text
institution,entity_id,inclusion_basis,query_coverage,entity_clarity,external_diversity,concept_ownership,freshness,total,tier,evidence_confidence,generic_hits,generic_queries,brand_hits,evidence_count,independent_domains,authority_index,competition_route,notes
```

- 五维权重不变：30/25/20/15/10
- `inclusion_basis`: `discovered|user-requested|owned-forced|benchmark`
- `generic_hits/generic_queries` 只来自机构 Measurement
- `authority_index` 0–100，独立于 GEO Score，算法应透明并可复算
- `competition_route` 为报告解释标签，不参与加分

## score_details.json

每个评分实体记录五维分数、理由、证据或 Measurement Query ID；不得只有总分。

## ip_entities.csv

```text
teacher_name,entity_id,aliases,institution,relation_status,relation_period,subjects,products,regions,platforms,ip_hits,ip_queries,ip_recall,entity_confidence,institution_relation,subject_binding,concept_ownership,evidence_health,brand_hits,source_ids,evidence_confidence,notes
```

只有实际执行 IP Measurement 时 `ip_queries>0`。没有 IP Measurement 时不得称为 IP GEO Ranking。

## warning_resolutions.csv

```text
issue_code,issue_key,resolution,status,reviewed_by,reviewed_at
```

只允许处理 warning，不得压制 error。

## report_model.json

统一正式报告内容层，建议包含：

```json
{
  "meta": {},
  "kpis": {},
  "executive_summary": [],
  "ranking": [],
  "authority_recall": [],
  "scorecards": [],
  "diagnoses": [],
  "query_occupancy": [],
  "concept_gaps": [],
  "entry_strategy": [],
  "plan_90_days": [],
  "monthly_dashboard": [],
  "charts": {},
  "appendix": {}
}
```

Renderer 只读取 Report Model 与本次 Run 的已生成资产，不再各自重新生成研究结论。

## 报告机器审计字段

这些字段应放在 Appendix / Research Audit，而不是封面或 Executive Summary：

```text
Schema版本：2.1
Skill版本：2.1
观察日期：YYYY-MM-DD
研究模式：...
研究范围：...
采样模式：...
Discovery问题数：N
机构Measurement问题数：N
IP Measurement问题数：N
Verification问题数：N
Discovery渠道覆盖：...
Discovery Semantic Theme数：N
候选记录数：N
独立机构候选：N
实体图谱节点：N
具备评估条件：N
正式评分：N
IP实体：N
证据数：N
scored：N
证据不足：N
merged：N
excluded：N
unresolved：N
```

注意：“实体图谱节点”不能写成“机构数量”。
