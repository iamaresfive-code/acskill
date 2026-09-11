#!/usr/bin/env python3
"""Apply a completed citation_audit.csv to ai_mentions.csv and write an audit summary."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path


def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);return list(r),list(r.fieldnames or [])
def wcsv(p,fields,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def rjsonl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def split(v):return [x.strip() for x in str(v or "").split("|") if x.strip()]
def citation_urls(a):
    out=[]
    for c in a.get("citations") or []:
        if isinstance(c,str):u=c.strip()
        elif isinstance(c,dict):u=next((str(c[k]).strip() for k in ("url","href","link") if c.get(k)),"")
        else:u=""
        if u and u not in out:out.append(u)
    return out

def apply(run:Path):
    mentions,fields=rcsv(run/"ai_mentions.csv");audit,af=rcsv(run/"citation_audit.csv");answers={a.get("answer_id"):a for a in rjsonl(run/"ai_answers.jsonl")}
    amap={r.get("mention_id"):r for r in audit};errors=[]
    if len(amap)!=len(audit):errors.append("citation_audit.csv mention_id 重复")
    mention_ids={m.get("mention_id") for m in mentions};extra=set(amap)-mention_ids
    if extra:errors.append(f"citation_audit.csv 包含不存在 mention_id: {sorted(extra)[:10]}")
    for m in mentions:
        mid=m.get("mention_id");a=amap.get(mid);ans=answers.get(m.get("answer_id"))
        if not a:errors.append(f"{mid}: 缺 citation audit row");continue
        if a.get("answer_id")!=m.get("answer_id") or a.get("entity_id")!=m.get("entity_id"):errors.append(f"{mid}: audit answer/entity 与 ai_mentions 不一致")
        if a.get("review_status")!="confirmed":errors.append(f"{mid}: citation review_status 必须 confirmed")
        refs=split(a.get("linked_citation_refs"));available=set(citation_urls(ans or {}));bad=[x for x in refs if x not in available]
        if bad:errors.append(f"{mid}: linked_citation_refs 不在原 Answer citations: {bad[:3]}")
        if not refs and not str(a.get("link_basis") or "").strip():errors.append(f"{mid}: 无链接时 link_basis 也不能为空")
    if errors:raise ValueError("Citation Audit 未完成：\n- "+"\n- ".join(errors[:100]))
    linked_mentions=0;linked_entities=set();linked_refs=set()
    for m in mentions:
        a=amap[m.get("mention_id")];refs=split(a.get("linked_citation_refs"));linked=bool(refs)
        m["citation_linked"]="true" if linked else "false";m["citation_refs"]="|".join(refs);a["citation_linked"]="true" if linked else "false"
        if linked:linked_mentions+=1;linked_entities.add(m.get("entity_id"));linked_refs.update(refs)
    wcsv(run/"ai_mentions.csv",fields,mentions);wcsv(run/"citation_audit.csv",af,audit)
    all_answer_refs=[u for a in answers.values() for u in citation_urls(a)]
    summary={
        "schema_version":"2.2","audit_rows":len(audit),"reviewed_rows":sum(r.get("review_status")=="confirmed" for r in audit),
        "answer_cells_with_citations":sum(bool(citation_urls(a)) for a in answers.values()),"total_answer_citation_refs":len(all_answer_refs),
        "unique_answer_citation_refs":len(set(all_answer_refs)),"linked_mentions":linked_mentions,"linked_entities":len(linked_entities),"linked_unique_refs":len(linked_refs)
    }
    (run/"citation_audit_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(apply(a.run_dir),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"apply_citation_audit：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
