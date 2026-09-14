---
name: acs-video-script-extractor
description: 从本地视频或音频离线提取完整逐字稿与忠实整理文案，并用双模型差异、风险分级和视频字幕画面辅助校对。用户提供本地 MP4、MOV、M4V、MP3、M4A、WAV 等文件，要求提取文案、转写、生成逐字稿或校对字幕时使用。默认不上传源文件、不调用云端转写；网络视频下载、知识库入库和创作性改写不属于本 Skill 的默认职责。
metadata:
  version: "1.0"
---

# 本地视频逐字稿与文案提取器

当前版本：`v1.0`。

本 Skill 的目标不是“跑一次语音识别”，而是把本地音视频转成**可追溯、可复核、角色分明**的逐字稿与忠实整理文案。

核心原则：

1. **Local First**：源文件默认不上传，执行链路优先本地完成。
2. **Dual ASR**：默认至少两个本地模型交叉识别，不能把单模型结果冒充双模型校对。
3. **Risk-first Review**：数字、日期、否定词、一侧缺文和专名候选优先复核。
4. **Evidence Boundary**：模型原始转写、校对逐字稿、忠实整理稿、创作稿严格分层。
5. **No Guessing**：关键身份、数字、专名和事实无法确认时明确留待确认，不猜。

## 适用范围

适合：

- 本地 MP4 / MOV / M4V / MP3 / M4A / WAV 等音视频；
- 用户要求完整逐字稿、视频文案提取、字幕校对、访谈转写；
- 需要重点核对人名、机构名、数字、日期、英文和否定表达的内容。

不负责：

- 主动寻找、破解或下载网络视频；
- 默认上传飞书妙记或其他云端转写服务；
- 默认将结果写入 Obsidian / 第二大脑 / 其他知识库；
- 在来源交付尚未完成前直接做传播性改写；
- 对无法确认的关键内容自行补全。

用户只有网络链接时，应先通过用户允许的其他 ingest / 下载流程获得本地媒体，再进入本 Skill。

## 默认交付

用户没有另行限定时，同时交付：

### 机器产物

1. `source-probe.json` / `source-probe.md`；
2. 双模型原始转写 JSON 与带时间戳文本；
3. `review-points.json` / `review-points.md`；
4. 视频存在可见字幕且需要复核时的 `review-frames/`。

### 最终交付

1. `逐字稿-校对版.md`：尽量忠实保留原话，标明实质校正和待确认项；
2. `文案-忠实整理版.md`：删除明显口头停顿、无意义重复和拍摄口令，但不新增观点、不重排论证；
3. `待确认疑点.md`：只列仍未可靠解决、且会影响事实、身份或含义的疑点。

用户明确要求优化、压缩、拟标题或生成发布稿时，在上述来源交付完成后再处理，并另建创作稿，不覆盖来源稿。

输出目录优先使用用户明确指定的位置；用户未指定时，在当前任务可写目录下创建独立输出文件夹。不得猜测开发者个人路径或历史用户路径。

## 必须遵守的边界

- 仅处理用户有权访问的本地文件。
- 源媒体只读，不覆盖、不改写。
- 执行阶段不自动联网安装依赖，不自动下载 Whisper 模型。
- 不因文件扩展名正确就假定媒体有效，必须先做预检。
- 双模型一致不等于事实正确。人名、机构名、地名、数字、日期、身份、引语和敏感评价仍需结合字幕、上下文或用户确认。
- 视频没有可见字幕、纯音频或画面不足以辨认时，跳过字幕复核并明确说明。
- 原始模型结果不可手工覆盖；人工校正写入单独的最终文档。
- 用户随后要求入库时，再加载对应知识库 Skill；本 Skill 本身不修改知识库结构、索引或治理状态。

## 执行流程

### 1. 只读媒体预检

先运行：

```bash
python scripts/probe_media.py \
  "/absolute/path/video.mp4" \
  --output-dir "/absolute/path/output"
```

必须确认并记录：

- 绝对路径、文件名、扩展名、字节数、修改时间、SHA-256；
- 媒体时长；
- 音频轨、视频轨与主要编码；
- 媒体是否可被 ffprobe 正常读取；
- 是否存在视频轨，以及是否能看到成片字幕。

如果媒体预检失败，停止，不把后续结果宣称为完整转写。

### 2. 本地双模型转写

运行：

```bash
python scripts/transcribe_local.py \
  "/absolute/path/video.mp4" \
  --output-dir "/absolute/path/output"
```

