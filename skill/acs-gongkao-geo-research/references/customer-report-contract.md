# 中文客户报告契约（v2.2.1 补丁）

本文件约束唯一正式交付物 `deliverables/report.docx` 的**用户可见层**。研究底稿、审计 CSV/JSON、内部枚举和脚本仍保留在 Run 目录，但不得直接倾倒进客户报告。

## 1. 三层信息边界

### 客户报告层：必须给用户看

- 核心结论：谁在 AI 回答中更容易被提名，差距有多大；
- 全国品牌、本地/区域机构、老师/IP 分开比较；
- 换一种问法后结果是否稳定；
- GEO 资产基础、概念占位，以及它们与 AI 可见度的关系；
- 重点主体的优势、短板、优先动作；
- 区域策略与 90 天行动；
- 必要的方法边界与“不适用”说明。

### 方法附录层：可以给专业用户看

- 研究地区、AI 测量环境、回答样本数、观察日期；
- 机构题与老师/IP题分开计量；
- 语义等价问法的稳定性口径；
- 正式研究主体清单；
- 暂无足够公开证据、因此暂不评分的主体。

### 工程审计层：不进入客户 DOCX

- `measurement_target`、`market_role`、`query_variant_mode` 等内部字段；
- `local-core`、`native-recorded`、`semantic-retrieval-variants` 等内部枚举；
- CSV / JSON / JSONL / Python 文件名；
- Validator 错误码、脚本调用链、内部哈希与 Run 文件清单；
- Python dict / JSON 原始对象字符串；
- Annotation / Resolution / Citation 的逐行审计明细。

完整工程底稿继续保留在 Run 目录，必要时单独提供审计，不在客户报告正文展开。

## 2. 语言规则

正式报告默认使用**简体中文**。

允许保留的常用缩写：`AI`、`GEO`、`IP`、`URL`、`Word / DOCX`。

可翻译术语一律使用中文主名，例如：

| 内部/英文术语 | 客户报告写法 |
| --- | --- |
| Market Universe | 研究主体池 |
| AI Answer Measurement | AI 回答测量 |
| Nomination Rate | 提名率 |
| Top3 Rate | 前三出现率 |
| First Mention Rate | 首提率 |
| Citation Rate | 引用率 |
| Query / Retrieval Robustness | 提问与检索鲁棒性 / 结果稳定性 |
| GEO Asset Readiness | GEO 资产基础 |
| Concept Ownership | 概念占位 |
| AI-emergent | AI 回答中新出现的主体 |
| native | 模型原生回答 |
| programmatic | 程序性隔离 |
| single-engine | 单引擎 |
| unknown | 暂无可核验证据 |

不得为了“专业感”在主体报告中堆英文内部字段。

## 3. 图表规则

图表必须先帮助用户判断，再保证数据完整。

- 排名图使用中文标题、中文主体名、直接数值标签；
- 概念占位使用 Top N 条形图，不使用高度稀疏且难读的热力图；
- 资产排名只展示有足够证据形成评分的主体，未知不得画成 0 分；
- 使用“AI 可见度 × GEO 资产基础”二维图解释机会区，虚线只能作为本轮相对中位数，不包装成行业绝对阈值；
- 内部 Bucket/enum 不得直接作为图例或坐标标签；
- 若运行环境缺少中文字体，可以退化为编号标签，但不得自动改成英文客户图。

## 4. 引用率语义

如果原 Answer 没有提供 citations：

- `Citation Rate` 在客户报告中显示为**不适用**；
- 不得显示 `0%`；
- 不得解释为“AI 从未引用该主体”。

只有测量环境真实提供引用链时，才展示引用率。

## 5. GEO 资产证据不足

没有找到公开证据不等于 0 分。

- 有足够证据：可形成资产基础得分与等级；
- 证据不足：客户报告写“暂不评分”；
- 主表不展示 `unknown_fields` 字段清单；
- 可在方法附录列出“暂不评分主体”名称。

## 6. 概念绑定强度

概念绑定必须可核验，强度带宽如下：

| 绑定性质 | 合法强度 |
| --- | ---: |
| 主体主动表达（owned-declaration） | 8–10 |
| 公开内容高频绑定（high-frequency-public-binding） | 6–8 |
| 第三方稳定描述（third-party-description） | 3–5 |
| 单次偶发提及（single-incidental-mention） | 1–2 |

单次第三方提及不得包装成强概念占位。

## 7. 自动 QA 必须阻断

客户 DOCX 出现以下情况应直接 FAIL：

- 一级标题仍是英文；
- 内部字段名或 snake_case；
- `.csv` / `.json` / `.jsonl` / `.py` 工程文件名；
- Python / JSON 原始对象字符串；
- 无引用链时把引用率写成 0；
- 工程审计清单进入客户正文；
- 关键章节只有标题没有内容。
