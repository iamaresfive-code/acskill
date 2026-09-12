#!/usr/bin/env python3
"""Compute transparent AI Answer visibility metrics.

v2.2 rules:
- Market Universe measurement_target is explicit: institution/ip/both.
- Resolved AI-emergent entities prefer reviewed_measurement_target after Target Closure review and
  may also be institution/ip/both.
- Hybrid entities produce one metrics row per target; denominators never mix institution and IP.
- Only resolved, entity-correct recommended/listed mentions count as positive nominations.
- Raw mentions remain auditable even when non-positive.
"""
from __future__ import annotations
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path
from measurement_target_utils import expanded_target,require_effective_emergent_target

TRUE={"1","true","yes","y","是"};POSITIVE={"recommended","listed"}
OUT_FIELDS=["entity_id","canonical_name","entity_type","measurement_target","market_scope","market_role","universe_status","answer_cells","raw_mentioned_answers","raw_mention_rate","mentioned_answers","nomination_rate","top3_answers","top3_rate","first_mention_answers","first_mention_rate","cited_answers","citation_rate","engines_sampled","engines_mentioned","engine_coverage_rate","cross_model_consistency"]

def rcsv(p):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjsonl(p):
    out=[]
    with p.open("r",encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if line.strip():o=json.loads(line);o["_line"]=n;out.append(o)
    return out
def wcsv(p,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=OUT_FIELDS);w.writeheader();w.writerows(rows)
def norm(s):return re.sub(r"\s+","",str(s or "").lower())
def fnum(v):
    try:return float(v)
    except:return None
def truth(v):return str(v or "").strip().lower() in TRUE

def compute(run:Path):
    universe=rcsv(run/"market_universe.csv");emergent=rcsv(run/"ai_emergent_entities.csv");queries=rcsv(run/"queries.csv");answers=rjsonl(run/"ai_answers.jsonl");mentions=rcsv(run/"ai_mentions.csv")
    qmap={q["query_id"]:q for q in queries};amap={a["answer_id"]:a for a in answers};answer_target={a["answer_id"]:qmap.get(a.get("query_id"),{}).get("measurement_target","") for a in answers}
    entity_rows=[]
    for u in universe:
        target=(u.get("measurement_target") or "").strip().lower();targets=expanded_target(target)
        if not targets:raise ValueError(f"{u.get('canonical_name')} measurement_target 必须显式为 institution/ip/both")
        for t in targets:
            x=dict(u);x["_measurement_target"]=t;entity_rows.append(x)
    for e in emergent:
        if (e.get("resolution_status") or "").lower()!="resolved":continue
        declared=require_effective_emergent_target(e);targets=expanded_target(declared)
        for t in targets:
            base=(e.get("measurement_target") or "").strip().lower()
            entity_rows.append({"entity_id":e.get("entity_id",""),"canonical_name":e.get("canonical_name",""),"entity_type":"ip" if base=="ip" else "institution","market_scope":e.get("market_scope") or "unknown","market_role":"observation","universe_status":"ai-emergent","_measurement_target":t})
    known_ids={x.get("entity_id") for x in entity_rows};raw_by=defaultdict(list);positive_by=defaultdict(list);positive_by_answer=defaultdict(list)
    for m in mentions:
        aid=m.get("answer_id","");eid=m.get("entity_id","")
        if aid not in amap:raise ValueError(f"ai_mentions 引用不存在 answer_id: {aid}")
        if eid not in known_ids or m.get("match_method") not in {"explicit-name","verified-alias"}:continue
        needle=norm(m.get("mentioned_name"));text=norm(amap[aid].get("response_text",""))
        if not needle or needle not in text:raise ValueError(f"{m.get('mention_id')} 的 mentioned_name 未出现在原始回答文本中")
        rr=fnum(m.get("mention_rank"))
        if rr is None or rr<1:raise ValueError(f"{m.get('mention_id')} mention_rank 无效")
        raw_by[eid].append(m)
        if (m.get("resolution_status") or "").lower()=="resolved" and truth(m.get("entity_correct")) and (m.get("mention_intent") or "").lower() in POSITIVE:
            nr=fnum(m.get("nomination_rank"))
            if nr is None or nr<1:raise ValueError(f"{m.get('mention_id')} 正向提名缺 nomination_rank")
            positive_by[eid].append(m);positive_by_answer[aid].append(m)
    first_rank={aid:min(fnum(m.get("nomination_rank")) for m in ms) for aid,ms in positive_by_answer.items() if ms}
    rows=[]
    for u in entity_rows:
        eid=u.get("entity_id");target=u.get("_measurement_target");cells=[a for a in answers if answer_target.get(a["answer_id"])==target];cell_ids={a["answer_id"] for a in cells};engines={a.get("engine") for a in cells if a.get("engine")}
        raw=[m for m in raw_by[eid] if m.get("answer_id") in cell_ids];raw_answers={m["answer_id"] for m in raw};pos=[m for m in positive_by[eid] if m.get("answer_id") in cell_ids];mentioned={m["answer_id"] for m in pos};top3={m["answer_id"] for m in pos if (fnum(m.get("nomination_rank")) or 999)<=3};first={m["answer_id"] for m in pos if fnum(m.get("nomination_rank"))==first_rank.get(m["answer_id"])};cited={m["answer_id"] for m in pos if truth(m.get("citation_linked"))};eng_mentioned={amap[a].get("engine") for a in mentioned if amap[a].get("engine")}
        positive_qids={amap[a].get("query_id") for a in mentioned};positive_cells=[a for a in cells if a.get("query_id") in positive_qids];positive_hits=sum(a.get("answer_id") in mentioned for a in positive_cells);den=len(cell_ids);mden=len(mentioned)
        rows.append({"entity_id":eid,"canonical_name":u.get("canonical_name"),"entity_type":u.get("entity_type"),"measurement_target":target,"market_scope":u.get("market_scope"),"market_role":u.get("market_role"),"universe_status":u.get("universe_status"),"answer_cells":den,"raw_mentioned_answers":len(raw_answers),"raw_mention_rate":round(len(raw_answers)/den,4) if den else 0,"mentioned_answers":len(mentioned),"nomination_rate":round(len(mentioned)/den,4) if den else 0,"top3_answers":len(top3),"top3_rate":round(len(top3)/den,4) if den else 0,"first_mention_answers":len(first),"first_mention_rate":round(len(first)/den,4) if den else 0,"cited_answers":len(cited),"citation_rate":round(len(cited)/mden,4) if mden else 0,"engines_sampled":len(engines),"engines_mentioned":len(eng_mentioned),"engine_coverage_rate":round(len(eng_mentioned)/len(engines),4) if engines else 0,"cross_model_consistency":round(positive_hits/len(positive_cells),4) if len(engines)>=2 and positive_cells else ""})
    rows.sort(key=lambda r:(r["measurement_target"],r["universe_status"]!="included",-r["nomination_rate"],-r["top3_rate"],r["canonical_name"] or ""));wcsv(run/"ai_metrics.csv",rows);return rows

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:rows=compute(a.run_dir);print(f"ai_metrics.csv: {len(rows)} rows");return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"compute_ai_metrics：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
