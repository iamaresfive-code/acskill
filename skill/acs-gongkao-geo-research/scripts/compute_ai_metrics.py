#!/usr/bin/env python3
"""Compute transparent AI Answer visibility metrics from raw answer cells and explicit entity mentions.

v2.2 rules:
- included + observation/unresolved Market Universe entities retain metrics;
- resolved AI-emergent entities may also receive metrics without rewriting the pre-confirmed Universe;
- Top3 / first-mention are derived from mention_rank, not trusted as free-form labels;
- cross_model_consistency measures positive-query agreement across engines, while
  engine_coverage_rate separately measures how many sampled engines ever mention the entity.
"""
from __future__ import annotations
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path

TRUE={"1","true","yes","y","是"}
OUT_FIELDS=[
    "entity_id","canonical_name","entity_type","market_scope","market_role","universe_status",
    "answer_cells","mentioned_answers","nomination_rate","top3_answers","top3_rate",
    "first_mention_answers","first_mention_rate","cited_answers","citation_rate",
    "engines_sampled","engines_mentioned","engine_coverage_rate","cross_model_consistency"
]

def rcsv(p:Path):
    if not p.is_file():return []
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
def fnum(v):
    try:return float(v)
    except:return None

def compute(run:Path):
    universe=rcsv(run/"market_universe.csv")
    emergent=rcsv(run/"ai_emergent_entities.csv")
    queries=rcsv(run/"queries.csv")
    answers=rjsonl(run/"ai_answers.jsonl")
    mentions=rcsv(run/"ai_mentions.csv")
    qmap={q["query_id"]:q for q in queries}
    amap={a["answer_id"]:a for a in answers}
    answer_target={a["answer_id"]:qmap.get(a.get("query_id"),{}).get("measurement_target","") for a in answers}

    entities=[]
    for u in universe:
        x=dict(u)
        x["_measurement_target"]="ip" if (u.get("entity_type") or "").lower() in {"teacher","ip","expert","person","studio"} or u.get("market_role")=="expert-ip" else "institution"
        entities.append(x)
    for e in emergent:
        if (e.get("resolution_status") or "").lower()!="resolved":continue
        target=(e.get("measurement_target") or "").lower()
        x={
            "entity_id":e.get("entity_id",""),"canonical_name":e.get("canonical_name",""),
            "entity_type":"ip" if target=="ip" else "institution",
            "market_scope":e.get("market_scope") or "unknown","market_role":"observation",
            "universe_status":"ai-emergent","_measurement_target":target
        }
        entities.append(x)
    umap={u["entity_id"]:u for u in entities if u.get("entity_id")}

    mention_by=defaultdict(list)
    eligible_by_answer=defaultdict(list)
    for m in mentions:
        aid=m.get("answer_id","");eid=m.get("entity_id","")
        if aid not in amap:raise ValueError(f"ai_mentions 引用不存在 answer_id: {aid}")
        if eid not in umap:raise ValueError(f"ai_mentions 引用不存在/未解析 entity_id: {eid}")
        if m.get("match_method") not in {"explicit-name","verified-alias"}:continue
        text=norm(amap[aid].get("response_text",""));needle=norm(m.get("mentioned_name",""))
        if not needle or needle not in text:raise ValueError(f"{m.get('mention_id')} 的 mentioned_name 未出现在原始回答文本中")
        rank=fnum(m.get("mention_rank"))
        if rank is None or rank < 1:raise ValueError(f"{m.get('mention_id')} mention_rank 无效")
        mention_by[eid].append(m);eligible_by_answer[aid].append(m)

    first_rank={}
    for aid,ms in eligible_by_answer.items():
        ranks=[fnum(m.get("mention_rank")) for m in ms]
        ranks=[r for r in ranks if r is not None]
        if ranks:first_rank[aid]=min(ranks)

    rows=[]
    for eid,u in umap.items():
        target=u.get("_measurement_target") or "institution"
        cells=[a for a in answers if answer_target.get(a["answer_id"])==target]
        cell_ids={a["answer_id"] for a in cells}
        engines={a.get("engine","") for a in cells if a.get("engine")}
        ms=[m for m in mention_by[eid] if m.get("answer_id") in cell_ids]
        mentioned={m["answer_id"] for m in ms}
        top3={m["answer_id"] for m in ms if (fnum(m.get("mention_rank")) or 999)<=3}
        first={m["answer_id"] for m in ms if fnum(m.get("mention_rank"))==first_rank.get(m["answer_id"])}
        cited={m["answer_id"] for m in ms if m.get("citation_linked","").lower() in TRUE}
        eng_mentioned={amap[a].get("engine","") for a in mentioned if amap[a].get("engine")}

        # Positive-query cross-model consistency: among queries where at least one engine
        # mentioned the entity, what share of sampled query×engine cells also mentioned it?
        positive_qids={amap[a].get("query_id") for a in mentioned}
        positive_cells=[a for a in cells if a.get("query_id") in positive_qids]
        positive_mentions=sum(1 for a in positive_cells if a.get("answer_id") in mentioned)

        den=len(cell_ids);mden=len(mentioned)
        rows.append({
            "entity_id":eid,"canonical_name":u.get("canonical_name"),"entity_type":u.get("entity_type"),
            "market_scope":u.get("market_scope"),"market_role":u.get("market_role"),
            "universe_status":u.get("universe_status"),
            "answer_cells":den,"mentioned_answers":len(mentioned),
            "nomination_rate":round(len(mentioned)/den,4) if den else 0,
            "top3_answers":len(top3),"top3_rate":round(len(top3)/den,4) if den else 0,
            "first_mention_answers":len(first),"first_mention_rate":round(len(first)/den,4) if den else 0,
            "cited_answers":len(cited),"citation_rate":round(len(cited)/mden,4) if mden else 0,
            "engines_sampled":len(engines),"engines_mentioned":len(eng_mentioned),
            "engine_coverage_rate":round(len(eng_mentioned)/len(engines),4) if engines else 0,
            "cross_model_consistency":(
                round(positive_mentions/len(positive_cells),4)
                if len(engines)>=2 and positive_cells else ""
            )
        })
    rows.sort(key=lambda r:(r["universe_status"]!="included",r["entity_type"] in {"teacher","ip","expert","person","studio"},-r["nomination_rate"],-r["top3_rate"],r["canonical_name"] or ""))
    wcsv(run/"ai_metrics.csv",rows)
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:rows=compute(a.run_dir);print(f"ai_metrics.csv: {len(rows)} rows");return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"compute_ai_metrics：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
