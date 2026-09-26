#!/usr/bin/env python3
"""Align two ASR texts globally and map meaningful differences back to time."""

from __future__ import annotations

import argparse
from difflib import SequenceMatcher
import json
import math
from pathlib import Path
import re
import statistics
import unicodedata

NEGATIONS = ("不", "没", "无", "未", "非", "否", "不是", "没有", "不能", "不会")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="全文对齐两份转写并生成带时间戳的差异检查点。")
    parser.add_argument("first", type=Path, help="第一份 raw-*.json")
    parser.add_argument("second", type=Path, help="第二份 raw-*.json")
    parser.add_argument("--output-dir", type=Path, required=True, help="输出目录")
    parser.add_argument("--context-chars", type=int, default=18, help="差异两侧保留的上下文字数")
    parser.add_argument("--merge-gap-seconds", type=float, default=2.0, help="相邻差异合并间隔")
    return parser.parse_args()


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {
            "model": path.stem,
            "duration": max((float(x["end"]) for x in data), default=0),
            "segments": data,
        }
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        raise SystemExit(f"无法识别转写 JSON：{path}")
    return data


def keep_char(char: str) -> bool:
    return char.isalnum() or "\u4e00" <= char <= "\u9fff"


def comparison_chars(text: str) -> list[str]:
    """Ignore prose punctuation, but retain symbols that change numeric meaning."""
    text = unicodedata.normalize("NFKC", text).lower().replace("−", "-")
    chars = []
    for index, char in enumerate(text):
        before = text[:index].rstrip()
        after = text[index + 1:].lstrip()
        left_digit = bool(before) and before[-1].isdigit()
        right_digit = bool(after) and after[0].isdigit()
        numeric_symbol = (
            (char == "." and right_digit)
            or (char in "+-" and right_digit)
            or (char in "%‰" and left_digit)
        )
        if keep_char(char) or numeric_symbol:
            chars.append(char)
    return chars


def flatten(segments: list[dict]) -> tuple[str, list[float]]:
    chars: list[str] = []
    times: list[float] = []
    for segment in segments:
        start = float(segment["start"])
        end = float(segment["end"])
        kept = comparison_chars(str(segment.get("text", "")))
        count = len(kept)
        for index, char in enumerate(kept):
            chars.append(char)
            times.append(start + (index + 0.5) * (end - start) / max(1, count))
    return "".join(chars), times


def nearby_time(times: list[float], start: int, end: int) -> list[float]:
    values = times[start:end]
    if values:
        return values
    if times:
        return [times[min(max(start, 0), len(times) - 1)]]
    return [0.0]


