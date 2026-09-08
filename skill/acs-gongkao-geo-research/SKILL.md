---
name: acs-gongkao-geo-research
description: Research current GEO and AI-search visibility of Chinese civil-service and public-exam training institutions by province, city, region, or named brand. Use when users ask for 公考机构GEO调查、GEO排名、地区公考竞争格局、机构AI搜索可见性、品牌实体分析、老师/IP GEO、GEO关键词空白、区域公考机构对比，or want a cited GEO research report. The workflow builds a query matrix, discovers competitors, grades evidence, scores GEO visibility, analyzes entity graphs and concept ownership, separates organic evidence from promotional content, and produces an auditable report. Do not use it to rank teaching quality, learning outcomes, market share, or general brand reputation.
---

# 公考机构 GEO 调研

调查中国公务员、事业单位、选调生等公职考试培训机构在生成式 AI、AI 搜索及传统搜索与生成式搜索融合环境中的可发现、可理解、可确认、可召回和可引用能力。

最终目标不是简单罗列搜索结果，而是回答四个问题：

1. 哪些机构能在不含品牌名的真实用户问题中被发现？
2. 搜索系统能否清楚确认机构是谁、在哪里、做什么、由谁提供什么服务？
3. 这些关系只有机构自己陈述，还是存在独立来源交叉确认？
4. 哪些地区、考试、课程、师资或决策问题仍存在可占领的 GEO 空白？

每项结论都应能回到具体 Query、来源 URL、证据等级和观察日期。分数是对证据的压缩表达，不得替代证据本身。

## 触发与边界

- 用于地区竞争格局、单机构深挖、多机构比较、品牌/老师实体、GEO 空白词或正式引用报告。
- “哪家教学最好”本身不是 GEO 研究；不要用 GEO 分数回答教学质量、市场份额或真实口碑问题。
- 默认模式是 `public-web-proxy`：公开网页可见性代理观察。只有真实采样多个生成式搜索引擎时才增加 `multi-engine sampling`，并与网页代理结果分开报告。
- 报告开头明确：GEO 观察指数不是教学实力排名、市场份额或任何大模型官方推荐榜；未做多引擎实测时不得声称“ChatGPT 真实推荐排名”或“所有 AI 排名”。
- 调查涉及当前公开信息，必须在本次任务重新联网检索；不得根据记忆假装已搜索。

### 四种研究模式

| 模式 | 何时使用 | 必须完成的核心工作 |
| --- | --- | --- |
| `regional-landscape` | 用户只给地区，或询问当地整体格局 | 地区考试生态、Generic Query 题池、10—20 个候选主体、分层竞争格局 |
| `institution-deep-dive` | 用户指定一个机构、品牌或老师/IP | 保留指定主体，补 5—8 家合理对标，完成实体图谱、泛词表现、外部验证和空白分析 |
| `institution-comparison` | 用户指定两个及以上主体进行比较 | 保留全部指定主体；新增主体只作 `Benchmark`，统一题池、窗口和评分口径 |
| `gap-analysis` | 用户询问空白词、机会问题或概念占位 | 从无结果、弱结果、实体歧义和概念归属不稳的真实查询生成 A/B/C Gap Map |

若请求同时涉及多个模式，以用户最关心的问题为主模式，其他模式作为子任务。例如“比较三家机构并找广东空白词”以 `institution-comparison` 为主，同时输出 Gap Map。

### 不应触发或应改道的请求

- 只问公告、大纲、招录人数、考试时间或题型题量：使用公考考情检索能力，不启动 GEO 评分。
- 只问某机构教学质量、师资水平、退费纠纷、真实口碑或市场份额：说明 GEO 证据不能回答这些问题，转为相应事实调查。
- 只要求撰写品牌宣传、SEO 文章或投放文案：不是本 Skill 的研究任务。
- 用户把“GEO 排名”等同“教学最好”时，先纠正口径，再决定是否继续做可见性研究。

## 解析请求

