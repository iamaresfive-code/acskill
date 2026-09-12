#!/usr/bin/env python3
from __future__ import annotations
import json,zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from validation_common import *
from measurement_target_utils import effective_emergent_target

W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ASSET_DIM_MAX={"entity_clarity":25,"regional_semantic_density":20,"open_web_assets":15,"external_authority":15,"content_depth_freshness":10,"data_tool_assets":10,"platform_coverage":5}
CONCEPT_BINDING_BANDS={"owned-declaration":(8,10),"high-frequency-public-binding":(6,8),"third-party-description":(3,5),"single-incidental-mention":(1,2)}
ANALYSIS_LAYERS=("facts","metrics","proxies","inferences","recommendations")
REPORT_MODEL_REQUIRED=("market_universe","ai_visibility","asset_readiness","concept_map","observation_group","ai_visible_emergent","appendix","kpis","measurement_protocol","robustness","risks")
ASSET_INPUT_REQUIRED=("entity_id","canonical_name","evidence_refs","evidence_date","confidence","unknown_fields")
RESEARCH_MANIFEST_REQUIRED=("evidence_id","entity_id","field","source_url","source_grade","source_owner","access_status","observed_at")
CONCEPT_REQUIRED=("concept","entity_id","canonical_name","strength","binding_type","basis","source_url","source_type","observed_at")
# DOCX 必须真实出现的核心章节（与 generate_report_docx.py 的一级标题一致）
REQUIRED_DOCX_SECTIONS=(
    "研究概览",
    "Executive Summary",
    "一、研究范围与测量协议",
    "二、Market Universe / 本次到底研究谁",
    "三、全国品牌在本地区的 AI GEO 表现",
    "四、本土 / 区域机构 AI GEO",
    "五、Expert / IP GEO",
    "六、Query / Retrieval Robustness（查询/检索鲁棒性）",
    "七、概念山头 / Concept Ownership",
    "八、GEO Asset Readiness / 为什么 AI 可能认识它",
    "九、AI 可见的观察组与 AI-emergent 竞争主体",
    "十、重点主体诊断",
    "十一、区域策略与 90 天 GEO 工程",
    "十二、风险与局限",
    "Appendix / Research Audit",
)


def required_report_entity_ids(universe,emergent):
    """正式 Report Entity Identity 集合：included Universe + resolved AI-emergent（去重，both 只算一个主体）。"""
    ids={r.get("entity_id") for r in universe if r.get("universe_status")=="included"}
    ids|={r.get("entity_id") for r in emergent if r.get("resolution_status")=="resolved"}
    return {i for i in ids if i}


def registry_entity_ids(universe,emergent):
    ids={r.get("entity_id") for r in universe}
    ids|={r.get("entity_id") for r in emergent}
    return {i for i in ids if i}


def docx_sections(docx:Path):
    """解析 DOCX 一级标题及其后的实际内容量（正文段落 / 表格 / 图片），不依赖 python-docx。"""
    with zipfile.ZipFile(docx) as z:
        if "word/document.xml" not in z.namelist():raise ValueError("缺少 word/document.xml")
        root=ET.fromstring(z.read("word/document.xml"))
    body=root.find(W+"body")
    out=[];cur=None
    if body is None:return out
    for el in list(body):
        if el.tag==W+"p":
            pstyle=el.find(W+"pPr/"+W+"pStyle")
            val=(pstyle.get(W+"val") or "") if pstyle is not None else ""
            text="".join(t.text or "" for t in el.iter(W+"t")).strip()
            has_img=el.find(".//"+W+"drawing") is not None
            if val=="Heading1" and text:
                cur={"heading":text,"content":0};out.append(cur);continue
            if cur is not None and (text or has_img):cur["content"]+=1
        elif el.tag==W+"tbl":
            if cur is not None and len(el.findall(W+"tr"))>=2:cur["content"]+=1
    return out


