# acs-gongkao-geo-research v2.2

> 公考行业 GEO 竞争研究 Skill：先确认“研究谁”，再测“AI 到底提不提”，最后用公开资产解释原因。

v2.2 不把“网页多”直接等同于“AI GEO 强”。正式研究拆成三层：

1. **Market Universe**：地区里真正值得研究的机构、品牌、Expert/IP；
2. **AI Answer Measurement**：固定无品牌问题下，AI 实际提名谁；
3. **GEO Asset Readiness**：官网、平台、第三方证据、地域语义等公开资产，用于解释为什么可能被 AI 识别/引用。

## Preflight

第一次只确认：

1. 调查地区；
2. User Seed：希望一定覆盖的机构/品牌/老师 IP；
3. 是否允许系统补充竞争主体。

Seed 只保证研究和解析，不加分、不自动 included、不自动成为本土核心。

正式输出固定为 Word：`deliverables/report.docx`。

## Market Universe Gate

System Discovery 后必须先形成并让用户确认：

- A 全国 Benchmark；
- B 本地/区域机构；
- C Expert/IP；
- D Observation/Historical/Unresolved。

确认前：

```text
market_universe_confirmed = false
measurement_allowed = false
```

确认后才能进入 Measurement。`market_scope` 只能来自实体/地域事实，不能由 Recall 低反推“本地”。全国 Benchmark 默认保持少量代表性样本；SEO 榜单出现不等于当地核心竞争者。

## Stage 2.1 Measurement Contract

广东真实回归证明：单引擎 + WorkBuddy 外部 Web Search 增强得到的结果，不能包装成“模型原生 Recall”。因此当前 v2.2 Draft 对 Measurement 增加了明确协议。

### 1. 先探测真实 AI Engine

执行者必须先实际确认哪些 AI / AI Search 能返回回答，再运行：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine \
  --context-mode native \
  --profile snapshot \
  --repeat-runs 1 \
  --allow-shared-context
```

禁止模拟第二模型。0/1/2/3+ 个真实引擎分别标为 `asset-audit-only / single-engine / limited-multi-engine / multi-engine`。

### 2. Answer Context 必须分开

每个 Run 只能使用一种：

- `native`：模型原生、不额外搜索；
- `engine-native-search`：产品自身联网/搜索回答；
- `external-search-augmented`：执行者先 Web Search/RAG，再把检索上下文给模型。

第三种只能叫“外部检索增强下的 AI Answer Visibility”，不能叫模型原生 Recall。

### 3. Snapshot 与 Release 分开

- `snapshot`：允许每个 query×engine 采 1 次，用于快速压力测试；
- `release`：正式发布口径，每个 query×engine 至少 **3 次独立采样**，`sample_run=1..N`，并要求 fresh context + 唯一 `context_id`。

正式发布示例：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine \
  --context-mode native \
  --profile release \
  --repeat-runs 3 \
  --fresh-context
```

## Raw Mention 不等于 Nomination

`ai_mentions.csv` 同时保存原始提及和正式正向提名。关键字段：

```text
mention_rank
nomination_rank
resolution_status
mention_intent
citation_refs
```

`mention_intent`：

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

例如“花生十三不是广东专属，本条不展开”仍要保留 raw mention，但应标 `excluded` 或 `caveat`，不能提高正向 Nomination。

Top3 / First Mention 从 `nomination_rank` 派生，不从网页排名或原始 mention 顺序硬推。

## Emergent Competitor 不得删除

真实 AI Answer 或 SERP title/snippet 出现 Stage 1 Universe 外主体时，统一登记到 `ai_emergent_entities.csv`。它现在承担 Stage 2 emergent registry：

- AI 来源记录 `source_answer_ids`；
- SERP 来源记录 `source_result_ids`；
- unresolved 主体仍保留 raw mention、rank、来源；
- 只有 resolved 主体进入正式 Metrics；
- emergent 永远单列，不偷偷改写 Stage 1 已确认主榜。

## Citation 必须是实体级

不能因为一个回答“整体有 citations”就把所有品牌 `citation_linked=true`。

若 `citation_linked=true`：

- `citation_refs` 至少有一个真实 URL；
- URL 必须存在于该 Answer Cell 原始 citations；
- 采样员确认它指向该主体、官方域或明确绑定该实体的页面。

## 核心指标

正式透明输出：

- Raw Mention Rate
- Nomination Rate
- Top3 Rate
- First Mention Rate
- Citation Rate
- Engine Coverage Rate
- Cross-model Consistency

单引擎时 Cross-model Consistency 必须 N.A.。不再造黑箱“AI GEO 总分”。

报告应优先同时显示命中次数和分母，例如 `5/60 (8.3%)`，避免把小样本差异包装成稳定排名。

## Open-Web 与 AI Measurement 物理分离

- `serp_results.csv`：真实 Result Item；
- `serp_mentions.csv`：只允许 title/snippet 可见提及；
- `page_mentions.csv`：打开正文后发现的提及。

一篇“十大机构”正文写 10 家，只产生 Page Mention，不产生 10 个 SERP/AI Hit。若本次不抓网页正文，可保留空的 `page_mentions.csv`，但必须披露 page layer 未采样。

## 20% Blind Recheck

Answer Cells >=10 时，至少随机复判 20%。第二 reviewer 不看首轮判断，复核 raw mention、alias、entity、mention_intent、nomination_rank、Top3、First Mention、实体级 citation。分歧必须记录 resolution。

## Validator

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

Measurement Validator 还会检查：引擎可达性确认、sampling_mode、context mode、repeat coverage、fresh context、raw/nomination rank、emergent registry、citation refs、SERP 物理分离与 recheck coverage。

## GEO Asset Readiness

解释层 /100：Entity Clarity /25、Regional Semantic Density /20、Open-Web Assets /15、External Authority /15、Content Depth & Freshness /10、Data/Tool Assets /10、Platform Coverage /5。它不等于 AI Answer Visibility。

## 运行顺序

```bash
python3 scripts/preflight.py ...
python3 scripts/build_market_universe.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/confirm_market_universe.py <run-dir> --approved-by user
# 实际探测 AI Engine
python3 scripts/configure_measurement.py <run-dir> ...
# Agent 执行固定题池并写入 raw answers / mentions / emergent / SERP / rechecks
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/score_assets.py <run-dir>
python3 scripts/generate_charts.py <run-dir>
python3 scripts/build_report_model.py <run-dir>
python3 scripts/generate_report_docx.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

## 依赖与测试

核心研究/校验仅需 Python 标准库。Word 需要 `python-docx`，图表需要 `matplotlib`。

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

第三方依赖缺失时 DOCX/图表集成测试可以 SKIP，但必须明确输出；核心研究协议测试不能因此整体崩溃。

## 发布纪律

Synthetic Test 全绿不能直接发布。正式 v2.2 仍需完成广东、天津、山东真实地区回归。Golden Reality Fixture 只能在盲跑后做后验漏召回检查，生产逻辑不得读取、注入 Candidate 或加分。

GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。
