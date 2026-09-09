---
name: acs-gongkao-geo-research
description: 调查中国公务员及公职考试培训机构、品牌和老师/IP 在生成式搜索与 AI 搜索中的可见性，支持地区 GEO 竞争格局、指定机构深挖、机构比较、候选召回、实体解析、Semantic Discovery Audit、AI Search Visibility 与正式咨询报告生成。v2.1 先完成地区、指定关注主体、正式输出格式三步 Preflight，再执行 Candidate Discovery → Entity Resolution → Semantic Coverage → Measurement → Evidence → Scoring → Strategy Analysis → Report Model → Selected Renderer；不得用来评价教学质量、上岸效果、市场份额或一般口碑。
metadata:
  version: "2.1"
---

# 公考机构 GEO 调研 v2.1

版本定位：**Research Quality + Consulting Report Experience Upgrade**。

v2.1 不是推翻 v2.0。v2.0 的 Candidate Discovery、Entity Resolution、Discovery / Measurement / Verification 分离、Evidence Audit、五维 GEO Score、Authority × Recall 全部保留；v2.1 在此基础上重点增加：三步 Preflight、Semantic Discovery Coverage、双门禁 Candidate Freeze、IP Measurement、Report ↔ Data 一致性、统一 Report Model、三类 Renderer 与咨询报告设计系统。

GEO 观察的是机构、品牌或老师/IP 在公开信息环境中被发现、理解、确认、召回和引用的能力。它不是教学质量、市场份额、经营规模、真实口碑、学员上岸率，也不是任何大模型官方推荐榜。

## 0. 启动前强制 Preflight

任何新 GEO 调研，在完整 Research Run 前必须明确三个参数：

1. `requested_region`：省、市或区域；
2. `requested_entities`：用户是否指定关注机构、品牌或老师/IP；可以明确“不指定”；
3. `requested_output_format`：`docx|pdf|html`，默认一次任务只正式交付用户明确选择的格式。

先读 [preflight.md](references/preflight.md)。

### 对话规则

- 用户已给出的参数自动识别，不重复机械询问。
- 三项都缺：只先问地区。
- 已知地区：继续问是否有指定关注主体。
- 已知地区和指定主体：只问 Word、PDF 还是 HTML。
- 三项都明确：总结确认后直接开始。
- 非行政区区域如珠三角、粤东、苏南，先建立 Scope；存在明显口径争议才再确认。

### 指定主体规则

指定关注只解决 Candidate Recall：

- `user_specified=true` 的主体强制进入 Candidate Pool；
- 不自动加分、不自动进入正式排名、不提高证据等级、不提高置信度；
- 最终必须落在 `scored|evidence-insufficient|unresolved|merged` 之一，不能静默消失；
- 证据不足时进入“用户指定关注 / 证据不足观察组”；无法解析时进入“用户指定关注 / 未解析主体”。

### 输出格式规则

- Word → 最终正式产出仅 `report.docx`；
- PDF → 最终正式产出仅 `report.pdf`；
- HTML → 最终正式产出仅 `report.html`；
- 只有用户明确要求多个格式时，才允许多个正式文件。

内部 CSV、JSON、SVG、临时 HTML/DOCX/PDF 都属于 Research / Render 资产，不等于正式交付物；除非用户另行要求，不向用户展示。

只有 `region_confirmed=true`、`specified_entities_confirmed=true`、`output_format_confirmed=true` 时，完整 Research Run 才能开始；否则 `run_status=preflight-incomplete`。

## 1. 研究模式

| 模式 | 触发 | 研究对象 |
| --- | --- | --- |
| 地区全景 `regional-landscape` | 用户给省、市或区域 | 自动发现整个地区候选；指定关注主体只做强制召回 |
| 单主体深挖 `institution-deep-dive` | 用户点名一个主体 | 只深挖点名主体；用户明确要求才加 benchmark |
| 多主体比较 `institution-comparison` | 用户点名两个及以上主体 | 只比较点名集合；不自动扩张名单 |
| 空白机会 `gap-analysis` | 用户问机会词、概念空白 | 从真实弱召回、无结果、实体歧义、概念断层中形成机会地图 |

