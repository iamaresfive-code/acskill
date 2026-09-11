# acs-gongkao-geo-research v2.2

> 公考行业 GEO 竞争研究 Skill：先确认“研究谁”，再测“AI 到底提不提”，最后用公开资产解释原因。

v2.2 正式拆成三层：

1. **Market Universe**：地区里真正值得研究的机构、品牌、Expert/IP；
2. **AI Answer Measurement**：固定无品牌问题下，AI 实际提名谁；
3. **GEO Asset Readiness**：官网、平台、第三方证据、地域语义等公开资产，用于解释为什么可能被 AI 识别/引用。

正式输出固定为 Word：`deliverables/report.docx`。

## Stage 1：Market Universe

Preflight 只确认地区、User Seed、是否允许系统补充。Seed 只保证研究和解析，不自动 included、不加分。

Market Universe 必须显式审定：

```text
market_scope
market_role
measurement_target = institution | ip | both
universe_status
```

A/B/C/D Market Bucket 与 Measurement Target 是**两条独立轴**。Stage 2/3 不得因为 `entity_type=studio/person` 或主体名称含“工作室”就重新分桶。

既有 Run 若缺 `measurement_target`：

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 填 measurement_target_audit.csv：new_explicit_target / evidence_basis / review_status=confirmed
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

确认 Universe：

```bash
python3 scripts/confirm_market_universe.py <run-dir> --approved-by user
```

没有显式 measurement_target 的主体不能被确认。

## Stage 2：Measurement Contract

先真实探测可用 AI/AI Search 引擎，禁止模拟第二模型。代理/本地服务探测要检查 HTTP 状态码和响应体，不能只看 shell exit code；必要时绕过代理复核。

配置示例：

```bash
python3 scripts/configure_measurement.py <run-dir> \
  --engine actual-engine \
  --context-mode external-search-augmented \
  --profile release \
  --repeat-runs 3 \
  --fresh-context \
  --context-isolation programmatic \
  --query-variant-mode semantic-retrieval-variants \
  --page-collection-status not-collected \
  --observation-date 2026-09-10
```

脚本同时写 `run_metadata.json` 与 `measurement_config.json`。

### Context mode

- `native`：模型原生回答；
- `engine-native-search`：AI 产品自身联网/搜索；
- `external-search-augmented`：外部 Web Search/RAG 后再交给 LLM。

第三种只能称“外部检索增强下的 AI Answer Visibility”，不能称模型原生 Recall。

### Context isolation

- `api-isolated`
- `product-isolated`
- `programmatic`

`programmatic` 必须填写 `fresh_context_note`，披露同会话残余风险。

### Exact repeat vs semantic variants

- `exact-query-repeat`：同一 canonical query 原样重复；
- `semantic-retrieval-variants`：语义等价检索式变体，用于 Query/Retrieval Robustness。

如果同 Query 被搜索通道强缓存，可以切 semantic variants，但不得继续把它描述为严格同条件随机 repeat。

## Raw Mention 与 Positive Nomination

`ai_mentions.csv` 保留所有原始 Mention。只有：

```text
explicit-name / verified-alias
+ resolved
+ entity_correct=true
+ mention_intent in {recommended, listed}
```

才进入 Nomination Rate。

Intent 锚定原则：

- 明确否定/排除 → `excluded`
- 明确条件性弱推荐/降低优先级 → `caveat`
- 明确推荐/优先 → `recommended`
- 正常进入候选/榜单且未否定 → `listed`
- 仅作参照 → `comparison`

**榜单成员附带普通缺点仍然是 listed**。例如“第二名华图，线下体系成熟，但价格偏高”不能仅因“价格偏高”降为 caveat。

完整正例/反例见 `references/data-schema.md`。

## 可复现 Annotation Pipeline

如果已有 `mentions_raw.json`：

```bash
python3 scripts/prepare_annotation_tasks.py <run-dir>
# Reviewer 根据 references/data-schema.md 给 annotation_labels.csv 打语义标签
python3 scripts/apply_annotation_labels.py <run-dir>
```

`apply_annotation_labels.py` 自动派生 `nomination_rank / top3 / first_mention`，避免人工顺序漂移。`resolution_status` 从上游实体解析冻结，Annotation Reviewer 不重新猜实体工商/解析状态。

Release 模式的 Annotation Blind Recheck 与 Resolution Audit 分开：

- `annotation_rechecks.csv`：只看 Mention/Intent/Positive Set/顺序；
- `resolution_rechecks.csv`：单独检查 canonical mapping 与 resolved/unresolved。

## AI Metrics

```bash
python3 scripts/compute_ai_metrics.py <run-dir>
```

`ai_metrics.csv` 一行 = `entity_id × measurement_target`。Hybrid `both` 必须分别产生 institution 与 ip 两行，分母不能混合。

透明指标：Raw Mention Rate、Nomination Rate、Top3 Rate、First Mention Rate、Citation Rate、Engine Coverage Rate、Cross-model Consistency。单引擎时 Cross-model Consistency 必须 N.A.。

## Robustness

```bash
python3 scripts/compute_variant_robustness.py <run-dir>
```

正式产出：

- `variant_robustness.csv`
- `query_set_similarity.csv`
- `robustness_summary.json`

旧式“只看至少命中过一次的 entity×query 中有多少 3/3”的指标改名为：

`positive_persistence_3of3_rate`

它**不是 Overall Repeat Stability**。同时必须看 0/N、1/N、2/N、N/N Hit Pattern、Pairwise Positive-set Jaccard、Exact Set Match。

如果 Run 使用 semantic variants，这些只能解释为 Query/Retrieval Robustness。

## Open-Web 与 Page Layer

- `serp_results.csv`：真实 Result Item；
- `serp_mentions.csv`：只允许 title/snippet；
- `page_mentions.csv`：打开正文后的提及。

`page_collection_status=not-collected` 时空表表示“未采集”，不是“正文 0 提及”。Stage 3 Asset Audit 前应补 Page Collection 或明确披露。

## Validator

```bash
python3 scripts/validate_run.py <run-dir> --stage universe --strict
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

Release Validator 检查 target-specific denominator、query variant、context isolation disclosure、Annotation Recheck、robustness artifacts 等，但在广东/天津/山东多地区与多引擎校准前，不把 30%/80% 等经验值硬编码成永久理论门槛。

## Report Contract

唯一正式交付：`deliverables/report.docx`。Stage 1 A/B/C/D 分桶被冻结；`build_report_model.py` 和 `generate_charts.py` 不得再通过 entity_type 重分组。Hybrid 的两套 target metrics 可同时保留，但不能反向修改 Market Role。

数据低稳定或单引擎时，只能写“在本次协议下提名率最高/未形成正向召回”，禁止写“真实第一”“所有 AI 都不认识”“所有模型都不会推荐”。

## 依赖与测试

核心研究/校验仅需 Python 标准库。Word 需要 `python-docx`，图表需要 `matplotlib`。

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

第三方依赖缺失时 DOCX/图表集成测试可以 SKIP，但核心协议测试不能崩溃。

## 发布纪律

Synthetic Test 全绿不能直接发布。正式 v2.2 仍需完成广东、天津、山东真实地区回归。Golden Reality Fixture 只能在盲跑后做后验漏召回检查，生产逻辑不得读取、注入 Candidate 或加分。

GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。
