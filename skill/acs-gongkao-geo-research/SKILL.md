---
name: acs-gongkao-geo-research
description: 调查中国公务员及公职考试培训机构、品牌和IP名师在生成式搜索与AI搜索中的可见性。用于省、市或区域公考机构GEO排名、地区竞争格局、机构与名师实体分析、AI搜索可见性、候选机构召回、概念空白、指定机构比较及可引用的HTML研究报告。先以多渠道两轮发现建立候选池，再以独立Measurement题池统一评分；不得用来评价教学质量、上岸效果、市场份额或一般口碑。
metadata:
  version: "2.0"
---

# 公考机构 GEO 调研

当前版本：`v2.0`。本版把“先找全对象，再统一测量”设为地区全景调查的强制架构。

GEO 观察的是机构、品牌或老师/IP 在公开信息环境中被发现、理解、确认、召回和引用的能力。它不是教学质量、市场份额、经营规模、学员效果、真实口碑或任何大模型官方推荐排名。

## 先判断研究模式

| 模式 | 触发方式 | 主体范围 |
| --- | --- | --- |
| 地区全景 `regional-landscape` | 用户只给省、市或区域 | 用六条渠道两轮发现整个地区候选；统一测量后重点分析领先者，低证据主体进入待观察组 |
| 单主体深挖 `institution-deep-dive` | 用户点名一个机构、品牌或老师 | 只调查点名主体；不得自动补竞品 |
| 多主体比较 `institution-comparison` | 用户点名两个及以上主体 | 只比较点名集合；用户明确要求时才增加对标 |
| 空白机会 `gap-analysis` | 用户询问机会词、概念空白 | 从真实无结果、弱结果、实体歧义中形成机会地图 |

“哪家教学最好”、退费纠纷、市场份额、公告大纲或宣传文案不属于本 Skill。用户把 GEO 等同于教学排名时先纠正口径。

## 开始前问询

首次回复只补齐尚未给出的关键信息：

```text
开始前请确认：
1. 要调查哪个省、市或区域的公考机构 GEO 排名？
2. 是否需要把您自己的机构强制纳入报告？如需要，请提供准确对外名称；简称、曾用名或官网可选。
```

- 已给地区则不重复问地区。
- 地区全景必须询问是否纳入自有机构；用户未确认前不从画像、记忆或历史对话猜测。
- 自有机构使用 `owned-forced` 入选方式，强制保留但不加分；泛词未命中就如实记零。
- 单/多主体指定模式不再询问自有机构，只调查当前请求点名集合。
- 地区与机构报告默认调查可核验的 IP 名师，不再额外询问。

## 范围卡

搜索前记录：研究模式、地区与城市、指定主体、自有机构决定、查询深度、采样模式、观察日期和交付格式。默认深度 `standard`，默认采样模式 `public-web-proxy`，默认交付 `report.html`。

公开网页代理观察不等于真实 AI 回答。只有实际用同一题池采样多个生成式搜索引擎、保存原始回答和时间，才可另列 `multi-engine sampling`；两类结果不得混算。

## v2 三类查询

`query_type` 仍只有 `generic` 与 `brand`；新增且必须填写 `query_purpose`：

- `discovery`：发现候选与别名，可为泛词或品牌词；不进入覆盖率分母或命中。
- `measurement`：统一测量泛词召回；必须是 `generic`。只有 `generic + measurement + sampled` 进入分母。
- `verification`：核验主体、官网、名师、课程、关系与来源；不进入泛词覆盖。

不得把 Discovery 或 Verification 结果改记为 Measurement 命中。实际结果逐条写入 `query_results.csv`，`scores.csv` 的 `generic_hits`、`generic_queries`、`brand_hits` 必须由日志派生，而不是手填想象。

## 地区全景候选召回

### 六条发现渠道

1. `user-query`：当地用户会直接提出的机构、课程、科目、面试与决策问题。
2. `exam-vertical`：省考、国考、事业单位、选调、遴选、军队文职及当地真实专项。
3. `institutional`：政府、高校、招投标、培训合作、办学主体、招聘与公开活动来源。
4. `platform`：地图、视频、播客、问答、教育平台、稳定账号和站内检索。
5. `expert-ip`：老师实名、稳定别名、科目 IP、课程主讲人与创始人线索。
6. `entity-alias`：品牌简称、公司名、曾用名、老师/IP 与机构关系、同名污染排除。

