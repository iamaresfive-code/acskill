# 公考 GEO 查询词库 v2.0

先按当地真实考试生态替换变量，再分别建立 Discovery、Measurement、Verification。不得把示例地区、考试或机构机械复制到其他地区。

## 变量

- `{region}`：省、自治区、直辖市或研究区域。
- `{city}`：重点城市、区县或独立招录城市。
- `{exam}`：当地真实存在的国考、省考、市考、事业单位、选调、遴选等。
- `{interview_type}`：经官方或可靠来源确认的面试形式。
- `{institution}`、`{teacher}`、`{legal_name}`、`{alias}`：待核实体字段。

## Discovery：找对象，不计分

每题填 `query_purpose=discovery`、渠道和轮次。标准地区全景覆盖六渠道。

### 第一轮

| 渠道 | 示例问题 |
| --- | --- |
| user-query | `{region}公考培训机构有哪些`、`{city}公务员培训班`、`{region}公考基地班` |
| exam-vertical | `{region}{exam}笔试培训机构`、`{region}{exam}面试培训老师` |
| institutional | `site:gov.cn {region} 公务员 培训 机构`、`site:edu.cn {region} 公考 讲座 老师` |
| platform | `{region}公考机构 B站`、`{region}公考老师 抖音/小红书/知乎` |
| expert-ip | `{region}行测老师`、`{region}申论名师`、`{region}面试老师` |
| entity-alias | 第一轮品牌的简称、公司名、创始人和老师关系检索 |

### 第二轮漏项审计

- 加入非省会重点城市、区县、当地独立招录或高频专项。
- 搜索“本土、小班、工作室、基地、老师姓名、创始人、公司名、曾用名”。
- 从政府/高校活动、招投标、招聘、地图与平台账号反向发现机构。
- 对第一轮每个机构核验简称、公司名、主讲老师；对每个老师反查机构。
- 检查候选类型：全国品牌、本土综合、细分机构、老师/IP 型、新主体。

发现题不得改成 Measurement。第二轮新增占比高于 35% 时继续补一轮或说明停止依据。

## Measurement：统一测量，才计泛词覆盖

所有机构使用完全相同、与品牌无关的题池。默认标准档 20 题，均为 `query_type=generic`、`query_purpose=measurement`。

### 区域与综合（4）

1. `{region}公考培训机构有哪些？`
2. `{region}公务员考试培训机构怎么选？`
3. `{region}本土公考培训机构有哪些？`
4. `{city}公务员培训班有哪些？`

### 考试与课程（4）

5. `{region}{exam}培训机构推荐`
6. `{region}{exam}笔试培训班有哪些？`
7. `{region}{exam}面试培训机构有哪些？`
8. `{city}{exam}培训机构有哪些？`

### 科目与师资（4）

9. `{region}行测培训老师有哪些？`
10. `{region}申论培训老师有哪些？`
11. `{region}公考面试老师有哪些？`
12. `{region}公考选岗指导机构有哪些？`

### 产品（4）

13. `{region}公考基地班有哪些？`
14. `{region}公考一对一培训机构`
15. `{region}公考集训营有哪些？`
16. `{region}公考线上课程与线下课程有哪些？`

### 决策与专项（4）

17. `{region}公务员笔试培训机构对比`
18. `{region}公务员面试培训机构对比`
19. `{region}{interview_type}面试培训机构`
20. `{region}公考职位表分析和选岗服务机构`

快速档从五组各取题，约 10 题；深入/完整档增加城市、考试、科目、产品与人群组合到 50/100 题。Measurement 题池冻结后不得为某机构临时增删。

## Verification：核验，不计泛词覆盖

对冻结候选逐一执行：

- `{institution}是什么机构`、`{institution}官网`、`{legal_name}`。
- `{institution}主要课程/校区/基地`、`{institution}最近一年内容`。
- `{institution}创始人/老师是谁`、`{teacher}与{institution}关系`。
- `{alias} {region} 公考`、`{alias} 公司`，排除同名地区、历史、人物或普通词污染。
- `site:gov.cn|edu.cn "{institution}"` 以及独立来源核验。

品牌查询是 Verification，不证明非品牌问题会自然召回。

## 模式差异

- 地区全景：完整两轮 Discovery → 冻结候选 → 同一 Measurement → 逐主体 Verification。
- 单主体：不扩张候选；至少 10 个统一泛词 Measurement，再做点名主体 Verification。
- 多主体：所有点名主体共享同一 Measurement 题池和时间窗口；不自动加入竞品。
- 自有机构强制纳入：地区发现照常进行；该机构用 Verification 核验，Measurement 零命中仍记零。

## 最终检查

考试真实存在、地区层级正确、城市无歧义、面试类型有依据；三类 purpose 已分离；每条 sampled 查询有结果日志；重复问题已去除；Measurement 中不含任何品牌、机构或老师名。
