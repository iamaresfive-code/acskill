#!/usr/bin/env python3
"""Build ai_mentions.csv from annotation_tasks.jsonl + reviewed annotation_labels.csv.

The reviewer supplies semantic labels only. This script derives nomination_rank/top3/first_mention
so those fields cannot drift by hand. Frozen resolution_status comes from annotation_tasks.jsonl.
Citation linkage is deliberately reset here and must be rebuilt independently through
prepare_citation_audit.py + apply_citation_audit.py.
"""
from __future__ import annotations
import argparse,csv,json
from collections import defaultdict
from pathlib import Path

INTENTS={"recommended","listed","comparison","caveat","excluded"};POSITIVE={"recommended","listed"};MATCH={"explicit-name","verified-alias","citation-only"};TRUE={"1","true","yes","y","是"}
OUT=["mention_id","answer_id","entity_id","mention_rank","nomination_rank","mentioned_name","match_method","resolution_status","mention_intent","top3","first_mention","entity_correct","citation_linked","citation_refs","concepts","notes"]

def rjsonl(p):return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def truth(v):return str(v or "").strip().lower() in TRUE
def apply(run:Path):
    tasks=rjsonl(run/"annotation_tasks.jsonl");labels=rcsv(run/"annotation_labels.csv");lmap={r.get("mention_id"):r for r in labels};errors=[];rows=[]
    if len(lmap)!=len(labels):errors.append("annotation_labels.csv mention_id 重复")
    for t in tasks:
        mid=t.get("mention_id");lab=lmap.get(mid)
        if not lab:errors.append(f"{mid}: 缺 annotation label");continue
        intent=(lab.get("mention_intent") or "").strip();method=(lab.get("match_method") or "").strip();resolution=t.get("frozen_resolution_status") or "unresolved"
        if intent not in INTENTS:errors.append(f"{mid}: mention_intent 无效")
        if method not in MATCH:errors.append(f"{mid}: match_method 无效")
        if str(lab.get("entity_correct") or "").strip().lower() not in TRUE|{"false","0","no","n","否"}:errors.append(f"{mid}: entity_correct 必须布尔")
        rows.append({
            "mention_id":mid,"answer_id":t.get("answer_id"),"entity_id":t.get("entity_id"),"mention_rank":t.get("mention_rank"),"nomination_rank":"",
            "mentioned_name":t.get("mentioned_name"),"match_method":method,"resolution_status":resolution,"mention_intent":intent,
            "top3":"false","first_mention":"false","entity_correct":"true" if truth(lab.get("entity_correct")) else "false",
            "citation_linked":"false","citation_refs":"","concepts":lab.get("concepts","") or "","notes":lab.get("notes","") or ""
        })
    if errors:raise ValueError("Annotation Labels 未完成：\n- "+"\n- ".join(errors[:50]))
    by_answer=defaultdict(list)
    for r in rows:
        if r["resolution_status"]=="resolved" and r["mention_intent"] in POSITIVE and r["match_method"] in {"explicit-name","verified-alias"} and r["entity_correct"]=="true":by_answer[r["answer_id"]].append(r)
    for aid,rs in by_answer.items():
        rs.sort(key=lambda r:float(r.get("mention_rank") or 10**9))
        for i,r in enumerate(rs,1):r["nomination_rank"]=str(i);r["top3"]="true" if i<=3 else "false";r["first_mention"]="true" if i==1 else "false"
    p=run/"ai_mentions.csv"
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=OUT);w.writeheader();w.writerows(rows)
    return p,len(rows)
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:path,n=apply(a.run_dir);print(f"{path}: {n} rows; citation linkage reset and requires separate citation audit");return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"apply_annotation_labels：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
