---
name: acs-gongkao-geo-research
description: 调查中国公务员及公职考试培训机构、品牌和老师/IP 的 GEO。v2.2.1 沿用 v2.2 的 Market Universe + AI Answer Measurement + GEO Asset Readiness 方法，只修首次运行与中文客户报告体验：先确认研究谁，再用固定无品牌问题记录真实 AI 回答，并用公开资产解释可见度。唯一正式输出为中文 DOCX；工程审计数据保留在 Run 目录，不直接暴露给客户。不得用来评价教学质量、通过率、市场份额、招生量或一般口碑。
metadata:
  version: "2.2.1"
---

# 公考机构 GEO 调研 v2.2.1

> 数据契约仍为 `schema_version=2.2`。v2.2.1 是首次运行与客户报告体验补丁，不改变评分权重、Measurement 定义或 v2.2 的研究方法。

核心方法：**先确定研究谁，再测 AI 到底提不提；真实 AI 回答是 Measurement，公开网页是发现/解释层。**

正式交付固定为：`deliverables/report.docx`。

## 0. Preflight

只确认用户尚未给出的三项：

- 地区；
- 一定要覆盖的机构 / 品牌 / 老师 IP Seed List；
- 是否允许系统补充竞争主体。

Seed 只保证研究与解析，不自动进入主榜，不加分。

## 1. Market Universe Gate

流程：

```text
Preflight
→ User Seed + System Discovery
→ Entity Resolution + Market Salience
→ Market Universe Draft
→ Measurement Target Review（第一轮）
→ USER CONFIRMATION GATE
→ Measurement Capability Check
→ AI Answer Measurement
→ Annotation / Resolution / Citation audits
→ AI-emergent Resolution
→ Measurement Target Review（第二轮，仅有新解析主体时）
→ Metrics + Robustness + Asset Readiness
→ 中文客户 DOCX
```

Market Bucket 与 Measurement Target 是两条独立轴。

`measurement_target` 必须显式审定：

- `institution`
- `ip`
- `both`

`both` 用于机构品牌入口与个人/IP入口同时成立的 Hybrid/IP-led Brand；机构题/IP题各算一套 Metrics，分母不得混合。Stage 2/3 不得因 `entity_type=studio/person` 或 target 改变已确认 A/B/C/D Bucket。

### 1.1 市场发现必须留下可核验来源

v2.2.1 新建的 `market_universe.csv` 增加：

```text
discovery_evidence_urls
```

每个准备 `included` 的正式研究主体，确认前至少需要 1 条可独立打开、可核验的公开来源 URL。优先级：第一方官网 / 官方账号 > 稳定实名平台 > 可信第三方页面。

如果无法取得来源：

- 不得为了凑榜静默确认；
- 明确标记证据不足；
- `universe_review.json` 应列出缺来源主体；
- 用户补充或系统继续发现后再确认。

旧的冻结 v2.2 Run 若没有该列，不追溯性判失败。

### 1.2 Target Audit 是两轮闭环

第一轮发生在 Stage 1，此时 `ai_emergent_entities.csv` 可能尚不存在，这是正常状态：

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 填 new_explicit_target / evidence_basis / reviewer_reason / confirmed
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

`apply_measurement_target_audit.py` 在 Stage 1 会把缺失的 `ai_emergent_entities.csv` 视为空集合，不再形成次序死锁。

第二轮仅在正式 AI 测量后解析出新的 AI-emergent 主体时触发。此时重新运行 prepare → review → apply，确保所有 resolved emergent 都有显式 target。

`hybrid_signal`、institution/ip evidence、cross-target raw mention 都只是 Reviewer 提醒，不自动赋值 `both`。

## 2. Measurement Capability / Context

实际探测当前可用 AI / AI Search 引擎，禁止模拟第二模型。每 Run 固定：

- `answer_context_mode`: native | engine-native-search | external-search-augmented
- `context_isolation_level`: api-isolated | product-isolated | programmatic
- `query_variant_mode`: exact-query-repeat | semantic-retrieval-variants
- `measurement_profile`: snapshot | release

边界：

- external-search-augmented 不得包装成模型原生 Recall；
- semantic-retrieval-variants 只能解释为 Query/Retrieval Robustness；
- programmatic 必须披露残余上下文风险；
- 单引擎结果不得表述为跨模型共识。

## 3. Answer Cell 与冻结原始证据

新采样每个 Answer Cell 保存完整原文、citations、sample_run、context_id、fresh_context、query_variant_id。

**原始 `ai_answers.jsonl` 是冻结证据，不得为了过新版 Validator 事后改写。**

历史 Run 缺 `query_variant_id` 时：

```bash
python3 scripts/prepare_answer_variant_manifest.py <run-dir>
```

允许使用 sidecar 做可审计迁移，但不得包装成“原采样时已记录真实变体 query”。

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

榜单成员附普通短板仍然是 listed；只有明确条件性弱推荐 / 降优先级才是 caveat。

## 5. Annotation / Resolution / Citation 三链分离

### Annotation

