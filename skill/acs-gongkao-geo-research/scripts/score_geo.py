#!/usr/bin/env python3
"""Calculate the fixed five-dimension gongkao GEO score and tier."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


WEIGHTS = {
    "query_coverage": 30,
    "entity_clarity": 25,
    "external_diversity": 20,
    "concept_ownership": 15,
    "freshness": 10,
}


class ScoreError(ValueError):
    """Raised when score input is invalid."""


def tier_for(total: float) -> str:
    if total >= 85:
        return "S"
    if total >= 80:
        return "A+"
    if total >= 70:
        return "A"
    if total >= 65:
        return "A-"
    if total >= 60:
        return "B+"
    if total >= 50:
        return "B"
    if total >= 45:
        return "B-"
    return "C"


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoreError(f"{field} must be a number, not {type(value).__name__}")
    value = float(value)
    if not math.isfinite(value):
        raise ScoreError(f"{field} must be finite")
    return value


def score_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ScoreError("each score record must be a JSON object")

    normalized: dict[str, float] = {}
    for field, maximum in WEIGHTS.items():
        if field not in record:
            raise ScoreError(f"missing required field: {field}")
        value = _number(record[field], field)
        if value < 0 or value > maximum:
            raise ScoreError(f"{field} must be between 0 and {maximum}; got {value:g}")
        normalized[field] = value

    total = round(sum(normalized.values()), 4)
    result = dict(record)
    result.update(normalized)
    result["total"] = int(total) if total.is_integer() else total
    result["tier"] = tier_for(total)
    return result


def calculate(payload: Any) -> Any:
    if isinstance(payload, list):
        return [score_record(item) for item in payload]
    if isinstance(payload, dict):
        return score_record(payload)
    raise ScoreError("input must be one JSON object or a list of JSON objects")


def load_payload(path: str | None) -> Any:
    if path and path != "-":
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ScoreError(f"cannot read {path}: {exc}") from exc
    else:
        text = sys.stdin.read()
    if not text.strip():
        raise ScoreError("no JSON input received")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScoreError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def self_test() -> None:
    sample = {
        "institution": "示例机构",
        "query_coverage": 24,
        "entity_clarity": 20,
        "external_diversity": 13,
        "concept_ownership": 11,
        "freshness": 8,
    }
    result = score_record(sample)
    assert result["total"] == 76 and result["tier"] == "A"

    boundaries = [
        (100, "S"), (85, "S"), (84, "A+"), (80, "A+"),
        (79, "A"), (70, "A"), (69, "A-"), (65, "A-"),
        (64, "B+"), (60, "B+"), (59, "B"), (50, "B"),
        (49, "B-"), (45, "B-"), (44, "C"), (0, "C"),
    ]
    for total, expected in boundaries:
        assert tier_for(total) == expected, (total, expected)

    invalid_records = [
        {**sample, "query_coverage": 31},
        {**sample, "freshness": -1},
        {**sample, "entity_clarity": True},
        {key: value for key, value in sample.items() if key != "concept_ownership"},
    ]
    for invalid in invalid_records:
        try:
            score_record(invalid)
        except ScoreError:
            continue
        raise AssertionError(f"invalid record was accepted: {invalid}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calculate gongkao GEO five-dimension totals and tiers from JSON."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="JSON file containing one score object or a list; use '-' or omit for stdin",
    )
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    parser.add_argument("--self-test", action="store_true", help="run built-in scoring tests")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.self_test:
            self_test()
            print("score_geo self-test: PASS")
            return 0
        payload = load_payload(args.input)
        result = calculate(payload)
    except (ScoreError, AssertionError) as exc:
        print(f"score_geo: ERROR: {exc}", file=sys.stderr)
        return 2

    indent = 2 if args.pretty else None
    print(json.dumps(result, ensure_ascii=False, indent=indent, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
