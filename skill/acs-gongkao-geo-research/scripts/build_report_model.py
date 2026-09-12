#!/usr/bin/env python3
"""Build the single v2.2 report model used only by the DOCX renderer.

Market buckets are frozen by the confirmed Market Universe. Measurement target is a separate
axis and never reclassifies an institution into Expert/IP (or vice versa). Hybrid entities,
including reviewed AI-emergent hybrids, may carry institution and IP metrics simultaneously.
All QA counts in the model are computed from final persisted files to avoid report/data drift.

Report Layer 追加（v2.2 Report Layer Completion）：
- measurement_protocol：把 run_metadata 的协议披露字段显式搬进报告模型，供 DOCX 强制披露；
- robustness：直接读取最终 robustness_summary.json，不手抄数字；
- risks：来自 analysis.json.limitations，并补齐协议/口径层面的固定局限；
- 报告层不得为空——空 analysis 会构建出空 diagnosis/strategy/plan，由 report validator 阻断。
"""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from pathlib import Path
from measurement_target_utils import expanded_target,effective_emergent_target

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

PROTOCOL_KEYS=("measurement_profile","sampling_mode","answer_context_mode_expected","context_isolation_level","query_variant_mode","repeat_runs_expected","fresh_context_required","fresh_context_note","page_collection_status","observation_date","ai_engines_sampled","ai_engine_notes")


def build_protocol(meta:dict,answers:list):
    proto={k:meta.get(k,"") for k in PROTOCOL_KEYS}
    stamps=sorted({str(a.get("sampled_at") or "") for a in answers if a.get("sampled_at")})
    proto["sampled_at_range"]=(f"{stamps[0]} → {stamps[-1]}" if stamps else "")
    proto["answer_cells"]=len(answers)
    proto["declarations"]=[]
    if str(meta.get("sampling_mode") or "")=="single-engine":proto["declarations"].append("本轮为单引擎测量，不得表述为跨模型共识。")
    if str(meta.get("answer_context_mode_expected") or "")=="external-search-augmented":proto["declarations"].append("本轮为外部检索增强条件下的 AI Answer Visibility，不等同模型原生参数记忆 Recall。")
    if str(meta.get("context_isolation_level") or "")=="programmatic":proto["declarations"].append("本轮仅实现程序性 fresh context，无法证明达到 API 级物理上下文重置。")
    if str(meta.get("query_variant_mode") or "")=="semantic-retrieval-variants":proto["declarations"].append("本轮使用语义等价检索变体，稳定性指标只能解释为 Query/Retrieval Robustness。")
    if str(meta.get("page_collection_status") or "")!="collected":proto["declarations"].append("本轮未采集网页正文，空的 page mention 表示未采集，不代表正文 0 提及。")
    return proto


def build_robustness(run:Path):
    return rjson(run/"robustness_summary.json",{})


def build_risks(analysis:dict,meta:dict,protocol:dict):
    risks=list(analysis.get("limitations") or [])
    for d in protocol.get("declarations") or []:
        if d not in risks:risks.append(d)
    return risks


