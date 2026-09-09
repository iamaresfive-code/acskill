# GEO v2.1 Report Design System

目标：正式行业研究 / 战略咨询报告，而不是 Dashboard、Agent 运行日志或花哨营销册。

## 1. 视觉定位

参考气质：券商研究简报、战略咨询报告、行业情报白皮书。

建议：

- 主色：深海军蓝
- 辅色：深灰、浅灰蓝
- 背景：白
- 强调色：克制使用单一蓝色层级

禁止：

- 大面积渐变
- 高饱和多色
- 3D 图表
- 花哨阴影
- 大量 Icon
- Dashboard 产品页风格

## 2. 页面尺寸

- A4 Portrait
- 页边距 18–20mm
- 正文 10.5–11pt
- 行距 1.5–1.65
- 主表不低于 8.5–9pt
- 一级标题 18–22pt
- 二级标题 13–16pt
- 封面标题 28–34pt

一页有效正文尽量控制在 700–900 中文字以内；内容多就分页，不缩字硬塞。

## 3. 封面

只放人类真正需要的信息：

- `{year} {region}公考`
- `GEO 竞争格局深度报告`
- `生成式搜索环境下的品牌可见性 · 实体资产 · 答案占位 · 竞争机会`
- 研究范围
- 观察日期
- 研究性质
- 内部用途
- `INTERNAL RESEARCH`

禁止封面出现：Schema、query_purpose、Candidate Count、CSV 名、内部状态码。

封面必须有明显留白。

## 4. 页面节奏

连续两页纯文本后，应出现至少一个视觉元素：

- Ranking Chart
- Authority × Recall
- Heatmap
- KPI Cards
- Funnel
- Diagnosis Card
- Opportunity Map
- Timeline
- Conclusion Box

避免长时间“文字 → 表格 → 文字 → 表格”。

## 5. 表格

Main Report 尽量 ≤6–7 列。复杂五维评分、完整 Query Result、Evidence Audit 放 Appendix。

不使用 7.5pt 等极小字号塞表。

## 6. 分页

明确 page break：

- 封面单页
- Executive Summary 新页
- Ranking Chart 新页
- Authority × Recall 新页
- 重点机构合理分页
- 90 Day Plan 新页
- Appendix 新页

避免标题孤立页底、表头与数据分离、图像跨页、一页只剩两三行。

## 7. 页眉页脚

除封面：

页眉：

```text
{year} {region}公考 GEO 竞争格局深度报告 | INTERNAL RESEARCH
```

页脚：

```text
公开网络语料审计 · 观察日期 YYYY-MM-DD
```

右下页码。

## 8. 图表

### Ranking

横向条形图，从高到低，显示机构名、总分、Tier。

### Authority × Recall

二维散点图，必须是真实坐标图，不用四行表代替。

### Heatmap

把五维分数换算为统一百分比视觉，展示总分相近但资产结构不同。

### Candidate Funnel

展示研究从候选记录到正式评分的收敛过程。

全部图表必须来自本 Run，禁止历史硬编码。

## 9. 图表注释

Ranking 图下统一注明：

> GEO观察指数衡量公开网络与AI可利用资产结构，不代表教学水平、市场份额或通过率。

## 10. Evidence

Main Report 使用 `[E019]` 等短引用，不塞长 URL。

Appendix 列 Evidence ID、主体、来源标题、发布方、发布日期、Grade、URL。

HTML 和 Word 尽量提供可点击链接；PDF 技术允许时保留点击。
