# Quick Start

这是 `acs-video-script-extractor` 的最短启动路径。

## 1. 准备环境

确认本机已有：

```bash
python --version
ffmpeg -version
ffprobe -version
```

当前 Python 需要能导入：

```bash
python -c "import faster_whisper; print('ok')"
```

默认还需要本地已经缓存 `large-v3` 与 `medium` 两个模型。Skill 运行时不会自动下载。

如果 `faster-whisper` 在另一个 Python 环境：

```bash
export ACS_TRANSCRIBE_PYTHON="/path/to/python"
```

FFmpeg 不在 PATH 时：

```bash
export ACS_FFMPEG="/path/to/ffmpeg"
export ACS_FFPROBE="/path/to/ffprobe"
```

## 2. 建立独立输出目录

```bash
mkdir -p /path/to/output
```

不要把机器产物直接写回源视频所在文件名，也不要覆盖历史交付。

## 3. 预检媒体

```bash
python scripts/probe_media.py \
  "/path/to/video.mp4" \
  --output-dir "/path/to/output"
```

预检失败就先停，不继续宣称可以完整转写。

## 4. 双模型转写

```bash
python scripts/transcribe_local.py \
  "/path/to/video.mp4" \
  --output-dir "/path/to/output"
```

默认生成 `large-v3` 与 `medium` 两份原始结果。

## 5. 比较差异

```bash
python scripts/compare_transcripts.py \
  "/path/to/output/raw-large-v3.json" \
  "/path/to/output/raw-medium.json" \
  --output-dir "/path/to/output"
```

重点先看 `high` 风险检查点。

## 6. 有可见字幕时抽帧

```bash
python scripts/extract_review_frames.py \
  "/path/to/video.mp4" \
  "/path/to/output/review-points.json" \
  --output-dir "/path/to/output/review-frames"
```

默认最多处理 30 个高优先级检查点。全部处理：

```bash
--max-points 0
```

纯音频或没有成片字幕时跳过。

## 7. 生成三个最终文件

按照 [输出格式](../references/output-format.md) 生成：

```text
逐字稿-校对版.md
文案-还原整理版.md
待确认疑点.md
```

其中“还原文案整理”只负责在不改变原意的前提下清理口头噪声和无意义重复，不等于创作性改写。

## 8. 验收

```bash
python scripts/validate_outputs.py "/path/to/output"
```

脚本会校验不同模型、结果文件、来源哈希及差异文件结构。看到 `PASS｜完整交付有效` 后，还需确认人工校对完成、未确认项保留及完整性警告已说明，才能把任务称为完整完成。

如果只是检查机器阶段：

```bash
python scripts/validate_outputs.py "/path/to/output" --machine-only
```
