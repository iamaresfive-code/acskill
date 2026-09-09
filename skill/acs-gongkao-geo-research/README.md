# acs-gongkao-geo-research v2.1.1

> 公考行业 GEO 竞争研究与咨询报告 Skill

如果你第一次接触 GEO，可以把它理解成：

**调查一个公考机构、品牌或老师/IP，在 AI 搜索与生成式搜索环境里是否容易被找到、能不能被机器正确理解、在用户没有输入品牌名时是否会自然出现、公开证据是否足够稳定。**

它不是“教学最好排行榜”，也不是“谁家上岸率最高”。

## v2.1.1 为什么要升级

v2.1 在全新广东环境实测后暴露出一个很典型的问题：全国品牌容易被找到，但一些真实存在、在本地市场有影响力的机构和老师/IP 可能没有进入最终报告；上游即使测过 IP，也可能因为 Report Model / Renderer 没消费数据而只剩一句“本次已执行 IP Measurement”。同时 HTML 把固定 A4 宽度直接套在浏览器，宽 SVG 和长表格容易出现错位、拥挤或横向溢出。

v2.1.1 不是给本土机构“抬分”，而是先解决四件事：

1. **找得更完整**：补本土机构、工作室、老师型品牌和平台原生 IP 的发现路线；
2. **没进榜也说清楚**：证据不足、实体未解析的主体进入观察组，不再静默消失；
3. **数据不丢**：IP Measurement、Candidate Audit、Research Assets 真正进入 Report Model 和三套正式报告；
4. **报告排得稳**：HTML 响应式，A4 只用于打印；宽表和 SVG 不再硬挤。

五维评分仍是 30/25/20/15/10，不因为某家机构或某个 IP 修改。

## 第一次使用仍然只回答三个问题

1. **调查哪里？** 例如广东省、天津市、广州市、珠三角；
2. **有没有特别想看的机构、品牌或老师/IP？** 没有也可以；
3. **最后要 Word、PDF 还是 HTML？** 默认只正式交你选择的那一种。

例如：

> 做广东公考 GEO，不指定机构，出 HTML。

三个参数齐全后直接开始，不重复问。

## “指定机构/老师”不等于加分

指定只表示：**这个主体一定要调查到。**

它不表示一定进排名，不自动增加 Recall，不提高证据等级，也不改变评分权重。

证据够 → 正常评分；证据不足 → 进入观察组；名字/实体还无法确认 → 标记 unresolved；老师/IP 做了独立 Measurement → 可标 `ip-measured`。

## 为什么增加 Local Ecosystem Recall

v2.1 已经有六路 Discovery 和 Semantic Coverage，但“考试主题都搜过”仍不等于“真实本土生态找全了”。一个地区可能有：

- 本土机构与工作室；
- 基地班/地市型品牌；
- 以老师个人为品牌的小机构；
- 抖音、视频号、B站、小红书等平台原生公考 IP；
- 以“选岗、公考规划、专业选择、面试”等概念占位的人物，而不是传统学科老师。

所以 v2.1.1 在 Candidate Freeze 前新增三组通用检查：

```text
local-institution-ecosystem
local-expert-ip
platform-native-ip
```

注意：这不是把广东某些机构或老师写死进去，而是要求系统真的覆盖“本土机构生态、概念型 Expert/IP、平台原生 IP”三类入口。

## Candidate Pool 现在有三道门

以前：

```text
Semantic Coverage Gate
+ Saturation Gate
```

现在：

```text
Semantic Coverage Gate
+ Saturation Gate
+ Local Ecosystem Completeness Gate
```

而且有两条“不得漏掉”的机器规则：

- Discovery 已经解析出 entity_id，就必须进入 Candidate Pool；
- 同一个未解析名称在至少两个独立来源域重复出现，不能直接丢掉，必须继续做候选/实体解析。

## 为什么“没排名”不等于“GEO 为零”

正式报告现在分至少两层：

### A. 正式 GEO 排名

Measurement、实体关系和证据达到正式评分要求。

### B. 本土候选观察组

对 `evidence-insufficient` / `unresolved` 主体公开说明：

- 谁；
- 什么类型；
- 已经确认了什么；
- 缺官网、法律主体、官方账号还是其他证据；
- 为什么本次没有进入正式排名。

这样用户不会再看到“13 家证据不足”却不知道是哪 13 家。

