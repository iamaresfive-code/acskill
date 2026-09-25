# Onboarding 与已有库接管

## 目标

第一次接管的任务不是“整理”，而是建立对当前知识库的可靠理解。

## 已有库流程

1. 确认根目录和读取权限。
2. 查找已有权威文件：`AGENTS.md`、README、结构约定、索引、治理配置。
3. 运行或等价执行只读结构扫描。
4. 只按需要抽样读取 Markdown，不默认全文扫描。
5. 识别目录、frontmatter、链接、来源、索引、项目和归档习惯。
6. 将每条识别结果标为：confirmed / inferred / conflict / unknown。
7. 输出 Knowledge Base Understanding Report。
8. 用户确认或纠正。
9. 再创建/更新 `.second-brain/profile.yaml` 和 `structure-contract.md`，或引用已有等价规范。

## Understanding Report 最小字段

- root / platform；
- 主要目录；
- 主要知识域；
- 已发现治理文件；
- 页面类型和 frontmatter；
- 链接方式；
- 来源资料管理；
- 索引方式；
- 项目/归档状态；
- 推断规则；
- 冲突和未知；
- 推荐继续沿用的规则；
- 需要用户确认的最小问题。

## 新库流程

新库不执行 Adaptive Scan 推断现有规则。先询问：主要用途、主要资料类型、是否使用 Obsidian、是否需要原始材料层、是否管理项目。

只提出最小结构，不一次建立大量目录。用户确认后初始化，并把规则写入库内治理层。

## 治理层写入

`.second-brain/` 只用于治理配置、规则、运行状态和治理日志。

如果已有等价机制，优先引用已有文件并在 Profile 中登记 authority path。

## 结构漂移

Profile 可记录 `adaptive_scan.last_scan_at`、`confirmed_at` 和 `structure_fingerprint`。

fingerprint 建议基于目录结构、治理文件、frontmatter schema、索引路径等轻量信号，不需要给所有知识页做哈希。

检测到明显漂移时先提示重新扫描；不得静默按旧规则继续大规模写入。
