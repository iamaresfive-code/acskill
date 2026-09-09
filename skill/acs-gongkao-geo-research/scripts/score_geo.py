#!/usr/bin/env python3
"""计算固定五维公考 GEO 分数，并可从 v2 查询日志派生命中指标。"""

from __future__ import annotations

import argparse
import csv
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
TRUE_VALUES = {"1", "true", "yes", "y", "是"}


class ScoreError(ValueError):
    """评分输入无效时抛出。"""


def tier_for(total: float) -> str:
    if total >= 85: return "S"
    if total >= 80: return "A+"
    if total >= 70: return "A"
    if total >= 65: return "A-"
    if total >= 60: return "B+"
    if total >= 50: return "B"
    if total >= 45: return "B-"
    return "C"


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoreError(f"{field} 必须是数字，不能是 {type(value).__name__}")
    value = float(value)
    if not math.isfinite(value):
        raise ScoreError(f"{field} 必须是有限数值")
    return value


def score_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ScoreError("每条评分记录必须是 JSON 对象")
    normalized: dict[str, float] = {}
    for field, maximum in WEIGHTS.items():
        if field not in record:
            raise ScoreError(f"缺少必需字段：{field}")
        value = _number(record[field], field)
        if value < 0 or value > maximum:
            raise ScoreError(f"{field} 必须在 0 到 {maximum} 之间；当前值为 {value:g}")
        normalized[field] = value
    total = round(sum(normalized.values()), 4)
    result = dict(record)
    result.update(normalized)
    result["total"] = int(total) if total.is_integer() else total
    result["tier"] = tier_for(total)
    return result


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ScoreError(f"缺少 {path.name}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def derive_query_metrics(run_dir: Path) -> dict[str, dict[str, int]]:
    """只让 generic + measurement + sampled 进入泛词分母与命中。"""
    queries = _read_csv(run_dir / "queries.csv")
    results = _read_csv(run_dir / "query_results.csv")
    query_map = {row.get("query_id", "").strip(): row for row in queries}
    measurement_ids = {
        query_id for query_id, row in query_map.items()
        if row.get("query_type", "").strip().lower() == "generic"
        and row.get("query_purpose", "").strip().lower() == "measurement"
        and row.get("status", "sampled").strip().lower() == "sampled"
    }
    metrics: dict[str, dict[str, set[str]]] = {}
    for row in results:
        if row.get("matched", "").strip().lower() not in TRUE_VALUES:
            continue
        entity_id = row.get("entity_id", "").strip()
        query_id = row.get("query_id", "").strip()
        if not entity_id or query_id not in query_map:
            continue
        item = metrics.setdefault(entity_id, {"generic": set(), "brand": set()})
        query = query_map[query_id]
        if query_id in measurement_ids and row.get("counts_as_measurement_hit", "").strip().lower() in TRUE_VALUES:
            item["generic"].add(query_id)
        if query.get("query_type", "").strip().lower() == "brand" and query.get("query_purpose", "").strip().lower() == "verification":
            item["brand"].add(query_id)
    denominator = len(measurement_ids)
    entity_ids = set(metrics)
    return {
        entity_id: {
            "generic_hits": len(metrics.get(entity_id, {}).get("generic", set())),
            "generic_queries": denominator,
            "brand_hits": len(metrics.get(entity_id, {}).get("brand", set())),
        }
        for entity_id in entity_ids
    }


def calculate(payload: Any, metrics: dict[str, dict[str, int]] | None = None, generic_queries: int = 0) -> Any:
    records = payload if isinstance(payload, list) else [payload]
    if not all(isinstance(item, dict) for item in records):
        raise ScoreError("输入必须是一个 JSON 对象或 JSON 对象列表")
    output = []
    for item in records:
        merged = dict(item)
        entity_id = str(merged.get("entity_id", "")).strip()
        if metrics is not None:
            if not entity_id:
                raise ScoreError("使用 --run-dir 时每条记录必须包含 entity_id")
            merged.update(metrics.get(entity_id, {"generic_hits": 0, "generic_queries": generic_queries, "brand_hits": 0}))
        output.append(score_record(merged))
    return output if isinstance(payload, list) else output[0]


def load_payload(path: str | None) -> Any:
    text = Path(path).read_text(encoding="utf-8") if path and path != "-" else sys.stdin.read()
    if not text.strip():
        raise ScoreError("没有收到 JSON 输入")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScoreError(f"JSON 无效，第 {exc.lineno} 行第 {exc.colno} 列：{exc.msg}") from exc


def self_test() -> None:
    sample = {"institution": "示例机构", "entity_id": "I001", "query_coverage": 24, "entity_clarity": 20, "external_diversity": 13, "concept_ownership": 11, "freshness": 8}
    result = score_record(sample)
    assert result["total"] == 76 and result["tier"] == "A"
    for total, expected in [(100,"S"),(85,"S"),(84,"A+"),(80,"A+"),(79,"A"),(70,"A"),(69,"A-"),(65,"A-"),(64,"B+"),(60,"B+"),(59,"B"),(50,"B"),(49,"B-"),(45,"B-"),(44,"C"),(0,"C")]:
        assert tier_for(total) == expected
    for invalid in [{**sample,"query_coverage":31},{**sample,"freshness":-1},{**sample,"entity_clarity":True}]:
        try: score_record(invalid)
        except ScoreError: continue
        raise AssertionError(f"错误地接受了无效记录：{invalid}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据 JSON 计算公考 GEO 五维总分与等级。")
    parser.add_argument("input", nargs="?", help="JSON 文件；使用 - 或省略时从标准输入读取")
    parser.add_argument("--run-dir", type=Path, help="v2 运行目录；从 queries.csv 和 query_results.csv 派生命中指标")
    parser.add_argument("--pretty", action="store_true", help="美化 JSON 输出")
    parser.add_argument("--self-test", action="store_true", help="运行内置评分测试")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.self_test:
            self_test(); print("score_geo 自测：通过"); return 0
        metrics = derive_query_metrics(args.run_dir) if args.run_dir else None
        denominator = 0
        if args.run_dir:
            queries = _read_csv(args.run_dir / "queries.csv")
            denominator = sum(row.get("query_type", "").lower() == "generic" and row.get("query_purpose", "").lower() == "measurement" and row.get("status", "sampled").lower() == "sampled" for row in queries)
        result = calculate(load_payload(args.input), metrics, denominator)
    except (OSError, ScoreError, AssertionError) as exc:
        print(f"score_geo：错误：{exc}", file=sys.stderr); return 2
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
