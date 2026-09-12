#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,re
from collections import defaultdict,Counter
from pathlib import Path
FIELDS=["entity_id","canonical_name","entity_source","resolution_status","stage1_market_role","market_bucket","entity_type","current_explicit_target","candidate_target","institution_evidence","ip_evidence","hybrid_signal","hybrid_signal_basis","cross_target_ai_signal","new_explicit_target","evidence_basis","reviewer_reason","changed","review_status","notes"]
VALID={"institution","ip","both"}
PERSON_MARKERS=re.compile(r"老师|师姐|师兄|学长|学姐|主播|主讲|创始人|领衔|个人\s*IP|IP-led",re.I)
ORG_MARKERS=re.compile(r"公司|机构|教育|工作室|培训|课程店铺|线下|小班|教研|品牌",re.I)
IP_MARKERS=re.compile(r"老师|师姐|师兄|主播|主讲|创始人|领衔|IP-led|个人\s*IP|抖音|B站|播客",re.I)
def rcsv(p):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def bucket(r):
    if r.get("universe_status")=="included" and r.get("market_role")=="national-benchmark":return "A_national_benchmarks"
    if r.get("universe_status")=="included" and r.get("market_role") in {"local-core","local-active"} and r.get("market_scope") in {"local","regional"}:return "B_local_regional"
    if r.get("universe_status")=="included" and r.get("market_role")=="expert-ip":return "C_expert_ip"
    return "D_observation_or_other"
def kw_hits(pattern,text):return sorted(set(m.group(0) for m in pattern.finditer(text or "")))
def make_row(r:dict,source:str,raw_counts:dict):
    eid=r.get("entity_id","");aliases=r.get("aliases","") or ""
    if source=="universe":
        role=r.get("market_role","") or "";b=bucket(r);entity_type=r.get("entity_type","") or "";resolution="resolved";current=(r.get("measurement_target") or "").strip();extra=[r.get("salience_basis","") or "",r.get("notes","") or ""]
    else:
        role="ai-emergent";b="AI_emergent";entity_type="ai-emergent";resolution=(r.get("resolution_status") or "").strip().lower();current=(r.get("reviewed_measurement_target") or r.get("measurement_target") or "").strip();extra=[r.get("notes","") or "",r.get("source_answer_ids","") or "",r.get("source_result_ids","") or ""]
    text=" | ".join([r.get("canonical_name","") or "",aliases,*extra]);org=kw_hits(ORG_MARKERS,text);ip=kw_hits(IP_MARKERS,text);personal_aliases=[a.strip() for a in aliases.split("|") if a.strip() and PERSON_MARKERS.search(a)];counts=raw_counts.get(eid,Counter());cross=f"institution_raw={counts.get('institution',0)};ip_raw={counts.get('ip',0)}";reasons=[]
    if counts.get('institution',0)>0 and counts.get('ip',0)>0:reasons.append("cross-target-raw-mention")
    if personal_aliases:reasons.append("personal/ip alias")
    if PERSON_MARKERS.search(text):reasons.append("explicit IP/person language")
    if r.get("entity_type")=="studio":reasons.append("studio requires manual brand-vs-IP review")
    if org and ip:reasons.append("organization + IP signals coexist")
    if role=="expert-ip" and org:reasons.append("expert-ip role + organization signal")
    if source=="ai-emergent" and counts.get('institution',0)>0 and counts.get('ip',0)>0:reasons.append("emergent cross-target closure required")
    institution_bits=[]
    if source=="universe":institution_bits.extend([f"entity_type={entity_type}",f"market_role={role}"])
    else:institution_bits.extend([f"registry_target={r.get('measurement_target','')}",f"source_answers={r.get('source_answer_ids','')}"])
    if org:institution_bits.append("org_keywords="+",".join(org))
    ip_bits=[]
    if personal_aliases:ip_bits.append("personal_aliases="+",".join(personal_aliases))
    if ip:ip_bits.append("ip_keywords="+",".join(ip))
    return {"entity_id":eid,"canonical_name":r.get("canonical_name","") or "","entity_source":source,"resolution_status":resolution,"stage1_market_role":role,"market_bucket":b,"entity_type":entity_type,"current_explicit_target":current,"candidate_target":current,"institution_evidence":"; ".join(institution_bits),"ip_evidence":"; ".join(ip_bits),"hybrid_signal":"true" if reasons else "false","hybrid_signal_basis":" | ".join(dict.fromkeys(reasons)),"cross_target_ai_signal":cross,"new_explicit_target":current,"evidence_basis":"","reviewer_reason":"","changed":"false","review_status":"needs-review","notes":"hybrid_signal only forces review; it never auto-assigns both. For resolved AI-emergent rows, confirmed new_explicit_target is written back to canonical measurement_target on apply; reviewed_measurement_target is review provenance and must match."}
def _carry_forward(row:dict,old:dict|None)->bool:
    if not old or (old.get("review_status") or "").strip()!="confirmed":return False
    source=(row.get("entity_source") or "").strip();old_source=(old.get("entity_source") or "").strip()
    if source=="ai-emergent" and old_source!="ai-emergent":return False
    if source=="universe" and old_source not in {"","universe"}:return False
    t=(old.get("new_explicit_target") or "").strip();basis=(old.get("evidence_basis") or "").strip();reason=(old.get("reviewer_reason") or "").strip()
    if t not in VALID or not basis:return False
    if row.get("hybrid_signal")=="true" and not reason:return False
    row["new_explicit_target"]=t;row["candidate_target"]=t;row["evidence_basis"]=basis;row["reviewer_reason"]=reason;row["review_status"]="confirmed";row["changed"]="true" if t!=(row.get("current_explicit_target") or "").strip() else "false";row["notes"]=(row.get("notes") or "")+" | prior confirmed decision carried forward; current signals recomputed";return True
def prepare(run:Path):
    p=run/"measurement_target_audit.csv";prior=rcsv(p) if p.is_file() else [];prior_by={r.get("entity_id"):r for r in prior if (r.get("entity_id") or "").strip()};universe=rcsv(run/"market_universe.csv");emergent=rcsv(run/"ai_emergent_entities.csv");raw_path=run/"mentions_raw.json";raw=json.loads(raw_path.read_text(encoding="utf-8")) if raw_path.is_file() else [];raw_counts=defaultdict(Counter)
    for m in raw:
        eid=m.get("entity_id");t=m.get("measurement_target")
        if eid and t in {"institution","ip"}:raw_counts[eid][t]+=1
    out=[make_row(r,"universe",raw_counts) for r in universe];resolved=[r for r in emergent if (r.get("resolution_status") or "").strip().lower()=="resolved"];out.extend(make_row(r,"ai-emergent",raw_counts) for r in resolved);ids=[r["entity_id"] for r in out]
    if len(ids)!=len(set(ids)):raise ValueError("Universe 与 resolved emergent 出现重复 entity_id")
    preserved=sum(_carry_forward(r,prior_by.get(r.get("entity_id"))) for r in out)
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(out)
    summary={"audit_rows":len(out),"universe_rows":len(universe),"resolved_emergent_rows":len(resolved),"hybrid_review_signals":sum(r["hybrid_signal"]=="true" for r in out),"preserved_confirmed_rows":preserved,"needs_review_rows":sum(r["review_status"]!="confirmed" for r in out)};(run/"measurement_target_audit_prepare_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return p,summary