提取并记录：

| 字段 | 识别内容 | 默认与处理规则 |
| --- | --- | --- |
| `region` | 省、城市、都市圈或跨区域范围 | 缺失但机构地域明确时先从可靠来源核验；无法确定且会改变题池时询问用户 |
| `cities` | 核心城市、地级市或独立招录城市 | 省域任务根据当地考试生态选择，不默认只看省会 |
| `institution_names` | 机构、品牌、老师/IP，可为零个、一个或多个 | 零个则自动发现；指定主体无论证据强弱都保留 |
| `research_scope` | 四种研究模式之一 | 未指定时按上表自动判断 |
| `query_depth` | `quick`、`standard`、`deep`、`full` | 默认 `standard=20`；依次对应约 10、20、50、100 个实际采样问题 |
| `output_format` | 对话摘要、Markdown、完整运行目录、Word、图表 | 默认先交付有引用的 Markdown/对话报告；用户明确要求才生成 Word |
| `observation_date` | 实际采样日期 | 必须使用本次调查日期，不使用 Skill 创建日期或旧报告日期 |

用户说“深度”“完整”“详细”时至少使用 `deep`；明确说“100 个问题”或“全量题池”时使用 `full`。用户指定问题数时以用户数量为准，同时保持五组问题的合理覆盖。

开始搜索前先生成一张范围卡，至少写明：

```text
研究模式：
地区与城市：
指定主体：
自动发现/对标规则：
查询深度与预计问题数：
采样模式：public-web-proxy / multi-engine sampling
观察日期：
交付格式：
已知限制：
```

缺失信息若不影响方向，可以采用明确默认值继续；若会改变地区、指定机构、研究模式或真实采样范围，则用一个最小问题向用户确认，不猜测。

### 地区和候选主体规则

- 只有地区时，先识别当地主要城市、独立招录体系、主要考试及真实笔面试生态，再地区化题池；不得把某省专属词机械复制到其他省份。
- 未给机构名单时，用 Generic Queries 发现 10—20 个有证据的主体，覆盖全国品牌、本土综合机构、细分机构、老师/IP 型品牌和近期新主体。
- 证据弱者标为“证据不足 / 待观察”，不为凑数量建立精确分数。
- 单机构研究自动增加 5—8 家合理对标；多机构比较保留全部指定机构，可增加 2—5 家，新增者必须标记 `Benchmark` 并解释选择理由。
- 名称相近、品牌与公司主体不一致、老师/IP 与机构关系不明时，先建立别名和待核关系，不提前合并实体。

## 按需读取参考文件

- 开始评分或解释口径前读 [methodology.md](references/methodology.md)。
- 生成地区化查询矩阵时读 [public-exam-query-bank.md](references/public-exam-query-bank.md)。
- 搜索、取证、分级、去重和引用时读 [source-policy.md](references/source-policy.md)。
- 建立中间数据或运行校验时读 [data-schema.md](references/data-schema.md)。
- 输出完整报告、Word 或图表时读 [report-template.md](references/report-template.md)。

不要一次性加载全部 references。普通地区概览通常读取题库、来源政策与方法论；只有需要落结构化文件、运行脚本或生成正式报告时，再读取数据规范和报告模板。

## 执行流程

按证据驱动顺序执行，不先定排名再找材料。下面 20 步是完整流程；`quick` 可以减少问题数和主体数，但不能跳过证据分级、Generic/Brand 分离、置信度和免责声明。

1. Parse Scope
2. Determine Region / Exam Ecosystem
3. Build Generic Query Matrix
4. Discover Candidate Institutions
5. Run Generic Searches
6. Run Brand/Entity Searches
7. Identify Official Sources
8. Collect Independent Sources
9. Deduplicate Domains / Articles
10. Grade Evidence
11. Build Entity Graphs
12. Identify Concepts
13. Score Five Dimensions
14. Assign Confidence
15. Compare Competitors
16. Detect GEO Modes
17. Build Gap Map
18. Draft Report
19. Validate Claims
20. Produce Evidence Appendix

