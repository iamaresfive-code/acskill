#!/usr/bin/env python3
"""GEO v2.2 stage-aware validator."""
from __future__ import annotations
import argparse,json
from dataclasses import asdict
from pathlib import Path
from validation_common import *
from validation_universe_v221 import validate_universe
from validation_measurement import validate_measurement
from validation_target_closure import validate_target_closure
from validation_report_customer import validate_report

def validate(run:Path,strict=False,stage="full"):
    issues=[]
    if stage not in STAGES:return [Issue("error","invalid-stage",f"stage 必须是 {', '.join(sorted(STAGES))}")]
    if not run.is_dir():return [Issue("error","missing-run-dir",f"不是目录：{run}")]
    meta=rjson(run/"run_metadata.json",issues,"run-metadata")
    if str(meta.get("schema_version"))!=VERSION or str(meta.get("skill_version"))!=VERSION:issues.append(Issue("error","version","run_metadata schema_version / skill_version 必须为 2.2"))
    if meta.get("official_output_format")!="docx":issues.append(Issue("error","output-contract","v2.2 唯一正式输出必须是 docx"))
    for k in ("region_confirmed","seed_entities_confirmed","discovery_supplement_confirmed"):
        if meta.get(k) is not True:issues.append(Issue("error","preflight-incomplete",f"Preflight 未确认：{k}",k))
    mode=meta.get("research_mode");seeds=[str(x).strip() for x in meta.get("seed_entities",[]) if str(x).strip()]
    if mode=="scoped-geo-landscape" and not seeds:issues.append(Issue("error","seed-required","scoped-geo-landscape 必须至少有一个用户 Seed"))
    if mode not in {"scoped-geo-landscape","blind-discovery-scan"}:issues.append(Issue("error","research-mode","research_mode 无效"))
    require_confirmed=stage in {"measurement","report","full"}
    if require_confirmed:
        if meta.get("market_universe_confirmed") is not True:issues.append(Issue("error","universe-not-confirmed","Market Universe 未经用户确认，不得进入正式 Measurement"))
        if meta.get("measurement_allowed") is not True:issues.append(Issue("error","measurement-not-authorized","measurement_allowed 必须为 true"))
    universe,ids=validate_universe(run,meta,issues,require_confirmed)
    metrics=[];emergent=[]
    if stage in {"measurement","report","full"}:
        metrics,emergent=validate_measurement(run,meta,issues,ids,mode)
        validate_target_closure(run,meta,issues,universe,metrics,emergent)
    if stage in {"report","full"}:validate_report(run,issues,universe,metrics,emergent)
    return issues

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",nargs="?",type=Path);p.add_argument("--strict",action="store_true");p.add_argument("--json",action="store_true");p.add_argument("--stage",choices=sorted(STAGES),default="full");a=p.parse_args()
    if not a.run_dir:p.error("必须提供 run_dir")
    issues=validate(a.run_dir,a.strict,a.stage);errors=sum(x.level=="error" for x in issues);warnings=sum(x.level=="warning" for x in issues)
    if a.json:print(json.dumps({"stage":a.stage,"errors":errors,"warnings":warnings,"issues":[asdict(x) for x in issues]},ensure_ascii=False,indent=2))
    else:
        for x in issues:print(f"{x.level.upper()} [{x.code}] {x.message}")
        print(f"校验摘要（stage={a.stage}）：{errors} 个错误，{warnings} 个警告")
    return 1 if errors or (a.strict and warnings) else 0
if __name__=="__main__":raise SystemExit(main())
