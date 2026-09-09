#!/usr/bin/env python3
"""Score GEO Asset Readiness. This is explanatory infrastructure, not AI Answer visibility."""
from __future__ import annotations
import argparse,csv,json,math
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
WEIGHTS={"entity_clarity":25,"regional_semantic_density":20,"open_web_assets":15,"external_authority":15,"content_depth_freshness":10,"data_tool_assets":10,"platform_coverage":5}

def rcsv(p):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def n(v):
    try:return float(v)
    except:return None
def tier(t):
    if t>=85:return "S"
    if t>=75:return "A"
    if t>=65:return "B+"
    if t>=55:return "B"
    if t>=45:return "B-"
    return "C"
def score(run:Path):
    inputs=rcsv(run/"asset_inputs.csv");evidence=rcsv(run/"evidence.csv");by=defaultdict(list)
    for e in evidence:by[e.get("entity_id","")].append(e)
    out=[]
    for r in inputs:
        vals={};
        for f,mx in WEIGHTS.items():
            v=n(r.get(f));
            if v is None or not 0<=v<=mx:raise ValueError(f"{r.get('entity_id')} {f} 必须在 0-{mx}")
            vals[f]=v
        total=round(sum(vals.values()),2);ev=[e for e in by[r.get("entity_id","")] if e.get("counting_scope","")!="ignored"]
        domains={urlparse(e.get("source_url","")).netloc.lower().removeprefix("www.") for e in ev if e.get("source_url")}
        owned=sum(e.get("source_owner","")=="owned" for e in ev);ratio=round(owned/len(ev),4) if ev else 0
        item=dict(r);item.update(vals);item.update({"asset_readiness":total,"asset_tier":tier(total),"evidence_count":len(ev),"independent_domains":len(domains),"owned_source_dependency":ratio});out.append(item)
    if out:
        fields=list(out[0].keys())
        with (run/"asset_scores.csv").open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(f"asset_scores.csv: {len(score(a.run_dir))} rows");return 0
    except (OSError,ValueError) as e:print(f"score_assets：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
