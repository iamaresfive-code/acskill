# 公考 GEO 调研方法论 v2.2

## 1. 研究定义

v2.2 将 GEO 分成两个互补但不能混淆的对象：

- **AI Answer Visibility**：用户不输入品牌名时，AI 实际是否提名、是否进入 Top3、是否首提、是否引用、是否跨模型稳定；
- **GEO Asset Readiness**：公开互联网和平台资产是否让机器容易识别、理解、确认和引用该主体。

前者回答“实际上被提到多少”；后者回答“为什么可能被提到”。

## 2. Market Universe 先于 Measurement

地区研究不能让搜索引擎单独决定“谁是这个市场的主要玩家”。Universe = User Seed + System Discovery + Entity/Market Salience Review + User Confirmation。

市场重要性与网页可见性分离：Market Salience 判断是否值得研究；Web Visibility 判断是否容易在公开搜索中出现。SEO 强不自动等于当地市场重要；私域/平台强也不应因开放网页弱而被直接排除。

User Seed 只保证必须研究/解析，不保证自动 `included`。完成 Rescue 后再决定 included / observation / unresolved。

## 3. 市场角色、分桶与 Measurement Target

- `national-benchmark`：全国公考品牌在本地区的代表性基准样本；
- `local-core`：有明确本地/区域运营与持续市场存在；
- `local-active`：本地活跃但证据/规模仍在确认；
- `expert-ip`：老师、规划、选岗、科目型内容实体；
- `historical`：历史活跃、当前新鲜度不足；
- `observation`：值得观察但不进入正式比较；
- `unclassified`：信息不足，禁止套用带地域含义的路线标签。

`market_scope` 描述主体整体经营/内容覆盖范围，不等同于品牌最早创立地。Benchmark 默认约 4–6 个；只有办公点/普通职业培训分校地址，不足以证明当前地区公考业务相关性。

**Market Bucket 与 Measurement Target 是两条独立轴。** `measurement_target` 必须在 Universe 确认前显式审定为 institution / ip / both，不能因为 `entity_type=studio/person` 或名称里出现“工作室”就在 Stage 2/3 改桶。Hybrid/IP-led Brand 可以 `market_role=local-active` 且 `measurement_target=both`，此时机构题与 IP 题分开计算两套指标。

## 4. AI Answer Measurement

### 4.1 固定题池

机构和 IP 分开，全部为无品牌问题。地区题池固定后不得根据已知竞争者改题。

### 4.2 Measurement Context 与 Answer Cell

不同联网方式不能混成同一个 GEO 指标。每个 Run 固定 `answer_context_mode`：

- `native`：模型原生回答，不额外联网；
- `engine-native-search`：由该 AI 产品自身联网/搜索模式回答；
- `external-search-augmented`：执行者先 Web Search/RAG，再把检索上下文提供给模型。

第三种测的是“外部检索增强后的 AI Answer Visibility”，不能写成“模型原生 Recall”。不同 context mode 应拆成独立 Run。

一个 Answer Cell 由 `query_id × engine/model × sample_run` 唯一确定，同时保存 `query_variant_id / context_id / fresh_context / sampled_at / response_text`。

`context_isolation_level` 必须区分：

- `api-isolated`：每个 Cell 使用真正独立 API 上下文；
- `product-isolated`：产品提供可验证的新会话/新线程隔离；
- `programmatic`：只能通过唯一 context_id、独立检索与执行纪律模拟 fresh context。此模式必须写 `fresh_context_note`，明确仍有残余串扰风险。

### 4.3 Repeat 与 Semantic Retrieval Variant 不得混淆

`query_variant_mode`：

- `exact-query-repeat`：同一个 canonical query 原样重复，用于同条件重复性；
- `semantic-retrieval-variants`：为绕开缓存或测试查询鲁棒性而使用语义等价检索式变体。它测的是 **Query/Retrieval Robustness**，不是严格同条件 stochastic repeatability。

如果执行环境发现完全相同 Query 被检索通道强缓存，允许切换到 `semantic-retrieval-variants`，但必须显式记录每个 `query_variant_id`，不得继续把结果叫“完全独立重复”。

`measurement_profile`：

- `snapshot`：每 query×engine 可只跑 1 次，用于方法压力测试和单时点快照；
- `release`：至少 3 个 sample_run，fresh context，且必须产出 robustness artifact。

Release 目前只定义**完整性门槛**，不把 30%/80% 等经验值硬编码为普适发布门槛；这些阈值只能作为 provisional engineering criteria，待多地区/多引擎校准。

### 4.4 原始 Mention 与正式 Nomination 分离

`mention_rank` 只记录原文实体出现顺序，不代表正向推荐。`mention_intent` 五分类：recommended / listed / comparison / caveat / excluded。

正式正向 Nomination 必须同时满足：explicit-name/verified-alias + resolved + entity_correct=true + mention_intent∈{recommended, listed}。

**锚定规则：**

1. 明确否定、排除、不属于范围 → excluded；
2. 明确条件性弱推荐、降低优先级、显著保留意见 → caveat；
3. 明确推荐、优先、首选 → recommended；
4. 正常进入候选/排行榜/推荐名单且未被明确否定 → listed；
5. 仅作为横向参照出现 → comparison。

