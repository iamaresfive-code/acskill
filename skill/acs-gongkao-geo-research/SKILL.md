---
name: acs-gongkao-geo-research
description: 调查中国公务员及公职考试培训机构、品牌和老师/IP 的 GEO。v2.2 采用 Market Universe + AI Answer Measurement + GEO Asset Readiness：先让用户提供需要保证覆盖的 Seed 主体，再由系统补充并让用户确认 Market Universe；之后用固定无品牌问题记录真实 AI 回答中的提名、Top3、首提、引用和跨模型一致性，公开网页只用于解释资产成熟度与证据。唯一正式输出为 DOCX。不得用来评价教学质量、通过率、市场份额或一般口碑。
metadata:
  version: "2.2"
---

# 公考机构 GEO 调研 v2.2

版本定位：**Market Universe + AI Answer Measurement + Single DOCX Report**。

首要原则：**先确定研究谁，再测 AI 到底提不提；公开网页用于解释，不再替代 AI Answer。**

## 0. 启动协议：三步 Preflight，Word 固定输出

只确认尚未明确的三项：

1. `requested_region`；
2. `seed_entities`：用户希望一定覆盖的机构 / 品牌 / 老师 IP，可只给部分；
3. `allow_discovery_supplement`：是否允许系统继续补充竞争主体，默认建议允许。

正式输出固定：

```text
official_output_format = docx
```

不再询问 Word/PDF/HTML，不正式生成 HTML 或 PDF。

用户明确没有 Seed、要求系统自己发现时，进入 `blind-discovery-scan`。这类结果必须命名为“公开网络发现扫描”，不得称为完整地区竞争全景。

## 1. User Seed 的作用边界

`user_seed=true` 只表示：

- 必须进入 Universe Review；
- 必须完成实体解析或明确 unresolved；
- 不能静默消失。

它不得：

- 提高 AI 提名率；
- 提高 Asset Score；
- 提高 Source Grade；
- 自动变成本土核心；
- 自动进入榜首；
- **自动获得 `included`。**

Seed 初次建池若尚未完成 Rescue，应为 `unresolved + needs-review`。完成实体解析和市场核验后，再决定 included / observation / unresolved。

当 Seed 与 System Discovery 同名时，必须字段级合并：保留 `user_seed=true`，同时吸收 Discovery 的 aliases、scope、role、salience_basis、notes 等非空证据；不得只把 user_seed 改 true 后丢掉 Discovery 行。

## 2. v2.2 总流程

```text
Preflight
↓
User Seed List
↓
System Discovery Supplement
↓
Entity Resolution + Market Salience Review
↓
Market Universe Draft
↓
refresh_universe_review.py
↓
Stage 1 Validation
↓
USER CONFIRMATION GATE
↓
AI Answer Measurement
+ Open-Web Asset Audit
↓
20% Blind Recheck
↓
Stage 2 Measurement Validation
↓
AI Metrics + Asset Readiness
↓
Concept Ownership / Strategy Analysis
↓
report_model.json
↓
Single DOCX Renderer
↓
Final Report Validation + Visual QA
```

## 3. Market Universe 是独立研究层

Market Universe 回答：“这个地区有哪些值得研究的主体？”

它不能由 GEO Score、Recall 或 SEO 页面数反推。

`market_universe.csv` 必须显式记录：

- `market_scope`: `national|regional|local|unknown`；
- `market_role`: `national-benchmark|local-core|local-active|expert-ip|historical|observation|unclassified`；
- `operating_region`；
- `salience_basis`；
- `activity_status`；
- `platform_native`；
- `user_seed`；
- `universe_status`；
- `confirmation_status`。

`universe_status` 在 v2.2 只允许 `included | observation | unresolved`。不提供会让主体静默跳过 Measurement 的 `excluded` 状态；Observation / unresolved 仍保留 Measurement 资格。

“本地实体”只能来自地域事实和市场证据。低 Recall 不等于本地。

`market_scope` 描述整体经营/内容覆盖范围，不等于品牌最早创立地。品牌创立于外省但当前在本地区形成稳定运营，不构成逻辑矛盾；创立地写入 evidence/notes，不应单独决定 scope。

### 3.1 National Benchmark 只做代表性基准

`national-benchmark` 不是“所有在本地有地址的全国品牌”。默认约 4–6 个代表性全国公考品牌；超过 8 个必须解释每一个为什么都具有当前、明确的“地区 × 公考”业务相关性。

