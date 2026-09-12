# 第二大脑知识库管理器

`acs-second-brain-manager` 是一个面向本地 Markdown / Obsidian 知识库的 AI 管理 Skill。

它的目标不是“帮你整理一次资料”，而是让 Agent 在长期使用中持续维护一套**可追溯、可更新、可查询、不过度改写原有结构**的第二大脑。

> 原始材料负责保留“当时到底说了什么”，知识页负责维护“我们现在对这件事到底怎么看”。

如果你第一次使用，不建议从这份 README 开始研究全部规则。

👉 先看 [acskill 新手入门](../../docs/新手入门.md)

## 这个 Skill 解决什么问题

随着资料越来越多，普通“文件夹 + 搜索 + AI 总结”会逐渐出现几个典型问题：

- 同一个人物、机构、项目被写进多个页面；
- 新信息来了，不知道应该更新旧页还是新建文件；
- 旧结论和新结论混在一起；
- AI 推断、用户判断和来源事实没有边界；
- Word、PDF、会议记录保存了很多，但无法长期复用；
- 每次提问都重新搜索、重新判断，知识没有积累；
- 一旦让 AI 自动整理，又担心它改乱目录、误删原件或写错长期事实。

`acs-second-brain-manager` 把这些问题视为**知识治理**问题，而不是单纯的文件搜索问题。

## 核心设计

### 1. Adaptive Structure

先理解已有知识库，再适配。

已有库第一次接管默认只读，不把开发者预设的 `People / Projects / Topics` 等结构强加给用户。如果知识库已经有 `AGENTS.md`、README、索引、frontmatter、双链或治理规则，优先复用。

### 2. Immutable Source

原始材料默认不可变。

PDF、Word、会议原文、聊天导出、网页快照等 Source Layer 负责保留可追溯证据，不为了“整理得更漂亮”而静默改写。

### 3. Living Knowledge

知识页维护当前最清晰、最可继续使用的版本。

例如最初资料说“计划开 5 个教学点”，后来确认“最终落地 3 个”，知识页应更新到当前状态；历史口径继续由来源材料或必要快照承担，而不是把每次聊天机械追加到页面末尾。

### 4. Read ≠ Write

查询、分析、健康检查默认不等于写入。

“我以前怎么看这个问题？”和“把这条信息更新进去”是两类不同任务。Skill 不会因为用户问了一次问题，就顺手修改长期知识库。

### 5. Evidence Boundary

重要信息区分：

- `Source Fact`：来源直接支持；
- `User Judgment`：用户明确表达的判断；
- `Agent Inference`：Agent 基于材料形成的推断；
- `Decision`：用户明确拍板；
- `Unknown / Pending`：当前无法确认。

Agent 推断不能伪装成来源事实，用户观点也不能自动写成行业客观事实。

## 能力地图

### 知识库接管

对已有 Markdown / Obsidian 知识库做 Read-only Adaptive Scan，识别目录、命名、frontmatter、链接方式、索引、原始资料区、项目组织方式和已有治理规则。

首次接管先输出 `Knowledge Base Understanding Report`，把“已确认、推断、冲突、未知、建议沿用规则”分开，再进入长期治理。

### 知识查询

支持查询：

- 过去的观点；
- 当前项目状态；
- 人物或机构关系；
- 某主题的历史结论；
- 某条事实来自哪里。

查询优先从明确实体、标题、别名和已知入口开始，只在必要时扩大扫描范围。

### 资料入库与知识变更

写入前先读源、找相关页、查重、检查冲突，再做 Mutation Decision：

| 动作 | 含义 | 典型情况 |
| --- | --- | --- |
| `UPDATE` | 更新已有知识 | 新事实明确替代旧状态 |
| `MERGE` | 合并进已有内容 | 新资料属于已有主题 |
| `CREATE` | 新建知识页 | 形成新的实体、项目、概念、流程或案例 |
| `PENDING` | 暂时待核 | 关键事实冲突或无法确认 |
| `SOURCE_ONLY` | 只保存原始材料 | 原件值得保留，但暂不值得形成知识页 |

默认不会因为“有新材料”就一定创建新文件。

### 来源追踪

Source Layer 与 Knowledge Layer 分离：

```text
原始材料
└── 某机构2026年交流纪要.docx

知识页
├── 机构-某机构.md
├── 渠道模式.md
└── 班型运营对比.md
```

这样既能保留原始证据，又能持续更新当前认知。

### 实体与关系

处理人物、机构、项目、产品等实体时，会考虑：

- 同名；
- 简称；
- 别名；
- 曾用名；
- 人物—机构关系；
- 项目—负责人关系。

有重大歧义时不自动合并，而是形成 Merge Proposal 或标记待核。

### 时效知识与快照

排名、价格、人数、粉丝量、项目状态等时效信息需要记录观察日期或统计期间。