“哪家教学最好”“哪家通过率最高”“真实口碑排名”不属于本 Skill。用户把 GEO 等同于教学排名时先纠正口径。

## 2. v2.1 Research Engine 总流程

```text
Preflight
↓
Region / Exam Ecology
↓
Candidate Discovery
↓
Entity Resolution
↓
Semantic Coverage Audit
↓
Coverage Gate + Saturation Gate
↓
Candidate Pool Freeze
↓
Institution Measurement + IP Measurement
↓
Verification + Evidence Audit
↓
Five-Dimension Scoring
↓
Strategy Analysis
↓
Report Model
↓
Selected Renderer
↓
Strict Validation + Visual QA
```

详细方法读 [methodology.md](references/methodology.md)，数据字段读 [data-schema.md](references/data-schema.md)，来源政策读 [source-policy.md](references/source-policy.md)。

## 3. Discovery / Measurement / Verification 必须隔离

`query_purpose` 只有：

- `discovery`：找候选、别名、关系；不计泛词覆盖；
- `measurement`：统一无品牌问题实测；只有合法 Measurement 才进入 Recall / Query Coverage；
- `verification`：核验官网、公司、老师、课程、关系和外部来源；不计 Query Coverage。

v2.1 的 `queries.csv` 增加 `measurement_target`：

- `institution`：机构 Measurement；
- `ip`：老师/IP Measurement；
- 非 Measurement 留空。

只有同时满足：

```text
query_type=generic
query_purpose=measurement
measurement_target=institution
status=sampled
```

才进入机构 `generic_queries` 分母；命中还必须对应 result 的 `counts_as_measurement_hit=true`。

IP Measurement 另行计算，不与机构总榜混算。

## 4. 地区 Discovery：六路保留，但升级为 Semantic Coverage

六路 Discovery 保留：

1. `user-query`
2. `exam-vertical`
3. `institutional`
4. `platform`
5. `expert-ip`
6. `entity-alias`

v2.1 不再把“每条渠道跑过一条查询”视为发现完成。必须先根据当地考试生态建立 `semantic_theme`，再生成 Discovery Query。

典型语义主题包括但不限于：省/市考、国考、事业单位、选调、定向选调、遴选、军队文职、公安警法、面试形式、本地高校活动、老师/IP、品牌简称、公司名、曾用名。具体主题必须动态适配地区，禁止写死天津案例。

所有覆盖情况写入 `discovery_coverage.csv`。字段和状态见 [data-schema.md](references/data-schema.md)。

## 5. Candidate Pool Freeze：双门禁

候选池只有同时通过两道门才可 Freeze：

### Gate A — Semantic Coverage Gate

所有 `required=true` 的关键 `semantic_theme` 均需达到 `covered|no-result-reviewed`。如果关键考试垂类、Institutional Source、Platform、Expert/IP、Entity Alias 等存在未覆盖项，不得冻结。

### Gate B — Saturation Gate

针对性补漏后新 Eligible Candidate 必须明显收敛。默认可接受任一条件：

- 最近一轮新增率 `<10%`；或
- 最近一轮新增可评估独立机构 `<=1`；或
- 连续两轮无重要新增主体。

第二轮仍新增大量主体时不得仅因为“低于 35%”就判定饱和。

## 6. 实体治理与指定主体深度解析

用户给出的名字只是入口。至少尝试扩展：

`canonical_name`、`aliases`、`legal_name`、`former_names`、`brand_name`、`official_domain`、`official_account`、`teacher/IP`、`parent_brand`、`related_entity`。

品牌、公司、老师、产品、平台、地区使用独立实体节点；多对多关系写 `entity_relations.csv`。

短别名、常见词、历史同名必须写 `disambiguation_notes`。不能因名称相似自动合并。

