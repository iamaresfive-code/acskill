---
name: acs-gongkao-geo-research
description: 调查中国公务员及公职考试培训机构、品牌和老师/IP 的 GEO。v2.2 采用 Market Universe + AI Answer Measurement + GEO Asset Readiness：先确认研究谁，再用固定无品牌问题记录真实 AI Answer，并用公开资产解释可见度。区分模型原生/引擎搜索/外部检索增强、raw mention/positive nomination、Market Bucket/Measurement Target、Intent/Citation/Resolution 审计。唯一正式输出为 DOCX。不得用来评价教学质量、通过率、市场份额、招生量或一般口碑。
metadata:
  version: "2.2"
---

# 公考机构 GEO 调研 v2.2

版本定位：**Market Universe + Auditable AI Answer Measurement + Single DOCX Report**。

首要原则：**先确定研究谁，再测 AI 到底提不提；真实 AI Answer 是 Measurement，公开网页是发现/解释层。**

## 0. Preflight

只确认：requested_region、seed_entities、allow_discovery_supplement。Seed 只保证研究/解析，不自动 included、不加分。

正式输出固定 `deliverables/report.docx`。

## 1. Market Universe Gate

流程：

```text
Preflight
→ User Seed + System Discovery
→ Entity Resolution + Market Salience
→ Market Universe Draft
→ Explicit Measurement Target Review
→ USER CONFIRMATION GATE
→ Measurement Capability Check
→ AI Answer Measurement
→ Annotation / Resolution / Citation audits
→ Metrics + Robustness + Asset Readiness
→ DOCX
```

Market Bucket 与 Measurement Target 是两条独立轴。

`measurement_target` 必须显式审定：
- institution
- ip
- both

`both` 用于机构品牌入口与个人/IP入口同时成立的 Hybrid/IP-led Brand；机构题/IP题各算一套 Metrics，分母不得混合。Stage 2/3 不得因 `entity_type=studio/person` 或 target 改变已确认 A/B/C/D Bucket。

### Target Audit

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 填 new_explicit_target / evidence_basis / reviewer_reason / confirmed
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

`hybrid_signal`、institution_evidence、ip_evidence、cross_target_ai_signal 只是 Reviewer 提醒，不自动赋值 both。`hybrid_signal=true` 必须写 reviewer_reason。

## 2. Measurement Capability / Context

实际探测当前可用 AI/AI Search 引擎，禁止模拟第二模型。每 Run 固定：

- `answer_context_mode`: native | engine-native-search | external-search-augmented
- `context_isolation_level`: api-isolated | product-isolated | programmatic
- `query_variant_mode`: exact-query-repeat | semantic-retrieval-variants
- `measurement_profile`: snapshot | release

`external-search-augmented` 不得包装成模型原生 Recall。`semantic-retrieval-variants` 只能解释为 Query/Retrieval Robustness。`programmatic` 必须披露残余上下文风险。

## 3. Answer Cell 与 Legacy Variant Sidecar

新采样每个 Answer Cell 保存完整原文、citations、sample_run、context_id、fresh_context、query_variant_id。

**原始 `ai_answers.jsonl` 是冻结证据，不得为了过新版 Validator 事后改写。**

历史 Run 缺 `query_variant_id` 时：

```bash
python3 scripts/prepare_answer_variant_manifest.py <run-dir>
```

生成 `answer_variant_manifest.csv`：
- native-recorded：原 Answer 原生记录；
- legacy-reconstructed：按 sample_run + run-level variant mode 做迁移侧写。

legacy-reconstructed 不等于“原采样时已保存真实变体 query”。Validator 与 Robustness 必须使用同一套 raw-or-sidecar effective variant；冲突直接 fail，禁止静默 `run-{sample_run}` fallback。

## 4. Raw Mention ≠ Positive Nomination

`mention_intent`: recommended / listed / comparison / caveat / excluded。

只有：

```text
explicit-name / verified-alias
+ resolved
+ entity_correct=true
+ recommended / listed
```

