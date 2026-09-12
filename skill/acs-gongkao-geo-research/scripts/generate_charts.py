#!/usr/bin/env python3
"""Generate customer-facing PNG charts for the Chinese GEO report.

Rules:
- Customer charts are Chinese-first. Never fall back to English labels.
- Charts should communicate a decision, not mirror internal enums/tables.
- Missing evidence is omitted from score rankings rather than rendered as zero.
- Report Entity Identity is one point per entity; `both` never creates duplicate scatter points.
"""
from __future__ import annotations
import argparse,csv,json,statistics
from pathlib import Path
from fs_utils import ensure_directory


def rcsv(p:Path):
    if not p.is_file():return []
    with p.open("r",encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))


def fnum(v):
    try:return float(v)
    except:return None


def configure_font(plt):
    try:
        from matplotlib import font_manager
        names={f.name for f in font_manager.fontManager.ttflist}
        for cand in ["PingFang SC","Microsoft YaHei","Noto Sans CJK SC","Noto Sans CJK JP","SimHei","Arial Unicode MS","WenQuanYi Zen Hei"]:
            if cand in names:
                plt.rcParams["font.sans-serif"]=[cand,"DejaVu Sans"]
                plt.rcParams["axes.unicode_minus"]=False
                return True
    except Exception:
        pass
    return False


def _save(fig,plt,path:Path):
    fig.tight_layout();fig.savefig(path,bbox_inches="tight");plt.close(fig)


def _bar_labels(ax,bars,values,suffix="%",extras=None):
    extras=extras or [""]*len(values)
    for b,v,extra in zip(bars,values,extras):
        label=f"{v:.1f}{suffix}{extra}"
        ax.text(b.get_width()+max(0.8,b.get_width()*0.015),b.get_y()+b.get_height()/2,label,va="center",fontsize=8)


