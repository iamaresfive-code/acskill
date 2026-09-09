#!/usr/bin/env python3
"""GEO v2.1.1 PDF Renderer: direct A4 PDF from the shared Report Model."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
from fs_utils import ensure_directory
try:
    from svglib.svglib import svg2rlg
except Exception:svg2rlg=None
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

def read_csv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def pct(v):return f"{float(v or 0)*100:.0f}%"
def chart(path:Path,maxw=170*mm):
    if svg2rlg and path.is_file():
        d=svg2rlg(str(path))
        if d and d.width:
            scale=min(1,maxw/d.width);d.width*=scale;d.height*=scale;d.scale(scale,scale);return d
    return Paragraph(f"图表资产：{path.name}",ParagraphStyle('fallback',fontName='STSong-Light',fontSize=9))
def mk_table(data,widths=None,size=8.2):
    return Table(data,repeatRows=1,colWidths=widths,style=TableStyle([('FONTNAME',(0,0),(-1,-1),'STSong-Light'),('FONTSIZE',(0,0),(-1,-1),size),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f6')),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#ccd5df')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEADING',(0,0),(-1,-1),10)]))
def render(run:Path,out:Path):
    model=json.loads((run/'report_model.json').read_text(encoding='utf-8'));meta=model.get('meta',{});ev=read_csv(run/'evidence.csv');ensure_directory(out.parent);doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=19*mm,leftMargin=19*mm,topMargin=18*mm,bottomMargin=18*mm);styles=getSampleStyleSheet();body=ParagraphStyle('cn',parent=styles['BodyText'],fontName='STSong-Light',fontSize=10.2,leading=15.5,spaceAfter=5);h1=ParagraphStyle('h1cn',parent=styles['Heading1'],fontName='STSong-Light',fontSize=20,leading=26,textColor=colors.HexColor('#18324f'),spaceAfter=9);h2=ParagraphStyle('h2cn',parent=styles['Heading2'],fontName='STSong-Light',fontSize=14.5,leading=19,textColor=colors.HexColor('#18324f'),spaceAfter=7);cover=ParagraphStyle('cover',parent=h1,fontSize=27,leading=33,alignment=TA_CENTER,spaceAfter=14);center=ParagraphStyle('center',parent=body,alignment=TA_CENTER)
    story=[Spacer(1,55*mm),Paragraph('INTERNAL RESEARCH',center),Paragraph(model.get('title',''),cover),Paragraph(model.get('subtitle',''),center),Spacer(1,8*mm),Paragraph(f"研究范围：{meta.get('normalized_region') or meta.get('requested_region','')}<br/>观察日期：{meta.get('observation_date','')}<br/>研究性质：公开互联网 GEO 竞争情报<br/>采样模式：{meta.get('sampling_mode','public-web-proxy')}",center),PageBreak()]
    k=model.get('kpis',{});story += [Paragraph('研究概览 / KPI Cards',h1),mk_table([['独立机构候选','正式评分机构','机构问题','IP问题','Evidence'],[str(k.get('independent_institutions',0)),str(k.get('scored_institutions',0)),str(k.get('institution_measurement_queries',0)),str(k.get('ip_measurement_queries',0)),str(k.get('evidence_count',0))]],[34*mm]*5,9),Spacer(1,6*mm),Paragraph('Executive Summary',h1)]
    for x in model.get('executive_summary',[]):story.append(Paragraph('• '+str(x),body))
    for title,key in [('GEO 综合排名与市场格局','ranking'),('Authority × Recall 竞争矩阵','authority_recall'),('Candidate Coverage / 调研完整性','funnel'),('五维能力结构','heatmap')]:story += [PageBreak(),Paragraph(title,h1),chart(run/model['charts'][key])]
    story += [PageBreak(),Paragraph('商业解释型 Scorecard',h1)];data=[['排名','主体','GEO','Tier','Recall','Authority']]+[[str(r.get('rank')),r.get('institution',''),str(r.get('total','')),r.get('tier',''),pct(r.get('recall_rate')),str(r.get('authority_index',''))] for r in model.get('ranking',[])];story.append(mk_table(data,[12*mm,53*mm,20*mm,16*mm,28*mm,28*mm],8.5));story.append(Spacer(1,5*mm));story.append(Paragraph('机构诊断卡',h2))
    for r in model.get('scorecards',[]):story += [Paragraph(str(r.get('institution')),h2),Paragraph(f"竞争路线：{r.get('route')}<br/>最强资产：{r.get('strongest_asset')}<br/>最大短板：{r.get('largest_gap')}<br/>自有来源依赖：{pct(r.get('owned_source_dependency_ratio'))}",body)]
    story += [PageBreak(),Paragraph('本土候选观察组',h1)];obs=model.get('observation_group',[]);story.append(mk_table([['主体','类型','状态','缺失项','原因']]+[[x.get('name',''),x.get('candidate_type',''),x.get('status',''),'、'.join(x.get('missing') or []) or '—',x.get('reason','')] for x in obs],[34*mm,22*mm,28*mm,40*mm,46*mm],7.8) if obs else Paragraph('本次无证据不足或未解析主体。',body))
    ip=model.get('ip_measurement',{});story += [Spacer(1,5*mm),Paragraph('IP / Expert GEO',h1),Paragraph(ip.get('note',''),body)]
    if ip.get('executed'):
        story.append(mk_table([['排名','IP/老师','关联机构','召回','Recall','标签/科目','平台']]+[[str(x.get('rank')),x.get('teacher_name',''),x.get('institution') or '—',f"{x.get('ip_hits')}/{x.get('ip_queries')}",pct(x.get('ip_recall')),x.get('subjects') or x.get('concepts') or '—',x.get('platforms') or '—'] for x in ip.get('rows',[])],[10*mm,30*mm,30*mm,18*mm,18*mm,34*mm,30*mm],7.8))
    story += [PageBreak(),Paragraph('固定 Query 占位观察',h1)];story.append(mk_table([['Query','问题','主题','命中主体数']]+[[x.get('query_id',''),x.get('query_text',''),x.get('theme',''),str(x.get('matched_entities',''))] for x in model.get('query_occupancy',[])],[18*mm,90*mm,36*mm,28*mm],8.2));story.append(Paragraph('概念山头 / Gap Map',h2))
    for x in model.get('concept_gaps',[]) or ['本次未形成足够稳定的自动 Gap 结论，不强行填充。']:story.append(Paragraph('• '+str(x),body))
    story += [PageBreak(),Paragraph('区域进入策略与 90 天 GEO 工程',h1)]
    for title,key,fallback in [('区域进入策略','entry_strategy','由本次 Gap 与竞争路线分析生成。'),('90 天 GEO 内容与知识资产工程','plan_90_days','需与本次实际 Gap 强关联。'),('月度 GEO 监测看板','monthly_dashboard','核心 KPI：无品牌召回率、正确实体率、可引用 Evidence 数、概念绑定稳定度、错误信息率。')]:
        story.append(Paragraph(title,h2))
        for x in model.get(key,[]) or [fallback]:story.append(Paragraph('• '+str(x),body))
    app=model.get('appendix',{});audit=app.get('research_audit',{});story += [PageBreak(),Paragraph('Appendix / Research Audit',h1),Paragraph(f"Schema版本：{model.get('schema_version','2.1.1')}<br/>Skill版本：{meta.get('skill_version','2.1.1')}<br/>采样模式：{audit.get('sampling_mode')}<br/>Semantic Coverage Gate：{audit.get('semantic_coverage_gate')}<br/>Saturation Gate：{audit.get('saturation_gate')}<br/>Local Ecosystem Gate：{audit.get('local_ecosystem_gate')}<br/>Candidate Frozen：{audit.get('candidate_pool_frozen')}",body),Paragraph('Candidate Status',h2),mk_table([['状态','数量']]+[[k,str(v)] for k,v in sorted(app.get('candidate_status',{}).items())],[80*mm,40*mm],8.5),Paragraph('Research Assets',h2)]
    for x in app.get('research_assets',[]):story.append(Paragraph('• '+str(x),body))
    story += [Paragraph('Evidence Index',h2),mk_table([['ID','主体','来源标题','Grade','发布日期','URL']]+[[r.get('evidence_id',''),r.get('institution',''),r.get('source_title',''),r.get('source_grade',''),r.get('published_date',''),r.get('source_url','')] for r in ev],[13*mm,25*mm,39*mm,12*mm,21*mm,56*mm],7.3)]
    doc.build(story);return out
def main():
    p=argparse.ArgumentParser();p.add_argument('run_dir',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();out=a.output or a.run_dir/'deliverables'/'report.pdf';print(render(a.run_dir,out));return 0
if __name__=='__main__':raise SystemExit(main())
