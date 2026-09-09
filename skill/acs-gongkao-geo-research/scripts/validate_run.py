#!/usr/bin/env python3
"""校验公考 GEO 调研运行目录；v2 强制召回、实体与计数审计。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


WEIGHTS = {"query_coverage":30.0,"entity_clarity":25.0,"external_diversity":20.0,"concept_ownership":15.0,"freshness":10.0}
TRUE = {"1","true","yes","y","是"}
FALSE = {"0","false","no","n","否"}
PURPOSES = {"discovery","measurement","verification"}
QUERY_TYPES = {"generic","brand"}
DISCOVERY_CHANNELS = {"user-query","exam-vertical","institutional","platform","expert-ip","entity-alias"}
CORE_DISCOVERY_CHANNELS = {"user-query","exam-vertical","institutional","entity-alias"}
FINAL_CANDIDATE_STATUSES = {"scored","evidence-insufficient","merged","excluded","unresolved"}
INCLUSION_BASES = {"discovered","user-requested","owned-forced","benchmark"}
ENTITY_TYPES = {"institution","brand","teacher","company","platform","exam","product","region"}
RELATION_TYPES = {"operated-by","brand-of","teaches-at","founded-by","formerly-known-as","alias-of","offers","located-in","appears-on","partner-of","other"}
CONFIDENCE = {"high","medium","low"}
EVIDENCE_ID_RE = re.compile(r"^E\d+$")
ENTITY_ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]*\d+$")
DATE_RE = re.compile(r"(?:观察日期|observation_date)\s*[：:]\s*\d{4}-\d{2}-\d{2}", re.I)
DISCLAIMER_TERMS = ("不代表教学实力","不等于教学实力","不是教学实力")
STRONG_FACT_RE = re.compile(r"(?:上岸率|市场份额|排名第一|第\s*1\s*名|\d+(?:\.\d+)?%)")
LINK_RE = re.compile(r"https?://|\[[^\]]+\]\(https?://|\[E\d+\]", re.I)
DETERMINISTIC_TERMS = ("毫无疑问","必然","绝对","稳居第一","领先所有","最佳","唯一首选","本土最强","单极压制")

QUERY_FIELDS_V2 = {"query_id","query_text","query_type","query_purpose","discovery_channel","discovery_round","theme","region","city","exam","sampled_channel","sampled_at","status","notes"}
RESULT_FIELDS_V2 = {"result_id","query_id","entity_id","result_rank","source_url","source_title","matched_name","observed_at","channel","matched","counts_as_measurement_hit","notes"}
CANDIDATE_FIELDS_V2 = {"candidate_id","entity_id","display_name","candidate_type","discovery_round","discovery_channel","discovery_query_id","discovery_result_id","first_seen_at","evidence_strength","status","merged_into_entity_id","exclusion_reason","notes"}
ENTITY_FIELDS_V2 = {"entity_id","canonical_name","entity_type","aliases","legal_name","former_names","official_domain","region","parent_entity_id","entity_status","disambiguation_notes","source_ids","notes"}
RELATION_FIELDS_V2 = {"relation_id","source_entity_id","relation_type","target_entity_id","relation_status","valid_from","valid_to","evidence_ids","confidence","notes"}
EVIDENCE_FIELDS_V2 = {"evidence_id","entity_id","institution","query_id","query","query_type","source_title","source_url","source_domain","published_date","accessed_date","source_grade","independent","claim_type","concepts","duplicate_group","duplicate_reason","review_status","counting_scope","notes"}
SCORE_FIELDS_V2 = {"institution","entity_id","inclusion_basis",*WEIGHTS.keys(),"total","tier","evidence_confidence","generic_hits","generic_queries","brand_hits","evidence_count","independent_domains","notes"}
IP_FIELDS = {"teacher_name","aliases","institution","relation_status","relation_period","subjects","products","regions","platforms","generic_hits","brand_hits","concepts","source_ids","evidence_confidence","notes"}


@dataclass
class Issue:
    level: str
    code: str
    message: str
    key: str = ""


def _read_text(path: Path, issues: list[Issue], code: str) -> str:
    if not path.is_file():
        issues.append(Issue("error", f"missing-{code}", f"缺少必需文件：{path.name}")); return ""
    try: return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        issues.append(Issue("error", f"read-{code}", f"无法读取 {path.name}：{exc}")); return ""


def _read_csv(path: Path, issues: list[Issue], label: str, required: set[str] | None = None) -> tuple[list[dict[str,str]], set[str]]:
    if not path.is_file():
        issues.append(Issue("error", f"missing-{label}", f"缺少必需文件：{path.name}")); return [], set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle); rows = list(reader); fields = set(reader.fieldnames or [])
    except (OSError, csv.Error, UnicodeError) as exc:
        issues.append(Issue("error", f"read-{label}", f"无法读取 {path.name}：{exc}")); return [], set()
    missing = (required or set()) - fields
    if missing: issues.append(Issue("error", f"{label}-schema", f"{path.name} 缺少字段：{', '.join(sorted(missing))}"))
    return rows, fields


def _number(value: str, label: str, issues: list[Issue]) -> float | None:
    try: return float(value)
    except (TypeError, ValueError):
        issues.append(Issue("error","invalid-number",f"{label} 不是数字：{value!r}")); return None


def _expected_tier(total: float) -> str:
    if total >= 85: return "S"
    if total >= 80: return "A+"
    if total >= 70: return "A"
    if total >= 65: return "A-"
    if total >= 60: return "B+"
    if total >= 50: return "B"
    if total >= 45: return "B-"
    return "C"


def _field(report: str, label: str) -> str | None:
    match = re.search(rf"^{re.escape(label)}\s*[：:]\s*(.+?)\s*$", report, re.M)
    return match.group(1).strip() if match else None


def _int_field(report: str, label: str) -> int | None:
    value = _field(report, label)
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else None


def _split(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[|｜;,，；]", value or "") if item.strip()]


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _schema_version(report: str) -> str:
    value = _field(report, "Schema版本") or _field(report, "schema_version") or "1.1"
    return value.lstrip("vV")


def _base_report_checks(report: str, issues: list[Issue]) -> None:
    if report and not DATE_RE.search(report): issues.append(Issue("error","missing-observation-date","report.md 缺少 YYYY-MM-DD 格式的观察日期"))
    if report and not any(term in report for term in DISCLAIMER_TERMS): issues.append(Issue("error","missing-disclaimer","报告必须声明 GEO 不代表教学实力"))
    if report and _field(report,"IP名师调查") not in {"是","yes","Yes"}: issues.append(Issue("error","missing-ip-analysis","报告必须记录 IP名师调查：是"))
    owned = _field(report,"自有机构纳入")
    if owned not in {"是","否","yes","no","Yes","No"}: issues.append(Issue("error","missing-owned-institution-decision","报告必须记录 自有机构纳入：是/否"))
    elif owned.lower() in {"是","yes"} and not _field(report,"自有机构名称"): issues.append(Issue("error","missing-owned-institution-name","报告纳入自有机构时必须记录名称"))
    for line_no, line in enumerate(report.splitlines(), 1):
        if STRONG_FACT_RE.search(line) and not LINK_RE.search(line) and not any(term in line for term in DISCLAIMER_TERMS):
            issues.append(Issue("warning","unsourced-strong-fact",f"report.md 第 {line_no} 行可能包含没有同段证据的强事实",str(line_no)))


def _validate_html(run_dir: Path, issues: list[Issue], required: bool, schema: str) -> None:
    if not required: return
    html_text = _read_text(run_dir / "report.html", issues, "html")
    if not html_text: return
    low = html_text.lower()
    if not all(token in low for token in ("<html","<body","</html>")): issues.append(Issue("error","invalid-html","report.html 不是完整 HTML"))
    if schema.startswith("2"):
        if 'id="evidence-e' not in low: issues.append(Issue("error","missing-html-evidence-anchors","report.html 缺少证据锚点"))
        if not re.search(r'href=["\']https?://', html_text, re.I): issues.append(Issue("error","missing-html-source-links","report.html 缺少可点击来源链接"))
        if "@media print" not in low or "min-width:0" not in low.replace(" ",""): issues.append(Issue("error","unsafe-print-table-css","report.html 缺少窄页打印表格覆盖样式"))


def _validate_legacy(run_dir: Path, report: str, issues: list[Issue]) -> None:
    issues.append(Issue("info","legacy-schema","按 v1.1 兼容模式识别；这不是研究错误。新运行应使用 Schema版本：2.0"))
    queries, qf = _read_csv(run_dir/"queries.csv",issues,"queries",{"query_id","query_text","query_type"})
    if queries and not any(r.get("query_type","").lower()=="generic" for r in queries): issues.append(Issue("error","no-generic-query","queries.csv 必须包含泛词查询"))
    evidence, _ = _read_csv(run_dir/"evidence.csv",issues,"evidence",{"evidence_id","institution","source_url","source_grade"})
    for i,row in enumerate(evidence,2):
        if not re.match(r"^https?://\S+$",row.get("source_url","")): issues.append(Issue("error","invalid-source-url",f"evidence.csv 第 {i} 行网址无效"))
    scores, _ = _read_csv(run_dir/"scores.csv",issues,"scores",{"institution",*WEIGHTS,"total","tier"})
    institutions={r.get("institution","").strip() for r in evidence}
    for i,row in enumerate(scores,2):
        if row.get("institution","").strip() not in institutions: issues.append(Issue("error","score-without-evidence",f"scores.csv 第 {i} 行机构没有证据"))
    ips,_ = _read_csv(run_dir/"ip_entities.csv",issues,"ip-entities",IP_FIELDS)
    count=_int_field(report,"IP名师样本数")
    if count is None: issues.append(Issue("error","missing-ip-count","报告必须记录 IP名师样本数"))
    elif count != len(ips): issues.append(Issue("error","ip-count-mismatch",f"报告名师数 {count} 与 CSV {len(ips)} 不一致"))


def _validate_v2(run_dir: Path, report: str, issues: list[Issue]) -> None:
    queries,_ = _read_csv(run_dir/"queries.csv",issues,"queries",QUERY_FIELDS_V2)
    results,_ = _read_csv(run_dir/"query_results.csv",issues,"query-results",RESULT_FIELDS_V2)
    candidates,_ = _read_csv(run_dir/"candidate_pool.csv",issues,"candidate-pool",CANDIDATE_FIELDS_V2)
    entities,_ = _read_csv(run_dir/"entities.csv",issues,"entities",ENTITY_FIELDS_V2)
    relations,_ = _read_csv(run_dir/"entity_relations.csv",issues,"entity-relations",RELATION_FIELDS_V2)
    evidence,_ = _read_csv(run_dir/"evidence.csv",issues,"evidence",EVIDENCE_FIELDS_V2)
    scores,_ = _read_csv(run_dir/"scores.csv",issues,"scores",SCORE_FIELDS_V2)
    ips,_ = _read_csv(run_dir/"ip_entities.csv",issues,"ip-entities",IP_FIELDS)
    details_text = _read_text(run_dir/"score_details.json",issues,"score-details")
    if not queries: issues.append(Issue("error","empty-queries","queries.csv 没有记录"))
    if not entities: issues.append(Issue("error","empty-entities","entities.csv 没有实体"))
    if not scores: issues.append(Issue("error","empty-scores","scores.csv 没有评分主体"))

    query_map: dict[str,dict[str,str]] = {}
    discovery_rounds: set[int] = set(); discovery_channels:set[str]=set(); measurement_ids:set[str]=set()
    purpose_counts=Counter()
    for i,row in enumerate(queries,2):
        qid=row.get("query_id","").strip()
        if not qid or qid in query_map: issues.append(Issue("error","duplicate-query-id",f"queries.csv 第 {i} 行 query_id 为空或重复：{qid!r}"))
        query_map[qid]=row
        qtype=row.get("query_type","").strip().lower(); purpose=row.get("query_purpose","").strip().lower(); status=row.get("status","").strip().lower()
        if qtype not in QUERY_TYPES: issues.append(Issue("error","invalid-query-type",f"queries.csv 第 {i} 行 query_type 无效"))
        if purpose not in PURPOSES: issues.append(Issue("error","invalid-query-purpose",f"queries.csv 第 {i} 行 query_purpose 无效"))
        if status not in {"planned","sampled","failed","skipped"}: issues.append(Issue("error","invalid-query-status",f"queries.csv 第 {i} 行 status 无效"))
        if status == "sampled": purpose_counts[purpose]+=1
        if purpose == "measurement" and qtype != "generic": issues.append(Issue("error","measurement-not-generic",f"{qid}：measurement 必须是 generic"))
        if purpose == "measurement" and qtype == "generic" and status == "sampled": measurement_ids.add(qid)
        if purpose == "discovery" and status == "sampled":
            channel=row.get("discovery_channel","").strip().lower()
            if channel not in DISCOVERY_CHANNELS: issues.append(Issue("error","invalid-discovery-channel",f"{qid}：discovery_channel 无效"))
            else: discovery_channels.add(channel)
            try: discovery_rounds.add(int(row.get("discovery_round","")))
            except ValueError: issues.append(Issue("error","invalid-discovery-round",f"{qid}：discovery_round 必须是整数"))

    mode=_field(report,"研究模式") or ""
    if "地区全景" in mode or "regional-landscape" in mode:
        if not CORE_DISCOVERY_CHANNELS <= discovery_channels: issues.append(Issue("error","discovery-channel-coverage","地区全景至少覆盖 user-query、exam-vertical、institutional、entity-alias"))
        if not {1,2} <= discovery_rounds: issues.append(Issue("error","missing-discovery-round","地区全景必须完成两轮候选发现"))
    if not measurement_ids: issues.append(Issue("error","no-measurement-query","没有 sampled 的 generic + measurement 查询"))

    entity_map:dict[str,dict[str,str]]={}; name_index:defaultdict[str,set[str]]=defaultdict(set)
    for i,row in enumerate(entities,2):
        eid=row.get("entity_id","").strip()
        if not ENTITY_ID_RE.match(eid): issues.append(Issue("error","invalid-entity-id",f"entities.csv 第 {i} 行 entity_id 无效：{eid!r}"))
        if eid in entity_map: issues.append(Issue("error","duplicate-entity-id",f"entities.csv entity_id 重复：{eid}"))
        entity_map[eid]=row
        if row.get("entity_type","").strip().lower() not in ENTITY_TYPES: issues.append(Issue("error","invalid-entity-type",f"{eid} 的 entity_type 无效"))
        names=[row.get("canonical_name",""),row.get("legal_name",""),*_split(row.get("aliases","")),*_split(row.get("former_names",""))]
        for name in names:
            key=re.sub(r"[\s·•・（）()\-—_]+","",name).casefold()
            if key: name_index[key].add(eid)
        short_aliases=[a for a in _split(row.get("aliases","")) if len(re.sub(r"[^\u4e00-\u9fff]","",a))<=2]
        if short_aliases and not row.get("disambiguation_notes","").strip(): issues.append(Issue("error","missing-short-alias-disambiguation",f"{eid} 含短别名但缺少同名污染排除说明"))
    for name,ids in name_index.items():
        if len(ids)>1: issues.append(Issue("error","alias-collision",f"实体名称/别名 {name!r} 同时指向：{', '.join(sorted(ids))}"))

    result_map:dict[str,dict[str,str]]={}; hits:defaultdict[str,set[str]]=defaultdict(set); brand_hits:defaultdict[str,set[str]]=defaultdict(set)
    for i,row in enumerate(results,2):
        rid=row.get("result_id","").strip(); qid=row.get("query_id","").strip(); eid=row.get("entity_id","").strip()
        if not rid or rid in result_map: issues.append(Issue("error","duplicate-result-id",f"query_results.csv 第 {i} 行 result_id 为空或重复"))
        result_map[rid]=row
        if qid not in query_map: issues.append(Issue("error","result-query-missing",f"{rid} 引用了不存在的 query_id：{qid}"))
        if eid and eid not in entity_map: issues.append(Issue("error","result-entity-missing",f"{rid} 引用了不存在的 entity_id：{eid}"))
        matched=row.get("matched","").strip().lower() in TRUE; counted=row.get("counts_as_measurement_hit","").strip().lower() in TRUE
        if counted and (qid not in measurement_ids or not matched): issues.append(Issue("error","measurement-isolation",f"{rid} 不是有效 measurement 命中却被计入泛词覆盖"))
        if matched and eid and qid in measurement_ids and counted: hits[eid].add(qid)
        if matched and eid and qid in query_map and query_map[qid].get("query_type","").lower()=="brand" and query_map[qid].get("query_purpose","").lower()=="verification": brand_hits[eid].add(qid)

    candidate_map:dict[str,dict[str,str]]={}; scored_candidates:set[str]=set(); eligible_round2:set[str]=set(); eligible_total:set[str]=set(); first_round_entities:set[str]=set(); second_round_entities:set[str]=set()
    for i,row in enumerate(candidates,2):
        cid=row.get("candidate_id","").strip(); eid=row.get("entity_id","").strip(); status=row.get("status","").strip().lower()
        if not cid or cid in candidate_map: issues.append(Issue("error","duplicate-candidate-id",f"candidate_pool.csv 第 {i} 行 candidate_id 为空或重复"))
        candidate_map[cid]=row
        if eid and eid not in entity_map: issues.append(Issue("error","candidate-entity-missing",f"{cid} 引用了不存在的 entity_id：{eid}"))
        if status not in FINAL_CANDIDATE_STATUSES: issues.append(Issue("error","unfinished-candidate-status",f"{cid} 最终状态无效：{status!r}"))
        if status=="scored": scored_candidates.add(eid)
        if status in {"scored","evidence-insufficient"}:
            eligible_total.add(eid)
            if row.get("discovery_round","").strip()=="2": eligible_round2.add(eid)
        if row.get("discovery_round","").strip()=="1" and eid: first_round_entities.add(eid)
        if row.get("discovery_round","").strip()=="2" and eid and eid not in first_round_entities: second_round_entities.add(eid)
        if status=="merged" and not row.get("merged_into_entity_id","").strip(): issues.append(Issue("error","missing-merge-target",f"{cid} 标为 merged 但没有归并目标"))
        elif status=="merged" and row.get("merged_into_entity_id","").strip() not in entity_map: issues.append(Issue("error","merge-target-missing",f"{cid} 的归并目标不存在"))
        if status=="excluded" and not row.get("exclusion_reason","").strip(): issues.append(Issue("error","missing-exclusion-reason",f"{cid} 标为 excluded 但没有原因"))
        qid=row.get("discovery_query_id","").strip(); rid=row.get("discovery_result_id","").strip()
        if qid and qid not in query_map: issues.append(Issue("error","candidate-query-missing",f"{cid} 的发现问题不存在"))
        if rid and rid not in result_map: issues.append(Issue("error","candidate-result-missing",f"{cid} 的发现结果不存在"))
    second_round_entities -= first_round_entities
    if eligible_total:
        ratio=len(eligible_round2)/len(eligible_total)
        if ratio>0.35 and not _field(report,"第二轮新增占比说明"):
            issues.append(Issue("warning","candidate-saturation",f"第二轮新增可评估实体占 {ratio:.0%}，候选池可能尚未饱和；报告需说明是否继续搜索",f"{ratio:.3f}"))

    relation_ids:set[str]=set()
    for i,row in enumerate(relations,2):
        rid=row.get("relation_id","").strip(); source=row.get("source_entity_id","").strip(); target=row.get("target_entity_id","").strip()
        if not rid or rid in relation_ids: issues.append(Issue("error","duplicate-relation-id",f"entity_relations.csv 第 {i} 行 relation_id 为空或重复"))
        relation_ids.add(rid)
        if source not in entity_map or target not in entity_map: issues.append(Issue("error","relation-entity-missing",f"{rid} 的起点或终点实体不存在"))
        if row.get("relation_type","").strip().lower() not in RELATION_TYPES: issues.append(Issue("error","invalid-relation-type",f"{rid} 的 relation_type 无效"))
        if row.get("confidence","").strip().lower() not in CONFIDENCE: issues.append(Issue("error","invalid-relation-confidence",f"{rid} 的 confidence 无效"))
        if not row.get("evidence_ids","").strip(): issues.append(Issue("error","relation-without-evidence",f"{rid} 缺少 evidence_ids"))

    evidence_ids:set[str]=set(); evidence_by_entity:defaultdict[str,list[dict[str,str]]]=defaultdict(list); urls:defaultdict[str,list[dict[str,str]]]=defaultdict(list)
    for i,row in enumerate(evidence,2):
        evid=row.get("evidence_id","").strip(); eid=row.get("entity_id","").strip(); qid=row.get("query_id","").strip(); url=row.get("source_url","").strip()
        if not EVIDENCE_ID_RE.match(evid): issues.append(Issue("error","invalid-evidence-id",f"evidence.csv 第 {i} 行 evidence_id 必须匹配 E\\d+：{evid!r}"))
        if evid in evidence_ids: issues.append(Issue("error","duplicate-evidence-id",f"evidence_id 重复：{evid}"))
        evidence_ids.add(evid)
        if eid not in entity_map: issues.append(Issue("error","evidence-entity-missing",f"{evid} 引用了不存在的 entity_id"))
        if qid not in query_map: issues.append(Issue("error","evidence-query-missing",f"{evid} 引用了不存在的 query_id"))
        if not re.match(r"^https?://\S+$",url,re.I): issues.append(Issue("error","invalid-source-url",f"{evid} 的 source_url 无效"))
        if row.get("source_grade","").strip().upper() not in {"A1","A2","B","C"}: issues.append(Issue("error","invalid-source-grade",f"{evid} 的 source_grade 无效"))
        if row.get("independent","").strip().lower() not in TRUE|FALSE: issues.append(Issue("error","invalid-independent",f"{evid} 的 independent 无效"))
        if row.get("claim_type","").strip().lower() not in {"fact","institution-claim","proxy-metric","analysis"}: issues.append(Issue("error","invalid-claim-type",f"{evid} 的 claim_type 无效"))
        if url: urls[url].append(row)
        evidence_by_entity[eid].append(row)
    for url,rows in urls.items():
        if len(rows)>1:
            structured=all(r.get("duplicate_group","").strip() and r.get("duplicate_reason","").strip() and r.get("review_status","").strip().lower()=="reviewed" and r.get("counting_scope","").strip() for r in rows)
            if not structured: issues.append(Issue("warning","duplicate-url",f"来源网址出现 {len(rows)} 次但缺少完整的结构化复核：{url}",url))

    for eid,row in entity_map.items():
        for evid in _split(row.get("source_ids","")):
            if evid not in evidence_ids: issues.append(Issue("error","entity-evidence-missing",f"实体 {eid} 引用了不存在的证据 {evid}"))

    score_map:dict[str,dict[str,str]]={}; has_low=False
    for i,row in enumerate(scores,2):
        eid=row.get("entity_id","").strip(); name=row.get("institution","").strip(); basis=row.get("inclusion_basis","").strip().lower()
        if eid in score_map: issues.append(Issue("error","duplicate-score-entity",f"scores.csv entity_id 重复：{eid}"))
        score_map[eid]=row
        if eid not in entity_map: issues.append(Issue("error","score-entity-missing",f"{name or eid} 的实体不存在"))
        if eid not in scored_candidates: issues.append(Issue("error","score-candidate-status",f"{name or eid} 已评分但 candidate_pool 未标 scored"))
        if basis not in INCLUSION_BASES: issues.append(Issue("error","invalid-inclusion-basis",f"{name or eid} 的 inclusion_basis 无效"))
        confidence=row.get("evidence_confidence","").strip().lower(); has_low |= confidence=="low"
        if confidence not in CONFIDENCE: issues.append(Issue("error","invalid-confidence",f"{name or eid} 的 evidence_confidence 无效"))
        values={}
        for field,maximum in WEIGHTS.items():
            value=_number(row.get(field,""),f"scores.csv 第 {i} 行 {field}",issues)
            if value is not None:
                values[field]=value
                if not 0<=value<=maximum: issues.append(Issue("error","score-out-of-range",f"{name or eid} 的 {field} 超出 0..{maximum:g}"))
        total=_number(row.get("total",""),f"scores.csv 第 {i} 行 total",issues)
        if total is not None and len(values)==len(WEIGHTS):
            if abs(total-sum(values.values()))>0.0001: issues.append(Issue("error","score-sum",f"{name or eid} 的 total 不等于五维之和"))
            if row.get("tier","").strip()!=_expected_tier(total): issues.append(Issue("error","score-tier",f"{name or eid} 的等级与总分不一致"))
        expected_generic=len(hits[eid]); expected_brand=len(brand_hits[eid])
        actual_hits=_number(row.get("generic_hits",""),f"{name} generic_hits",issues); actual_queries=_number(row.get("generic_queries",""),f"{name} generic_queries",issues); actual_brand=_number(row.get("brand_hits",""),f"{name} brand_hits",issues)
        if actual_hits is not None and actual_hits!=expected_generic: issues.append(Issue("error","generic-hit-mismatch",f"{name} 的 generic_hits={actual_hits:g}，查询日志派生值为 {expected_generic}"))
        if actual_queries is not None and actual_queries!=len(measurement_ids): issues.append(Issue("error","generic-query-denominator-mismatch",f"{name} 的 generic_queries={actual_queries:g}，有效 measurement 问题为 {len(measurement_ids)}"))
        if actual_brand is not None and actual_brand!=expected_brand: issues.append(Issue("error","brand-hit-mismatch",f"{name} 的 brand_hits={actual_brand:g}，查询日志派生值为 {expected_brand}"))
        actual_ev=_number(row.get("evidence_count",""),f"{name} evidence_count",issues)
        if actual_ev is not None and actual_ev!=len(evidence_by_entity[eid]): issues.append(Issue("error","evidence-count-mismatch",f"{name} 的 evidence_count 与 evidence.csv 不一致"))
        independent_domains={_domain(r.get("source_url","")) for r in evidence_by_entity[eid] if r.get("independent","").lower() in TRUE and r.get("counting_scope","").lower()!="ignored"}
        actual_domains=_number(row.get("independent_domains",""),f"{name} independent_domains",issues)
        if actual_domains is not None and actual_domains!=len(independent_domains): issues.append(Issue("error","independent-domain-mismatch",f"{name} 的 independent_domains 与证据派生值不一致"))
    if scored_candidates != set(score_map): issues.append(Issue("error","candidate-score-set-mismatch","candidate_pool 中 scored 实体与 scores.csv 集合不一致"))

    owned=_field(report,"自有机构纳入")
    if owned and owned.lower() in {"否","no"} and any(r.get("inclusion_basis","").lower()=="owned-forced" for r in scores): issues.append(Issue("error","unexpected-owned-forced","用户选择不纳入自有机构，但 scores.csv 出现 owned-forced"))
    if ("单主体" in mode or "多主体" in mode or "institution-" in mode) and any(r.get("inclusion_basis","").lower()=="discovered" for r in scores): issues.append(Issue("error","specified-mode-expanded","指定主体模式不得自动加入 discovered 主体"))

    for i,row in enumerate(ips,2):
        if not row.get("teacher_name","").strip(): issues.append(Issue("error","missing-teacher-name",f"ip_entities.csv 第 {i} 行缺少 teacher_name"))
        if row.get("relation_status","").strip().lower() not in {"current","historical","partner","multiple","unverified"}: issues.append(Issue("error","invalid-ip-relation",f"ip_entities.csv 第 {i} 行 relation_status 无效"))
        if row.get("evidence_confidence","").strip().lower() not in CONFIDENCE: issues.append(Issue("error","invalid-ip-confidence",f"ip_entities.csv 第 {i} 行 evidence_confidence 无效"))
        for evid in _split(row.get("source_ids","")):
            if evid not in evidence_ids: issues.append(Issue("error","ip-evidence-missing",f"ip_entities.csv 第 {i} 行引用不存在的证据 {evid}"))

    try: details=json.loads(details_text) if details_text else []
    except json.JSONDecodeError as exc:
        issues.append(Issue("error","invalid-score-details-json",f"score_details.json 无效：{exc}")); details=[]
    details_map={item.get("entity_id"):item for item in details if isinstance(item,dict)} if isinstance(details,list) else {}
    for eid,row in score_map.items():
        item=details_map.get(eid); name=row.get("institution",eid)
        if not item: issues.append(Issue("error","missing-score-detail",f"{name} 缺少逐维评分理由")); continue
        dims=item.get("dimensions",{})
        for field in WEIGHTS:
            detail=dims.get(field,{}) if isinstance(dims,dict) else {}
            if not str(detail.get("reason","")).strip(): issues.append(Issue("error","missing-dimension-reason",f"{name} 的 {field} 缺少理由"))
            refs=detail.get("evidence_ids",[]) or detail.get("query_ids",[])
            if not refs: issues.append(Issue("error","missing-dimension-sources",f"{name} 的 {field} 缺少证据或问题编号"))
            try: detail_score=float(detail.get("score"))
            except (TypeError,ValueError): issues.append(Issue("error","invalid-dimension-detail-score",f"{name} 的 {field} 详情分无效")); continue
            if abs(detail_score-float(row.get(field,0)))>0.0001: issues.append(Issue("error","dimension-score-mismatch",f"{name} 的 {field} 详情分与 scores.csv 不一致"))

    for row in relations:
        for evid in _split(row.get("evidence_ids","")):
            if evid not in evidence_ids: issues.append(Issue("error","relation-evidence-missing",f"关系 {row.get('relation_id')} 引用不存在的证据 {evid}"))

    expected_counts={"Discovery问题数":purpose_counts["discovery"],"Measurement问题数":purpose_counts["measurement"],"Verification问题数":purpose_counts["verification"],"漏项审计轮数":max(discovery_rounds or {0}),"候选记录数":len(candidates),"第一轮候选实体数":len(first_round_entities),"第二轮新增实体数":len(second_round_entities),"去重后实体数":len(entities),"正式评分数":len(scores),"待观察/证据不足数":sum(r.get("status","").lower() in {"evidence-insufficient","unresolved"} for r in candidates),"IP名师样本数":len(ips),"证据数":len(evidence)}
    for label,expected in expected_counts.items():
        actual=_int_field(report,label)
        if actual is None: issues.append(Issue("error","missing-report-count",f"报告缺少机器可检字段：{label}"))
        elif actual!=expected: issues.append(Issue("error","report-count-mismatch",f"报告 {label}={actual}，结构化文件实际为 {expected}",label))
    channels_field=_field(report,"Discovery渠道覆盖") or ""
    for channel in sorted(discovery_channels):
        if channel not in channels_field: issues.append(Issue("error","report-discovery-channel-mismatch",f"报告 Discovery渠道覆盖 缺少 {channel}"))
    if has_low:
        found=[term for term in DETERMINISTIC_TERMS if term in report]
        if found: issues.append(Issue("warning","low-confidence-strong-language","低置信度主体与确定性措辞同时出现："+", ".join(found),"language"))


def _apply_warning_resolutions(run_dir: Path, issues: list[Issue]) -> list[Issue]:
    path=run_dir/"warning_resolutions.csv"
    if not path.is_file(): return issues
    temp:list[Issue]=[]; rows,_=_read_csv(path,temp,"warning-resolutions",{"issue_code","issue_key","resolution","status","reviewed_by","reviewed_at"})
    issues.extend(temp)
    resolved={(r.get("issue_code","").strip(),r.get("issue_key","").strip()) for r in rows if r.get("status","").strip().lower()=="reviewed" and r.get("resolution","").strip() and r.get("reviewed_by","").strip() and r.get("reviewed_at","").strip()}
    output=[]
    for issue in issues:
        if issue.level=="warning" and (issue.code,issue.key) in resolved:
            output.append(replace(issue,level="info",code="documented-"+issue.code,message="已结构化人工复核："+issue.message))
        else: output.append(issue)
    return output


def validate_run(run_dir: Path, require_deliverable: bool=True, schema_override: str="auto") -> list[Issue]:
    issues:list[Issue]=[]
    if not run_dir.is_dir(): return [Issue("error","missing-run-dir",f"不是目录：{run_dir}")]
    report=_read_text(run_dir/"report.md",issues,"report")
    schema=_schema_version(report) if schema_override=="auto" else schema_override
    _base_report_checks(report,issues); _validate_html(run_dir,issues,require_deliverable,schema)
    if schema.startswith("2"): _validate_v2(run_dir,report,issues)
    else: _validate_legacy(run_dir,report,issues)
    return _apply_warning_resolutions(run_dir,issues)


def route_smoke_prompt(prompt: str) -> dict[str,object]:
    if any(term in prompt for term in ("教学最好","老师最好","哪家教得好")): return {"route":"not-geo"}
    if any(term in prompt for term in ("空白","机会词","Gap")): scope="gap-analysis"
    elif any(term in prompt for term in ("对比","比较")): scope="institution-comparison"
    elif any(term in prompt for term in ("GEO表现","GEO 表现","查一下")): scope="institution-deep-dive"
    else: scope="regional-landscape"
    return {"route":"geo","scope":scope,"auto_discovery":scope=="regional-landscape","specified_only":scope in {"institution-deep-dive","institution-comparison"},"ask_region":True,"ask_include_owned_institution":scope=="regional-landscape","include_ip_teacher_analysis":True,"query_purposes":["discovery","measurement","verification"]}


def self_test() -> None:
    assert route_smoke_prompt("调查浙江公考机构GEO情况")["scope"]=="regional-landscape"
    assert route_smoke_prompt("查一下上岸村的GEO表现")["specified_only"] is True
    assert route_smoke_prompt("对比甲机构、乙机构GEO")["scope"]=="institution-comparison"
    assert route_smoke_prompt("浙江公考哪家教学最好")["route"]=="not-geo"


def build_parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description="校验公考 GEO 调研运行目录。")
    parser.add_argument("run_dir",nargs="?",type=Path)
    parser.add_argument("--strict",action="store_true",help="存在未处置警告时返回非零状态")
    parser.add_argument("--draft",action="store_true",help="制作过程允许暂缺 report.html")
    parser.add_argument("--schema",choices=["auto","1.1","2.0"],default="auto")
    parser.add_argument("--json",action="store_true")
    parser.add_argument("--self-test",action="store_true")
    return parser


def main() -> int:
    args=build_parser().parse_args()
    if args.self_test:
        try: self_test()
        except AssertionError as exc: print(f"validate_run 自测：失败：{exc}",file=sys.stderr); return 2
        print("validate_run 自测：通过（4 个路由场景）"); return 0
    if args.run_dir is None: build_parser().error("除使用 --self-test 外，必须提供 run_dir")
    issues=validate_run(args.run_dir,not args.draft,args.schema)
    errors=sum(i.level=="error" for i in issues); warnings=sum(i.level=="warning" for i in issues)
    if args.json: print(json.dumps({"run_dir":str(args.run_dir),"errors":errors,"warnings":warnings,"issues":[asdict(i) for i in issues]},ensure_ascii=False,indent=2))
    else:
        for issue in issues: print(f"{issue.level.upper()} [{issue.code}] {issue.message}")
        print(f"校验摘要：{errors} 个错误，{warnings} 个未处置警告")
    return 1 if errors or (args.strict and warnings) else 0


if __name__=="__main__":
    raise SystemExit(main())
