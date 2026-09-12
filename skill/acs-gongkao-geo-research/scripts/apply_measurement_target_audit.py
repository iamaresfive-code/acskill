#!/usr/bin/env python3
"""Apply reviewed Measurement Target Audit to Universe + resolved AI-emergent entities.

Universe entities persist their reviewed target directly in market_universe.csv. AI-emergent
entities keep the legacy single-target `measurement_target` for backward compatibility and gain
`reviewed_measurement_target`, which may be institution/ip/both and is authoritative downstream.
No target is inferred here.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from build_market_universe import write_review

VALID={"institution","ip","both"};TRUE={"1","true","yes","y","是"}

def truth(v):return str(v or "").strip().lower() in TRUE
def read_csv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);return list(r),list(r.fieldnames or [])
def write_csv(p,fields,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def apply(run:Path):
    up=run/"market_universe.csv";xp=run/"ai_emergent_entities.csv";ap=run/"measurement_target_audit.csv";mp=run/"run_metadata.json"
    if not up.is_file() or not xp.is_file() or not ap.is_file() or not mp.is_file():raise ValueError("缺 market_universe.csv / ai_emergent_entities.csv / measurement_target_audit.csv / run_metadata.json")
    universe,ufields=read_csv(up);emergent,xfields=read_csv(xp);audit,afields=read_csv(ap);by={r.get("entity_id"):r for r in audit};errors=[]
    if len(by)!=len(audit):errors.append("measurement_target_audit.csv entity_id 重复")
    expected={r.get("entity_id"):("universe",r.get("canonical_name") or r.get("entity_id")) for r in universe}
    for r in emergent:
        if (r.get("resolution_status") or "").strip().lower()=="resolved":expected[r.get("entity_id")]=("ai-emergent",r.get("canonical_name") or r.get("entity_id"))
    for eid,(source,name) in expected.items():
        a=by.get(eid)
        if not a:errors.append(f"{name}: 缺 audit row");continue
        if (a.get("entity_source") or "").strip()!=source:errors.append(f"{name}: entity_source 应为 {source}")
        t=(a.get("new_explicit_target") or "").strip();status=(a.get("review_status") or "").strip();basis=(a.get("evidence_basis") or "").strip();reason=(a.get("reviewer_reason") or "").strip()
        if t not in VALID:errors.append(f"{name}: new_explicit_target 必须 institution/ip/both")
        if status!="confirmed":errors.append(f"{name}: review_status 必须 confirmed")
        if not basis:errors.append(f"{name}: evidence_basis 不能为空")
        if truth(a.get("hybrid_signal")) and not reason:errors.append(f"{name}: hybrid_signal=true 时 reviewer_reason 必须明确说明为何选择 {t or '当前 target'}")
    extra=set(by)-set(expected)
    if extra:errors.append(f"measurement_target_audit.csv 含非预期/未解析主体：{sorted(extra)[:20]}")
    if errors:raise ValueError("Measurement Target Audit 未完成：\n- "+"\n- ".join(errors))
    if "measurement_target" not in ufields:
        idx=ufields.index("entity_type")+1 if "entity_type" in ufields else len(ufields);ufields.insert(idx,"measurement_target")
    changes=0;universe_changes=0;emergent_changes=0;both_emergent=0
    for r in universe:
        a=by[r.get("entity_id")];old=(r.get("measurement_target") or "").strip();new=a.get("new_explicit_target").strip();r["measurement_target"]=new
        if old!=new:changes+=1;universe_changes+=1
        a["changed"]="true" if old!=new else "false"
    for field in ("reviewed_measurement_target","measurement_target_review_status","measurement_target_review_source"):
        if field not in xfields:xfields.append(field)
    for r in emergent:
        if (r.get("resolution_status") or "").strip().lower()!="resolved":continue
        a=by[r.get("entity_id")];new=a.get("new_explicit_target").strip();old=(r.get("reviewed_measurement_target") or r.get("measurement_target") or "").strip()
        r["reviewed_measurement_target"]=new;r["measurement_target_review_status"]="confirmed";r["measurement_target_review_source"]="measurement_target_audit.csv"
        # Preserve legacy registry compatibility: its measurement_target remains a single query target.
        if new in {"institution","ip"}:r["measurement_target"]=new
        else:both_emergent+=1
        if old!=new:changes+=1;emergent_changes+=1
        a["changed"]="true" if old!=new else "false"
    write_csv(up,ufields,universe);write_csv(xp,xfields,emergent);write_csv(ap,afields,audit)
    meta=json.loads(mp.read_text(encoding="utf-8"));meta.update({
        "measurement_target_reviewed":True,"measurement_target_review_source":"measurement_target_audit.csv","measurement_target_hybrid_signals_reviewed":True,
        "resolved_emergent_target_reviewed":True,"resolved_emergent_target_review_count":sum((r.get('resolution_status') or '').lower()=='resolved' for r in emergent),
        "resolved_emergent_both_count":both_emergent
    });mp.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_review(run,universe,meta)
    summary={"rows":len(expected),"universe_rows":len(universe),"resolved_emergent_rows":meta["resolved_emergent_target_review_count"],"changed":changes,"universe_changed":universe_changes,"emergent_changed":emergent_changes,"emergent_both":both_emergent,"measurement_target_reviewed":True}
    (run/"measurement_target_audit_apply_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(apply(a.run_dir),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"apply_measurement_target_audit：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
