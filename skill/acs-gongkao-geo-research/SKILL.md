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
→ USER CONFIRMATION GATE
→ Measurement Capability Check
→ AI Answer Measurement + Open-Web Asset Audit
→ 20% Blind Recheck
→ Metrics + Asset Readiness + Concept Ownership
→ DOCX Report
```

`market_universe.csv` 必须显式记录：`market_scope / operating_region / market_role / activity_status / platform_native / salience_basis / universe_status / downgrade_reason`。

`market_scope` 仅允许 national / regional / local / unknown，不能由 Recall 低反推“本地”。

`universe_status` 仅允许 included / observation / unresolved。v2.2 不设 silent excluded：Observation / unresolved 仍可参加 Measurement。

`downgrade_reason` 使用结构化枚举，不靠 notes 字面量猜原因。至少支持 `seo-only / insufficient-evidence / unresolvable / user-ruling / historical / out-of-scope`。

### Market Universe Review

由 Skill 生成/刷新 `universe_review.json`，A/B/C/D 四桶必须互斥且覆盖全集：

- A National Benchmarks
- B Local / Regional Institutions
- C Expert / IP
- D Observation / Historical / Unresolved

全国 Benchmark 默认约 4–6 个代表性公考品牌；有普通分校/办公点不等于应进 Benchmark。非 Seed Expert/IP 仅有单条地区内容时默认 Observation，正式纳入需要持续 Region × Public Exam 绑定、明确服务身份、稳定平台身份或独立 Authority。

用户确认后才能：

```text
market_universe_confirmed = true
measurement_allowed = true
```

## 3. Candidate Rescue

以下主体在 Universe Confirmation 前必须专项 Rescue：User Seed、两个以上独立来源重复出现的主体、明显的平台原生地区 Expert/IP。

至少尝试官网/官方账号、公司或组织主体、地区、平台账号、创始人/老师、课程/服务、历史名/别名。无官网或工商不能单独成为排除 IP/工作室的理由。

## 4. Stage 2 前先做 Measurement Capability Check

进入 AI Answer Measurement 前，执行者必须实际验证当前环境可访问哪些 AI / AI Search 引擎。禁止模拟第二模型、复制一个模型回答伪装多引擎、或用普通 Web Search Result 冒充 AI Answer。

真实探测后运行：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine-name \
  --context-mode native \
  --profile snapshot \
  --repeat-runs 1 \
  --allow-shared-context
```

引擎数对应：0=`asset-audit-only`，1=`single-engine`，2=`limited-multi-engine`，3+=`multi-engine`。

## 5. Measurement Context 必须物理区分

每个 Run 固定一种 `answer_context_mode`：

- `native`：模型原生回答，无额外搜索；
- `engine-native-search`：AI 产品自身搜索/联网模式；
- `external-search-augmented`：执行者先外部 Web Search/RAG，再把上下文提供给模型。

`external-search-augmented` 测到的是“外部检索增强条件下的 AI Answer Visibility”，**不得包装成模型原生 Recall**。不同 context mode 必须拆 Run。

## 6. Snapshot 与 Release 是两种不同证据等级

`measurement_profile=snapshot` 可每 query×engine 只采 1 次，用于方法压力测试、方向判断和单时点快照。

正式可发布 Measurement 使用 `release`：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine-name \
  --context-mode native \
  --profile release \
  --repeat-runs 3 \
  --fresh-context
