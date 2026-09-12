#!/usr/bin/env python3
"""Customer-facing report contract layered on top of the mature v2.2 report validator."""
from __future__ import annotations
import json,re,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import validation_report as core
from validation_common import Issue

W="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

REQUIRED_DOCX_SECTIONS=(
    "核心结论","一、重点优化机会","二、全国品牌 AI 可见度","三、本地 / 区域机构 AI 可见度",
    "四、老师 / 个人品牌 AI 可见度","五、结果稳定性","六、概念占位","七、GEO 资产基础",
    "八、观察主体与新出现竞争者","九、重点主体诊断","十、区域策略与 90 天行动",
    "十一、如何理解本报告","附录：研究口径与主体清单",
)

FORBIDDEN_VISIBLE_TOKENS=(
    "INTERNAL RESEARCH","Executive Summary","Market Universe","Universe","AI Answer",
    "Query / Retrieval Robustness","Query/Retrieval Robustness","Concept Ownership","Asset Readiness",
    "Expert / IP","Expert/IP","Answer Cell","Top3","AI-emergent","Observation","Stage 1","Hybrid",
    "Recall","Jaccard","N.A.","single-engine","limited-multi-engine","multi-engine","native",
    "programmatic","semantic-retrieval-variants","external-search-augmented","not-collected",
    "measurement_target","market_role","market_scope","entity_type","sampling_mode",
    "answer_context_mode","context_isolation_level","query_variant_mode","repeat_runs_expected",
    "fresh_context_required","page_collection_status","positive_persistence_3of3_rate",
    "pairwise_positive_set_jaccard","exact_positive_set_match_rate","unknown_fields","unknown",
    "native-recorded","legacy-reconstructed","local-core","local-active","national-benchmark","expert-ip",
    "Annotation Review","Resolution Recheck","Citation Audit","Engine Coverage Rate","Cross-model Consistency",
    "机构题","IP 题","IP题","老师 / IP","Metrics","Entity Resolution","Query Matrix","citations","page mention","用户 Seed","API 级",
    "单引擎","模型原生回答","程序性隔离","记忆召回","首提率","正向集合",
)


def _docx_text(docx:Path):
    with zipfile.ZipFile(docx) as z:root=ET.fromstring(z.read("word/document.xml"))
    return "\n".join((t.text or "") for t in root.iter(W+"t"))


def _answer_citations(run:Path):
    p=run/"ai_answers.jsonl"
    if not p.is_file():return None
    total=0
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():total+=len(json.loads(line).get("citations") or [])
    except Exception:return None
    return total


def check_customer_docx(run:Path,issues:list[Issue]):
    docx=run/"deliverables"/"report.docx"
    if not docx.is_file():return
    try:text=_docx_text(docx)
    except Exception:return

    leaked=[x for x in FORBIDDEN_VISIBLE_TOKENS if x in text]
    if leaked:issues.append(Issue("error","customer-report-internal-field","客户版 DOCX 暴露内部字段、开发者术语或不友好的缩写："+", ".join(leaked[:20])))

    engineering=re.findall(r"(?<![\w./-])[^\s|，。；：]{1,80}\.(?:csv|jsonl?|py)(?![\w-])",text,re.I)
    if engineering:issues.append(Issue("error","customer-report-engineering-file","客户版 DOCX 不应展示工程文件名："+", ".join(sorted(set(engineering))[:10])))
    if re.search(r"\{\s*['\"][^{}\n]{1,80}['\"]\s*:\s*",text):issues.append(Issue("error","customer-report-raw-object","客户版 DOCX 出现原始 Python/JSON 对象字符串"))

    snake=sorted(set(re.findall(r"\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b",text)))
    if snake:issues.append(Issue("error","customer-report-snake-case","客户版 DOCX 出现内部 snake_case 字段："+", ".join(snake[:12])))

    tiers=sorted(set(re.findall(r"等级\s*[A-Z](?:[+-])?",text)))
    if tiers:issues.append(Issue("error","customer-report-tier-code","客户版报告不展示内部字母等级，只展示资产基础得分："+", ".join(tiers[:10])))

    if re.search(r"仅弱相关|更依赖品牌记忆",text):
        issues.append(Issue("error","customer-report-overclaim","客户版报告出现未经统计/因果验证的强推断（弱相关/依赖品牌记忆）"))
    if re.search(r"为全部\s*\d+\s*个本土|为每个目标主体锁定|唯一判据",text):
        issues.append(Issue("error","customer-report-action-scope","90 天行动仍把竞争主体当成客户可执行对象，或把复测写成唯一判据"))

    citations=_answer_citations(run)
    if citations==0:
        if "不适用" not in text and "不评估引用率" not in text:issues.append(Issue("error","customer-report-citation-na","原 Answer 无引用链时，客户版报告必须明确引用率不适用/不评估"))
        if re.search(r"引用率.{0,12}(?:恒为|为|=)?\s*0(?:\.0)?%?",text):issues.append(Issue("error","customer-report-citation-zero","原 Answer 无引用链时不得把引用率写成 0 或 0%"))

    sections=core.docx_sections(docx);english_headings=[]
    for s in sections:
        h=s.get("heading") or "";cleaned=re.sub(r"\b(?:AI|GEO|DOCX)\b","",h,flags=re.I)
        if re.search(r"[A-Za-z]{2,}",cleaned):english_headings.append(h)
    if english_headings:issues.append(Issue("error","customer-report-english-heading","客户版一级标题必须中文化："+", ".join(english_headings)))


def validate_report(run:Path,issues:list[Issue],universe:list[dict],metrics:list[dict],emergent:list[dict]):
    core.REQUIRED_DOCX_SECTIONS=REQUIRED_DOCX_SECTIONS
    core.validate_report(run,issues,universe,metrics,emergent)
    check_customer_docx(run,issues)
