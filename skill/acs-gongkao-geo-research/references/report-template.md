# 公考 GEO 正式咨询报告模板 v2.1

Main Report 的职责是让管理者快速理解市场格局、竞争路线、机会与动作；Research Audit 后置 Appendix。

## P1 封面

```text
2026 {region}公考
GEO 竞争格局深度报告

生成式搜索环境下的
品牌可见性 · 实体资产 · 答案占位 · 竞争机会

研究范围：{scope}
观察日期：{YYYY.MM.DD}
研究性质：公开互联网 GEO 竞争情报
内部用途：竞争监测 / 区域进入 / 品牌 GEO / 内容资产规划

INTERNAL RESEARCH
```

不出现 Schema、CSV、内部状态码。

## P2 研究概览 / KPI Cards

建议四张卡：

- 独立机构候选
- 正式评分机构
- Institution Measurement Query
- 可复核 Evidence

可加第二行：IP Entity、Semantic Theme、可评估机构、Observation Window。全部来自本 Run。

## P3 Executive Summary

先写一句话结论，再写 5–7 个关键判断。每个判断按：

```text
现象 → 原因 → 经营含义
```

优先回答市场格局、谁在赢、哪些本土机构值得重视、哪些主体高权威低召回、哪些主体偏主动铺量、最大 GEO 空位、新进入者最值得做什么。不要先讲研究流程。

## P4 GEO 综合排名与市场格局

必须嵌入 `geo-score-ranking.svg`。低置信度或 60 分以下不强调 1–2 分精确差距。

## P5 Authority × Recall

必须嵌入 `authority-recall-matrix.svg`。四象限：成熟占位型、高权威低召回型、主动铺量型、基础薄弱型。

## P6 Candidate Coverage / 调研完整性

用 `candidate-funnel.svg` 或等价可视化，不在 Main Report 放巨大状态表。必须区分候选记录、独立机构候选、实体图谱节点、具备评估条件、正式评分、IP Entity。

## P7 研究口径与评分体系

用一页简洁解释：GEO 不是教学排名；Discovery / Measurement / Verification 分工；五维 30/25/20/15/10；Evidence Grade；Observation Snapshot。后台字段和 Schema 细节留 Appendix。

## P8–P9 GEO Scorecard

Main Report 表格建议：

| 排名 | 主体 | GEO指数 | Tier | 竞争路线 | 最强资产 | 最大短板 |
| --- | --- | ---: | --- | --- | --- | --- |

最多 7 列。完整五维表放 Appendix。建议嵌入 `dimension-heatmap.svg`。

## P10–P14 重点机构诊断

每家公司统一诊断卡：

```text
机构名称
GEO Score / Tier
Route
Recall
Authority
Confidence

【为什么被看见】
【为什么被相信】
【概念占位】
【当前最大短板】
【最值得做的3个动作】
【核心 Evidence】
```

每页 1–2 家。用户指定主体使用低干扰标识：`用户指定关注`，不改变排序和视觉高亮等级。证据不足则标 `用户指定关注 | 证据不足，未进入正式排名`。

## P15 IP / Expert GEO

如果实际执行 IP Measurement：可写“IP / Expert GEO”。否则标题必须写“IP实体 / 专家可见性观察”。人物不与机构混排。

## P16–P17 固定 Query 占位

把 Measurement Matrix 转译成：

| Query | 当前强势主体 | 竞争强度 | Evidence Health | 机会判断 |
| --- | --- | --- | --- | --- |

重点展示高商业价值、强竞争、高空位、默认答案、同名污染、高权威低召回。完整 Query Results 放 Appendix。

## P18–P19 概念山头 / Gap Map

输出：

| 概念 / 问题 | 当前较强主体 | 成熟度 | Evidence Health | 机会等级 | 建议进入方式 |
| --- | --- | --- | --- | --- | --- |

只根据本次真实 Run 识别，不写死任何地区案例。

## P20 竞争路线

| 路线 | 代表主体 | 运行机制 | 优势 | 典型短板 |
| --- | --- | --- | --- | --- |

路线标签由本次资产结构归纳，不参与分数。

## P21 区域进入策略

必须回答：哪些红海不要正面打、哪些 Gap 先抢、先做品牌还是知识、先做什么实体、先做哪个考试细分、如何建立第三方 Evidence、如何建立 Expert Entity。

## P22–P23 90 天 GEO 内容与知识资产工程

按 0–30 天、31–60 天、61–90 天、持续四阶段写目标、核心动作、为什么有效、验收指标。必须与本次 Gap 强关联，不生成泛 SEO 建议。

## P24 月度 GEO 监测看板

建议核心模块包括实体识别、固定 Query、知识资产、第三方引用、概念绑定、竞品动态、质量风险、转化连接。核心指标优先无品牌召回率、首提率、引用率、正确实体率、可引用 Evidence、权威页面数、概念绑定稳定度、错误信息率；“文章数量”不作为核心 KPI。

## P25+ Appendix

建议：A. 完整五维评分表；B. Candidate Coverage Audit；C. Discovery Semantic Coverage；D. Entity / Alias / Legal Entity；E. IP实体关系；F. 完整 Query + Result；G. Evidence Grade；H. Evidence Index；I. Research Boundary / Schema / Version。

Appendix 中保留机器审计字段：Schema版本、Skill版本、观察日期、研究模式、研究范围、采样模式、Discovery问题数、机构Measurement问题数、IP Measurement问题数、Verification问题数、Discovery Semantic Theme数、候选记录数、独立机构候选、实体图谱节点、具备评估条件、正式评分、IP实体、证据数及各 Candidate Status 数量。
