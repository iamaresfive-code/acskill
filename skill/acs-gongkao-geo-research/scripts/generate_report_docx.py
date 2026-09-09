#!/usr/bin/env python3
"""v2.1 DOCX Renderer：从统一 Report Model 生成正式 A4 Word 报告。"""
from __future__ import annotations
import argparse,csv,json,tempfile
from pathlib import Path
import cairosvg
from docx import Document
from docx.shared import Mm,Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT

def read_csv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def set_font(run,size=None,bold=None):
    run.font.name='Aptos';run._element.rPr.rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
    if size:run.font.size=Pt(size)
    if bold is not None:run.bold=bold
def add_title(doc,text,size=20):
    p=doc.add_paragraph();r=p.add_run(text);set_font(r,size,True);p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(8);return p
def add_page_break(doc):doc.add_page_break()
def add_header_footer(section,region,date):
    hp=section.header.paragraphs[0];hp.text=f"2026 {region}公考 GEO 竞争格局深度报告 | INTERNAL RESEARCH";hp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in hp.runs:set_font(r,8)
    fp=section.footer.paragraphs[0];fp.text=f"公开网络语料审计 · 观察日期 {date}";fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in fp.runs:set_font(r,8)
def add_table(doc,headers,rows):
    t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.style='Table Grid'
    for i,h in enumerate(headers):
        t.rows[0].cells[i].text=str(h)
        for p in t.rows[0].cells[i].paragraphs:
            for r in p.runs:set_font(r,9,True)
    for row in rows:
        cells=t.add_row().cells
        for i,v in enumerate(row):
            cells[i].text=str(v or '')
            for p in cells[i].paragraphs:
                for r in p.runs:set_font(r,9)
    return t
def add_chart(doc,path:Path):
    if path.is_file():
        try:
            with tempfile.NamedTemporaryFile(suffix='.png',delete=False) as tmp:tmp_path=Path(tmp.name)
            cairosvg.svg2png(url=str(path),write_to=str(tmp_path),output_width=1500);doc.add_picture(str(tmp_path),width=Mm(165));tmp_path.unlink(missing_ok=True);return
        except Exception:
            try:tmp_path.unlink(missing_ok=True)
            except Exception:pass
    p=doc.add_paragraph(f"[图表资产：{path.name}]")
    for r in p.runs:set_font(r,9)
