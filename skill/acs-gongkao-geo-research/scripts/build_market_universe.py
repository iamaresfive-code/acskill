#!/usr/bin/env python3
"""Build a reviewable Market Universe skeleton from user seeds + system discovery candidates.
No GEO score or recall signal is used to infer local/national identity.
"""
from __future__ import annotations
import argparse,csv,json,re
from pathlib import Path
from fs_utils import ensure_directory

FIELDS=["entity_id","canonical_name","aliases","entity_type","user_seed","discovery_origin","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","universe_status","confirmation_status","notes"]


def norm(s:str)->str:return re.sub(r"[\s·•._\-—（）()【】\[\]]+","",(s or "").strip().lower())
def read_csv(p:Path):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def write_csv(p:Path,rows):
    ensure_directory(p.parent)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)

def build(run:Path):
    meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8"))
    discovered=read_csv(run/"discovery_candidates.csv")
    rows=[];seen={};counter=1
    def add(name,user_seed,origin,row=None):
        nonlocal counter
        key=norm(name)
        if not key:return
        if key in seen:
            if user_seed:rows[seen[key]]["user_seed"]="true"
            return
        source=row or {};eid=source.get("entity_id") or f"U{counter:03d}";counter+=1
        item={
            "entity_id":eid,"canonical_name":name.strip(),"aliases":source.get("aliases","") or "",
            "entity_type":source.get("entity_type","") or "unknown","user_seed":"true" if user_seed else "false",
            "discovery_origin":origin,"market_scope":source.get("market_scope","") or "unknown",
            "operating_region":source.get("operating_region","") or "",
            "market_role":source.get("market_role","") or "unclassified",
            "activity_status":source.get("activity_status","") or "uncertain",
            "platform_native":source.get("platform_native","") or "false",
            "salience_basis":source.get("salience_basis","") or "",
            "universe_status":source.get("universe_status","") or "included",
            "confirmation_status":"needs-review","notes":source.get("notes","") or ""
        }
        seen[key]=len(rows);rows.append(item)
    for s in meta.get("seed_entities",[]):add(str(s),True,"user-seed")
    if meta.get("allow_discovery_supplement"):
        for r in discovered:add(r.get("canonical_name") or r.get("display_name") or "",False,r.get("discovery_origin") or "system-discovery",r)
    write_csv(run/"market_universe.csv",rows)
    summary={"total":len(rows),"user_seed":sum(r["user_seed"]=="true" for r in rows),"needs_review":len(rows),"message":"在进入任何正式 Measurement 前，逐项补齐 market_scope / market_role / salience_basis，并由用户确认 Universe。"}
    (run/"universe_review.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();print(json.dumps(build(a.run_dir),ensure_ascii=False));return 0
if __name__=="__main__":raise SystemExit(main())
