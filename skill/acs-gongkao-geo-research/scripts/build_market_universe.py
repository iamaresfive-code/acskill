#!/usr/bin/env python3
"""Build a reviewable Market Universe from user seeds + system discovery candidates.

v2.2 rules:
- User Seed guarantees review/resolution, not inclusion or score.
- Seed/discovery duplicate names are merged field-by-field; discovery evidence is never dropped.
- Review buckets are disjoint and machine-generated so executors do not invent incompatible summaries.
"""
from __future__ import annotations
import argparse,csv,json,re
from collections import Counter
from pathlib import Path
from fs_utils import ensure_directory

FIELDS=["entity_id","canonical_name","aliases","entity_type","user_seed","discovery_origin","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","universe_status","confirmation_status","downgrade_reason","notes"]
PLACEHOLDERS={"":"", "unknown":"unknown", "unclassified":"unclassified", "uncertain":"uncertain"}
TRUE={"1","true","yes","y","是"}


def norm(s:str)->str:return re.sub(r"[\s·•._\-—（）()【】\[\]]+","",(s or "").strip().lower())
def read_csv(p:Path):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def write_csv(p:Path,rows):
    ensure_directory(p.parent)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)

def _merge_aliases(a:str,b:str)->str:
    out=[];seen=set()
    for raw in (a,b):
        for x in (raw or "").split("|"):
            x=x.strip();k=norm(x)
            if x and k not in seen:seen.add(k);out.append(x)
    return "|".join(out)

def _merge_text(a:str,b:str)->str:
    a=(a or "").strip();b=(b or "").strip()
    if not a:return b
    if not b or b in a:return a
    return a+" | "+b

def _is_default(field:str,value:str)->bool:
    v=(value or "").strip().lower()
    if not v:return True
    if field=="entity_type":return v=="unknown"
    if field=="market_scope":return v=="unknown"
    if field=="market_role":return v=="unclassified"
    if field=="activity_status":return v=="uncertain"
    if field=="universe_status":return v in {"unresolved",""}
    return False

def merge_row(dst:dict,src:dict,user_seed:bool=False,origin:str=""):
    if user_seed:dst["user_seed"]="true"
    if origin:
        current=[x for x in (dst.get("discovery_origin") or "").split("|") if x]
        if origin not in current:current.append(origin)
        dst["discovery_origin"]="|".join(current)
    dst["aliases"]=_merge_aliases(dst.get("aliases",""),src.get("aliases","") or "")
    for field in ("entity_type","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","universe_status","downgrade_reason"):
        incoming=(src.get(field) or "").strip()
        if not incoming:continue
        if field in {"operating_region","salience_basis"}:
            if not dst.get(field):dst[field]=incoming
        elif field=="platform_native":
            if incoming.lower() in TRUE:dst[field]="true"
        elif field=="downgrade_reason":
            if not dst.get(field):dst[field]=incoming
        elif _is_default(field,dst.get(field,"")):
            dst[field]=incoming
    dst["notes"]=_merge_text(dst.get("notes",""),src.get("notes","") or "")
    return dst

