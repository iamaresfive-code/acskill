#!/usr/bin/env python3
"""Offline dual-model transcription for local audio/video files."""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def candidate_pythons() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("ACS_TRANSCRIBE_PYTHON")
    if configured:
        candidates.append(Path(configured).expanduser())

    skill_root = Path(__file__).resolve().parents[1]
    repo_root = skill_root.parents[1] if len(skill_root.parents) > 1 else skill_root
    for root in (skill_root, repo_root):
        candidates.extend(
            [
                root / ".venv" / "bin" / "python",
                root / ".venv" / "bin" / "python3",
                root / ".venv" / "Scripts" / "python.exe",
            ]
        )
    for name in ("python3", "python"):
        resolved = shutil.which(name)
        if resolved:
            candidates.append(Path(resolved))

    unique: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        key = str(item)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def ensure_runtime() -> None:
    if importlib.util.find_spec("faster_whisper") is not None:
        return
    if os.environ.get("ACS_TRANSCRIPT_REEXEC") == "1":
        raise SystemExit("当前 Python 缺少 faster_whisper，且候选本地环境也不可用。")

    # A venv's interpreter is often a symlink to the base Python. Resolving it
    # loses pyvenv.cfg discovery and can also make distinct environments equal.
    current = Path(sys.executable).absolute()
    for candidate in candidate_pythons():
        if not candidate.is_file():
            continue
        executable = candidate.absolute()
        if executable == current:
            continue
        probe = subprocess.run(
            [str(executable), "-c", "import faster_whisper"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if probe.returncode == 0:
            env = os.environ.copy()
            env["ACS_TRANSCRIPT_REEXEC"] = "1"
            os.execve(str(executable), [str(executable), str(Path(__file__).resolve()), *sys.argv[1:]], env)

    raise SystemExit(
        "未找到包含 faster_whisper 的本地 Python。请在当前环境安装依赖，"
        "或设置 ACS_TRANSCRIBE_PYTHON 指向已有环境；脚本不会联网安装。"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stamp(seconds: float) -> str:
    millis = max(0, round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="使用本地 faster-whisper 双模型转写音视频。")
    parser.add_argument("source", type=Path, help="本地音频或视频文件")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
    parser.add_argument("--models", default="large-v3,medium", help="逗号分隔模型名")
    parser.add_argument("--language", default="zh", help="语言代码，默认 zh")
    parser.add_argument("--device", default="cpu", help="推理设备，默认 cpu")
    parser.add_argument("--compute-type", default="int8", help="计算类型，默认 int8")
    parser.add_argument("--no-vad", action="store_true", help="关闭 VAD 静音过滤")
    parser.add_argument("--progress-segments", type=int, default=50, help="每处理多少段打印一次进度；0 为关闭")
    return parser.parse_args()


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"源文件不存在：{source}")
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    if len(models) < 2:
        raise SystemExit("至少需要两个本地模型，默认 large-v3,medium。")
    if len(set(models)) != len(models):
        raise SystemExit("模型名称不能重复；双模型复核需要不同模型。")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    ensure_runtime()
    from faster_whisper import WhisperModel

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(source)
    manifest_path = output_dir / "run-manifest.json"
    manifest = {
        "schema_version": 2,
        "source": str(source),
        "source_size": source.stat().st_size,
        "source_sha256": source_hash,
        "settings": {
            "models": models,
            "language": args.language,
            "device": args.device,
            "compute_type": args.compute_type,
            "vad_filter": not args.no_vad,
            "local_files_only": True,
        },
        "results": [],
        "failures": [],
    }
    write_manifest(manifest_path, manifest)

    for model_name in models:
        started = time.monotonic()
        print(f"开始本地转写：{model_name}", flush=True)
        model = None
        try:
            model = WhisperModel(
                model_name,
                device=args.device,
                compute_type=args.compute_type,
                local_files_only=True,
            )
            segment_iter, info = model.transcribe(
                str(source), language=args.language, vad_filter=not args.no_vad
            )
            segments = []
            interval = max(0, args.progress_segments)
            for index, segment in enumerate(segment_iter, start=1):
                item = {
                    "start": round(float(segment.start), 3),
                    "end": round(float(segment.end), 3),
                    "text": segment.text.strip(),
                }
                segments.append(item)
                if interval and index % interval == 0:
                    print(
                        f"{model_name} 已处理 {index} 段，当前到 {stamp(item['end'])}",
                        flush=True,
                    )
        except Exception as exc:
            manifest["failures"].append({"model": model_name, "error": str(exc)})
            write_manifest(manifest_path, manifest)
            raise SystemExit(
                f"模型 {model_name} 本地转写失败：{exc}\n"
                "请确认模型已经缓存且本地运行环境可用；脚本不会联网下载模型。"
            ) from exc
        finally:
            if model is not None:
                del model
                gc.collect()

        elapsed = round(time.monotonic() - started, 1)
        slug = model_name.replace("/", "-")
        result = {
            "schema_version": 2,
            "source": str(source),
            "source_sha256": source_hash,
            "model": model_name,
            "language": info.language,
            "language_probability": round(float(info.language_probability), 6),
            "duration": round(float(info.duration), 3),
            "transcription_seconds": elapsed,
            "segments": segments,
        }
        json_path = output_dir / f"raw-{slug}.json"
        text_path = output_dir / f"raw-{slug}-timestamped.txt"
        json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        text_path.write_text(
            "\n".join(
                f"[{stamp(item['start'])} --> {stamp(item['end'])}] {item['text']}"
                for item in segments
            )
            + "\n",
            encoding="utf-8",
        )
        manifest["results"].append(
            {
                "model": model_name,
                "json": json_path.name,
                "timestamped_text": text_path.name,
                "segments": len(segments),
                "duration": result["duration"],
                "transcription_seconds": elapsed,
            }
        )
        write_manifest(manifest_path, manifest)
        print(f"完成：{model_name}，{len(segments)} 段，耗时 {elapsed} 秒", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