默认：

- `faster-whisper`；
- `large-v3` + `medium`；
- 中文；
- CPU `int8`；
- VAD；
- `local_files_only=True`；
- `HF_HUB_OFFLINE=1`。

运行环境查找顺序：

1. 当前 Python；
2. `ACS_TRANSCRIBE_PYTHON` 指定的环境；
3. Skill / 仓库附近的 `.venv`；
4. PATH 中可用的 Python。

任何候选环境都不能静默联网安装依赖。模型未缓存时停止并说明。

长视频转写应保留进度输出。单个模型完成后立即保存结果和 manifest；第二模型失败时，保留已完成产物，同时明确双模型流程未完成。

### 3. 生成差异检查点与风险分级

```bash
python scripts/compare_transcripts.py \
  "/absolute/path/output/raw-large-v3.json" \
  "/absolute/path/output/raw-medium.json" \
  --output-dir "/absolute/path/output"
```

差异至少检查：

- 数字 / 日期；
- 否定词；
- 英文 / 专名候选；
- 一侧缺句、重复、截断；
- 普通文字差异；
- 结尾补录、插播和画面切换处是否漏段。

`review-points.json` 只是复核入口，不自动决定哪个模型正确。

### 4. 视频字幕画面复核

仅当存在视频轨且成片有可见字幕时执行：

```bash
python scripts/extract_review_frames.py \
  "/absolute/path/video.mp4" \
  "/absolute/path/output/review-points.json" \
  --output-dir "/absolute/path/output/review-frames"
```

默认最多选 30 个检查点，但选择策略是**风险优先**，不是简单截取前 30 个。要处理全部检查点可使用：

```bash
--max-points 0
```

逐张查看字幕与画面。一个时间点字幕未完整出现时，检查同一检查点的前后帧。字幕本身也可能有错，因此仍须结合声音、上下文和用户确认。

纯音频或无字幕视频跳过此步骤，不把“未抽帧”视为失败。

### 5. 编写校对稿与忠实整理稿

按 [输出格式](references/output-format.md) 生成三个最终文件。

- 校对稿保留原叙述顺序和有意义的语气，不为了顺滑而改变立场。
- 忠实整理稿只清理口头噪声、重复和拍摄口令；保留原事实边界、情绪、举例和论证关系。
- 实质校正必须能追溯到时间戳、字幕画面、上下文或用户确认。
- 无法确认的词使用明确占位，例如 `[人名待确认｜02:13]`，并同步写入疑点清单。
- 不要求把标点、普通断句和不改变含义的语气词调整全部写入“校正记录”。

### 6. 完整验收

最终运行：

```bash
python scripts/validate_outputs.py "/absolute/path/output"
```

完整验收要求：

- 存在 `source-probe.json`；
- 至少两个模型的原始结果均存在且可解析；
- 转写结果、probe 和 review points 的源文件哈希一致；
- 时间戳基本单调，媒体时长差异有明确警告；
- 已执行双模型差异比较；
- `逐字稿-校对版.md`、`文案-忠实整理版.md`、`待确认疑点.md` 均存在且非空；
- 重要未确认项没有被写成确定事实。

只想检查机器产物时可以使用：

```bash
python scripts/validate_outputs.py "/absolute/path/output" --machine-only
```

如果仅完成单模型转写、缺少预检、缺少差异比较、最终三个 Markdown 不完整或存在未说明缺段，不得称为完整交付。

## 最终回复

向用户交付时至少说明：

- 是否完成双模型转写；
- 是否执行字幕画面复核，以及跳过原因（如有）；
- 最终三个文件在哪里；
- 是否仍有待确认疑点；
- 是否存在完整性警告。

不要只说“已经提取好了”。

## 资源

- [Quick Start](docs/quick-start.md)：最短运行路径。
- [使用案例](docs/examples.md)：常见任务怎么说、会得到什么。
- [常见问题](docs/faq.md)：环境、隐私、模型和边界说明。
- [输出格式](references/output-format.md)：最终三个 Markdown 的结构与边界。
- `scripts/probe_media.py`：媒体只读预检。
- `scripts/transcribe_local.py`：离线双模型转写。
- `scripts/compare_transcripts.py`：全文差异对齐与风险分级。
- `scripts/extract_review_frames.py`：按风险优先从检查点抽取字幕画面。
- `scripts/validate_outputs.py`：校验机器产物与最终交付完整性。
