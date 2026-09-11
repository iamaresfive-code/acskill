#!/usr/bin/env python3
"""Prepare a review sheet for explicit Market Universe measurement targets.

This helper does NOT decide the new target. `old_inferred_target` is shown only to expose legacy
behavior and must not be copied automatically. A reviewer must fill new_explicit_target and
review_status=confirmed, then run apply_measurement_target_audit.py.
"""
from __future__ import annotations
import argparse,csv
from pathlib import Path

FIELDS=["entity_id","canonical_name","stage1_market_role","entity_type","old_inferred_target","current_explicit_target","new_explicit_target","evidence_basis","changed","review_status","notes"]

def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def legacy_target(r):
    et=(r.get("entity_type") or "").lower()
    return "ip" if et in {"teacher","ip","expert","person","studio"} or r.get("market_role")=="expert-ip" else "institution"
def prepare(run:Path):
    rows=rcsv(run/"market_universe.csv");out=[]
    for r in rows:
        current=(r.get("measurement_target") or "").strip()
        out.append({"entity_id":r.get("entity_id",""),"canonical_name":r.get("canonical_name",""),"stage1_market_role":r.get("market_role",""),"entity_type":r.get("entity_type",""),"old_inferred_target":legacy_target(r),"current_explicit_target":current,"new_explicit_target":current,"evidence_basis":"","changed":"false","review_status":"needs-review","notes":"legacy inference is diagnostic only; reviewer must use market identity/evidence"})
    p=run/"measurement_target_audit.csv"
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(out)
    return p,len(out)
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:path,n=prepare(a.run_dir);print(f"{path}: {n} rows; fill new_explicit_target + evidence_basis + review_status=confirmed before apply");return 0
    except OSError as e:print(f"prepare_measurement_target_audit：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
