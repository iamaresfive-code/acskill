#!/usr/bin/env python3
"""v2.1 PDF Renderer：使用 ReportLab 直接生成正式 A4 PDF。"""
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
try:
    from svglib.svglib import svg2rlg
except Exception:svg2rlg=None
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

def read_csv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def chart(path:Path,maxw=170*mm):
    if svg2rlg and path.is_file():
        d=svg2rlg(str(path))
        if d and d.width:
            scale=min(1,maxw/d.width);d.width*=scale;d.height*=scale;d.scale(scale,scale);return d
    return Paragraph(f"图表资产：{path.name}",ParagraphStyle('fallback',fontName='STSong-Light',fontSize=9))
def render(run:Path,out:Path):
    model=json.loads((run/'report_model.json').read_text(encoding='utf-8'));meta=model.get('meta',{});ev=read_csv(run/'evidence.csv');out.parent.mkdir(parents=True,exist_ok=True);doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=19*mm,leftMargin=19*mm,topMargin=18*mm,bottomMargin=18*mm);styles=getSampleStyleSheet();body=ParagraphStyle('cn',parent=styles['BodyText'],fontName='STSong-Light',fontSize=10.5,leading=16,spaceAfter=6);h1=ParagraphStyle('h1cn',parent=styles['Heading1'],fontName='STSong-Light',fontSize=21,leading=27,textColor=colors.HexColor('#18324f'),spaceAfter=10);h2=ParagraphStyle('h2cn',parent=styles['Heading2'],fontName='STSong-Light',fontSize=15,leading=20,textColor=colors.HexColor('#18324f'),spaceAfter=8);cover=ParagraphStyle('cover',parent=h1,fontSize=28,leading=34,alignment=TA_CENTER,spaceAfter=14);center=ParagraphStyle('center',parent=body,alignment=TA_CENTER)
    story=[Spacer(1,55*mm),Paragraph('INTERNAL RESEARCH',center),Paragraph(model.get('title',''),cover),Paragraph(model.get('subtitle',''),center),Spacer(1,8*mm),Paragraph(f"研究范围：{meta.get('normalized_region') or meta.get('requested_region','')}<br/>观察日期：{meta.get('observation_date','')}<br/>研究性质：公开互联网 GEO 竞争情报",center),PageBreak()]
    k=model.get('kpis',{});story += [Paragraph('研究概览 / KPI Cards',h1),Table([[str(k.get('independent_institutions',0)),str(k.get('scored_institutions',0)),str(k.get('institution_measurement_queries',0)),str(k.get('evidence_count',0))],['独立机构候选','正式评分机构','无品牌问题实测','可复核 Evidence']],colWidths=[42*mm]*4,style=TableStyle([('FONTNAME',(0,0),(-1,-1),'STSong-Light'),('ALIGN',(0,0),(-1,-1),'CENTER'),('BACKGROUND',(0,1),(-1,1),colors.HexColor('#eaf0f6')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#ccd5df')),('FONTSIZE',(0,0),(-1,-1),9)])),Spacer(1,7*mm),Paragraph('Executive Summary',h1)]
    for x in model.get('executive_summary',[]):story.append(Paragraph('• '+str(x),body))
    for title,key in [('GEO 综合排名与市场格局','ranking'),('Authority × Recall 竞争矩阵','authority_recall'),('Candidate Coverage / 调研完整性','funnel'),('五维能力结构','heatmap')]:story += [PageBreak(),Paragraph(title,h1),chart(run/model['charts'][key])]
    story += [PageBreak(),Paragraph('商业解释型 Scorecard',h1)];data=[['排名','主体','GEO指数','Tier','竞争路线','最强资产','最大短板']]+[[str(i),r.get('institution',''),str(r.get('total','')),r.get('tier',''),r.get('route',''),r.get('strongest_asset',''),r.get('largest_gap','')] for i,r in enumerate(model.get('scorecards',[]),1)];story.append(Table(data,repeatRows=1,colWidths=[10*mm,28*mm,18*mm,13*mm,25*mm,34*mm,34*mm],style=TableStyle([('FONTNAME',(0,0),(-1,-1),'STSong-Light'),('FONTSIZE',(0,0),(-1,-1),8.5),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f6')),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#ccd5df')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEADING',(0,0),(-1,-1),10)])))
    story += [PageBreak(),Paragraph('重点机构诊断',h1)]
    if model.get('diagnoses'):
        for x in model.get('diagnoses',[]):story.append(Paragraph(str(x.get('institution') or x.get('name') or '机构诊断') if isinstance(x,dict) else '机构诊断',h2));story.append(Paragraph(str(x.get('summary') if isinstance(x,dict) else x),body))
    else:story.append(Paragraph('重点机构诊断由本次 Score、Recall、Authority 与 Evidence 归纳。',body))
    story += [Paragraph('IP / Expert GEO',h2),Paragraph('本次已执行 IP Measurement。' if model.get('kpis',{}).get('ip_measurement_queries',0) else '本次未执行 IP Measurement，仅作 IP 实体 / 专家可见性观察。',body),PageBreak(),Paragraph('固定 Query 占位观察',h1)]
    for x in model.get('query_occupancy',[]) or ['由 Institution Measurement Matrix 转译。']:story.append(Paragraph('• '+str(x),body))
    story.append(Paragraph('概念山头 / Gap Map',h2))
    for x in model.get('concept_gaps',[]) or ['由无结果、弱召回、实体歧义与概念关系不稳识别。']:story.append(Paragraph('• '+str(x),body))
    story += [Paragraph('竞争路线',h2),Paragraph('竞争路线由本次资产结构自动归纳，不参与评分。',body),PageBreak(),Paragraph('区域进入策略与 90 天 GEO 工程',h1)]
    for title,key,fallback in [('区域进入策略','entry_strategy','由本次 Gap 与竞争路线分析生成。'),('90 天 GEO 内容与知识资产工程','plan_90_days','需与本次实际 Gap 强关联。'),('月度 GEO 监测看板','monthly_dashboard','核心 KPI：无品牌召回率、首提率、引用率、正确实体率、可引用 Evidence 数、概念绑定稳定度、错误信息率。')]:
        story.append(Paragraph(title,h2))
        for x in model.get(key,[]) or [fallback]:story.append(Paragraph('• '+str(x),body))
    story += [PageBreak(),Paragraph('Appendix / Research Audit',h1),Paragraph('Schema版本：2.1<br/>Skill版本：2.1<br/>采样模式：'+str(meta.get('sampling_mode','public-web-proxy')),body),Paragraph('Evidence Index',h2)];ed=[['ID','主体','来源标题','Grade','发布日期','URL']]+[[r.get('evidence_id',''),r.get('institution',''),r.get('source_title',''),r.get('source_grade',''),r.get('published_date',''),r.get('source_url','')] for r in ev];story.append(Table(ed,repeatRows=1,colWidths=[14*mm,24*mm,38*mm,13*mm,22*mm,53*mm],style=TableStyle([('FONTNAME',(0,0),(-1,-1),'STSong-Light'),('FONTSIZE',(0,0),(-1,-1),8.5),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eaf0f6')),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#ccd5df')),('VALIGN',(0,0),(-1,-1),'TOP')])))
    doc.build(story);return out
def main():
    p=argparse.ArgumentParser();p.add_argument('run_dir',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();out=a.output or a.run_dir/'deliverables'/'report.pdf';print(render(a.run_dir,out));return 0
if __name__=='__main__':raise SystemExit(main())
