#!/usr/bin/env python3
"""Build annotation_tasks.jsonl from frozen raw mentions and answers.

The task pack freezes entity resolution upstream. Reviewers label semantic intent only; they are
not asked to infer corporate/entity resolution from answer prose or decide citation linkage.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def rcsv(p):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjsonl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def main_build(run:Path):
    raw=json.loads((run/"mentions_raw.json").read_text(encoding="utf-8"));answers={a["answer_id"]:a for a in rjsonl(run/"ai_answers.jsonl")};universe={r.get("entity_id"):r for r in rcsv(run/"market_universe.csv")};emergent={r.get("entity_id"):r for r in rcsv(run/"ai_emergent_entities.csv")};out=[]
    for i,r in enumerate(raw,1):
        aid=r.get("answer_id");eid=r.get("entity_id");a=answers.get(aid)
        if not a:raise ValueError(f"raw mention 引用不存在 answer_id: {aid}")
        if eid in universe:resolution="resolved"
        elif eid in emergent:resolution=(emergent[eid].get("resolution_status") or "unresolved").lower()
        else:raise ValueError(f"raw mention entity_id 未在 Universe/emergent registry: {eid}")
        out.append({"mention_id":r.get("mention_id") or f"AM{i:04d}","answer_id":aid,"query_id":a.get("query_id"),"entity_id":eid,"canonical_name":r.get("canonical_name") or (universe.get(eid) or emergent.get(eid) or {}).get("canonical_name"),"mentioned_name":r.get("mentioned_name"),"mention_rank":r.get("mention_rank"),"char_pos":r.get("char_pos"),"mention_context":r.get("context",""),"response_text":a.get("response_text",""),"frozen_resolution_status":resolution,"measurement_target":r.get("measurement_target",""),"label_instruction":"Choose mention_intent using data-schema anchors; do not re-decide frozen_resolution_status; do not label citations here because citation linkage is reviewed separately."})
    p=run/"annotation_tasks.jsonl";p.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in out)+"\n",encoding="utf-8");return p,len(out)
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:path,n=main_build(a.run_dir);print(f"{path}: {n} annotation tasks");return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"prepare_annotation_tasks：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
