---
name: acs-gongkao-geo-research
description: 调查中国公务员及公职考试培训机构、品牌和老师/IP 在生成式搜索与 AI 搜索中的可见性。v2.1.1 在 v2.1 的三步 Preflight、Semantic Coverage、机构/IP Measurement、五维 GEO Score 与正式咨询报告基础上，新增 Local Ecosystem Completeness Gate、本土机构与平台原生 IP 召回、观察组不消失、Report Model 完整性、响应式 HTML 与四层验收。不得用来评价教学质量、上岸率、市场份额或一般口碑。
metadata:
  version: "2.1.1"
---

# 公考机构 GEO 调研 v2.1.1

版本定位：**Stability + Recall Completeness + Report Contract Patch**。

v2.1.1 不改 v2.1 的五维评分权重，也不为了任何已知机构/IP 调分。它修复三类问题：工程稳定性、复杂地区候选召回完整性、Report Model / Renderer 完整性与版式稳定性。详细补丁说明见 [v2.1.1-stability.md](references/v2.1.1-stability.md)。

GEO 观察的是机构、品牌、老师/IP 在公开信息环境中被**发现、正确识别、无品牌召回、引用、概念绑定**的能力。它不是教学质量、通过率、市场份额、经营规模或真实口碑排名。

## 0. 三步 Preflight 是唯一启动入口

完整 Research Run 前只确认尚未明确的三项：

1. `requested_region`：省、市或自定义区域；
2. `requested_entities`：是否有指定关注机构、品牌、老师/IP；可以明确“不指定”；
3. `requested_output_format`：`docx|pdf|html`，默认一次任务只正式生成用户选择的格式。

用户已经给出的参数不得重复机械询问。新 Run 应使用：

```bash
python3 scripts/preflight.py --region 广东 --no-specified-entities --format html --output <run-dir>/run_metadata.json
```

并写入：

```text
schema_version = 2.1.1
skill_version  = 2.1.1
```

Preflight 只建立研究配置，不能把三道 Freeze Gate 预先写成 true。

### 指定主体规则

指定关注只解决 Candidate Recall：

- 强制进入 Candidate / Entity Resolution 流程；
- 不加分、不自动进正式排名、不提高 Evidence Grade / Confidence；
- 最终不能静默消失；机构至少落在 `scored|evidence-insufficient|unresolved|merged`，老师/IP 可落在 `ip-measured`。

## 1. 研究模式

| 模式 | 说明 |
| --- | --- |
| `regional-landscape` | 地区全景；自动发现整个地区候选，必须过三道 Freeze Gate |
| `institution-deep-dive` | 单主体深挖；不自动扩张无关名单 |
| `institution-comparison` | 指定主体比较；点名只保证调查，不加分 |
| `gap-analysis` | 从真实弱召回、无结果、实体歧义与概念断层形成机会图 |

## 2. v2.1.1 Research Engine

```text
Preflight
↓
Region / Exam Ecology
↓
Six-route Candidate Discovery
↓
Local Ecosystem Recall Audit
↓
Entity Resolution
↓
Semantic Coverage Audit
↓
Semantic Coverage Gate
+ Saturation Gate
+ Local Ecosystem Completeness Gate
↓
Candidate Pool Freeze
↓
Institution Measurement + IP Measurement
↓
Verification + Evidence Audit
↓
Fixed Five-Dimension Scoring
↓
Strategy Analysis
↓
Shared Report Model
↓
Selected Renderer
↓
Research Validation
→ Report Model Validation
→ Renderer Validation
→ Visual QA
```

## 3. Discovery / Measurement / Verification 必须隔离

- `discovery`：找候选、别名、关系；不计 Recall；
- `measurement`：统一无品牌问题实测；只有合法 Measurement 可计 Recall；
- `verification`：核验官网、公司、账号、老师、产品、关系、第三方来源；不计 Recall。

机构 Measurement：

```text
query_type=generic
query_purpose=measurement
measurement_target=institution
status=sampled
```

IP Measurement：

```text
query_type=generic
query_purpose=measurement
measurement_target=ip
status=sampled
```