标准档应覆盖六条；受限环境最低也须覆盖 `user-query`、`exam-vertical`、`institutional`、`entity-alias`，并在报告说明未覆盖渠道。

### 两轮发现与冻结

第一轮：按地区、考试、产品、师资和机构性来源建立初始池，所有线索立即写入 `candidate_pool.csv`，不能只把熟悉品牌放进表。

第二轮：围绕第一轮遗漏方向补搜本土小机构、老师型品牌、简称/公司名、非省会城市与平台线索。完成 `Missing Entity Audit`：逐项检查全国品牌、本土综合机构、细分机构、老师/IP 型品牌、新主体和各主要城市是否存在空白。

然后执行 `Candidate Pool Freeze`：归并别名，排除跨区/非公考/纯历史噪声，给每条候选确定最终状态。冻结前不得建立 Measurement 得分榜。

候选最终状态只允许：`scored`、`evidence-insufficient`、`merged`、`excluded`、`unresolved`。第二轮新增可评估实体占比高于 35% 时视为可能尚未饱和：继续一轮搜索，或在报告“第二轮新增占比说明”中解释停止依据。

## 指定主体模式

- 单主体或多主体只保留用户点名主体，入选方式为 `user-requested`。
- 用户明确要求增加对标时才可加入 `benchmark`，并说明选择依据。
- 指定主体即使泛词零命中也保留，不得用品牌词补成泛词命中。
- 指定模式不运行地区候选扩张；仍需建立实体、查询结果、证据和逐维评分理由。

## 实体治理

所有候选先进入 `entities.csv`，使用稳定 `entity_id`。品牌、公司、老师、平台、产品与地区是不同实体；多对多关系写入 `entity_relations.csv`，不把复杂关系塞进一个文本字段。

- 规范名、公司名、简称、曾用名和老师/IP 关系分别保存。
- 只按已核验别名做归并；可运行 `resolve_entities.py` 检查精确别名。
- 短别名、历史名或常见词必须写 `disambiguation_notes`，明确同名污染如何排除。
- 找不到官网不等于机构不存在；主体不清则标 `unresolved` 或 `evidence-insufficient`。
- 机构性 A1 证据只支持其直接陈述的合作、活动或主体关系，不自动成为对该机构全部能力的背书。

## 证据政策

开始取证时读 [source-policy.md](references/source-policy.md)，建表时读 [data-schema.md](references/data-schema.md)。核心规则：

- 搜索摘要只作线索；关键事实必须打开原页面。
- A1 为政府/高校/监管等高质量独立来源；A2 为机构官方；B 为稳定实名平台；C 为软文、榜单和聚合内容。
- 每条重要陈述标为确认事实、机构自述、代理指标或分析推断。
- 同一稿件转载不重复计数。同 URL 多用途引用必须填写 `duplicate_group`、`duplicate_reason`、`review_status=reviewed` 和 `counting_scope`。
- `evidence_id` 必须匹配 `E\d+`，如 `E001`；不得加 TJ、SD 等地区前缀。正文用 `[E001]` 回指。

## 五维评分与展示

开始评分前完整读取 [methodology.md](references/methodology.md)。五维权重保持不变：泛词覆盖 30、实体清晰 25、外部来源多样性 20、概念占位 15、内容新鲜度 10。

1. 每一维先在 `score_details.json` 写分数、理由、证据编号或查询编号。
2. 使用 `score_geo.py` 计算总分和等级；加 `--run-dir` 时命中指标从查询日志派生。
3. 分数之外独立评定证据置信度。
4. 入选方式 `discovered`、`user-requested`、`owned-forced`、`benchmark` 只解释样本来源，不参与加分。
5. 60 分以下或低置信度主体分组展示，不强调 1—2 分和精确名次；主榜不出现“本土最强”“唯一首选”等无充分证据措辞。

名师 GEO 单列，不和机构混排。粉丝量、播放量或宣传称号不直接给机构加分；只有可核验的“机构—名师—科目—产品—地域”关系才影响相应维度。

## 完整执行流程

