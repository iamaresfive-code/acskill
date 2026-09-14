#!/usr/bin/env python3
"""Extract still frames around transcript review points."""

from __future__ import annotations

import argparse
import json
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
    points = data.get("points", data if isinstance(data, list) else [])
    if not isinstance(points, list):
        raise SystemExit("review-points.json 格式错误。")
    offsets = [float(item.strip()) for item in args.offsets.split(",") if item.strip()]
    if not offsets:
        raise SystemExit("--offsets 至少需要一个数值。")

    selected, strategy = select_points(points, args.max_points)
    try:
        media_duration = float(data.get("duration")) if isinstance(data, dict) and data.get("duration") is not None else None
    except (TypeError, ValueError):
        media_duration = None
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    manifest = []
    for point in selected:
        point_id = str(point.get("id", f"Q{len(manifest) + 1:03d}"))
        base_time = float(point.get("frame_time", (float(point["start"]) + float(point["end"])) / 2))
        for index, offset in enumerate(offsets, start=1):
            timestamp = max(0.0, base_time + offset)
            if media_duration is not None and media_duration > 0:
                timestamp = min(timestamp, max(0.0, media_duration - 0.05))
            target = output_dir / f"{point_id}-{index}-{timestamp:.2f}s.png"
            command = [
                ffmpeg,
                "-loglevel",
                "error",
                "-y",
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
    payload = {
        "video": str(video),
        "total_review_points": len(points),
        "selected_review_points": len(selected),
        "selection_strategy": strategy,
        "frames": manifest,
    }
    (output_dir / "frames-manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    omitted = len(points) - len(selected)
    suffix = f"，另有 {omitted} 个低优先级检查点未抽帧" if omitted else ""
    print(f"已生成 {len(manifest)} 张复核画面：{output_dir}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
