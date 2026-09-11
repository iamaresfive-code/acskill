#!/usr/bin/env python3
"""Build the single v2.2 report model used only by the DOCX renderer.

Market buckets are frozen by the confirmed Market Universe. Measurement target is a separate
axis and never reclassifies an institution into Expert/IP (or vice versa). Hybrid entities may
carry institution and IP target-specific metrics simultaneously.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def rcsv(p:Path):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def rjson(p:Path,default):
    if not p.is_file():return default
    return json.loads(p.read_text(encoding="utf-8"))
def rjsonl(p:Path):
    if not p.is_file():return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
def fnum(v):
    try:return float(v)
    except:return 0.0

def build(run:Path):
    meta=rjson(run/"run_metadata.json",{});u=rcsv(run/"market_universe.csv");emergent_rows=rcsv(run/"ai_emergent_entities.csv");metrics=rcsv(run/"ai_metrics.csv");assets=rcsv(run/"asset_scores.csv");concepts=rcsv(run/"concept_ownership.csv");evidence=rcsv(run/"evidence.csv");rechecks=rcsv(run/"rechecks.csv");analysis=rjson(run/"analysis.json",{})
    included=[x for x in u if x.get("universe_status")=="included"];observation=[x for x in u if x.get("universe_status") in {"observation","unresolved"}]
    groups={"national_benchmarks":[],"local_institutions":[],"expert_ip":[],"other_included":[]}
    for x in included:
        role=x.get("market_role");scope=x.get("market_scope")
        if role=="national-benchmark":groups["national_benchmarks"].append(x)
        elif role=="expert-ip":groups["expert_ip"].append(x)
        elif role in {"local-core","local-active"} and scope in {"local","regional"}:groups["local_institutions"].append(x)
        else:groups["other_included"].append(x)

    m_by={}
    for x in metrics:m_by[(x.get("entity_id"),x.get("measurement_target"))]=x
    a_by={x.get("entity_id"):x for x in assets}
    def preferred_target(row,group_name):
        declared=row.get("measurement_target") or ""
        if declared=="both":return "ip" if group_name=="expert_ip" else "institution"
        return declared if declared in {"institution","ip"} else ("ip" if group_name=="expert_ip" else "institution")
    def merge_rows(rows,group_name):
        out=[]
        for x in rows:
            y=dict(x);eid=x.get("entity_id");declared=x.get("measurement_target") or "";targets=["institution","ip"] if declared=="both" else [declared]
            target_metrics={t:m_by.get((eid,t),{}) for t in targets if t in {"institution","ip"}}
            pt=preferred_target(x,group_name);metric=target_metrics.get(pt) or {}
            y.update({k:v for k,v in metric.items() if k not in y or not y.get(k)})
            y["measurement_target_for_report"]=pt;y["target_metrics"]=target_metrics
            asset=a_by.get(eid) or {};y["asset_readiness"]=asset.get("asset_readiness","");y["asset_tier"]=asset.get("asset_tier","");y["owned_source_dependency"]=asset.get("owned_source_dependency","")
            out.append(y)
        return sorted(out,key=lambda r:(-fnum(r.get("nomination_rate")),-fnum(r.get("top3_rate")),r.get("canonical_name","") or ""))
    grouped={k:merge_rows(v,k) for k,v in groups.items()};obs_merged=merge_rows(observation,"observation")
    ai_visible_observation=[r for r in obs_merged if any(fnum(m.get("nomination_rate"))>0 for m in (r.get("target_metrics") or {}).values())]

    resolved_emergent=[];unresolved_emergent=[]
    for e in emergent_rows:
        x=dict(e);metric=m_by.get((e.get("entity_id"),e.get("measurement_target"))) or {};x.update({k:v for k,v in metric.items() if k not in x or not x.get(k)});x["universe_status"]="ai-emergent";x["measurement_target_for_report"]=e.get("measurement_target")
        (resolved_emergent if e.get("resolution_status")=="resolved" else unresolved_emergent).append(x)
    ai_visible_emergent=sorted([r for r in resolved_emergent if fnum(r.get("nomination_rate"))>0],key=lambda r:(-fnum(r.get("nomination_rate")),-fnum(r.get("top3_rate")),r.get("canonical_name","") or ""))
    engines=sorted({x.get("engine","") for x in rjsonl(run/"ai_answers.jsonl") if x.get("engine")});disagreements=[x for x in rechecks if x.get("disagreement","").lower() in {"1","true","yes","y","是"}];resolved=[x for x in disagreements if x.get("resolution","").strip()]
    title_region=meta.get("normalized_region") or meta.get("requested_region") or "地区";title=(f"{title_region}公考 GEO 竞争格局深度报告" if meta.get("research_mode")!="blind-discovery-scan" else f"{title_region}公考 GEO 公开网络发现扫描")
    summaries=list(analysis.get("executive_summary") or [])
    if not summaries:
        summaries.append(f"本次 Market Universe 共确认 {len(included)} 个正式研究主体，其中全国基准 {len(grouped['national_benchmarks'])} 个、本地/区域机构 {len(grouped['local_institutions'])} 个、Expert/IP {len(grouped['expert_ip'])} 个。")
        if engines:summaries.append(f"AI Answer Measurement 覆盖 {len(engines)} 个引擎/模型入口；提名率、Top3率和首提率均按显式 measurement_target 分母计算。")
        else:summaries.append("本次未形成可用 AI Answer Measurement，因此只能解释 GEO Asset Readiness。")
        if meta.get("query_variant_mode")=="semantic-retrieval-variants":summaries.append("本轮采用语义等价检索变体，稳定性指标解释为 Query/Retrieval Robustness，不等同于严格同条件随机重复。")
        if meta.get("context_isolation_level")=="programmatic":summaries.append("本轮仅实现程序性 fresh context，无法等同于 API 级物理上下文隔离；相关排名结论需保守解释。")
        if ai_visible_observation:summaries.append(f"另有 {len(ai_visible_observation)} 个 Stage 1 Observation 主体在真实 AI 回答中获得提名，已单独披露。")
        if ai_visible_emergent:summaries.append(f"AI Answer 自然带出 {len(ai_visible_emergent)} 个 Stage 1 Universe 外已解析主体，单独披露且不回写主榜。")
    model={"schema_version":"2.2","skill_version":"2.2","title":title,"subtitle":"Market Universe × AI Answer Measurement × GEO Asset Readiness","meta":meta,"kpis":{"included_entities":len(included),"national_benchmarks":len(grouped["national_benchmarks"]),"local_institutions":len(grouped["local_institutions"]),"expert_ip":len(grouped["expert_ip"]),"observation_entities":len(observation),"ai_visible_observation_entities":len(ai_visible_observation),"ai_emergent_entities":len(emergent_rows),"ai_visible_emergent_entities":len(ai_visible_emergent),"ai_engines":len(engines),"evidence_count":len(evidence),"definitions":{"included_entities":"经 Market Universe Confirmation 纳入正式研究的全部主体","national_benchmarks":"included 且 market_role=national-benchmark","local_institutions":"included 且 market_role=local-core/local-active 且 scope=local/regional；不再由 entity_type 重分组","expert_ip":"included 且 market_role=expert-ip；不再由 studio/person 类型自动重分组","observation_entities":"Stage 1 未进入正式比较、但仍保留 AI Measurement 的 observation/unresolved 主体","ai_visible_observation_entities":"Observation 中至少一个显式 measurement_target 获得正向提名的主体","ai_emergent_entities":"正式 Measurement 中由 AI 回答自然带出的 Universe 外主体","ai_visible_emergent_entities":"已解析并形成 AI Metrics 的 AI-emergent 主体"}},"executive_summary":summaries,"market_universe":grouped,"observation_group":obs_merged,"ai_visible_observation":ai_visible_observation,"ai_emergent_entities":resolved_emergent+unresolved_emergent,"ai_visible_emergent":ai_visible_emergent,"ai_visibility":{"national_benchmarks":grouped["national_benchmarks"],"local_institutions":grouped["local_institutions"],"expert_ip":grouped["expert_ip"],"other":grouped["other_included"]},"asset_readiness":sorted(assets,key=lambda r:fnum(r.get("asset_readiness")),reverse=True),"concept_map":concepts,"diagnoses":analysis.get("diagnoses",[]),"strategy":analysis.get("strategy",[]),"plan_90_days":analysis.get("plan_90_days",[]),"charts":{"universe":"charts/market-universe.png","national_visibility":"charts/ai-visibility-national.png","local_visibility":"charts/ai-visibility-local.png","ip_visibility":"charts/ai-visibility-ip.png","asset_readiness":"charts/asset-readiness.png","concept_ownership":"charts/concept-ownership.png"},"appendix":{"recheck":{"rows":len(rechecks),"disagreements":len(disagreements),"resolved_disagreements":len(resolved)},"research_assets":[x.name for x in run.iterdir() if x.is_file()],"methodology_notes":["User Seed 只保证研究，不影响任何 AI/资产指标。","Market Scope 不能由 Recall 反推。","Market Bucket 与 Measurement Target 是两条独立轴，Stage 2/3 不得用 entity_type 重写 Stage 1 分桶。","Hybrid entity 可 measurement_target=both，并分别保留 institution/IP 指标。","AI Answer Measurement 与 Open-Web SERP/页面提及物理分离。","Observation / unresolved 主体仍保留 AI Metrics。","公开网页用于解释 GEO 资产，不替代真实 AI 提名。"]}}
    (run/"report_model.json").write_text(json.dumps(model,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return model

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();build(a.run_dir);print(a.run_dir/"report_model.json");return 0
if __name__=="__main__":raise SystemExit(main())