Discovery / Verification 即使命中品牌，也不得写 `counts_as_measurement_hit=true`。

## 4. 六路 Discovery 保留，但不能当作“已找全”

六路：

1. `user-query`
2. `exam-vertical`
3. `institutional`
4. `platform`
5. `expert-ip`
6. `entity-alias`

所有 Discovery 仍需写入 `discovery_coverage.csv`，记录 `semantic_theme`、query_count、result_count、eligible_candidates_found、status。

## 5. Local Ecosystem Recall Audit（v2.1.1 新增）

地区全景 Candidate Freeze 前必须额外覆盖三组机器可检主题：

```text
local-institution-ecosystem
local-expert-ip
platform-native-ip
```

### local-institution-ecosystem

寻找本土机构、工作室、基地班、地市型品牌、老师型机构。Query 动态组合地区、主要城市、主要考试垂类、课程/服务场景。禁止把任何已知机构名单写进生产规则。

### local-expert-ip

从“概念/服务 → 人”反向找老师和 IP。按当地实际生态覆盖申论、行测、面试、选岗、公考规划、事业单位、选调等，不能只跑一个“老师推荐”总词。

### platform-native-ip

专门寻找先在平台形成影响力、再关联机构/概念的 Expert Entity。根据公开可访问情况覆盖抖音、视频号、B站、小红书、知乎、微博等；平台不可访问时记录限制或 `no-result-reviewed`，不得伪造结果。

## 6. Candidate Freeze 从双门禁升级为三门禁

地区全景只有以下三者全部通过才能 `candidate_pool_frozen=true`：

### Gate A — Semantic Coverage

所有 `required=true` 的关键语义主题达到 `covered|no-result-reviewed`，且真实有查询。

### Gate B — Saturation

默认满足任一：最近一轮新增率 `<10%`；或新增可评估主体 `<=1`；或连续两轮无重要新增。

### Gate C — Local Ecosystem Completeness

三组 `local-* / platform-native-*` 语义均真实执行并复核，且 `run_metadata.local_ecosystem_gate=true`。

此外：

- Discovery 已解析出的 `entity_id` 必须进入 Candidate Pool；
- 同一未解析名称若在至少两个独立来源域重复出现，必须进入 Candidate / Entity Resolution，不能直接丢弃。

## 7. Candidate 状态与“绝不静默消失”

机构/品牌：

- `scored`
- `evidence-insufficient`
- `unresolved`
- `merged`
- `excluded`

老师/IP 增加：

- `ip-measured`：进入独立 IP Measurement，但不进入机构五维总榜。

凡 `evidence-insufficient|unresolved`，正式报告必须进入“本土候选观察组”，说明谁没进榜、为什么没进榜、缺什么。不能只显示“13 家证据不足”而不列名字。

## 8. Evidence 与派生字段所有权

Evidence 继续执行 A1/A2/B/C、独立来源、claim type、counting scope 与去重规则。

v2.1.1 明确：

- `generic_hits/generic_queries/brand_hits`：由 Query Log 派生；
- `evidence_count`：由 `evidence.csv` 按 entity_id 自动派生，`counting_scope=ignored` 不计；
- `independent_domains`：由独立 Evidence 的真实域名派生。

执行者不应手工补这些数。使用：

```bash
python3 scripts/score_geo.py score_input.json --run-dir <run-dir> --pretty
```

## 9. 五维 GEO Score 保持不变

- Query Coverage /30
- Entity Clarity /25
- External Diversity /20
- Concept Ownership /15
- Freshness /10

不引入“本土品牌加分”“用户指定加分”“粉丝量加分”。

自有域名依赖暂不改总分，只新增解释指标：

- `Owned Source Dependency Ratio`
- `Evidence Authority Index`

是否把自有来源依赖纳入评分，必须放到后续方法论版本单独回归。

## 10. IP Measurement 是独立报告对象

只要执行了 sampled `measurement_target=ip`：

