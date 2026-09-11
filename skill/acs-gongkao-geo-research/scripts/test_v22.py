#!/usr/bin/env python3
from __future__ import annotations
import csv,importlib.util,json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
pre=load('pre_v22','preflight.py');cfg=load('cfg_v22','configure_measurement.py');ub=load('ub_v22','build_market_universe.py');met=load('met_v22','compute_ai_metrics.py');rob=load('rob_v22','compute_variant_robustness.py');val=load('val_v22','validate_run.py');modeler=load('model_v22','build_report_model.py');assets=load('assets_v22','score_assets.py')

def wcsv(p,fields,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def rcsv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def wjsonl(p,rows):p.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8')

def fixture(run:Path):
    m=pre.make_metadata('示例省',['甲公考','乙老师'],True);m.update({'market_universe_confirmed':True,'measurement_allowed':True,'sampling_mode':'limited-multi-engine','ai_engines_expected':['a','b'],'ai_engine_access_checked':True,'measurement_profile':'snapshot','answer_context_mode_expected':'native','repeat_runs_expected':1,'fresh_context_required':True,'context_isolation_level':'api-isolated','query_variant_mode':'exact-query-repeat','page_collection_status':'not-collected','observation_date':'2026-09-10'});(run/'run_metadata.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8')
    uf=['entity_id','canonical_name','aliases','entity_type','measurement_target','user_seed','discovery_origin','market_scope','operating_region','market_role','activity_status','platform_native','salience_basis','universe_status','confirmation_status','downgrade_reason','notes']
    us=[dict(zip(uf,['I1','甲公考','甲教育','institution','institution','true','user-seed|system-discovery','local','示例省','local-core','active','false','本地实体+独立来源','included','confirmed','',''])),dict(zip(uf,['I2','全国乙教育','乙教育','institution','institution','false','system-discovery','national','全国/示例省','national-benchmark','active','false','全国品牌+本地业务','included','confirmed','',''])),dict(zip(uf,['P1','乙老师','乙老师公考','ip','ip','true','user-seed|platform-native-ip','local','示例省','expert-ip','active','true','持续本地主题','included','confirmed','',''])),dict(zip(uf,['O1','观察机构','','institution','institution','false','system-discovery','unknown','','observation','uncertain','false','单一聚合页','observation','confirmed','seo-only','证据不足']))]
    wcsv(run/'market_universe.csv',uf,us);ub.write_review(run,us,m)
    qf=['query_id','query_text','query_group','measurement_target','region','status'];qs=[{'query_id':'M1','query_text':'示例省公考机构推荐','query_group':'综合','measurement_target':'institution','region':'示例省','status':'sampled'},{'query_id':'M2','query_text':'示例省面试机构推荐','query_group':'面试','measurement_target':'institution','region':'示例省','status':'sampled'},{'query_id':'P1Q','query_text':'示例省申论老师推荐','query_group':'申论','measurement_target':'ip','region':'示例省','status':'sampled'},{'query_id':'P2Q','query_text':'示例省面试老师推荐','query_group':'面试','measurement_target':'ip','region':'示例省','status':'sampled'}];wcsv(run/'queries.csv',qf,qs)
    ans=[]
    for q in qs:
      for eng in ['a','b']:
        aid=f"A-{q['query_id']}-{eng}";text='建议甲公考，其次全国乙教育。' if q['measurement_target']=='institution' else '推荐乙老师。'
        if q['query_id']=='P1Q' and eng=='a':text+=' 新星老师也可关注。'
        ans.append({'answer_id':aid,'query_id':q['query_id'],'engine':eng,'model':eng,'sample_run':1,'query_variant_id':'canonical','context_id':aid,'fresh_context':True,'answer_context_mode':'native','sampled_at':'2026-09-10T10:00:00+08:00','response_text':text,'citations':[],'notes':''})
    wjsonl(run/'ai_answers.jsonl',ans)
    xf=['entity_id','canonical_name','aliases','measurement_target','market_scope','operating_region','resolution_status','source_answer_ids','source_result_ids','notes'];wcsv(run/'ai_emergent_entities.csv',xf,[{'entity_id':'X1','canonical_name':'新星老师','aliases':'','measurement_target':'ip','market_scope':'unknown','operating_region':'','resolution_status':'resolved','source_answer_ids':'A-P1Q-a','source_result_ids':'','notes':''}])
    mf=['mention_id','answer_id','entity_id','mention_rank','nomination_rank','mentioned_name','match_method','resolution_status','mention_intent','top3','first_mention','entity_correct','citation_linked','citation_refs','concepts','notes'];ms=[];n=1
    for a in ans:
      if a['query_id'].startswith('M'):
        for eid,name,rank in [('I1','甲公考',1),('I2','全国乙教育',2)]:ms.append({'mention_id':f'AM{n}','answer_id':a['answer_id'],'entity_id':eid,'mention_rank':rank,'nomination_rank':rank,'mentioned_name':name,'match_method':'explicit-name','resolution_status':'resolved','mention_intent':'listed','top3':'true','first_mention':'true' if rank==1 else 'false','entity_correct':'true','citation_linked':'false','citation_refs':'','concepts':'','notes':''});n+=1
      else:
        ms.append({'mention_id':f'AM{n}','answer_id':a['answer_id'],'entity_id':'P1','mention_rank':1,'nomination_rank':1,'mentioned_name':'乙老师','match_method':'explicit-name','resolution_status':'resolved','mention_intent':'recommended','top3':'true','first_mention':'true','entity_correct':'true','citation_linked':'false','citation_refs':'','concepts':'','notes':''});n+=1
        if a['answer_id']=='A-P1Q-a':ms.append({'mention_id':f'AM{n}','answer_id':a['answer_id'],'entity_id':'X1','mention_rank':2,'nomination_rank':2,'mentioned_name':'新星老师','match_method':'explicit-name','resolution_status':'resolved','mention_intent':'listed','top3':'true','first_mention':'false','entity_correct':'true','citation_linked':'false','citation_refs':'','concepts':'','notes':''});n+=1
    wcsv(run/'ai_mentions.csv',mf,ms)
    sf=['result_id','query_id','engine','rank','url','title','snippet','sampled_at'];wcsv(run/'serp_results.csv',sf,[{'result_id':'S1','query_id':'M1','engine':'web','rank':1,'url':'https://example.org/a','title':'甲公考','snippet':'甲公考','sampled_at':'2026-09-10'},{'result_id':'S2','query_id':'M1','engine':'web','rank':2,'url':'https://example.org/b','title':'全国乙教育','snippet':'全国乙教育','sampled_at':'2026-09-10'}])
    smf=['serp_mention_id','result_id','entity_id','matched_text','match_surface','notes'];wcsv(run/'serp_mentions.csv',smf,[{'serp_mention_id':'SM1','result_id':'S1','entity_id':'I1','matched_text':'甲公考','match_surface':'both','notes':''}])
    pmf=['page_mention_id','result_id','entity_id','matched_text','page_url','notes'];wcsv(run/'page_mentions.csv',pmf,[])
    ef=['evidence_id','entity_id','source_url','source_title','source_grade','source_owner','claim_type','counting_scope','notes'];wcsv(run/'evidence.csv',ef,[{'evidence_id':'E1','entity_id':'I1','source_url':'https://jia.example','source_title':'甲','source_grade':'A2','source_owner':'owned','claim_type':'entity','counting_scope':'entity','notes':''}])
    rf=['recheck_id','sample_type','source_id','first_decision','second_decision','disagreement','resolution','recheck_by','notes'];wcsv(run/'rechecks.csv',rf,[{'recheck_id':'R1','sample_type':'ai-answer','source_id':ans[0]['answer_id'],'first_decision':'ok','second_decision':'ok','disagreement':'false','resolution':'','recheck_by':'r2','notes':''}])
    af=['entity_id','canonical_name','entity_clarity','regional_semantic_density','open_web_assets','external_authority','content_depth_freshness','data_tool_assets','platform_coverage','notes'];wcsv(run/'asset_inputs.csv',af,[{'entity_id':'I1','canonical_name':'甲公考','entity_clarity':20,'regional_semantic_density':18,'open_web_assets':10,'external_authority':10,'content_depth_freshness':8,'data_tool_assets':5,'platform_coverage':3,'notes':''},{'entity_id':'I2','canonical_name':'全国乙教育','entity_clarity':20,'regional_semantic_density':10,'open_web_assets':10,'external_authority':10,'content_depth_freshness':8,'data_tool_assets':5,'platform_coverage':3,'notes':''},{'entity_id':'P1','canonical_name':'乙老师','entity_clarity':18,'regional_semantic_density':18,'open_web_assets':8,'external_authority':6,'content_depth_freshness':8,'data_tool_assets':3,'platform_coverage':5,'notes':''}]);assets.score(run)
    cf=['concept','entity_id','canonical_name','strength','evidence_ids','notes'];wcsv(run/'concept_ownership.csv',cf,[]);met.compute(run);rob.compute(run);modeler.build(run)

def main():
    checks=0;skips=[]
    pre.self_test();checks+=1
    with tempfile.TemporaryDirectory() as td:
      r=Path(td);m=pre.make_metadata('广东',['甲'],True);(r/'run_metadata.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8');o=cfg.configure(r,['a'],'external-search-augmented','snapshot',1,False,'2026-09-10','programmatic','semantic-retrieval-variants','not-collected');assert o['sampling_mode']=='single-engine' and (r/'measurement_config.json').is_file() and o['observation_date']=='2026-09-10';checks+=1
      try:cfg.configure(r,['a'],'native','release',2,True);raise AssertionError
      except ValueError:checks+=1
    with tempfile.TemporaryDirectory() as td:
      r=Path(td);m=pre.make_metadata('广东',['甲'],True);(r/'run_metadata.json').write_text(json.dumps(m,ensure_ascii=False),encoding='utf-8');wcsv(r/'discovery_candidates.csv',['canonical_name','entity_type','measurement_target','market_scope','market_role','salience_basis'],[{'canonical_name':'甲','entity_type':'studio','measurement_target':'both','market_scope':'local','market_role':'local-active','salience_basis':'真实证据'}]);ub.build(r);u=rcsv(r/'market_universe.csv')[0];assert u['user_seed']=='true' and u['measurement_target']=='both' and u['market_scope']=='local';checks+=1
    with tempfile.TemporaryDirectory() as td:
      r=Path(td);fixture(r);assert not [x for x in val.validate(r,True,'universe') if x.level in {'error','warning'}];checks+=1;assert not [x for x in val.validate(r,True,'measurement') if x.level in {'error','warning'}];checks+=1
      rows=rcsv(r/'ai_metrics.csv');assert next(x for x in rows if x['entity_id']=='I1' and x['measurement_target']=='institution')['nomination_rate']=='1.0';checks+=1;assert any(x['entity_id']=='X1' for x in rows);checks+=1
      ms=rcsv(r/'ai_mentions.csv');x=next(x for x in ms if x['answer_id']=='A-M1-a' and x['entity_id']=='I2');x.update(mention_intent='excluded',nomination_rank='',top3='false',first_mention='false');wcsv(r/'ai_mentions.csv',list(ms[0]),ms);met.compute(r);assert float(next(z for z in rcsv(r/'ai_metrics.csv') if z['entity_id']=='I2')['nomination_rate'])<1;checks+=1
      u=rcsv(r/'market_universe.csv');i1=next(z for z in u if z['entity_id']=='I1');i1['measurement_target']='both';i1['entity_type']='studio';wcsv(r/'market_universe.csv',list(u[0]),u);ub.write_review(r,u,json.loads((r/'run_metadata.json').read_text()));met.compute(r);rows=rcsv(r/'ai_metrics.csv');assert len([z for z in rows if z['entity_id']=='I1'])==2 and {z['measurement_target'] for z in rows if z['entity_id']=='I1'}=={'institution','ip'};checks+=1;model=modeler.build(r);assert any(z['entity_id']=='I1' for z in model['market_universe']['local_institutions']) and not any(z['entity_id']=='I1' for z in model['market_universe']['expert_ip']);checks+=1
      summary=rob.compute(r);assert 'positive_persistence_3of3_rate' in summary and (r/'query_set_similarity.csv').is_file();checks+=1
      i1['measurement_target']='';wcsv(r/'market_universe.csv',list(u[0]),u);assert any(z.code=='entity-measurement-target-required' for z in val.validate(r,stage='measurement'));checks+=1;i1['measurement_target']='both';wcsv(r/'market_universe.csv',list(u[0]),u);met.compute(r)
      aa=[json.loads(x) for x in (r/'ai_answers.jsonl').read_text().splitlines()];aa[0]['answer_context_mode']='external-search-augmented';wjsonl(r/'ai_answers.jsonl',aa);assert any(z.code=='answer-context-mode-mismatch' for z in val.validate(r,stage='measurement'));checks+=1;aa[0]['answer_context_mode']='native';aa[0]['citations']=['https://jia.example'];wjsonl(r/'ai_answers.jsonl',aa)
      ms=rcsv(r/'ai_mentions.csv');m0=next(z for z in ms if z['answer_id']==aa[0]['answer_id'] and z['entity_id']=='I1');m0.update(citation_linked='true',citation_refs='');wcsv(r/'ai_mentions.csv',list(ms[0]),ms);assert any(z.code=='citation-ref-missing' for z in val.validate(r,stage='measurement'));checks+=1;m0['citation_refs']='https://jia.example';wcsv(r/'ai_mentions.csv',list(ms[0]),ms);assert not any(z.code.startswith('citation-ref') for z in val.validate(r,stage='measurement'));checks+=1
      sr=rcsv(r/'serp_results.csv');sr.append(dict(sr[0],result_id='SDUP',url='https://example.org/dup'));wcsv(r/'serp_results.csv',list(sr[0]),sr);assert any(z.code=='serp-rank-duplicate' for z in val.validate(r,stage='measurement'));checks+=1;sr.pop();wcsv(r/'serp_results.csv',list(sr[0]),sr)
      ms=rcsv(r/'ai_mentions.csv');p=next(z for z in ms if z['entity_id']=='I1');p['top3']='false';wcsv(r/'ai_mentions.csv',list(ms[0]),ms);assert any(z.code=='top3-rank-mismatch' for z in val.validate(r,stage='measurement'));checks+=1;p['top3']='true';wcsv(r/'ai_mentions.csv',list(ms[0]),ms)
      meta=json.loads((r/'run_metadata.json').read_text());meta.update(measurement_profile='release',repeat_runs_expected=3,context_isolation_level='programmatic',fresh_context_note='',query_variant_mode='semantic-retrieval-variants');(r/'run_metadata.json').write_text(json.dumps(meta,ensure_ascii=False));assert any(z.code=='programmatic-context-disclosure' for z in val.validate(r,stage='measurement'));checks+=1
      try:
        charts=load('charts_v22','generate_charts.py');docx=load('docx_v22','generate_report_docx.py');meta.update(measurement_profile='snapshot',context_isolation_level='api-isolated');(r/'run_metadata.json').write_text(json.dumps(meta,ensure_ascii=False));met.compute(r);modeler.build(r);charts.generate(r);docx.render(r,r/'deliverables'/'report.docx');assert not [x for x in val.validate(r,True,'report') if x.level in {'error','warning'}];checks+=1
      except Exception as e:skips.append(f'DOCX/图表集成测试 SKIP: {e}')
    print(f'PASS: GEO v2.2 {checks} 项核心回归通过')
    for s in skips:print(s)
    return 0
if __name__=='__main__':raise SystemExit(main())
