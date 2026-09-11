#!/usr/bin/env python3
"""Score annotation blind-recheck agreement as diagnostics, not a universal release gate.

Expected annotation_rechecks.csv columns:
review_id, answer_id, first_positive_set, second_positive_set, first_intents, second_intents,
disagreement, resolution, reviewer, notes

Positive sets use pipe-separated entity ids. Intent maps use JSON objects {entity_id:intent}.
"""
from __future__ import annotations
import argparse,csv,json,math
from collections import Counter
from pathlib import Path

CLASSES={"recommended","listed","comparison","caveat","excluded"}
THREE=lambda x: "recommended" if x=="recommended" else "listed" if x=="listed" else "non-positive"

def rcsv(p):
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def splitset(v):return {x.strip() for x in str(v or "").split("|") if x.strip()}
def loadmap(v):
    if not str(v or "").strip():return {}
    obj=json.loads(v)
    if not isinstance(obj,dict):raise ValueError("first_intents/second_intents 必须是 JSON object")
    return {str(k):str(val) for k,val in obj.items()}
def kappa(pairs):
    if not pairs:return None
    n=len(pairs);agree=sum(a==b for a,b in pairs)/n
    ca=Counter(a for a,_ in pairs);cb=Counter(b for _,b in pairs)
    labels=set(ca)|set(cb);pe=sum((ca[x]/n)*(cb[x]/n) for x in labels)
    return None if math.isclose(1-pe,0) else (agree-pe)/(1-pe)
def score(run:Path):
    rows=rcsv(run/"annotation_rechecks.csv");positive_exact=0;intent_pairs=[];three_pairs=[];conf=Counter();reviewed=0
    for r in rows:
        a=splitset(r.get("first_positive_set"));b=splitset(r.get("second_positive_set"));positive_exact+=a==b;reviewed+=1
        m1=loadmap(r.get("first_intents"));m2=loadmap(r.get("second_intents"))
        for eid in sorted(set(m1)&set(m2)):
            x=m1[eid];y=m2[eid]
            if x not in CLASSES or y not in CLASSES:continue
            intent_pairs.append((x,y));three_pairs.append((THREE(x),THREE(y)));conf[(x,y)]+=1
    out={"schema_version":"2.2","reviewed_answer_cells":reviewed,"positive_set_exact_agreement":round(positive_exact/reviewed,4) if reviewed else None,"intent_exact_agreement":round(sum(a==b for a,b in intent_pairs)/len(intent_pairs),4) if intent_pairs else None,"three_class_agreement":round(sum(a==b for a,b in three_pairs)/len(three_pairs),4) if three_pairs else None,"cohens_kappa_intent":round(kappa(intent_pairs),4) if kappa(intent_pairs) is not None else None,"cohens_kappa_three_class":round(kappa(three_pairs),4) if kappa(three_pairs) is not None else None,"listed_caveat_confusions":conf.get(("listed","caveat"),0)+conf.get(("caveat","listed"),0),"confusion_matrix":{f"{a}->{b}":n for (a,b),n in sorted(conf.items())},"note":"Diagnostic only. Any 80% threshold is provisional until calibrated across datasets/reviewers."}
    (run/"annotation_agreement.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(score(a.run_dir),ensure_ascii=False));return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"score_annotation_rechecks：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