```

Release 要求：每个 query×engine 至少独立采 3 次；`sample_run=1..N` 完整；每个 Answer Cell fresh context；`context_id` 唯一。这样降低上下文串扰和单次随机波动。

## 7. Answer Cell 与原始回答

一个 Answer Cell = `query_id × engine/model × sample_run`。

`ai_answers.jsonl` 必须保存完整原文以及：

```text
answer_id
query_id
engine
model
sample_run
context_id
fresh_context
answer_context_mode
sampled_at
response_text
citations
notes
```

不能只存摘要或事后重写答案。

## 8. Raw Mention ≠ Positive Nomination

所有实体原文出现先写入 `ai_mentions.csv`。`mention_rank` 记录 raw 出现顺序，哪怕实体 unresolved 或语境是否定/排除也不能物理删除。

每条 mention 必须标：

```text
resolution_status = resolved | unresolved
mention_intent = recommended | listed | comparison | caveat | excluded
```

只有同时满足以下四条才进入正式 Nomination：

1. `match_method = explicit-name | verified-alias`；
2. `resolution_status=resolved`；
3. `entity_correct=true`；
4. `mention_intent = recommended | listed`。

例如“某老师并非广东专属，本条不展开”属于 caveat/excluded：保留 raw mention，但不能提升 Nomination Rate。

正向提名使用独立 `nomination_rank=1..N` 连续编号。Top3 / First Mention 从 nomination_rank 派生，不从 raw mention rank 或 SERP rank 代替。

## 9. AI/SERP Emergent Competitor 统一登记

Stage 1 Universe 不是封闭名单。真实 AI Answer 或 SERP title/snippet 出现名单外新主体时，登记到 `ai_emergent_entities.csv`（兼容文件名，实际承担 Stage 2 emergent registry）。

它可以同时记录 `source_answer_ids` 与 `source_result_ids`。未解析 emergent 仍必须保存 raw AI/SERP mention、原文 rank 与来源；只有 resolved emergent 能进入正式 AI Metrics。

Emergent 在报告中单列，不能偷偷回写 Stage 1 预注册的 A/B/C 主榜。

## 10. Citation 必须是实体级关联

`citation_linked=true` 不能由“该回答有 citations”推出。

每条被引用 mention 必须填 `citation_refs`；至少一个 URL 必须真实存在于该 Answer Cell citations，且经核对指向该主体、其官方域或明确绑定该实体的页面。

## 11. Open-Web 与 AI Measurement 物理分离

- `serp_results.csv`：一行一个真实 Result Item；
- `serp_mentions.csv`：只允许 title/snippet 可见提及；
- `page_mentions.csv`：打开正文后发现的提及。

榜单正文写 12 家机构只能形成 Page Mention，不得让 12 家获得同一个 Query 的 SERP/AI Hit。Page fetch 是可选解释层；若没抓正文，可保留空表并明确披露“page layer 未采样”。

## 12. 核心 Metrics

透明计算：

- Raw Mention Rate
- Nomination Rate
- Top3 Rate
- First Mention Rate
- Citation Rate
- Engine Coverage Rate
- Cross-model Consistency

`Engine Coverage Rate` 表示多少个实际采样引擎至少提名过主体；`Cross-model Consistency` 只在 >=2 引擎时计算。单引擎必须 N.A.。

不再制造黑箱 AI GEO 总分。报告优先同时显示命中次数/Answer Cells与百分比，例如 `5/60 (8.3%)`。

## 13. 20% Blind Recheck

Answer Cells >=10 时，至少随机抽 20% 由第二 reviewer 独立复判，复判前不看首轮实体判断。至少检查 raw mention、alias、entity、mention_intent、nomination_rank、Top3、First Mention、实体级 citation。分歧必须记录 resolution，否则 strict fail。

## 14. GEO Asset Readiness

解释层 /100：

- Entity Clarity /25
- Regional Semantic Density /20
- Open-Web Assets /15
- External Authority /15
- Content Depth & Freshness /10
- Data/Tool Assets /10
- Platform Coverage /5

它解释“为什么可能被认识/引用”，不等于 AI Answer Visibility。

## 15. Report Contract

唯一正式交付 `deliverables/report.docx`。全国品牌、本地/区域机构、Expert/IP 分榜；Observation 与 emergent 单列。

报告必须显式披露：

```text
measurement_profile
sampling_mode
answer_context_mode_expected
repeat_runs_expected
fresh_context_required
sampled_at range
```

Snapshot、single-engine、external-search-augmented 都必须在标题/脚注中明确限定，不得包装成跨模型稳定排名或模型原生 Recall。

## 16. Validator

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

Validator 分模块检查：Universe Contract、Measurement Contract、Report Contract。Measurement Gate 包括引擎可达性确认、sampling mode、context mode、repeat runs、fresh context、raw/nomination ranks、emergent registry、citation refs、SERP/Page 物理分离和 Blind Recheck。

## 17. 回归测试

每次方法/Schema 修改至少执行：

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

第三方 Word/图表依赖缺失时对应集成测试可 SKIP，但核心协议测试必须继续运行并明确列出 skip。

发布前还必须真实回归广东、天津、山东。Golden Reality Fixture 只允许盲跑结束后后验检查，生产 Discovery/Universe/评分不得读取它。

## 18. 研究边界

GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。用户提供的行业判断可帮助 Seed/Market Salience，但写成报告事实时必须区分用户判断、机构自述、代理指标和公开独立事实。
