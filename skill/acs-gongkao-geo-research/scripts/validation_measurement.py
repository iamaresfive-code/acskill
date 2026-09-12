#!/usr/bin/env python3
"""Stage 2.4 compatibility wrapper around the v2.2 measurement validator core.

The core keeps the mature v2.2 validation surface. This wrapper closes the resolved AI-emergent
entity-target contract: resolved emergents may canonically be institution/ip/both; both expands to
two metric channels. Unresolved emergents remain single-target and never enter formal metrics.
"""
from __future__ import annotations
import csv
from pathlib import Path
from validation_common import Issue,VALID_QUERY_TARGETS
from measurement_target_utils import VALID_ENTITY_TARGETS,expanded_target,effective_emergent_target
from validation_measurement_core import validate_measurement as _validate_core


def _read(path:Path):
    if not path.is_file():return []
    with path.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def validate_measurement(run:Path,meta:dict,issues:list[Issue],ids:set,mode:str):
    start=len(issues)
    metrics,emergent=_validate_core(run,meta,issues,ids,mode)
    generated=issues[start:]
    resolved_both={e.get("canonical_name") or e.get("entity_id") for e in emergent if (e.get("resolution_status") or "").lower()=="resolved" and (e.get("measurement_target") or "").strip().lower()=="both"}
    # The pre-Stage2.4 core treats every emergent measurement_target as a query target. Remove only
    # the now-obsolete resolved-both error; unresolved both is still invalid and remains untouched.
    filtered=[]
    for i in generated:
        if i.code=="emergent-target" and any(i.message.startswith(name) for name in resolved_both):continue
        if i.code=="metric-target-missing":continue
        filtered.append(i)
    issues[start:]=filtered

    for e in emergent:
        name=e.get("canonical_name") or e.get("entity_id");status=(e.get("resolution_status") or "").lower();base=(e.get("measurement_target") or "").strip().lower();reviewed=(e.get("reviewed_measurement_target") or "").strip().lower()
        if status=="resolved":
            if base not in VALID_ENTITY_TARGETS:issues.append(Issue("error","emergent-target",f"{name} resolved measurement_target 必须 institution/ip/both"))
            if reviewed and reviewed not in VALID_ENTITY_TARGETS:issues.append(Issue("error","emergent-reviewed-target",f"{name} reviewed_measurement_target 必须 institution/ip/both"))
            if reviewed and base in VALID_ENTITY_TARGETS and reviewed!=base:issues.append(Issue("error","emergent-target-canonical-drift",f"{name} measurement_target={base} 与 reviewed_measurement_target={reviewed} 不一致"))
        elif base not in VALID_QUERY_TARGETS:
            # The core already emits emergent-target for this case; avoid adding a duplicate.
            pass

    universe=_read(run/"market_universe.csv")
    expected=set()
    for u in universe:
        for t in expanded_target(u.get("measurement_target")):expected.add((u.get("entity_id"),t))
    for e in emergent:
        if (e.get("resolution_status") or "").lower()=="resolved":
            for t in expanded_target(effective_emergent_target(e)):expected.add((e.get("entity_id"),t))
    actual={(m.get("entity_id"),m.get("measurement_target")) for m in metrics}
    missing=expected-actual;extra=actual-expected
    if missing:issues.append(Issue("error","metric-target-missing",f"ai_metrics 缺 entity×target：{sorted(missing)}"))
    if extra:issues.append(Issue("error","metric-target-extra",f"ai_metrics 含未授权 entity×target：{sorted(extra)}"))
    # Snapshot does not require robustness artifacts. If robustness is explicitly invoked, its own
    # script still requires explicit native/sidecar query_variant_id and never invents a fallback.
    return metrics,emergent
