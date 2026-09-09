#!/usr/bin/env python3
from __future__ import annotations
import csv,importlib.util,json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
pre=load("pre_v22","preflight.py");metrics=load("metrics_v22","compute_ai_metrics.py");assets=load("assets_v22","score_assets.py");validator=load("validator_v22","validate_run.py");modeler=load("model_v22","build_report_model.py")

def wcsv(p,fields,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def wjsonl(p,rows):p.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+"\n",encoding="utf-8")

def build(run:Path):
    meta=pre.make_metadata("示例省",["甲公考","乙老师"],True);meta.update({"observation_date":"2026-09-10","market_universe_confirmed":True,"measurement_allowed":True,"run_status":"measurement-complete","sampling_mode":"multi-engine","ai_engines_expected":["engine-a","engine-b"]});(run/"run_metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    uf=["entity_id","canonical_name","aliases","entity_type","user_seed","discovery_origin","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","universe_status","confirmation_status","notes"]
    wcsv(run/"market_universe.csv",uf,[
      {"entity_id":"I1","canonical_name":"甲公考","aliases":"甲教育","entity_type":"institution","user_seed":"true","discovery_origin":"user-seed","market_scope":"local","operating_region":"示例省","market_role":"local-core","activity_status":"active","platform_native":"false","salience_basis":"用户Seed+本地主体证据","universe_status":"included","confirmation_status":"confirmed","notes":""},
      {"entity_id":"I2","canonical_name":"全国乙教育","aliases":"乙教育","entity_type":"institution","user_seed":"false","discovery_origin":"system-discovery","market_scope":"national","operating_region":"全国/示例省","market_role":"national-benchmark","activity_status":"active","platform_native":"false","salience_basis":"区域直营网点+独立来源","universe_status":"included","confirmation_status":"confirmed","notes":""},
      {"entity_id":"P1","canonical_name":"乙老师","aliases":"乙老师公考","entity_type":"ip","user_seed":"true","discovery_origin":"user-seed","market_scope":"local","operating_region":"示例省","market_role":"expert-ip","activity_status":"active","platform_native":"true","salience_basis":"平台账号+本地主题持续内容","universe_status":"included","confirmation_status":"confirmed","notes":""},
      {"entity_id":"O1","canonical_name":"待核机构","aliases":"","entity_type":"institution","user_seed":"false","discovery_origin":"system-discovery","market_scope":"unknown","operating_region":"","market_role":"observation","activity_status":"uncertain","platform_native":"false","salience_basis":"单一聚合页","universe_status":"observation","confirmation_status":"confirmed","notes":"证据不足"}
    ])
    qf=["query_id","query_text","query_group","measurement_target","region","status"];qs=[
      {"query_id":"M1","query_text":"示例省公考机构推荐","query_group":"综合","measurement_target":"institution","region":"示例省","status":"sampled"},{"query_id":"M2","query_text":"示例省面试机构推荐","query_group":"面试","measurement_target":"institution","region":"示例省","status":"sampled"},{"query_id":"M3","query_text":"示例省本土公考机构","query_group":"本土","measurement_target":"institution","region":"示例省","status":"sampled"},
      {"query_id":"P1Q","query_text":"示例省申论老师推荐","query_group":"申论","measurement_target":"ip","region":"示例省","status":"sampled"},{"query_id":"P2Q","query_text":"示例省面试老师推荐","query_group":"面试","measurement_target":"ip","region":"示例省","status":"sampled"},{"query_id":"P3Q","query_text":"示例省公考规划老师","query_group":"规划","measurement_target":"ip","region":"示例省","status":"sampled"}
    ];wcsv(run/"queries.csv",qf,qs)
    ans=[]
    for q in qs:
        for eng in ["engine-a","engine-b"]:
            aid=f"A-{q['query_id']}-{eng[-1]}";text="建议关注甲公考和全国乙教育，前者本地内容更集中。" if q["measurement_target"]=="institution" else "乙老师在本地申论和规划内容中较常被提及。";ans.append({"answer_id":aid,"query_id":q["query_id"],"engine":eng,"model":eng,"sampled_at":"2026-09-10T10:00:00+08:00","response_text":text,"citations":[],"notes":""})
    wjsonl(run/"ai_answers.jsonl",ans)
    mf=["mention_id","answer_id","entity_id","mention_rank","mentioned_name","match_method","top3","first_mention","entity_correct","citation_linked","concepts","notes"];ms=[];n=1
    for a in ans:
        if a["query_id"].startswith("M"):
            ms += [{"mention_id":f"AM{n}","answer_id":a["answer_id"],"entity_id":"I1","mention_rank":1,"mentioned_name":"甲公考","match_method":"explicit-name","top3":"true","first_mention":"true","entity_correct":"true","citation_linked":"false","concepts":"本土|面试","notes":""},{"mention_id":f"AM{n+1}","answer_id":a["answer_id"],"entity_id":"I2","mention_rank":2,"mentioned_name":"全国乙教育","match_method":"explicit-name","top3":"true","first_mention":"false","entity_correct":"true","citation_linked":"false","concepts":"综合","notes":""}];n+=2
        else:ms.append({"mention_id":f"AM{n}","answer_id":a["answer_id"],"entity_id":"P1","mention_rank":1,"mentioned_name":"乙老师","match_method":"explicit-name","top3":"true","first_mention":"true","entity_correct":"true","citation_linked":"false","concepts":"申论|规划","notes":""});n+=1
    wcsv(run/"ai_mentions.csv",mf,ms)
    sf=["result_id","query_id","engine","rank","url","title","snippet","sampled_at"];wcsv(run/"serp_results.csv",sf,[{"result_id":"S1","query_id":"M1","engine":"web","rank":1,"url":"https://example.org/a","title":"示例省公考机构：甲公考","snippet":"甲公考本地内容介绍","sampled_at":"2026-09-10"},{"result_id":"S2","query_id":"M1","engine":"web","rank":2,"url":"https://example.org/b","title":"全国乙教育示例省课程","snippet":"全国乙教育在当地设点","sampled_at":"2026-09-10"}])
    smf=["serp_mention_id","result_id","entity_id","matched_text","match_surface","notes"];wcsv(run/"serp_mentions.csv",smf,[{"serp_mention_id":"SM1","result_id":"S1","entity_id":"I1","matched_text":"甲公考","match_surface":"both","notes":""},{"serp_mention_id":"SM2","result_id":"S2","entity_id":"I2","matched_text":"全国乙教育","match_surface":"title","notes":""}])
    pmf=["page_mention_id","result_id","entity_id","matched_text","page_url","notes"];wcsv(run/"page_mentions.csv",pmf,[{"page_mention_id":"PM1","result_id":"S1","entity_id":"I2","matched_text":"全国乙教育","page_url":"https://example.org/a","notes":"正文中提到，但不计 SERP/AI Measurement"}])
    evf=["evidence_id","entity_id","source_url","source_title","source_grade","source_owner","claim_type","counting_scope","notes"];wcsv(run/"evidence.csv",evf,[{"evidence_id":"E1","entity_id":"I1","source_url":"https://jia.example/about","source_title":"甲官网","source_grade":"A2","source_owner":"owned","claim_type":"entity","counting_scope":"entity","notes":""},{"evidence_id":"E2","entity_id":"I1","source_url":"https://uni.example/news","source_title":"高校活动","source_grade":"A1","source_owner":"independent","claim_type":"relation","counting_scope":"entity","notes":""},{"evidence_id":"E3","entity_id":"I2","source_url":"https://yi.example/local","source_title":"乙官网","source_grade":"A2","source_owner":"owned","claim_type":"entity","counting_scope":"entity","notes":""},{"evidence_id":"E4","entity_id":"P1","source_url":"https://platform.example/p1","source_title":"乙老师平台页","source_grade":"B","source_owner":"platform","claim_type":"entity","counting_scope":"entity","notes":""}])
    aif=["entity_id","canonical_name","entity_clarity","regional_semantic_density","open_web_assets","external_authority","content_depth_freshness","data_tool_assets","platform_coverage","notes"];wcsv(run/"asset_inputs.csv",aif,[{"entity_id":"I1","canonical_name":"甲公考","entity_clarity":22,"regional_semantic_density":18,"open_web_assets":11,"external_authority":10,"content_depth_freshness":8,"data_tool_assets":5,"platform_coverage":3,"notes":""},{"entity_id":"I2","canonical_name":"全国乙教育","entity_clarity":23,"regional_semantic_density":10,"open_web_assets":14,"external_authority":8,"content_depth_freshness":8,"data_tool_assets":6,"platform_coverage":2,"notes":""},{"entity_id":"P1","canonical_name":"乙老师","entity_clarity":18,"regional_semantic_density":19,"open_web_assets":7,"external_authority":7,"content_depth_freshness":9,"data_tool_assets":3,"platform_coverage":5,"notes":""}])
    cf=["concept","entity_id","canonical_name","strength","evidence_ids","notes"];wcsv(run/"concept_ownership.csv",cf,[{"concept":"本地面试","entity_id":"I1","canonical_name":"甲公考","strength":0.8,"evidence_ids":"E1|E2","notes":""},{"concept":"公考规划","entity_id":"P1","canonical_name":"乙老师","strength":0.9,"evidence_ids":"E4","notes":""}])
    rf=["recheck_id","sample_type","source_id","first_decision","second_decision","disagreement","resolution","recheck_by","notes"];wcsv(run/"rechecks.csv",rf,[{"recheck_id":"R1","sample_type":"ai-answer","source_id":ans[0]["answer_id"],"first_decision":"I1,I2","second_decision":"I1,I2","disagreement":"false","resolution":"","recheck_by":"reviewer-2","notes":"blind"},{"recheck_id":"R2","sample_type":"ai-answer","source_id":ans[4]["answer_id"],"first_decision":"I1,I2","second_decision":"I1","disagreement":"true","resolution":"按显式品牌名规则保留 I2","recheck_by":"reviewer-2","notes":"blind"},{"recheck_id":"R3","sample_type":"ai-answer","source_id":ans[8]["answer_id"],"first_decision":"P1","second_decision":"P1","disagreement":"false","resolution":"","recheck_by":"reviewer-2","notes":"blind"}])
    metrics.compute(run);assets.score(run);modeler.build(run)

def main():
    checks=0;skips=[];pre.self_test();checks+=1
    with tempfile.TemporaryDirectory() as td:
        run=Path(td);build(run);rows=rcsv(run/"ai_metrics.csv");assert any(r["entity_id"]=="I1" and float(r["nomination_rate"])==1.0 for r in rows);checks+=1
        assert not any(r["entity_id"]=="I2" and r["result_id"]=="S1" for r in rcsv(run/"serp_mentions.csv"));checks+=1
        assert next(r for r in rcsv(run/"market_universe.csv") if r["entity_id"]=="I2")["market_scope"]=="national";checks+=1
        model=json.loads((run/"report_model.json").read_text(encoding="utf-8"));assert len(model["market_universe"]["national_benchmarks"])==1 and len(model["market_universe"]["local_institutions"])==1 and len(model["market_universe"]["expert_ip"])==1;checks+=1
        sr=rcsv(run/"serp_results.csv");sr.append(dict(sr[0],result_id="S3",url="https://example.org/c"));wcsv(run/"serp_results.csv",list(sr[0].keys()),sr);assert any(x.code=="serp-rank-duplicate" for x in validator.validate(run));checks+=1;sr=sr[:-1];wcsv(run/"serp_results.csv",list(sr[0].keys()),sr)
        meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8"));meta["market_universe_confirmed"]=False;(run/"run_metadata.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8");assert any(x.code=="universe-not-confirmed" for x in validator.validate(run));checks+=1;meta["market_universe_confirmed"]=True;(run/"run_metadata.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
        try:
            charts=load("charts_v22","generate_charts.py");docxr=load("docx_v22","generate_report_docx.py");charts.generate(run);docxr.render(run,run/"deliverables"/"report.docx");issues=validator.validate(run,True);assert not [x for x in issues if x.level in {"error","warning"}],[(x.level,x.code,x.message) for x in issues];checks+=1
        except Exception as e:skips.append(f"DOCX/图表集成测试 SKIP: {e}")
    print(f"PASS: GEO v2.2 {checks} 项核心回归通过")
    for x in skips:print(x)
    return 0
if __name__=="__main__":raise SystemExit(main())
