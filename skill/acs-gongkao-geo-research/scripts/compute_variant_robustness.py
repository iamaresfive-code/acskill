#!/usr/bin/env python3
"""Compute repeat/variant robustness without treating it as a GEO score.

Outputs:
- variant_robustness.csv: entity × target × canonical query × engine hit pattern (0/N..N/N)
- query_set_similarity.csv: pairwise Jaccard of positive nomination sets between variants
- robustness_summary.json: descriptive aggregate metrics

Variant IDs come from ai_answers.jsonl when natively recorded, otherwise from the audited
answer_variant_manifest.csv sidecar. The script never invents a silent run-{sample_run} fallback.
If query_variant_mode=semantic-retrieval-variants these metrics describe query/retrieval
robustness, not stochastic repeatability under identical conditions.
"""
from __future__ import annotations
import argparse,csv,json,itertools,statistics
from collections import defaultdict,Counter
from pathlib import Path

TRUE={"1","true","yes","y","是"};POSITIVE={"recommended","listed"};VARIANT_EVIDENCE={"native-recorded","legacy-reconstructed"}

def rcsv(p):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjsonl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def truth(v):return str(v or "").strip().lower() in TRUE
def wcsv(p,fields,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def jaccard(a:set,b:set):
    if not a and not b:return 1.0
    return len(a&b)/len(a|b) if a|b else 1.0

def variant_map(run:Path,answers:list[dict]):
    manifest=rcsv(run/"answer_variant_manifest.csv");mmap={};evidence={}
    if manifest:
        if len({r.get("answer_id") for r in manifest})!=len(manifest):raise ValueError("answer_variant_manifest.csv answer_id 重复")
        answer_ids={a.get("answer_id") for a in answers}
        extra={r.get("answer_id") for r in manifest}-answer_ids
        if extra:raise ValueError(f"answer_variant_manifest.csv 含未知 answer_id: {sorted(extra)[:10]}")
        for r in manifest:
            aid=r.get("answer_id");qv=(r.get("query_variant_id") or "").strip();status=(r.get("evidence_status") or "").strip()
            if not qv:raise ValueError(f"{aid}: sidecar query_variant_id 为空")
            if status not in VARIANT_EVIDENCE:raise ValueError(f"{aid}: evidence_status 无效")
            mmap[aid]=qv;evidence[aid]=status
    out={};status_counts=Counter()
    for a in answers:
        aid=a.get("answer_id");native=(a.get("query_variant_id") or "").strip();side=mmap.get(aid,"")
        if native and side and native!=side:raise ValueError(f"{aid}: raw query_variant_id 与 sidecar 不一致")
        qv=native or side
        if not qv:raise ValueError(f"{aid}: 缺 query_variant_id；先运行 prepare_answer_variant_manifest.py")
        out[aid]=qv;status_counts["native-recorded" if native else evidence.get(aid,"legacy-reconstructed")]+=1
    return out,status_counts

def compute(run:Path):
    meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8"));queries=rcsv(run/"queries.csv");answers=rjsonl(run/"ai_answers.jsonl");mentions=rcsv(run/"ai_mentions.csv");universe=rcsv(run/"market_universe.csv");emergent=rcsv(run/"ai_emergent_entities.csv")
    amap={a["answer_id"]:a for a in answers};answer_to_variant,variant_status=variant_map(run,answers)
    positive=defaultdict(set)
    for m in mentions:
        if m.get("answer_id") not in amap:continue
        if m.get("match_method") not in {"explicit-name","verified-alias"}:continue
        if (m.get("resolution_status") or "").lower()!="resolved" or not truth(m.get("entity_correct")):continue
        if (m.get("mention_intent") or "").lower() not in POSITIVE:continue
        positive[m["answer_id"]].add(m.get("entity_id"))
    entity_targets=[]
    for u in universe:
        t=(u.get("measurement_target") or "").strip()
        for x in (["institution","ip"] if t=="both" else [t]):
            if x in {"institution","ip"}:entity_targets.append((u.get("entity_id"),u.get("canonical_name"),x,u.get("universe_status")))
    for e in emergent:
        if e.get("resolution_status")=="resolved" and e.get("measurement_target") in {"institution","ip"}:entity_targets.append((e.get("entity_id"),e.get("canonical_name"),e.get("measurement_target"),"ai-emergent"))
    by_q_engine=defaultdict(list)
    for a in answers:by_q_engine[(a.get("query_id"),a.get("engine"))].append(a)
    engines_by_q=defaultdict(set)
    for qid,eng in by_q_engine:engines_by_q[qid].add(eng)
    rows=[];hit_patterns=defaultdict(int);positive_den=0;positive_all=0
    for eid,name,target,status in entity_targets:
        for q in queries:
            qid=q.get("query_id")
            if q.get("measurement_target")!=target or q.get("status")!="sampled":continue
            for eng in sorted(engines_by_q.get(qid,[])):
                qanswers=by_q_engine.get((qid,eng),[])
                if not qanswers:continue
                hits=sum(eid in positive[a["answer_id"]] for a in qanswers);n=len(qanswers);pattern=f"{hits}/{n}";hit_patterns[pattern]+=1
                if hits>0:
                    positive_den+=1
                    if hits==n:positive_all+=1
                rows.append({"entity_id":eid,"canonical_name":name,"measurement_target":target,"universe_status":status,"query_id":qid,"engine":eng,"variant_count":n,"hit_count":hits,"hit_pattern":pattern,"all_positive":"true" if hits==n else "false","all_negative":"true" if hits==0 else "false"})
    vf=["entity_id","canonical_name","measurement_target","universe_status","query_id","engine","variant_count","hit_count","hit_pattern","all_positive","all_negative"]
    wcsv(run/"variant_robustness.csv",vf,rows)

    sim=[];jac=[];exact=0;pair_n=0
    for (qid,eng),xs in sorted(by_q_engine.items()):
        xs=sorted(xs,key=lambda a:(int(a.get("sample_run") or 0),answer_to_variant[a["answer_id"]]))
        for a,b in itertools.combinations(xs,2):
            sa=positive[a["answer_id"]];sb=positive[b["answer_id"]];j=jaccard(sa,sb);eq=sa==sb;pair_n+=1;exact+=int(eq);jac.append(j)
            sim.append({"query_id":qid,"engine":eng,"variant_a":answer_to_variant[a["answer_id"]],"variant_b":answer_to_variant[b["answer_id"]],"answer_a":a["answer_id"],"answer_b":b["answer_id"],"positive_jaccard":round(j,4),"exact_positive_set_match":"true" if eq else "false"})
    sf=["query_id","engine","variant_a","variant_b","answer_a","answer_b","positive_jaccard","exact_positive_set_match"]
    wcsv(run/"query_set_similarity.csv",sf,sim)
    summary={
        "schema_version":"2.2","query_variant_mode":meta.get("query_variant_mode"),
        "variant_evidence_status_counts":dict(variant_status),
        "interpretation":"semantic retrieval/query robustness" if meta.get("query_variant_mode")=="semantic-retrieval-variants" else "repeatability under exact canonical query",
        "positive_persistence_3of3_rate":round(positive_all/positive_den,4) if positive_den else None,"positive_persistence_numerator":positive_all,"positive_persistence_denominator":positive_den,
        "pairwise_positive_set_jaccard_mean":round(statistics.fmean(jac),4) if jac else None,"pairwise_positive_set_jaccard_median":round(statistics.median(jac),4) if jac else None,
        "exact_positive_set_match_rate":round(exact/pair_n,4) if pair_n else None,"hit_pattern_distribution":dict(sorted(hit_patterns.items())),
        "note":"Descriptive/diagnostic only; legacy-reconstructed variant IDs are migration metadata, not originally recorded query strings."
    }
    (run/"robustness_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(compute(a.run_dir),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"compute_variant_robustness：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
