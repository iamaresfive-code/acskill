#!/usr/bin/env python3
"""Build the single v2.2 report model used only by the DOCX renderer."""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from pathlib import Path


def rcsv(p:Path):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjson(p:Path,default):
    if not p.is_file():return default
    return json.loads(p.read_text(encoding="utf-8"))
def rjsonl(p:Path):
    if not p.is_file():return []
    out=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():out.append(json.loads(line))
    return out
def fnum(v):
    try:return float(v)
    except:return 0.0

def build(run:Path):
    meta=rjson(run/"run_metadata.json",{});u=rcsv(run/"market_universe.csv");metrics=rcsv(run/"ai_metrics.csv");assets=rcsv(run/"asset_scores.csv");concepts=rcsv(run/"concept_ownership.csv");evidence=rcsv(run/"evidence.csv");rechecks=rcsv(run/"rechecks.csv");analysis=rjson(run/"analysis.json",{})
    included=[x for x in u if x.get("universe_status")=="included"];observation=[x for x in u if x.get("universe_status") in {"observation","unresolved"}]
    groups={"national_benchmarks":[],"local_institutions":[],"expert_ip":[],"other_included":[]}
    for x in included:
        role=x.get("market_role");et=x.get("entity_type")
        if role=="national-benchmark":groups["national_benchmarks"].append(x)
        elif role=="expert-ip" or et in {"teacher","ip","expert"}:groups["expert_ip"].append(x)
        elif x.get("market_scope") in {"local","regional"}:groups["local_institutions"].append(x)
        else:groups["other_included"].append(x)
    m_by={x.get("entity_id"):x for x in metrics};a_by={x.get("entity_id"):x for x in assets}
    def merge_rows(rows):
        out=[]
        for x in rows:
            y=dict(x);y.update({k:v for k,v in (m_by.get(x.get("entity_id")) or {}).items() if k not in y or not y.get(k)});asset=a_by.get(x.get("entity_id")) or {};y["asset_readiness"]=asset.get("asset_readiness","");y["asset_tier"]=asset.get("asset_tier","");y["owned_source_dependency"]=asset.get("owned_source_dependency","");out.append(y)
        return sorted(out,key=lambda r:(-fnum(r.get("nomination_rate")),-fnum(r.get("top3_rate")),r.get("canonical_name","") or ""))
    grouped={k:merge_rows(v) for k,v in groups.items()}
    engines=sorted({x.get("engine","") for x in rjsonl(run/"ai_answers.jsonl") if x.get("engine")})
    disagreements=[x for x in rechecks if x.get("disagreement","").lower() in {"1","true","yes","y","是"}];resolved=[x for x in disagreements if x.get("resolution","").strip()]
    counts=Counter(x.get("market_role") or "unclassified" for x in included)
    title_region=meta.get("normalized_region") or meta.get("requested_region") or "地区"
    title=(f"{title_region}公考 GEO 竞争格局深度报告" if meta.get("research_mode")!="blind-discovery-scan" else f"{title_region}公考 GEO 公开网络发现扫描")
    summaries=list(analysis.get("executive_summary") or [])
    if not summaries:
        summaries.append(f"本次 Market Universe 共确认 {len(included)} 个正式研究主体，其中全国基准 {len(grouped['national_benchmarks'])} 个、本地/区域机构 {len(grouped['local_institutions'])} 个、Expert/IP {len(grouped['expert_ip'])} 个。")
        if engines:summaries.append(f"AI Answer Measurement 覆盖 {len(engines)} 个引擎/模型入口；主排名以提名率、Top3率和首提率为透明指标，不以公开网页 SEO 命中替代 AI 提名。")
        else:summaries.append("本次未形成可用 AI Answer Measurement，因此报告只能解释 GEO Asset Readiness，不应被称为真实 AI GEO 排名。")
    model={
      "schema_version":"2.2","skill_version":"2.2","title":title,"subtitle":"Market Universe × AI Answer Measurement × GEO Asset Readiness","meta":meta,
      "kpis":{"included_entities":len(included),"national_benchmarks":len(grouped["national_benchmarks"]),"local_institutions":len(grouped["local_institutions"]),"expert_ip":len(grouped["expert_ip"]),"observation_entities":len(observation),"ai_engines":len(engines),"evidence_count":len(evidence),"definitions":{"included_entities":"经 Market Universe Confirmation 纳入正式研究的全部主体","observation_entities":"未进入正式比较、但需具名披露的 observation/unresolved 主体"}},
      "executive_summary":summaries,"market_universe":grouped,"observation_group":observation,
      "ai_visibility":{"national_benchmarks":grouped["national_benchmarks"],"local_institutions":grouped["local_institutions"],"expert_ip":grouped["expert_ip"],"other":grouped["other_included"]},
      "asset_readiness":sorted(assets,key=lambda r:fnum(r.get("asset_readiness")),reverse=True),"concept_map":concepts,"diagnoses":analysis.get("diagnoses",[]),"strategy":analysis.get("strategy",[]),"plan_90_days":analysis.get("plan_90_days",[]),
      "charts":{"universe":"charts/market-universe.png","national_visibility":"charts/ai-visibility-national.png","local_visibility":"charts/ai-visibility-local.png","ip_visibility":"charts/ai-visibility-ip.png","asset_readiness":"charts/asset-readiness.png","concept_ownership":"charts/concept-ownership.png"},
      "appendix":{"market_role_counts":dict(counts),"recheck":{"rows":len(rechecks),"disagreements":len(disagreements),"resolved_disagreements":len(resolved)},"research_assets":[x.name for x in run.iterdir() if x.is_file()],"methodology_notes":["User Seed 只保证研究，不影响任何 AI/资产指标。","Market Scope 不能由 Recall 反推。","AI Answer Measurement 与 Open-Web SERP/页面提及物理分离。","公开网页用于解释 GEO 资产，不替代真实 AI 提名。"]}
    }
    (run/"report_model.json").write_text(json.dumps(model,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return model

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();build(a.run_dir);print(a.run_dir/"report_model.json");return 0
if __name__=="__main__":raise SystemExit(main())
