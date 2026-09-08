# GEO 调研数据规范

每次深度调研使用独立运行目录，目录名建议为“日期-地区或品牌”的英文安全写法。CSV 统一使用 UTF-8、首行字段名；日期统一为 `YYYY-MM-DD`，时间可用 ISO 8601。

## 标准目录

```text
run-dir/
├── queries.csv          # 必需：本次实际题池与采样记录
├── evidence.csv         # 必需：逐条证据
├── scores.csv           # 必需：逐机构五维评分
├── ip_entities.csv      # 必需：IP名师实体及与机构的关系；未发现时保留表头
├── report.md            # 必需：可追溯的正式报告源文件
├── report.html          # 必需：默认最终交付件
├── geo-index.png        # 可选：GEO 指数图
└── geo-quadrant.png     # 可选：实体可核验性 × 泛词覆盖象限图
```

可以增加 `claims.csv`、抓取快照或过程笔记，但不得用中间文件代替上述必需文件。网页全文应遵守版权边界，不为复现而批量保存无必要的受版权保护正文。

## queries.csv

必需字段：

```text
query_id,query_text,query_type,theme,region,city,exam,sampled_channel,sampled_at,notes
```

- `query_type`：内部值 `generic` 或 `brand`，分别表示泛词查询或品牌词查询。
- `sampled_channel`：例如内部值 `public-web` 或具体生成式搜索引擎名称；未实际采样不得填写。
- 未执行的候选问题不要混入实际题池；如需保留，增加 `status` 并让校验只统计 `sampled`。

## evidence.csv

CSV 必需字段与 JSON 对象一致：

```json
{
  "evidence_id": "E001",
  "institution": "机构或实体名称",
  "query": "触发该证据的问题",
  "query_type": "generic|brand",
  "source_title": "来源标题",
  "source_url": "https://...",
  "source_domain": "example.com",
  "published_date": "YYYY-MM-DD 或 unknown",
  "accessed_date": "YYYY-MM-DD",
  "source_grade": "A1|A2|B|C",
  "independent": true,
  "claim_type": "fact|institution-claim|proxy-metric|analysis",
  "concepts": ["概念1", "概念2"],
  "notes": "核验、去重或局限说明"
}
```

CSV 中 `concepts` 使用 JSON 数组字符串，例如 `["本地考情","基地班"]`；`independent` 使用 `true`/`false`。同一 URL 支持多个机构或多个不同陈述时可以多行，但必须说明，不得误计为多个独立来源。

## scores.csv

必需字段：

```text
institution,role,query_coverage,entity_clarity,external_diversity,concept_ownership,freshness,total,tier,evidence_confidence,generic_hits,generic_queries,brand_hits,evidence_count,independent_domains,notes
```

- `role`：内部值 `Candidate`、`Specified` 或 `Benchmark`，分别表示调研发现、用户指定或对标补充。它不是机构等级，也不得影响评分。
- `role` 保留在结构化数据中供复核；最终报告主排名表默认不显示。确需说明时使用中文列名“入选方式”，并映射为“调研发现 / 用户指定 / 对标补充”。
- 五维上限依次为 30、25、20、15、10；`total` 必须是五项之和。
- `tier`：S、A+、A、A-、B+、B、B-、C。
- `evidence_confidence`：内部值 `High`、`Medium`、`Low`，报告显示为高、中、低。
- `generic_hits` 不得大于 `generic_queries`；泛词覆盖度高分必须由泛词查询证据支持。
- 没有足够证据的主体可以记录为内部值 `Evidence insufficient`，报告显示为“证据不足”，不要伪造精确分。
- 地区调查中用户要求纳入的自有机构必须使用内部值 `Specified` 并保留，即使 `generic_hits=0`；不得把品牌词查询命中改算为泛词命中。

## ip_entities.csv

必需字段：

```text
teacher_name,aliases,institution,relation_status,relation_period,subjects,products,regions,platforms,generic_hits,brand_hits,concepts,source_ids,evidence_confidence,notes
```

- 每位进入正式分析或待核名单的老师一行；未发现达到最低证据门槛的老师时保留表头，并在报告说明“本次未发现可确认的 IP 名师”。
- `relation_status` 使用内部值 `current`、`historical`、`partner`、`multiple` 或 `unverified`，报告分别显示“当前任职／历史关系／合作关系／多重关系／关系待核”。
- `generic_hits` 只统计不含老师或机构名称的查询自然命中；人物品牌词结果计入 `brand_hits`。
- `source_ids` 引用 `evidence.csv` 中可回溯的证据编号；关系待核时不得据此提高机构评分。
- 粉丝量、播放量等可写入备注或单独代理指标，但不得直接折算为机构总分。

## report.md 的机器可检字段

建议在正文开头保留以下明确文本，便于人工和脚本检查：

```markdown
观察日期：YYYY-MM-DD
研究范围：...
采样模式：公开网页代理观察 | 多引擎实测
IP名师调查：是
IP名师样本数：N
自有机构纳入：是 | 否
自有机构名称：...  # 选择“是”时必填
证据置信度：高 | 中 | 低
免责声明：GEO 观察指数不代表教学实力、市场份额或大模型官方推荐排名。
```

每个重要事实在同段附来源链接，或使用能回溯到 `evidence.csv` 的脚注/证据编号。强结论必须有证据等级和置信度支撑。

`自有机构纳入`是前置问询的审计字段。选择“否”时不得凭历史信息加入内部“用户指定”样本；选择“是”时必须记录准确名称，并在 `scores.csv` 中保留对应内部样本值。

## 脚本接口

- `python3 scripts/score_geo.py scores-input.json --pretty`
- `python3 scripts/score_geo.py --self-test`
- `python3 scripts/validate_run.py run-dir`
- `python3 scripts/validate_run.py run-dir --strict`
- `python3 scripts/validate_run.py run-dir --strict --require-deliverable`
- `python3 scripts/validate_run.py --self-test`

校验通过只表示结构和主要逻辑约束通过，不能替代人工打开来源、确认来源支持陈述、核验时间窗口和复查对标合理性。

## HTML 交付

`report.html` 必须从最终 `report.md` 生成，包含完整正文和必要样式，并在交付前用浏览器检查。至少核对中文字体、标题层级、宽表格横向滚动、来源链接、打印分页、裁切、重叠和黑块。Markdown 或 CSV 不能代替默认 HTML 最终交付。
