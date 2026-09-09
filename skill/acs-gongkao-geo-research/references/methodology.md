# 公考机构 GEO 调研方法论 v2.1

## 1. 研究定义

GEO 指机构、品牌或老师/IP 在生成式 AI、AI 搜索及传统搜索与生成式搜索融合环境中，被系统发现、理解、确认、召回和引用的能力。

默认采样模式为 `public-web-proxy`：调查公开可检索、可抓取、可复核的网页资产，构建 GEO 可见性代理指标。它不等于特定模型在特定时刻的真实答案。

只有对多个生成式搜索引擎使用同一题池并保存原始回答与时间，才可另列 `multi-engine sampling`。两类结果必须分开呈现。

任何报告都必须声明：GEO 观察指数不代表教学实力、市场份额、经营规模、真实口碑、学员效果或大模型官方推荐榜。

## 2. Preflight 先于 Research Run

v2.1 在研究前必须确认：

- 地区
- 指定关注主体决定
- 正式输出格式

这三个参数影响范围、强制召回和 Renderer，因此属于 Research Contract，而不是普通备注。

## 3. Candidate Discovery：从 Channel Coverage 升级到 Semantic Coverage

v2.0 的六路 Discovery 保留：user-query、exam-vertical、institutional、platform、expert-ip、entity-alias。

v2.1 增加一个更重要的约束：**渠道执行过，不代表关键语义已经覆盖。**

研究者先建立当地考试生态，再形成 Semantic Theme Map。每个 required theme 在 `discovery_coverage.csv` 中都必须有真实查询和复核状态。

Semantic Coverage 的判断对象是“当地重要问题空间”，不是“搜索引擎按钮是否点过”。

## 4. Candidate Freeze 双门禁

### Gate A：Semantic Coverage Gate

全部 required theme 必须 `covered|no-result-reviewed`。以下典型方向不得明显缺失：

- 当地主要公务员 / 公职考试类型
- Institutional Source
- Platform
- Expert/IP
- Entity Alias

### Gate B：Saturation Gate

目标是验证 Candidate Recall 已明显收敛。默认接受以下任一信号：

- 最新补漏轮新增率 <10%；
- 最新补漏轮新增可评估独立机构 <=1；
- 连续两轮无重要新增主体。

数据量很小时允许合理工程化调整，但必须在 Run Metadata / Audit 中解释。不能使用“第二轮低于 35% 就自动饱和”的旧式高阈值。

## 5. Query 三分法保持严格隔离

### Discovery

找对象、别名、公司、老师、关系、平台线索；不进入 Recall。

### Institution Measurement

全体可评分机构共享同一无品牌题池：

```text
query_type=generic
query_purpose=measurement
measurement_target=institution
status=sampled
```

只有这类 Query 进入机构泛词分母。

### IP Measurement

老师/IP 使用独立无品牌题池：

```text
query_type=generic
query_purpose=measurement
measurement_target=ip
status=sampled
```

人物结果不进入机构总榜。

### Verification

核验官网、法律主体、老师、课程、校区、关系、近期内容与外部来源；不进入 Query Coverage。

## 6. Entity Resolution

逐家建立：

```text
品牌
→ 公司/组织主体
→ 创始人
→ 老师/专家
→ 科目
→ 考试类型
→ 课程/产品
→ 校区/基地
→ 城市/区域
→ 平台
→ 外部引用
```

每条边记录证据和置信度。

用户指定的名称只是入口，必须尝试扩展 canonical / alias / legal / former / official domain / official account / teacher / parent brand / related entity。

同名、短别名、历史名必须人工可审计地消歧。禁止仅靠字符串相似度自动合并。

## 7. 五维 GEO 观察指数

总分 100，权重不变。

### Query Coverage /30

只由 Institution Measurement 支持。

参考锚点：

- 0–5：几乎无品牌词外自然出现
- 6–12：少量问题偶发出现
- 13–18：覆盖多个组别但稳定性一般
- 19–24：多数核心问题有可复核占位
- 25–30：覆盖广、跨组稳定，形成明确 Query → Page 资产

### Entity Clarity /25

观察品牌、公司、地区、老师、科目、产品、考试类型、基地、联系方式等关系能否被机器稳定确认。

### External Diversity /20

统计独立域名、跨平台来源、高质量第三方验证；同稿转载和站群必须去重。

### Concept Ownership /15

