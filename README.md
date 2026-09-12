# acskill

`acskill` 是一个持续维护的 AI Skills 仓库。

当前正式维护的核心 Skill 是 `acs-second-brain-manager`：用于让 Agent 长期接管和治理本地 Markdown / Obsidian 第二大脑。

它不是简单的文件搜索，也不是把每次聊天原样塞进知识库。它会先理解你已有的目录、命名、双链、项目和资料习惯，再处理查询、入库、更新、合并、来源追踪、实体关系、项目状态和知识库健康检查。

## 第一次使用

如果你已经有一个知识库，可以直接告诉 Agent：

```text
请使用 acs-second-brain-manager 接管这个知识库。
这是一个已有库，第一次先只读扫描，不要修改文件。
```

然后提供当前 Obsidian Vault 或知识库目录即可。

完整的新手使用方式见：

👉 [新手入门](docs/新手入门.md)

## 当前 Skill

### `acs-second-brain-manager`

第二大脑管理与知识治理 Skill。

适合：

- 本地 Markdown 文件夹；
- Obsidian Vault；
- 同时包含 PDF、Word、图片、表格等原始资料的知识库；
- 需要长期维护人物、机构、项目、研究、方法论和持续判断的个人或团队。

核心能力包括：

- 自适应理解已有知识库结构；
- 查询历史知识与当前项目状态；
- 新资料入库前查重、冲突检查和写入决策；
- `UPDATE / MERGE / CREATE / PENDING / SOURCE_ONLY` 五种知识变更；
- 原始材料与知识页分层；
- 来源追踪与事实边界；
- 人物、机构等实体关系维护；
- 时效数据与历史快照；
- 知识库健康检查；
- 高风险治理操作确认；
- 多 Agent 场景下的写入边界。

详细说明：

- [Skill README](skill/acs-second-brain-manager/README.md)
- [SKILL.md](skill/acs-second-brain-manager/SKILL.md)
- [5 分钟快速开始](skill/acs-second-brain-manager/docs/quick-start.md)
- [使用案例](skill/acs-second-brain-manager/docs/examples.md)
- [概念解释](skill/acs-second-brain-manager/docs/concepts.md)
- [常见问题](skill/acs-second-brain-manager/docs/faq.md)

## 核心原则

```text
先理解，再治理。
先读源，再写知识。
查询不等于写入。
原始材料默认不可变。
关键冲突不猜。
知识页维护当前可用版本。
```

如果你第一次接触这个仓库，不需要先读完整个 `SKILL.md`。

从 [新手入门](docs/新手入门.md) 开始，然后把一个真实知识库和真实任务交给 Agent 即可。
