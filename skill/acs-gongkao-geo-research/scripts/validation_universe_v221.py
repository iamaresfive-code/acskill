#!/usr/bin/env python3
"""Backward-compatible v2.2.1 Market Universe evidence gate."""
from __future__ import annotations
from pathlib import Path
from validation_common import Issue
from validation_universe import validate_universe as _validate_core

MAIN_ROLES={"national-benchmark","local-core","local-active","expert-ip","historical"}


def validate_universe(run:Path,meta:dict,issues:list[Issue],require_confirmed:bool):
    universe,ids=_validate_core(run,meta,issues,require_confirmed)
    # New universes built by v2.2.1 contain this column. Old frozen/migrated v2.2 runs remain valid.
    has_gate=any("discovery_evidence_urls" in r for r in universe)
    if require_confirmed and has_gate:
        for r in universe:
            if r.get("universe_status")=="included" and r.get("market_role") in MAIN_ROLES and not (r.get("discovery_evidence_urls") or "").strip():
                issues.append(Issue("error","included-without-discovery-evidence",f"{r.get('canonical_name')} 已进入正式研究但缺可独立核验来源链接"))
    return universe,ids
