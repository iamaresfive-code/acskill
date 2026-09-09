#!/usr/bin/env python3
"""v2.1 strict validator：Preflight、Semantic Coverage、Freeze、数据一致性、图表与唯一 Renderer 门禁。"""
from __future__ import annotations
import argparse,csv,json,re
from collections import Counter,defaultdict
from dataclasses import dataclass,asdict
from pathlib import Path
WEIGHTS={"query_coverage":30.0,"entity_clarity":25.0,"external_diversity":20.0,"concept_ownership":15.0,"freshness":10.0}
TRUE={"1","true","yes","y","是"};PURPOSES={"discovery","measurement","verification"};TARGETS={"institution","ip"};DISCOVERY_CHANNELS={"user-query","exam-vertical","institutional","platform","expert-ip","entity-alias"};FINAL_STATUSES={"scored","evidence-insufficient","merged","excluded","unresolved"};FORMATS={"docx","pdf","html"}
@dataclass
class Issue:level:str;code:str;message:str;key:str=""
def _csv(path:Path,issues,label,required:set[str]):
    if not path.is_file():issues.append(Issue('error','missing-'+label,f'缺少 {path.name}'));return [],set()
    try:
        with path.open('r',encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);rows=list(r);fields=set(r.fieldnames or [])
    except Exception as e:issues.append(Issue('error','read-'+label,f'{path.name} 读取失败：{e}'));return [],set()
    miss=required-fields
    if miss:issues.append(Issue('error',label+'-schema',f'{path.name} 缺少字段：{", ".join(sorted(miss))}'))
    return rows,fields
def _json(path:Path,issues,label):
    if not path.is_file():issues.append(Issue('error','missing-'+label,f'缺少 {path.name}'));return {}
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:issues.append(Issue('error','invalid-'+label,f'{path.name} JSON 无效：{e}'));return {}
def _num(v):
    try:return float(v)
    except:return None
def _tier(t):
    if t>=85:return'S'
    if t>=80:return'A+'
    if t>=70:return'A'
    if t>=65:return'A-'
    if t>=60:return'B+'
    if t>=50:return'B'
    if t>=45:return'B-'
    return'C'
