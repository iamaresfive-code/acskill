#!/usr/bin/env python3
"""Persist the Stage 2 measurement contract after the executor probes real AI-engine access.

This script does not probe external services itself. The executor must first verify actual access,
then pass only engines that can genuinely return answers in the current environment.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

CONTEXT_MODES={"native","engine-native-search","external-search-augmented"}
PROFILES={"snapshot","release"}

def infer_sampling(engines:list[str])->str:
    n=len(engines)
    return "asset-audit-only" if n==0 else "single-engine" if n==1 else "limited-multi-engine" if n==2 else "multi-engine"

def configure(run:Path,engines:list[str],context_mode:str,profile:str,repeat_runs:int|None=None,fresh_context:bool|None=None):
    mp=run/"run_metadata.json"
    if not mp.is_file():raise ValueError("缺少 run_metadata.json")
    if context_mode not in CONTEXT_MODES:raise ValueError("context_mode 无效")
    if profile not in PROFILES:raise ValueError("profile 无效")
    clean=[]
    for x in engines:
        x=x.strip()
        if x and x not in clean:clean.append(x)
    if profile=="release":
        repeats=3 if repeat_runs is None else repeat_runs
        if repeats<3:raise ValueError("release profile repeat_runs 必须 >=3")
        fresh=True if fresh_context is None else fresh_context
        if not fresh:raise ValueError("release profile 必须使用 fresh context")
    else:
        repeats=1 if repeat_runs is None else repeat_runs
        if repeats<1:raise ValueError("snapshot repeat_runs 必须 >=1")
        fresh=False if fresh_context is None else fresh_context
    meta=json.loads(mp.read_text(encoding="utf-8"))
    meta.update({
        "ai_engine_access_checked":True,
        "ai_engines_expected":clean,
        "sampling_mode":infer_sampling(clean),
        "measurement_profile":profile,
        "answer_context_mode_expected":context_mode,
        "repeat_runs_expected":repeats,
        "fresh_context_required":bool(fresh),
        "measurement_contract_status":"configured"
    })
    mp.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {k:meta[k] for k in ("ai_engine_access_checked","ai_engines_expected","sampling_mode","measurement_profile","answer_context_mode_expected","repeat_runs_expected","fresh_context_required")}

def main():
    p=argparse.ArgumentParser(description="配置 GEO v2.2 Stage 2 Measurement Contract")
    p.add_argument("run_dir",type=Path)
    p.add_argument("--engine",action="append",default=[],help="仅填写已实际验证可用的 AI/AI Search 引擎，可重复")
    p.add_argument("--context-mode",required=True,choices=sorted(CONTEXT_MODES))
    p.add_argument("--profile",choices=sorted(PROFILES),default="snapshot")
    p.add_argument("--repeat-runs",type=int)
    g=p.add_mutually_exclusive_group();g.add_argument("--fresh-context",action="store_true");g.add_argument("--allow-shared-context",action="store_true")
    a=p.parse_args();fresh=True if a.fresh_context else (False if a.allow_shared_context else None)
    try:print(json.dumps(configure(a.run_dir,a.engine,a.context_mode,a.profile,a.repeat_runs,fresh),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"configure_measurement：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
