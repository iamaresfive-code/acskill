# acskill

> 一组面向真实工作场景的开源 Agent Skills。当前重点覆盖：公考行业 GEO 竞争研究，以及本地 Markdown / Obsidian 第二大脑管理。

**当前正式 Release：`v2.2`**

[新手入门](docs/新手入门.md) · [GEO Skill](skill/acs-gongkao-geo-research/README.md) · [第二大脑 Skill](skill/acs-second-brain-manager/README.md) · [Releases](https://github.com/iamaresfive-code/acskill/releases)

## 目前包含什么

| Skill | 版本 | 用途 |
| --- | --- | --- |
| `acs-gongkao-geo-research` | v2.2 | 调研某地区公考机构 / 老师 IP 的 AI Answer Visibility、竞争格局与 GEO Asset Readiness，正式输出 Word 报告 |
| `acs-second-brain-manager` | v1.0 | 自适应管理本地 Markdown / Obsidian 知识库，支持查询、入库、更新、合并、来源追踪和健康检查 |

## 快速安装

安装公考 GEO 调研 Skill：

```bash
npx skills add https://github.com/iamaresfive-code/acskill --skill acs-gongkao-geo-research
```

安装第二大脑知识库管理器：

```bash
npx skills add https://github.com/iamaresfive-code/acskill --skill acs-second-brain-manager
```

安装后不需要先学脚本，直接把真实任务交给 Agent。

例如：

```text
使用 acs-gongkao-geo-research 调研天津公考 GEO。
必须覆盖津仕、北宋，允许系统补充其他竞争主体。
```

或者：

```text
使用 acs-second-brain-manager 接管我的 Obsidian 知识库。
第一次先只读扫描，不要修改文件。
```

## 两个 Skill 怎么选

**你要研究外部市场和竞争格局：** 用 `acs-gongkao-geo-research`。

**你要管理自己的长期资料和知识：** 用 `acs-second-brain-manager`。

也可以前后配合：先用 GEO Skill 形成正式研究结果，再用 Second Brain Skill 把结果长期沉淀、更新和复用。

## 完整说明书

第一次使用，建议直接看：

**[《acskill 新手入门》](docs/新手入门.md)**

里面包含：

- 怎么安装；
- 第一次应该怎么说；
- GEO 调研到底测什么；
- 为什么不能把 GEO 结果当真实市场份额；
- 第二大脑第一次为什么只读接管；
- 常用输入示例；
- 两个 Skill 的使用边界；
- 更新方式；
- 深度文档入口。

## 更新

使用 Skills CLI 安装后：

```bash
npx skills update
```

正式版本、Tag 和 Release 以本仓库 GitHub 页面为准。

## 仓库结构

```text
acskill/
├── README.md
├── docs/
│   └── 新手入门.md
└── skill/
    ├── acs-gongkao-geo-research/
    └── acs-second-brain-manager/
```

如果你是第一次来，不需要先读 `SKILL.md`。先从 [新手入门](docs/新手入门.md) 和一个真实任务开始。