def render(run:Path,out:Path):
    model=json.loads((run/'report_model.json').read_text(encoding='utf-8'));meta=model.get('meta',{});ev=read_csv(run/'evidence.csv');d=Document();sec=d.sections[0];sec.top_margin=Mm(18);sec.bottom_margin=Mm(18);sec.left_margin=Mm(19);sec.right_margin=Mm(19);region=meta.get('normalized_region') or meta.get('requested_region','');date=meta.get('observation_date','')
    for _ in range(5):d.add_paragraph('')
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run('INTERNAL RESEARCH');set_font(r,11,True)
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run(model.get('title',''));set_font(r,30,True)
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run(model.get('subtitle',''));set_font(r,14);d.add_paragraph('')
    for line in [f"研究范围：{region}",f"观察日期：{date}","研究性质：公开互联网 GEO 竞争情报","内部用途：竞争监测 / 区域进入 / 品牌 GEO / 内容资产规划"]:
        p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run(line);set_font(r,10)
    section=d.add_section(WD_SECTION.NEW_PAGE);section.top_margin=Mm(18);section.bottom_margin=Mm(18);section.left_margin=Mm(19);section.right_margin=Mm(19);section.header.is_linked_to_previous=False;section.footer.is_linked_to_previous=False;add_header_footer(section,region,date)
    add_title(d,'研究概览 / KPI Cards');k=model.get('kpis',{});add_table(d,['独立机构候选','正式评分机构','无品牌问题实测','可复核 Evidence'],[[k.get('independent_institutions',0),k.get('scored_institutions',0),k.get('institution_measurement_queries',0),k.get('evidence_count',0)]])
    add_title(d,'Executive Summary');
    for x in model.get('executive_summary',[]):p=d.add_paragraph(style='List Bullet');r=p.add_run(str(x));set_font(r,10.5)
    add_page_break(d);add_title(d,'GEO 综合排名与市场格局');add_chart(d,run/model['charts']['ranking'])
    add_page_break(d);add_title(d,'Authority × Recall 竞争矩阵');add_chart(d,run/model['charts']['authority_recall'])
    add_page_break(d);add_title(d,'Candidate Coverage / 调研完整性');add_chart(d,run/model['charts']['funnel']);add_title(d,'五维能力结构',16);add_chart(d,run/model['charts']['heatmap'])
    add_page_break(d);add_title(d,'商业解释型 Scorecard');rows=[[i,r.get('institution'),r.get('total'),r.get('tier'),r.get('route'),r.get('strongest_asset'),r.get('largest_gap')] for i,r in enumerate(model.get('scorecards',[]),1)];add_table(d,['排名','主体','GEO指数','Tier','竞争路线','最强资产','最大短板'],rows)
    add_page_break(d);add_title(d,'重点机构诊断')
    if model.get('diagnoses'):
        for x in model.get('diagnoses',[]):
            p=d.add_paragraph();r=p.add_run(str(x.get('institution') or x.get('name') or '机构诊断') if isinstance(x,dict) else '机构诊断');set_font(r,13,True);p=d.add_paragraph();r=p.add_run(str(x.get('summary') if isinstance(x,dict) else x));set_font(r,10.5)
    else:
        p=d.add_paragraph('重点机构诊断由本次 Score、Recall、Authority 与 Evidence 归纳。');[set_font(r,10.5) for r in p.runs]
    add_title(d,'IP / Expert GEO',15);p=d.add_paragraph('本次已执行 IP Measurement。' if model.get('kpis',{}).get('ip_measurement_queries',0) else '本次未执行 IP Measurement，仅作 IP 实体 / 专家可见性观察。');[set_font(r,10.5) for r in p.runs]
    add_page_break(d);add_title(d,'固定 Query 占位观察')
    for x in model.get('query_occupancy',[]) or ['由 Institution Measurement Matrix 转译。']:p=d.add_paragraph(style='List Bullet');r=p.add_run(str(x));set_font(r,10.5)
    add_title(d,'概念山头 / Gap Map',15)
    for x in model.get('concept_gaps',[]) or ['由无结果、弱召回、实体歧义与概念关系不稳识别。']:p=d.add_paragraph(style='List Bullet');r=p.add_run(str(x));set_font(r,10.5)
    add_title(d,'竞争路线',15);p=d.add_paragraph('竞争路线由本次资产结构自动归纳，不参与评分。');[set_font(r,10.5) for r in p.runs]
    add_page_break(d);add_title(d,'区域进入策略与 90 天 GEO 工程')
    for title,key,fallback in [('区域进入策略','entry_strategy','由本次 Gap 与竞争路线分析生成。'),('90 天 GEO 内容与知识资产工程','plan_90_days','需与本次实际 Gap 强关联。'),('月度 GEO 监测看板','monthly_dashboard','核心 KPI：无品牌召回率、首提率、引用率、正确实体率、可引用 Evidence 数、概念绑定稳定度、错误信息率。')]:
        add_title(d,title,15)
        for x in model.get(key,[]) or [fallback]:p=d.add_paragraph(style='List Bullet');r=p.add_run(str(x));set_font(r,10.5)
    add_page_break(d);add_title(d,'Appendix / Research Audit');p=d.add_paragraph(f"Schema版本：2.1\nSkill版本：2.1\n采样模式：{meta.get('sampling_mode','public-web-proxy')}");[set_font(r,9) for r in p.runs];add_title(d,'Evidence Index',14);add_table(d,['ID','主体','来源标题','Grade','发布日期','URL'],[[r.get('evidence_id'),r.get('institution'),r.get('source_title'),r.get('source_grade'),r.get('published_date'),r.get('source_url')] for r in ev]);out.parent.mkdir(parents=True,exist_ok=True);d.save(out);return out
def main():
    p=argparse.ArgumentParser();p.add_argument('run_dir',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();out=a.output or a.run_dir/'deliverables'/'report.docx';print(render(a.run_dir,out));return 0
if __name__=='__main__':raise SystemExit(main())
