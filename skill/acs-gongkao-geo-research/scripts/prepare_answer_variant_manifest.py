#!/usr/bin/env python3
"""Create answer_variant_manifest.csv without mutating raw ai_answers.jsonl.

For new runs, query_variant_id should be recorded natively in ai_answers.jsonl. For legacy runs
sampled before that field existed, this sidecar reconstructs a deterministic identifier from
sample_run + the declared run-level query_variant_mode. Reconstructed IDs are explicitly marked
legacy-reconstructed and must not be described as originally recorded variant queries.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

FIELDS=["answer_id","query_id","engine","model","sample_run","query_variant_id","evidence_status","assignment_basis","notes"]
VALID_MODES={"exact-query-repeat","semantic-retrieval-variants"}


def rjsonl(p:Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

def wcsv(p:Path,rows):
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)

def derive_variant(sample_run:int,mode:str)->str:
    if mode=="semantic-retrieval-variants":
        return "canonical" if sample_run==1 else f"semantic-variant-{sample_run}"
    return f"exact-repeat-{sample_run}"

def build(run:Path):
    mp=run/"run_metadata.json";ap=run/"ai_answers.jsonl"
    if not mp.is_file() or not ap.is_file():raise ValueError("缺 run_metadata.json / ai_answers.jsonl")
    meta=json.loads(mp.read_text(encoding="utf-8"));mode=meta.get("query_variant_mode")
    if mode not in VALID_MODES:raise ValueError("run_metadata.query_variant_mode 无效")
    answers=rjsonl(ap);rows=[];seen=set()
    for a in answers:
        aid=str(a.get("answer_id") or "").strip()
        if not aid or aid in seen:raise ValueError(f"answer_id 重复/为空: {aid}")
        seen.add(aid)
        try:sr=int(a.get("sample_run"))
        except Exception:raise ValueError(f"{aid}: sample_run 无效")
        if sr<1:raise ValueError(f"{aid}: sample_run 必须 >=1")
        native=str(a.get("query_variant_id") or "").strip()
        if native:
            qv=native;status="native-recorded";basis="ai_answers.jsonl.query_variant_id"
        else:
            qv=derive_variant(sr,mode);status="legacy-reconstructed";basis=f"sample_run={sr} + run_metadata.query_variant_mode={mode}"
        rows.append({
            "answer_id":aid,"query_id":a.get("query_id","") or "","engine":a.get("engine","") or "","model":a.get("model","") or "",
            "sample_run":sr,"query_variant_id":qv,"evidence_status":status,"assignment_basis":basis,
            "notes":"legacy-reconstructed 表示迁移侧写，不代表原采样时逐 Cell 原生记录" if status=="legacy-reconstructed" else ""
        })
    out=run/"answer_variant_manifest.csv";wcsv(out,rows)
    summary={
        "schema_version":"2.2","query_variant_mode":mode,"answer_cells":len(rows),
        "native_recorded":sum(r["evidence_status"]=="native-recorded" for r in rows),
        "legacy_reconstructed":sum(r["evidence_status"]=="legacy-reconstructed" for r in rows),
        "raw_answers_modified":False
    }
    (run/"answer_variant_manifest_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(build(a.run_dir),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"prepare_answer_variant_manifest：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
