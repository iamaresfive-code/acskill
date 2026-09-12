#!/usr/bin/env python3
"""Generate Word-oriented PNG charts for GEO v2.2. Optional dependency: matplotlib."""
from __future__ import annotations
import argparse,csv,json
from collections import Counter,defaultdict
from pathlib import Path
from fs_utils import ensure_directory

def rcsv(p:Path):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def fnum(v):
    try:return float(v)
    except:return 0.0

def configure_font(plt):
    try:
        from matplotlib import font_manager
        names={f.name for f in font_manager.fontManager.ttflist}
        for cand in ["PingFang SC","Microsoft YaHei","Noto Sans CJK SC","Noto Sans CJK JP","SimHei","Arial Unicode MS","WenQuanYi Zen Hei"]:
            if cand in names:plt.rcParams["font.sans-serif"]=[cand,"DejaVu Sans"];plt.rcParams["axes.unicode_minus"]=False;return True
    except Exception:pass
    return False

def generate(run:Path):
    try:import matplotlib.pyplot as plt
    except Exception as e:raise RuntimeError(f"缺少 matplotlib，无法生成图表：{e}")
    cjk=configure_font(plt);out=ensure_directory(run/"charts");universe=rcsv(run/"market_universe.csv");metrics=rcsv(run/"ai_metrics.csv");assets=rcsv(run/"asset_scores.csv");concepts=rcsv(run/"concept_ownership.csv");files=[];counts=Counter()
    for r in universe:
        if r.get("universe_status")=="included":counts[r.get("market_role") or "unclassified"]+=1
    if counts:
        labels=list(counts);values=[counts[x] for x in labels];fig,ax=plt.subplots(figsize=(6.5,3.4),dpi=180);ax.barh(labels,values);ax.set_xlabel("Entity count");ax.set_title("Market Universe Composition");fig.tight_layout();p=out/"market-universe.png";fig.savefig(p,bbox_inches="tight");plt.close(fig);files.append(p.name)
    def visibility(rows,filename,title):
        rows=sorted(rows,key=lambda r:fnum(r.get("nomination_rate")),reverse=True)[:15]
        if not rows:return
        names=[r.get("canonical_name","") for r in rows];labels=names if cjk else [f"#{i+1}" for i in range(len(rows))];fig,ax=plt.subplots(figsize=(6.5,max(3.2,0.28*len(rows)+1.5)),dpi=180);ax.barh(list(reversed(labels)),[100*fnum(r.get("nomination_rate")) for r in reversed(rows)]);ax.set_xlabel("Nomination rate (%)");ax.set_title(title);ax.set_xlim(0,100)
        if not cjk:ax.text(0,-0.17,"Entity names are mapped by rank in the table below.",transform=ax.transAxes,fontsize=8)
        fig.tight_layout();p=out/filename;fig.savefig(p,bbox_inches="tight");plt.close(fig);files.append(p.name)
    # Charts use Stage 1 market_role/scope plus explicit metric target. entity_type never re-buckets a subject.
    inst=[r for r in metrics if r.get("measurement_target")=="institution"]
    visibility([r for r in inst if r.get("market_role")=="national-benchmark"],"ai-visibility-national.png","AI Answer Visibility — National Benchmarks")
    visibility([r for r in inst if r.get("market_role") in {"local-core","local-active"} and r.get("market_scope") in {"local","regional"}],"ai-visibility-local.png","AI Answer Visibility — Local / Regional Institutions")
    ips=[r for r in metrics if r.get("measurement_target")=="ip" and r.get("market_role")=="expert-ip"]
    visibility(ips,"ai-visibility-ip.png","AI Answer Visibility — Expert / IP")
    aset=sorted(assets,key=lambda r:fnum(r.get("asset_readiness")),reverse=True)[:15]
    if aset:
        names=[r.get("canonical_name") or r.get("institution") or r.get("entity_id") for r in aset];labels=names if cjk else [f"#{i+1}" for i in range(len(aset))];fig,ax=plt.subplots(figsize=(6.5,max(3.2,0.28*len(aset)+1.5)),dpi=180);ax.barh(list(reversed(labels)),[fnum(r.get("asset_readiness")) for r in reversed(aset)]);ax.set_xlabel("Asset Readiness / 100");ax.set_title("GEO Asset Readiness");ax.set_xlim(0,100)
        if not cjk:ax.text(0,-0.17,"Entity names are mapped by rank in the table below.",transform=ax.transAxes,fontsize=8)
        fig.tight_layout();p=out/"asset-readiness.png";fig.savefig(p,bbox_inches="tight");plt.close(fig);files.append(p.name)
    if concepts:
        concept_names=[];entity_names=[];matrix=defaultdict(dict)
        for r in concepts:
            c=r.get("concept","");e=r.get("canonical_name") or r.get("entity_name","")
            if c and c not in concept_names:concept_names.append(c)
            if e and e not in entity_names:entity_names.append(e)
            matrix[e][c]=fnum(r.get("strength") or r.get("score"))
        concept_names=concept_names[:10];entity_names=entity_names[:12]
        if concept_names and entity_names:
            data=[[matrix[e].get(c,0) for c in concept_names] for e in entity_names];xlabels=concept_names if cjk else [f"C{i+1}" for i in range(len(concept_names))];ylabels=entity_names if cjk else [f"E{i+1}" for i in range(len(entity_names))];fig,ax=plt.subplots(figsize=(6.5,max(3.6,0.32*len(entity_names)+1.5)),dpi=180);im=ax.imshow(data,aspect="auto");ax.set_xticks(range(len(xlabels)),xlabels,rotation=45,ha="right");ax.set_yticks(range(len(ylabels)),ylabels);ax.set_title("Concept Ownership Map");fig.colorbar(im,ax=ax,fraction=.03,pad=.02);fig.tight_layout();p=out/"concept-ownership.png";fig.savefig(p,bbox_inches="tight");plt.close(fig);files.append(p.name)
    payload={"files":files,"cjk_font_available":cjk,"generated_from":{"market_universe":len(universe),"ai_metrics":len(metrics),"asset_scores":len(assets),"concept_rows":len(concepts)}};(out/"chart_manifest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return payload

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(generate(a.run_dir),ensure_ascii=False));return 0
    except (OSError,RuntimeError,ValueError) as e:print(f"generate_charts：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