def validate(run:Path,strict=False):
    issues=[]
    if not run.is_dir():return [Issue('error','missing-run-dir',f'不是目录：{run}')]
    meta=_json(run/'run_metadata.json',issues,'run-metadata');model=_json(run/'report_model.json',issues,'report-model')
    if str(meta.get('schema_version'))!='2.1':issues.append(Issue('error','schema-version','run_metadata.schema_version 必须为 2.1'))
    for k in ('region_confirmed','specified_entities_confirmed','output_format_confirmed'):
        if meta.get(k) is not True:issues.append(Issue('error','preflight-incomplete',f'Preflight 未确认：{k}',k))
    formats=meta.get('requested_output_format') or []
    if isinstance(formats,str):formats=[formats]
    if not formats or any(x not in FORMATS for x in formats):issues.append(Issue('error','invalid-output-format','requested_output_format 必须是 docx/pdf/html 数组'))
    if meta.get('run_status')=='preflight-incomplete':issues.append(Issue('error','preflight-status','run_status 仍为 preflight-incomplete'))
    qreq={'query_id','query_text','query_type','query_purpose','measurement_target','discovery_channel','discovery_round','semantic_theme','region','status'};rreq={'result_id','query_id','entity_id','matched','counts_as_measurement_hit'};creq={'candidate_id','entity_id','display_name','candidate_type','discovery_round','discovery_channel','user_specified','status','merged_into_entity_id','exclusion_reason'};ereq={'entity_id','canonical_name','entity_type','aliases','legal_name','former_names','brand_name','official_domain','official_account','disambiguation_notes'};evreq={'evidence_id','entity_id','institution','query_id','source_url','source_grade','independent','claim_type','counting_scope'};sreq={'institution','entity_id','inclusion_basis',*WEIGHTS.keys(),'total','tier','generic_hits','generic_queries','brand_hits','evidence_count','independent_domains','authority_index','competition_route'};covreq={'region','discovery_channel','semantic_theme','required','query_count','result_count','eligible_candidates_found','status'};ipreq={'teacher_name','entity_id','institution','ip_hits','ip_queries','ip_recall','source_ids'}
    queries,_=_csv(run/'queries.csv',issues,'queries',qreq);results,_=_csv(run/'query_results.csv',issues,'query-results',rreq);coverage,_=_csv(run/'discovery_coverage.csv',issues,'discovery-coverage',covreq);cands,_=_csv(run/'candidate_pool.csv',issues,'candidate-pool',creq);entities,_=_csv(run/'entities.csv',issues,'entities',ereq);evidence,_=_csv(run/'evidence.csv',issues,'evidence',evreq);scores,_=_csv(run/'scores.csv',issues,'scores',sreq);ips,_=_csv(run/'ip_entities.csv',issues,'ip-entities',ipreq);_csv(run/'entity_relations.csv',issues,'entity-relations',{'relation_id','source_entity_id','relation_type','target_entity_id','evidence_ids','confidence'});details=_json(run/'score_details.json',issues,'score-details')
    qmap={};inst_m=set();ip_m=set();discovery_channels=set();rounds=set()
    for i,q in enumerate(queries,2):
        qid=q.get('query_id','').strip()
        if not qid or qid in qmap:issues.append(Issue('error','duplicate-query-id',f'queries.csv 第{i}行 query_id 重复/为空'))
        qmap[qid]=q;qt=q.get('query_type','').lower();qp=q.get('query_purpose','').lower();status=q.get('status','').lower();target=q.get('measurement_target','').lower()
        if qp not in PURPOSES:issues.append(Issue('error','invalid-query-purpose',f'{qid} query_purpose 无效'))
        if qp=='measurement':
            if qt!='generic':issues.append(Issue('error','measurement-not-generic',f'{qid} measurement 必须 generic'))
            if target not in TARGETS:issues.append(Issue('error','measurement-target',f'{qid} measurement_target 必须 institution/ip'))
            if status=='sampled':(inst_m if target=='institution' else ip_m).add(qid)
        elif target:issues.append(Issue('error','unexpected-measurement-target',f'{qid} 非 measurement 不应设置 measurement_target'))
        if qp=='discovery' and status=='sampled':
            ch=q.get('discovery_channel','').lower();discovery_channels.add(ch)
            if ch not in DISCOVERY_CHANNELS:issues.append(Issue('error','invalid-discovery-channel',f'{qid} discovery_channel 无效'))
            try:rounds.add(int(q.get('discovery_round') or 0))
            except:issues.append(Issue('error','invalid-discovery-round',f'{qid} discovery_round 无效'))
            if not q.get('semantic_theme','').strip():issues.append(Issue('error','missing-semantic-theme',f'{qid} 缺少 semantic_theme'))
    if meta.get('research_mode','regional-landscape')=='regional-landscape' and not DISCOVERY_CHANNELS<=discovery_channels:issues.append(Issue('error','discovery-channel-coverage','地区全景必须覆盖六路 Discovery'))
    if not inst_m:issues.append(Issue('error','no-institution-measurement','没有机构 Measurement'))
    hit=defaultdict(set);brand=defaultdict(set);ip_hit=defaultdict(set)
    for r in results:
        qid=r.get('query_id','');eid=r.get('entity_id','');matched=r.get('matched','').lower() in TRUE;counted=r.get('counts_as_measurement_hit','').lower() in TRUE
        if qid not in qmap:issues.append(Issue('error','result-query-missing',f'{r.get("result_id")} 引用不存在 Query'));continue
        if counted and not matched:issues.append(Issue('error','measurement-isolation',f'{r.get("result_id")} 未命中却计入 Measurement'))
        if counted and qid not in inst_m|ip_m:issues.append(Issue('error','measurement-isolation',f'{r.get("result_id")} Discovery/Verification 不得计入 Recall'))
        if matched and counted and qid in inst_m:hit[eid].add(qid)
        if matched and counted and qid in ip_m:ip_hit[eid].add(qid)
        q=qmap[qid]
        if matched and q.get('query_type','').lower()=='brand' and q.get('query_purpose','').lower()=='verification':brand[eid].add(qid)
    required=[r for r in coverage if r.get('required','').lower() in TRUE];bad=[r for r in required if r.get('status','') not in {'covered','no-result-reviewed'} or (_num(r.get('query_count')) or 0)<=0]
    if bad:issues.append(Issue('error','semantic-coverage-gate',f'{len(bad)} 个 required Semantic Theme 未完成'))
    if meta.get('semantic_coverage_gate') is not True:issues.append(Issue('error','semantic-coverage-metadata','run_metadata 未标记 semantic_coverage_gate=true'))
    entity_ids={e.get('entity_id') for e in entities};scored=set();user_spec=set();round_entities=defaultdict(set)
    for c in cands:
        eid=c.get('entity_id','');st=c.get('status','')
        if st not in FINAL_STATUSES:issues.append(Issue('error','unfinished-candidate-status',f'{c.get("candidate_id")} status 无效'))
        if eid and eid not in entity_ids:issues.append(Issue('error','candidate-entity-missing',f'{c.get("candidate_id")} entity_id 不存在'))
        if st=='scored':scored.add(eid)
        if c.get('user_specified','').lower() in TRUE:
            user_spec.add(eid)
            if st=='excluded':issues.append(Issue('error','user-specified-disappeared',f'用户指定主体 {c.get("display_name")} 不得 excluded 后静默消失'))
        try:round_entities[int(c.get('discovery_round') or 0)].add(eid)
        except:pass
    if (meta.get('requested_entities') or []) and not user_spec:issues.append(Issue('error','specified-entities-untracked','run_metadata 有指定主体，但 candidate_pool 无 user_specified=true'))
    last=max(rounds or round_entities.keys() or {0});prev=set().union(*(round_entities[r] for r in round_entities if r<last));eligible={c.get('entity_id') for c in cands if c.get('status') in {'scored','evidence-insufficient'} and c.get('entity_id')};neweligible={c.get('entity_id') for c in cands if c.get('discovery_round')==str(last) and c.get('status') in {'scored','evidence-insufficient'} and c.get('entity_id') not in prev};ratio=len(neweligible)/max(1,len(eligible));saturation_ok=(ratio<0.10 or len(neweligible)<=1 or meta.get('consecutive_no_important_new_rounds',0)>=2)
    if not saturation_ok:issues.append(Issue('error','saturation-gate',f'候选未收敛：末轮新增可评估 {len(neweligible)}，占 {ratio:.0%}'))
    if meta.get('saturation_gate') is not True:issues.append(Issue('error','saturation-metadata','run_metadata 未标记 saturation_gate=true'))
    if meta.get('candidate_pool_frozen') is not True:issues.append(Issue('error','candidate-not-frozen','candidate_pool_frozen 必须 true'))
    score_ids=set();ev_by=defaultdict(list)
    for e in evidence:ev_by[e.get('entity_id')].append(e)
    for s in scores:
        eid=s.get('entity_id','');score_ids.add(eid)
        if eid not in entity_ids:issues.append(Issue('error','score-entity-missing',f'{s.get("institution")} entity_id 不存在'))
        if eid not in scored:issues.append(Issue('error','score-candidate-status',f'{s.get("institution")} candidate 未标 scored'))
        vals=[]
        for f,mx in WEIGHTS.items():
            v=_num(s.get(f))
            if v is None or not 0<=v<=mx:issues.append(Issue('error','score-out-of-range',f'{s.get("institution")} {f} 无效'))
            else:vals.append(v)
        total=_num(s.get('total'))
        if total is None or abs(total-sum(vals))>1e-6:issues.append(Issue('error','score-sum',f'{s.get("institution")} total 与五维不一致'))
        elif s.get('tier')!=_tier(total):issues.append(Issue('error','score-tier',f'{s.get("institution")} tier 不一致'))
        if _num(s.get('generic_hits'))!=len(hit[eid]) or _num(s.get('generic_queries'))!=len(inst_m):issues.append(Issue('error','institution-recall-mismatch',f'{s.get("institution")} 机构 Recall 与 Query Log 不一致'))
        if _num(s.get('brand_hits'))!=len(brand[eid]):issues.append(Issue('error','brand-hit-mismatch',f'{s.get("institution")} brand_hits 不一致'))
        if _num(s.get('evidence_count'))!=len(ev_by[eid]):issues.append(Issue('error','evidence-count-mismatch',f'{s.get("institution")} evidence_count 不一致'))
    if scored!=score_ids:issues.append(Issue('error','candidate-score-set-mismatch','candidate_pool scored 集合与 scores.csv 不一致'))
    dmap={x.get('entity_id'):x for x in details if isinstance(x,dict)} if isinstance(details,list) else {}
    for s in scores:
        dims=(dmap.get(s.get('entity_id')) or {}).get('dimensions',{})
        for f in WEIGHTS:
            d=dims.get(f,{}) if isinstance(dims,dict) else {}
            if not d.get('reason'):issues.append(Issue('error','missing-dimension-reason',f'{s.get("institution")} {f} 缺理由'))
            if not (d.get('query_ids') or d.get('evidence_ids')):issues.append(Issue('error','missing-dimension-sources',f'{s.get("institution")} {f} 缺来源'))
    for ip in ips:
        eid=ip.get('entity_id','');queries_n=_num(ip.get('ip_queries')) or 0;hits_n=_num(ip.get('ip_hits')) or 0
        if queries_n!=len(ip_m):issues.append(Issue('error','ip-query-denominator-mismatch',f'{ip.get("teacher_name")} ip_queries 不一致'))
        if hits_n!=len(ip_hit[eid]):issues.append(Issue('error','ip-hit-mismatch',f'{ip.get("teacher_name")} ip_hits 不一致'))
    k=(model or {}).get('kpis',{});inst_ids={e.get('entity_id') for e in entities if e.get('entity_type') in {'institution','brand'}};unique_inst={c.get('entity_id') for c in cands if c.get('entity_id') in inst_ids};evaluable={c.get('entity_id') for c in cands if c.get('entity_id') in inst_ids and c.get('status') in {'scored','evidence-insufficient'}};expected={'independent_institutions':len(unique_inst),'evaluable_institutions':len(evaluable),'scored_institutions':len(scores),'institution_measurement_queries':len(inst_m),'ip_measurement_queries':len(ip_m),'evidence_count':len(evidence),'entity_nodes':len(entities),'ip_entities':len(ips)}
    for key,val in expected.items():
        if k.get(key)!=val:issues.append(Issue('error','report-data-mismatch',f'report_model.kpis.{key}={k.get(key)!r}，实际 {val}',key))
    if 'appendix' not in model:issues.append(Issue('error','missing-appendix','Report Model 必须有 Appendix'))
    chart_data=_json(run/'charts'/'chart_data.json',issues,'chart-data')
    for name in ('geo-score-ranking.svg','authority-recall-matrix.svg'):
        if not (run/'charts'/name).is_file():issues.append(Issue('error','missing-required-chart',f'缺少 {name}',name))
    ranking=chart_data.get('ranking',[]) if isinstance(chart_data,dict) else [];expected_rank=[(s.get('entity_id'),_num(s.get('total'))) for s in sorted(scores,key=lambda x:_num(x.get('total')) or 0,reverse=True)];got_rank=[(x.get('entity_id'),_num(x.get('total'))) for x in ranking]
    if expected_rank!=got_rank:issues.append(Issue('error','chart-score-mismatch','Ranking Chart 数据与 scores.csv 不一致'))
    if chart_data.get('measurement_denominator')!=len(inst_m):issues.append(Issue('error','chart-recall-denominator-mismatch','Chart Measurement denominator 不一致'))
    delivered=run/'deliverables';found=[]
    if delivered.is_dir():
        for p in delivered.iterdir():
            if p.is_file() and p.suffix.lower().lstrip('.') in FORMATS:found.append(p.suffix.lower().lstrip('.'))
    missing=[f for f in formats if f not in found]
    if missing:issues.append(Issue('error','missing-selected-artifact','缺少用户选择的正式产出：'+','.join(missing)))
    extra=[f for f in found if f not in formats]
    if extra:issues.append(Issue('warning','unexpected-output-artifact','存在未请求的正式产出：'+','.join(extra),','.join(sorted(extra))))
    return issues

def main():
    p=argparse.ArgumentParser();p.add_argument('run_dir',nargs='?',type=Path);p.add_argument('--strict',action='store_true');p.add_argument('--json',action='store_true');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    if a.self_test:print('validate_run v2.1：请运行 scripts/test_v21.py 完整自测');return 0
    if not a.run_dir:p.error('必须提供 run_dir')
    issues=validate(a.run_dir,a.strict);errors=sum(x.level=='error' for x in issues);warnings=sum(x.level=='warning' for x in issues)
    if a.json:print(json.dumps({'errors':errors,'warnings':warnings,'issues':[asdict(x) for x in issues]},ensure_ascii=False,indent=2))
    else:
        for x in issues:print(f'{x.level.upper()} [{x.code}] {x.message}')
        print(f'校验摘要：{errors} 个错误，{warnings} 个警告')
    return 1 if errors or (a.strict and warnings) else 0
if __name__=='__main__':raise SystemExit(main())
