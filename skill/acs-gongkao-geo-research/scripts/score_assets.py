#!/usr/bin/env python3
"""Score GEO Asset Readiness. This is explanatory infrastructure, not AI Answer visibility.

v2.2 Report Layer Completion 口径：
- 7 个维度允许取字面量 unknown；**没有找到证据 ≠ 0 分**，unknown 维度不计入分母，
  并写入 asset_readiness_basis_weight（已证据化权重）与 unknown_fields。
- asset_readiness = round(100 * 已证据化维度得分 / 已证据化维度满分, 2)；全无证据时留空。
- 已证据化权重 < 50/100 时 Tier 记 U（证据不足），不得据此判断主体“没有资产”。
- evidence_count / independent_domains / owned_source_dependency 同时统计
  Stage 1 SERP evidence 与 Report Layer 公开网页证据（report_research_manifest.csv）。
"""
from __future__ import annotations
import argparse,csv,json
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
WEIGHTS={"entity_clarity":25,"regional_semantic_density":20,"open_web_assets":15,"external_authority":15,"content_depth_freshness":10,"data_tool_assets":10,"platform_coverage":5}
UNKNOWN_TOKENS={"","unknown","not-observed","insufficient-evidence","na","n/a"}
CONFIRMED={"found","blocked"}

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
    inputs=rcsv(run/"asset_inputs.csv");evidence=rcsv(run/"evidence.csv");manifest=rcsv(run/"report_research_manifest.csv");by=defaultdict(list)
    for e in evidence:by[e.get("entity_id","")].append(e)
    report_ev=defaultdict(list)
    for e in manifest:
        if e.get("source_url") and e.get("access_status") in CONFIRMED:report_ev[e.get("entity_id","")].append(e)
    out=[]
    for r in inputs:
        known={};unknown=[]
        for f,mx in WEIGHTS.items():
            raw=str(r.get(f,"")).strip()
            if raw.lower() in UNKNOWN_TOKENS:unknown.append(f);continue
            v=n(raw)
            if v is None or not 0<=v<=mx:raise ValueError(f"{r.get('entity_id')} {f} 必须是 0-{mx} 或 unknown")
            known[f]=v
        basis=sum(WEIGHTS[f] for f in known)
        total=round(100*sum(known.values())/basis,2) if basis else ""
        band=tier(total) if isinstance(total,float) else ""
        ev=[e for e in by[r.get("entity_id","")] if e.get("counting_scope","")!="ignored"]+report_ev[r.get("entity_id","")]
        allrows=by[r.get("entity_id","")]+report_ev[r.get("entity_id","")]
        domains={urlparse(e.get("source_url","")).netloc.lower().removeprefix("www.") for e in ev if e.get("source_url")}
        owned=sum(e.get("source_owner","")=="owned" for e in allrows);ratio=round(owned/len(allrows),4) if allrows else 0
        declared={x.strip() for x in str(r.get("unknown_fields","")).replace(";","|").split("|") if x.strip()}
        item=dict(r);item.update(known);item.update({f:("unknown" if f in unknown else r.get(f,"")) for f in WEIGHTS})
        item.update({"asset_readiness":total,"asset_tier":("U" if known and basis<50 else band),"asset_readiness_basis_weight":basis,"evidence_count":len(ev),"independent_domains":len(domains),"owned_source_dependency":ratio,"unknown_fields":"|".join(sorted(set(unknown)|declared))});out.append(item)
    if out:
        fields=list(out[0].keys())
        with (run/"asset_scores.csv").open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:
        rows=score(a.run_dir)
        if not rows:print("score_assets：错误：asset_inputs.csv 没有有效主体行，拒绝产出空 asset_scores.csv");return 2
        scored=sum(1 for r in rows if r.get("asset_readiness")!="")
        if not scored:print("score_assets：错误：没有任何主体具备证据化维度，拒绝产出无数据 asset_scores.csv");return 2
        print(f"asset_scores.csv: {len(rows)} rows（其中 {scored} 行有证据化评分）");return 0
    except (OSError,ValueError) as e:print(f"score_assets：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
