#!/usr/bin/env python3
"""Single official renderer for GEO v2.2: stable A4 DOCX consulting report."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from fs_utils import ensure_directory


def _deps():
    try:
        from docx import Document
        from docx.shared import Mm,Pt
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        return Document,Mm,Pt,WD_ALIGN_PARAGRAPH,WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT,OxmlElement,qn
    except Exception as e:raise RuntimeError(f"需要 python-docx：{e}")

def render(run:Path,out:Path):
    Document,Mm,Pt,ALIGN,TALIGN,CVAL,OxmlElement,qn=_deps();model=json.loads((run/"report_model.json").read_text(encoding="utf-8"));meta=model.get("meta",{});d=Document();sec=d.sections[0]
    sec.page_width=Mm(210);sec.page_height=Mm(297);sec.top_margin=Mm(18);sec.bottom_margin=Mm(18);sec.left_margin=Mm(19);sec.right_margin=Mm(19)
    styles=d.styles
    for sname,size,bold in [("Normal",10.5,False),("Title",30,True),("Heading 1",20,True),("Heading 2",15,True),("Heading 3",12,True)]:
        s=styles[sname];s.font.name="Aptos";s.font.size=Pt(size);s.font.bold=bold;s._element.rPr.rFonts.set(qn("w:eastAsia"),"Microsoft YaHei")
    styles["Normal"].paragraph_format.line_spacing=1.45;styles["Normal"].paragraph_format.space_after=Pt(5)
    def set_run(r,size=None,bold=None):
        r.font.name="Aptos";r._element.rPr.rFonts.set(qn("w:eastAsia"),"Microsoft YaHei")
        if size:r.font.size=Pt(size)
        if bold is not None:r.bold=bold
    def page_break():d.add_page_break()
    def h(text,level=1):
        p=d.add_paragraph(style=f"Heading {level}");p.paragraph_format.keep_with_next=True;p.add_run(text);return p
    def bullet(text):
        p=d.add_paragraph(style="List Bullet");p.add_run(str(text));return p
    def set_repeat_header(row):
        trPr=row._tr.get_or_add_trPr();tblHeader=OxmlElement("w:tblHeader");tblHeader.set(qn("w:val"),"true");trPr.append(tblHeader)
    def no_split(row):
        trPr=row._tr.get_or_add_trPr();x=OxmlElement("w:cantSplit");trPr.append(x)
    def shade(cell,fill="EAF0F6"):
        tcPr=cell._tc.get_or_add_tcPr();shd=OxmlElement("w:shd");shd.set(qn("w:fill"),fill);tcPr.append(shd)
    def table(headers,rows,widths=None,font=8.5):
        t=d.add_table(rows=1,cols=len(headers));t.alignment=TALIGN.CENTER;t.style="Table Grid";set_repeat_header(t.rows[0])
        for i,x in enumerate(headers):
            c=t.rows[0].cells[i];c.text=str(x);shade(c);c.vertical_alignment=CVAL.CENTER
            for p in c.paragraphs:
                for r in p.runs:set_run(r,font,True)
        for row in rows:
            cells=t.add_row().cells;no_split(t.rows[-1])
            for i,v in enumerate(row):
                cells[i].text=str(v if v is not None else "");cells[i].vertical_alignment=CVAL.TOP
                for p in cells[i].paragraphs:
                    for r in p.runs:set_run(r,font)
        if widths:
            for row in t.rows:
                for i,w in enumerate(widths):row.cells[i].width=Mm(w)
        return t
    def chart(path):
        p=run/path
        if p.is_file():d.add_picture(str(p),width=Mm(165));d.paragraphs[-1].alignment=ALIGN.CENTER
    def pct(v):
        try:return f"{float(v)*100:.1f}%"
        except:return "—"
    def vis_rows(rows):return [[i+1,r.get("canonical_name"),pct(r.get("nomination_rate")),pct(r.get("top3_rate")),pct(r.get("first_mention_rate")),r.get("asset_readiness") or "—",r.get("market_scope") or "—"] for i,r in enumerate(rows)]
    for _ in range(5):d.add_paragraph("")
    p=d.add_paragraph();p.alignment=ALIGN.CENTER;r=p.add_run("INTERNAL RESEARCH");set_run(r,10,True)
    p=d.add_paragraph();p.alignment=ALIGN.CENTER;r=p.add_run(model.get("title",""));set_run(r,28,True)
    p=d.add_paragraph();p.alignment=ALIGN.CENTER;r=p.add_run(model.get("subtitle",""));set_run(r,13)
    for text in [f"研究范围：{meta.get('normalized_region') or meta.get('requested_region','')}",f"观察日期：{meta.get('observation_date','')}","正式交付：Word / DOCX","研究边界：GEO 不代表教学质量、市场份额或真实口碑"]:
        p=d.add_paragraph();p.alignment=ALIGN.CENTER;p.add_run(text)
    from docx.enum.section import WD_SECTION
    section=d.add_section(WD_SECTION.NEW_PAGE);section.page_width=Mm(210);section.page_height=Mm(297);section.top_margin=Mm(18);section.bottom_margin=Mm(18);section.left_margin=Mm(19);section.right_margin=Mm(19);section.header.is_linked_to_previous=False;section.footer.is_linked_to_previous=False
    hp=section.header.paragraphs[0];hp.text=model.get("title","");hp.alignment=ALIGN.CENTER
    fp=section.footer.paragraphs[0];fp.alignment=ALIGN.CENTER;fp.add_run("公开信息研究 · ");fld=OxmlElement("w:fldSimple");fld.set(qn("w:instr"),"PAGE");fp._p.append(fld)
    sec.header.paragraphs[0].clear();sec.footer.paragraphs[0].clear()
    h("研究概览",1);k=model.get("kpis",{});table(["正式研究主体","全国基准","本地/区域机构","Expert/IP","观察组","AI引擎"],[[k.get("included_entities"),k.get("national_benchmarks"),k.get("local_institutions"),k.get("expert_ip"),k.get("observation_entities"),k.get("ai_engines")]],widths=[28,28,30,26,26,26],font=9)
    h("Executive Summary",1)
    for x in model.get("executive_summary",[]):bullet(x)
    page_break();h("一、Market Universe / 本次到底研究谁",1);chart(model["charts"]["universe"]);table(["主体","类型","市场范围","市场角色","用户Seed","纳入依据"],[[r.get("canonical_name"),r.get("entity_type"),r.get("market_scope"),r.get("market_role"),r.get("user_seed"),r.get("salience_basis")] for group in model.get("market_universe",{}).values() for r in group],widths=[34,22,22,32,18,42],font=8)
    page_break();h("二、全国品牌在本地区的 AI GEO 表现",1);chart(model["charts"]["national_visibility"]);rows=model.get("ai_visibility",{}).get("national_benchmarks",[]);table(["排名","主体","提名率","Top3率","首提率","资产成熟度","范围"],vis_rows(rows),widths=[12,38,24,24,24,30,18],font=8.5)
    page_break();h("三、本土 / 区域机构 AI GEO",1);chart(model["charts"]["local_visibility"]);rows=model.get("ai_visibility",{}).get("local_institutions",[]);table(["排名","主体","提名率","Top3率","首提率","资产成熟度","范围"],vis_rows(rows),widths=[12,38,24,24,24,30,18],font=8.5)
    page_break();h("四、Expert / IP GEO",1);chart(model["charts"]["ip_visibility"]);rows=model.get("ai_visibility",{}).get("expert_ip",[]);table(["排名","IP/老师","提名率","Top3率","首提率","资产成熟度","范围"],vis_rows(rows),widths=[12,38,24,24,24,30,18],font=8.5)
    page_break();h("五、概念山头 / Concept Ownership",1);chart(model["charts"]["concept_ownership"]);concepts=model.get("concept_map",[])
    if concepts:table(["概念","主体","强度","证据/说明"],[[x.get("concept"),x.get("canonical_name") or x.get("entity_name"),x.get("strength") or x.get("score"),x.get("notes") or x.get("evidence_ids")] for x in concepts],widths=[38,38,18,66],font=8)
    page_break();h("六、GEO Asset Readiness / 为什么 AI 可能认识它",1);chart(model["charts"]["asset_readiness"]);assets=model.get("asset_readiness",[]);table(["主体","资产成熟度","Tier","自有来源依赖","证据数","独立域名"],[[x.get("canonical_name") or x.get("institution") or x.get("entity_id"),x.get("asset_readiness"),x.get("asset_tier"),pct(x.get("owned_source_dependency")),x.get("evidence_count"),x.get("independent_domains")] for x in assets],widths=[50,28,18,30,20,22],font=8.5)
    page_break();h("七、重点主体诊断",1)
    if model.get("diagnoses"):
        for x in model["diagnoses"]:
            h(str(x.get("name") or x.get("entity") or "主体诊断"),2);table(["项目","判断"],[["市场角色",x.get("market_role","")],["AI表现",x.get("ai_visibility","")],["最强资产",x.get("strongest_asset","")],["主要短板",x.get("largest_gap","")],["关键动作",x.get("recommendation","")]],widths=[30,130],font=9)
    else:d.add_paragraph("本章节应由 Agent 基于 Market Universe、AI Measurement、Asset Audit 与 Evidence 形成，不允许用模板占位替代实际诊断。")
    h("八、区域策略与 90 天 GEO 工程",1)
    for x in model.get("strategy",[]) or ["策略结论必须来自本次真实 AI 提名差异、概念空位和资产短板。"]:bullet(x)
    h("90 天工程",2)
    for x in model.get("plan_90_days",[]) or ["0–30天：实体与关键概念页；31–60天：专家/IP与结构化知识资产；61–90天：第三方证据与多模型复测。"]:bullet(x)
    page_break();h("Appendix / Research Audit",1);app=model.get("appendix",{});r=app.get("recheck",{});table(["复判记录","分歧","已解决分歧","Evidence"],[[r.get("rows",0),r.get("disagreements",0),r.get("resolved_disagreements",0),k.get("evidence_count",0)]],widths=[40,40,40,40],font=9)
    h("研究方法边界",2)
    for x in app.get("methodology_notes",[]):bullet(x)
    emergent=model.get("ai_visible_observation",[])
    if emergent:
        h("Observation 中被 AI 实际提名的主体",2)
        table(["主体","提名率","Top3率","市场范围","Stage 1 状态"],[[x.get("canonical_name"),pct(x.get("nomination_rate")),pct(x.get("top3_rate")),x.get("market_scope"),x.get("universe_status")] for x in emergent],widths=[52,28,28,28,30],font=8.5)
        d.add_paragraph("这些主体未进入 Stage 1 主榜，但真实 AI Answer 已出现提名，应在最终解释中单独复核是否需要升级为正式竞争主体。")
    h("观察组 / 未进入正式比较的主体",2);obs=model.get("observation_group",[])
    if obs:table(["主体","状态","市场范围","AI提名率","原因/备注"],[[x.get("canonical_name"),x.get("universe_status"),x.get("market_scope"),pct(x.get("nomination_rate")),x.get("notes") or x.get("salience_basis")] for x in obs],widths=[38,24,24,24,58],font=8)
    h("研究资产清单",2)
    for x in app.get("research_assets",[]):bullet(x)
    ensure_directory(out.parent);d.save(out);return out

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",type=Path);p.add_argument("--output",type=Path);a=p.parse_args();out=a.output or a.run_dir/"deliverables"/"report.docx"
    try:print(render(a.run_dir,out));return 0
    except (OSError,RuntimeError,ValueError) as e:print(f"generate_report_docx：错误：{e}");return 2
if __name__=="__main__":raise SystemExit(main())
