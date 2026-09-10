# 公考 GEO 调研方法论 v2.2

## 1. 研究定义

v2.2 将 GEO 分成两个互补但不能混淆的对象：

- **AI Answer Visibility**：用户不输入品牌名时，AI 实际是否提名、是否进入 Top3、是否首提、是否引用、是否跨模型稳定；
- **GEO Asset Readiness**：公开互联网和平台资产是否让机器容易识别、理解、确认和引用该主体。

前者回答“实际上被提到多少”；后者回答“为什么可能被提到”。

## 2. Market Universe 先于 Measurement

地区研究不能让搜索引擎单独决定“谁是这个市场的主要玩家”。Universe = User Seed + System Discovery + Entity/Market Salience Review + User Confirmation。

市场重要性与网页可见性分离：

- Market Salience：是否值得进入地区竞争研究；
- Web Visibility：是否容易在公开搜索中出现。

SEO 强不自动等于当地市场重要；私域/平台强也不应因开放网页弱而被直接排除。

User Seed 只保证必须研究/解析，不保证自动 `included`。Seed 初始状态应为 `unresolved` 或 `needs-review`；完成 Rescue 后再决定 included / observation / unresolved。

## 3. 市场角色与范围

- `national-benchmark`：全国公考品牌在本地区的**代表性基准样本**；
- `local-core`：有明确本地/区域运营与持续市场存在；
- `local-active`：本地活跃但证据/规模仍在确认；
- `expert-ip`：老师、规划、选岗、科目型内容实体；
- `historical`：历史活跃、当前新鲜度不足；
- `observation`：值得观察但不进入正式比较；
- `unclassified`：信息不足，禁止套用带地域含义的路线标签。

`market_scope` 描述主体整体经营/内容覆盖范围，不等同于“品牌最早创立地”。一个品牌可以创立于北京、但当前在广东形成稳定区域运营；这不构成逻辑矛盾。创立地信息应写入 notes / entity evidence，不能单独决定 market_scope。

### 3.1 National Benchmark 不是“所有在广东有地址的全国品牌”

Benchmark 的目的，是给本地区结果提供少量可比基准，不是把全国连锁全部塞入主榜。

原则：

- 默认保留约 4–6 个代表性全国公考品牌；
- 超过 8 个必须解释为什么每一个都具有当前、明确的“广东 × 公考”业务相关性；
- 只有办公点/职业培训分校地址，不足以证明其当前广东公考业务相关性；
- 其他全国品牌即使有本地存在，也可留在 Observation，等待真实 AI Answer 是否主动提名。

### 3.2 Local / Regional Institution 的纳入

至少需要“实体可解析 + 当前地区公考业务”两类证据。工商注册地、官网、平台官方账号、校区、课程、师资都可以参与，但不能只凭营销榜单。

### 3.3 Expert / IP 的纳入

System Discovery 发现的 IP 若不是 User Seed，主榜纳入必须体现**持续的 Region × Public Exam 主题绑定**。单条视频、单期播客、一次“广东上岸经历”不足以自动进入 Expert/IP 主榜；这类主体默认 Observation。

可支持 included 的信号包括：持续系列内容、明确教学/咨询服务、跨平台稳定身份、机构师资身份、独立第三方 Authority 等。

## 4. AI Answer Measurement

### 4.1 题池

机构和 IP 分开，全部为无品牌问题。每个地区固定题池后不随竞争者调整。

### 4.2 Answer Cell

一个 `query_id × engine/model × sampled_at` = 一个 Answer Cell。原始回答完整保存到 `ai_answers.jsonl`。

### 4.3 提名规则

只有回答正文显式出现 canonical name 或已核验 alias 才算 Nomination。引用链接单独出现不算正文提名。

`mention_rank` 按回答中的真实提名顺序，不使用网页 Result Rank 代替。

### 4.4 指标

- Nomination Rate
- Top3 Rate
- First Mention Rate
- Citation Rate
- Cross-model Consistency

不建议在 v2.2 再造一个黑箱“AI总分”；主榜按提名率排序，Top3/首提/跨模型一致性并列展示。

## 5. Open-Web Proxy 降级为解释层

传统搜索用于：Entity Discovery、资产核验、第三方 Authority、来源解释。

一条搜索结果必须拆成真实 Result Item；打开网页后正文中的品牌列表写入 `page_mentions.csv`。正文品牌不得回填为 SERP Result Hit，更不得变成 AI Nomination。

## 6. Platform-native IP Discovery

按 Region × Intent × Platform 组合发现。对短视频/视频号等封闭平台无法直接抓取时，允许使用公开索引页、账号公开页、跨平台资料作为线索，但必须在 evidence 中标明可访问边界。

Platform-native Discovery 的目标是补候选，不是把所有出现过地区关键词的账号直接纳入主榜。

## 7. 20% Blind Recheck

当 Answer Cells >=10：随机抽至少 20%，第二采样者不看首轮实体判定独立复判。分歧必须记录并解决。

复判是 Measurement Quality，不是“再搜一遍看结果是否一样”；需要复核的是：是否真实提名、别名是否成立、实体是否正确、排名顺序是否一致。

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

A1 政府/高校/监管等高质量独立来源；A2 第一方官网/官方账号；B 稳定实名平台；C 营销榜单/聚合。C 类可证明语料存在，不可单独证明本地市场地位。

“有本地地址”与“有本地公考业务”必须区分。跨赛道职业培训品牌若只有广东分校地址、没有当前广东公考产品/师资/内容证据，不应仅凭地址进入 national-benchmark。

## 10. Market Universe Review Contract

`universe_review.json` 不是装饰性文件。它必须由 Skill 脚本生成/刷新，并至少包含：

- distribution；
- A/B/C/D 四个互斥 bucket；
- SEO-only downgraded；
- unresolved_or_weak；
- bucket audit。

四个 bucket 必须互斥且并集等于 `market_universe.csv` 全部主体。用户确认前运行 `validate_run.py --stage universe --strict`；确认后才能解锁 Measurement。

## 11. 报告解释纪律

- 全国品牌、本地机构、Expert/IP 分榜；
- “本地”必须有 market_scope 支撑；
- User Seed 在报告中不做特殊加分标记；
- 公开资产分高但 AI 提名低，应明确写成“Asset Ready / AI Recall Weak”；
- AI 提名高但公开网页弱，可写“AI Native Visibility / Open-Web Evidence Weak”；
- 单模型结果必须显著标注，不能冒充跨模型共识。