### 阶段一：确定范围与当地考试生态（步骤 1—2）

1. 输出范围卡，固定研究模式、地区、主体、题量、采样模式、观察日期和交付格式。
2. 从官方或可靠来源核对当地实际考试类型、主要城市、独立招录体系和面试形式。
3. 将未经核实的地区术语标为候选，不直接进入最终题池。

完成标志：地区边界清楚，题池中的考试和面试术语均适用于目标地区。

### 阶段二：建立 Query Matrix 与候选池（步骤 3—5）

1. 按综合推荐、地域、产品、专项能力、决策五组生成 Generic Queries。
2. 为指定主体或初步候选生成 Brand Queries，但单独标记，不混入泛词统计。
3. 记录实际执行的问题、时间、渠道和结果；没有执行的问题不计入覆盖率分母。
4. 从 Generic Query 结果发现候选主体，并记录“由哪一道问题发现”。

完成标志：`queries.csv` 或等价题池记录完整，至少存在一个 Generic Query，候选池的发现依据可追溯。

### 阶段三：搜索、开源与证据入账（步骤 6—10）

1. 搜索结果页和 AI 摘要只用于发现线索；重要事实必须打开原始页面核验。
2. 优先识别官方主体、政府或主流媒体、独立平台，再补机构官网和稳定内容平台。
3. 每条证据记录机构、Query、标题、URL、域名、发布日期、访问日期、来源等级、是否独立、陈述类型、概念和核验备注。
4. 同一稿件跨站转载只算一个内容源；同域名多篇文章不自动等于来源多样。
5. 机构自述的排名、上岸率、学员数和市场地位必须标为 `institution-claim`，不能改写成独立事实。

完成标志：重点结论都有真实 URL，A1/A2/B/C 与 Own/Earned 已区分，重复稿件已标记。

### 阶段四：建立实体图谱与概念占位（步骤 11—12）

逐家回答：

- 品牌与公司/组织主体是否清楚？
- 创始人、老师/IP 与机构关系是否可确认？
- 科目、考试类型、课程产品、校区/基地和地域是否形成稳定关联？
- 哪些关系仅来自 Own Media，哪些得到 Earned Media 确认？
- 哪些概念只偶尔提及，哪些已经在多种问题和独立来源中形成稳定所有权？

关系不确定时使用“疑似关联”“机构自述”“尚无独立来源确认”等限定语，不补全缺失关系。

### 阶段五：评分、置信度与比较（步骤 13—17）

1. 按方法论中的评分锚点逐维打分，每一维先写证据理由，再运行评分脚本。
2. Query Coverage 主要由 Generic Queries 支撑；Brand Queries 只能补充实体确认。
3. 分数之外独立评定 `Evidence Confidence`，因为高可见性不等于高证据质量。
4. 比较时保持相同地区、题池、采样窗口和来源去重规则；条件不一致时分组展示。
5. 识别 GEO 模式和 Concept Ownership 后，再从真实弱结果生成 Gap Map。

完成标志：五维分数可复算、等级正确、置信度有依据，对标主体和指定主体已区分。

### 阶段六：成稿、校验与交付（步骤 18—20）

1. 先写核心答案，再给方法、榜单/分组、竞争格局、逐家分析、模式、Gap Map、局限和证据附录。
2. 所有强事实直接附链接或可回溯证据编号；没有证据时降格为待核或分析判断。
3. 运行 `validate_run.py`；修复 error，逐项人工判断 warning。
4. 对照用户最初问题逐项确认是否回答，不以文件齐全替代问题闭环。

完成标志：报告写明观察日期、范围、采样模式、证据覆盖和局限；所有文件可打开，脚本无 error。

Generic Query 与 Brand Query 必须分开。泛问题召回主要计入 Query Coverage；品牌词只用于确认官网、老师、课程、校区、专业领域和第三方关系，不能替代泛词占位证据。