```bash
python3 scripts/prepare_annotation_tasks.py <run-dir>
python3 scripts/apply_annotation_labels.py <run-dir>
```

Reviewer 只判 intent / match_method / entity_correct。

### Resolution

resolution_status 是冻结上游实体解析；Resolution Audit 单独写 `resolution_rechecks.csv`。

### Citation

```bash
python3 scripts/prepare_citation_audit.py <run-dir>
python3 scripts/apply_citation_audit.py <run-dir>
```

Release Answer 只要真实带 citations，就必须完成 Citation Audit。

**如果原 Answer 环境根本不提供 citations：客户报告中的引用率必须显示“不适用”，不得显示 0%，更不得解释成“AI 零引用”。**

## 6. Blind Recheck

Answer Cells >=10 时 Annotation Blind Recheck 至少 20%。第二 Reviewer 可见冻结 canonical entity / resolution_status，只复判 Mention / Intent / Positive Set / 顺序。

## 7. Metrics

```bash
python3 scripts/compute_ai_metrics.py <run-dir>
```

`ai_metrics.csv` 一行 = `entity_id × measurement_target`。Hybrid both 两行。

透明指标包括：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。

这些是内部数据字段；客户报告默认翻译成中文，不直接展示内部字段名。

## 8. Robustness

```bash
python3 scripts/compute_variant_robustness.py <run-dir>
```

必须保留：

- positive_persistence_3of3_rate；
- 0/N…N/N Hit Pattern；
- Pairwise Positive-set Jaccard；
- Exact Positive-set Match。

客户报告不直接堆字段名，而翻译成：

- 三种问法持续命中率；
- 不同问法推荐名单平均重合度；
- 推荐名单完全一致率；
- 0/3、1/3、2/3、3/3 的稳定性分布。

## 9. SERP / Page / AI 物理分离

- serp_results.csv：真实 Result Item；
- serp_mentions.csv：只允许 title/snippet；
- page_mentions.csv：打开正文后的提及。

`page_collection_status=not-collected` 时空 page 表表示未采集，不表示 0 mentions。

## 10. Report Layer

报告层公开证据与原 AI Sampling Evidence 分开。

流程：

```bash
python3 scripts/score_assets.py <run-dir>
python3 scripts/generate_charts.py <run-dir>
python3 scripts/build_report_model.py <run-dir>
python3 scripts/generate_report_docx.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage report --strict
python3 scripts/qa_report_docx.py <run-dir>
```

三条数据硬约束不变：

1. **没有证据 ≠ 0 分**：缺证据维度内部记 unknown；客户报告写“暂不评分”；
2. **评分必须能从公开证据复算**；
3. **空壳报告不得通过**。

概念绑定合法强度：

| 绑定类型 | 强度 |
| --- | ---: |
| owned-declaration | 8–10 |
| high-frequency-public-binding | 6–8 |
| third-party-description | 3–5 |
| single-incidental-mention | 1–2 |

详细客户报告规则见 `references/customer-report-contract.md`。

## 11. 中文客户报告契约

正式 DOCX 是给中国用户看的咨询交付物，不是工程日志。

### 必须给用户看

- 核心结论；
- 全国品牌 / 本地机构 / 老师 IP 的 AI 可见度；
- 结果稳定性；
- AI 可见度 × GEO 资产基础；
- 概念占位；
- 重点主体诊断；
- 优先动作与 90 天行动；
- 必要的方法边界。

### 不应给用户看

- 内部字段与 enum；
- CSV / JSON / Python 文件名；
- Validator 错误码；
- Run 文件清单；
- Python dict / JSON 原始对象；
- 工程审计逐行明细。

工程底稿继续保留在 Run 目录，必要时单独审计。

### 图表原则

- 中文标题、中文主体名、直接数值标签；
- 概念占位用 Top N 条形图，不用稀疏热力图；
- 资产证据不足的主体不画成 0；
- 主体构成图改为“AI 可见度 × GEO 资产基础”决策矩阵；
- 内部 market_role / bucket 不作为客户图例。

## 12. Validator / Customer QA

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
python3 scripts/qa_report_docx.py <run-dir>
```

客户报告 QA 会阻断：

- 英文一级标题；
- snake_case / 内部字段；
- `.csv` / `.json` / `.py` 工程文件名；
- Python / JSON 原始对象；
- 无引用链时把引用率写成 0；
- 工程审计内容进入客户 DOCX；
- 核心章节只有标题无正文。

## 13. 测试纪律

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

测试包含：核心 v2.2、Target Closure、Report Layer、Empty-Audit Gate，以及 v2.2.1 Fresh Run 补丁回归。

只有真正缺少 matplotlib/python-docx 等第三方依赖时，DOCX/图表集成测试允许明确 SKIP。AssertionError、Validator failure、RuntimeError 必须 FAIL，禁止吞成 SKIP。

## 14. 发布纪律

正式小版本发布前必须：

- Fresh Run 从空环境跑通；
- 现有合规 RC 不回退；
- 中文客户报告 QA PASS；
- 图表人工视觉检查；
- main / tag 只在最终审核后更新。

GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。
