#!/usr/bin/env python3
"""Focused Stage 2.4 regression: emergent Target Closure + resolution risk + final-data QA."""
from __future__ import annotations
import csv,json,tempfile
from pathlib import Path
from prepare_measurement_target_audit import prepare as prepare_targets
from apply_measurement_target_audit import apply as apply_targets
from prepare_resolution_rechecks import prepare as prepare_resolution
from prepare_annotation_tasks import main_build as prepare_annotation
from compute_ai_metrics import compute as compute_metrics
from compute_variant_robustness import compute as compute_robustness
from validation_target_closure import validate_target_closure
from build_measurement_qa_summary import build as build_qa
from build_report_model import build as build_report


def wcsv(p,fields,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def wjsonl(p,rows):p.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")

def fixture(r:Path):
    meta={"schema_version":"2.2","skill_version":"2.2","official_output_format":"docx","requested_region":"示例省","normalized_region":"示例省","research_scope":"示例省","seed_entities":["中公"],"research_mode":"scoped-geo-landscape","market_universe_confirmed":True,"measurement_allowed":True,"measurement_profile":"release","query_variant_mode":"exact-query-repeat"}
    (r/"run_metadata.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
    uf=["entity_id","canonical_name","aliases","entity_type","measurement_target","user_seed","discovery_origin","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","universe_status","confirmation_status","downgrade_reason","notes"]
    wcsv(r/"market_universe.csv",uf,[dict(zip(uf,["I1","中公","中公教育","institution","institution","true","user-seed","local","示例省","local-core","active","false","本地机构","included","confirmed","",""]))])
    xf=["entity_id","canonical_name","aliases","measurement_target","market_scope","operating_region","resolution_status","source_answer_ids","source_result_ids","notes"]
    wcsv(r/"ai_emergent_entities.csv",xf,[
        {"entity_id":"X1","canonical_name":"新星品牌","aliases":"新星老师","measurement_target":"institution","market_scope":"local","operating_region":"示例省","resolution_status":"resolved","source_answer_ids":"A-M1|A-P1","source_result_ids":"","notes":"品牌与老师入口并存"},
        {"entity_id":"XU","canonical_name":"未解析新星","aliases":"","measurement_target":"ip","market_scope":"unknown","operating_region":"","resolution_status":"unresolved","source_answer_ids":"A-P1","source_result_ids":"","notes":"保持 unresolved，不进入正式 metrics"}
    ])
    qf=["query_id","query_text","query_group","measurement_target","region","status"]
    wcsv(r/"queries.csv",qf,[{"query_id":"M1","query_text":"示例省机构推荐","query_group":"综合","measurement_target":"institution","region":"示例省","status":"sampled"},{"query_id":"P1","query_text":"示例省老师推荐","query_group":"综合","measurement_target":"ip","region":"示例省","status":"sampled"}])
    answers=[{"answer_id":"A-M1","query_id":"M1","engine":"a","model":"a","sample_run":1,"query_variant_id":"canonical","context_id":"c1","fresh_context":True,"answer_context_mode":"native","sampled_at":"2026-09-12","response_text":"推荐新星品牌。本次检索中公职一对一师资未公开。","citations":[],"notes":""},{"answer_id":"A-P1","query_id":"P1","engine":"a","model":"a","sample_run":1,"query_variant_id":"canonical","context_id":"c2","fresh_context":True,"answer_context_mode":"native","sampled_at":"2026-09-12","response_text":"新星老师可以关注。","citations":[],"notes":""}]
    wjsonl(r/"ai_answers.jsonl",answers)
    raw=[{"mention_id":"AM1","answer_id":"A-M1","query_id":"M1","measurement_target":"institution","entity_id":"X1","canonical_name":"新星品牌","mentioned_name":"新星品牌","mention_rank":1},{"mention_id":"AM2","answer_id":"A-P1","query_id":"P1","measurement_target":"ip","entity_id":"X1","canonical_name":"新星品牌","mentioned_name":"新星老师","mention_rank":1},{"mention_id":"AM3","answer_id":"A-M1","query_id":"M1","measurement_target":"institution","entity_id":"I1","canonical_name":"中公","mentioned_name":"中公","mention_rank":2}]
    (r/"mentions_raw.json").write_text(json.dumps(raw,ensure_ascii=False),encoding="utf-8")
    mf=["mention_id","answer_id","entity_id","mention_rank","nomination_rank","mentioned_name","match_method","resolution_status","mention_intent","top3","first_mention","entity_correct","citation_linked","citation_refs","concepts","notes"]
    wcsv(r/"ai_mentions.csv",mf,[{"mention_id":"AM1","answer_id":"A-M1","entity_id":"X1","mention_rank":"1","nomination_rank":"1","mentioned_name":"新星品牌","match_method":"explicit-name","resolution_status":"resolved","mention_intent":"recommended","top3":"true","first_mention":"true","entity_correct":"true","citation_linked":"false","citation_refs":"","concepts":"","notes":""},{"mention_id":"AM2","answer_id":"A-P1","entity_id":"X1","mention_rank":"1","nomination_rank":"1","mentioned_name":"新星老师","match_method":"verified-alias","resolution_status":"resolved","mention_intent":"listed","top3":"true","first_mention":"true","entity_correct":"true","citation_linked":"false","citation_refs":"","concepts":"","notes":""},{"mention_id":"AM3","answer_id":"A-M1","entity_id":"I1","mention_rank":"2","nomination_rank":"","mentioned_name":"中公","match_method":"explicit-name","resolution_status":"resolved","mention_intent":"comparison","top3":"false","first_mention":"false","entity_correct":"false","citation_linked":"false","citation_refs":"","concepts":"","notes":"substring false positive"}])
    # Simulate Stage 2.3 legacy audit: Universe was reviewed, emergents were not yet included.
    legacy_fields=["entity_id","canonical_name","new_explicit_target","evidence_basis","reviewer_reason","review_status"]
    wcsv(r/"measurement_target_audit.csv",legacy_fields,[{"entity_id":"I1","canonical_name":"中公","new_explicit_target":"institution","evidence_basis":"prior Stage2.3 Universe review","reviewer_reason":"reviewed","review_status":"confirmed"}])

def _closure(r:Path,metrics=None):
    meta=json.loads((r/"run_metadata.json").read_text());issues=[];universe=rcsv(r/"market_universe.csv");emergent=rcsv(r/"ai_emergent_entities.csv");metrics=rcsv(r/"ai_metrics.csv") if metrics is None else metrics
    validate_target_closure(r,meta,issues,universe,metrics,emergent);return issues

def main():
    checks=0
    with tempfile.TemporaryDirectory() as td:
        r=Path(td);fixture(r)
        _,summary=prepare_targets(r);assert summary["universe_rows"]==1 and summary["resolved_emergent_rows"]==1 and summary["preserved_confirmed_rows"]==1 and summary["needs_review_rows"]==1;checks+=1
        audit=rcsv(r/"measurement_target_audit.csv");assert {a["entity_id"] for a in audit}=={"I1","X1"};i1=next(a for a in audit if a["entity_id"]=="I1");assert i1["review_status"]=="confirmed" and i1["entity_source"]=="universe";checks+=1
        # Release must fail before resolved emergent Target Review is confirmed/applied.
        early=_closure(r,[]);assert any(i.code in {"emergent-target-closure-not-reviewed","target-audit-unreviewed"} for i in early);checks+=1
        for a in audit:
            if a["review_status"]=="confirmed":continue
            a["new_explicit_target"]="both" if a["entity_id"]=="X1" else "institution";a["evidence_basis"]="synthetic reviewed evidence";a["reviewer_reason"]="cross-target brand + teacher entry" if a["hybrid_signal"]=="true" else "reviewed";a["review_status"]="confirmed"
        wcsv(r/"measurement_target_audit.csv",list(audit[0]),audit);applied=apply_targets(r);assert applied["resolved_emergent_rows"]==1 and applied["emergent_both"]==1
        emergent=rcsv(r/"ai_emergent_entities.csv");x=next(z for z in emergent if z["entity_id"]=="X1");assert x["measurement_target"]=="both" and x["reviewed_measurement_target"]=="both";checks+=1
        rows=compute_metrics(r);xrows=[m for m in rows if m["entity_id"]=="X1"];assert {m["measurement_target"] for m in xrows}=={"institution","ip"};assert {int(m["answer_cells"]) for m in xrows}=={1};assert not any(m["entity_id"]=="XU" for m in rows);checks+=1
        compute_robustness(r);vr=[z for z in rcsv(r/"variant_robustness.csv") if z["entity_id"]=="X1"];assert {z["measurement_target"] for z in vr}=={"institution","ip"};checks+=1
        _,_,sus=prepare_annotation(r);tasks=[json.loads(line) for line in (r/"annotation_tasks.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()];am3=next(t for t in tasks if t["mention_id"]=="AM3");assert sus>=1 and am3["substring_suspicion"] is True;checks+=1
        # Resolution audit is an independent release gate.
        missing_resolution=_closure(r);assert any(i.code=="missing-resolution-rechecks" for i in missing_resolution);checks+=1
        _,rs=prepare_resolution(r);assert rs["risk_rows"]>=2 and rs["short_name_boundary_rows"]>=1
        rr=rcsv(r/"resolution_rechecks.csv");unreviewed=_closure(r);assert any(i.code=="resolution-recheck-unreviewed" for i in unreviewed);checks+=1
        mention_by={m["mention_id"]:m for m in rcsv(r/"ai_mentions.csv")}
        for z in rr:
            m=mention_by[z["mention_id"]];z["reviewer_resolution_status"]=m["resolution_status"];z["reviewer_entity_correct"]="true" if m["entity_correct"].lower()=="true" else "false";z["disagreement"]="false";z["resolution_outcome"]="confirmed-existing";z["resolution"]="independent targeted resolution review confirmed current state";z["reviewer"]="stage24-test";z["review_status"]="confirmed"
        wcsv(r/"resolution_rechecks.csv",list(rr[0]),rr)
        issues=_closure(r);assert not [i for i in issues if i.level=="error"],[(i.code,i.message) for i in issues];checks+=1
        qa=build_qa(r);assert qa["mention_intent_distribution"]=={"comparison":1,"listed":1,"recommended":1};model=build_report(r);assert model["measurement_qa"]["annotation_intent_distribution"]==qa["mention_intent_distribution"] and model["appendix"]["annotation_intent_distribution"]==qa["mention_intent_distribution"];checks+=1
        bad=[m for m in rows if not (m["entity_id"]=="X1" and m["measurement_target"]=="ip")];issues=_closure(r,bad);assert any(i.code=="target-closure-metric-missing" for i in issues);checks+=1
    # Snapshot policy: robustness is optional, but if explicitly invoked it must still have explicit
    # native/sidecar variant evidence; there is no run-{sample_run} fallback.
    with tempfile.TemporaryDirectory() as td:
        r=Path(td);fixture(r);meta=json.loads((r/"run_metadata.json").read_text());meta["measurement_profile"]="snapshot";(r/"run_metadata.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
        answers=[json.loads(x) for x in (r/"ai_answers.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        for a in answers:a.pop("query_variant_id",None)
        wjsonl(r/"ai_answers.jsonl",answers)
        try:compute_robustness(r);raise AssertionError("snapshot robustness must require explicit variant evidence when invoked")
        except ValueError as e:assert "query_variant_id" in str(e);checks+=1
    print(f"PASS: Stage 2.4 Target Closure focused regression ({checks} checks)")
    return 0
if __name__=="__main__":raise SystemExit(main())
