#!/usr/bin/env python3
"""Customer-facing report contract layered on top of the v2.2 report validator.

The underlying data/audit contract remains v2.2. This wrapper adds a product contract:
formal DOCX output is Chinese-first and must not leak developer fields, engineering files,
raw Python/JSON structures, or inapplicable citation metrics into the customer report.
"""
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import validation_report as core
from validation_common import Issue

W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

REQUIRED_DOCX_SECTIONS=(
    "核心结论",
    "一、竞争格局总览",
    "二、全国品牌 AI 可见度",
    "三、本地 / 区域机构 AI 可见度",
    "四、老师 / IP AI 可见度",
    "五、结果稳定性",
    "六、概念占位",
    "七、GEO 资产基础",
    "八、观察主体与新出现竞争者",
    "九、重点主体诊断",
    "十、区域策略与 90 天行动",
    "十一、如何理解本报告",
    "附录：研究口径与主体清单",
)

FORBIDDEN_VISIBLE_TOKENS=(
    "INTERNAL RESEARCH","Executive Summary","Market Universe","Query / Retrieval Robustness",
    "Query/Retrieval Robustness","Concept Ownership","Asset Readiness","Expert / IP","Top3",
    "measurement_target","market_role","market_scope","entity_type","sampling_mode",
    "answer_context_mode","context_isolation_level","query_variant_mode","repeat_runs_expected",
    "fresh_context_required","page_collection_status","positive_persistence_3of3_rate",
    "pairwise_positive_set_jaccard","exact_positive_set_match_rate","unknown_fields",
    "native-recorded","legacy-reconstructed","local-core","local-active","national-benchmark","expert-ip",
)


def _docx_text(docx:Path):
    with zipfile.ZipFile(docx) as z:
        root=ET.fromstring(z.read("word/document.xml"))
    return "\n".join((t.text or "") for t in root.iter(W+"t"))


def _answer_citations(run:Path):
    p=run/"ai_answers.jsonl"
    if not p.is_file():return None
    total=0
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():continue
            obj=json.loads(line);total+=len(obj.get("citations") or [])
    except Exception:return None
    return total


def check_customer_docx(run:Path,issues:list[Issue]):
    docx=run/"deliverables"/"report.docx"
    if not docx.is_file():return
    try:text=_docx_text(docx)
    except Exception:return

    leaked=[x for x in FORBIDDEN_VISIBLE_TOKENS if x in text]
    if leaked:
        issues.append(Issue("error","customer-report-internal-field","客户版 DOCX 暴露内部字段/英文工程术语："+", ".join(leaked[:12])))

    engineering=re.findall(r"(?<![\w./-])[^\s|，。；：]{1,80}\.(?:csv|jsonl?|py)(?![\w-])",text,re.I)
    if engineering:
        issues.append(Issue("error","customer-report-engineering-file","客户版 DOCX 不应展示工程文件名："+", ".join(sorted(set(engineering))[:10])))

    if re.search(r"\{\s*['\"][^{}\n]{1,80}['\"]\s*:\s*",text):
        issues.append(Issue("error","customer-report-raw-object","客户版 DOCX 出现原始 Python/JSON 对象字符串"))

    snake=sorted(set(re.findall(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b",text)))
    if snake:
        issues.append(Issue("error","customer-report-snake-case","客户版 DOCX 出现内部 snake_case 字段："+", ".join(snake[:12])))

    citations=_answer_citations(run)
    if citations==0 and "不适用" not in text:
        issues.append(Issue("error","customer-report-citation-na","原 Answer 无引用链时，客户版报告必须明确把引用率写为“不适用”，不得呈现为 0"))

    sections=core.docx_sections(docx)
    english_headings=[]
    for s in sections:
        h=s.get("heading") or ""
        cleaned=re.sub(r"\b(?:AI|GEO|IP|DOCX)\b","",h,flags=re.I)
        if re.search(r"[A-Za-z]{2,}",cleaned):english_headings.append(h)
    if english_headings:
        issues.append(Issue("error","customer-report-english-heading","客户版一级标题必须中文化："+", ".join(english_headings)))


def validate_report(run:Path,issues:list[Issue],universe:list[dict],metrics:list[dict],emergent:list[dict]):
    # Reuse the mature v2.2 data/report-layer validator while replacing only the visible DOCX contract.
    core.REQUIRED_DOCX_SECTIONS=REQUIRED_DOCX_SECTIONS
    core.validate_report(run,issues,universe,metrics,emergent)
    check_customer_docx(run,issues)
