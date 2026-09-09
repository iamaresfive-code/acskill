#!/usr/bin/env python3
"""GEO v2.2 preflight: region -> seed entities -> supplement permission. Official output is always DOCX."""
from __future__ import annotations
import argparse, json
from pathlib import Path

VERSION = "2.2"
MUNICIPALITIES={"北京":"北京市","北京市":"北京市","天津":"天津市","天津市":"天津市","上海":"上海市","上海市":"上海市","重庆":"重庆市","重庆市":"重庆市"}
PROVINCES={"广东":"广东省","广东省":"广东省","山东":"山东省","山东省":"山东省","浙江":"浙江省","浙江省":"浙江省","江苏":"江苏省","江苏省":"江苏省","河北":"河北省","河北省":"河北省","河南":"河南省","河南省":"河南省","四川":"四川省","四川省":"四川省","湖北":"湖北省","湖北省":"湖北省","湖南":"湖南省","湖南省":"湖南省","福建":"福建省","福建省":"福建省","辽宁":"辽宁省","辽宁省":"辽宁省","安徽":"安徽省","安徽省":"安徽省","江西":"江西省","江西省":"江西省","陕西":"陕西省","陕西省":"陕西省","山西":"山西省","山西省":"山西省"}
CITY_ALIASES={"广州":"广州市","广州市":"广州市","深圳":"深圳市","深圳市":"深圳市","成都":"成都市","成都市":"成都市","杭州":"杭州市","杭州市":"杭州市","南京":"南京市","南京市":"南京市","济南":"济南市","济南市":"济南市"}
CUSTOM={"珠三角":["广州市","深圳市","珠海市","佛山市","惠州市","东莞市","中山市","江门市","肇庆市"]}


def normalize_region(value:str)->dict[str,object]:
    raw=value.strip()
    if raw in MUNICIPALITIES:return {"requested_region":raw,"normalized_region":MUNICIPALITIES[raw],"region_type":"municipality","research_scope":[MUNICIPALITIES[raw]]}
    if raw in PROVINCES:return {"requested_region":raw,"normalized_region":PROVINCES[raw],"region_type":"province","research_scope":[PROVINCES[raw]]}
    if raw in CITY_ALIASES:return {"requested_region":raw,"normalized_region":CITY_ALIASES[raw],"region_type":"city","research_scope":[CITY_ALIASES[raw]]}
    if raw in CUSTOM:return {"requested_region":raw,"normalized_region":raw,"region_type":"custom-region","research_scope":CUSTOM[raw]}
    if raw.endswith("省"):return {"requested_region":raw,"normalized_region":raw,"region_type":"province","research_scope":[raw]}
    if raw.endswith("市"):return {"requested_region":raw,"normalized_region":raw,"region_type":"city","research_scope":[raw]}
    return {"requested_region":raw,"normalized_region":raw,"region_type":"custom-region","research_scope":[raw],"scope_requires_review":True}


def make_metadata(region:str|None,seeds:list[str]|None,supplement:bool|None,seed_decided:bool=False)->dict[str,object]:
    meta={"schema_version":VERSION,"skill_version":VERSION,"official_output_format":"docx"}
    if region:
        meta.update(normalize_region(region));meta["region_confirmed"]=not bool(meta.get("scope_requires_review"))
    else:
        meta.update({"requested_region":"","normalized_region":"","region_type":"","research_scope":[],"region_confirmed":False})
    clean=[]
    for x in seeds or []:
        x=x.strip()
        if x and x not in clean:clean.append(x)
    decided=seed_decided or seeds is not None
    meta["seed_entities"]=clean
    meta["seed_entities_confirmed"]=decided
    meta["allow_discovery_supplement"]=supplement
    meta["discovery_supplement_confirmed"]=supplement is not None
    meta["research_mode"]="scoped-geo-landscape" if clean else ("blind-discovery-scan" if decided else "")
    meta["market_universe_confirmed"]=False
    meta["measurement_allowed"]=False
    meta["sampling_mode"]="pending"
    ready=all(bool(meta.get(k)) for k in ("region_confirmed","seed_entities_confirmed","discovery_supplement_confirmed"))
    meta["run_status"]="universe-building" if ready else "preflight-incomplete"
    return meta


def missing_questions(meta:dict[str,object])->list[str]:
    if not meta.get("region_confirmed"):return ["region"]
    if not meta.get("seed_entities_confirmed"):return ["seed_entities"]
    if not meta.get("discovery_supplement_confirmed"):return ["discovery_supplement"]
    return []


def self_test():
    a=make_metadata(None,None,None);assert missing_questions(a)==["region"]
    b=make_metadata("广东",None,None);assert missing_questions(b)==["seed_entities"]
    c=make_metadata("广东",["甲机构","乙老师"],None);assert missing_questions(c)==["discovery_supplement"]
    d=make_metadata("广东",["甲机构"],True);assert d["research_mode"]=="scoped-geo-landscape" and d["official_output_format"]=="docx"
    e=make_metadata("山东",[],True,seed_decided=True);assert e["research_mode"]=="blind-discovery-scan"


def main()->int:
    p=argparse.ArgumentParser(description="生成 GEO v2.2 Preflight metadata")
    p.add_argument("--region")
    p.add_argument("--seed",action="append",dest="seeds")
    p.add_argument("--no-seeds",action="store_true")
    g=p.add_mutually_exclusive_group();g.add_argument("--allow-supplement",action="store_true");g.add_argument("--no-supplement",action="store_true")
    p.add_argument("--output",type=Path);p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:self_test();print("preflight v2.2 自测：通过");return 0
    supplement=True if a.allow_supplement else (False if a.no_supplement else None)
    meta=make_metadata(a.region,a.seeds,supplement,a.no_seeds)
    text=json.dumps(meta,ensure_ascii=False,indent=2)
    if a.output:a.output.write_text(text+"\n",encoding="utf-8")
    else:print(text)
    return 0
if __name__=="__main__":raise SystemExit(main())