def generate(run:Path):
    try:import matplotlib.pyplot as plt
    except Exception as e:raise RuntimeError(f"缺少 matplotlib，无法生成图表：{e}")
    cjk=configure_font(plt)
    out=ensure_directory(run/"charts")
    metrics=rcsv(run/"ai_metrics.csv")
    assets=rcsv(run/"asset_scores.csv")
    concepts=rcsv(run/"concept_ownership.csv")
    files=[]

    # 1) AI 可见度 × GEO 资产基础：每个现实主体只画一个点。
    asset_by={r.get("entity_id"):r for r in assets}
    best_by_entity={}
    for r in metrics:
        eid=r.get("entity_id");a=asset_by.get(eid) or {}
        x=fnum(a.get("asset_readiness"));y=fnum(r.get("nomination_rate"))
        if not eid or x is None or y is None:continue
        point={"name":r.get("canonical_name") or a.get("canonical_name") or eid,"x":x,"y":y*100,"target":r.get("measurement_target")}
        old=best_by_entity.get(eid)
        if old is None or point["y"]>old["y"]:best_by_entity[eid]=point
    points=list(best_by_entity.values())
    if points:
        xs=[p["x"] for p in points];ys=[p["y"] for p in points]
        mx=statistics.median(xs);my=statistics.median(ys)
        fig,ax=plt.subplots(figsize=(6.7,4.4),dpi=180)
        ax.scatter(xs,ys,s=30)
        ax.axvline(mx,linestyle="--",linewidth=0.8);ax.axhline(my,linestyle="--",linewidth=0.8)
        top=sorted(range(len(points)),key=lambda i:(points[i]["y"],points[i]["x"]),reverse=True)[:12]
        for rank,i in enumerate(top,1):
            p=points[i];label=p["name"] if cjk else f"#{rank}"
            ax.annotate(label,(p["x"],p["y"]),xytext=(4,4),textcoords="offset points",fontsize=7)
        if cjk:
            ax.set_xlabel("GEO 资产基础得分")
            ax.set_ylabel("AI 提名率（%）")
            ax.set_title("AI 可见度 × GEO 资产基础（虚线为本轮中位数）")
        else:
            ax.set_xlabel("0–100");ax.set_ylabel("%")
        ax.set_xlim(0,105);ax.set_ylim(bottom=0)
        p=out/"market-universe.png";_save(fig,plt,p);files.append(p.name)

    def visibility(rows,filename,title):
        rows=[r for r in rows if fnum(r.get("nomination_rate")) is not None]
        rows=sorted(rows,key=lambda r:fnum(r.get("nomination_rate")) or 0,reverse=True)[:12]
        if not rows:return
        names=[r.get("canonical_name","") for r in rows]
        labels=names if cjk else [f"#{i+1}" for i in range(len(rows))]
        values=[100*(fnum(r.get("nomination_rate")) or 0) for r in rows]
        fig,ax=plt.subplots(figsize=(6.7,max(3.2,0.34*len(rows)+1.4)),dpi=180)
        bars=ax.barh(list(reversed(labels)),list(reversed(values)))
        _bar_labels(ax,bars,list(reversed(values)))
        ax.set_xlim(0,max(100,max(values)*1.18 if values else 100))
        if cjk:
            ax.set_xlabel("AI 提名率（%）");ax.set_title(title)
        else:ax.set_xlabel("%")
        p=out/filename;_save(fig,plt,p);files.append(p.name)

    inst=[r for r in metrics if r.get("measurement_target")=="institution"]
    visibility([r for r in inst if r.get("market_role")=="national-benchmark"],"ai-visibility-national.png","全国品牌 AI 提名率")
    visibility([r for r in inst if r.get("market_role") in {"local-core","local-active"} and r.get("market_scope") in {"local","regional"}],"ai-visibility-local.png","本地 / 区域机构 AI 提名率")
    ips=[r for r in metrics if r.get("measurement_target")=="ip" and r.get("market_role")=="expert-ip"]
    visibility(ips,"ai-visibility-ip.png","老师 / IP AI 提名率")

    scored=[]
    for r in assets:
        score=fnum(r.get("asset_readiness"))
        if score is not None:scored.append((r,score))
    scored=sorted(scored,key=lambda x:x[1],reverse=True)[:15]
    if scored:
        names=[r.get("canonical_name") or r.get("institution") or r.get("entity_id") for r,_ in scored]
        labels=names if cjk else [f"#{i+1}" for i in range(len(scored))]
        values=[s for _,s in scored];extras=[f" / {r.get('asset_tier')}" if r.get("asset_tier") else "" for r,_ in scored]
        fig,ax=plt.subplots(figsize=(6.7,max(3.2,0.34*len(scored)+1.5)),dpi=180)
        bars=ax.barh(list(reversed(labels)),list(reversed(values)))
        _bar_labels(ax,bars,list(reversed(values)),suffix="",extras=list(reversed(extras)))
        ax.set_xlim(0,112)
        if cjk:
            ax.set_xlabel("GEO 资产基础得分（100分制）");ax.set_title("GEO 资产基础排名（仅展示可评分主体）")
        else:ax.set_xlabel("0–100")
        p=out/"asset-readiness.png";_save(fig,plt,p);files.append(p.name)

    ranked=[]
    for r in concepts:
        strength=fnum(r.get("strength") or r.get("score"))
        if strength is None:continue
        entity=r.get("canonical_name") or r.get("entity_name") or "";concept=r.get("concept") or ""
        if entity and concept:ranked.append((r,strength,entity,concept))
    ranked=sorted(ranked,key=lambda x:x[1],reverse=True)[:10]
    if ranked:
        labels=[f"{e}｜{c}" for _,_,e,c in ranked] if cjk else [f"#{i+1}" for i in range(len(ranked))]
        values=[s for _,s,_,_ in ranked]
        fig,ax=plt.subplots(figsize=(6.7,max(3.4,0.42*len(ranked)+1.4)),dpi=180)
        bars=ax.barh(list(reversed(labels)),list(reversed(values)))
        _bar_labels(ax,bars,list(reversed(values)),suffix="")
        ax.set_xlim(0,max(10.8,max(values)*1.15 if values else 10.8))
        if cjk:
            ax.set_xlabel("概念绑定强度（10分制）");ax.set_title("概念占位 Top 10")
        p=out/"concept-ownership.png";_save(fig,plt,p);files.append(p.name)

    payload={"files":files,"cjk_font_available":cjk,"customer_chart_language":"zh-CN","generated_from":{"ai_metrics":len(metrics),"asset_scores":len(assets),"concept_rows":len(concepts),"opportunity_matrix_entities":len(points)}}
    (out/"chart_manifest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return payload


def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(generate(a.run_dir),ensure_ascii=False));return 0
    except (OSError,RuntimeError,ValueError) as e:print(f"generate_charts：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
