#!/usr/bin/env python3
"""Read-only media preflight using local ffprobe and SHA-256."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="只读检查本地音视频，并生成 source-probe.json。")
    parser.add_argument("source", type=Path, help="本地音频或视频文件")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def find_ffprobe() -> str:
    configured = os.environ.get("ACS_FFPROBE")
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return str(path.resolve())
        raise SystemExit(f"ACS_FFPROBE 指向的文件不存在：{path}")
    direct = shutil.which("ffprobe")
    if direct:
        return direct
    raise SystemExit("未找到本地 ffprobe。请先安装 FFmpeg，或设置 ACS_FFPROBE；脚本不会联网安装。")


def compact_stream(stream: dict) -> dict:
    keep = (
        "index",
        "codec_name",
        "codec_long_name",
        "codec_type",
        "profile",
        "width",
        "height",
        "pix_fmt",
        "sample_rate",
        "channels",
        "channel_layout",
        "duration",
        "bit_rate",
        "avg_frame_rate",
    )
    return {key: stream[key] for key in keep if key in stream}


def stamp(seconds: float | None) -> str:
    if seconds is None:
        return "未知"
    total = max(0, int(round(seconds)))
    hours, total = divmod(total, 3600)
    minutes, secs = divmod(total, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"源文件不存在：{source}")

    ffprobe = find_ffprobe()
    completed = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "未知 ffprobe 错误"
        raise SystemExit(f"媒体预检失败：{detail}")
    try:
        probed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ffprobe 输出无法解析：{exc}") from exc

    fmt = probed.get("format") or {}
    streams = probed.get("streams") or []
    if not streams:
        raise SystemExit("媒体文件没有可识别的音视频流。")

    duration = None
    try:
        duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        candidates = []
        for stream in streams:
            try:
                candidates.append(float(stream.get("duration")))
            except (TypeError, ValueError):
                pass
        if candidates:
            duration = max(candidates)

    stat = source.stat()
    payload = {
        "schema_version": 1,
        "source": str(source),
        "source_name": source.name,
        "source_suffix": source.suffix.lower(),
        "source_size": stat.st_size,
        "source_mtime_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        "source_sha256": sha256(source),
        "duration": round(duration, 3) if duration is not None else None,
        "format_name": fmt.get("format_name"),
        "format_long_name": fmt.get("format_long_name"),
        "bit_rate": fmt.get("bit_rate"),
        "streams": [compact_stream(stream) for stream in streams],
        "ffprobe": ffprobe,
    }

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "source-probe.json"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audio_count = sum(1 for stream in streams if stream.get("codec_type") == "audio")
    video_count = sum(1 for stream in streams if stream.get("codec_type") == "video")
    md_lines = [
        "# 源媒体预检",
        "",
        f"- 文件：`{source.name}`",
        f"- 大小：{stat.st_size} bytes",
        f"- SHA-256：`{payload['source_sha256']}`",
        f"- 时长：{stamp(duration)}",
        f"- 格式：{fmt.get('format_long_name') or fmt.get('format_name') or '未知'}",
        f"- 音频流：{audio_count}",
        f"- 视频流：{video_count}",
        "",
        "## 轨道",
        "",
        "| index | 类型 | 编码 | 关键信息 |",
        "| ---: | --- | --- | --- |",
    ]
    for stream in payload["streams"]:
        details = []
        if stream.get("width") and stream.get("height"):
            details.append(f"{stream['width']}×{stream['height']}")
        if stream.get("sample_rate"):
            details.append(f"{stream['sample_rate']} Hz")
        if stream.get("channels"):
            details.append(f"{stream['channels']} ch")
        md_lines.append(
            f"| {stream.get('index', '')} | {stream.get('codec_type', '')} | "
            f"{stream.get('codec_name', '')} | {' / '.join(details) or '—'} |"
        )
    (output_dir / "source-probe.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(f"预检完成：{json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