只有当地职业培训分校/办公地址，不足以证明当地公考业务相关性。此类主体可以保留 Observation，等待真实 AI Answer 是否主动提名。

### 3.2 Local / Regional Institution

至少需要“实体可解析 + 当前地区公考业务”两类证据。工商、官网、平台官方账号、校区、课程、师资都可参与，但纯营销榜单不足以证明本地市场地位。

### 3.3 Expert / IP

System Discovery 发现的 IP 若不是 User Seed，主榜纳入必须体现**持续的 Region × Public Exam 主题绑定**。

单条视频、单期播客、一次本地上岸经历，不足以自动进入 Expert/IP 主榜；默认 Observation。

持续系列内容、明确教学/咨询服务、跨平台稳定身份、机构师资身份、独立第三方 Authority 等可以支持 included。

## 4. Market Universe Review Contract + 用户确认 Gate

Agent 完成/修订 `market_universe.csv` 后必须执行：

```bash
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

`universe_review.json` 必须由 Skill 脚本产生，至少包含 distribution、A/B/C/D 四个互斥 buckets、SEO-only downgraded、unresolved_or_weak、bucket_audit。

四个 bucket 必须互斥且并集等于 `market_universe.csv` 全部主体。不得由执行者另写不可比的临时分桶脚本替代正式 Review Contract。

然后把 Review 给用户。用户可补充、删除、改分类。

用户确认后运行：

```bash
python3 scripts/confirm_market_universe.py <run-dir> --approved-by user
```

写入：

```text
market_universe_confirmed = true
measurement_allowed = true
```

未确认时禁止正式 AI Measurement。

## 5. AI Answer Measurement 是核心 GEO

正式地区 GEO 使用固定无品牌问题，保存每个 Engine/Model 的原始回答到 `ai_answers.jsonl`，实体提名写 `ai_mentions.csv`。

允许计入正文 Nomination 的 `match_method`：

- `explicit-name`
- `verified-alias`

仅 citation 中出现但正文未提名，不能算正文 Nomination。

### 核心指标

- `Nomination Rate`
- `Top3 Rate`
- `First Mention Rate`
- `Citation Rate`
- `Engine Coverage Rate`
- `Cross-model Consistency`

其中 `Engine Coverage Rate` 表示“多少个已采样引擎至少提到过一次”；`Cross-model Consistency` 则衡量同一批正向 Query 上不同引擎是否共同提名，二者不能混用。

`Top3` 与 `First Mention` 必须由 `mention_rank` 约束；Validator 会校验布尔字段与真实顺序一致。

不把 Web Search Proxy 的命中率称为真实 AI GEO Recall，也不再造黑箱“AI 总分”。

### AI-emergent competitor

Stage 1 Universe 是预先确认的研究合同，但不能成为封闭名单。正式 AI Answer 中若自然出现 Stage 1 未预置的新机构/IP：

1. 保存到 `ai_emergent_entities.csv`；
2. 记录来源 `answer_id` 并完成实体解析；
3. resolved 后允许进入 `ai_mentions.csv` / `ai_metrics.csv`；
4. 最终报告必须单列为 AI-emergent competitors；
5. 不得把它们回写进预先确认的 A/B/C 主榜，也不得因为不在初始 Universe 就静默忽略。

这样既保持预注册 Universe 的可比性，也避免真实 AI 新竞争者被研究名单过滤掉。

### 采样模式

- >=3 个独立 AI/AI Search 引擎：`multi-engine`
- 2 个：`limited-multi-engine`
- 1 个：`single-engine`
- 0 个：`asset-audit-only`

没有真实 AI Answer Measurement，不得生成“真实 AI GEO 排名”。

## 6. Open-Web 只做解释层，Result Item 与网页正文物理分离

必须使用：

```text
serp_results.csv
serp_mentions.csv
page_mentions.csv
```

规则：

- `serp_results.csv` 一行 = 一个真实 Query/Engine/Rank Result Item；
- `serp_mentions.csv` 只能匹配该 Result 的 title/snippet；
- 打开网页正文后看到的品牌写 `page_mentions.csv`；
- Page Mention 不得转换为 AI/Query Measurement Hit。

一篇榜单正文写 12 家机构，不等于 12 家都被该 Query 召回。

## 7. Platform-native IP Discovery

系统补充 Expert/IP 时必须按 `Region × Intent × Platform` 展开，而不是只跑全国泛词。

典型：

- `{region} × 公考规划 × 抖音/视频号`
- `{region} × 选岗 × 抖音/视频号`
- `{region} × 申论 × B站`
- `{region} × 面试 × B站/小红书`

从账号反向建立：

```text
账号 → 人物 → 机构 → 地区 → 科目/服务 → 概念
```

发现候选不等于自动纳入主榜。

## 8. Candidate Rescue

以下任一主体若仍 unresolved，Universe Confirmation 前必须专项 Rescue：

- `user_seed=true`；
- 在两个以上独立来源重复出现；
- 明显的平台原生本地 Expert/IP。

专项核验至少尝试：官网、公司/组织主体、地区、平台账号、创始人/老师、课程/服务、历史名/别名。

## 9. 20% Blind Recheck

当 AI Answer cells >=10，至少随机抽 20% 写入 `rechecks.csv`，由第二采样者在不知道首轮判定的情况下复判。

出现分歧必须写 `resolution`。未解决分歧禁止 strict pass。

## 10. GEO Asset Readiness：解释 AI 为什么可能认识它

Asset Readiness 满分 100，但不是最终 AI GEO 排名：

- Entity Clarity /25
- Regional Semantic Density /20
- Open-Web Assets /15
- External Authority /15
- Content Depth & Freshness /10
- Data / Tool Assets /10
- Platform Coverage /5

`Owned Source Dependency` 单独展示，不自动扣分。

## 11. Concept Ownership

对高价值用户意图形成 `concept_ownership.csv`，至少记录 concept、entity、strength、evidence/query 支持、时间边界。

例如“申论”“材料结构化”“选岗”“地市待遇”“公考规划”等必须来自本次 Universe 与真实资料，不写死地区案例。

## 12. 报告分榜，不混淆全国与本土

正式 Word 至少包含：

1. 封面
2. 研究概览 / Executive Summary
3. Market Universe
4. 全国品牌在本地区的 AI GEO
5. 本土 / 区域机构 AI GEO
6. Expert / IP GEO
7. Concept Ownership
8. GEO Asset Readiness
9. 重点主体诊断
10. 区域策略与 90 天工程
11. Appendix / Research Audit

不再用一个混合总榜把全国连锁、本地机构、个人 IP 全放在一起。

## 13. 唯一 Renderer：DOCX

正式链路：

```text
Research Data
→ report_model.json
→ generate_report_docx.py
→ deliverables/report.docx
```

不运行正式 HTML/PDF Renderer。若用户需要 PDF，让其从最终 Word 导出。

## 14. Validator 分阶段门禁

### Stage 1：Universe

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

只检查 Preflight、Seed 不消失、Market Universe、Review buckets。Measurement 尚未开始时，不因缺 queries/AI/report/docx 报几十个预期错误。

### Stage 2：Measurement

```bash
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
```

要求 Universe 已确认，并检查 AI Answer、SERP Result Item、20% Recheck、AI Metrics。

### Final：Report

```bash
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

