#!/usr/bin/env python3
"""Validate machine artifacts and final deliverables from the local transcript workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

FINAL_FILES = ("逐字稿-校对版.md", "文案-忠实整理版.md", "待确认疑点.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验视频文案提取工作流产物。")
    parser.add_argument("output_dir", type=Path, help="工作流输出目录")
    parser.add_argument("--machine-only", action="store_true", help="只校验机器产物，不要求最终三个 Markdown")
    return parser.parse_args()


def load_json(path: Path, errors: list[str]) -> dict | None:
    if not path.is_file():
        errors.append(f"缺少 {path.name}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"{path.name} 无法解析：{exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path.name} 顶层必须是 JSON object")
        return None
    return data


def validate_segments(path: Path, expected_hash: str | None) -> tuple[list[str], list[str], float]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path.name} 无法解析：{exc}"], warnings, 0.0
    if expected_hash and data.get("source_sha256") != expected_hash:
        errors.append(f"{path.name} 的源文件哈希与 manifest 不一致")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        return errors + [f"{path.name} 没有有效 segments"], warnings, 0.0
    previous_end = -1.0
    for index, segment in enumerate(segments, start=1):
        try:
            start = float(segment["start"])
            end = float(segment["end"])
        except Exception:
            errors.append(f"{path.name} 第 {index} 段时间戳无效")
            continue
        if start < 0 or end <= start:
            errors.append(f"{path.name} 第 {index} 段起止时间无效")
        if start + 0.05 < previous_end:
            warnings.append(f"{path.name} 第 {index} 段与上一段时间重叠")
        previous_end = max(previous_end, end)
        if not str(segment.get("text", "")).strip():
            warnings.append(f"{path.name} 第 {index} 段文本为空")
    try:
        duration = float(data.get("duration", previous_end))
    except (TypeError, ValueError):
        duration = previous_end
        warnings.append(f"{path.name} duration 无效，改用末段时间")
    if previous_end < max(0, duration - 15):
        warnings.append(f"{path.name} 末段距媒体结尾超过 15 秒，请确认是否为静音或漏段")
    return errors, warnings, duration


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest = load_json(output_dir / "run-manifest.json", errors)
    probe = load_json(output_dir / "source-probe.json", errors)
    if manifest is None:
        manifest = {}
    if probe is None:
        probe = {}

    source_hash = manifest.get("source_sha256")
    if source_hash and probe.get("source_sha256") and source_hash != probe.get("source_sha256"):
        errors.append("source-probe.json 与 run-manifest.json 的源文件哈希不一致")

    results = manifest.get("results", [])
    if not isinstance(results, list):
        errors.append("run-manifest.json 的 results 格式错误")
        results = []
    if len(results) < 2:
        errors.append("少于两份模型转写结果")
    failures = manifest.get("failures", [])
    if failures:
        errors.append(f"manifest 记录了模型失败：{len(failures)} 项")

    durations = []
    for result in results:
        raw_path = output_dir / str(result.get("json", ""))
        text_path = output_dir / str(result.get("timestamped_text", ""))
        if not raw_path.is_file():
            errors.append(f"缺少 {raw_path.name}")
            continue
        if not text_path.is_file() or text_path.stat().st_size == 0:
            errors.append(f"缺少或为空：{text_path.name}")
        item_errors, item_warnings, duration = validate_segments(raw_path, source_hash)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        durations.append(duration)

    if durations and max(durations) - min(durations) > 2:
        warnings.append("两个模型报告的媒体时长相差超过 2 秒")
    try:
        probe_duration = float(probe.get("duration"))
    except (TypeError, ValueError):
        probe_duration = 0.0
    if probe_duration and durations:
        for duration in durations:
            if abs(duration - probe_duration) > 3:
                warnings.append("模型报告时长与 ffprobe 媒体时长相差超过 3 秒")
                break

    review = load_json(output_dir / "review-points.json", errors)
    if review is not None:
        if source_hash and review.get("source_sha256") and review.get("source_sha256") != source_hash:
            errors.append("review-points.json 的源文件哈希与 manifest 不一致")
        if not isinstance(review.get("points", []), list):
            errors.append("review-points.json 的 points 格式错误")

    if not args.machine_only:
        for name in FINAL_FILES:
            path = output_dir / name
            if not path.is_file():
                errors.append(f"缺少最终交付：{name}")
            elif not path.read_text(encoding="utf-8").strip():
                errors.append(f"最终交付为空：{name}")

    for message in errors:
        print(f"ERROR｜{message}")
    for message in warnings:
        print(f"WARN｜{message}")
    if errors:
        print(f"FAIL｜{len(errors)} error，{len(warnings)} warning")
        return 1
    scope = "机器产物" if args.machine_only else "完整交付"
    print(f"PASS｜{scope}有效｜{len(results)} 个模型，{len(warnings)} 个警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
