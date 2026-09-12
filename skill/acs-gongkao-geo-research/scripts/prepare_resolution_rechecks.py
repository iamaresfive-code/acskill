#!/usr/bin/env python3
"""Prepare targeted Entity Resolution rechecks for high-risk mentions.

This is intentionally separate from Annotation Blind Review. It selects mentions that are more
likely to suffer alias/sub-string/entity-resolution errors: AI-emergent entities, unresolved
mentions, verified aliases, citation-only matches, and short Chinese names embedded inside a
larger Chinese token. Reviewers do not re-label mention_intent here.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from resolution_review_utils import risk_flags

FIELDS=["review_id","mention_id","answer_id","entity_id","canonical_name","mentioned_name","match_method","risk_flags","first_resolution_status","first_entity_correct","reviewer_resolution_status","reviewer_entity_correct","disagreement","resolution_outcome","resolution","reviewer","review_status","notes"]

def rcsv(p):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjsonl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def prepare(run:Path):
    mentions=rcsv(run/"ai_mentions.csv");answers={a.get("answer_id"):a for a in rjsonl(run/"ai_answers.jsonl")};universe={r.get("entity_id"):r for r in rcsv(run/"market_universe.csv")};emergent={r.get("entity_id"):r for r in rcsv(run/"ai_emergent_entities.csv")};emergent_ids=set(emergent)
    out=[]
    for m in mentions:
        aid=m.get("answer_id");a=answers.get(aid)
        if not a:raise ValueError(f"{m.get('mention_id')}: 不存在 answer_id {aid}")
        flags=risk_flags(m,a.get("response_text","") or "",emergent_ids)
        if not flags:continue
        ent=universe.get(m.get("entity_id")) or emergent.get(m.get("entity_id")) or {}
        out.append({
            "review_id":f"RR{len(out)+1:04d}","mention_id":m.get("mention_id","") or "","answer_id":aid or "","entity_id":m.get("entity_id","") or "","canonical_name":ent.get("canonical_name","") or "","mentioned_name":m.get("mentioned_name","") or "","match_method":m.get("match_method","") or "","risk_flags":"|".join(flags),
            "first_resolution_status":m.get("resolution_status","") or "","first_entity_correct":m.get("entity_correct","") or "",
            "reviewer_resolution_status":"","reviewer_entity_correct":"","disagreement":"","resolution_outcome":"","resolution":"","reviewer":"","review_status":"needs-review",
            "notes":"Review canonical mapping / resolved status / entity_correct only. Do not re-label mention_intent. If disagreement requires registry remap, mark resolution_outcome=requires-upstream-fix."
        })
    p=run/"resolution_rechecks.csv"
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(out)
    summary={"schema_version":"2.2","risk_rows":len(out),"ai_emergent_rows":sum("ai-emergent" in r["risk_flags"].split("|") for r in out),"short_name_boundary_rows":sum("short-name-boundary" in r["risk_flags"].split("|") for r in out)}
    (run/"resolution_rechecks_prepare_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return p,summary
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:path,s=prepare(a.run_dir);print(f"{path}: {s['risk_rows']} targeted resolution rechecks; short-name-boundary={s['short_name_boundary_rows']}");return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"prepare_resolution_rechecks：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
