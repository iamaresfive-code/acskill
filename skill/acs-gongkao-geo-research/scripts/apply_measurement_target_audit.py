#!/usr/bin/env python3
"""Apply a fully reviewed measurement_target_audit.csv to market_universe.csv.

No target is inferred here. Every universe entity must have exactly one confirmed audit row with
new_explicit_target in institution/ip/both and non-empty evidence_basis. Rows carrying a
hybrid_signal must also include reviewer_reason so a reviewer cannot silently dismiss the signal.
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
    up=run/"market_universe.csv";ap=run/"measurement_target_audit.csv";mp=run/"run_metadata.json"
    if not up.is_file() or not ap.is_file() or not mp.is_file():raise ValueError("缺 market_universe.csv / measurement_target_audit.csv / run_metadata.json")
    universe,fields=read_csv(up);audit,_=read_csv(ap);by={r.get("entity_id"):r for r in audit};errors=[]
    if len(by)!=len(audit):errors.append("measurement_target_audit.csv entity_id 重复")
    for r in universe:
        eid=r.get("entity_id");a=by.get(eid);name=r.get("canonical_name") or eid
        if not a:errors.append(f"{name}: 缺 audit row");continue
        t=(a.get("new_explicit_target") or "").strip();status=(a.get("review_status") or "").strip();basis=(a.get("evidence_basis") or "").strip();reason=(a.get("reviewer_reason") or "").strip()
        if t not in VALID:errors.append(f"{name}: new_explicit_target 必须 institution/ip/both")
        if status!="confirmed":errors.append(f"{name}: review_status 必须 confirmed")
        if not basis:errors.append(f"{name}: evidence_basis 不能为空")
        if truth(a.get("hybrid_signal")) and not reason:errors.append(f"{name}: hybrid_signal=true 时 reviewer_reason 必须明确说明为何选择 {t or '当前 target'}")
    if errors:raise ValueError("Measurement Target Audit 未完成：\n- "+"\n- ".join(errors))
    if "measurement_target" not in fields:
        idx=fields.index("entity_type")+1 if "entity_type" in fields else len(fields);fields.insert(idx,"measurement_target")
    changes=0
    for r in universe:
        a=by[r.get("entity_id")];old=(r.get("measurement_target") or "").strip();new=a.get("new_explicit_target").strip();r["measurement_target"]=new
        if old!=new:changes+=1
        a["changed"]="true" if old!=new else "false"
    af=list(audit[0].keys()) if audit else []
    write_csv(up,fields,universe)
    if audit:write_csv(ap,af,audit)
    meta=json.loads(mp.read_text(encoding="utf-8"));meta["measurement_target_reviewed"]=True;meta["measurement_target_review_source"]="measurement_target_audit.csv";meta["measurement_target_hybrid_signals_reviewed"]=True;mp.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    write_review(run,universe,meta)
    return {"rows":len(universe),"changed":changes,"measurement_target_reviewed":True,"hybrid_signals_reviewed":True}
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(apply(a.run_dir),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"apply_measurement_target_audit：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
