---
name: acs-gongkao-geo-research
description: 调查中国公务员及公职考试培训机构、品牌和老师/IP 的 GEO。v2.2 采用 Market Universe + AI Answer Measurement + GEO Asset Readiness：先由 User Seed 与系统发现建立并确认 Market Universe，再用固定无品牌问题记录真实 AI Answer；区分模型原生、引擎原生搜索与外部检索增强，区分 raw mention 与正向 nomination，并用公开资产解释可见度。唯一正式输出为 DOCX。不得用来评价教学质量、通过率、市场份额、招生量或一般口碑。
metadata:
  version: "2.2"
---

# 公考机构 GEO 调研 v2.2

版本定位：**Market Universe + Auditable AI Answer Measurement + Single DOCX Report**。

首要原则：**先确定研究谁，再测 AI 到底提不提；真实 AI Answer 是 Measurement，公开网页是发现/解释层。**

## 0. Preflight：只确认三项

用户只需确认尚未明确的：

1. `requested_region`；
2. `seed_entities`：希望一定覆盖的机构/品牌/老师 IP，可不完整；
3. `allow_discovery_supplement`：是否允许系统补充竞争主体，默认建议允许。

正式输出固定 `docx`。没有 Seed 且用户明确让系统自行发现时，进入 `blind-discovery-scan`，结果只能称“公开网络发现扫描”。

## 1. User Seed 边界

`user_seed=true` 只保证：必须进入 Universe Review、必须解析或明确 unresolved、不得静默消失。

Seed 不得提高 AI 提名率、Asset Score、Source Grade、Market Salience，不自动成为 local-core，也不自动 included。

## 2. Market Universe 先于 Measurement

流程：

```text
Preflight
→ User Seed
→ System Discovery Supplement
→ Entity Resolution + Market Salience Review
→ Market Universe Draft
→ Explicit Measurement Target Review
→ USER CONFIRMATION GATE
→ Measurement Capability Check
→ AI Answer Measurement + Open-Web Asset Audit
→ Annotation Blind Recheck + Resolution Audit
→ Metrics + Robustness + Asset Readiness + Concept Ownership
→ DOCX Report
```

`market_universe.csv` 必须显式记录：

```text
market_scope
operating_region
market_role
measurement_target
activity_status
platform_native
salience_basis
universe_status
downgrade_reason
```

`market_scope` 仅允许 national / regional / local / unknown，不能由 Recall 低反推“本地”。

`universe_status` 仅允许 included / observation / unresolved。v2.2 不设 silent excluded：Observation / unresolved 仍可参加 Measurement。

### 2.1 Market Bucket 与 Measurement Target 分离

Market Bucket 由 Stage 1 用户确认后冻结；Stage 2/3 不得因为 `entity_type` 或名称里有“工作室”就重新分桶。

`measurement_target` 必须在 Universe Confirmation 前显式审定：

- `institution`
- `ip`
- `both`

`both` 用于 IP-led Brand / 工作室 / 老师品牌化机构等 hybrid entity。它产生两套 target-specific Metrics；机构题和 IP 题分母不能合并。

例如：`market_role=local-active + measurement_target=both` 合法；不得因此把该主体从 B 本地机构桶自动移入 C Expert/IP。

### 2.2 Market Universe Review

由 Skill 生成/刷新 `universe_review.json`，A/B/C/D 四桶必须互斥且覆盖全集：

- A National Benchmarks
- B Local / Regional Institutions
- C Expert / IP
- D Observation / Historical / Unresolved

全国 Benchmark 默认约 4–6 个代表性公考品牌；有普通分校/办公点不等于应进 Benchmark。非 Seed Expert/IP 仅有单条地区内容时默认 Observation。

用户确认后才能：

```text
market_universe_confirmed = true
measurement_allowed = true
```

`confirm_market_universe.py` 必须拒绝尚未填写 `measurement_target` 的主体。

## 3. Candidate Rescue

以下主体在 Universe Confirmation 前必须专项 Rescue：User Seed、两个以上独立来源重复出现的主体、明显的平台原生地区 Expert/IP。

至少尝试官网/官方账号、公司或组织主体、地区、平台账号、创始人/老师、课程/服务、历史名/别名。无官网或工商不能单独成为排除 IP/工作室的理由。

## 4. Stage 2 前先做 Measurement Capability Check

执行者必须实际验证当前环境可访问哪些 AI / AI Search 引擎。禁止模拟第二模型、复制一个模型回答伪装多引擎、或用普通 Web Search Result 冒充 AI Answer。

代理/本地服务探测不能只看 shell exit code；若经过代理，必须检查 HTTP status/响应体，并在需要时用 `--noproxy` 或等价方式确认不是代理错误页假阳性。