def build(run:Path):
    meta=rjson(run/"run_metadata.json",{});u=rcsv(run/"market_universe.csv");emergent_rows=rcsv(run/"ai_emergent_entities.csv");metrics=rcsv(run/"ai_metrics.csv");mentions=rcsv(run/"ai_mentions.csv");assets=rcsv(run/"asset_scores.csv");concepts=rcsv(run/"concept_ownership.csv");evidence=rcsv(run/"evidence.csv");rechecks=rcsv(run/"rechecks.csv");resolution_rechecks=rcsv(run/"resolution_rechecks.csv");analysis=rjson(run/"analysis.json",{});answers=rjsonl(run/"ai_answers.jsonl")
    included=[x for x in u if x.get("universe_status")=="included"];observation=[x for x in u if x.get("universe_status") in {"observation","unresolved"}]
    groups={"national_benchmarks":[],"local_institutions":[],"expert_ip":[],"other_included":[]}
    for x in included:
        role=x.get("market_role");scope=x.get("market_scope")
        if role=="national-benchmark":groups["national_benchmarks"].append(x)
        elif role=="expert-ip":groups["expert_ip"].append(x)
        elif role in {"local-core","local-active"} and scope in {"local","regional"}:groups["local_institutions"].append(x)
        else:groups["other_included"].append(x)

    m_by={(x.get("entity_id"),x.get("measurement_target")):x for x in metrics};a_by={x.get("entity_id"):x for x in assets}
    def preferred_target(row,group_name):
        declared=row.get("measurement_target") or ""
        if declared=="both":return "ip" if group_name=="expert_ip" else "institution"
        return declared if declared in {"institution","ip"} else ("ip" if group_name=="expert_ip" else "institution")
    def merge_rows(rows,group_name):
        out=[]
        for x in rows:
            y=dict(x);eid=x.get("entity_id");declared=x.get("measurement_target") or "";targets=expanded_target(declared)
            target_metrics={t:m_by.get((eid,t),{}) for t in targets};pt=preferred_target(x,group_name);metric=target_metrics.get(pt) or {}
            y.update({k:v for k,v in metric.items() if k not in y or not y.get(k)});y["measurement_target_for_report"]=pt;y["target_metrics"]=target_metrics
            asset=a_by.get(eid) or {};y["asset_readiness"]=asset.get("asset_readiness","");y["asset_tier"]=asset.get("asset_tier","");y["owned_source_dependency"]=asset.get("owned_source_dependency","");out.append(y)
        return sorted(out,key=lambda r:(-fnum(r.get("nomination_rate")),-fnum(r.get("top3_rate")),r.get("canonical_name","") or ""))
    grouped={k:merge_rows(v,k) for k,v in groups.items()};obs_merged=merge_rows(observation,"observation")
    ai_visible_observation=[r for r in obs_merged if any(fnum(m.get("nomination_rate"))>0 for m in (r.get("target_metrics") or {}).values())]

    resolved_emergent=[];unresolved_emergent=[]
    for e in emergent_rows:
        x=dict(e);declared=effective_emergent_target(e);targets=expanded_target(declared);target_metrics={t:m_by.get((e.get("entity_id"),t),{}) for t in targets}
        # Emergent entities are disclosed separately. For compact table sorting, use the highest observed target metric, while preserving every target in target_metrics.
        metric=max(target_metrics.values(),key=lambda m:fnum(m.get("nomination_rate"))) if target_metrics else {}
        x.update({k:v for k,v in metric.items() if k not in x or not x.get(k)});x["universe_status"]="ai-emergent";x["measurement_target_for_report"]=declared;x["target_metrics"]=target_metrics
        asset=a_by.get(e.get("entity_id")) or {}
        x["asset_readiness"]=asset.get("asset_readiness","");x["asset_tier"]=asset.get("asset_tier","");x["owned_source_dependency"]=asset.get("owned_source_dependency","")
        (resolved_emergent if e.get("resolution_status")=="resolved" else unresolved_emergent).append(x)
    ai_visible_emergent=sorted([r for r in resolved_emergent if any(fnum(m.get("nomination_rate"))>0 for m in (r.get("target_metrics") or {}).values())],key=lambda r:(-max([fnum(m.get("nomination_rate")) for m in (r.get("target_metrics") or {}).values()] or [0]),r.get("canonical_name","") or ""))
    engines=sorted({x.get("engine","") for x in answers if x.get("engine")});disagreements=[x for x in rechecks if x.get("disagreement","").lower() in {"1","true","yes","y","是"}];resolved=[x for x in disagreements if x.get("resolution","").strip()]
    intent_distribution=dict(sorted(Counter((m.get("mention_intent") or "").strip() for m in mentions if (m.get("mention_intent") or "").strip()).items()))
    positive_mentions=sum(intent_distribution.get(x,0) for x in ("recommended","listed"));resolution_risk_count=len(resolution_rechecks);resolution_confirmed=sum((r.get("review_status") or "")=="confirmed" for r in resolution_rechecks)
    title_region=meta.get("normalized_region") or meta.get("requested_region") or "地区";title=(f"{title_region}公考 GEO 竞争格局深度报告" if meta.get("research_mode")!="blind-discovery-scan" else f"{title_region}公考 GEO 公开网络发现扫描")
    protocol=build_protocol(meta,answers);robustness=build_robustness(run);risks=build_risks(analysis,meta,protocol)
    summaries=list(analysis.get("executive_summary") or [])
    if not summaries:
        summaries.append(f"本次 Market Universe 共确认 {len(included)} 个正式研究主体，其中全国基准 {len(grouped['national_benchmarks'])} 个、本地/区域机构 {len(grouped['local_institutions'])} 个、Expert/IP {len(grouped['expert_ip'])} 个。")
        if engines:summaries.append(f"AI Answer Measurement 覆盖 {len(engines)} 个引擎/模型入口；提名率、Top3率和首提率均按显式 measurement_target 分母计算。")
        else:summaries.append("本次未形成可用 AI Answer Measurement，因此只能解释 GEO Asset Readiness。")
        if meta.get("query_variant_mode")=="semantic-retrieval-variants":summaries.append("本轮采用语义等价检索变体，稳定性指标解释为 Query/Retrieval Robustness，不等同于严格同条件随机重复。")
        if meta.get("context_isolation_level")=="programmatic":summaries.append("本轮仅实现程序性 fresh context，无法等同于 API 级物理上下文隔离；相关排名结论需保守解释。")
        if ai_visible_observation:summaries.append(f"另有 {len(ai_visible_observation)} 个 Stage 1 Observation 主体在真实 AI 回答中获得提名，已单独披露。")
        if ai_visible_emergent:summaries.append(f"AI Answer 自然带出 {len(ai_visible_emergent)} 个 Stage 1 Universe 外已解析主体，单独披露且不回写主榜。")
    model={
        "schema_version":"2.2","skill_version":"2.2","title":title,"subtitle":"Market Universe × AI Answer Measurement × GEO Asset Readiness","meta":meta,
        "kpis":{"included_entities":len(included),"national_benchmarks":len(grouped["national_benchmarks"]),"local_institutions":len(grouped["local_institutions"]),"expert_ip":len(grouped["expert_ip"]),"observation_entities":len(observation),"ai_visible_observation_entities":len(ai_visible_observation),"ai_emergent_entities":len(emergent_rows),"ai_visible_emergent_entities":len(ai_visible_emergent),"ai_engines":len(engines),"evidence_count":len(evidence),"definitions":{"included_entities":"经 Market Universe Confirmation 纳入正式研究的全部主体","national_benchmarks":"included 且 market_role=national-benchmark","local_institutions":"included 且 market_role=local-core/local-active 且 scope=local/regional；不再由 entity_type 重分组","expert_ip":"included 且 market_role=expert-ip；不再由 studio/person 类型自动重分组","observation_entities":"Stage 1 未进入正式比较、但仍保留 AI Measurement 的 observation/unresolved 主体","ai_visible_observation_entities":"Observation 中至少一个显式 measurement_target 获得正向提名的主体","ai_emergent_entities":"正式 Measurement 中由 AI 回答自然带出的 Universe 外主体","ai_visible_emergent_entities":"已解析并形成 AI Metrics 的 AI-emergent 主体"}},
        "executive_summary":summaries,"measurement_protocol":protocol,"market_universe":grouped,"observation_group":obs_merged,"ai_visible_observation":ai_visible_observation,"ai_emergent_entities":resolved_emergent+unresolved_emergent,"ai_visible_emergent":ai_visible_emergent,
        "ai_visibility":{"national_benchmarks":grouped["national_benchmarks"],"local_institutions":grouped["local_institutions"],"expert_ip":grouped["expert_ip"],"other":grouped["other_included"]},
        "robustness":robustness,"asset_readiness":sorted(assets,key=lambda r:fnum(r.get("asset_readiness")),reverse=True),"concept_map":concepts,
        "measurement_qa":{"annotation_intent_distribution":intent_distribution,"positive_mentions":positive_mentions,"resolution_recheck_rows":resolution_risk_count,"resolution_recheck_confirmed":resolution_confirmed},
        "diagnoses":analysis.get("diagnoses",[]),"strategy":analysis.get("strategy",[]),"plan_90_days":analysis.get("plan_90_days",[]),"risks":risks,
        "charts":{"universe":"charts/market-universe.png","national_visibility":"charts/ai-visibility-national.png","local_visibility":"charts/ai-visibility-local.png","ip_visibility":"charts/ai-visibility-ip.png","asset_readiness":"charts/asset-readiness.png","concept_ownership":"charts/concept-ownership.png"},
        "appendix":{"recheck":{"rows":len(rechecks),"disagreements":len(disagreements),"resolved_disagreements":len(resolved)},"resolution_recheck":{"rows":resolution_risk_count,"confirmed":resolution_confirmed},"annotation_intent_distribution":intent_distribution,"research_assets":[x.name for x in run.iterdir() if x.is_file()],"methodology_notes":["User Seed 只保证研究，不影响任何 AI/资产指标。","Market Scope 不能由 Recall 反推。","Market Bucket 与 Measurement Target 是两条独立轴，Stage 2/3 不得用 entity_type 重写 Stage 1 分桶。","Hybrid entity（含 reviewed AI-emergent hybrid）可 measurement_target=both，并分别保留 institution/IP 指标。","AI Answer Measurement 与 Open-Web SERP/页面提及物理分离。","Annotation Review 与 Entity Resolution Recheck 分离。","Observation / unresolved 主体仍保留 AI Metrics。","公开网页用于解释 GEO 资产，不替代真实 AI 提名。","Asset Readiness 只统计可核验公开证据；未取到证据的维度记为 unknown，不得解释为主体一定没有。","Concept Ownership 只来自可核验公开内容绑定，单次偶发提及不得包装为强绑定。","GEO 不代表教学质量、通过率、招生量、市场份额或一般口碑。"]}}
    (run/"report_model.json").write_text(json.dumps(model,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return model

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();build(a.run_dir);print(a.run_dir/"report_model.json");return 0
if __name__=="__main__":raise SystemExit(main())
