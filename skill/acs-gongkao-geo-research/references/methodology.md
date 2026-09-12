# 公考 GEO 调研方法论 v2.2

## 1. 研究定义

v2.2 将 GEO 拆成两个不能混淆的对象：

- **AI Answer Visibility**：固定无品牌问题下，AI 实际是否提名、Top3、首提、引用、跨引擎/变体表现；
- **GEO Asset Readiness**：公开互联网和平台资产是否让机器容易识别、理解、确认和引用主体。

前者回答“实际上被提到多少”；后者回答“为什么可能被提到”。

## 2. Market Universe 先于 Measurement

Universe = User Seed + System Discovery + Entity/Market Salience Review + User Confirmation。Seed 只保证必须研究/解析，不保证 included，不加分。

市场重要性与网页可见性分离：SEO 强不自动等于当地市场重要；私域/平台强也不应因开放网页弱而被直接排除。

## 3. Market Bucket 与 Measurement Target 是两条独立轴

Market Bucket 由 Stage 1 冻结：A National Benchmark / B Local-Regional / C Expert-IP / D Observation-Other。

`measurement_target` 必须显式审定为：
- institution
- ip
- both

`both` 用于机构品牌入口与个人/IP入口同时成立的 Hybrid/IP-led Brand。同一主体可以 `market_role=local-active + measurement_target=both`，但 Stage 2/3 不能据此把它从 B 桶改进 C 桶。

Target Review 不能再把 `entity_type=studio/person` 当答案。`prepare_measurement_target_audit.py` 会提供 organization/IP/cross-target 信号，`hybrid_signal` 只强制 Reviewer 审视，不自动赋值 both；Reviewer 必须写 evidence_basis，hybrid 行还必须写 reviewer_reason。

## 4. Measurement Context

每个 Run 固定一种 `answer_context_mode`：native / engine-native-search / external-search-augmented。第三种只能称“外部检索增强下的 AI Answer Visibility”，不能称模型原生 Recall。

Context Isolation 分为：api-isolated / product-isolated / programmatic。`programmatic` 必须显著披露残余上下文污染风险。

## 5. Exact Repeat 与 Semantic Retrieval Variant 不得混淆

`exact-query-repeat` 用于同一 canonical query 原样重复；`semantic-retrieval-variants` 用于语义等价检索式变体，测的是 Query/Retrieval Robustness。

新采样必须把 `query_variant_id` 原生记录进每个 Answer Cell。

### 5.1 Legacy Variant Sidecar

历史 Run 如果采样时还没有 `query_variant_id`，**不得为通过新版 Validator 改写冻结的 `ai_answers.jsonl`**。应运行：

```bash
python3 scripts/prepare_answer_variant_manifest.py <run-dir>
```

生成 `answer_variant_manifest.csv`。原生记录标 `native-recorded`；按历史 sample_run + run-level variant mode 恢复的迁移侧写标 `legacy-reconstructed`。

`legacy-reconstructed` 只能说明“当前能够审计地恢复 variant 身份”，不能事后声称“当时逐 Cell 已保存真实变体检索词”。Validator 与 Robustness 计算都接受 sidecar，但 raw/sidecar 冲突会报错。

## 6. Raw Mention 与 Positive Nomination 分离

`mention_intent` 五分类：recommended / listed / comparison / caveat / excluded。

正式正向 Nomination = explicit-name/verified-alias + resolved + entity_correct=true + recommended/listed。

关键锚定：列表成员附带普通缺点仍是 listed；只有明确条件性弱推荐、降优先级、明显保留才是 caveat；明确否定/排除才是 excluded。

Top3 与 First Mention 从独立 `nomination_rank` 派生，不从 raw mention 顺序或 SERP rank 推断。

## 7. Annotation、Resolution、Citation 必须拆成三条审计链

### 7.1 Annotation

Intent Reviewer 只判 Mention/Intent/match/entity_correct；不重新决定冻结的 `resolution_status`，也**不负责 Citation**。

`apply_annotation_labels.py` 会自动派生 nomination_rank/top3/first_mention，并主动把 citation 字段重置为空/false，防止旧引用在新 Intent 标注中被误继承或误删除。

### 7.2 Resolution

Entity Resolution 另做 Resolution Audit；unresolved raw mention 必须保留，但不得进入 Positive Metrics。

### 7.3 Citation

Citation Rate 是实体级指标，不能由“这个回答整体有 citations”推出，也不能在 Intent 重标时静默归零。

正式链路：

```bash
python3 scripts/prepare_citation_audit.py <run-dir>
# Reviewer 逐 mention 核对实体级引用
python3 scripts/apply_citation_audit.py <run-dir>
```

`citation_audit.csv` 保存每个 mention 的原 Answer candidate refs、linked refs、link basis、review status。linked refs 必须真实存在于该 Answer Cell citations，并明确绑定实体/官方域/可识别该主体的页面。

Release Run 只要 Answer Cells 存在 citations，就必须完成 `citation_audit.csv + citation_audit_summary.json`，并与 `ai_mentions.csv` 同步；否则 strict Validator fail。

## 8. Annotation Blind Recheck

Answer Cells >=10 时至少覆盖 20%。第二 Reviewer 可见冻结的 canonical entity/resolution_status，只复判 Mention/Intent/Positive Set/顺序。建议报告 Positive Set Agreement、Intent Exact Agreement、3-Class Agreement、Cohen's Kappa、confusion matrix。

80% 等数只能作为 provisional engineering target，不是行业理论门槛。

## 9. AI Metrics

`ai_metrics.csv` 一行 = `entity_id × measurement_target`。Hybrid both 必须有 institution/ip 两行，分母禁止混合。

