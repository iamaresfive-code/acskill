#!/usr/bin/env python3
"""Build the deterministic GEO v2.1.1 Report Model from current-run data only."""
from __future__ import annotations
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlparse

DIMENSIONS=[("query_coverage",30,"泛词覆盖"),("entity_clarity",25,"实体清晰"),("external_diversity",20,"外部来源多样性"),("concept_ownership",15,"概念占位"),("freshness",10,"内容新鲜度")]
TRUE={"1","true","yes","y","是"}

def read_csv(p:Path):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def num(v,default=0.0):
    try:return float(v)
    except:return default
def split(v):
    import re
    return [x.strip() for x in re.split(r"[|｜;,，；]",v or "") if x.strip()]
def domain(url):return urlparse(url or "").netloc.lower().removeprefix("www.")

def recall_map(queries,results,target="institution"):
    qids={q.get("query_id") for q in queries if q.get("query_purpose")=="measurement" and q.get("measurement_target")==target and q.get("status")=="sampled"}
    hits=defaultdict(set)
    for r in results:
        if r.get("query_id") in qids and r.get("matched","").lower() in TRUE and r.get("counts_as_measurement_hit","").lower() in TRUE and r.get("entity_id"):
            hits[r["entity_id"]].add(r["query_id"])
    den=len(qids)
    return {eid:(len(v),den,(len(v)/den if den else 0.0)) for eid,v in hits.items()},den

def derive_route(score,recall,authority,owned_ratio):
    route=(score.get("competition_route") or "").strip()
    if route and route not in {"待归纳","unknown","n/a","N/A"}:return route
    total=num(score.get("total"));rec=recall;auth=authority
    if rec>=.65 and auth>=60:return "成熟占位型"
    if rec>=.65 and owned_ratio>=.60:return "SEO/自有资产占位型"
    if rec<.35 and auth>=60:return "高权威低召回型"
    if rec>=.40 and auth<45:return "主动铺量型"
    if total>=70:return "全国品牌权重型"
    if rec<.35:return "本地实体待扩召回型"
    return "本地实体型"

def dimension_summary(score,details):
    dims=(details or {}).get("dimensions",{}) if isinstance(details,dict) else {}
    values=[]
    for field,maxv,label in DIMENSIONS:
        raw=num(score.get(field));pct=raw/maxv if maxv else 0
        reason=(dims.get(field) or {}).get("reason","") if isinstance(dims,dict) else ""
        values.append((pct,label,reason,raw,maxv))
    hi=max(values,key=lambda x:x[0]);lo=min(values,key=lambda x:x[0])
    strongest=f"{hi[1]} {hi[3]:g}/{hi[4]}"+(f"：{hi[2]}" if hi[2] else "")
    gap=f"{lo[1]} {lo[3]:g}/{lo[4]}"+(f"：{lo[2]}" if lo[2] else "")
    return strongest,gap

def source_dependency(scores,entities,evidence):
    emap={e.get("entity_id"):e for e in entities};by=defaultdict(list)
    for e in evidence:
        if e.get("counting_scope","").lower()!="ignored":by[e.get("entity_id")].append(e)
    out={}
    for s in scores:
        eid=s.get("entity_id");official=(emap.get(eid) or {}).get("official_domain","").lower().removeprefix("www.");rows=by[eid]
        own=sum(1 for e in rows if official and domain(e.get("source_url"))==official)
        out[eid]=round(own/len(rows),4) if rows else 0.0
    return out

