#!/usr/bin/env python3
"""Create/validate v2.1 GEO preflight metadata without starting research."""
from __future__ import annotations
import argparse, json
from pathlib import Path

FORMATS={"word":"docx","docx":"docx",".docx":"docx","pdf":"pdf",".pdf":"pdf","html":"html",".html":"html","网页":"html","word文档":"docx"}
MUNICIPALITIES={"北京":"北京市","北京市":"北京市","天津":"天津市","天津市":"天津市","上海":"上海市","上海市":"上海市","重庆":"重庆市","重庆市":"重庆市"}
PROVINCES={"广东":"广东省","广东省":"广东省","山东":"山东省","山东省":"山东省","浙江":"浙江省","浙江省":"浙江省","江苏":"江苏省","江苏省":"江苏省","河北":"河北省","河北省":"河北省","河南":"河南省","河南省":"河南省","四川":"四川省","四川省":"四川省","湖北":"湖北省","湖北省":"湖北省","湖南":"湖南省","湖南省":"湖南省","福建":"福建省","福建省":"福建省","辽宁":"辽宁省","辽宁省":"辽宁省","安徽":"安徽省","安徽省":"安徽省","江西":"江西省","江西省":"江西省","陕西":"陕西省","陕西省":"陕西省","山西":"山西省","山西省":"山西省"}
CITY_ALIASES={"广州":"广州市","广州市":"广州市","深圳":"深圳市","深圳市":"深圳市","成都":"成都市","成都市":"成都市","杭州":"杭州市","杭州市":"杭州市","南京":"南京市","南京市":"南京市","济南":"济南市","济南市":"济南市"}
CUSTOM={"珠三角":["广州市","深圳市","珠海市","佛山市","惠州市","东莞市","中山市","江门市","肇庆市"]}

def normalize_region(value:str)->dict[str,object]:
    raw=value.strip()
    if raw in MUNICIPALITIES: return {"requested_region":raw,"normalized_region":MUNICIPALITIES[raw],"region_type":"municipality","research_scope":[MUNICIPALITIES[raw]]}
    if raw in PROVINCES: return {"requested_region":raw,"normalized_region":PROVINCES[raw],"region_type":"province","research_scope":[PROVINCES[raw]]}
    if raw in CITY_ALIASES: return {"requested_region":raw,"normalized_region":CITY_ALIASES[raw],"region_type":"city","research_scope":[CITY_ALIASES[raw]]}
    if raw in CUSTOM: return {"requested_region":raw,"normalized_region":raw,"region_type":"custom-region","research_scope":CUSTOM[raw]}
    if raw.endswith("省"): return {"requested_region":raw,"normalized_region":raw,"region_type":"province","research_scope":[raw]}
    if raw.endswith("市"): return {"requested_region":raw,"normalized_region":raw,"region_type":"city","research_scope":[raw]}
    return {"requested_region":raw,"normalized_region":raw,"region_type":"custom-region","research_scope":[raw],"scope_requires_review":True}

def normalize_formats(values:list[str])->list[str]:
    out=[]
    for value in values:
        key=value.strip().lower();fmt=FORMATS.get(key)
        if not fmt: raise ValueError(f"不支持的输出格式：{value}")
        if fmt not in out: out.append(fmt)
    return out

def make_metadata(region:str|None, entities:list[str]|None, formats:list[str]|None, entities_decided:bool=False)->dict[str,object]:
    meta={"schema_version":"2.1","skill_version":"2.1"}
    if region:
        meta.update(normalize_region(region)); meta["region_confirmed"]=not bool(meta.get("scope_requires_review"))
    else:
        meta.update({"requested_region":"","normalized_region":"","region_type":"","research_scope":[],"region_confirmed":False})
    decided=entities_decided or entities is not None
    meta["requested_entities"]=[x.strip() for x in (entities or []) if x.strip()]
    meta["specified_entities_confirmed"]=decided
    if formats:
        meta["requested_output_format"]=normalize_formats(formats); meta["output_format_confirmed"]=True
    else:
        meta["requested_output_format"]=[]; meta["output_format_confirmed"]=False
    ready=all(bool(meta.get(k)) for k in ("region_confirmed","specified_entities_confirmed","output_format_confirmed"))
    meta["run_status"]="ready" if ready else "preflight-incomplete"
    meta["candidate_pool_frozen"]=False; meta["semantic_coverage_gate"]=False; meta["saturation_gate"]=False
    return meta

def missing_questions(meta:dict[str,object])->list[str]:
    if not meta.get("region_confirmed"): return ["region"]
    if not meta.get("specified_entities_confirmed"): return ["specified_entities"]
    if not meta.get("output_format_confirmed"): return ["output_format"]
    return []

def self_test():
    a=make_metadata(None,None,None); assert missing_questions(a)==["region"]
    b=make_metadata("天津",None,None); assert b["normalized_region"]=="天津市" and missing_questions(b)==["specified_entities"]
    c=make_metadata("天津",["津仕","北宋"],None); assert missing_questions(c)==["output_format"]
    d=make_metadata("天津",["津仕","北宋"],["Word"]); assert d["run_status"]=="ready" and d["requested_output_format"]==["docx"]
    e=make_metadata("广东",[],["PDF"],entities_decided=True); assert e["run_status"]=="ready"

def main()->int:
    p=argparse.ArgumentParser(description="生成 GEO v2.1 Preflight metadata")
    p.add_argument("--region");p.add_argument("--entity",action="append",dest="entities");p.add_argument("--no-specified-entities",action="store_true");p.add_argument("--format",action="append",dest="formats");p.add_argument("--output",type=Path);p.add_argument("--self-test",action="store_true");args=p.parse_args()
    if args.self_test: self_test(); print("preflight 自测：通过（5 个场景）"); return 0
    try: meta=make_metadata(args.region,args.entities,args.formats,args.no_specified_entities)
    except ValueError as exc: p.error(str(exc))
    text=json.dumps(meta,ensure_ascii=False,indent=2)
    if args.output: args.output.write_text(text+"\n",encoding="utf-8")
    else: print(text)
    return 0
if __name__=="__main__": raise SystemExit(main())
