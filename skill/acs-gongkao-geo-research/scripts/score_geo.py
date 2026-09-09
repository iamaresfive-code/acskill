#!/usr/bin/env python3
"""计算固定五维公考 GEO 分数；v2.1 仅从机构 Measurement 派生机构召回指标。"""
from __future__ import annotations
import argparse, csv, json, math, sys
from pathlib import Path
from typing import Any

WEIGHTS={"query_coverage":30,"entity_clarity":25,"external_diversity":20,"concept_ownership":15,"freshness":10}
TRUE_VALUES={"1","true","yes","y","是"}
class ScoreError(ValueError): pass

def tier_for(total:float)->str:
    if total>=85:return "S"
    if total>=80:return "A+"
    if total>=70:return "A"
    if total>=65:return "A-"
    if total>=60:return "B+"
    if total>=50:return "B"
    if total>=45:return "B-"
    return "C"

def _number(value:Any,field:str)->float:
    if isinstance(value,bool) or not isinstance(value,(int,float)): raise ScoreError(f"{field} 必须是数字")
    v=float(value)
    if not math.isfinite(v): raise ScoreError(f"{field} 必须是有限数值")
    return v

def score_record(record:dict[str,Any])->dict[str,Any]:
    if not isinstance(record,dict): raise ScoreError("每条评分记录必须是 JSON 对象")
    vals={}
    for field,maximum in WEIGHTS.items():
        if field not in record: raise ScoreError(f"缺少必需字段：{field}")
        v=_number(record[field],field)
        if not 0<=v<=maximum: raise ScoreError(f"{field} 必须在 0 到 {maximum} 之间")
        vals[field]=v
    total=round(sum(vals.values()),4); out=dict(record); out.update(vals); out["total"]=int(total) if total.is_integer() else total; out["tier"]=tier_for(total); return out

def _read_csv(path:Path)->list[dict[str,str]]:
    if not path.is_file(): raise ScoreError(f"缺少 {path.name}")
    with path.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))

def derive_query_metrics(run_dir:Path)->tuple[dict[str,dict[str,int]],int]:
    queries=_read_csv(run_dir/"queries.csv"); results=_read_csv(run_dir/"query_results.csv")
    qmap={r.get("query_id","").strip():r for r in queries}
    mids={qid for qid,r in qmap.items() if r.get("query_type","").lower()=="generic" and r.get("query_purpose","").lower()=="measurement" and r.get("measurement_target","").lower()=="institution" and r.get("status","").lower()=="sampled"}
    metrics={}
    for r in results:
        if r.get("matched","").lower() not in TRUE_VALUES: continue
        eid=r.get("entity_id","").strip(); qid=r.get("query_id","").strip()
        if not eid or qid not in qmap: continue
        item=metrics.setdefault(eid,{"generic":set(),"brand":set()}); q=qmap[qid]
        if qid in mids and r.get("counts_as_measurement_hit","").lower() in TRUE_VALUES:item["generic"].add(qid)
        if q.get("query_type","").lower()=="brand" and q.get("query_purpose","").lower()=="verification":item["brand"].add(qid)
    return {eid:{"generic_hits":len(v["generic"]),"generic_queries":len(mids),"brand_hits":len(v["brand"])} for eid,v in metrics.items()},len(mids)

def calculate(payload:Any,metrics=None,denominator=0):
    records=payload if isinstance(payload,list) else [payload]; out=[]
    for item in records:
        merged=dict(item); eid=str(merged.get("entity_id","")).strip()
        if metrics is not None:
            if not eid: raise ScoreError("使用 --run-dir 时每条记录必须包含 entity_id")
            merged.update(metrics.get(eid,{"generic_hits":0,"generic_queries":denominator,"brand_hits":0}))
        out.append(score_record(merged))
    return out if isinstance(payload,list) else out[0]

def load_payload(path:str|None):
    text=Path(path).read_text(encoding="utf-8") if path and path!="-" else sys.stdin.read()
    if not text.strip(): raise ScoreError("没有收到 JSON 输入")
    try:return json.loads(text)
    except json.JSONDecodeError as e: raise ScoreError(f"JSON 无效：{e}") from e

def self_test():
    sample={"entity_id":"I1","query_coverage":24,"entity_clarity":20,"external_diversity":13,"concept_ownership":11,"freshness":8}
    assert score_record(sample)["total"]==76
    assert tier_for(76)=="A"

def main():
    p=argparse.ArgumentParser();p.add_argument("input",nargs="?");p.add_argument("--run-dir",type=Path);p.add_argument("--pretty",action="store_true");p.add_argument("--self-test",action="store_true");a=p.parse_args()
    try:
        if a.self_test:self_test();print("score_geo v2.1 自测：通过");return 0
        metrics,den=derive_query_metrics(a.run_dir) if a.run_dir else (None,0)
        print(json.dumps(calculate(load_payload(a.input),metrics,den),ensure_ascii=False,indent=2 if a.pretty else None))
        return 0
    except (OSError,ScoreError,AssertionError) as e: print(f"score_geo：错误：{e}",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
