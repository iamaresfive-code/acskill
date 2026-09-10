# acs-gongkao-geo-research v2.2

> 公考行业 GEO 竞争研究 Skill：先确认“研究谁”，再测“AI 到底提不提”，最后用公开资产解释原因。

如果你第一次接触 GEO，可以先把它理解成：

**研究一家公考机构、品牌或老师/IP，在用户没有输入其名字时，是否会被 AI 自然提名；如果会，为什么会；如果不会，缺的是什么。**

v2.2 不再把“搜索引擎能找到很多页面”直接等同于“AI GEO 强”。

## 为什么 v2.2 要重构

v2.1/v2.1.1 的工程稳定性提高了，但真实地区回归暴露了一个更根本的问题：如果先盲搜一个省份，再让公开网页搜索决定 Candidate Universe，SEO 榜单型全国品牌会被系统性放大，而本土强招生、强私域、强短视频/视频号、强老师 IP 的主体可能被低估或漏掉。

因此 v2.2 改成三层：

1. **Market Universe**：这个地区真正值得研究的主体是谁；
2. **AI Answer Measurement**：固定无品牌问题下，AI 实际提到了谁；
3. **GEO Asset Readiness**：公开网页、平台、第三方证据、地域语义等资产，解释 AI 为什么可能认识它。

## 第一次使用只确认三件事

### 1. 调查哪里？

例如：广东省、天津市、广州市、珠三角。

### 2. 你希望一定覆盖哪些机构 / 品牌 / 老师 IP？

这叫 **Seed List（种子主体）**。不要求完整，可以只列最关心的一批。

Seed 的意义只有一个：**保证研究和实体解析，不保证自动 included，更不保证高分。**

Seed 初始应为 `unresolved / needs-review`；完成 Rescue 后，才决定 included / observation / unresolved。它不会自动增加提名率、Top3率、资产分或证据等级。

如果用户明确说“我没有名单，你自己发现”，系统切换为 `blind-discovery-scan`。这种模式只能叫“公开网络发现扫描”，不能直接包装成地区真实竞争全景。

### 3. 是否允许系统补充竞争主体？

默认建议允许。最终 Universe = 用户 Seed + 系统补充。

**输出格式不再询问：v2.2 唯一正式交付是 Word（`report.docx`）。**

## 最重要的新步骤：Market Universe Confirmation

系统完成补充 Discovery 后，不允许马上跑 Measurement。

必须先给用户看一版拟研究清单，至少分成：

- 全国基准品牌；
- 本地 / 区域机构；
- Expert / IP；
- Observation / Historical / Unresolved。

`universe_review.json` 必须由 Skill 脚本生成/刷新，不应由执行者另写一套分桶格式：

```bash
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
```

Stage 1 校验只检查 Preflight、Market Universe 与 Review Contract，不会因为 AI/Report 文件尚未生成而制造几十个预期错误。

用户确认后，才执行：

```bash
python3 scripts/confirm_market_universe.py <run-dir> --approved-by user
```

该脚本写入：

```text
market_universe_confirmed = true
measurement_allowed = true
```

它只确认当前研究合同，不发现主体、不打分、不改变任何 AI Measurement 结果。

## Seed 与 Discovery 同名时怎么处理

v2.2 采用字段级合并：

- 始终保留 `user_seed=true`；
- Discovery 的 aliases / market_scope / market_role / salience_basis / notes 等非空信息，可以回填 Seed 的空字段；
- 不再因为 Seed 先进入表而静默丢掉后续 Discovery 证据。

## National Benchmark 不是“所有全国连锁”

正式 Word 报告仍分全国与本地，但 `national-benchmark` 只是一组**代表性可比基准**，不是“只要在本地有地址就进入”。

默认建议约 4–6 个全国公考品牌。超过 8 个需要解释每一家为什么都具有当前、明确的“地区 × 公考”业务相关性。

仅有本地职业培训分校、办公地址或泛职业教育业务，不足以证明当前本地公考业务足够强；这类全国品牌可以留在 Observation，等待真实 AI Answer 是否主动提名。

## Platform-native IP 不能因一条本地内容自动进主榜

非 User Seed 的 IP，需要持续的 `Region × Public Exam` 主题绑定，或明确教学/咨询服务、跨平台稳定身份、机构师资身份、独立 Authority 等信号。

单条视频、单期播客、一次“广东上岸经历”默认只进 Observation，不能因为含地区关键词就直接进入 Expert/IP 主榜。

