#!/usr/bin/env python3
"""Generate v2.1 SVG charts from current-run CSV/JSON only."""
from __future__ import annotations
import argparse, csv, html, json
from collections import defaultdict, Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

TRUE={"1","true","yes","y","是"}
DIMENSIONS=[("query_coverage",30,"泛词覆盖"),("entity_clarity",25,"实体清晰"),("external_diversity",20,"外部多样"),("concept_ownership",15,"概念占位"),("freshness",10,"新鲜度")]

def read_csv(path:Path):
    with path.open("r",encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f))
def esc(s): return html.escape(str(s))
def num(v,default=0.0):
    try:return float(v)
    except:return default

def recall_by_entity(queries,results):
    qmap={q.get("query_id",""):q for q in queries}
    valid={qid for qid,q in qmap.items() if q.get("query_type","").lower()=="generic" and q.get("query_purpose","").lower()=="measurement" and q.get("measurement_target","").lower() in {"","institution"} and q.get("status","").lower()=="sampled"}
    hits=defaultdict(set)
    for r in results:
        if r.get("matched","").lower() in TRUE and r.get("counts_as_measurement_hit","").lower() in TRUE and r.get("query_id","") in valid and r.get("entity_id",""):
            hits[r["entity_id"]].add(r["query_id"])
    den=len(valid)
    return {eid:(len(qs)/den if den else 0.0) for eid,qs in hits.items()},den

def parse_date(s):
    if not s:return None
    try:return date.fromisoformat(s[:10])
    except:return None

def re_split(s):
    import re
    return [x.strip() for x in re.split(r"[|｜;,，；]",s or "") if x.strip()]

def authority_indices(scores,evidence,relations,observation:date):
    by=defaultdict(list)
    for e in evidence: by[e.get("entity_id","")].append(e)
    rel_by=defaultdict(list)
    for r in relations: rel_by[r.get("target_entity_id","")].append(r); rel_by[r.get("source_entity_id","")].append(r)
    grade={"A1":1.0,"A2":0.75,"B":0.5,"C":0.2};out={}
    for s in scores:
        eid=s.get("entity_id",""); rows=[e for e in by[eid] if e.get("counting_scope","").lower()!="ignored"]
        g=sum(grade.get(e.get("source_grade","").upper(),0) for e in rows)/len(rows) if rows else 0
        domains={urlparse(e.get("source_url","")).netloc.lower().removeprefix("www.") for e in rows if e.get("independent","").lower() in TRUE and e.get("source_url")}
        div={0:0,1:.35,2:.6,3:.8}.get(len(domains),1.0)
        keyrels=[r for r in rel_by[eid] if r.get("relation_type","") in {"operated-by","brand-of","teaches-at","founded-by","offers","located-in"}]
        cross=sum(1 for r in keyrels if len(re_split(r.get("evidence_ids","")))>=2)/len(keyrels) if keyrels else 0
        fresh_rows=[e for e in rows if parse_date(e.get("published_date",""))]
        fresh=sum((observation-parse_date(e.get("published_date",""))).days<=365 for e in fresh_rows)/len(fresh_rows) if fresh_rows else 0
        dup=sum(1 for e in rows if e.get("counting_scope","").lower()!="ignored")/len(rows) if rows else 0
        out[eid]=round(100*(.35*g+.25*div+.20*cross+.10*fresh+.10*dup),1)
    return out

def svg_wrap(width,height,body,title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}"><rect width="100%" height="100%" fill="#fff"/><style>text{{font-family:'Noto Sans CJK SC','PingFang SC','Microsoft YaHei',sans-serif;fill:#182638}} .muted{{fill:#6b778c}} .axis{{stroke:#b8c4d4;stroke-width:1}} .grid{{stroke:#e5eaf1;stroke-width:1}} .bar{{fill:#244f7d}} .label{{font-size:13px}} .small{{font-size:11px}} .title{{font-size:20px;font-weight:700}}</style><text x="24" y="30" class="title">{esc(title)}</text>{body}</svg>'''