长期方法与当期数据分开；只有至少两期同口径数据，才应称为“趋势”。

### 项目状态维护

不会仅凭日期、沉默时间或 Agent 猜测把项目标为结束。

项目状态优先依据用户明确确认、已有状态字段和知识库已确认的治理规则。

### 知识库健康检查

可检查：

- 重复页面和疑似重复实体；
- 断链；
- 孤立页；
- 索引遗漏；
- 重要事实缺来源；
- 过期快照；
- 项目状态矛盾；
- 同主题碎片化；
- frontmatter、命名和路径漂移；
- 原始材料异常风险。

健康检查默认只报告，不自动批量修复。

### 多 Agent 协作

默认 `single-agent`。

确有多个 Agent 同库协作时，采用 `multiple readers + single writer` 的原则，通过任务所有者、写锁、handoff 和故障接管限制并发写入风险。

## 写入模式

支持三种模式：

| 模式 | 行为 |
| --- | --- |
| `read-only` | 只查询、分析、诊断，不写入 |
| `confirm-first` | 默认。先给完整 Mutation Plan，用户确认后执行 |
| `trusted-task` | 用户先确认任务边界，在边界内连续维护 |

即使在 `trusted-task` 下，删除、大规模移动、治理规则变化、批量实体合并等高风险动作仍需单独确认。

## 库内治理层

在没有等价机制时，可使用：

```text
.second-brain/
├── profile.yaml
├── structure-contract.md
├── state.json
└── governance-log.md
```

其中：

- `profile.yaml`：知识库机器配置；
- `structure-contract.md`：知识库治理约定；
- `state.json`：确有运行状态或并发需要时使用；
- `governance-log.md`：需要记录治理变更时使用。

`.second-brain/` 只属于治理层，不存放人物事实、项目结论、行业研究或用户观点。

如果已有库已经有等价规则，优先复用，不制造第二套真相源。

## 安全边界

普通“帮我入库”不会顺带授权以下行为：

- 一级目录新增、删除或重命名；
- 大规模移动或批量重命名；
- 页面类型体系变化；
- 模板、索引或来源策略变化；
- 改变治理配置的含义；
- 开启或改变多 Agent 写入机制；
- 大规模实体合并；
- 删除文件。

高风险治理变更必须先说明影响、迁移范围与回滚路径，再单独确认。

## 适用范围

适合：

- 本地 Markdown 文件夹；
- Obsidian Vault；
- 同时保存 PDF / Word / 图片 / 表格等原始资料的知识库；
- 行业研究、项目管理、人物与机构资料、咨询案例、内容研究、长期方法论沉淀；
- 希望 AI 长期维护“当前可用知识”的个人或团队。

不负责：

- 纯网页抓取；
- 公众号正文提取；
- 在线 PDF 下载；
- 普通泛问答；
- 与知识库无关的代码、写作或网页搜索；
- 未经授权的大规模目录重构和删除。

## 工具与文件结构

```text
acs-second-brain-manager/
├── SKILL.md                         # Agent 执行协议
├── README.md                        # 能力与架构说明
├── agents/
│   └── openai.yaml
├── docs/
│   ├── quick-start.md               # 最短启动路径
│   ├── examples.md                  # 使用案例
│   ├── concepts.md                  # 概念解释
│   └── faq.md                       # 常见问题
├── references/
│   ├── onboarding.md                # 首次接管执行细则
│   ├── knowledge-model.md           # 知识模型与写入规则
│   ├── health-check.md              # 健康检查细则
│   └── concurrency-policy.md        # 多 Agent 并发规则
├── templates/
│   ├── profile.yaml
│   └── structure-contract.md
├── scripts/
│   ├── scan_knowledge_base.py       # 只读结构扫描
│   ├── validate_profile.py          # Profile 校验
│   └── health_check.py              # 只读结构健康检查
└── tests/
    └── test_v1.py                   # 最小 smoke test
```

## 快速测试

```bash
python tests/test_v1.py
```

扫描与健康检查脚本默认使用只读逻辑；除非显式指定输出，不会因为运行检查而改写业务知识。

## 文档入口

### 第一次使用

- [acskill 新手入门](../../docs/新手入门.md)
- [Quick Start](docs/quick-start.md)

### 看实际场景

- [使用案例](docs/examples.md)
- [常见问题](docs/faq.md)

### 理解概念

- [概念解释](docs/concepts.md)

### Agent / 开发者执行细则

- [SKILL.md](SKILL.md)
- [首次接管](references/onboarding.md)
- [知识模型与写入规则](references/knowledge-model.md)
- [健康检查](references/health-check.md)
- [多 Agent 并发](references/concurrency-policy.md)

## 一句话总结

`acs-second-brain-manager` 不是替用户建立一套固定目录，而是让 Agent **先理解用户已经形成的知识体系，再在明确证据边界和写入权限下长期治理它**。