再检查 Report Contract、Metrics 不丢失、DOCX-only、占位文案。

典型 ERROR：

- Universe 未确认却开始 Measurement；
- Review 分桶重叠或没有覆盖全部主体；
- 一个 Query/Engine/Rank 出现多个 Result Item；
- SERP Mention 实际来自网页正文；
- User Seed 从 Universe 消失；
- Report 把 national/unknown 主体写成本地机构；
- AI Metrics 有主体但 Report Model 丢失；
- deliverables 同时出现正式 PDF/HTML。

全国 Benchmark 超过 8 家触发 `benchmark-sprawl` warning，要求人工复核是否把“全国品牌有本地地址”误当成“代表性基准”。

## 15. 发布回归

每次 v2.2 方法变更至少执行：

```bash
python -m py_compile scripts/*.py
python scripts/test_v22.py
```

然后必须真实跑广东、天津、山东至少三个地区。

Golden Reality Fixture 只允许在盲跑结束后用于后验检查，生产逻辑绝不能读取它、不能预置主体、不能加分。

若一个版本在已知公开存在、具有明显地区资产的典型主体上出现大面积完全漏召回，版本不得发布，即使 Synthetic Test 和 validator 全绿。

## 16. 研究边界

GEO 不代表教学质量、通过率、市场份额、招生量或口碑。

用户提供“招生量大”“市场很火”等行业信息可以帮助确定 Seed / Market Salience，但若要写成报告事实，必须明确来源类型：用户判断、机构自述、代理指标或公开独立事实。

历史 references 文档状态以 `references/README.md` 为准；legacy/deprecated 文档不得覆盖 v2.2 当前协议。
