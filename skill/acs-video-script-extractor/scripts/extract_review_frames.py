#!/usr/bin/env python3
"""Extract still frames around transcript review points."""

from __future__ import annotations

import argparse
import json
import hashlib
import math
import re
import os
from pathlib import Path
import shutil
import subprocess


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从差异时间点提取视频字幕画面。")
    parser.add_argument("video", type=Path, help="本地视频文件")
    parser.add_argument("review_points", type=Path, help="review-points.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="画面输出目录")
    parser.add_argument("--offsets", default="-0.5,0,0.5", help="相对检查点的抽帧偏移秒数")
    parser.add_argument("--max-points", type=int, default=30, help="最多处理多少个检查点；0 表示全部")
    return parser.parse_args()


def find_ffmpeg() -> str:
    configured = os.environ.get("ACS_FFMPEG")
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return str(path.resolve())
        raise SystemExit(f"ACS_FFMPEG 指向的文件不存在：{path}")
    direct = shutil.which("ffmpeg")
    if direct:
        return direct
    try:
        import imageio_ffmpeg  # type: ignore

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and Path(bundled).is_file():
            return bundled
    except Exception:
        pass
    raise SystemExit("未找到本地 ffmpeg。请先安装 FFmpeg，或设置 ACS_FFMPEG；脚本不会联网安装。")


def select_points(points: list[dict], max_points: int) -> tuple[list[dict], str]:
    if max_points <= 0 or len(points) <= max_points:
        return list(points), "all"
    ranked = sorted(
        points,
        key=lambda item: (-int(item.get("risk_score", 1)), float(item.get("frame_time", 0.0))),
    )[:max_points]
    return sorted(ranked, key=lambda item: float(item.get("frame_time", 0.0))), "risk-first"


def main() -> int:
    args = parse_args()
    video = args.video.expanduser().resolve()
    if not video.is_file():
        raise SystemExit(f"视频不存在：{video}")
    review_path = args.review_points.expanduser().resolve()
    if not review_path.is_file():
        raise SystemExit(f"差异文件不存在：{review_path}")
    data = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("points"), list):
        raise SystemExit("review-points.json 必须包含来源哈希和points列表。")
    def file_hash(path):
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""): h.update(chunk)
        return h.hexdigest()
    expected = data.get("source_sha256")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise SystemExit("差异文件缺少有效来源哈希，拒绝抽帧。")
    if file_hash(video) != expected.lower():
        raise SystemExit("视频与差异文件来源哈希不匹配，拒绝抽帧。")
    media_duration = data.get("duration")
    if type(media_duration) not in (int,float) or not math.isfinite(media_duration) or media_duration <= 0:
        raise SystemExit("差异文件时长无效。")
    points = data["points"]
    ids = set()
    for point in points:
        if not isinstance(point, dict): raise SystemExit("检查点必须是object。")
        point_id = point.get("id")
        if not isinstance(point_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",point_id):
            raise SystemExit("检查点id不是安全标识，拒绝路径分隔符或绝对路径。")
        if point_id in ids: raise SystemExit("检查点id重复。")
        ids.add(point_id)
        if not all(type(point.get(k)) in (int,float) and math.isfinite(point[k]) for k in ("start","end","frame_time")):
            raise SystemExit("检查点时间戳无效。")
        if not 0 <= point["start"] <= point["frame_time"] <= point["end"] <= media_duration + 0.1:
            raise SystemExit("检查点时间戳超出媒体范围。")
        if type(point.get("risk_score",1)) not in (int,float) or not math.isfinite(point.get("risk_score",1)):
            raise SystemExit("检查点风险值无效。")
    offsets = [float(item.strip()) for item in args.offsets.split(",") if item.strip()]
    if not offsets or not all(math.isfinite(x) for x in offsets):
        raise SystemExit("--offsets 必须为有限数值。")
    selected, strategy = select_points(points, args.max_points)
    requested_output = args.output_dir.expanduser().absolute()
    if requested_output.is_symlink(): raise SystemExit("输出目录不能是符号链接。")
    output_dir = requested_output.resolve()
    if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
        raise SystemExit("抽帧目录必须为空或不存在，不覆盖已有画面。")
    ffmpeg = find_ffmpeg() if selected else None
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for point in selected:
        point_id = str(point.get("id", f"Q{len(manifest) + 1:03d}"))
        base_time = float(point.get("frame_time", (float(point["start"]) + float(point["end"])) / 2))
        for index, offset in enumerate(offsets, start=1):
            timestamp = max(0.0, base_time + offset)
            if media_duration is not None and media_duration > 0:
                timestamp = min(timestamp, max(0.0, media_duration - 0.05))
            target = output_dir / f"{point_id}-{index}-{timestamp:.2f}s.png"
            if target.parent.resolve() != output_dir or target.exists() or target.is_symlink():
                raise SystemExit("抽帧目标越界或已存在。")
            command = [
                ffmpeg,
                "-loglevel",
                "error",
                "-n",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(target),
            ]
            completed = subprocess.run(command, check=False)
            if completed.returncode != 0 or not target.is_file():
                raise SystemExit(f"抽帧失败：{point_id} @ {timestamp:.3f}s")
            manifest.append(
                {
                    "review_id": point_id,
                    "timestamp": round(timestamp, 3),
                    "risk_score": point.get("risk_score"),
                    "file": target.name,
                }
            )
    if file_hash(video) != expected.lower():
        raise SystemExit("抽帧期间源视频变化，输出未验收。")
    payload = {
        "source_sha256": expected.lower(),
        "video": str(video),
        "total_review_points": len(points),
        "selected_review_points": len(selected),
        "selection_strategy": strategy,
        "frames": manifest,
    }
    with (output_dir / "frames-manifest.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    omitted = len(points) - len(selected)
    suffix = f"，另有 {omitted} 个低优先级检查点未抽帧" if omitted else ""
    print(f"已生成 {len(manifest)} 张复核画面：{output_dir}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