关键约束：**“进入候选列表 + 普通短板描述”仍然是 listed；不能因为一句“价格偏高/班型较大/更适合某类人”自动降为 caveat。** 只有 AI 主动表达“仅在某条件下勉强可选/不优先/其他情况不建议”才进入 caveat。

正向提名另以 `nomination_rank=1..N` 连续编号；Top3 与 First Mention 从 nomination_rank 派生。

### 4.5 Annotation Blind Recheck 与 Resolution Audit 分离

Blind Annotation Review 只复判：Mention 是否存在、Intent、Positive Set、Nomination 顺序。第二 Reviewer 可拿到**冻结的** canonical mapping / resolution_status 作为输入，不要求它从一段回答正文猜工商主体或实体解析状态。

Entity Resolution 正确性另做 Resolution Audit。Annotation Agreement 与 Resolution Agreement 必须分开汇报。

建议同时报告：Positive Set Agreement、Intent Exact Agreement、recommended/listed/non-positive 三层 Agreement、Cohen's Kappa、confusion matrix。80% 只能作为当前工程参考目标，不是行业标准。

### 4.6 Emergent Entity 不得物理删除

AI Answer 或 SERP title/snippet 中出现 Stage 1 Universe 之外的新主体时，统一登记到 Stage 2 emergent registry。未解析主体仍保留 raw mention、原文顺序和 source IDs；只有 resolved 主体进入正式 AI Metrics。SERP emergent 与 AI emergent 共享同一实体解析链路。

### 4.7 Citation 口径

`citation_linked` 是实体级判断，不是“回答整体有引用”。只有该 mention 的 citation_refs 真实存在于 Answer Cell citations，并经核对确实指向该实体、其官方域或明确绑定实体的页面，才能标 true。

### 4.8 指标

正式 AI 指标：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。

**一行 Metrics = entity_id × measurement_target。** Hybrid both 产生两行，Institution 与 IP 分母禁止混合。

单引擎时 Cross-model Consistency 必须为空/N.A.；snapshot 或单引擎结果不得包装成跨模型稳定排名。不建议再造黑箱“AI总分”。

## 5. Robustness 指标

官方脚本 `compute_variant_robustness.py` 产出：

- `positive_persistence_3of3_rate`：旧“12.3% Repeat Stability”类指标的正确命名，只在至少一次正向命中的 entity×query 中看是否 N/N 命中；
- 0/N、1/N…N/N Hit Pattern；
- Pairwise Positive-set Jaccard；
- Exact Positive-set Match Rate。

0/N 稳定负例必须保留在 Hit Pattern 中，不能从“整体稳定性”讨论里消失。

如果 query_variant_mode=semantic-retrieval-variants，上述指标解释为 Query/Retrieval Robustness，不得写“模型重复稳定性”。检索结果相似度与回答 Positive Set 相似度的相关性可以做 exploratory diagnostic，但不进入 GEO Score。

## 6. Open-Web 只做发现与解释层

传统搜索用于 Entity Discovery、资产核验、第三方 Authority、来源解释。一条搜索结果必须拆成真实 Result Item；网页正文品牌写 `page_mentions.csv`，不得回填为 SERP Result Hit 或 AI Nomination。

`page_collection_status=not-collected` 时空表只表示未采集，不表示正文 0 提及。Page Collection 可在 Stage 3 Asset Audit 前补齐。

## 7. Platform-native IP Discovery

按 Region × Intent × Platform 组合发现。封闭平台无法直接抓取时，可用公开索引页、账号公开页、跨平台资料作为线索，但必须标明可访问边界。Platform-native Discovery 只负责补候选，不自动纳入主榜。

## 8. 20% Blind Recheck

当 Answer Cells >=10，Annotation Blind Recheck 至少覆盖 20% Answer Cells。分歧必须记录并解决；Resolution Audit 单独执行，不与 Annotation Agreement 混算。

## 9. GEO Asset Readiness /100

- Entity Clarity /25
- Regional Semantic Density /20
- Open-Web Assets /15
- External Authority /15
- Content Depth & Freshness /10
- Data / Tool Assets /10
- Platform Coverage /5

该分只解释基础设施，不等价于 AI Answer Visibility。

## 10. 来源与证据

A1 政府/高校/监管等高质量独立来源；A2 第一方官网/官方账号；B 稳定实名平台；C 营销榜单/聚合。C 类可证明语料存在，不可单独证明本地市场地位。“有本地地址”与“有本地公考业务”必须区分。

## 11. 报告解释纪律

- 全国品牌、本地机构、Expert/IP 的 **Market Bucket 由 Stage 1 冻结**，不得在 Stage 2/3 按 entity_type 重新分组；
- Hybrid both 可以在两个 Measurement Target 都有指标，但不能反向修改 Market Role；
- 单模型结果显著标注，不能冒充跨模型共识；
- external-search-augmented 必须写明外部检索增强，不得表述为模型原生 Recall；
- semantic-retrieval-variants 必须写成“查询/检索鲁棒性”，不能写成严格重复稳定性；
- 数据不足时只能写“在本次协议下提名率最高/未形成正向召回”，禁止写“真实第一/AI都不认识/所有模型都不会推荐”；
- 报告优先同时展示 `命中次数 / Answer Cells` 与百分比，避免把小样本差异包装成稳定排名。
