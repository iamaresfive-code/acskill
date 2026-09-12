# acskill

`acskill` 是一个持续维护的 AI Skills 仓库。

当前正式维护的核心 Skill 是 [`acs-second-brain-manager`](skill/acs-second-brain-manager/)：让 Agent 长期接管和治理本地 Markdown / Obsidian 第二大脑，而不是每次从头搜索、总结和整理资料。

它会先理解你已经存在的目录、命名、双链、项目和资料习惯，再处理知识查询、资料入库、更新合并、来源追踪、实体关系、项目状态和知识库健康检查。

## 第一次使用

如果你已经有知识库，可以直接告诉 Agent：

```text
请使用 acs-second-brain-manager 接管这个知识库。
这是一个已有库，第一次先只读扫描，不要修改文件。
```

然后提供当前 Obsidian Vault 或知识库目录即可。

如果你是第一次接触这个项目，直接看：

👉 **[新手入门](docs/新手入门.md)**

不需要先阅读完整 `SKILL.md`。

## 当前 Skill

### `acs-second-brain-manager`

第二大脑管理与知识治理 Skill。

适合：

- 本地 Markdown 文件夹；
- Obsidian Vault；
- 同时包含 PDF、Word、图片、表格等原始资料的知识库；
- 长期维护人物、机构、项目、研究、方法论和持续判断的个人或团队。

核心能力：

- 自适应理解已有知识库结构；
- 查询历史知识与当前项目状态；
- 新资料写入前查重、冲突检查和 Mutation Decision；
- `UPDATE / MERGE / CREATE / PENDING / SOURCE_ONLY` 五种知识变更；
- Source Layer / Knowledge Layer 分层；
- 来源追踪与事实边界；
- 人物、机构等实体关系维护；
- 时效数据与历史快照；
- 知识库健康检查；
- 高风险治理操作确认；
- 多 Agent 场景下的写入边界。

## 文档怎么读

不同文档承担不同职责，尽量不重复：

| 文档 | 给谁看 | 解决什么问题 |
| --- | --- | --- |
| [新手入门](docs/新手入门.md) | 第一次使用的人 | 第一句话怎么说、第一次会发生什么、平时怎么交任务 |
| [Skill README](skill/acs-second-brain-manager/README.md) | 想理解完整能力的人 | Skill 的能力模型、设计边界、目录与工具 |
| [Quick Start](skill/acs-second-brain-manager/docs/quick-start.md) | 已经理解项目的人 | 最短启动路径与常用入口 |
| [SKILL.md](skill/acs-second-brain-manager/SKILL.md) | Agent / 开发者 | 实际执行协议、治理规则和安全边界 |
| [使用案例](skill/acs-second-brain-manager/docs/examples.md) | 想看具体场景的人 | 真实资料如何查询、入库、更新和合并 |
| [概念解释](skill/acs-second-brain-manager/docs/concepts.md) | 想理解术语的人 | Living Knowledge、Source Layer、Profile 等概念 |
| [常见问题](skill/acs-second-brain-manager/docs/faq.md) | 遇到疑问的人 | 常见边界与使用问题 |

## 核心原则

```text
先理解，再治理。
先读源，再写知识。
查询不等于写入。
原始材料默认不可变。
关键冲突不猜。
知识页维护当前可用版本。
```

如果只是想开始使用，到这里就够了：打开 [新手入门](docs/新手入门.md)，然后把一个真实知识库和真实任务交给 Agent。