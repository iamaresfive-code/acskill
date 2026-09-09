# acs-gongkao-geo-research v2.1

> 公考行业 GEO 竞争研究与咨询报告 Skill

如果你第一次接触 GEO，可以先把它理解成：

**调查一家公考机构、老师或品牌，在 AI 搜索与生成式搜索环境里，是否容易被找到、能否被机器正确理解、有没有稳定的公开证据、在用户不输入品牌名时会不会自然被召回。**

它不是“教学质量排行榜”，也不是“谁家上岸率最高”。

## 这个 Skill 解决什么问题

公考行业里常见的问题是：

- 大机构大家都知道，但 AI 在当地问题下到底会不会提到？
- 本土机构有没有真实可被机器理解的品牌、公司、老师、课程、地区关系？
- 某个老师很有影响力，这种影响力有没有形成可被 AI 识别的 Expert Entity？
- 一家机构网上文章很多，到底是自然引用多，还是自己铺量多？
- 一个新品牌进入广东、天津、山东等市场，哪些 GEO 山头已经被占，哪些问题还没有稳定答案？

v2.1 的目标，是把这些问题做成一套可复核的研究流程，同时把最终成品做成真正能拿去内部讨论的行业研究 / 战略咨询报告。

## 第一次使用，只需要回答三个问题

Skill 启动时不会先给你讲 Candidate Pool、Schema、Measurement 这些技术词。

它只确认三件事：

1. **调查哪里？** 例如广东省、天津市、广州市、珠三角。
2. **有没有特别想看的机构、品牌或老师？** 没有也可以，让系统自己发现。
3. **最后要 Word、PDF 还是 HTML？** 一次默认只正式生成你选择的那一种。

例如：

> 做天津公考 GEO，把津仕和北宋也看一下，出 Word。

三个参数都已经明确，系统就不再重复提问。

## “指定机构”是什么意思

指定机构只表示：**这家一定要调查到。**

不表示：

- 一定进排名；
- 自动加分；
- 自动变成高置信度；
- 用户希望它表现好。

如果证据足够，它正常评分；证据不足，它进入“用户指定关注 / 证据不足观察组”；名称都无法确认，就进入“用户指定关注 / 未解析主体”。不会悄悄删掉。

## 为什么 v2.1 要做 Semantic Coverage

v2.0 已经会从六条路线找机构，但后来发现一个关键问题：

**“渠道跑过”不等于“重要语义覆盖过”。**

例如 Institutional Discovery 不能只搜一次“高校 + 公考培训”就算完成。当地如果真实存在国考、事业单位、选调、定向选调、公安警法等生态，就应该分别覆盖相关语义。

所以 v2.1 增加 `discovery_coverage.csv`，记录：

- 哪条 Discovery 渠道；
- 覆盖了哪个考试/业务语义；
- 跑了多少查询；
- 找到多少结果和有效候选；
- 这个主题是否已经覆盖。

这样 Candidate Pool 冻结不再只看“搜索轮数”，而要同时通过：

**Semantic Coverage Gate + Saturation Gate。**

## GEO 分数怎么理解

五维权重延续 v2.0，不因为任何机构改模型：

- 泛词覆盖 30
- 实体清晰 25
- 外部来源多样性 20
- 概念占位 15
- 内容新鲜度 10

总分 100。

这里的“泛词覆盖”只看统一无品牌 Measurement。Discovery 找到你、品牌词搜到你，都不能冒充泛词自然召回。

## 为什么要把“机构 Measurement”和“老师 Measurement”分开

机构和老师不是同一种对象。

一家机构可能品牌实体很强，但老师个人召回弱；也可能某个老师非常强，但机构本身的公开实体关系不完整。

v2.1 因此把两类 Measurement 分开。没有做真正 IP Measurement 的 Run，报告只能叫“IP实体 / 专家可见性观察”，不能写成“IP GEO 排名”。

## 最终报告不再像研究运行日志

v2.1 明确区分：

- **Research Engine**：后台严谨，保留 CSV、JSON、Query、Evidence、Schema；
- **Report Product**：前台给管理者看，先讲结论、格局、机会和动作。

正式地区报告通常包含：

- Executive Summary
- GEO 综合排名图
- Authority × Recall 四象限
- Candidate Discovery 漏斗
- 商业解释型 Scorecard
- 重点机构诊断卡
- IP / Expert GEO
- 固定 Query 占位
- 概念山头 / Gap Map
- 区域进入策略
- 90 天 GEO 内容与知识资产工程
- 月度监测看板
- Appendix 研究审计

## Word / PDF / HTML 为什么只选一个

内部研究会产生很多数据文件，但用户正式交付只按第三步选择。

- 选 Word → 只正式交 `report.docx`
- 选 PDF → 只正式交 `report.pdf`
- 选 HTML → 只正式交 `report.html`

除非你明确说“Word + PDF”或“三种都要”。

这能避免一个任务最后出现一堆用户并不需要下载的中间文件。

## 最常用的说法

你可以直接这样用：

- “做广东公考 GEO，不指定机构，出 PDF。”
- “做天津公考 GEO，把津仕、北宋放进去，出 Word。”
- “深挖一下上岸村 GEO，HTML。”
- “比较甲机构和乙机构在山东的 GEO 表现，出 PDF。”
- “看广东公考 GEO 里还有哪些概念空位。”

## 研究边界

本 Skill 只能根据本次公开可访问的信息和实际采样做判断。它不能保证覆盖：

- 登录墙；
- 微信封闭内容；
- 部分短视频平台；
- 动态网页；
- 搜索引擎个性化结果；
- 所有模型在所有时间点的真实回答。

所以最终报告必须写清观察日期、采样方式、研究范围和证据边界。

## 给开发者 / Agent 的文件

- `SKILL.md`：完整执行协议
- `references/preflight.md`：三步启动规则
- `references/public-exam-query-bank.md`：Discovery / Measurement / Verification 题池
- `references/methodology.md`：研究方法与五维评分
- `references/data-schema.md`：运行目录数据结构
- `references/report-template.md`：咨询报告结构
- `references/report-design-system.md`：A4 报告视觉规范
- `scripts/validate_run.py`：严格门禁
- `scripts/generate_charts.py`：图表
- `scripts/build_report_model.py`：统一 Report Model
- `scripts/generate_report_docx.py` / `generate_report_pdf.py` / `generate_report_html.py`：三类 Renderer
- `scripts/test_v21.py`：v2.1 行为回归
