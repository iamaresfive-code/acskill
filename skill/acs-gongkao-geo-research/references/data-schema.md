# GEO 调研数据规范 v2.0

所有 CSV 使用 UTF-8、首行字段名；日期用 `YYYY-MM-DD`，时间用 ISO 8601。报告声明 `Schema版本：2.0` 后，下列文件均为必需。

## 标准目录

```text
run-dir/
├── queries.csv
├── query_results.csv
├── candidate_pool.csv
├── entities.csv
├── entity_relations.csv
├── evidence.csv
├── scores.csv
├── score_details.json
├── ip_entities.csv
├── warning_resolutions.csv       # 有人工处置警告时使用
├── report.md
└── report.html
```

## queries.csv

```text
query_id,query_text,query_type,query_purpose,discovery_channel,discovery_round,theme,region,city,exam,sampled_channel,sampled_at,status,notes
```

- `query_type`：`generic|brand`。
- `query_purpose`：`discovery|measurement|verification`。
- `measurement` 必须是 `generic`；只有 `generic + measurement + sampled` 进入泛词分母。
- `discovery_channel`：`user-query|exam-vertical|institutional|platform|expert-ip|entity-alias`；非 Discovery 可留空。
- `discovery_round`：Discovery 使用 `1|2|3...`；其他可留空。
- `status`：`planned|sampled|failed|skipped`。未实际执行的问题不得伪装为 sampled。

## query_results.csv

```text
result_id,query_id,entity_id,result_rank,source_url,source_title,matched_name,observed_at,channel,matched,counts_as_measurement_hit,notes
```

- 每个实际结果一行；即使不能确认实体，也可暂时留空 `entity_id` 并在候选池标 unresolved。
- `matched` 使用 `true|false`。
- `counts_as_measurement_hit=true` 仅允许用于 matched 的 `generic + measurement + sampled` 结果。
- 同一实体同一 Measurement 问题出现多次，泛词命中只计一次。

## candidate_pool.csv

```text
candidate_id,entity_id,display_name,candidate_type,discovery_round,discovery_channel,discovery_query_id,discovery_result_id,first_seen_at,evidence_strength,status,merged_into_entity_id,exclusion_reason,notes
```

- 每条发现线索一行；同一实体可有多条线索。
- `candidate_type` 建议 `institution|brand|teacher|company|other`。
- 最终 `status`：`scored|evidence-insufficient|merged|excluded|unresolved`。
- `merged` 必填 `merged_into_entity_id`；`excluded` 必填原因。
- 地区全景中第二轮新发现的 scored/evidence-insufficient 实体数用于饱和度检查。

## entities.csv

```text
entity_id,canonical_name,entity_type,aliases,legal_name,former_names,official_domain,region,parent_entity_id,entity_status,disambiguation_notes,source_ids,notes
```

- `entity_id` 使用稳定大写前缀和数字，例如 `I05`、`T012`、`C003`。
- `entity_type`：`institution|brand|teacher|company|platform|exam|product|region`。
- 多值字段用 `|` 分隔。
- 短别名、常见词或历史同名必须填写 `disambiguation_notes`；不能仅靠名称相似自动合并。
- `source_ids` 使用 `E001|E008`，不得写地区前缀。

## entity_relations.csv

```text
relation_id,source_entity_id,relation_type,target_entity_id,relation_status,valid_from,valid_to,evidence_ids,confidence,notes
```

- `relation_type`：`operated-by|brand-of|teaches-at|founded-by|formerly-known-as|alias-of|offers|located-in|appears-on|partner-of|other`。
- `relation_status` 建议 `current|historical|partner|multiple|unverified`。
- `confidence`：`High|Medium|Low`。
- 每条关系必须有证据编号；历史关系不得冒充当前关系。

## evidence.csv

```text
evidence_id,entity_id,institution,query_id,query,query_type,source_title,source_url,source_domain,published_date,accessed_date,source_grade,independent,claim_type,concepts,duplicate_group,duplicate_reason,review_status,counting_scope,notes
```

- `evidence_id` **必须匹配 `E\d+`**，如 `E001`；校验器与正文锚点只识别这一格式，禁止 `TJ01`、`SD01` 等自定义前缀。
- `source_grade`：`A1|A2|B|C`；`independent`：`true|false`。
- `claim_type`：`fact|institution-claim|proxy-metric|analysis`。
- `concepts` 用 JSON 数组字符串。
- 同 URL 复用时，每一行都填写相同 `duplicate_group`、具体 `duplicate_reason`、`review_status=reviewed`、`counting_scope`。
- 合理保留：同一原页支持不同实体或不同关系，但独立域名只计一次。必须去重：同稿转载、站群换域名、同内容拆成多个计数。被排除计数的行用 `counting_scope=ignored`。

