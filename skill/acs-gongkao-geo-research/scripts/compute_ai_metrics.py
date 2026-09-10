#!/usr/bin/env python3
"""Compute transparent AI Answer visibility metrics from raw answer cells and explicit entity mentions.

v2.2 computes metrics for included + observation/unresolved entities. Main report rankings still use
confirmed included groups, but observation metrics are retained so unexpected AI-visible competitors
are not silently discarded after a conservative Market Universe review.
"""
from __future__ import annotations
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path

TRUE={"1","true","yes","y","是"}
OUT_FIELDS=["entity_id","canonical_name","entity_type","market_scope","market_role","universe_status","answer_cells","mentioned_answers","nomination_rate","top3_answers","top3_rate","first_mention_answers","first_mention_rate","cited_answers","citation_rate","engines_sampled","engines_mentioned","cross_model_consistency"]

def rcsv(p:Path):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def wcsv(p:Path,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=OUT_FIELDS);w.writeheader();w.writerows(rows)
def rjsonl(p:Path):
    out=[]
    with p.open("r",encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if line.strip():obj=json.loads(line);obj["_line"]=n;out.append(obj)
    return out

def norm(s:str)->str:return re.sub(r"\s+","",(s or "").lower())

def compute(run:Path):
    universe=rcsv(run/"market_universe.csv");queries=rcsv(run/"queries.csv");answers=rjsonl(run/"ai_answers.jsonl");mentions=rcsv(run/"ai_mentions.csv")
    qmap={q["query_id"]:q for q in queries};amap={a["answer_id"]:a for a in answers};umap={u["entity_id"]:u for u in universe}
    answer_target={a["answer_id"]:qmap.get(a.get("query_id"),{}).get("measurement_target","") for a in answers}
    mention_by=defaultdict(list)
    for m in mentions:
        aid=m.get("answer_id","");eid=m.get("entity_id","")
        if aid not in amap:raise ValueError(f"ai_mentions 引用不存在 answer_id: {aid}")
        if eid not in umap:raise ValueError(f"ai_mentions 引用不存在 entity_id: {eid}")
        if m.get("match_method") not in {"explicit-name","verified-alias"}:continue
        text=norm(amap[aid].get("response_text",""));needle=norm(m.get("mentioned_name",""))
        if not needle or needle not in text:raise ValueError(f"{m.get('mention_id')} 的 mentioned_name 未出现在原始回答文本中")
        mention_by[eid].append(m)
    rows=[]
    for eid,u in umap.items():
        if u.get("universe_status")=="excluded":continue
        et=(u.get("entity_type") or "").lower();target="ip" if et in {"teacher","ip","expert","person","studio"} or u.get("market_role")=="expert-ip" else "institution"
        cells=[a for a in answers if answer_target.get(a["answer_id"])==target]
        cell_ids={a["answer_id"] for a in cells};engines={a.get("engine","") for a in cells if a.get("engine")}
        ms=[m for m in mention_by[eid] if m.get("answer_id") in cell_ids]
        mentioned={m["answer_id"] for m in ms};top3={m["answer_id"] for m in ms if m.get("top3","").lower() in TRUE};first={m["answer_id"] for m in ms if m.get("first_mention","").lower() in TRUE};cited={m["answer_id"] for m in ms if m.get("citation_linked","").lower() in TRUE};eng_mentioned={amap[a].get("engine","") for a in mentioned if amap[a].get("engine")}
        den=len(cell_ids);mden=len(mentioned)
        rows.append({
            "entity_id":eid,"canonical_name":u.get("canonical_name"),"entity_type":u.get("entity_type"),"market_scope":u.get("market_scope"),"market_role":u.get("market_role"),"universe_status":u.get("universe_status"),
            "answer_cells":den,"mentioned_answers":len(mentioned),"nomination_rate":round(len(mentioned)/den,4) if den else 0,
            "top3_answers":len(top3),"top3_rate":round(len(top3)/den,4) if den else 0,
            "first_mention_answers":len(first),"first_mention_rate":round(len(first)/den,4) if den else 0,
            "cited_answers":len(cited),"citation_rate":round(len(cited)/mden,4) if mden else 0,
            "engines_sampled":len(engines),"engines_mentioned":len(eng_mentioned),"cross_model_consistency":round(len(eng_mentioned)/len(engines),4) if engines else 0
        })
    rows.sort(key=lambda r:(r["universe_status"]!="included",r["entity_type"] in {"teacher","ip","expert","person","studio"},-r["nomination_rate"],-r["top3_rate"],r["canonical_name"] or ""))
    wcsv(run/"ai_metrics.csv",rows)
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:rows=compute(a.run_dir);print(f"ai_metrics.csv: {len(rows)} rows");return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"compute_ai_metrics：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