透明输出：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。单引擎时 Cross-model Consistency 必须 N.A.。

## 10. Robustness

`compute_variant_robustness.py` 产出：
- positive_persistence_3of3_rate；
- 0/N、1/N…N/N Hit Pattern；
- Pairwise Positive-set Jaccard；
- Exact Positive-set Match Rate。

`positive_persistence_3of3_rate` 不是 Overall Repeat Stability，因为 0/N 稳定负例不在其分母。Semantic variants 下，这些是 Query/Retrieval Robustness 指标。

Robustness 必须使用 raw Answer 原生 `query_variant_id` 或审计 sidecar；禁止和 Validator 不一致的静默 `run-{sample_run}` fallback。

## 11. Open-Web 分离

`serp_results.csv` 一行一个真实 Result Item；`serp_mentions.csv` 只允许 title/snippet；`page_mentions.csv` 只记录打开正文后的提及。网页正文品牌不得回填为 SERP/AI Hit。

`page_collection_status=not-collected` 时空 page 表只表示未采集，不表示正文 0 提及。

## 12. 来源与证据

A1 政府/高校/监管；A2 第一方官网/官方账号；B 稳定实名平台；C 营销榜单/聚合。C 类可证明语料存在，不足以单独证明本地市场地位。

## 13. 报告解释纪律

- Market Bucket 由 Stage 1 冻结；
- Hybrid both 可有两套指标，但不能反向修改 Market Role；
- 单引擎不得冒充跨模型共识；
- external-search-augmented 不得表述为模型原生 Recall；
- semantic-retrieval-variants 不得表述为纯模型重复稳定性；
- legacy-reconstructed variant 必须披露为迁移侧写；
- 数据低稳定时只能写“在本次协议下提名率最高/未形成正向召回”，禁止写“真实第一/所有 AI 都不认识/GEO 为零”；
- 报告优先展示命中次数/分母与百分比。

## 14. 测试可信度

核心测试与 DOCX/图表集成测试必须区分。只有 `ImportError` 等真实第三方依赖缺失才允许 SKIP；AssertionError、Validator error、RuntimeError 等必须直接 FAIL / 非0退出，不能被宽泛 `except Exception` 伪装成 SKIP。

## 15. Release Gate

Release Gate 关注**协议完整性与可审计性**：target、variant、context、annotation、citation、robustness、recheck、denominator 是否完整。30%/80% 等经验阈值在广东/天津/山东和多引擎数据校准前只作为 diagnostic，不硬编码成普适理论门槛。

## 16. GEO Asset Readiness：没有证据 ≠ 0 分

Asset Readiness 解释的是「公开资产是否让机器容易识别、理解、确认和引用该主体」，它**不是**教学质量、通过率、招生量、市场份额或口碑指标，也不能替代 AI Answer Visibility。

七个维度（entity_clarity 25 / regional_semantic_density 20 / open_web_assets 15 / external_authority 15 / content_depth_freshness 10 / data_tool_assets 10 / platform_coverage 5）**只由可核验的公开证据算分**，换算表见 `data-schema.md` 第 18.2 节。

两条不可让步的纪律：

1. **没有找到证据 ≠ 0 分。** 未取到证据的维度写 `unknown` 并登记进 `unknown_fields`，不计入分母；已证据化权重不足时 Tier 记 U（证据不足）。把「本次没搜到」写成「主体一定没有」是本层最严重的口径错误。
2. **评分必须能从原始公开证据复算。** 每个数值维度都要能追到 `report_research_manifest.csv` 的具体证据行；只有 URL 经独立核验可达（HTTP 2xx，或被反爬拒绝但地址真实存在的 403/468/502）的证据才参与计分；404、域名不可达等不可核验行整行丢弃。

同时必须区分**可核验证据**与**未核验主张**：无 URL 的发现记录可以保留，但 `access_status` 只能记 `indexed-only`，且不参与任何计分。

## 17. Concept Ownership：只能来自可核验的公开内容绑定

概念绑定回答「哪个主体在公开内容中与哪个概念形成了可复核的关联」。它不得来自品牌名、行业常识、Reviewer 印象或 AI 回答中的共现。

每条绑定必须区分绑定类型，并遵守对应强度区间：

| binding_type | 含义 | strength |
|---|---|---|
| owned-declaration | 品牌在自有官网/官方账号主动宣称的定位与业务 | 8–10 |
| high-frequency-public-binding | 多个独立公开页面高频把该概念与主体绑定 | 6–8 |
| third-party-description | 第三方页面描述其专注于某概念 | 3–5 |
| single-incidental-mention | 仅在单次提及中出现 | 1–2 |

**单次第三方提及不得包装成强 Concept Ownership。**

## 18. Report Layer 的五层表述纪律

`analysis.json` 必须把事实、指标、代理指标、推断、建议分开记录，并且：

- GEO Visibility 指标只能表述为「本次协议下的可见度」，**禁止写成真实市场份额或市场排名**；
- Asset Readiness 是公开资产代理，Concept Ownership 是内容绑定代理，两者都不构成市场地位判断；
- 所有统计数字必须由脚本从最终持久化产物实算，不得手抄中间统计，避免 QA 修正后报告仍停留在旧版本。

## 19. Report Layer 门禁纪律

报告层必须与 Measurement 层同等对待：**空壳报告不得通过 strict**。`validate_run.py --stage report --strict` 必须对空 `asset_scores` / `concept_ownership` / `analysis.json`、空的 `diagnoses` / `strategy` / `plan_90_days` / `risks`、缺失或正文为空的核心章节、缺失的图表引用全部报错；渲染器本身在关键结构为空时必须直接失败退出，不得用占位文案兜底。
