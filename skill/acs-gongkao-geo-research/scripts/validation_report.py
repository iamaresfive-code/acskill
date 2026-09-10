#!/usr/bin/env python3
from __future__ import annotations
import zipfile
from pathlib import Path
from validation_common import *

def validate_report(run:Path,issues:list[Issue],universe:list[dict],metrics:list[dict],emergent:list[dict]):
    model=rjson(run/"report_model.json",issues,"report-model")
    for key in ("market_universe","ai_visibility","asset_readiness","concept_map","observation_group","ai_visible_emergent","appendix","kpis"):
        if key not in model:issues.append(Issue("error","report-contract",f"report_model 缺少 {key}"))
    if model.get("schema_version")!=VERSION:issues.append(Issue("error","report-version","report_model.schema_version 必须为 2.2"))
    for r in (model.get("market_universe",{}) or {}).get("local_institutions",[]):
        if r.get("market_scope") not in {"local","regional"}:issues.append(Issue("error","report-local-scope",f"报告本土机构 {r.get('canonical_name')} 缺 local/regional scope"))
    mm={r.get("entity_id"):r for r in metrics};report_ids=set()
    for group in (model.get("ai_visibility") or {}).values():
        if isinstance(group,list):report_ids.update(r.get("entity_id") for r in group)
    expected={r.get("entity_id") for r in universe if r.get("universe_status")=="included" and r.get("entity_id") in mm}
    if expected-report_ids:issues.append(Issue("error","metrics-dropped",f"Report Model 丢失 AI Metrics 主体：{', '.join(sorted(expected-report_ids))}"))
    resolved_emergent={r.get("entity_id") for r in emergent if r.get("resolution_status")=="resolved"};rendered_emergent={r.get("entity_id") for r in (model.get("ai_visible_emergent") or [])};visible_resolved={eid for eid in resolved_emergent if num((mm.get(eid) or {}).get("nomination_rate")) and num((mm.get(eid) or {}).get("nomination_rate"))>0}
    if visible_resolved-rendered_emergent:issues.append(Issue("error","emergent-dropped",f"Report Model 丢失 AI-emergent 主体：{', '.join(sorted(visible_resolved-rendered_emergent))}"))
    app=model.get("appendix") or {}
    for key in ("recheck","research_assets","methodology_notes"):
        if key not in app:issues.append(Issue("error","appendix-contract",f"report_model.appendix 缺少 {key}"))
    delivered=run/"deliverables";docx=delivered/"report.docx"
    if not docx.is_file():issues.append(Issue("error","missing-docx","缺少唯一正式交付物 deliverables/report.docx"))
    if delivered.is_dir():
        bad=[p.name for p in delivered.iterdir() if p.is_file() and p.name!="report.docx" and p.suffix.lower() in {".pdf",".html"}]
        if bad:issues.append(Issue("error","extra-formats","v2.2 不允许正式生成 PDF/HTML："+", ".join(bad)))
    if docx.is_file():
        try:
            with zipfile.ZipFile(docx) as z:xml=z.read("word/document.xml").decode("utf-8",errors="ignore")
            for phrase in ("待归纳","由 score_details","本次已执行 IP Measurement。"):
                if phrase in xml:issues.append(Issue("error","placeholder-text",f"Word 报告仍包含占位文案：{phrase}"))
        except Exception as e:issues.append(Issue("error","docx-invalid",f"report.docx 无法读取：{e}"))