def build(run:Path):
    meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8"));scores=read_csv(run/"scores.csv");candidates=read_csv(run/"candidate_pool.csv");entities=read_csv(run/"entities.csv");queries=read_csv(run/"queries.csv");results=read_csv(run/"query_results.csv");evidence=read_csv(run/"evidence.csv");ips=read_csv(run/"ip_entities.csv");coverage=read_csv(run/"discovery_coverage.csv")
    try:details=json.loads((run/"score_details.json").read_text(encoding="utf-8"))
    except Exception:details=[]
    dmap={x.get("entity_id"):x for x in details if isinstance(x,dict)} if isinstance(details,list) else {}
    emap={e.get("entity_id"):e for e in entities};inst_ids={r.get("entity_id") for r in entities if r.get("entity_type") in {"institution","brand"}}
    unique_inst={r.get("entity_id") for r in candidates if r.get("entity_id") in inst_ids};evaluable={r.get("entity_id") for r in candidates if r.get("entity_id") in inst_ids and r.get("status") in {"scored","evidence-insufficient"}}
    inst_recall,inst_den=recall_map(queries,results,"institution");ip_recall,ip_den=recall_map(queries,results,"ip")
    top=sorted(scores,key=lambda r:num(r.get("total")),reverse=True);status=Counter(r.get("status") for r in candidates);dep=source_dependency(scores,entities,evidence)
    scorecards=[];ranking=[]
    for i,r in enumerate(top,1):
        eid=r.get("entity_id");hits,den,rec=inst_recall.get(eid,(0,inst_den,0.0));auth=num(r.get("authority_index"));strong,gap=dimension_summary(r,dmap.get(eid));route=derive_route(r,rec,auth,dep.get(eid,0))
        ranking.append({"rank":i,"entity_id":eid,"institution":r.get("institution"),"total":num(r.get("total")),"tier":r.get("tier"),"confidence":r.get("evidence_confidence"),"recall_hits":hits,"recall_queries":den,"recall_rate":round(rec,4),"authority_index":auth,"owned_source_dependency_ratio":dep.get(eid,0),"competition_route":route})
        scorecards.append({"entity_id":eid,"institution":r.get("institution"),"total":num(r.get("total")),"tier":r.get("tier"),"route":route,"strongest_asset":strong,"largest_gap":gap,"recall_rate":round(rec,4),"authority_index":auth,"owned_source_dependency_ratio":dep.get(eid,0)})
    observation=[]
    for c in candidates:
        if c.get("status") not in {"evidence-insufficient","unresolved"}:continue
        eid=c.get("entity_id");e=emap.get(eid,{})
        missing=[]
        if not e.get("legal_name"):missing.append("工商/法律主体")
        if not e.get("official_domain"):missing.append("官网域名")
        if not e.get("official_account"):missing.append("官方账号")
        observation.append({"entity_id":eid,"name":c.get("display_name") or e.get("canonical_name"),"candidate_type":c.get("candidate_type"),"status":c.get("status"),"user_specified":c.get("user_specified","").lower() in TRUE,"missing":missing,"reason":c.get("notes") or c.get("exclusion_reason") or ("证据不足，未进入正式评分" if c.get("status")=="evidence-insufficient" else "实体尚未完成解析")})
    ip_rows=[]
    for ip in ips:
        eid=ip.get("entity_id","");hits,den,rec=ip_recall.get(eid,(int(num(ip.get("ip_hits"))),ip_den,num(ip.get("ip_recall"))))
        if den==0:den=int(num(ip.get("ip_queries")));rec=(hits/den if den else num(ip.get("ip_recall")))
        ip_rows.append({"entity_id":eid,"teacher_name":ip.get("teacher_name"),"institution":ip.get("institution"),"ip_hits":hits,"ip_queries":den,"ip_recall":round(rec,4),"subjects":ip.get("subjects",""),"platforms":ip.get("platforms",""),"concepts":ip.get("concepts",""),"evidence_confidence":ip.get("evidence_confidence",""),"source_ids":split(ip.get("source_ids",""))})
    ip_rows.sort(key=lambda x:(x["ip_recall"],x["ip_hits"]),reverse=True)
    for i,row in enumerate(ip_rows,1):row["rank"]=i
    query_audit=[]
    for q in queries:
        if q.get("query_purpose")!="measurement" or q.get("measurement_target")!="institution" or q.get("status")!="sampled":continue
        qid=q.get("query_id");matched={r.get("entity_id") for r in results if r.get("query_id")==qid and r.get("matched","").lower() in TRUE and r.get("counts_as_measurement_hit","").lower() in TRUE and r.get("entity_id")}
        query_audit.append({"query_id":qid,"query_text":q.get("query_text"),"theme":q.get("theme"),"matched_entities":len(matched)})
    assets=["run_metadata.json","discovery_coverage.csv","candidate_pool.csv","entities.csv","entity_relations.csv","queries.csv","query_results.csv","evidence.csv","scores.csv","score_details.json","ip_entities.csv","charts/chart_data.json"]
    model={"schema_version":"2.1.1","meta":meta,"title":f"{meta.get('observation_date','')} {meta.get('normalized_region') or meta.get('requested_region','')}公考 GEO 竞争格局深度报告".strip(),"subtitle":"生成式搜索环境下的品牌可见性 · 实体资产 · 答案占位 · 竞争机会","kpis":{"independent_institutions":len(unique_inst),"evaluable_institutions":len(evaluable),"scored_institutions":len(scores),"institution_measurement_queries":inst_den,"ip_measurement_queries":ip_den,"evidence_count":len(evidence),"entity_nodes":len(entities),"ip_entities":len(ips),"observation_entities":len(observation)},"executive_summary":[],"ranking":ranking,"scorecards":scorecards,"diagnoses":[],"observation_group":observation,"ip_measurement":{"executed":ip_den>0,"query_count":ip_den,"rows":ip_rows,"note":"IP Measurement 与机构总榜分离，不使用机构五维总分。" if ip_den else "本次未执行 IP Measurement，仅作 Expert Entity 观察。"},"query_occupancy":query_audit,"concept_gaps":[],"entry_strategy":[],"plan_90_days":[],"monthly_dashboard":[],"charts":{"ranking":"charts/geo-score-ranking.svg","authority_recall":"charts/authority-recall-matrix.svg","heatmap":"charts/dimension-heatmap.svg","funnel":"charts/candidate-funnel.svg"},"appendix":{"candidate_status":dict(status),"candidate_status_note":"所有 evidence-insufficient / unresolved 主体必须在观察组披露，不得静默消失。","research_assets":assets,"research_audit":{"sampling_mode":meta.get("sampling_mode","public-web-proxy"),"semantic_coverage_gate":bool(meta.get("semantic_coverage_gate")),"saturation_gate":bool(meta.get("saturation_gate")),"local_ecosystem_gate":bool(meta.get("local_ecosystem_gate")),"candidate_pool_frozen":bool(meta.get("candidate_pool_frozen")),"coverage_rows":len(coverage),"institution_measurement_queries":inst_den,"ip_measurement_queries":ip_den,"evidence_count":len(evidence)},"query_results_summary":{"measurement_rows":len(query_audit),"result_rows":len(results)}}}
    if top:
        lead=top[0];model["executive_summary"].append(f"本次公开网络代理观察中，{lead.get('institution')} 的 GEO 观察指数最高，为 {lead.get('total')}（{lead.get('tier')}）。该结论仅反映本次公开网络与 AI 可利用资产结构，不代表教学质量或市场份额。")
    model["executive_summary"].append(f"本次共发现 {len(unique_inst)} 家独立机构候选，其中 {len(scores)} 家进入正式评分，{len(observation)} 家/主体进入证据不足或未解析观察组；机构 Measurement 共 {inst_den} 个无品牌问题。")
    if ip_den:model["executive_summary"].append(f"本次同时执行 {ip_den} 个 IP Measurement 问题，识别 {len(ip_rows)} 个 Expert/IP 实体；IP 结果单独展示，不与机构总榜混算。")
    path=run/"report_model.json";path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return model

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();build(a.run_dir);print(a.run_dir/"report_model.json");return 0
if __name__=="__main__":raise SystemExit(main())
