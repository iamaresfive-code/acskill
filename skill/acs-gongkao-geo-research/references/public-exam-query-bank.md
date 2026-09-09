# 公考 GEO 查询词库 v2.1

先识别当地真实考试生态，再生成 Discovery / Institution Measurement / IP Measurement / Verification。示例只用于说明，不能机械复制到其他地区。

## 变量

- `{region}`：省、自治区、直辖市、城市或研究区域
- `{city}`：重点城市、区县
- `{exam}`：当地真实存在的考试
- `{interview_type}`：可靠来源确认的面试形式
- `{institution}`、`{teacher}`、`{legal_name}`、`{alias}`：待核实体字段

## 一、先建立 Semantic Theme Map

地区全景开始前，根据地区考试生态建立 `semantic_theme`。候选主题可包括：

- 综合公考
- 省/市考
- 国考
- 事业单位
- 选调
- 定向选调
- 遴选
- 军队文职
- 公安警法
- 面试形式
- 高校活动 / 就业指导
- 本地老师 / IP
- 品牌简称 / 公司名 / 曾用名
- 非省会重点城市 / 区县

不是每个地区都需要所有主题。是否 `required=true` 必须根据当地真实考试结构决定。

## 二、Discovery：找对象，不计分

六路全部保留：

### user-query

- `{region}公考培训机构有哪些`
- `{region}本土公考机构`
- `{city}公务员培训班`
- `{region}公考基地班`

### exam-vertical

对每个 required exam theme 至少形成一组：

- `{region}{exam}培训机构`
- `{region}{exam}笔试培训`
- `{region}{exam}面试培训`
- `{region}{exam}老师`

### institutional

不能只跑一条 `site:edu.cn`。按 Semantic Theme 覆盖：

- `site:edu.cn {region} {exam} 培训`
- `site:edu.cn {region} {exam} 讲座`
- `site:edu.cn {region} {exam} 经验分享`
- `site:gov.cn {region} {exam} 培训`
- `{region} 高校 {exam} 就业 讲座`

### platform

- `{region}公考机构 B站`
- `{region}公考老师 知乎`
- `{region}公考老师 抖音`
- `{region}公考老师 小红书`

能否实际覆盖取决于当前环境可访问性；登录墙和不可抓取平台应写明局限。

### expert-ip

- `{region}行测老师`
- `{region}申论老师`
- `{region}面试老师`
- `{region}{exam}老师`

### entity-alias

围绕已发现机构/老师反向查：

- `{institution} 公司`
- `{institution} 简称`
- `{institution} 曾用名`
- `{teacher} {institution}`
- `{alias} {region} 公考`

Discovery Query 即使本身没有品牌名，也绝不能计入 Query Coverage。

## 三、Institution Measurement：统一无品牌实测

冻结候选池后，所有可评分机构共享同一题池。

默认标准档 20 题；字段：

```text
query_type=generic
query_purpose=measurement
measurement_target=institution
```

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

9. `{region}行测培训机构有哪些？`
10. `{region}申论培训机构有哪些？`
11. `{region}公考面试培训机构有哪些？`
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

题池冻结后不得为某机构临时增删。

## 四、IP Measurement：人物无品牌实测

深度地区模式建议至少 6 题：

```text
query_type=generic
query_purpose=measurement
measurement_target=ip
```

示例：

1. `{region}申论老师推荐`
2. `{region}行测老师推荐`
3. `{region}公考面试老师推荐`
4. `{region}事业单位面试老师推荐`
5. `{region}选调老师推荐`
6. `{region}谁最懂本地公考考情`

机构 Measurement 与 IP Measurement 分母严格分开。

## 五、Verification：核验，不计 Query Coverage

- `{institution}是什么机构`
- `{institution}官网`
- `{legal_name}`
- `{institution}主要课程/校区/基地`
- `{institution}最近一年内容`
- `{institution}创始人/老师是谁`
- `{teacher}与{institution}关系`
- `{alias} {region} 公考`
- `site:gov.cn "{institution}"`
- `site:edu.cn "{institution}"`

品牌词命中只说明主体可核验，不证明无品牌问题下会自然召回。

## 六、Semantic Coverage Audit

每个 required 主题至少记录：

- query_count
- result_count
- eligible_candidates_found
- status

只有实际检索后才可标 `covered` 或 `no-result-reviewed`。

## 七、Candidate Saturation

补漏轮次继续直到至少满足一项：

- 最近一轮新增率 <10%；
- 最近一轮新增可评估独立机构 <=1；
- 连续两轮无重要新增主体。

如果新增仍明显，应继续搜索，而不是只因“做了两轮”就冻结。