天津回归中，“北宋”必须能区分北宋教育/北宋公考与历史朝代污染；该规则只能出现在 fixture / test data，不得写成生产逻辑。

## 7. 证据政策

核心规则：

- 搜索摘要只作线索，关键事实打开原页面；
- A1：政府/高校/监管等高质量独立来源；A2：机构第一方；B：稳定实名平台；C：软文/榜单/聚合；
- A1 只支持它直接陈述的事件或关系，不泛化为机构全部能力背书；
- 同一稿件转载不重复计数；同 URL 多用途引用需结构化说明；
- 每条重要陈述标：确认事实、机构自述、代理指标、分析推断；
- Evidence ID 使用 `E\d+`，正文引用 `[E001]`。

## 8. 五维 GEO Score 保持 v2.0，不改权重

继续使用：

- Query Coverage /30
- Entity Clarity /25
- External Diversity /20
- Concept Ownership /15
- Freshness /10

满分 100。不得为了任何具体机构调权重或写死加分。

逐维理由写 `score_details.json`；最终数值由 `scripts/score_geo.py` 计算。证据置信度独立于总分。

## 9. IP Measurement

深度地区模式默认增加 IP Measurement，无品牌问题例如：

- `{region}申论老师推荐`
- `{region}行测老师推荐`
- `{region}公考面试老师推荐`
- `{region}事业单位面试老师推荐`
- `{region}选调老师推荐`
- `{region}谁最懂本地公考考情`

IP Measurement 与机构 Measurement 分开。人物不进入机构总榜。

如果实际 Run 没有执行 IP Measurement，正式报告只能写“IP实体 / 专家可见性观察”，不得写“IP GEO 排名”。

## 10. Report Product：前台商业化，后台工程化

正式报告定位：**Industry Intelligence Report / Strategy Consulting Report**。

Main Report 优先讲结论、竞争格局、机会和行动，不堆 `candidate_pool.csv`、`query_purpose`、`regional-landscape` 等后台字段；完整方法、Schema、Candidate Audit、Query Results、Evidence Index 放 Appendix。

地区深度报告建议 20–28 页但不为页数注水。推荐顺序：

1. 封面
2. 研究概览 / KPI Cards
3. Executive Summary
4. GEO 综合排名与市场格局
5. Authority × Recall 竞争矩阵
6. Candidate Coverage / 调研完整性
7. 研究口径与评分体系
8. GEO Scorecard
9. 重点机构诊断
10. IP / Expert GEO
11. 固定 Query 占位观察
12. 概念山头 / Gap Map
13. 竞争路线
14. 区域进入策略
15. 90 天 GEO 内容与知识资产工程
16. 月度监测看板
17. Appendix

完整报告结构读 [report-template.md](references/report-template.md)，视觉规范读 [report-design-system.md](references/report-design-system.md)。

## 11. 强制图表

正式地区报告至少真实嵌入：

- `geo-score-ranking.svg`
- `authority-recall-matrix.svg`

深度报告建议同时包含：

- `dimension-heatmap.svg`
- `candidate-funnel.svg`

所有图表必须由本次 Run 的 `scores.csv`、`score_details.json`、`evidence.csv`、`query_results.csv` 动态生成。禁止复制旧报告图片、旧分数或硬编码机构。

使用：

```bash
python3 scripts/generate_charts.py <run-dir>
```

## 12. Report Model 与 Renderer

推荐统一：

```text
Research Data
→ Analysis Model
→ report_model.json
→ Selected Renderer
```

Report Model 保证 Word/PDF/HTML 使用同一章节、数字、排名、图表、结论和 Evidence Reference；三个 Renderer 不得各自重新让 LLM 生成正文。

生成：

```bash
python3 scripts/build_report_model.py <run-dir>
python3 scripts/generate_report_docx.py <run-dir>
python3 scripts/generate_report_pdf.py <run-dir>
python3 scripts/generate_report_html.py <run-dir>
```