def _check_asset_layer(run,issues,model,universe,emergent):
    required_ids=required_report_entity_ids(universe,emergent);registry=registry_entity_ids(universe,emergent)
    inputs,inf=rcsv(run/"asset_inputs.csv",issues,"asset-inputs",ASSET_INPUT_REQUIRED)
    manifest,mf=rcsv(run/"report_research_manifest.csv",issues,"report-research-manifest",RESEARCH_MANIFEST_REQUIRED)
    rows,rf=rcsv(run/"asset_scores.csv",issues,"asset-scores")
    ids=[(r.get("entity_id") or "").strip() for r in rows]
    valid=[r for r in rows if num(r.get("asset_readiness")) is not None]
    if not rows:issues.append(Issue("error","empty-asset-readiness","asset_scores.csv 没有有效正式主体数据；空表 / 只有表头不得通过 report gate"))
    elif not valid:issues.append(Issue("error","empty-asset-readiness","asset_scores.csv 存在行但没有任何有效 asset_readiness 数值"))
    dup=sorted(k for k,v in Counter(i for i in ids if i).items() if v>1)
    if dup:issues.append(Issue("error","asset-readiness-duplicate-entity","asset_scores.csv 同一主体出现多行（Measurement Target 与 Report Entity Identity 是不同维度，both 不得拆成两个资产主体）："+", ".join(dup)))
    missing=sorted(required_ids-set(ids))
    if missing:issues.append(Issue("error","asset-readiness-coverage",f"asset_scores.csv 未覆盖全部正式主体（{len(missing)} 个缺失）："+", ".join(missing)))
    unknown=sorted(set(i for i in ids if i)-registry)
    if unknown:issues.append(Issue("error","asset-readiness-unknown-entity","asset_scores.csv 含不在正式 entity registry 中的主体："+", ".join(unknown)))
    if not model.get("asset_readiness"):issues.append(Issue("error","empty-asset-readiness","report_model.asset_readiness 为空，DOCX Asset Readiness 章节将为空"))
    # 证据可复算性：每个数值维度必须能追到公开证据；无证据维度必须显式声明 unknown
    evids={r.get("evidence_id") for r in manifest}
    for r in inputs:
        eid=r.get("entity_id") or ""
        declared={x.strip() for x in (r.get("unknown_fields") or "").replace(";","|").split("|") if x.strip()}
        bad_decl=declared-set(ASSET_DIM_MAX)
        if bad_decl:issues.append(Issue("error","asset-readiness-unknown-mismatch",f"{eid} unknown_fields 含未定义维度：{', '.join(sorted(bad_decl))}"))
        refs=[x.strip() for x in (r.get("evidence_refs") or "").split("|") if x.strip()]
        unresolved=[x for x in refs if x not in evids]
        if refs and unresolved:issues.append(Issue("error","asset-readiness-untraceable",f"{eid} evidence_refs 指向 report_research_manifest 中不存在的证据：{', '.join(unresolved)}"))
        for dim in ASSET_DIM_MAX:
            raw=(r.get(dim) or "").strip()
            known=raw.lower() not in {"","unknown","not-observed","insufficient-evidence"} and num(raw) is not None
            if known and not refs:issues.append(Issue("error","asset-readiness-no-evidence",f"{eid}.{dim} 有分数但没有任何公开证据引用，评分无法从原始公开证据复算"))
            if known and dim in declared:issues.append(Issue("error","asset-readiness-unknown-mismatch",f"{eid}.{dim} 已给出分数却同时被列为 unknown_fields"))
            if not known and dim not in declared:issues.append(Issue("error","asset-readiness-unknown-mismatch",f"{eid}.{dim} 缺证据时必须显式写入 unknown_fields，不得静默置空/置 0"))
    for r in manifest:
        if not (r.get("source_url") or "").strip() and (r.get("access_status") or "")=="found":
            issues.append(Issue("error","report-research-evidence-invalid",f"{r.get('evidence_id')} access_status=found 但没有 source_url"))


