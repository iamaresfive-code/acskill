#!/usr/bin/env python3
"""Generate customer-facing PNG charts for the Chinese GEO report.

Rules:
- Customer charts are Chinese-first. Missing CJK font is a hard error.
- Charts communicate decisions, not internal enums or developer diagnostics.
- Missing evidence is omitted from score rankings rather than rendered as zero.
- Institution-recommendation and teacher-recommendation measurements are not mixed into one scatter plot.
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
                return cand
    except Exception:
        pass
    return ""


def _save(fig,plt,path:Path):
    fig.tight_layout();fig.savefig(path,bbox_inches="tight");plt.close(fig)


def _bar_labels(ax,bars,values,suffix="%",extras=None):
    extras=extras or [""]*len(values)
    for b,v,extra in zip(bars,values,extras):
        ax.text(b.get_width()+max(0.8,b.get_width()*0.015),b.get_y()+b.get_height()/2,
                f"{v:.1f}{suffix}{extra}",va="center",fontsize=8)


def _opportunity_rows(metrics,assets):
    """Select readable opportunity subjects without creating a synthetic composite score.

    Opportunity = has an asset score, asset score at/above the scored-sample median, and AI
    nomination rate below the median of its own measurement group. Institution and teacher
    groups therefore keep separate baselines.
    """
    asset_by={r.get("entity_id"):r for r in assets}
    rows=[]
    for r in metrics:
        score=fnum((asset_by.get(r.get("entity_id")) or {}).get("asset_readiness"))
        rate=fnum(r.get("nomination_rate"))
        if score is None or rate is None:continue
        rows.append({
            "entity_id":r.get("entity_id"),
            "name":r.get("canonical_name") or (asset_by.get(r.get("entity_id")) or {}).get("canonical_name") or r.get("entity_id"),
            "target":r.get("measurement_target"),
            "asset":score,
            "rate":rate*100,
        })
    if not rows:return [],0.0,{}
    asset_median=statistics.median([x["asset"] for x in rows])
    target_medians={}
    for target in {x["target"] for x in rows}:
        vals=[x["rate"] for x in rows if x["target"]==target]
        if vals:target_medians[target]=statistics.median(vals)
    selected=[x for x in rows if x["asset"]>=asset_median and x["rate"]<target_medians.get(x["target"],0)]
    selected=sorted(selected,key=lambda x:(-x["asset"],x["rate"],x["name"]))[:8]
    return selected,asset_median,target_medians


def generate(run:Path):
    try:import matplotlib.pyplot as plt
    except Exception as e:raise RuntimeError(f"缺少 matplotlib，无法生成图表：{e}")
    cjk_font=configure_font(plt)
    if not cjk_font:
        raise RuntimeError("未检测到可用中文字体。正式客户报告必须安装 PingFang SC / Microsoft YaHei / Noto Sans CJK SC / SimHei 等中文字体后再生成图表。")
    out=ensure_directory(run/"charts")
    metrics=rcsv(run/"ai_metrics.csv");assets=rcsv(run/"asset_scores.csv");concepts=rcsv(run/"concept_ownership.csv");files=[]

    # 1) 重点优化机会：替代难读且混合两类分母的散点图。
    opportunity,asset_median,target_medians=_opportunity_rows(metrics,assets)
    fig,ax=plt.subplots(figsize=(6.8,max(3.6,0.55*max(len(opportunity),4)+1.7)),dpi=180)
    if opportunity:
        labels=[x["name"] for x in opportunity]
        y=list(range(len(opportunity)))
        assets_v=[x["asset"] for x in opportunity];rates=[x["rate"] for x in opportunity]
        h=0.34
        bars1=ax.barh([i+h/2 for i in y],assets_v,height=h,label="GEO 资产基础得分")
        bars2=ax.barh([i-h/2 for i in y],rates,height=h,label="AI 提名率（%）")
        ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlim(0,105)
        for bars,vals in ((bars1,assets_v),(bars2,rates)):
            for b,v in zip(bars,vals):ax.text(b.get_width()+1,b.get_y()+b.get_height()/2,f"{v:.1f}",va="center",fontsize=8)
        ax.legend(loc="lower right",fontsize=8)
        ax.set_xlabel("0–100（两项指标分别解读，不相加为总分）")
        ax.set_title("重点优化机会：资产基础较强，但 AI 可见度仍偏低")
    else:
        ax.axis("off");ax.text(.5,.55,"本轮没有识别出明显的“资产较强、AI 可见度偏低”主体",ha="center",va="center",fontsize=12)
        ax.text(.5,.42,"该图只用于筛选优化机会，不代表综合排名",ha="center",va="center",fontsize=9)
    p=out/"market-universe.png";_save(fig,plt,p);files.append(p.name)

    def visibility(rows,filename,title):
        rows=[r for r in rows if fnum(r.get("nomination_rate")) is not None]
        rows=sorted(rows,key=lambda r:fnum(r.get("nomination_rate")) or 0,reverse=True)[:12]
        if not rows:return
        labels=[r.get("canonical_name","") for r in rows];values=[100*(fnum(r.get("nomination_rate")) or 0) for r in rows]
        fig,ax=plt.subplots(figsize=(6.8,max(3.2,0.35*len(rows)+1.4)),dpi=180)
        bars=ax.barh(list(reversed(labels)),list(reversed(values)));_bar_labels(ax,bars,list(reversed(values)))
        ax.set_xlim(0,max(100,max(values)*1.18 if values else 100));ax.set_xlabel("AI 提名率（%）");ax.set_title(title)
        p=out/filename;_save(fig,plt,p);files.append(p.name)

    inst=[r for r in metrics if r.get("measurement_target")=="institution"]
    visibility([r for r in inst if r.get("market_role")=="national-benchmark"],"ai-visibility-national.png","全国品牌 AI 提名率")
    visibility([r for r in inst if r.get("market_role") in {"local-core","local-active"} and r.get("market_scope") in {"local","regional"}],"ai-visibility-local.png","本地 / 区域机构 AI 提名率")
    teacher=[r for r in metrics if r.get("measurement_target")=="ip" and r.get("market_role")=="expert-ip"]
    visibility(teacher,"ai-visibility-ip.png","老师 / 个人品牌 AI 提名率")

    # 5) GEO 资产基础：明确只展示前 15 名，避免标题暗示覆盖全部可评分主体。
    scored=[]
    for r in assets:
        score=fnum(r.get("asset_readiness"))
        if score is not None:scored.append((r,score))
    scored=sorted(scored,key=lambda x:x[1],reverse=True)[:15]
    if scored:
        labels=[r.get("canonical_name") or r.get("institution") or r.get("entity_id") for r,_ in scored]
        values=[s for _,s in scored];extras=[f" / {r.get('asset_tier')}" if r.get("asset_tier") else "" for r,_ in scored]
        fig,ax=plt.subplots(figsize=(6.8,max(3.2,0.35*len(scored)+1.5)),dpi=180)
        bars=ax.barh(list(reversed(labels)),list(reversed(values)));_bar_labels(ax,bars,list(reversed(values)),suffix="",extras=list(reversed(extras)))
        ax.set_xlim(0,112);ax.set_xlabel("GEO 资产基础得分（100分制）");ax.set_title("GEO 资产基础排名（前 15 名）")
        p=out/"asset-readiness.png";_save(fig,plt,p);files.append(p.name)

    # 6) 概念占位：Top 10 直接列出主体和概念，避免稀疏热力图。
    ranked=[]
    for r in concepts:
        strength=fnum(r.get("strength") or r.get("score"));entity=r.get("canonical_name") or r.get("entity_name") or "";concept=r.get("concept") or ""
        if strength is not None and entity and concept:ranked.append((r,strength,entity,concept))
    ranked=sorted(ranked,key=lambda x:x[1],reverse=True)[:10]
    if ranked:
        labels=[f"{e}｜{c}" for _,_,e,c in ranked];values=[s for _,s,_,_ in ranked]
        fig,ax=plt.subplots(figsize=(6.8,max(3.4,0.42*len(ranked)+1.4)),dpi=180)
        bars=ax.barh(list(reversed(labels)),list(reversed(values)));_bar_labels(ax,bars,list(reversed(values)),suffix="")
        ax.set_xlim(0,max(10.8,max(values)*1.15 if values else 10.8));ax.set_xlabel("概念绑定强度（10分制）");ax.set_title("概念占位前 10 名")
        p=out/"concept-ownership.png";_save(fig,plt,p);files.append(p.name)

    payload={
        "files":files,"cjk_font_available":True,"cjk_font":cjk_font,"customer_chart_language":"zh-CN",
        "generated_from":{"ai_metrics":len(metrics),"asset_scores":len(assets),"concept_rows":len(concepts),"opportunity_entities":len(opportunity)},
        "opportunity_rule":{"asset_median":asset_median,"target_nomination_medians":target_medians,"note":"机构推荐类与老师推荐类分别使用各自提名率中位数，不跨题型比较分母。"},
    }
    (out/"chart_manifest.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");return payload


def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);a=p.parse_args()
    try:print(json.dumps(generate(a.run_dir),ensure_ascii=False));return 0
    except (OSError,RuntimeError,ValueError) as e:print(f"generate_charts：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
