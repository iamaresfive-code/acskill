#!/usr/bin/env python3
"""Prepare explicit measurement-target review with hybrid/IP-led signals.

This helper never decides the target. It surfaces organization evidence, personal/IP evidence and
cross-target raw AI mentions so reviewers do not silently miss IP-led brands. `hybrid_signal`
forces attention only; it never auto-assigns `both`.
"""
from __future__ import annotations
import argparse,csv,json,re
from collections import defaultdict,Counter
from pathlib import Path

FIELDS=["entity_id","canonical_name","stage1_market_role","market_bucket","entity_type","current_explicit_target","candidate_target","institution_evidence","ip_evidence","hybrid_signal","hybrid_signal_basis","cross_target_ai_signal","new_explicit_target","evidence_basis","reviewer_reason","changed","review_status","notes"]
PERSON_MARKERS=re.compile(r"老师|师姐|师兄|学长|学姐|主播|主讲|创始人|领衔|个人\s*IP|IP-led",re.I)
ORG_MARKERS=re.compile(r"公司|机构|教育|工作室|培训|课程店铺|线下|小班|教研|品牌",re.I)
IP_MARKERS=re.compile(r"老师|师姐|师兄|主播|主讲|创始人|领衔|IP-led|个人\s*IP|抖音|B站|播客",re.I)


def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def bucket(r):
    if r.get("universe_status")=="included" and r.get("market_role")=="national-benchmark":return "A_national_benchmarks"
    if r.get("universe_status")=="included" and r.get("market_role") in {"local-core","local-active"} and r.get("market_scope") in {"local","regional"}:return "B_local_regional"
    if r.get("universe_status")=="included" and r.get("market_role")=="expert-ip":return "C_expert_ip"
    return "D_observation_or_other"
def kw_hits(pattern,text):return sorted(set(m.group(0) for m in pattern.finditer(text or "")))
def prepare(run:Path):
    rows=rcsv(run/"market_universe.csv");raw_path=run/"mentions_raw.json";raw=json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.is_file() else []
    raw_counts=defaultdict(Counter)
    for m in raw:
        eid=m.get("entity_id");t=m.get("measurement_target")
        if eid and t in {"institution","ip"}:raw_counts[eid][t]+=1
    out=[]
    for r in rows:
        eid=r.get("entity_id","");aliases=r.get("aliases","") or "";text=" | ".join([r.get("canonical_name","") or "",aliases,r.get("salience_basis","") or "",r.get("notes","") or ""])
        org=kw_hits(ORG_MARKERS,text);ip=kw_hits(IP_MARKERS,text);personal_aliases=[a.strip() for a in aliases.split("|") if a.strip() and PERSON_MARKERS.search(a)]
        counts=raw_counts[eid];cross=f"institution_raw={counts.get('institution',0)};ip_raw={counts.get('ip',0)}";reasons=[]
        if counts.get('institution',0)>0 and counts.get('ip',0)>0:reasons.append("cross-target-raw-mention")
        if personal_aliases:reasons.append("personal/ip alias")
        if PERSON_MARKERS.search(text):reasons.append("explicit IP/person language")
        if r.get("entity_type")=="studio":reasons.append("studio requires manual brand-vs-IP review")
        if org and ip:reasons.append("organization + IP signals coexist")
        if r.get("market_role")=="expert-ip" and org:reasons.append("expert-ip role + organization signal")
        current=(r.get("measurement_target") or "").strip()
        out.append({
            "entity_id":eid,"canonical_name":r.get("canonical_name","") or "","stage1_market_role":r.get("market_role","") or "","market_bucket":bucket(r),"entity_type":r.get("entity_type","") or "","current_explicit_target":current,"candidate_target":current,
            "institution_evidence":"; ".join([f"entity_type={r.get('entity_type','')}",f"market_role={r.get('market_role','')}"] + (["org_keywords="+",".join(org)] if org else [])),
            "ip_evidence":"; ".join((["personal_aliases="+",".join(personal_aliases)] if personal_aliases else []) + (["ip_keywords="+",".join(ip)] if ip else [])),
            "hybrid_signal":"true" if reasons else "false","hybrid_signal_basis":" | ".join(dict.fromkeys(reasons)),"cross_target_ai_signal":cross,
            "new_explicit_target":current,"evidence_basis":"","reviewer_reason":"","changed":"false","review_status":"needs-review",
            "notes":"hybrid_signal only forces review; it never auto-assigns both. Decide institution/ip/both from market identity + existing evidence."
        })
    p=run/"measurement_target_audit.csv"
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(out)
    return p,len(out),sum(r["hybrid_signal"]=="true" for r in out)
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:path,n,h=prepare(a.run_dir);print(f"{path}: {n} rows; hybrid review signals={h}; reviewer must fill new_explicit_target/evidence_basis/reviewer_reason + confirmed");return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"prepare_measurement_target_audit：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