def _check_concept_layer(run,issues,model,universe,emergent):
    registry=registry_entity_ids(universe,emergent)
    rows,fields=rcsv(run/"concept_ownership.csv",issues,"concept-ownership",CONCEPT_REQUIRED)
    valid=[r for r in rows if (r.get("concept") or "").strip() and (r.get("entity_id") or "").strip()]
    if not rows or not valid:
        issues.append(Issue("error","empty-concept-ownership","concept_ownership.csv 不存在、没有有效 Concept 数据、或存在行但没有有效数据"))
    seen=set()
    for r in rows:
        tag=f"{r.get('entity_id')}×{r.get('concept')}"
        miss=sorted(k for k in CONCEPT_REQUIRED if not (r.get(k) or "").strip())
        if miss:issues.append(Issue("error","concept-ownership-untraceable",f"{tag} 缺少可核验字段：{', '.join(miss)}"))
        if (r.get("entity_id") or "") not in registry:issues.append(Issue("error","concept-ownership-unknown-entity",f"{tag} 引用了不在正式 entity registry 中的主体"))
        if tag in seen:issues.append(Issue("error","concept-ownership-duplicate",f"{tag} 重复登记"))
        seen.add(tag)
        bt=(r.get("binding_type") or "").strip();st=num(r.get("strength"))
        if bt in CONCEPT_BINDING_BANDS and st is not None:
            lo,hi=CONCEPT_BINDING_BANDS[bt]
            if not lo<=st<=hi:issues.append(Issue("error","concept-strength-overstated",f"{tag} binding_type={bt} 时 strength 必须落在 {lo}-{hi}，实际 {r.get('strength')}"))
        elif bt not in CONCEPT_BINDING_BANDS:issues.append(Issue("error","concept-ownership-untraceable",f"{tag} binding_type 无效/缺失：{bt or '(空)'}"))
    if not model.get("concept_map"):issues.append(Issue("error","empty-concept-ownership","report_model.concept_map 为空，DOCX Concept Ownership 章节将为空"))


def _check_analysis_layer(run,issues,model):
    analysis=rjson(run/"analysis.json",issues,"analysis")
    if not analysis:
        issues.append(Issue("error","empty-analysis","analysis.json 不存在或为空，正式分析章节无法成立"));return
    if not (analysis.get("executive_summary") or []):issues.append(Issue("error","empty-analysis","analysis.executive_summary 为空"))
    for key in ANALYSIS_LAYERS:
        entries=analysis.get(key) or []
        if not entries:issues.append(Issue("error","empty-analysis",f"analysis.{key} 为空：事实/指标/代理指标/推断/建议五层不得缺层"))
        for e in entries:
            if not isinstance(e,dict) or not (e.get("statement") or "").strip() or not (e.get("basis") or "").strip():
                issues.append(Issue("error","empty-analysis",f"analysis.{key} 存在缺少 statement/basis 的条目，无法区分事实与推断"));break
            if key=="metrics" and not (e.get("metric") or "").strip():
                issues.append(Issue("error","empty-analysis","analysis.metrics 条目必须声明 metric 名称，禁止把 GEO 可见度写成市场份额/市场排名"));break
    if not (analysis.get("limitations") or []):issues.append(Issue("error","empty-analysis","analysis.limitations 为空，风险与局限章节将无内容"))


def _check_report_sections(issues,model,run):
    for key,label in (("diagnoses","重点主体诊断"),("strategy","区域策略"),("plan_90_days","90 天工程"),("risks","风险与局限")):
        if not (model.get(key) or []):issues.append(Issue("error","empty-report-section",f"report_model.{key} 为空（{label}），不得以模板兜底文案代替真实内容"))
    for key,label in (("measurement_protocol","测量协议"),("robustness","Robustness")):
        if not (model.get(key) or {}):issues.append(Issue("error","empty-report-section",f"report_model.{key} 为空（{label}）"))
    for d in (model.get("diagnoses") or []):
        lack=[k for k in ("name","market_role","ai_visibility","strongest_asset","largest_gap","recommendation") if not str((d or {}).get(k) or "").strip()]
        if lack:issues.append(Issue("error","empty-report-section",f"诊断条目「{(d or {}).get('name') or '?'}」缺少内容：{', '.join(lack)}"))
    charts=model.get("charts") or {}
    if not charts:issues.append(Issue("error","empty-report-section","report_model.charts 为空，DOCX 将不嵌入任何图表"))
    for key,rel in charts.items():
        if not (run/rel).is_file():issues.append(Issue("error","missing-report-chart",f"report_model.charts.{key} 指向的图表不存在：{rel}"))