每个重点机构建立：

```text
Brand → Company / Organization → Founder → Teacher / Expert
      → Subject → Exam Type → Course / Product → Campus / Base
      → City / Region → Results / Cases → Media / Platform
      → External Citation
```

Own Media（自有媒体）与 Earned Media（外部自然获得的引用）分开统计；同一稿件多站转载只算一个内容源。对事实、机构自述、代理指标和分析推断分别标注。

## 证据表达规范

最终文字中的每项重要陈述必须属于以下一种：

- `来源事实`：来源直接支持，表述不超出原文。
- `机构自述`：由机构、老师或关联账号自行发布，明确归因。
- `代理指标`：本次公开网页或真实引擎采样得到的观察结果，注明时间和样本。
- `分析推断`：基于多条证据形成的解释，写明推断依据和不确定性。

来源等级、软文识别和引用折价以 [source-policy.md](references/source-policy.md) 为准。不得用多篇同源转载制造“多方验证”，也不得用来源数量掩盖来源质量不足。

## 评分、结论与输出

- 用固定五维 100 分模型：Query Coverage 30、Entity Clarity 25、External Diversity 20、Concept Ownership 15、Freshness 10。
- 使用 `scripts/score_geo.py` 计算总分和等级，不手算后覆盖脚本结果。
- 每家机构同时给 `Evidence Confidence: High|Medium|Low`。低置信度或 60 分以下机构之间，不解释 1—2 分或一两个名次的细微差异。
- GEO 模式可多选：品牌权重型、Query 铺量型、实体知识图谱型、Expert/IP 型、地域实体型、主动 GEO 铺量型；允许按证据新增，不强迫单一归类。
- Gap Map 必须从实际查询结果提炼 Concept Ownership Opportunity，按 A 优先抢占、B 可系统布局、C 红海分层；不是普通 SEO 关键词堆砌。
- 深度研究尽可能保留 `queries.csv`、`evidence.csv`、`scores.csv`、`report.md`；可选图表和 `report.docx`。输出字段与目录见数据结构参考。
- 图表仅在数据质量足够时生成，数据必须来自实际评分：GEO 指数横向柱状图、Entity Verifiability × Query Coverage 象限图。
- 用户要求 Word 时使用可用的文档 Skill/工具生成可编辑 `.docx`，并完成渲染与版面验证。
- 默认不把研究产物写入任何外部知识库；用户明确要求归档时，遵守目标工作区的 `AGENTS.md`、授权边界和写入规范。

### 五维分数回答什么

| 维度 | 上限 | 核心问题 |
| --- | ---: | --- |
| Query Coverage | 30 | 不含品牌名的用户问题中，这个机构被发现和提及到什么程度？ |
| Entity Clarity | 25 | 品牌、主体、人物、科目、产品与地域关系是否清楚、稳定、可核验？ |
| External Diversity | 20 | 是否有真正独立且多样的外部来源，而非官网自述或同稿转载？ |
| Concept Ownership | 15 | 是否持续与某些地区、考试、课程、老师或方法概念建立稳定关联？ |
| Freshness | 10 | 关键实体和内容在当前观察窗口内是否仍然活跃、可访问、未明显过时？ |

分级固定为：S 85—100、A+ 80—84、A 70—79、A- 65—69、B+ 60—64、B 50—59、B- 45—49、C 低于 45。具体评分锚点只在评分时读取 [methodology.md](references/methodology.md)，不要凭印象给分。

### 置信度与排名解释

- `High`：核心结论有多类来源交叉支持，实体清楚，泛词样本和独立来源充分。
- `Medium`：主要关系可确认，但地区、题池、独立来源或时间覆盖存在明显缺口。
- `Low`：主要依赖第一方、品牌词、软文、旧页面或少量样本，只能作初步观察。
- 分数接近但置信度不同，应优先解释证据质量差异，不宣布确定胜负。
- 样本明显不可比时，用“领先组 / 中间组 / 待观察组”或“不足以排名”，不要强排 1—N。