def stamp(seconds: float) -> str:
    value = max(0, int(round(seconds)))
    hours, value = divmod(value, 3600)
    minutes, secs = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def escape_table(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def build_raw_points(first_text: str, second_text: str, first_times: list[float], second_times: list[float]) -> list[dict]:
    matcher = SequenceMatcher(None, first_text, second_text, autojunk=False)
    raw_points = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        time_values = nearby_time(first_times, i1, i2) + nearby_time(second_times, j1, j2)
        raw_points.append(
            {
                "start": max(0.0, min(time_values) - 0.8),
                "end": max(time_values) + 0.8,
                "frame_time": statistics.median(time_values),
                "first_start": i1,
                "first_end": i2,
                "second_start": j1,
                "second_end": j2,
                "tags": [tag],
            }
        )
    return raw_points


def merge_points(points: list[dict], gap: float) -> list[dict]:
    merged: list[dict] = []
    for point in points:
        if merged and point["start"] <= merged[-1]["end"] + gap:
            previous = merged[-1]
            previous["end"] = max(previous["end"], point["end"])
            previous["frame_time"] = (previous["frame_time"] + point["frame_time"]) / 2
            previous["first_start"] = min(previous["first_start"], point["first_start"])
            previous["first_end"] = max(previous["first_end"], point["first_end"])
            previous["second_start"] = min(previous["second_start"], point["second_start"])
            previous["second_end"] = max(previous["second_end"], point["second_end"])
            previous["tags"].extend(point["tags"])
        else:
            merged.append(dict(point))
    return merged


def risk(first_diff: str, second_diff: str, tags: list[str]) -> tuple[int, list[str]]:
    score = 1
    reasons = ["文字差异"]
    number_pattern = r"(?:\d+(?:\.\d+)?)|[零〇一二两三四五六七八九十百千万亿点]+"
    first_numbers = re.findall(number_pattern, first_diff)
    second_numbers = re.findall(number_pattern, second_diff)
    if first_numbers != second_numbers or re.search(r"[.+%‰-]", first_diff + second_diff):
        score += 5
        reasons.insert(0, "数字/日期风险")
    if re.search(r"[a-zA-Z]", first_diff + second_diff):
        score += 3
        reasons.append("英文/专名候选")
    if "delete" in tags or "insert" in tags:
        score += 4
        reasons.append("一侧缺文")
    first_neg = [token for token in NEGATIONS if token in first_diff]
    second_neg = [token for token in NEGATIONS if token in second_diff]
    if first_neg != second_neg:
        score += 5
        reasons.insert(0, "否定词风险")
    return score, list(dict.fromkeys(reasons))


def main() -> int:
    args = parse_args()
    first = load(args.first)
    second = load(args.second)
    first_hash = first.get("source_sha256")
    second_hash = second.get("source_sha256")
    if first_hash and second_hash and first_hash != second_hash:
        raise SystemExit("两份转写来自不同源文件，拒绝比较。")

    first_text, first_times = flatten(first["segments"])
    second_text, second_times = flatten(second["segments"])
    if not first_text or not second_text:
        raise SystemExit("至少一份转写没有有效文字。")
    raw_points = build_raw_points(first_text, second_text, first_times, second_times)
    merged = merge_points(raw_points, max(0.0, args.merge_gap_seconds))
    context = max(0, args.context_chars)
    duration = max(float(first.get("duration", 0)), float(second.get("duration", 0)))
    if not math.isfinite(duration) or duration <= 0:
        raise SystemExit("转写时长无效。")
    probe_path = args.output_dir.expanduser() / "source-probe.json"
    if probe_path.is_file():
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
        if not isinstance(probe,dict) or probe.get("source_sha256") not in (first_hash,second_hash) or not probe.get("source_sha256"):
            raise SystemExit("媒体预检与转写来源不一致。")
        value = probe.get("duration")
        if type(value) not in (int,float) or not math.isfinite(value) or value <= 0:
            raise SystemExit("媒体预检时长无效。")
        duration = value
    points = []
    for index, point in enumerate(merged, start=1):
        i1, i2 = point["first_start"], point["first_end"]
        j1, j2 = point["second_start"], point["second_end"]
        first_diff = first_text[i1:i2]
        second_diff = second_text[j1:j2]
        risk_score, reasons = risk(first_diff, second_diff, point["tags"])
        priority = "high" if risk_score >= 6 else "medium" if risk_score >= 4 else "normal"
        points.append(
            {
                "id": f"Q{index:03d}",
                "start": round(min(duration,max(0,point["start"])), 3),
                "end": round(min(duration,max(0,point["end"])), 3),
                "frame_time": round(min(duration,max(0,point["frame_time"])), 3),
                "risk_score": risk_score,
                "priority": priority,
                "first_model": first.get("model", args.first.stem),
                "second_model": second.get("model", args.second.stem),
                "first_diff": first_diff,
                "second_diff": second_diff,
                "first_context": first_text[max(0, i1 - context) : min(len(first_text), i2 + context)],
                "second_context": second_text[max(0, j1 - context) : min(len(second_text), j2 + context)],
                "reasons": reasons,
            }
        )

    overall_similarity = SequenceMatcher(None, first_text, second_text, autojunk=False).ratio()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 3,
        "source_sha256": first_hash or second_hash,
        "duration": duration,
        "overall_similarity": round(overall_similarity, 6),
        "points": points,
    }
    (output_dir / "review-points.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# 双模型差异检查点",
        "",
        f"- 第一模型：{first.get('model', args.first.stem)}",
        f"- 第二模型：{second.get('model', args.second.stem)}",
        f"- 全文相似度：{overall_similarity:.3f}",
        f"- 检查点：{len(points)}",
        "",
        "| 编号 | 时间点 | 风险 | 原因 | 第一模型差异 | 第二模型差异 | 上下文 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for point in points:
        lines.append(
            f"| {point['id']} | {stamp(point['frame_time'])} | {point['priority']} / {point['risk_score']} | "
            f"{escape_table('、'.join(point['reasons']))} | {escape_table(point['first_diff'] or '∅')} | "
            f"{escape_table(point['second_diff'] or '∅')} | {escape_table(point['first_context'])} |"
        )
    (output_dir / "review-points.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成 {len(points)} 个真实文字差异检查点：{output_dir / 'review-points.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