def build_review(rows:list[dict],meta:dict)->dict:
    # Four disjoint buckets. D is the catch-all for observation/unresolved/historical/other.
    A=[];B=[];C=[];D=[]
    for r in rows:
        name=r.get("canonical_name","");status=r.get("universe_status");role=r.get("market_role");scope=r.get("market_scope")
        if status=="included" and role=="national-benchmark":A.append(name)
        elif status=="included" and role in {"local-core","local-active"} and scope in {"local","regional"}:B.append(name)
        elif status=="included" and role=="expert-ip":C.append(name)
        else:D.append(name)
    flat=A+B+C+D
    counts=Counter(flat)
    unresolved=[{"entity":r.get("canonical_name",""),"issue":r.get("notes") or r.get("salience_basis") or "待补实体/市场证据"}
                for r in rows if r.get("universe_status")!="included" or r.get("market_scope")=="unknown" or r.get("market_role")=="unclassified"]
    seo=[r.get("canonical_name","") for r in rows if r.get("downgrade_reason")=="seo-only"]
    seeds=[r.get("canonical_name","") for r in rows if (r.get("user_seed") or "").lower() in TRUE]
    return {
      "schema_version":"2.2","region":meta.get("normalized_region") or meta.get("requested_region"),"research_mode":meta.get("research_mode"),
      "market_universe_confirmed":bool(meta.get("market_universe_confirmed")),"measurement_allowed":bool(meta.get("measurement_allowed")),
      "total_entities":len(rows),"user_seed_count":len(seeds),"user_seed_all_present":len(seeds)==len([x for x in meta.get("seed_entities",[]) if str(x).strip()]),
      "system_discovery_count":sum(
          ((r.get("user_seed") or "").lower() not in TRUE)
          and ("system-discovery" in (r.get("discovery_origin") or "") or "platform-native" in (r.get("discovery_origin") or ""))
          for r in rows
      ),
      "seed_also_discovered_count":sum(
          ((r.get("user_seed") or "").lower() in TRUE)
          and ("system-discovery" in (r.get("discovery_origin") or "") or "platform-native" in (r.get("discovery_origin") or ""))
          for r in rows
      ),
      "platform_native_count":sum((r.get("platform_native") or "").lower() in TRUE for r in rows),
      "expert_ip_included_count":sum(r.get("universe_status")=="included" and r.get("market_role")=="expert-ip" for r in rows),
      "distribution":{
          "market_scope":dict(Counter(r.get("market_scope") or "" for r in rows)),
          "market_role":dict(Counter(r.get("market_role") or "" for r in rows)),
          "universe_status":dict(Counter(r.get("universe_status") or "" for r in rows)),
          "platform_native":dict(Counter("true" if (r.get("platform_native") or "").lower() in TRUE else "false" for r in rows)),
          "discovery_origin":dict(Counter(x for r in rows for x in (r.get("discovery_origin") or "").split("|") if x))
      },
      "buckets":{"A_national_benchmarks":A,"B_local_regional":B,"C_expert_ip":C,"D_observation_or_other":D},
      "bucket_audit":{"represented_rows":len(flat),"unique_names":len(counts),"duplicates":[k for k,v in counts.items() if v>1],"complete":len(flat)==len(rows) and len(counts)==len(rows)},
      "seo_only_downgraded":seo,"unresolved_or_weak":unresolved,
      "message":"Market Universe 草案；确认前不得进入 AI Answer Measurement。"
    }

def write_review(run:Path,rows:list[dict],meta:dict):
    review=build_review(rows,meta)
    (run/"universe_review.json").write_text(json.dumps(review,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return review

def build(run:Path):
    meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8"))
    discovered=read_csv(run/"discovery_candidates.csv")
    rows=[];seen={};counter=1
    def add(name,user_seed,origin,row=None):
        nonlocal counter
        key=norm(name)
        if not key:return
        source=row or {}
        if key in seen:
            merge_row(rows[seen[key]],source,user_seed,origin)
            return
        eid=source.get("entity_id") or f"U{counter:03d}";counter+=1
        item={
            "entity_id":eid,"canonical_name":name.strip(),"aliases":source.get("aliases","") or "",
            "entity_type":source.get("entity_type","") or "unknown","user_seed":"true" if user_seed else "false",
            "discovery_origin":origin,"market_scope":source.get("market_scope","") or "unknown",
            "operating_region":source.get("operating_region","") or "",
            "market_role":source.get("market_role","") or "unclassified",
            "activity_status":source.get("activity_status","") or "uncertain",
            "platform_native":source.get("platform_native","") or "false",
            "salience_basis":source.get("salience_basis","") or "",
            # Seed alone is not automatic inclusion. It must be resolved/reviewed first.
            "universe_status":source.get("universe_status","") or ("unresolved" if user_seed else "observation"),
            "confirmation_status":"needs-review","downgrade_reason":source.get("downgrade_reason","") or "","notes":source.get("notes","") or ""
        }
        seen[key]=len(rows);rows.append(item)
    for s in meta.get("seed_entities",[]):add(str(s),True,"user-seed")
    if meta.get("allow_discovery_supplement"):
        for r in discovered:add(r.get("canonical_name") or r.get("display_name") or "",False,r.get("discovery_origin") or "system-discovery",r)
    write_csv(run/"market_universe.csv",rows)
    review=write_review(run,rows,meta)
    return {"total":len(rows),"user_seed":review["user_seed_count"],"needs_review":sum(r.get("confirmation_status")!="confirmed" for r in rows),"bucket_audit":review["bucket_audit"]}

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();print(json.dumps(build(a.run_dir),ensure_ascii=False));return 0
if __name__=="__main__":raise SystemExit(main())
