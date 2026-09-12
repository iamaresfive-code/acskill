#!/usr/bin/env python3
"""Prepare entity-level citation review independently from intent annotation.

Every ai_mentions row receives an audit row. Positive, resolved mentions in Answer Cells that have
citations require reviewer confirmation. Non-positive/unresolved mentions and answers without
citations are deterministically marked non-linked for the formal Citation Rate.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

FIELDS=["mention_id","answer_id","entity_id","canonical_name","answer_citation_count","candidate_citation_refs","linked_citation_refs","citation_linked","link_basis","review_status","notes"]
TRUE={"1","true","yes","y","是"};POSITIVE={"recommended","listed"}

def truth(v):return str(v or "").strip().lower() in TRUE
def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjsonl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def citation_urls(answer):
    out=[];seen=set()
    for c in answer.get("citations") or []:
        u=""
        if isinstance(c,str):u=c.strip()
        elif isinstance(c,dict):
            for k in ("url","href","link"):
                if c.get(k):u=str(c[k]).strip();break
        if u and u not in seen:seen.add(u);out.append(u)
    return out

def prepare(run:Path):
    answers={a.get("answer_id"):a for a in rjsonl(run/"ai_answers.jsonl")}
    mentions=rcsv(run/"ai_mentions.csv");universe={r.get("entity_id"):r for r in rcsv(run/"market_universe.csv")};emergent={r.get("entity_id"):r for r in rcsv(run/"ai_emergent_entities.csv")}
    rows=[];needs=0
    for m in mentions:
        aid=m.get("answer_id");a=answers.get(aid)
        if not a:raise ValueError(f"{m.get('mention_id')}: 不存在 answer_id {aid}")
        refs=citation_urls(a);eid=m.get("entity_id");ent=universe.get(eid) or emergent.get(eid) or {}
        eligible=(m.get("resolution_status")=="resolved" and truth(m.get("entity_correct")) and m.get("match_method") in {"explicit-name","verified-alias"} and m.get("mention_intent") in POSITIVE)
        if refs and eligible:
            status="needs-review";basis="";needs+=1
        elif not refs:
            status="confirmed";basis="no-answer-citations"
        else:
            status="confirmed";basis="nonpositive-or-unresolved-not-in-formal-citation-metric"
        rows.append({
            "mention_id":m.get("mention_id","") or "","answer_id":aid or "","entity_id":eid or "","canonical_name":ent.get("canonical_name","") or "",
            "answer_citation_count":len(refs),"candidate_citation_refs":"|".join(refs),"linked_citation_refs":"","citation_linked":"false",
            "link_basis":basis,"review_status":status,
            "notes":"Only link URLs present in this Answer Cell that demonstrably bind this entity." if status=="needs-review" else ""
        })
    out=run/"citation_audit.csv"
    with out.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
    summary={
        "schema_version":"2.2","audit_rows":len(rows),"needs_review":needs,
        "answer_cells_with_citations":sum(bool(citation_urls(a)) for a in answers.values()),
        "total_answer_citation_refs":sum(len(citation_urls(a)) for a in answers.values())
    }
    (run/"citation_audit_prepare_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(prepare(a.run_dir),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"prepare_citation_audit：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
