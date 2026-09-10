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

## 3. 市场角色与范围

- `national-benchmark`：全国公考品牌在本地区的代表性基准样本；
- `local-core`：有明确本地/区域运营与持续市场存在；
- `local-active`：本地活跃但证据/规模仍在确认；
- `expert-ip`：老师、规划、选岗、科目型内容实体；
- `historical`：历史活跃、当前新鲜度不足；
- `observation`：值得观察但不进入正式比较；
- `unclassified`：信息不足，禁止套用带地域含义的路线标签。

`market_scope` 描述主体整体经营/内容覆盖范围，不等同于品牌最早创立地。Benchmark 默认约 4–6 个；只有办公点/普通职业培训分校地址，不足以证明当前地区公考业务相关性。System Discovery 的非 Seed IP 若只有单条地区内容，默认 Observation；主榜纳入应体现持续的 Region × Public Exam 绑定、明确服务身份、稳定账号或独立 Authority。

## 4. AI Answer Measurement

### 4.1 固定题池

机构和 IP 分开，全部为无品牌问题。地区题池固定后不得根据已知竞争者改题。

### 4.2 Measurement Context 与 Answer Cell

不同“联网方式”不能混成同一个 GEO 指标。每个 Run 固定 `answer_context_mode`：

- `native`：模型原生回答，不额外联网；
- `engine-native-search`：由该 AI 产品自身联网/搜索模式回答；
- `external-search-augmented`：执行者先 Web Search/RAG，再把检索上下文提供给模型。

第三种测的是“外部检索增强后的 AI Answer Visibility”，不能写成“模型原生 Recall”。不同 context mode 应拆成独立 Run。

一个 Answer Cell 由 `query_id × engine/model × sample_run` 唯一确定，同时保存 `context_id / fresh_context / sampled_at / response_text`。

`measurement_profile`：

- `snapshot`：每 query×engine 可只跑 1 次，用于方法压力测试和单时点快照；
- `release`：正式发布口径，每 query×engine 至少独立运行 3 次，`sample_run=1..N`，且每个 Cell 必须 fresh context、唯一 context_id，避免上下文串扰与偶然波动。

Stage 2 前先真实探测当前环境可访问的 AI/AI Search 引擎，再用 `configure_measurement.py` 写入 Measurement Contract。不得模拟第二模型。

### 4.3 原始 Mention 与正式 Nomination 分离

`mention_rank` 只记录原文实体出现顺序，不代表正向推荐。每条 mention 必须标记 `mention_intent`：

- `recommended`
- `listed`
- `comparison`
- `caveat`
- `excluded`

只有 `explicit-name/verified-alias + resolved + entity_correct=true + mention_intent∈{recommended, listed}` 才进入正式 Nomination。

`comparison / caveat / excluded` 必须保留原始审计，但不得抬高 Nomination Rate。正向提名另以 `nomination_rank=1..N` 连续编号；Top3 与 First Mention 都从 `nomination_rank` 派生。

### 4.4 Emergent Entity 不得物理删除

AI Answer 或 SERP title/snippet 中出现 Stage 1 Universe 之外的新主体时，统一登记到 Stage 2 emergent registry。未解析主体仍保留 raw mention、原文顺序和 source IDs；只有 resolved 主体进入正式 AI Metrics。SERP emergent 与 AI emergent 共享同一实体解析链路，不因“不是 Stage 1 主体”而丢记录。

### 4.5 Citation 口径

`citation_linked` 是实体级判断，不是“回答整体有引用”。只有当该 mention 的 `citation_refs` 至少一条真实存在于 Answer Cell citations，并经核对确实指向该实体、其官方域或明确绑定该实体的页面，才能标 true。

### 4.6 指标

- Raw Mention Rate
- Nomination Rate
- Top3 Rate
- First Mention Rate
- Citation Rate
- Engine Coverage Rate
- Cross-model Consistency

单引擎时 Cross-model Consistency 必须为空/N.A.；snapshot 或单引擎结果不得包装成跨模型稳定排名。不建议再造黑箱“AI总分”。

## 5. Open-Web 只做发现与解释层

传统搜索用于 Entity Discovery、资产核验、第三方 Authority、来源解释。一条搜索结果必须拆成真实 Result Item；网页正文品牌写 `page_mentions.csv`，不得回填为 SERP Result Hit 或 AI Nomination。若未执行正文抓取，允许 `page_mentions.csv` 为空表，但必须披露 page layer 未采样。

## 6. Platform-native IP Discovery

按 Region × Intent × Platform 组合发现。封闭平台无法直接抓取时，可用公开索引页、账号公开页、跨平台资料作为线索，但必须标明可访问边界。Platform-native Discovery 只负责补候选，不自动把账号纳入主榜。

## 7. 20% Blind Recheck

当 Answer Cells >=10，随机抽至少 20%，第二采样者不看首轮实体判定独立复判。至少复核：raw mention、alias、entity、mention_intent、nomination_rank / Top3 / First Mention、实体级 citation。分歧必须记录 resolution。

## 8. GEO Asset Readiness /100

- Entity Clarity /25
- Regional Semantic Density /20
- Open-Web Assets /15
- External Authority /15
- Content Depth & Freshness /10
- Data / Tool Assets /10
- Platform Coverage /5

该分只解释基础设施，不等价于 AI Answer Visibility。

## 9. 来源与证据

A1 政府/高校/监管等高质量独立来源；A2 第一方官网/官方账号；B 稳定实名平台；C 营销榜单/聚合。C 类可证明语料存在，不可单独证明本地市场地位。“有本地地址”与“有本地公考业务”必须区分。

## 10. Market Universe Review Contract

`universe_review.json` 必须由 Skill 脚本生成/刷新，至少包含 distribution、A/B/C/D 四个互斥 bucket、结构化 SEO-only downgraded、unresolved_or_weak 和 bucket audit。四桶必须互斥且并集等于 `market_universe.csv` 全部主体。

## 11. 报告解释纪律

- 全国品牌、本地机构、Expert/IP 分榜；
- “本地”必须有 market_scope 支撑；
- User Seed 不加分；
- 公开资产分高但 AI 提名低，可写 `Asset Ready / AI Recall Weak`；
- AI 提名高但开放网页弱，可写 `AI Visibility Strong / Open-Web Evidence Weak`；
- 单模型结果必须显著标注，不能冒充跨模型共识；
- 报告必须披露 `measurement_profile / answer_context_mode / repeat_runs / fresh_context`；
- `external-search-augmented` 必须写明“外部检索增强”，不得表述为模型原生 Recall；
- 正式 release profile 至少 3 次独立采样，报告优先同时展示 `命中次数 / Answer Cells` 与百分比，避免把小样本差异包装成稳定排名。