一次任务只运行用户选择的正式 Renderer。PDF Renderer 可使用临时中间文件，但临时文件不得作为正式交付物保留或展示。

## 13. Strict Validation

使用：

```bash
python3 scripts/validate_run.py <run-dir> --strict
```

v2.1 strict 门禁至少检查：

- Preflight 三参数都确认；
- `requested_output_format` 存在；
- 只要求用户选择的正式 Artifact；额外正式 Artifact 给 warning；
- Semantic Coverage Gate 通过；
- Saturation Gate 通过；
- Candidate 状态统计与报告一致；
- 实体图谱节点、独立机构候选、可评估机构、正式评分机构、IP Entity、Evidence、三类 Query 数量与报告一致；
- 所有正式评分机构有 `entity_id`；
- `user_specified` 不产生 Score Bonus；
- 指定主体不得静默消失；
- Ranking 与 Authority × Recall 图表节点存在且数据来自本次 Run；
- Main Report 存在 Appendix；
- 正式报告不大面积暴露后台机器字段；
- Word/PDF 表格字号和分页符合设计系统。

## 14. 视觉 QA

不能只跑代码测试。正式输出后必须按用户选择格式做视觉检查：

- Word：渲染 DOCX 为逐页 PNG；
- PDF：逐页渲染 PDF；
- HTML：浏览器 viewport + print layout。

至少检查：封面、Executive Summary、排名图、Authority × Recall、Scorecard、重点机构、Query Gap、概念山头、90 天方案、Appendix 评分表、Evidence Index。

检查裁切、溢出、中文字体、图像清晰度、Label 重叠、孤页、异常空白页、字号过小、图表跨页、页脚覆盖正文。

## 15. 强制回归

### 天津 Real Smoke Test

只输入地区天津市、不指定机构、正式产出 Word。不得人工预置津仕或北宋。

必须检查：

- 津仕自然进入 Candidate Pool；
- 北宋/北学优仕自然进入 Candidate Pool；
- 北宋别名和法律主体正确解析并排除历史朝代污染；
- Discovery 不计 Query Coverage；
- A1 高校证据只支持对应维度；
- Candidate Pool 通过双门禁后才冻结；
- 最终只正式生成 Word；
- Word 真实包含咨询报告要求的关键章节和图表。

### 防天津过拟合

至少再测试两个不同市场：

- 本土机构 / IP 活跃市场，例如广东类市场；
- 全国品牌占主导的普通省级市场。

生产逻辑不得写死天津、津仕、北宋、天津考试结构；这些仅允许存在于测试 fixture。

## 16. 完成标准

v2.1 只有同时满足以下条件才可称完成：

- 三步 Preflight 正确且不重复提问；
- 用户选什么格式就只正式交付什么格式；
- v2.0 三类 Query 隔离和五维评分无回归；
- 六路 Discovery + Semantic Coverage 实现；
- Coverage Gate + Saturation Gate 实现；
- 指定主体强制调查但不加分；
- IP Measurement 与机构 Measurement 分开；
- 报告数字与结构化数据一致；
- Ranking、Authority × Recall 真实生成并嵌入；
- Main Report 是正式行业研究/战略咨询报告，而非运行日志；
- Appendix 保留完整可审计性；
- 天津真实 Smoke Test 与至少两个其他地区 Regression 通过；
- 最终正式文件完成视觉 QA。

## 禁止事项

- 不先定熟悉名单再找证据；
- 不把 Discovery / Verification 命中计入机构 Measurement；
- 不根据用户身份、记忆或历史对话自动加入机构；
- 不因 `user_specified` 提高分数、证据等级、排序或置信度；
- 不把品牌词、软文数量、粉丝量、搜索摘要包装成泛词领先、教学实力或市场份额；
- 不自动合并同名品牌、公司、老师；
- 不用旧天津报告的图片、分数、排名；
- 不默认同时生成 Word + PDF + HTML；
- 不把内部 CSV/JSON 作为用户正式报告；
- 不把“请自行导出”当完成。