## AI Answer Measurement 才是核心 GEO

固定无品牌问题，在可用的 AI / AI Search 引擎上保存原始回答，然后计算：

- Nomination Rate：提名率；
- Top3 Rate：进入前三的比例；
- First Mention Rate：首提率；
- Citation Rate：被提及时有实体关联引用的比例；
- Cross-model Consistency：跨模型一致性。

如果环境只能测一个模型，要明确写 `single-engine`；如果完全无法做 AI Answer Measurement，只能输出 Asset Audit，不能叫真实 AI GEO 排名。

完成原始 Measurement 后，可以先执行：

```bash
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
```

## 公开网页测量的角色变了

公开 Web 仍然重要，但它是**解释层**。

v2.2 把真实搜索结果拆成：

- `serp_results.csv`：每个 Query 的真实 Result Item；
- `serp_mentions.csv`：只允许标题 / 摘要中显式出现的主体；
- `page_mentions.csv`：打开网页正文后发现的品牌提及。

**Page Mention 永远不能冒充 Query / AI Measurement Hit。**

因此，一篇“十大机构”文章正文写了 12 家，只能产生 Page Mention，不能让 12 家都获得一次搜索召回。

## 20% Blind Recheck

AI Answer Measurement 至少随机抽 20% answer cells，由第二采样者独立复判，不先看第一次结果。

分歧必须写入 `rechecks.csv` 并给出 resolution。这样多人并行采样时，口径漂移能够被发现。

## GEO Asset Readiness

v2.2 不再把公开网页代理分数称为“最终 GEO 总分”。它只解释基础设施成熟度，100 分由以下维度组成：

- Entity Clarity /25
- Regional Semantic Density /20
- Open-Web Assets /15
- External Authority /15
- Content Depth & Freshness /10
- Data / Tool Assets /10
- Platform Coverage /5

同时单列 `Owned Source Dependency`，只作解释指标，不因某个地区或品牌临时改分。

## Word-only 报告

v2.2 删除正式 HTML / PDF Renderer，只维护一个 A4 DOCX 报告产品：

```text
Research Data
→ report_model.json
→ generate_report_docx.py
→ Visual QA
→ deliverables/report.docx
```

这样可以稳定控制：页面、字体、表格宽度、分页、诊断卡、图表最大宽度和 Appendix。

## 核心运行顺序

```bash
python3 scripts/preflight.py ...
python3 scripts/build_market_universe.py <run-dir>
# Agent 完成/补齐 Entity Resolution + Market Salience Review 后：
python3 scripts/refresh_universe_review.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage universe --strict
# 用户确认后：
python3 scripts/confirm_market_universe.py <run-dir> --approved-by user
# 只有确认后才允许正式 AI Measurement
python3 scripts/compute_ai_metrics.py <run-dir>
python3 scripts/score_assets.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage measurement --strict
python3 scripts/generate_charts.py <run-dir>
python3 scripts/build_report_model.py <run-dir>
python3 scripts/generate_report_docx.py <run-dir>
python3 scripts/validate_run.py <run-dir> --stage report --strict
```

## 依赖

核心研究、数据校验、AI Metrics：Python 标准库即可。

Word：

```bash
pip install python-docx
```

图表：

```bash
pip install matplotlib
```

图表脚本会优先使用系统中可用的中文字体；macOS 建议存在 PingFang SC，Windows 可使用 Microsoft YaHei，Linux 建议安装 Noto Sans CJK。

## 测试

```bash
python -m py_compile scripts/*.py
python scripts/test_v22.py
```

缺少 Word / 图表第三方依赖时，相应集成测试可 `SKIP`，但核心研究协议测试仍必须运行；发布说明必须列出被跳过项。

## 发布前真实回归

v2.2 不允许只看 Synthetic Test 全绿就发布。至少做：

1. Synthetic Test；
2. 广东 / 天津 / 山东真实地区回归；
3. 盲跑结束后再做 Golden Reality Check。

Golden Fixture **只能用于发布后验检查，生产逻辑不得读取、不得注入 Candidate、不得加分。**

广东回归另外固定维护 `tests/fixtures/guangdong-v22-measurement-queries.json`：20 条机构问题 + 8 条 Expert/IP 问题，全部无品牌词。同一版本比较时不得因已知结果临时改题。

历史文档状态请先看 `references/README.md`；v2.2 执行不得引用其中标记为 legacy/deprecated 的旧协议作为当前规范。
