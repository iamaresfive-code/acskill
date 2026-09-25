# acskill

`acskill` 是一个持续维护的 AI Skills 仓库。

这里不把所有能力塞进一个万能 Skill，而是按真实任务拆分：每个 Skill 都有自己的执行协议、用户说明、参考规范、脚本和最小测试，彼此职责尽量不重叠。

目前正式维护三个 Skill，其中知识库相关能力分为两个独立技能：

| Skill | 解决什么问题 | 入口 |
| --- | --- | --- |
| `acs-knowledge-governance-bootstrap` | 一次性安装治理方案；新库中文目录、已有库保留结构 | [查看 Skill](skill/acs-knowledge-governance-bootstrap/) |
| `acs-second-brain-manager` | 长期接管和治理本地 Markdown / Obsidian 第二大脑 | [查看 Skill](skill/acs-second-brain-manager/) |
| `acs-video-script-extractor` | 本地音视频离线转写、双模型复核、字幕校对与还原文案整理 | [查看 Skill](skill/acs-video-script-extractor/) |

如果你第一次使用，直接看：

👉 **[新手入门](docs/新手入门.md)**

不需要先读完整 `SKILL.md`。

## 第一次怎么选

### 你要给知识库安装治理方案

使用 `acs-knowledge-governance-bootstrap`：先了解用途和现状，生成可审阅方案，确认后落地AGENTS、必要规范和工具。安装后可直接按库内规则工作。

### 你要长期管理第二大脑

直接告诉 Agent：

```text
请使用 acs-second-brain-manager 接管这个知识库。
这是一个已有库，第一次先只读扫描，不要修改文件。
```

然后提供当前 Obsidian Vault 或知识库目录即可。

### 你要从本地视频提取文案

直接告诉 Agent：

```text
请使用 acs-video-script-extractor 处理这个本地视频。
全程离线，先做双模型转写，再校对高风险差异；如果视频有可见字幕，结合字幕画面复核。
最后给我完整逐字稿、还原整理文案和待确认疑点。
```

然后提供本地音视频文件。

## 当前 Skills

### `acs-knowledge-governance-bootstrap`

知识库治理初始化与适配（v1.0）。新库默认中文目录；已有库保留路径、命名和资料，按需补齐AGENTS、规范、模板和独立检查工具。先审阅方案再安装，重复运行保护用户改动；不要求长期管理器作为依赖。

详细说明：[初始化与适配 README](skill/acs-knowledge-governance-bootstrap/README.md)


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
- 长期项目专项记忆与跨对话接手；
- 知识库健康检查；
- 高风险治理操作确认；
- 多 Agent 场景下的写入边界。

详细说明：[Skill README](skill/acs-second-brain-manager/README.md)

### `acs-video-script-extractor`

本地视频逐字稿与文案提取 Skill。

适合：

- MP4 / MOV / M4V / MP3 / M4A / WAV 等本地音视频；
- 课程、访谈、会议、短视频原片的完整转写；
- 需要重点核对人名、机构名、数字、日期、否定词和英文专名的内容；
- 不希望把源视频上传云端转写服务的场景。

核心能力：

- ffprobe + SHA-256 只读媒体预检；
- `large-v3 + medium` 双模型本地转写；
- 全文差异对齐与风险分级；
- 高风险差异优先字幕抽帧；
- 校对逐字稿 / 还原整理稿 / 创作稿分层；
- 待确认疑点显式保留；
- 完整交付验收；
- 不写死开发者个人路径，可通过环境变量适配本机环境。

详细说明：[Skill README](skill/acs-video-script-extractor/README.md)

## 仓库结构

```text
acskill/
├── README.md
├── docs/
│   └── 新手入门.md
└── skill/
    ├── acs-knowledge-governance-bootstrap/  # 一次性安装与适配
    ├── acs-second-brain-manager/
    │   ├── README.md
    │   ├── SKILL.md
    │   ├── agents/
    │   ├── docs/
    │   ├── references/
    │   ├── scripts/
    │   ├── templates/
    │   └── tests/
    └── acs-video-script-extractor/
        ├── README.md
        ├── SKILL.md
        ├── agents/
        ├── docs/
        ├── references/
        ├── scripts/
        └── tests/
```

每个正式 Skill 至少应包含：

- `SKILL.md`：Agent 实际执行协议；
- `README.md`：给用户和开发者看的能力说明；
- `agents/`：Agent 接口配置；
- `docs/`：快速上手、案例、FAQ 等；
- `references/`：执行时需要读取的规范或参考；
- `scripts/`：可重复执行的本地工具；
- `tests/`：至少一套不依赖真实用户数据的 smoke test。

Skill 不需要为了形式强行拥有所有目录；只有确实需要模板、样例或额外资源时再增加。

## 文档怎么读

| 文档 | 给谁看 | 解决什么问题 |
| --- | --- | --- |
| [新手入门](docs/新手入门.md) | 第一次使用的人 | 先选哪个 Skill、第一句话怎么说 |
| [治理初始化 README](skill/acs-knowledge-governance-bootstrap/README.md) | 初始化/适配用户 | 中文建库、既有库适配、规范与工具安装 |
| [第二大脑 README](skill/acs-second-brain-manager/README.md) | 第二大脑用户 | 能力模型、治理边界与结构 |
| [专项记忆使用说明](skill/acs-second-brain-manager/docs/project-memory-guide.md) | 长期项目用户 | 跨对话接手、维护、归档与公开前脱敏 |
| [视频提取 README](skill/acs-video-script-extractor/README.md) | 视频转写用户 | 离线流程、环境要求与交付内容 |
| 各 Skill 的 `SKILL.md` | Agent / 开发者 | 实际执行协议、边界和验收标准 |
| 各 Skill 的 `docs/` | 实际使用者 | Quick Start、案例和 FAQ |

## 仓库原则

```text
一个 Skill 解决一类清晰任务。
先定义边界，再扩展能力。
可重复动作尽量脚本化。
关键过程必须可追溯、可验收。
公开 Skill 不写死开发者个人路径。
原始来源、校对结果和创作结果不要混成一层。
```

如果只是想开始使用，到这里就够了：打开 [新手入门](docs/新手入门.md)，然后把一个真实任务交给 Agent。
