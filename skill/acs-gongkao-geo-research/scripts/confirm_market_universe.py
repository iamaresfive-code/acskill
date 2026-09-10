#!/usr/bin/env python3
"""Confirm a reviewed Market Universe after explicit user approval.

This script never discovers entities or changes scores. It only converts an already
reviewed market_universe.csv into a confirmed research contract and unlocks
Measurement in run_metadata.json.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

MAIN_ROLES={"national-benchmark","local-core","local-active","expert-ip","historical"}
VALID_SCOPES={"national","regional","local","unknown"}
VALID_STATUS={"included","observation","excluded","unresolved"}


def read_csv(path:Path):
    with path.open("r",encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f);return list(r),list(r.fieldnames or [])


def write_csv(path:Path,fields,rows):
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def confirm(run:Path,approved_by:str="user"):
    up=run/"market_universe.csv";mp=run/"run_metadata.json"
    if not up.is_file() or not mp.is_file():
        raise SystemExit("market_universe.csv / run_metadata.json 缺失")
    rows,fields=read_csv(up);errors=[]
    for i,r in enumerate(rows,2):
        name=(r.get("canonical_name") or "").strip() or f"row-{i}"
        scope=(r.get("market_scope") or "").strip();role=(r.get("market_role") or "").strip();status=(r.get("universe_status") or "").strip();basis=(r.get("salience_basis") or "").strip()
        if scope not in VALID_SCOPES:errors.append(f"{name}: market_scope 无效")
        if status not in VALID_STATUS:errors.append(f"{name}: universe_status 无效")
        if status=="included" and role in MAIN_ROLES and scope=="unknown":errors.append(f"{name}: 主研究主体不能以 unknown scope 确认")
        if status=="included" and role in MAIN_ROLES and not basis:errors.append(f"{name}: 主研究主体缺 salience_basis")
        if role in {"local-core","local-active"} and scope not in {"local","regional"}:errors.append(f"{name}: 本土角色必须有 local/regional scope")
    if errors:
        raise SystemExit("Market Universe 不能确认：\n- "+"\n- ".join(errors))
    if "confirmation_status" not in fields:fields.append("confirmation_status")
    for r in rows:r["confirmation_status"]="confirmed"
    write_csv(up,fields,rows)
    meta=json.loads(mp.read_text(encoding="utf-8"));meta["market_universe_confirmed"]=True;meta["measurement_allowed"]=True;meta["universe_confirmation_source"]=approved_by;meta["run_status"]="universe-confirmed"
    mp.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"confirmed_rows":len(rows),"market_universe_confirmed":True,"measurement_allowed":True,"approved_by":approved_by}


def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);p.add_argument("--approved-by",default="user");a=p.parse_args();print(json.dumps(confirm(a.run_dir,a.approved_by),ensure_ascii=False));return 0

if __name__=="__main__":raise SystemExit(main())
