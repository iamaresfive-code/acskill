# acs-gongkao-geo-research v2.2.1

> 公考行业 GEO 竞争研究 Skill：先确认研究谁，再测 AI 到底提不提，最后用公开资产解释原因。

正式交付固定为**简体中文 Word 报告**：`deliverables/report.docx`。

> v2.2.1 是 v2.2 的首次运行与客户报告体验补丁。数据 schema 仍为 `2.2`，不改变 GEO 测量定义、评分权重或历史 v2.2 原始采样证据。

## 这次补丁解决什么

v2.2.1 主要修复 Fresh Run 暴露出的四类问题：

1. **首次运行次序**：Stage 1 做 Measurement Target Audit 时，尚未产生 `ai_emergent_entities.csv` 属正常状态，不再因此死锁；正式测量后如果出现新的已解析主体，再做第二轮 Target Audit 收口。
2. **市场发现证据**：新建研究主体池时，每个准备进入正式研究的主体必须至少保留 1 条可独立核验的公开来源 URL。
3. **引用率语义**：如果原始 AI 回答环境没有 citations，客户报告显示“引用率：不适用”，而不是 0%。
4. **客户报告产品化**：正式 DOCX 默认全中文，只展示结论、排名、稳定性、资产基础、概念占位、主体诊断和行动建议；内部字段、CSV/JSON/Python 文件名和审计明细留在 Run 底稿中。

## 核心研究结构

1. **研究主体池**：User Seed + 系统发现 + 市场显著性审核；
2. **AI 回答测量**：固定无品牌问题的真实采样；
3. **GEO 资产基础**：用公开互联网资产解释 AI 为什么更容易认识、理解和引用某个主体；
4. **概念占位**：识别机构 / 老师已经和哪些区域考试概念形成稳定公开绑定。

Market Bucket 与 Measurement Target 仍是两条独立轴：

```text
measurement_target = institution | ip | both
```

`both` 产生 institution / ip 两套 Metrics，分母不混合，也不能反向改变 Stage 1 已确认的市场分桶。

## 第一次运行

### 1. 先确认三项输入

- 地区；
- 用户一定要覆盖的机构 / 品牌 / 老师 IP Seed List；
- 是否允许系统补充竞争主体。

Seed 只保证研究与解析，不加分。

### 2. 建研究主体池并留存来源

系统发现的候选主体需要保留公开来源。v2.2.1 新建的 `market_universe.csv` 增加：

```text
discovery_evidence_urls
```

准备进入正式研究的主体至少需要 1 条可核验来源 URL。缺来源时继续补证据或留在观察状态，不为了凑榜强行确认。

### 3. 第一轮 Target Audit

```bash
python3 scripts/prepare_measurement_target_audit.py <run-dir>
# Reviewer 填 new_explicit_target / evidence_basis / reviewer_reason / confirmed
python3 scripts/apply_measurement_target_audit.py <run-dir>
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

此时还没有 `ai_emergent_entities.csv` 是正常的。Stage 1 apply 会把它视为空集合，不会创建伪造的空文件。

### 4. 用户确认主体池后开始正式测量

实际探测可用 AI / AI Search 引擎后再配置 Measurement。禁止虚构第二模型。

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
  --observation-date YYYY-MM-DD
```

外部检索增强只能解释为该条件下的 AI 回答可见度；语义等价问法只能解释为提问 / 检索鲁棒性。

### 5. Annotation / Resolution / Citation 分链审计

```bash
python3 scripts/prepare_annotation_tasks.py <run-dir>
python3 scripts/apply_annotation_labels.py <run-dir>

python3 scripts/prepare_citation_audit.py <run-dir>
python3 scripts/apply_citation_audit.py <run-dir>
```

只有 explicit-name / verified-alias + resolved + entity_correct + recommended / listed 才进入正式 Nomination。

如果正式测量后出现新的已解析 AI-emergent 主体，再运行第二轮 Target Audit，确保这些主体也有明确 institution / ip / both target。

## Metrics 与稳定性

```bash
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/compute_variant_robustness.py <run-dir>
```

内部数据保留完整指标，包括 Raw Mention、Nomination、Top3、First Mention、Citation、Engine Coverage、Cross-model Consistency，以及变体稳定性指标。

正式客户报告会把这些翻译成中文，例如：

- 提名率；
- 前三出现率；
- 首提率；
- 三种问法持续命中率；
- 不同问法推荐名单平均重合度；
- 推荐名单完全一致率。

## 中文客户报告

客户 DOCX 是咨询交付物，不是工程日志。

正文主要包含：

1. 核心结论；
2. 竞争格局总览；
3. 全国品牌 AI 可见度；
4. 本地 / 区域机构 AI 可见度；
5. 老师 / IP AI 可见度；
6. 结果稳定性；
7. 概念占位；
8. GEO 资产基础；
9. 观察主体与新出现竞争者；
10. 重点主体诊断；
11. 区域策略与 90 天行动；
12. 必要的方法边界和主体清单。

默认不向客户展示：

- 内部字段和 enum；
- CSV / JSON / Python 文件名；
- Validator 错误码；
- Run 文件清单；
- Python dict / JSON 原始对象；
- Annotation / Resolution / Citation 的逐行审计明细。

完整规则见 [`references/customer-report-contract.md`](references/customer-report-contract.md)。

## 图表原则

- 中文标题、中文主体名、柱尾直接标数值；
- 概念占位使用 Top N 条形图，不使用高度稀疏的热力图；
- 公开证据不足的主体不画成 0 分；
- 使用“AI 可见度 × GEO 资产基础”二维矩阵辅助判断机会区；
- 内部 market_role / bucket 不直接作为客户图例。

## Report Layer 流程

```bash
python3 scripts/score_assets.py <run-dir>
python3 scripts/generate_charts.py <run-dir>
python3 scripts/build_report_model.py <run-dir>
python3 scripts/generate_report_docx.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage report --strict
python3 scripts/qa_report_docx.py <run-dir>
```

三条硬约束不变：

1. 没有证据 ≠ 0 分；证据不足在客户报告中写“暂不评分”；
2. 资产评分与概念绑定必须能追到公开证据；
3. 空壳报告、内部字段泄漏、工程文件名、原始 Python/JSON 对象都不得通过客户报告 QA。

## 测试

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v22.py
```

总测试入口会串起：

- v2.2 核心回归；
- Target Closure；
- Report Layer / 中文客户报告；
- Empty-Audit Gate；
- v2.2.1 Fresh Run 补丁回归。

只有真正缺少 `matplotlib` / `python-docx` 等依赖时，集成测试才允许明确 SKIP；实际 Assertion / Validator / Runtime failure 不能伪装成 SKIP。

## 解释边界

报告中禁止把单引擎、检索增强或低稳定性结果写成“真实第一”“所有 AI 都不认识”“GEO 为零”。

GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。

详细数据合同见 [`references/data-schema.md`](references/data-schema.md)，客户报告契约见 [`references/customer-report-contract.md`](references/customer-report-contract.md)，旧 Run 迁移见 [`references/migration-v2.2.md`](references/migration-v2.2.md)。