1. 解析请求并输出范围卡。
2. 核验地区、城市、考试和面试生态。
3. 地区模式执行第一轮六渠道 Discovery；指定模式建立点名主体清单。
4. 建立初始 `candidate_pool.csv` 与 `entities.csv`。
5. 地区模式执行第二轮 Discovery 和 Missing Entity Audit。
6. 归并别名、排除噪声、补实体关系，冻结候选池。
7. 对冻结后的可评估主体生成同一套 Measurement 题池。
8. 逐题执行并写入 `query_results.csv`；不能仅写命中汇总。
9. 执行 Verification，核验官网、公司、老师、课程、地域、近期内容与独立来源。
10. 建立 `evidence.csv`、`entity_relations.csv` 和 `ip_entities.csv`。
11. 去重 URL/转载，评定来源等级、独立性、陈述类型与证据置信度。
12. 在 `score_details.json` 逐维写证据理由。
13. 运行评分脚本，生成并复核 `scores.csv`。
14. 撰写 `report.md`，包含候选覆盖审计和 Authority × Recall 诊断。
15. 草稿校验、修错、处理警告。
16. 生成 `report.html`，做浏览器/受限环境渲染检查。
17. 严格门禁通过后交付 HTML 和运行目录。

## 报告必须回答

- 候选池是否覆盖主要主体类型和城市？第二轮新增率是否显示仍可能漏项？
- 哪些机构在独立 Measurement 泛词中自然出现？哪些只是品牌核验可见？
- 谁在“权威性高/低 × 召回高/低”四象限中，依据是什么？
- 名师实体是否帮助形成稳定的机构—名师—科目—产品—地域关系？
- 领先者的优势、短板和可验证优化动作是什么？
- 哪些主体证据不足，只能进入待观察组？

报告结构与机器字段见 [report-template.md](references/report-template.md)。正文、标题、表头和结论用中文；英文仅保留文件名、字段名、枚举值、网址和通用技术缩写。

## HTML 渲染检查

推荐路径：

1. `python3 scripts/generate_report_html.py <run-dir>`。
2. 能用浏览器时直接打开 `report.html`，检查中文字体、标题、链接、宽表横向滚动；再用浏览器“打印为 PDF”检查 A4 分页、裁切、重叠和黑块。
3. 无 GUI 时至少做结构检查：运行生成器自测和严格校验；若有 Chromium，可用其 headless 截图/打印 PDF。环境不支持浏览器时必须在交付说明中标为未完成，不能声称已视觉检查。

本 Skill 不假设特定浏览器命令，因为宿主环境可能不同；调用者应使用当前环境已提供的浏览器或 PDF 渲染工具。

## 脚本与门禁

```bash
python3 scripts/score_geo.py scores-input.json --run-dir <run-dir> --pretty
python3 scripts/resolve_entities.py <run-dir>/entities.csv "待解析名称"
python3 scripts/validate_run.py <run-dir> --draft
python3 scripts/generate_report_html.py <run-dir>
python3 scripts/validate_run.py <run-dir> --strict
python3 scripts/test_v2.py
```

`--draft` 只允许制作中暂缺 HTML。`--strict` 在错误或未处置警告存在时返回非零；可保留的人工警告必须写入 `warning_resolutions.csv`，填写精确 `issue_code + issue_key`、处置结论、复核人和时间，复验后才放行。旧 v1.1 目录可被兼容识别为 `legacy-schema` 信息，不伪装成 v2 结果。

## 完成标准

- 地区模式已完成两轮、多渠道召回、漏项审计和候选池冻结；指定模式未扩张名单。
- `query_results.csv` 能复算泛词分母、泛词命中和品牌命中。
- 候选、实体、关系、证据、评分和报告中的对象及数量完全一致。
- 每个评分维度有理由及证据/查询编号；每个评分主体至少有一条真实可打开证据。
- 报告含候选覆盖审计、Authority × Recall、IP 名师、局限和证据附录。
- HTML 内 `[E001]` 可跳转到证据索引，来源网址可点击，打印样式不裁切宽表。
- `validate_run.py <run-dir> --strict` 返回 0；任何未处置警告都不能称为完成。
- 最终默认直接交付 `report.html`，同时保留完整运行目录供审计。

## 禁止事项

- 不先定熟悉名单再找证据；不把主流品牌列表当候选池。
- 不将 Discovery/Verification 命中计入 Measurement。
- 不根据用户身份或历史记忆自动加入机构。
- 不把品牌词、软文数量、粉丝量或搜索摘要包装成泛词领先、教学实力或市场份额。
- 不自动合并同名品牌、公司、老师或历史噪声。
- 不为证据弱主体凑精确排名，不把入选方式当质量等级。
- 不只交 Markdown/CSV，不把“请自行导出”当完成。