真实探测后运行：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine-name \
  --context-mode external-search-augmented \
  --profile release \
  --repeat-runs 3 \
  --fresh-context \
  --context-isolation programmatic \
  --query-variant-mode semantic-retrieval-variants \
  --page-collection-status not-collected \
  --observation-date 2026-09-10
```

该脚本必须同时写 `run_metadata.json` 与 `measurement_config.json`。

引擎数对应：0=`asset-audit-only`，1=`single-engine`，2=`limited-multi-engine`，3+=`multi-engine`。

## 5. Measurement Context 与隔离等级必须显式区分

每个 Run 固定一种 `answer_context_mode`：

- `native`：模型原生回答，无额外搜索；
- `engine-native-search`：AI 产品自身搜索/联网模式；
- `external-search-augmented`：执行者先外部 Web Search/RAG，再把上下文提供给模型。

`external-search-augmented` 只能叫“外部检索增强条件下的 AI Answer Visibility”，不得包装成模型原生 Recall。

同时记录：

- `api-isolated`：真正独立 API 上下文；
- `product-isolated`：产品层可验证的新会话/新线程；
- `programmatic`：只能通过唯一 context_id、独立检索和执行纪律模拟隔离。

若为 `programmatic`，必须填写 `fresh_context_note`，显式披露仍可能存在同会话残余影响。

## 6. Exact Repeat 与 Semantic Retrieval Variant 不能混淆

`query_variant_mode`：

- `exact-query-repeat`：canonical query 原样重复，研究同条件重复性；
- `semantic-retrieval-variants`：为绕开缓存或测试查询/检索鲁棒性而使用语义等价变体。

如果同一 Query 被搜索通道强缓存，可以使用 semantic variants，但必须给每个 Answer Cell 写 `query_variant_id`。这类 Run 只能解释为 **Query/Retrieval Robustness Test**，不得称“严格同条件重复实验”。

## 7. Snapshot 与 Release

`snapshot` 可每 query×engine 只采 1 次，用于方法压力测试和单时点快照。

`release` 至少要求：

- `repeat_runs_expected >= 3`；
- sample_run 完整；
- fresh context；
- 唯一 context_id；
- query_variant_id；
- `compute_variant_robustness.py` 产出 robustness artifacts；
- Annotation Blind Recheck 覆盖至少 20%。

Release 当前只定义**协议完整性**，不把 30%、80%、10% 等经验阈值写成永久理论门槛。跨地区/跨引擎校准前，这些只能是 provisional diagnostic criteria。

## 8. Answer Cell 与原始回答

一个 Answer Cell = `query_id × engine/model × sample_run`。

`ai_answers.jsonl` 至少保存：

```text
answer_id
query_id
engine
model
sample_run
query_variant_id
context_id
fresh_context
answer_context_mode
sampled_at
response_text
citations
notes
```

不能只存摘要或事后重写答案。

## 9. Raw Mention ≠ Positive Nomination

所有实体原文出现先写入 `ai_mentions.csv`。`mention_rank` 记录 raw 出现顺序，哪怕实体 unresolved 或语境是否定/排除也不能物理删除。

`mention_intent` 五分类：

- recommended
- listed
- comparison
- caveat
- excluded

只有：

```text
explicit-name / verified-alias
+ resolved
+ entity_correct=true
+ recommended / listed
```

才进入 Nomination Rate。

### 9.1 Intent 锚定规则

判定优先级：

1. 明确否定/排除/不属于范围 → `excluded`；
2. 明确条件性弱推荐、降低优先级、显著保留意见 → `caveat`；
3. 明确推荐、优先、首选 → `recommended`；
4. 正常进入推荐榜单/候选列表且未被明确否定 → `listed`；
5. 仅作为横向参照 → `comparison`。

**关键规则：榜单/候选成员附带普通缺点，仍然是 listed。**

例如：

```text
第二名华图，线下体系成熟，但价格偏高。
```

仍为 `listed`，不能仅因“价格偏高”降为 caveat。

只有类似：

```text
只有基础很强时才建议考虑甲，否则不优先。
```

才属于 `caveat`。

```text
花生十三、高照并非广东专属，本条不展开。
```

属于 `excluded`。

完整正例/反例以 `references/data-schema.md` 为准。

正向提名使用独立 `nomination_rank=1..N` 连续编号。Top3 / First Mention 从 nomination_rank 派生。

## 10. Annotation Blind Recheck 与 Resolution Audit 分离

不能再让第二 Reviewer 从回答正文猜 `resolution_status`。

Annotation Review 只复判：

- Mention 是否存在；
- mention_intent；
- Positive Nomination Set；
- nomination 顺序。

第二 Reviewer 可以看到冻结的 canonical entity 和 resolution_status，因为这些是 Entity Resolution 的上游元数据，而不是 Annotation 任务答案。

Entity Resolution 正确性另做 `resolution_rechecks.csv`。

Release 建议输出：Positive Set Agreement、Intent Exact Agreement、三类 Agreement（recommended / listed / non-positive）、Cohen's Kappa、confusion matrix。80% 只能作为当前工程参考目标，不是行业通用标准。

## 11. AI/SERP Emergent Competitor 统一登记

Stage 1 Universe 不是封闭名单。真实 AI Answer 或 SERP title/snippet 出现名单外主体时，登记到 `ai_emergent_entities.csv`。

未解析 emergent 仍保留 raw AI/SERP mention、原文 rank 与来源；只有 resolved emergent 能进入正式 AI Metrics。Emergent 在报告中单列，不能回写 Stage 1 主榜。

## 12. Citation 必须实体级

`citation_linked=true` 不能由“该回答整体有 citations”推出。每条被引用 mention 必须填 `citation_refs`，且至少一个 URL 真实存在于该 Answer Cell citations，并经核对明确绑定实体。

## 13. Open-Web 与 AI Measurement 物理分离

- `serp_results.csv`：一行一个真实 Result Item；
- `serp_mentions.csv`：只允许 title/snippet 可见提及；
- `page_mentions.csv`：打开正文后发现的提及。

若未抓正文：

```text
page_collection_status = not-collected
```

空 `page_mentions.csv` 只表示“未采集”，不能解释为“正文 0 提及”。Stage 3 Asset Audit 前应补 Page Collection 或显著披露缺口。

## 14. 核心 Metrics

`ai_metrics.csv` 一行 = `entity_id × measurement_target`。

Hybrid `measurement_target=both` 必须有 institution 与 ip 两行，不能把 60 个机构 Answer Cells 和 24 个 IP Answer Cells 混成一个分母。

透明计算：

- Raw Mention Rate
- Nomination Rate
- Top3 Rate
- First Mention Rate
- Citation Rate
- Engine Coverage Rate
- Cross-model Consistency

单引擎时 Cross-model Consistency 必须 N.A.。不再制造黑箱 AI GEO 总分。

## 15. Robustness Metrics

运行：

```bash
python3 scripts/compute_variant_robustness.py <run-dir>
```

产出：

- `variant_robustness.csv`
- `query_set_similarity.csv`
- `robustness_summary.json`

旧“Repeat Stability”中“只统计至少一次命中的 entity×query，再看 3/3”的指标正式改名为：

`positive_persistence_3of3_rate`

它不是 Overall Repeat Stability，因为 0/3 稳定负例不在分母。

必须同时看：

- 0/N、1/N、2/N、N/N Hit Pattern；
- Pairwise Positive-set Jaccard；
- Exact Positive-set Match Rate。

若使用 semantic variants，这些是 Query/Retrieval Robustness 指标，不是模型随机重复稳定性。

## 16. GEO Asset Readiness

解释层 /100：Entity Clarity /25、Regional Semantic Density /20、Open-Web Assets /15、External Authority /15、Content Depth & Freshness /10、Data/Tool Assets /10、Platform Coverage /5。

它解释“为什么可能被认识/引用”，不等于 AI Answer Visibility。

## 17. Report Contract

唯一正式交付 `deliverables/report.docx`。

**Stage 1 Market Bucket 必须冻结。** `build_report_model.py` / `generate_charts.py` 不得再通过 `entity_type=studio/person` 把 B 本地机构重分到 C Expert/IP。

Hybrid entity 的两套 target metrics 可以同时保留，但不能反向改写 market_role / market_scope / bucket。

报告必须显式披露：measurement_profile、sampling_mode、answer_context_mode、query_variant_mode、context_isolation_level、repeat_runs、采样日期、page_collection_status。

数据稳定性不足时，只能写“在本次协议下提名率最高/未形成正向召回”，禁止写“真实第一/所有AI都不认识/所有模型都不会推荐”。

## 18. Validator

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

Measurement Gate 至少检查：显式 measurement_target、target-specific denominator、context mode、variant mode、fresh context disclosure、raw/nomination ranks、emergent registry、citation refs、Annotation Recheck coverage、robustness artifacts、Page Collection 状态。

Report Gate 必须检查：Stage 1 冻结分桶未漂移；Hybrid 的两套 target metrics 未丢失。

## 19. 回归测试

每次方法/Schema 修改至少执行：

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

第三方 Word/图表依赖缺失时对应集成测试可 SKIP，但核心协议测试必须继续运行并明确列出 skip。

发布前仍需真实回归广东、天津、山东。Golden Reality Fixture 只允许盲跑结束后后验检查，生产 Discovery/Universe/评分不得读取它。

## 20. 研究边界

GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。用户提供的行业判断可帮助 Seed/Market Salience，但写成报告事实时必须区分用户判断、机构自述、代理指标和公开独立事实。