判断专业问题能否稳定指向某主体。宽泛的“某机构=公考培训”不算强占位。

### Freshness /10

以观察日为基准看近 30/90/180/365 天公开资产活跃度与准确性。

## 8. Authority × Recall

v2.1 将“权威”和“自然召回”真正拆开。

横轴：

```text
Measurement Recall Rate = generic_hits / generic_queries
```

纵轴：Evidence Authority Index，范围 0–100。

建议透明计算：

```text
35% Source Grade Quality
25% Independent Domain Diversity
20% Key Relation Cross-validation
10% Evidence Freshness
10% Duplicate Quality
```

推荐实现：

- Source Grade Quality：A1=1.0、A2=0.75、B=0.5、C=0.2 的证据均值；
- Independent Domain Diversity：独立域名数按 0/1/2/3/4+ 映射为 0/0.35/0.6/0.8/1；
- Key Relation Cross-validation：关键品牌/公司/老师关系中，被两个及以上独立来源支持的比例；无法计算时按 0；
- Evidence Freshness：近 365 天有效证据占比；
- Duplicate Quality：被计入的 evidence 中 `counting_scope!=ignored` 且无未处理重复告警的比例。

Authority Index 与 GEO Score 不是同一个分数，不能直接把 GEO 总分当作纵轴。

四象限：

- 右上：成熟占位型
- 左上：高权威低召回型
- 右下：主动铺量型
- 左下：基础薄弱型

象限阈值可以使用本 Run 中位数或透明固定阈值，但报告必须说明。

## 9. IP / Expert GEO

如果 Run 执行了 IP Measurement，可报告 IP Recall、Entity Confidence、Institution Relation、Subject Binding、Concept Ownership、Evidence Health。

人物粉丝量、播放量只作代理指标，不能直接提高机构总分或证明教学质量。

如果 `ip_queries=0`，只能写“IP实体 / 专家可见性观察”。

## 10. Candidate Discovery 漏斗

Main Report 用漏斗向普通读者解释研究完整度：

```text
候选记录
↓
独立机构候选
↓
具备评估条件
↓
正式评分
```

旁边列证据不足、merged、excluded、unresolved。

注意：Entity Graph Node 数量与“机构数量”严格区分。

## 11. 竞争路线

基于真实资产结构自动归纳，不参与评分。候选标签：

- 品牌权重型
- 知识基础设施型
- Query进攻型
- Expert/IP型
- 平台托管型
- Institutional Authority型
- 高权威低召回型
- 本地实体型

一机构可以主标签 + 副标签。路线判断必须可由 scores / evidence / query_results / entity_relations 回溯。

## 12. Concept / Gap

从实际 Measurement 的弱结果、无结果、默认答案集中度、同名污染、实体关系断裂中识别：

- 已占领概念
- 竞争中概念
- 无稳定占位概念
- 数据资产型机会
- IP型机会
- 地区/区县机会
- 考试垂类机会

不能把“没有搜索量数据的普通关键词”包装成确定商业机会。

## 13. 区域进入策略与 90 天工程

地区深度报告必须把 Gap 翻译成进入顺序：

- 哪些红海不要正面打
- 哪些 Gap 先抢
- 先做实体还是内容
- 先做哪个考试细分
- 如何建立第三方 Evidence
- 如何建立 Expert Entity

90 天计划必须分阶段并与本次 Gap 强关联：

- 0–30 天：Entity Engineering / Regional Query Tree
- 31–60 天：Knowledge Infrastructure / Expert Entity
- 61–90 天：Third-party Evidence
- 持续：Measurement Re-test / Query Attack

每阶段写目标、动作、为什么有效、验收指标。

## 14. 月度监测

建议核心 KPI：

- 无品牌召回率
- 首提率
- 引用率
- 正确实体率
- 可引用 Evidence 数
- 权威页面数
- 概念绑定稳定度
- 错误信息率

“文章数量”不能作为核心 KPI。

## 15. 时间窗口与可比性

历史比较只有在样本、题池、评分口径、采样环境和时间窗口可比时才计算变化；否则并列展示。

“本次未检索到”只表示本次范围内未发现，不等于互联网绝对不存在。

## 16. 防过拟合

生产逻辑不得写死天津、津仕、北宋、天津考试结构。这些案例只能出现在 fixture / smoke test。

至少用一个本土/IP活跃市场和一个全国品牌占主导的普通省级市场回归 Semantic Discovery 适配能力。
