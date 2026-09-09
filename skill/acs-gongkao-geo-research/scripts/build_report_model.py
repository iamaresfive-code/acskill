#!/usr/bin/env python3
"""从 v2.1 Run 数据构建统一 Report Model 的确定性骨架。分析结论可由 Agent 在此骨架上补充。"""
from __future__ import annotations
import argparse,csv,json
from collections import Counter
from pathlib import Path

def read_csv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def num(v):
    try:return float(v)
    except:return 0.0

def build(run:Path):
    meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8")); scores=read_csv(run/"scores.csv"); candidates=read_csv(run/"candidate_pool.csv"); entities=read_csv(run/"entities.csv"); queries=read_csv(run/"queries.csv"); results=read_csv(run/"query_results.csv"); evidence=read_csv(run/"evidence.csv"); ips=read_csv(run/"ip_entities.csv")
    inst_ids={r.get("entity_id") for r in entities if r.get("entity_type") in {"institution","brand"}}
    unique_inst={r.get("entity_id") for r in candidates if r.get("entity_id") in inst_ids}
    evaluable={r.get("entity_id") for r in candidates if r.get("entity_id") in inst_ids and r.get("status") in {"scored","evidence-insufficient"}}
    qinst=[q for q in queries if q.get("query_purpose")=="measurement" and q.get("measurement_target")=="institution" and q.get("status")=="sampled"]
    qip=[q for q in queries if q.get("query_purpose")=="measurement" and q.get("measurement_target")=="ip" and q.get("status")=="sampled"]
    top=sorted(scores,key=lambda r:num(r.get("total")),reverse=True)
    status=Counter(r.get("status") for r in candidates)
    model={
      "meta":meta,
      "title":f"{meta.get('observation_date','')} {meta.get('normalized_region') or meta.get('requested_region','')}公考 GEO 竞争格局深度报告".strip(),
      "subtitle":"生成式搜索环境下的品牌可见性 · 实体资产 · 答案占位 · 竞争机会",
      "kpis":{"independent_institutions":len(unique_inst),"evaluable_institutions":len(evaluable),"scored_institutions":len(scores),"institution_measurement_queries":len(qinst),"ip_measurement_queries":len(qip),"evidence_count":len(evidence),"entity_nodes":len(entities),"ip_entities":len(ips)},
      "executive_summary":[],
      "ranking":[{"rank":i+1,"entity_id":r.get("entity_id"),"institution":r.get("institution"),"total":num(r.get("total")),"tier":r.get("tier"),"confidence":r.get("evidence_confidence"),"competition_route":r.get("competition_route") or "待归纳"} for i,r in enumerate(top)],
      "scorecards":[{"entity_id":r.get("entity_id"),"institution":r.get("institution"),"total":num(r.get("total")),"tier":r.get("tier"),"route":r.get("competition_route") or "待归纳","strongest_asset":"由 score_details.json 归纳","largest_gap":"由 score_details.json 归纳"} for r in top],
      "diagnoses":[],"query_occupancy":[],"concept_gaps":[],"entry_strategy":[],"plan_90_days":[],"monthly_dashboard":[],
      "charts":{"ranking":"charts/geo-score-ranking.svg","authority_recall":"charts/authority-recall-matrix.svg","heatmap":"charts/dimension-heatmap.svg","funnel":"charts/candidate-funnel.svg"},
      "appendix":{"candidate_status":dict(status),"research_assets":["discovery_coverage.csv","candidate_pool.csv","entities.csv","entity_relations.csv","queries.csv","query_results.csv","evidence.csv","scores.csv","score_details.json","ip_entities.csv"]}
    }
    if top:
        lead=top[0]; model["executive_summary"].append(f"本次公开网络代理观察中，{lead.get('institution')} 的 GEO 观察指数最高，为 {lead.get('total')}（{lead.get('tier')}）。该结论仅反映本次公开网络与 AI 可利用资产结构，不代表教学质量或市场份额。")
    model["executive_summary"].append(f"本次共发现 {len(unique_inst)} 家独立机构候选，其中 {len(scores)} 家进入正式评分；机构 Measurement 共 {len(qinst)} 个无品牌问题。")
    path=run/"report_model.json"; path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return model

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args();build(a.run_dir);print(a.run_dir/"report_model.json");return 0
if __name__=="__main__":raise SystemExit(main())