## IP / Expert GEO 不再只剩一句话

如果真正执行了 IP Measurement，正式报告必须给出 IP 表格，至少包括：

- IP / 老师名称；
- 关联机构；
- IP hits / queries；
- Recall；
- 科目 / 概念标签；
- 平台；
- Evidence Confidence。

老师/IP 不和机构总榜混算，也不会因为粉丝多就直接获得机构 GEO 分数。

## 派生数字不用再手工补

v2.1.1 的 `score_geo.py --run-dir` 自动从当前 Run 派生：

- 泛词命中数与分母；
- Brand hits；
- Evidence 数；
- 独立来源域名数。

这能避免“第一次 strict validation 必挂，然后人工补数”的流程。

## 自有站很多，是否应该扣分？

v2.1.1 暂时**不改总分模型**。

报告新增解释指标：

- `Owned Source Dependency Ratio`：多少证据/占位高度依赖自身域名；
- `Evidence Authority Index`：独立来源与证据质量结构。

这样可以区分“召回很高但高度依赖自有站”和“第三方证据结构更健康”，但不会在 bug-fix 版本里临时改权重。是否纳入正式评分留给后续版本单独研究。

## public-web-proxy 要怎么理解

如果 `sampling_mode=public-web-proxy`，代表这是一轮**公开网页代理观察**，不是对所有 ChatGPT、DeepSeek、豆包、百度AI等产品真实回答的全量截屏。

它会受到 SEO 站群、聚合页、自有站矩阵、登录墙、平台可访问性和搜索索引差异影响。正式报告必须写清这层限制。

并行 Agent 采样时，建议至少随机抽 20% Measurement Query 做第二采样员复判，降低不同 Agent 对“什么算命中”的口径漂移。

## HTML 为什么会比 v2.1 整齐

v2.1 的浏览器页面把 A4 宽度直接用在屏幕端，里面又有 900/930px SVG 和 7 列长文本表，容易挤压和溢出。

v2.1.1 改为：

- 浏览器端 `max-width` 响应式；
- SVG 强制缩放到容器内；
- 宽表允许横向滚动；
- 商业 Scorecard 拆成“紧凑排名表 + 每家机构诊断卡”；
- Authority × Recall 加标签避碰与引导线；
- 只有打印时才使用 A4 规则。

所以 HTML 和 PDF/Word 不再被迫使用同一套物理版面。

## 报告为什么要有 Appendix

前台报告要给管理者看，后台研究又必须能审计。Appendix 至少披露：

- Candidate Status；
- Research Assets；
- Freeze Gate 状态；
- Institution / IP Measurement 数；
- Evidence Index。

这样“结论从哪里来的”和“哪些主体没进入正式排名”都可以追溯。

## 最常用的说法

- “做广东公考 GEO，不指定机构，出 HTML。”
- “做天津公考 GEO，把津仕和北宋也调查进去，出 Word。”
- “深挖上岸村 GEO，PDF。”
- “比较甲机构和乙机构在山东的 GEO 表现。”
- “广东本土公考 IP 和规划类 IP 的 GEO 怎么样？”
- “把证据不足的本土机构也列出来，不要只给正式排名。”

## 开发者 / Agent 入口

- `SKILL.md`：完整执行协议；
- `references/v2.1.1-stability.md`：本次稳定性/召回/报告契约补丁；
- `references/methodology.md`：研究方法；
- `references/data-schema.md`：v2.1 基础数据结构；
- `references/public-exam-query-bank.md`：Query Bank；
- `references/report-design-system.md`：报告设计；
- `scripts/preflight.py`：三步 Preflight；
- `scripts/score_geo.py`：评分与派生指标；
- `scripts/generate_charts.py`：本次 Run 图表；
- `scripts/build_report_model.py`：统一 Report Model；
- `scripts/generate_report_docx.py` / `generate_report_pdf.py` / `generate_report_html.py`：三 Renderer；
- `scripts/validate_run.py`：Research + Report Contract + Renderer 校验；
- `scripts/test_v211.py`：v2.1.1 回归。

## 验收命令

```bash
python3 -m py_compile scripts/*.py
python3 scripts/test_v211.py
python3 scripts/validate_run.py <run-dir> --strict
```

自动校验通过后仍需做 Visual QA，尤其是 HTML 溢出、Word/PDF 裁切与坏分页。fixture 只验证规则，不能冒充真实地区 Measurement。
