#!/usr/bin/env python3
"""v2.2.1 first-run regression for Fresh Run defects D1/D2/D3/D4."""
from __future__ import annotations
import csv,importlib.util,json,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def wcsv(path,fields,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def base_meta():
    return {"schema_version":"2.2","skill_version":"2.2","official_output_format":"docx","requested_region":"示例省","normalized_region":"示例省","research_mode":"scoped-geo-landscape","seed_entities":["甲公考"],"market_universe_confirmed":False,"measurement_allowed":False}


def main():
    apply_mod=load('apply_target_v221','apply_measurement_target_audit.py');confirm_mod=load('confirm_universe_v221','confirm_market_universe.py');checks=0
    fields=["entity_id","canonical_name","aliases","entity_type","measurement_target","user_seed","discovery_origin","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","discovery_evidence_urls","universe_status","confirmation_status","downgrade_reason","notes"]
    audit_fields=["entity_id","canonical_name","entity_source","resolution_status","stage1_market_role","market_bucket","entity_type","current_explicit_target","candidate_target","institution_evidence","ip_evidence","hybrid_signal","hybrid_signal_basis","cross_target_ai_signal","new_explicit_target","evidence_basis","reviewer_reason","changed","review_status","notes"]

    # D1/D2/D3: Stage 1 has no ai_emergent_entities.csv yet; apply must still succeed.
    with tempfile.TemporaryDirectory() as td:
        r=Path(td);(r/'run_metadata.json').write_text(json.dumps(base_meta(),ensure_ascii=False),encoding='utf-8')
        row=dict(zip(fields,['U001','甲公考','','institution','institution','true','user-seed','local','示例省','local-core','active','false','本地主体','https://example.org/jia','included','needs-review','','']))
        wcsv(r/'market_universe.csv',fields,[row])
        a={k:'' for k in audit_fields};a.update({'entity_id':'U001','canonical_name':'甲公考','entity_source':'universe','resolution_status':'resolved','stage1_market_role':'local-core','entity_type':'institution','current_explicit_target':'institution','candidate_target':'institution','institution_evidence':'品牌机构入口明确','new_explicit_target':'institution','evidence_basis':'官网机构页','review_status':'confirmed'})
        wcsv(r/'measurement_target_audit.csv',audit_fields,[a])
        result=apply_mod.apply(r)
        assert result['resolved_emergent_rows']==0,result
        assert not (r/'ai_emergent_entities.csv').exists(),'Stage 1 apply 不应为了过门禁伪造 emergent 空表'
        checks+=1

    # D4: a newly built universe with the evidence column may not confirm a main subject without URL.
    with tempfile.TemporaryDirectory() as td:
        r=Path(td);(r/'run_metadata.json').write_text(json.dumps(base_meta(),ensure_ascii=False),encoding='utf-8')
        row=dict(zip(fields,['U001','甲公考','','institution','institution','true','user-seed','local','示例省','local-core','active','false','本地主体','','included','needs-review','','']))
        wcsv(r/'market_universe.csv',fields,[row])
        failed=False
        try:confirm_mod.confirm(r)
        except SystemExit as e:
            failed=True;assert 'discovery_evidence_urls' in str(e),str(e)
        assert failed,'缺可核验来源链接的正式主体不应通过确认'
        row['discovery_evidence_urls']='https://example.org/jia';wcsv(r/'market_universe.csv',fields,[row])
        result=confirm_mod.confirm(r);assert result['market_universe_confirmed'] is True,result
        checks+=1

    print(f'PASS: v2.2.1 Fresh Run 修复回归 {checks} 项通过')
    return 0

if __name__=='__main__':raise SystemExit(main())