def _check_docx(run,issues):
    delivered=run/"deliverables";docx=delivered/"report.docx"
    if not docx.is_file():
        issues.append(Issue("error","missing-report-docx","缺少唯一正式交付物 deliverables/report.docx"));return
    try:
        sections=docx_sections(docx)
        with zipfile.ZipFile(docx) as z:xml=z.read("word/document.xml").decode("utf-8",errors="ignore")
    except Exception as e:
        issues.append(Issue("error","missing-report-docx",f"deliverables/report.docx 无法打开/不是有效 DOCX：{e}"));return
    found={s["heading"] for s in sections}
    for required in REQUIRED_DOCX_SECTIONS:
        if required not in found:
            issues.append(Issue("error","empty-report-section",f"report.docx 缺少核心章节：{required}"));continue
        sec=next(s for s in sections if s["heading"]==required)
        if sec["content"]==0:issues.append(Issue("error","empty-report-section",f"report.docx 章节「{required}」只有标题、正文为空"))
    for phrase in ("待归纳","由 score_details","本次已执行 IP Measurement。","应由 Agent 基于"):
        if phrase in xml:issues.append(Issue("error","placeholder-text",f"Word 报告仍包含占位文案：{phrase}"))


def validate_report(run:Path,issues:list[Issue],universe:list[dict],metrics:list[dict],emergent:list[dict]):
    model=rjson(run/"report_model.json",issues,"report-model")
    for key in REPORT_MODEL_REQUIRED:
        if key not in model:issues.append(Issue("error","report-contract",f"report_model 缺少 {key}"))
    if model.get("schema_version")!=VERSION:issues.append(Issue("error","report-version","report_model.schema_version 必须为 2.2"))
    expected_buckets={"national_benchmarks":{r.get("entity_id") for r in universe if r.get("universe_status")=="included" and r.get("market_role")=="national-benchmark"},"local_institutions":{r.get("entity_id") for r in universe if r.get("universe_status")=="included" and r.get("market_role") in {"local-core","local-active"} and r.get("market_scope") in {"local","regional"}},"expert_ip":{r.get("entity_id") for r in universe if r.get("universe_status")=="included" and r.get("market_role")=="expert-ip"}}
    for group,expected in expected_buckets.items():
        actual={r.get("entity_id") for r in (model.get("market_universe",{}) or {}).get(group,[])}
        if actual!=expected:issues.append(Issue("error","report-bucket-drift",f"report_model {group} 与 Stage 1 冻结 Market Bucket 不一致；missing={sorted(expected-actual)}, extra={sorted(actual-expected)}"))
    for r in (model.get("market_universe",{}) or {}).get("local_institutions",[]):
        if r.get("market_scope") not in {"local","regional"}:issues.append(Issue("error","report-local-scope",f"报告本土机构 {r.get('canonical_name')} 缺 local/regional scope"))
    metric_keys={(r.get("entity_id"),r.get("measurement_target")) for r in metrics};report_ids=set()
    for group in (model.get("ai_visibility") or {}).values():
        if isinstance(group,list):report_ids.update(r.get("entity_id") for r in group)
    expected_ids={r.get("entity_id") for r in universe if r.get("universe_status")=="included" and any(k[0]==r.get("entity_id") for k in metric_keys)}
    if expected_ids-report_ids:issues.append(Issue("error","metrics-dropped",f"Report Model 丢失 AI Metrics 主体：{', '.join(sorted(expected_ids-report_ids))}"))
    for group in (model.get("market_universe",{}) or {}).values():
        if not isinstance(group,list):continue
        for r in group:
            declared=r.get("measurement_target");tm=r.get("target_metrics") or {}
            if declared=="both" and set(tm)!={"institution","ip"}:issues.append(Issue("error","report-hybrid-target-loss",f"{r.get('canonical_name')} measurement_target=both 但报告未保留 institution/ip 两套 target_metrics"))
    resolved_emergent={r.get("entity_id") for r in emergent if r.get("resolution_status")=="resolved"};rendered_rows=(model.get("ai_emergent_entities") or []);rendered_by={r.get("entity_id"):r for r in rendered_rows};rendered_emergent={r.get("entity_id") for r in (model.get("ai_visible_emergent") or [])}
    visible_resolved={eid for eid in resolved_emergent if any(k[0]==eid and num((next((x for x in metrics if x.get('entity_id')==eid and x.get('measurement_target')==k[1]),{}) or {}).get("nomination_rate")) and num((next((x for x in metrics if x.get('entity_id')==eid and x.get('measurement_target')==k[1]),{}) or {}).get("nomination_rate"))>0 for k in metric_keys)}
    if visible_resolved-rendered_emergent:issues.append(Issue("error","emergent-dropped",f"Report Model 丢失 AI-emergent 主体：{', '.join(sorted(visible_resolved-rendered_emergent))}"))
    for e in emergent:
        if e.get("resolution_status")!="resolved" or effective_emergent_target(e)!="both":continue
        rr=rendered_by.get(e.get("entity_id")) or {};tm=rr.get("target_metrics") or {}
        if set(tm)!={"institution","ip"}:issues.append(Issue("error","report-emergent-hybrid-target-loss",f"{e.get('canonical_name')} measurement_target=both 但报告未保留 institution/ip 两套 target_metrics"))

    # Final-data consistency: report counts must be derived from the final persisted annotation and
    # metrics files, never copied from a pre-QA intermediate report.
    mentions,_=rcsv(run/"ai_mentions.csv",issues,"ai-mentions-report-consistency")
    final_intents=dict(sorted(Counter((m.get("mention_intent") or "").strip() for m in mentions if (m.get("mention_intent") or "").strip()).items()))
    model_qa=model.get("measurement_qa") or {};app=model.get("appendix") or {}
    if model_qa.get("annotation_intent_distribution")!=final_intents:issues.append(Issue("error","report-intent-count-drift","report_model.measurement_qa.annotation_intent_distribution 与最终 ai_mentions.csv 不一致"))
    if app.get("annotation_intent_distribution")!=final_intents:issues.append(Issue("error","report-appendix-intent-count-drift","report_model.appendix.annotation_intent_distribution 与最终 ai_mentions.csv 不一致"))
    qap=run/"measurement_qa_summary.json"
    if qap.is_file():
        try:qa=json.loads(qap.read_text(encoding="utf-8"))
        except Exception as e:issues.append(Issue("error","measurement-qa-summary-invalid",f"measurement_qa_summary.json 无效：{e}"));qa={}
        if qa:
            if qa.get("mention_intent_distribution")!=final_intents:issues.append(Issue("error","qa-summary-intent-count-drift","measurement_qa_summary.json 与最终 ai_mentions.csv 不一致；重新运行 build_measurement_qa_summary.py"))
            if intnum(qa.get("metrics_rows"))!=len(metrics):issues.append(Issue("error","qa-summary-metric-count-drift","measurement_qa_summary.metrics_rows 与最终 ai_metrics.csv 不一致"))
            target_dist=dict(sorted(Counter((m.get("measurement_target") or "").strip() for m in metrics if (m.get("measurement_target") or "").strip()).items()))
            if qa.get("metrics_target_distribution")!=target_dist:issues.append(Issue("error","qa-summary-target-count-drift","measurement_qa_summary.metrics_target_distribution 与最终 ai_metrics.csv 不一致"))

    for key in ("recheck","resolution_recheck","annotation_intent_distribution","research_assets","methodology_notes"):
        if key not in app:issues.append(Issue("error","appendix-contract",f"report_model.appendix 缺少 {key}"))

    # ---- Report Layer 真实产物门禁（阻断空壳报告）----
    _check_asset_layer(run,issues,model,universe,emergent)
    _check_concept_layer(run,issues,model,universe,emergent)
    _check_analysis_layer(run,issues,model)
    _check_report_sections(issues,model,run)
    _check_docx(run,issues)
    delivered=run/"deliverables"
    if delivered.is_dir():
        bad=[p.name for p in delivered.iterdir() if p.is_file() and p.name!="report.docx" and p.suffix.lower() in {".pdf",".html"}]
        if bad:issues.append(Issue("error","extra-formats","v2.2 不允许正式生成 PDF/HTML："+", ".join(bad)))