### 交付层级

- `quick`：约 10 个问题，输出范围、代表性发现、证据边界、初步机构组别和下一步；不得伪装成完整榜单。
- `standard`：约 20 个问题，完成标准地区/机构报告、五维评分和证据附录。
- `deep`：约 50 个问题，保留完整运行目录，强化实体图谱、独立来源、逐家分析与 Gap Map。
- `full`：约 100 个问题，覆盖更多城市、考试和决策场景；必须控制同一观察窗口和去重口径。

无论深度如何，都要明确实际执行的问题数、成功打开的来源数、独立域名数、证据不足的主体数和无法核验的关键事项。

## 标准运行目录与脚本

深度研究按 [data-schema.md](references/data-schema.md) 创建运行目录：

```text
run-dir/
├── queries.csv
├── evidence.csv
├── scores.csv
├── report.md
├── report.docx       # 可选
├── geo-index.png     # 可选
└── geo-quadrant.png  # 可选
```

评分输入使用单个 JSON 对象或对象数组：

```bash
python3 scripts/score_geo.py scores-input.json --pretty
python3 scripts/score_geo.py --self-test
```

交付前运行：

```bash
python3 scripts/validate_run.py run-dir
python3 scripts/validate_run.py run-dir --strict
python3 scripts/validate_run.py --self-test
```

脚本检查结构、字段、分数和部分高风险措辞，但不能替代人工打开网页、确认时间、判断独立性和核对陈述是否被来源支持。

## 禁止事项

- 不捏造机构、网址、来源、检索过程、AI 推荐率或 ChatGPT 推荐率。
- 不因用户点名、品牌搜索结果多或标题写“第一”而提高评分。
- 不把机构官网的上岸率、排名、学员量等自述直接写成客观事实。
- 不把营销软文、聚合转载或搜索摘要当独立权威证据；重要事实打开原始网页核验。
- 不只用品牌词做排名，不以一次搜索声称长期稳定，不混用不同时间窗口而不说明。
- 不为无证据机构凑精确分，不把推测写成确认事实，不把 GEO 指数称为教学实力指数。
- 不把找不到网页直接解释为机构不存在、经营失败或教学能力弱。
- 不因全国品牌规模大而预设其在某地区或某类 Query 中领先。
- 不把单次观察外推为长期稳定结论；跨期比较必须说明题池、渠道和方法是否一致。
- 不把 Benchmark 混入用户指定机构后伪装成用户原始比较对象。
- 不在未实际访问某个生成式搜索引擎时填写该引擎名称、推荐率或回答结果。

## 交付前验证

1. 用 `scripts/score_geo.py` 生成或复核 `scores.csv` 对应分数。
2. 用 `scripts/validate_run.py <run-dir>` 检查日期、题池、Generic Query、证据、分数、URL、品牌词依赖、低置信度强结论和无来源强事实。
3. 核对所有事实引用可打开并支持对应陈述；搜索摘要只作发现线索。
4. 检查报告明确观察日期、研究范围、真实采样方式、证据覆盖和局限。
5. 若校验仍有 error，不得称完整报告已完成；warning 必须人工复核并在交付中说明。

最后人工核对：

- 用户指定的地区和机构是否全部保留；
- Generic 与 Brand Query 是否分开统计；
- 对标机构是否明确标记 `Benchmark`；
- 每个评分机构是否至少有一条可打开的证据；
- Own/Earned、事实/自述/代理指标/推断是否分开；
- 榜单、图表和正文使用的分数是否来自同一份 `scores.csv`；
- Gap Map 是否来自实际查询缺口，而不是普通 SEO 词表；
- 报告是否明确写出观察日期、采样模式、证据置信度和 GEO 免责声明；
- 用户要求 Word 时，是否生成可编辑文档并完成渲染检查；
- 若只是对话摘要，是否仍提供足够链接让关键结论可复核。
