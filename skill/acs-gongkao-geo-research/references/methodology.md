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

## 3. 市场角色

- `national-benchmark`：全国品牌在本地区的基准样本；
- `local-core`：有明确本地/区域运营与持续市场存在；
- `local-active`：本地活跃但证据/规模仍在确认；
- `expert-ip`：老师、规划、选岗、科目型内容实体；
- `historical`：历史活跃、当前新鲜度不足；
- `observation`：值得观察但不进入正式比较；
- `unclassified`：信息不足，禁止套用带地域含义的路线标签。

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

## 10. 报告解释纪律

- 全国品牌、本地机构、Expert/IP 分榜；
- “本地”必须有 market_scope 支撑；
- User Seed 在报告中不做特殊加分标记；
- 公开资产分高但 AI 提名低，应明确写成“Asset Ready / AI Recall Weak”；
- AI 提名高但公开网页弱，可写“AI Native Visibility / Open-Web Evidence Weak”；
- 单模型结果必须显著标注，不能冒充跨模型共识。
