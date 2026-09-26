---
name: acs-knowledge-governance-bootstrap
description: 为本地Markdown或Obsidian知识库一次性初始化或适配治理体系，落地AGENTS.md、必要规范、模板和独立工具。新库使用中文目录，已有库保留原结构；仅初始化、接管配置或治理升级时使用，不接管日常查询与入库。
metadata:
  version: "1.1"
---

# 知识库治理初始化与适配

本Skill独立负责治理初始化与适配，与长期管理器 `acs-second-brain-manager` 分开：落地后的规则与工具独立属于目标库，不依赖本Skill常驻。

## 先确认需要

确认用户指定根目录存在；只补问尚不清楚的主要用途、已有库/新库、主要维护者及所需模块。首次只读：运行 `scripts/scan_knowledge_base.py` 或等价检查，完整读取AGENTS及相关现有权威规则，定位既有来源、知识、索引、模板与工具。扫描是观察，不是授权或确认规则。

- **新库**：默认中文目录 `知识/`、`原始材料/`、`索引/`、`规范与工具/`；按用途命名业务目录，不复制开发者行业、机构或个人路径。AGENTS.md等固定文件名保留。空的Obsidian配置目录不算业务内容。
- **已有库**：沿用原目录、文件名、页面字段和索引。明确映射知识和来源目录、现有权威文件与索引；不强制改中文、不批量移动。没有来源目录或索引时先说明需求，未确认不建立。已有等价工具与规范应复用或合并，不制造第二套权威。

## 生成可审阅方案

按 [安装流程](references/onboarding.md) 准备配置，在库外生成方案：

```bash
python3 scripts/bootstrap.py plan /absolute/vault --mode new --output /absolute/temp/plan
# 已有库必须提供人工核对的配置
python3 scripts/bootstrap.py plan /absolute/vault --mode existing --config /absolute/temp/config.json --output /absolute/temp/plan
```

脚本仅生成候选，不改目标库。说明每个新增、合并、保留项和可选模块，逐项审阅 `方案.md`、`plan.json`、`before/` 与 `after/` 的真实内容。AGENTS只追加/更新标记区，仍须人工判断语义冲突；它不能覆盖现有明确规则。

基础包包括AGENTS入口、结构约定、知识维护规则、空白知识页模板、路径配置、链接/索引检查和本地使用说明。新库另生成中文导航；已有库不重建索引。可选模块为网页收录、多格式读取、项目记忆、多Agent协作、原件哈希，只选择用户需要的，不为凑齐模板全部安装。

生成器提供最小起点，不代替适配判断。未知字段、目录交叠、路径越界、符号链接、已有文件冲突会拒绝。若目标已存在同名规则或自定义格式，先比较并沿用现有文件；必要的人工合并按 [冲突与升级](references/onboarding.md) 操作，不绕过冲突直接覆盖。

## 确认后安装

用户批准具体完整方案后执行；已明确批准的步骤不重复询问。授权只覆盖本次治理文件和工具，不包括业务资料迁移、外部账号调用、发布或后台监控。

```bash
python3 scripts/bootstrap.py apply /absolute/temp/plan/plan.json --approved
```

`--approved` 是执行者已取得用户授权的声明，不是授权来源。应用前重验候选内容、目标文件及既有权威规则指纹；变化则重读并重新出方案，不覆盖旧快照。批量预检通过后写入，失败只回退仍等于本次写入的文件并报告；无法保证跨进程原子性，需协调同文件并行修改。方案备份含用户规则，留在本机，不提交到公开仓库。

## 验收与退出

1. 运行安装后的 `治理检查.py`，核对入口、适用规则、链接与已配置索引；既有问题和新引入问题分开，不能把旧库告警隐去。
2. 选择原件模块时，prepare库外候选、人工核对、commit并独立check；已有原件改变或丢失必须报错，不能重建掩盖。
3. 人工核对目录中文/原结构保留、权限、事实边界、模板字段与业务适配。现有用户规则冲突未解决不能称安装完成。
4. 回报落地位置、启用模块、保留与合并项、验收范围及待核问题。说明日常直接按库内AGENTS和规范执行；只有明确升级治理时再调用本Skill。

不创建默认英文 `.second-brain/` 治理目录，不生成active/idle锁或强制交接板，不复制真实姓名、账号、业务数据或本机路径。

## 资源

- [安装流程与配置](references/onboarding.md)
- [知识维护规则](references/knowledge-model.md)
- [项目记忆规范](references/project-memory.md)（选择projects时读取）
- [协作规范](references/concurrency-policy.md)（选择collaboration时读取）
- [网页规范](references/web-ingestion.md)、[文件规范](references/file-reading.md)（按模块读取）
- [验收范围](references/health-check.md)
- `scripts/bootstrap.py`：库外方案、指纹预检及安装。
- `scripts/scan_knowledge_base.py`：只读结构观察。
- `scripts/health_check.py`、`scripts/check_governance.py`、`scripts/source_integrity.py`：安装时复制到目标库的独立工具。
- 只需Python 3.10+标准库，不依赖长期管理器或旧YAML配置。
