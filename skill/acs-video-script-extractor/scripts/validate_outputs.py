#!/usr/bin/env python3
"""Validate machine artifacts and final deliverables from the local transcript workflow."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

FINAL_FILES = ("逐字稿-校对版.md", "文案-还原整理版.md", "待确认疑点.md")


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


def check_hash(data: dict, label: str, expected: str | None, errors: list[str]) -> str | None:
    value = data.get("source_sha256")
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        errors.append(f"{label} 缺少有效的 source_sha256")
        return None
    value = value.lower()
    if expected and value != expected:
        errors.append(f"{label} 的源文件哈希与 manifest 不一致")
    return value


def finite_number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def validate_segments(path: Path, expected_hash: str | None, expected_model: str) -> tuple[list[str], list[str], float]:
    errors: list[str] = []
    warnings: list[str] = []
    data = load_json(path, errors)
    if data is None:
        return errors, warnings, 0.0
    check_hash(data, path.name, expected_hash, errors)
    if data.get("model") != expected_model:
        errors.append(f"{path.name} 的 model 与 manifest 不一致")
    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        return errors + [f"{path.name} 没有有效 segments"], warnings, 0.0
    previous_end = -1.0
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict) or not all(
            finite_number(segment.get(key)) for key in ("start", "end")
        ):
            errors.append(f"{path.name} 第 {index} 段时间戳无效")
            continue
        start, end = segment["start"], segment["end"]
        if start < 0 or end <= start:
            errors.append(f"{path.name} 第 {index} 段起止时间无效")
        if start + 0.05 < previous_end:
            warnings.append(f"{path.name} 第 {index} 段与上一段时间重叠")
        previous_end = max(previous_end, end)
        if not str(segment.get("text", "")).strip():
            warnings.append(f"{path.name} 第 {index} 段文本为空")
    duration = data.get("duration")
    if not finite_number(duration) or duration <= 0:
        errors.append(f"{path.name} duration 无效")
        duration = max(0.0, previous_end)
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

    source_hash = check_hash(manifest, "run-manifest.json", None, errors)
    check_hash(probe, "source-probe.json", source_hash, errors)

    results = manifest.get("results", [])
    if not isinstance(results, list):
        errors.append("run-manifest.json 的 results 格式错误")
        results = []
    if len(results) < 2:
        errors.append("少于两份模型转写结果")
    failures = manifest.get("failures", [])
    if not isinstance(failures, list):
        errors.append("run-manifest.json 的 failures 格式错误")
    elif failures:
        errors.append(f"manifest 记录了模型失败：{len(failures)} 项")

    durations = []
    models: set[str] = set()
    raw_paths: set[Path] = set()
    text_paths: set[Path] = set()
    for result in results:
        if not isinstance(result, dict):
            errors.append("manifest 的模型结果必须是 object")
            continue
        model = result.get("model")
        if not isinstance(model, str) or not model.strip():
            errors.append("manifest 的模型名称缺失或无效")
            continue
        if model in models:
            errors.append(f"重复模型：{model}")
        models.add(model)
        if not all(
            isinstance(result.get(key), str) and result[key].strip()
            for key in ("json", "timestamped_text")
        ):
            errors.append(f"{model} 的结果文件路径缺失或无效")
            continue
        raw_path = (output_dir / result["json"]).resolve()
        text_path = (output_dir / result["timestamped_text"]).resolve()
        if raw_path in raw_paths or text_path in text_paths:
            errors.append(f"{model} 重复引用模型结果文件")
        raw_paths.add(raw_path)
        text_paths.add(text_path)
        if not raw_path.is_file():
            errors.append(f"缺少 {raw_path.name}")
            continue
        if not text_path.is_file() or text_path.stat().st_size == 0:
            errors.append(f"缺少或为空：{text_path.name}")
        item_errors, item_warnings, duration = validate_segments(raw_path, source_hash, model)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        durations.append(duration)

    if len(models) < 2:
        errors.append("必须有至少两个不同模型")

    if durations and max(durations) - min(durations) > 2:
        warnings.append("两个模型报告的媒体时长相差超过 2 秒")
    probe_duration = probe.get("duration")
    if not finite_number(probe_duration) or probe_duration <= 0:
        errors.append("source-probe.json duration 无效")
        probe_duration = 0.0
    if probe_duration and durations:
        for duration in durations:
            if abs(duration - probe_duration) > 3:
                warnings.append("模型报告时长与 ffprobe 媒体时长相差超过 3 秒")
                break

    review = load_json(output_dir / "review-points.json", errors)
    if review is not None:
        check_hash(review, "review-points.json", source_hash, errors)
        similarity = review.get("overall_similarity")
        if not finite_number(similarity) or not 0 <= similarity <= 1:
            errors.append("review-points.json overall_similarity 无效")
        review_duration = review.get("duration")
        if not finite_number(review_duration) or review_duration <= 0:
            errors.append("review-points.json duration 无效")
        points = review.get("points")
        if not isinstance(points, list):
            errors.append("review-points.json 的 points 格式错误")
        else:
            for index, point in enumerate(points, start=1):
                if not isinstance(point, dict):
                    errors.append(f"第 {index} 个差异检查点必须是 object")
                    continue
                valid_times = all(
                    finite_number(point.get(key)) for key in ("start", "end", "frame_time")
                )
                if not valid_times or not 0 <= point["start"] <= point["frame_time"] <= point["end"]:
                    errors.append(f"第 {index} 个差异检查点时间戳无效")
                for key in ("id", "first_model", "second_model"):
                    if not isinstance(point.get(key), str) or not point[key].strip():
                        errors.append(f"第 {index} 个差异检查点缺少 {key}")
                first_model, second_model = point.get("first_model"), point.get("second_model")
                if (
                    not isinstance(first_model, str) or not isinstance(second_model, str)
                    or first_model not in models or second_model not in models
                    or first_model == second_model
                ):
                    errors.append(f"第 {index} 个差异检查点模型不匹配")
                if not all(isinstance(point.get(key), str) for key in ("first_diff", "second_diff")):
                    errors.append(f"第 {index} 个差异检查点缺少差异文本")

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
    print(f"PASS｜{scope}有效｜{len(models)} 个模型，{len(warnings)} 个警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
