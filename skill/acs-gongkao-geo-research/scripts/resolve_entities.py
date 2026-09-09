#!/usr/bin/env python3
"""按已核验别名做确定性实体归并；不进行模糊猜测。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


def normalize_name(value: str) -> str:
    return re.sub(r"[\s·•・（）()\-—_]+", "", value).casefold()


def split_values(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[|｜;,，；]", value or "") if part.strip()]


def build_alias_index(rows: list[dict[str, str]]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for row in rows:
        entity_id = row.get("entity_id", "").strip()
        names = [row.get("canonical_name", ""), row.get("legal_name", ""), *split_values(row.get("aliases", "")), *split_values(row.get("former_names", ""))]
        for name in names:
            key = normalize_name(name)
            if key and entity_id:
                index.setdefault(key, set()).add(entity_id)
    return index


def resolve_name(name: str, index: dict[str, set[str]]) -> dict[str, object]:
    matches = sorted(index.get(normalize_name(name), set()))
    if len(matches) == 1:
        return {"input": name, "status": "resolved", "entity_id": matches[0]}
    if len(matches) > 1:
        return {"input": name, "status": "ambiguous", "entity_ids": matches}
    return {"input": name, "status": "unmatched"}


def load_entities(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def self_test() -> None:
    rows = [
        {"entity_id":"I001","canonical_name":"津仕教育","aliases":"天津津仕|津仕公考","legal_name":"","former_names":""},
        {"entity_id":"I002","canonical_name":"北学优仕","aliases":"北宋公考","legal_name":"天津北学优仕教育科技有限公司","former_names":""},
    ]
    index = build_alias_index(rows)
    assert resolve_name("天津 津仕", index)["entity_id"] == "I001"
    assert resolve_name("北宋公考", index)["entity_id"] == "I002"
    assert resolve_name("未知机构", index)["status"] == "unmatched"


def main() -> int:
    parser = argparse.ArgumentParser(description="使用 entities.csv 中已核验的别名解析实体名称。")
    parser.add_argument("entities", nargs="?", type=Path)
    parser.add_argument("names", nargs="*")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(); print("resolve_entities 自测：通过"); return 0
    if not args.entities or not args.names:
        parser.error("必须提供 entities.csv 和至少一个待解析名称")
    try:
        index = build_alias_index(load_entities(args.entities))
    except OSError as exc:
        print(f"resolve_entities：错误：{exc}", file=sys.stderr); return 2
    print(json.dumps([resolve_name(name, index) for name in args.names], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