- `ip_entities.csv` 必须记录 IP 实体；
- `report_model.json.ip_measurement.executed=true`；
- IP 表必须至少展示：IP/老师、关联机构、hits/queries、Recall、科目/概念、平台、Evidence Confidence；
- HTML/DOCX/PDF 都必须真正渲染数据，不能只写“本次已执行 IP Measurement”。

如果没有真实 IP Measurement，只能写 Expert Entity / 可见性观察，不得写 IP GEO 排名。

## 11. public-web-proxy 方法论边界

`sampling_mode=public-web-proxy` 是公开网页代理观察，**不等价于所有大模型/AI 搜索产品在所有时点的真实回答**。它会受 SEO 站群、聚合站、自有站矩阵、索引差异、登录墙、动态网页、平台访问限制影响。

并行 Agent/采样员执行 Measurement 时：

- 使用统一“命中”定义；
- 随机抽取至少 20% Measurement Query 由第二采样员复判；
- 争议结果回到原始结果上下文，不能按印象决定。

## 12. Report Model 是强契约

`report_model.json` 至少必须有：

```text
meta
kpis
ranking
scorecards
observation_group
ip_measurement
query_occupancy
charts
appendix
```

`appendix` 至少消费：

- `candidate_status`
- `research_assets`
- `research_audit`
- Evidence Index

`competition_route` 为空/待归纳时，由 `build_report_model.py` 根据 Recall、Authority、总分、自有来源依赖自动归纳；`strongest_asset/largest_gap` 从 `score_details.json` 自动归纳，禁止整表保留占位文案。

## 13. HTML 设计规则

HTML 是浏览器产品，A4 只属于打印模式。

屏幕端必须：

- `main` 使用 `max-width` 响应式；
- SVG `width/max-width:100%; height:auto`；
- 宽表放入 `overflow-x:auto`；
- Scorecard 使用“紧凑排名表 + 机构诊断卡”；
- Authority × Recall 做标签避碰/引导线。

只有 `@media print` 使用 A4 页边距和分页。

## 14. Renderer 纪律

用户选什么正式格式，就只正式生成什么：

```text
Word → deliverables/report.docx
PDF  → deliverables/report.pdf
HTML → deliverables/report.html
```

三套 Renderer 使用同一个 Report Model，并必须包含：正式排名、本土候选观察组、IP / Expert GEO、Query 占位、策略区、Appendix / Research Audit。

## 15. 四层验收

不能再只用“CSV 一致”代表报告完成：

1. **Research Validation**：Preflight、Query、Entity、Evidence、Score、三道 Freeze Gate；
2. **Report Model Validation**：IP、观察组、Appendix、KPI、Chart Data 完整；
3. **Renderer Validation**：所选格式确实消费关键区块；
4. **Visual QA**：HTML 无横向溢出/错位；Word/PDF 无裁切、重叠、坏分页。

```bash
python3 scripts/validate_run.py <run-dir> --strict
```

自动验证不替代视觉检查。

## 16. 文件系统稳定性

Chart / Renderer 统一使用 `scripts/fs_utils.py::ensure_directory()`：路径不存在则创建，已存在目录则继续，已存在非目录或不可写则明确报错，并对短暂并发竞争做有限重试。

## 17. 回归测试

每次修改至少运行：

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v211.py
```

回归覆盖派生 evidence_count、预建输出目录、Local Ecosystem Gate、重复本土主体不得消失、IP 数据进入 Report Model、观察组披露、自动商业归纳、HTML 响应式契约、DOCX/PDF/HTML Renderer，以及广东/山东等非天津地区归一化。

fixture 只用于验证规则，不能冒充真实地区 Measurement。

## 18. 最终研究汇报

完成一次地区研究至少说明：

- 地区与研究模式；
- Candidate 数 / 正式评分数 / 观察组数；
- 三道 Freeze Gate 结果；
- 机构 / IP Measurement 数；
- 指定主体最终状态；
- 平台访问限制；
- 正式输出格式；
- Research / Report Model / Renderer / Visual QA 四层验收结果；
- 明确声明 GEO 不代表教学质量、市场份额或上岸率。