标准复核说明示例：

```text
duplicate_group=DG03
duplicate_reason=同一高校活动页同时支持机构参与事实与老师身份关系；保留两条陈述，但独立域名只计一次
review_status=reviewed
counting_scope=claim-only
```

## scores.csv

```text
institution,entity_id,inclusion_basis,query_coverage,entity_clarity,external_diversity,concept_ownership,freshness,total,tier,evidence_confidence,generic_hits,generic_queries,brand_hits,evidence_count,independent_domains,notes
```

- `inclusion_basis`：`discovered|user-requested|owned-forced|benchmark`，只表示入选来源，不影响分数。
- 五维上限 30、25、20、15、10；`total` 为五项之和。
- `tier`：S、A+、A、A-、B+、B、B-、C。
- `evidence_confidence`：`High|Medium|Low`；报告显示高/中/低。
- `generic_hits/generic_queries` 仅由 Measurement 派生，`brand_hits` 仅由 Verification 品牌词派生；Discovery 不进入任何命中指标。
- `evidence_count` 与该 entity_id 的 evidence 行数一致；`independent_domains` 为去重后的独立域名数。

## score_details.json

根节点为数组，每个评分实体一项：

```json
{
  "entity_id": "I001",
  "dimensions": {
    "query_coverage": {"score": 18, "reason": "5/20 个 Measurement 问题自然命中", "query_ids": ["QM01", "QM03"]},
    "entity_clarity": {"score": 16, "reason": "官网可确认品牌、主体与课程", "evidence_ids": ["E001", "E004"]},
    "external_diversity": {"score": 9, "reason": "2 个独立域名，外证有限", "evidence_ids": ["E006"]},
    "concept_ownership": {"score": 8, "reason": "面试概念形成重复关联", "evidence_ids": ["E009"]},
    "freshness": {"score": 7, "reason": "近 90 天有更新", "evidence_ids": ["E011"]}
  }
}
```

每维必须有分数、非空理由，并至少有 `evidence_ids` 或 `query_ids`。

## ip_entities.csv

```text
teacher_name,aliases,institution,relation_status,relation_period,subjects,products,regions,platforms,generic_hits,brand_hits,concepts,source_ids,evidence_confidence,notes
```

关系状态使用 `current|historical|partner|multiple|unverified`。人物粉丝量、播放量只作代理指标，不能直接提高机构得分。

## warning_resolutions.csv

```text
issue_code,issue_key,resolution,status,reviewed_by,reviewed_at
```

- 只处理允许人工判断的 warning，不能压制 error。
- `issue_key` 必须与校验输出完全一致；`status=reviewed`，且结论、复核人、复核时间均非空。
- 再跑 `--strict` 后，对应 warning 会转为 info；缺字段或泛化按 code 全部放行均无效。

## report.md 机器字段

正文开头逐行保留：

```text
Schema版本：2.0
Skill版本：2.0
观察日期：YYYY-MM-DD
研究模式：地区全景（regional-landscape）
研究范围：...
采样模式：公开网页代理观察
Discovery问题数：N
Measurement问题数：N
Verification问题数：N
Discovery渠道覆盖：user-query|exam-vertical|institutional|platform|expert-ip|entity-alias
漏项审计轮数：N
候选记录数：N
第一轮候选实体数：N
第二轮新增实体数：N
去重后实体数：N
正式评分数：N
待观察/证据不足数：N
证据数：N
IP名师调查：是
IP名师样本数：N
自有机构纳入：是|否
自有机构名称：...  # 是时必填
第二轮新增占比说明：...  # 第二轮新增可评估实体超过 35% 时必填
免责声明：GEO 观察指数不代表教学实力、市场份额或大模型官方推荐排名。
```

机器字段必须与 CSV/JSON 一致。正文重要事实用 `[E001]` 或 Markdown 来源链接；HTML 生成器会把证据编号链接到自动附加的证据索引。

## 兼容说明

没有 `Schema版本：2.0` 的旧运行目录按 v1.1 兼容模式读取，并输出 `legacy-schema` 信息而非研究错误；它不会自动升级为 v2。迁移规则见 [migration-v2.md](migration-v2.md)。
