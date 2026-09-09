#!/usr/bin/env python3
"""GEO v2.1.1 DOCX Renderer: one Report Model, A4-friendly layout."""
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
from fs_utils import ensure_directory

def read_csv(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def set_font(run,size=None,bold=None):
    run.font.name='Aptos';run._element.rPr.rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
    if size:run.font.size=Pt(size)
    if bold is not None:run.bold=bold
def add_title(doc,text,size=20):
    p=doc.add_paragraph();r=p.add_run(text);set_font(r,size,True);p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(8);return p
def add_table(doc,headers,rows,font_size=8.5):
    t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.style='Table Grid'
    for i,h in enumerate(headers):
        t.rows[0].cells[i].text=str(h)
        for p in t.rows[0].cells[i].paragraphs:
            for r in p.runs:set_font(r,font_size,True)
    for row in rows:
        cells=t.add_row().cells
        for i,v in enumerate(row):
            cells[i].text=str(v or '')
            for p in cells[i].paragraphs:
                for r in p.runs:set_font(r,font_size)
    return t
def add_chart(doc,path:Path):
    if path.is_file():
        tmp_path=None
        try:
            with tempfile.NamedTemporaryFile(suffix='.png',delete=False) as tmp:tmp_path=Path(tmp.name)
            cairosvg.svg2png(url=str(path),write_to=str(tmp_path),output_width=1500);doc.add_picture(str(tmp_path),width=Mm(165));tmp_path.unlink(missing_ok=True);return
        except Exception:
            if tmp_path:tmp_path.unlink(missing_ok=True)
    p=doc.add_paragraph(f"[图表资产：{path.name}]");[set_font(r,9) for r in p.runs]
def bullet(doc,text,size=10.5):
    p=doc.add_paragraph(style='List Bullet');r=p.add_run(str(text));set_font(r,size);return p
def pct(v):return f"{float(v or 0)*100:.0f}%"
def add_header_footer(section,region,date):
    hp=section.header.paragraphs[0];hp.text=f"{region}公考 GEO 竞争格局深度报告 | INTERNAL RESEARCH";hp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in hp.runs:set_font(r,8)
    fp=section.footer.paragraphs[0];fp.text=f"公开网络语料审计 · 观察日期 {date}";fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in fp.runs:set_font(r,8)
def render(run:Path,out:Path):
    model=json.loads((run/'report_model.json').read_text(encoding='utf-8'));meta=model.get('meta',{});ev=read_csv(run/'evidence.csv');d=Document();sec=d.sections[0];sec.top_margin=Mm(18);sec.bottom_margin=Mm(18);sec.left_margin=Mm(19);sec.right_margin=Mm(19);region=meta.get('normalized_region') or meta.get('requested_region','');date=meta.get('observation_date','')
    for _ in range(5):d.add_paragraph('')
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run('INTERNAL RESEARCH');set_font(r,11,True)
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run(model.get('title',''));set_font(r,30,True)
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run(model.get('subtitle',''));set_font(r,14)
    for line in [f"研究范围：{region}",f"观察日期：{date}","研究性质：公开互联网 GEO 竞争情报",f"采样模式：{meta.get('sampling_mode','public-web-proxy')}"]:
        p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;r=p.add_run(line);set_font(r,10)
    section=d.add_section(WD_SECTION.NEW_PAGE);section.top_margin=Mm(18);section.bottom_margin=Mm(18);section.left_margin=Mm(19);section.right_margin=Mm(19);section.header.is_linked_to_previous=False;section.footer.is_linked_to_previous=False;add_header_footer(section,region,date)
    add_title(d,'研究概览 / KPI Cards');k=model.get('kpis',{});add_table(d,['独立机构候选','正式评分机构','机构问题','IP问题','Evidence'],[[k.get('independent_institutions',0),k.get('scored_institutions',0),k.get('institution_measurement_queries',0),k.get('ip_measurement_queries',0),k.get('evidence_count',0)]])
    add_title(d,'Executive Summary');[bullet(d,x) for x in model.get('executive_summary',[])]
    for title,key in [('GEO 综合排名与市场格局','ranking'),('Authority × Recall 竞争矩阵','authority_recall'),('Candidate Coverage / 调研完整性','funnel'),('五维能力结构','heatmap')]:d.add_page_break();add_title(d,title);add_chart(d,run/model['charts'][key])
    d.add_page_break();add_title(d,'商业解释型 Scorecard');add_table(d,['排名','主体','GEO','Tier','Recall','Authority'],[[r.get('rank'),r.get('institution'),r.get('total'),r.get('tier'),pct(r.get('recall_rate')),r.get('authority_index')] for r in model.get('ranking',[])])
    add_title(d,'机构诊断卡',15)
    for r in model.get('scorecards',[]):
        p=d.add_paragraph();rr=p.add_run(str(r.get('institution')));set_font(rr,13,True)
        for line in [f"竞争路线：{r.get('route')}",f"最强资产：{r.get('strongest_asset')}",f"最大短板：{r.get('largest_gap')}",f"自有来源依赖：{pct(r.get('owned_source_dependency_ratio'))}"]:
            p=d.add_paragraph();rr=p.add_run(line);set_font(rr,10)
    d.add_page_break();add_title(d,'本土候选观察组');obs=model.get('observation_group',[]);add_table(d,['主体','类型','状态','缺失项','原因'],[[x.get('name'),x.get('candidate_type'),x.get('status'),'、'.join(x.get('missing') or []) or '—',x.get('reason')] for x in obs]) if obs else d.add_paragraph('本次无证据不足或未解析主体。')
    add_title(d,'IP / Expert GEO',15);ip=model.get('ip_measurement',{});p=d.add_paragraph(ip.get('note',''));[set_font(r,10.5) for r in p.runs]
    if ip.get('executed'):add_table(d,['排名','IP/老师','关联机构','召回','Recall','标签/科目','平台'],[[x.get('rank'),x.get('teacher_name'),x.get('institution') or '—',f"{x.get('ip_hits')}/{x.get('ip_queries')}",pct(x.get('ip_recall')),x.get('subjects') or x.get('concepts') or '—',x.get('platforms') or '—'] for x in ip.get('rows',[])])
    d.add_page_break();add_title(d,'固定 Query 占位观察');add_table(d,['Query','问题','主题','命中主体数'],[[x.get('query_id'),x.get('query_text'),x.get('theme'),x.get('matched_entities')] for x in model.get('query_occupancy',[])])
    add_title(d,'概念山头 / Gap Map',15);[bullet(d,x) for x in model.get('concept_gaps',[]) or ['本次未形成足够稳定的自动 Gap 结论，不强行填充。']]
    d.add_page_break();add_title(d,'区域进入策略与 90 天 GEO 工程')
    for title,key,fallback in [('区域进入策略','entry_strategy','由本次 Gap 与竞争路线分析生成。'),('90 天 GEO 内容与知识资产工程','plan_90_days','需与本次实际 Gap 强关联。'),('月度 GEO 监测看板','monthly_dashboard','核心 KPI：无品牌召回率、正确实体率、可引用 Evidence 数、概念绑定稳定度、错误信息率。')]:
        add_title(d,title,15);[bullet(d,x) for x in model.get(key,[]) or [fallback]]
    d.add_page_break();add_title(d,'Appendix / Research Audit');app=model.get('appendix',{});audit=app.get('research_audit',{});p=d.add_paragraph(f"Schema版本：{model.get('schema_version','2.1.1')}\nSkill版本：{meta.get('skill_version','2.1.1')}\n采样模式：{audit.get('sampling_mode')}\nSemantic Coverage Gate：{audit.get('semantic_coverage_gate')}\nSaturation Gate：{audit.get('saturation_gate')}\nLocal Ecosystem Gate：{audit.get('local_ecosystem_gate')}\nCandidate Frozen：{audit.get('candidate_pool_frozen')}");[set_font(r,9) for r in p.runs]
    add_title(d,'Candidate Status',14);add_table(d,['状态','数量'],[[k,v] for k,v in sorted(app.get('candidate_status',{}).items())])
    add_title(d,'Research Assets',14);[bullet(d,x,9) for x in app.get('research_assets',[])]
    add_title(d,'Evidence Index',14);add_table(d,['ID','主体','来源标题','Grade','发布日期','URL'],[[r.get('evidence_id'),r.get('institution'),r.get('source_title'),r.get('source_grade'),r.get('published_date'),r.get('source_url')] for r in ev],8)
    ensure_directory(out.parent);d.save(out);return out
def main():
    p=argparse.ArgumentParser();p.add_argument('run_dir',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();out=a.output or a.run_dir/'deliverables'/'report.docx';print(render(a.run_dir,out));return 0
if __name__=='__main__':raise SystemExit(main())