def ranking_svg(scores):
    rows=sorted(scores,key=lambda r:num(r.get("total")),reverse=True);w=900;left=190;top=55;rowh=32;h=max(180,top+len(rows)*rowh+55);body=[]
    for i,r in enumerate(rows):
        y=top+i*rowh;value=num(r.get("total"));bw=(w-left-120)*value/100
        body.append(f'<text x="{left-10}" y="{y+17}" text-anchor="end" class="label">{esc(r.get("institution",""))}</text><rect x="{left}" y="{y+3}" width="{bw:.1f}" height="18" rx="3" class="bar"/><text x="{left+bw+8:.1f}" y="{y+17}" class="label">{value:g} / {esc(r.get("tier",""))}</text>')
    body.append(f'<text x="24" y="{h-20}" class="small muted">GEO观察指数衡量公开网络与AI可利用资产结构，不代表教学水平、市场份额或通过率。</text>')
    return svg_wrap(w,h,"".join(body),"GEO综合排名")

def matrix_svg(scores,recall,authority):
    w=900;h=560;x0=90;y0=70;pw=750;ph=410;valsx=[recall.get(r.get("entity_id",""),0) for r in scores];valsy=[authority.get(r.get("entity_id",""),0) for r in scores]
    def median(a):
        b=sorted(a);n=len(b);return b[n//2] if n%2 else ((b[n//2-1]+b[n//2])/2 if n else 0.5)
    mx=median(valsx) if valsx else .5;my=median(valsy) if valsy else 50
    body=[f'<line x1="{x0}" y1="{y0+ph}" x2="{x0+pw}" y2="{y0+ph}" class="axis"/><line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0+ph}" class="axis"/>',f'<line x1="{x0+pw*mx:.1f}" y1="{y0}" x2="{x0+pw*mx:.1f}" y2="{y0+ph}" class="grid"/><line x1="{x0}" y1="{y0+ph*(1-my/100):.1f}" x2="{x0+pw}" y2="{y0+ph*(1-my/100):.1f}" class="grid"/>']
    body += [f'<text x="{x0+pw/2}" y="{h-20}" text-anchor="middle" class="label">Measurement Recall Rate</text>',f'<text transform="translate(22 {y0+ph/2}) rotate(-90)" text-anchor="middle" class="label">Evidence Authority Index</text>',f'<text x="{x0+pw-10}" y="{y0+20}" text-anchor="end" class="small muted">成熟占位型</text>',f'<text x="{x0+10}" y="{y0+20}" class="small muted">高权威低召回型</text>',f'<text x="{x0+pw-10}" y="{y0+ph-10}" text-anchor="end" class="small muted">主动铺量型</text>',f'<text x="{x0+10}" y="{y0+ph-10}" class="small muted">基础薄弱型</text>']
    for r in scores:
        eid=r.get("entity_id","");x=x0+pw*recall.get(eid,0);y=y0+ph*(1-authority.get(eid,0)/100);body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" class="bar"/><text x="{x+9:.1f}" y="{y-7:.1f}" class="small">{esc(r.get("institution",""))}</text>')
    return svg_wrap(w,h,"".join(body),"Authority × Recall竞争矩阵")

def heatmap_svg(scores):
    rows=sorted(scores,key=lambda r:num(r.get("total")),reverse=True)[:8];w=930;left=190;top=80;cellw=135;cellh=38;h=top+len(rows)*cellh+45;body=[]
    for j,(_,_,label) in enumerate(DIMENSIONS):body.append(f'<text x="{left+j*cellw+cellw/2}" y="{top-18}" text-anchor="middle" class="small">{label}</text>')
    for i,r in enumerate(rows):
        y=top+i*cellh;body.append(f'<text x="{left-12}" y="{y+24}" text-anchor="end" class="label">{esc(r.get("institution",""))}</text>')
        for j,(field,maxv,_) in enumerate(DIMENSIONS):
            p=max(0,min(1,num(r.get(field))/maxv));shade=int(245-115*p);fill=f'rgb({shade},{shade+8 if shade<247 else 247},{min(255,shade+22)})';x=left+j*cellw;body.append(f'<rect x="{x}" y="{y}" width="{cellw-6}" height="30" rx="3" fill="{fill}"/><text x="{x+(cellw-6)/2}" y="{y+20}" text-anchor="middle" class="small">{p*100:.0f}%</text>')
    return svg_wrap(w,h,"".join(body),"五维能力热力图")

def funnel_svg(candidates,entities,scores):
    inst_ids={e.get("entity_id","") for e in entities if e.get("entity_type","") in {"institution","brand"}};unique={c.get("entity_id","") for c in candidates if c.get("entity_id","") in inst_ids};evaluable={c.get("entity_id","") for c in candidates if c.get("entity_id","") in inst_ids and c.get("status","") in {"scored","evidence-insufficient"}};stages=[("候选记录",len(candidates)),("独立机构候选",len(unique)),("具备评估条件",len(evaluable)),("正式评分",len(scores))];status=Counter(c.get("status","") for c in candidates);w=900;h=480;cx=330;top=70;maxn=max([n for _,n in stages] or [1]);body=[]
    for i,(label,n) in enumerate(stages):
        width=max(420*(n/maxn if maxn else 1),150);x=cx-width/2;y=top+i*82;body.append(f'<polygon points="{x},{y} {x+width},{y} {x+width-28},{y+52} {x+28},{y+52}" fill="#244f7d" opacity="{1-i*.12:.2f}"/><text x="{cx}" y="{y+23}" text-anchor="middle" style="fill:white;font-size:15px;font-weight:700">{n}</text><text x="{cx}" y="{y+43}" text-anchor="middle" style="fill:white;font-size:11px">{esc(label)}</text>')
    x=620;body.append(f'<text x="{x}" y="95" class="label">状态补充</text>')
    for i,key in enumerate(["evidence-insufficient","merged","excluded","unresolved"]):body.append(f'<text x="{x}" y="{125+i*30}" class="small">{key}: {status.get(key,0)}</text>')
    return svg_wrap(w,h,"".join(body),"Candidate Discovery 漏斗")

def generate(run:Path):
    scores=read_csv(run/"scores.csv");queries=read_csv(run/"queries.csv");results=read_csv(run/"query_results.csv");evidence=read_csv(run/"evidence.csv");candidates=read_csv(run/"candidate_pool.csv");entities=read_csv(run/"entities.csv");relations=read_csv(run/"entity_relations.csv");meta=json.loads((run/"run_metadata.json").read_text(encoding="utf-8"));observation=date.fromisoformat(meta.get("observation_date") or date.today().isoformat());recall,den=recall_by_entity(queries,results);authority=authority_indices(scores,evidence,relations,observation);out=run/"charts";out.mkdir(exist_ok=True);svgs={"geo-score-ranking.svg":ranking_svg(scores),"authority-recall-matrix.svg":matrix_svg(scores,recall,authority),"dimension-heatmap.svg":heatmap_svg(scores),"candidate-funnel.svg":funnel_svg(candidates,entities,scores)}
    for name,text in svgs.items():(out/name).write_text(text,encoding="utf-8")
    chart_data={"measurement_denominator":den,"recall_rate":recall,"authority_index":authority,"ranking":[{"entity_id":r.get("entity_id"),"institution":r.get("institution"),"total":num(r.get("total")),"tier":r.get("tier")} for r in sorted(scores,key=lambda x:num(x.get("total")),reverse=True)]};(out/"chart_data.json").write_text(json.dumps(chart_data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return chart_data

def main():
    ap=argparse.ArgumentParser();ap.add_argument("run_dir",nargs="?",type=Path);ap.add_argument("--self-test",action="store_true");a=ap.parse_args()
    if a.self_test:print("generate_charts：请运行 scripts/test_v21.py 完整自测");return 0
    if not a.run_dir:ap.error("必须提供 run_dir")
    generate(a.run_dir);print(a.run_dir/"charts");return 0
if __name__=="__main__":raise SystemExit(main())
