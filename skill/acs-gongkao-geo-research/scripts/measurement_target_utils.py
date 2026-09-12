#!/usr/bin/env python3
"""Shared Measurement Target helpers.

Entity-level targets use institution/ip/both. For migrated AI-emergent rows,
`reviewed_measurement_target` is retained as audit provenance and must match the canonical
`measurement_target` after review. Downstream readers still prefer the reviewed field when present
so pre-closure legacy runs can be inspected without mutating raw evidence.
"""
from __future__ import annotations
import csv
from pathlib import Path

VALID_ENTITY_TARGETS={"institution","ip","both"}
VALID_QUERY_TARGETS={"institution","ip"}


def rcsv(path:Path):
    if not path.is_file():return []
    with path.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def expanded_target(value:str)->list[str]:
    t=str(value or "").strip().lower()
    if t=="both":return ["institution","ip"]
    return [t] if t in VALID_QUERY_TARGETS else []


def effective_emergent_target(row:dict)->str:
    """Return reviewed target when present; otherwise canonical/legacy registry target."""
    reviewed=str(row.get("reviewed_measurement_target") or "").strip().lower()
    if reviewed:return reviewed
    return str(row.get("measurement_target") or "").strip().lower()


def require_effective_emergent_target(row:dict)->str:
    t=effective_emergent_target(row)
    if t not in VALID_ENTITY_TARGETS:
        raise ValueError(f"AI-emergent {row.get('canonical_name') or row.get('entity_id')} reviewed measurement target 无效")
    return t


def audit_rows(run:Path):
    rows=rcsv(run/"measurement_target_audit.csv")
    return {r.get("entity_id"):r for r in rows if (r.get("entity_id") or "").strip()}
