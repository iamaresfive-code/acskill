#!/usr/bin/env python3
"""Build an authoritative QA summary from final persisted Measurement artifacts.

Diagnostic/hand-off reports should copy counts from this JSON instead of manually carrying forward
pre-correction distributions. This prevents report drift after late annotation or target fixes.
"""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from pathlib import Path


def rcsv(p):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjson(p,default=None):
    if not p.is_file():return {} if default is None else default
    return json.loads(p.read_text(encoding="utf-8"))
def build(run:Path):
    mentions=rcsv(run/"ai_mentions.csv");metrics=rcsv(run/"ai_metrics.csv");audit=rcsv(run/"measurement_target_audit.csv");resolution=rcsv(run/"resolution_rechecks.csv");citation=rjson(run/"citation_audit_summary.json",{});robust=rjson(run/"robustness_summary.json",{})
    intents=Counter((m.get("mention_intent") or "").strip() for m in mentions if (m.get("mention_intent") or "").strip());targets=Counter((m.get("measurement_target") or "").strip() for m in metrics if (m.get("measurement_target") or "").strip());sources=Counter((a.get("entity_source") or "").strip() for a in audit if (a.get("entity_source") or "").strip())
    out={
        "schema_version":"2.2","source_of_truth":"final persisted CSV/JSON artifacts",
        "mentions_total":len(mentions),"mention_intent_distribution":dict(sorted(intents.items())),"positive_mentions":intents.get("recommended",0)+intents.get("listed",0),
        "metrics_rows":len(metrics),"metrics_target_distribution":dict(sorted(targets.items())),
        "target_audit_rows":len(audit),"target_audit_source_distribution":dict(sorted(sources.items())),"target_audit_confirmed":sum((a.get("review_status") or "")=="confirmed" for a in audit),
        "resolution_recheck_rows":len(resolution),"resolution_recheck_confirmed":sum((r.get("review_status") or "")=="confirmed" for r in resolution),
        "citation_audit_summary":citation,"robustness_summary":robust
    }
    (run/"measurement_qa_summary.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return out
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:o=build(a.run_dir);print(json.dumps(o,ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"build_measurement_qa_summary：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