才进入 Nomination。

锚定优先级：明确排除→excluded；明确条件性弱推荐/降优先级→caveat；明确推荐→recommended；正常入榜且未否定→listed；仅参照→comparison。

**榜单成员附普通缺点仍是 listed。**

## 5. Annotation / Resolution / Citation 三链分离

### 5.1 Annotation

```bash
python3 scripts/prepare_annotation_tasks.py <run-dir>
# Reviewer 只判 intent / match_method / entity_correct
python3 scripts/apply_annotation_labels.py <run-dir>
```

`apply_annotation_labels.py` 自动派生 nomination_rank/top3/first_mention，并重置 citation 字段。Intent Reviewer 不负责 Citation。

### 5.2 Resolution

resolution_status 是冻结上游实体解析；Annotation Reviewer 不重新猜。Resolution Audit 单独写 `resolution_rechecks.csv`。

### 5.3 Citation

```bash
python3 scripts/prepare_citation_audit.py <run-dir>
# Reviewer 逐 mention 核对实体级 citation refs
python3 scripts/apply_citation_audit.py <run-dir>
```

Release Answer 只要存在 citations，就必须有完整 `citation_audit.csv + citation_audit_summary.json`。linked refs 必须真实存在于原 Answer citations 且明确绑定该实体。不能因回答整体有引用而全部标 true，也不能在 Intent 重标时静默归零。

## 6. Blind Recheck

Answer Cells >=10 时 Annotation Blind Recheck 至少 20%。第二 Reviewer 可见冻结 canonical entity/resolution_status，只复判 Mention/Intent/Positive Set/顺序。

输出至少包括 Positive Set Agreement、Intent Exact Agreement、3-Class Agreement、Cohen's Kappa、confusion matrix。经验阈值只作为 provisional diagnostic。

## 7. Metrics

```bash
python3 scripts/compute_ai_metrics.py <run-dir>
```

`ai_metrics.csv` 一行 = `entity_id × measurement_target`。Hybrid both 两行。

透明指标：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。单引擎 Cross-model Consistency=N.A.。

## 8. Robustness

```bash
python3 scripts/compute_variant_robustness.py <run-dir>
```

必须输出：
- positive_persistence_3of3_rate；
- 0/N…N/N Hit Pattern；
- Pairwise Positive-set Jaccard；
- Exact Positive-set Match。

`positive_persistence_3of3_rate` 不是 Overall Repeat Stability。Semantic variants 下全部解释为 Query/Retrieval Robustness；legacy variant evidence 必须披露。

## 9. SERP / Page / AI 物理分离

- serp_results.csv：真实 Result Item；
- serp_mentions.csv：只允许 title/snippet；
- page_mentions.csv：打开正文后的提及。

`page_collection_status=not-collected` 时空 page 表表示未采集，不表示 0 mentions。

## 10. Validator

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

Release Validator 检查 target-specific denominator、variant raw/sidecar、context isolation、Annotation Recheck、Citation Audit、Robustness artifacts 等。

## 11. Report Contract

唯一正式交付 `deliverables/report.docx`。Market Bucket 由 Stage 1 冻结；Hybrid metrics 不反向修改 Market Role。

单引擎、外部检索增强、semantic variants、programmatic context、legacy-reconstructed variant 都必须显著披露。数据低稳定时禁止写“真实第一”“所有 AI 都不认识”“GEO 为零”。

## 12. 测试纪律

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

仅真正缺少 matplotlib/python-docx 等第三方依赖时，DOCX/图表集成测试允许明确 SKIP。AssertionError、Validator failure、RuntimeError 必须 FAIL / 非0退出；禁止宽泛 `except Exception` 吞掉真实失败。

## 13. 发布纪律

Synthetic Test 全绿仍不能直接发布。正式 v2.2 必须完成广东、天津、山东真实地区回归；Golden Reality Fixture 只能盲跑后做漏召回检查，生产 Discovery/Universe/评分不得读取。

GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。
