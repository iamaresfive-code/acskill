# 本地视频逐字稿与文案提取器

当前版本：`v1.2`。本次修复数字符号差异漏检、重复模型及缺失来源信息的验收放行，以及虚拟环境切换丢失依赖的问题。

`acs-video-script-extractor` 是一个面向本地音视频的离线转写与校对 Skill。

它不是简单把 Whisper 跑一遍，而是把**媒体预检、双模型转写、差异定位、字幕画面复核、人工校对、还原文案整理、最终验收**串成一条可追溯流程。

> 原始转写负责保留“模型听到了什么”，校对稿负责说明“最终确认是什么”，还原整理稿负责在不改变原意的前提下，把原话清理成可继续使用的文案。

适合本地 MP4、MOV、M4V、MP3、M4A、WAV 等文件。默认不上传源文件，不调用飞书妙记或其他云端转写服务。

如果你只是第一次使用，先看：

👉 [Quick Start](docs/quick-start.md)

## 这个 Skill 解决什么问题

普通“视频转文字”经常会出现：

- 只跑一个模型，错了也不知道；
- 人名、机构名、数字、日期和否定词最容易误识别；
- 视频明明有成片字幕，却没有利用；
- 逐字稿、整理稿和二次创作混在一起；
- 输出缺段，但仍被当成“完整转写”；
- 中间结果无法追溯，后续不知道为什么改成这个词；
- 本地工具写死个人路径，换一台机器就失效。

`acs-video-script-extractor` 把这些问题拆成一套明确的验证流程。

## 核心流程

```text
本地音视频
   ↓
只读媒体预检（ffprobe + SHA-256）
   ↓
large-v3 + medium 双模型离线转写
   ↓
全文差异对齐与风险分级
   ↓
高风险时间点字幕抽帧复核（视频可用时）
   ↓
逐字稿-校对版.md
   ↓
文案-还原整理版.md
   ↓
待确认疑点.md
   ↓
完整性验收
```

## 默认交付

一次完整任务默认包含：

### 机器产物

- `source-probe.json` / `source-probe.md`：源媒体元数据、轨道、时长、SHA-256；
- `run-manifest.json`：转写设置、模型结果与失败记录；
- `raw-large-v3.json`；
- `raw-large-v3-timestamped.txt`；
- `raw-medium.json`；
- `raw-medium-timestamped.txt`；
- `review-points.json` / `review-points.md`：双模型真实差异与风险分级；
- `review-frames/`：需要时从高风险时间点抽出的字幕画面。

### 最终交付

- `逐字稿-校对版.md`：尽量忠实保留原话，记录实质校正依据；
- `文案-还原整理版.md`：在不改变原意的前提下，只清理口头停顿、无意义重复和拍摄口令，不新增观点；
- `待确认疑点.md`：只保留仍影响事实、身份或含义的未确认项。

创作性改写、标题、短视频改稿等属于下一层任务，必须和来源稿分开。

## 风险复核机制

`compare_transcripts.py` 不只输出“哪里不一样”，还会给差异点打风险分：

- 数字 / 日期差异：高风险；
- 否定词差异：高风险；
- 一侧缺文：高风险；
- 英文 / 专名候选：提高优先级；
- 普通文字差异：保留为常规检查点。

当差异点很多时，`extract_review_frames.py` 默认优先抽取高风险检查点，而不是机械只取前 30 个。`--max-points 0` 可以处理全部检查点。

## 环境要求

### 必需

- Python 3；
- [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper)；
- FFmpeg，且本机能调用 `ffmpeg` 与 `ffprobe`；
- 本地已经缓存至少两个 Whisper 模型，默认 `large-v3` 与 `medium`。

Skill 执行过程中不会自动联网安装依赖，也不会自动下载模型。

### 一次性环境准备示例

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install faster-whisper
```

macOS 可自行安装 FFmpeg：

```bash
brew install ffmpeg
```

模型首次准备需要在你允许联网的环境中自行完成。之后本 Skill 使用 `local_files_only=True` 和 `HF_HUB_OFFLINE=1` 执行本地转写。

## 可移植配置

本 Skill 不依赖开发者个人目录。

如当前 Python 不是安装了 `faster-whisper` 的环境，可以设置：

```bash
export ACS_TRANSCRIBE_PYTHON="/path/to/python"
```

FFmpeg / ffprobe 不在 PATH 时可以设置：

```bash
export ACS_FFMPEG="/path/to/ffmpeg"
export ACS_FFPROBE="/path/to/ffprobe"
```

`extract_review_frames.py` 还会兼容本地已安装的 `imageio-ffmpeg`，但不会联网下载任何二进制。

## 最短使用方式

```text
请使用 acs-video-script-extractor 处理这个本地视频。
全程离线，先做双模型转写，再校对字幕画面，最后给我完整逐字稿、还原整理文案和待确认疑点。
```

脚本执行顺序见 [Quick Start](docs/quick-start.md)。

## 适用范围

适合：

- 课程录屏；
- 访谈；
- 会议录像；
- 短视频原片；
- 本地音频；
- 需要核对字幕、人名、数字和专名的内容提取。

不负责：

- 主动寻找、破解或下载网络视频；
- 把源视频上传云端转写；
- 默认把结果写入第二大脑或其他知识库；
- 把“还原文案整理”直接改成更有传播力的创作稿；
- 在关键事实无法确认时自行猜答案。

如果用户给的是网络链接，应先通过用户允许的其他下载 / ingest 流程得到本地文件，再进入本 Skill。

## 文件结构

```text
acs-video-script-extractor/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── docs/
│   ├── quick-start.md
│   ├── examples.md
│   └── faq.md
├── references/
│   └── output-format.md
├── scripts/
│   ├── probe_media.py
│   ├── transcribe_local.py
│   ├── compare_transcripts.py
│   ├── extract_review_frames.py
│   └── validate_outputs.py
└── tests/
    └── test_v1.py
```

## 设计原则

```text
先预检，再转写。
双模型一致，不等于事实正确。
高风险差异优先复核。
原始转写不可冒充校对稿。
还原整理不可冒充创作稿。
无法确认就明确待确认，不猜。
没有完整验收，就不宣称“已完成”。
```
