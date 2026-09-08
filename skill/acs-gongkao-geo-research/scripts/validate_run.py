#!/usr/bin/env python3
"""校验公考 GEO 调研运行目录。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


WEIGHTS = {
    "query_coverage": 30.0,
    "entity_clarity": 25.0,
    "external_diversity": 20.0,
    "concept_ownership": 15.0,
    "freshness": 10.0,
}
REQUIRED_EVIDENCE = {
    "evidence_id", "institution", "query", "query_type", "source_title", "source_url",
    "source_domain", "published_date", "accessed_date", "source_grade",
    "independent", "claim_type", "concepts", "notes",
}
REQUIRED_SCORE = {
    "institution", "role", *WEIGHTS.keys(), "total", "tier", "evidence_confidence",
    "generic_hits", "generic_queries", "brand_hits", "evidence_count",
    "independent_domains", "notes",
}
REQUIRED_IP = {
    "teacher_name", "aliases", "institution", "relation_status", "relation_period",
    "subjects", "products", "regions", "platforms", "generic_hits", "brand_hits",
    "concepts", "source_ids", "evidence_confidence", "notes",
}
ALLOWED_ROLES = {"candidate", "specified", "benchmark"}
ALLOWED_RELATIONS = {"current", "historical", "partner", "multiple", "unverified"}
DATE_RE = re.compile(r"(?:观察日期|observation_date)\s*[：:]\s*\d{4}-\d{2}-\d{2}", re.I)
OWNED_INCLUDE_RE = re.compile(r"(?:自有机构纳入|include_owned_institution)\s*[：:]\s*(是|否|yes|no)\b", re.I)
OWNED_NAME_RE = re.compile(r"(?:自有机构名称|owned_institution_names?)\s*[：:]\s*(\S.+)", re.I)
IP_ANALYSIS_RE = re.compile(r"IP\s*名师调查\s*[：:]\s*(是|yes)\b", re.I)
IP_COUNT_RE = re.compile(r"IP\s*名师样本数\s*[：:]\s*(\d+)\b", re.I)
DISCLAIMER_TERMS = ("不代表教学实力", "不等于教学实力", "不是教学实力")
DETERMINISTIC_TERMS = ("毫无疑问", "必然", "绝对", "稳居第一", "领先所有", "最佳", "唯一首选")
STRONG_FACT_RE = re.compile(r"(?:上岸率|市场份额|排名第一|第\s*1\s*名|\d+(?:\.\d+)?%)")
LINK_RE = re.compile(r"https?://|\[[^\]]+\]\(https?://|\[E\d+\]", re.I)


@dataclass
class Issue:
    level: str
    code: str
    message: str


def _read_csv(path: Path, issues: list[Issue], label: str) -> tuple[list[dict[str, str]], set[str]]:
    if not path.is_file():
        issues.append(Issue("error", f"missing-{label}", f"缺少必需文件：{path.name}"))
        return [], set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return list(reader), set(reader.fieldnames or [])
    except (OSError, csv.Error, UnicodeError) as exc:
        issues.append(Issue("error", f"read-{label}", f"无法读取 {path.name}：{exc}"))
        return [], set()


def _number(value: str, label: str, issues: list[Issue]) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        issues.append(Issue("error", "invalid-number", f"{label} 不是数字：{value!r}"))
        return None
    return number


def _expected_tier(total: float) -> str:
    if total >= 85: return "S"
    if total >= 80: return "A+"
    if total >= 70: return "A"
    if total >= 65: return "A-"
    if total >= 60: return "B+"
    if total >= 50: return "B"
    if total >= 45: return "B-"
    return "C"


def validate_run(run_dir: Path, require_deliverable: bool = True) -> list[Issue]:
    issues: list[Issue] = []
    if not run_dir.is_dir():
        return [Issue("error", "missing-run-dir", f"不是目录：{run_dir}")]

    report_path = run_dir / "report.md"
    if not report_path.is_file():
        issues.append(Issue("error", "missing-report", "缺少必需文件：report.md"))
        report = ""
    else:
        try:
            report = report_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(Issue("error", "read-report", f"无法读取 report.md：{exc}"))
            report = ""
    if report and not DATE_RE.search(report):
        issues.append(Issue("error", "missing-observation-date", "report.md 缺少 YYYY-MM-DD 格式的观察日期"))
    if report and not any(term in report for term in DISCLAIMER_TERMS):
        issues.append(Issue("error", "missing-disclaimer", "报告必须声明 GEO 不代表教学实力"))
    if report and not IP_ANALYSIS_RE.search(report):
        issues.append(Issue("error", "missing-ip-analysis", "报告必须记录 IP名师调查：是"))
    ip_count_match = IP_COUNT_RE.search(report) if report else None
    if report and not ip_count_match:
        issues.append(Issue("error", "missing-ip-count", "报告必须记录 IP名师样本数"))
    owned_include = OWNED_INCLUDE_RE.search(report) if report else None
    if report and not owned_include:
        issues.append(Issue("error", "missing-owned-institution-decision", "报告必须记录 自有机构纳入：是/否"))
    elif owned_include and owned_include.group(1).lower() in {"是", "yes"} and not OWNED_NAME_RE.search(report):
        issues.append(Issue("error", "missing-owned-institution-name", "报告纳入了用户机构，但缺少 自有机构名称"))

    if require_deliverable:
        html_path = run_dir / "report.html"
        if not html_path.is_file():
            issues.append(Issue("error", "missing-html", "缺少默认最终交付文件：report.html"))
        else:
            try:
                html = html_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                issues.append(Issue("error", "read-html", f"无法读取 report.html：{exc}"))
            else:
                lowered = html.lower()
                if "<html" not in lowered or "</html>" not in lowered or "<body" not in lowered:
                    issues.append(Issue("error", "invalid-html", "report.html 缺少完整的 HTML 或 body 结构"))

    queries, query_fields = _read_csv(run_dir / "queries.csv", issues, "queries")
    required_query_fields = {"query_id", "query_text", "query_type", "theme", "region", "city", "exam", "sampled_channel", "sampled_at", "notes"}
    missing_query_fields = required_query_fields - query_fields
    if missing_query_fields:
        issues.append(Issue("error", "query-schema", "queries.csv 缺少字段：" + ", ".join(sorted(missing_query_fields))))
    if not queries and (run_dir / "queries.csv").is_file():
        issues.append(Issue("error", "empty-queries", "queries.csv 没有查询记录"))
    if queries and not any(row.get("query_type", "").strip().lower() == "generic" for row in queries):
        issues.append(Issue("error", "no-generic-query", "queries.csv 必须至少包含一条泛词查询"))

    evidence, evidence_fields = _read_csv(run_dir / "evidence.csv", issues, "evidence")
    missing_evidence_fields = REQUIRED_EVIDENCE - evidence_fields
    if missing_evidence_fields:
        issues.append(Issue("error", "evidence-schema", "evidence.csv 缺少字段：" + ", ".join(sorted(missing_evidence_fields))))
    if not evidence and (run_dir / "evidence.csv").is_file():
        issues.append(Issue("error", "empty-evidence", "evidence.csv 没有证据记录"))

    evidence_institutions: set[str] = set()
    urls: list[str] = []
    for line_no, row in enumerate(evidence, start=2):
        institution = row.get("institution", "").strip()
        if institution:
            evidence_institutions.add(institution)
        url = row.get("source_url", "").strip()
        if not re.match(r"^https?://\S+$", url, re.I):
            issues.append(Issue("error", "invalid-source-url", f"evidence.csv 第 {line_no} 行的 source_url 无效"))
        else:
            urls.append(url)
        if row.get("query_type", "").strip().lower() not in {"generic", "brand"}:
            issues.append(Issue("error", "invalid-query-type", f"evidence.csv 第 {line_no} 行 query_type 必须是 generic 或 brand"))
        if row.get("source_grade", "").strip().upper() not in {"A1", "A2", "B", "C"}:
            issues.append(Issue("error", "invalid-source-grade", f"evidence.csv 第 {line_no} 行 source_grade 无效"))
        if row.get("independent", "").strip().lower() not in {"true", "false"}:
            issues.append(Issue("error", "invalid-independent", f"evidence.csv 第 {line_no} 行 independent 必须是 true 或 false"))
        if row.get("claim_type", "").strip().lower() not in {"fact", "institution-claim", "proxy-metric", "analysis"}:
            issues.append(Issue("error", "invalid-claim-type", f"evidence.csv 第 {line_no} 行 claim_type 无效"))

    for url, count in Counter(urls).items():
        if count > 1:
            issues.append(Issue("warning", "duplicate-url", f"来源网址出现 {count} 次，请确认没有重复计数：{url}"))

    ip_entities, ip_fields = _read_csv(run_dir / "ip_entities.csv", issues, "ip-entities")
    missing_ip_fields = REQUIRED_IP - ip_fields
    if missing_ip_fields:
        issues.append(Issue("error", "ip-schema", "ip_entities.csv 缺少字段：" + ", ".join(sorted(missing_ip_fields))))
    if not ip_entities and (run_dir / "ip_entities.csv").is_file() and "本次未发现可确认的 IP 名师" not in report:
        issues.append(Issue("warning", "empty-ip-entities", "ip_entities.csv 没有记录；报告应说明本次未发现可确认的 IP 名师"))
    if ip_count_match and int(ip_count_match.group(1)) != len(ip_entities):
        issues.append(Issue("error", "ip-count-mismatch", f"报告中的 IP名师样本数为 {ip_count_match.group(1)}，但 ip_entities.csv 有 {len(ip_entities)} 行"))
    for line_no, row in enumerate(ip_entities, start=2):
        if not row.get("teacher_name", "").strip():
            issues.append(Issue("error", "missing-teacher-name", f"ip_entities.csv 第 {line_no} 行缺少 teacher_name"))
        relation = row.get("relation_status", "").strip().lower()
        if relation not in ALLOWED_RELATIONS:
            issues.append(Issue("error", "invalid-relation-status", f"ip_entities.csv 第 {line_no} 行 relation_status 无效"))
        confidence = row.get("evidence_confidence", "").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            issues.append(Issue("error", "invalid-ip-confidence", f"ip_entities.csv 第 {line_no} 行 evidence_confidence 无效"))
        for field in ("generic_hits", "brand_hits"):
            value = _number(row.get(field, ""), f"ip_entities.csv 第 {line_no} 行 {field}", issues)
            if value is not None and value < 0:
                issues.append(Issue("error", "negative-ip-hits", f"ip_entities.csv 第 {line_no} 行 {field} 不得小于 0"))

    scores, score_fields = _read_csv(run_dir / "scores.csv", issues, "scores")
    missing_score_fields = REQUIRED_SCORE - score_fields
    if missing_score_fields:
        issues.append(Issue("error", "score-schema", "scores.csv 缺少字段：" + ", ".join(sorted(missing_score_fields))))
    if not scores and (run_dir / "scores.csv").is_file():
        issues.append(Issue("error", "empty-scores", "scores.csv 没有机构评分记录"))

    has_low_confidence = False
    for line_no, row in enumerate(scores, start=2):
        institution = row.get("institution", "").strip()
        if institution and institution not in evidence_institutions:
            issues.append(Issue("error", "score-without-evidence", f"{institution} 已评分但没有证据记录"))
        confidence = row.get("evidence_confidence", "").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            issues.append(Issue("error", "invalid-confidence", f"scores.csv 第 {line_no} 行 evidence_confidence 无效"))
        has_low_confidence = has_low_confidence or confidence == "low"
        role = row.get("role", "").strip().lower()
        if role not in ALLOWED_ROLES:
            issues.append(Issue("error", "invalid-role", f"scores.csv 第 {line_no} 行 role 必须是 Candidate、Specified 或 Benchmark"))

        values: dict[str, float] = {}
        for field, maximum in WEIGHTS.items():
            value = _number(row.get(field, ""), f"scores.csv line {line_no} {field}", issues)
            if value is not None:
                values[field] = value
                if value < 0 or value > maximum:
                    issues.append(Issue("error", "score-out-of-range", f"{institution or line_no} 的 {field} 必须在 0..{maximum:g} 范围内"))
        total = _number(row.get("total", ""), f"scores.csv line {line_no} total", issues)
        if total is not None and len(values) == len(WEIGHTS):
            calculated = sum(values.values())
            if abs(total - calculated) > 0.0001:
                issues.append(Issue("error", "score-sum", f"{institution or line_no} 的 total {total:g} 不等于五维之和 {calculated:g}"))
            expected = _expected_tier(total)
            if row.get("tier", "").strip() != expected:
                issues.append(Issue("error", "score-tier", f"{institution or line_no} 的 tier 应为 {expected}"))

        query_coverage = values.get("query_coverage")
        if query_coverage is not None and query_coverage >= 24:
            generic_hits = _number(row.get("generic_hits", ""), f"scores.csv line {line_no} generic_hits", issues)
            generic_queries = _number(row.get("generic_queries", ""), f"scores.csv line {line_no} generic_queries", issues)
            if generic_hits is not None and generic_queries is not None and (generic_hits <= 0 or generic_queries <= 0):
                issues.append(Issue("error", "brand-only-high-coverage", f"{institution or line_no} 没有泛词查询支持却获得了高泛词覆盖度"))

    if report and has_low_confidence:
        found = [term for term in DETERMINISTIC_TERMS if term in report]
        if found:
            issues.append(Issue("warning", "low-confidence-strong-language", "低置信度评分与确定性措辞同时出现：" + ", ".join(found)))

    if report:
        for line_no, line in enumerate(report.splitlines(), start=1):
            if STRONG_FACT_RE.search(line) and not LINK_RE.search(line) and not any(term in line for term in DISCLAIMER_TERMS):
                issues.append(Issue("warning", "unsourced-strong-fact", f"report.md 第 {line_no} 行可能包含没有同段来源的强事实"))

    return issues


def route_smoke_prompt(prompt: str) -> dict[str, object]:
    """Small deterministic routing smoke check; it is not a production NLP parser."""
    if any(term in prompt for term in ("教学最好", "老师最好", "哪家教得好")):
        return {"route": "not-geo"}
    if any(term in prompt for term in ("空白", "机会词", "Gap")):
        scope = "gap-analysis"
    elif any(term in prompt for term in ("对比", "比较")):
        scope = "institution-comparison"
    elif any(term in prompt for term in ("GEO表现", "GEO 表现", "查一下")):
        scope = "institution-deep-dive"
    else:
        scope = "regional-landscape"
    return {
        "route": "geo",
        "scope": scope,
        "auto_discovery": scope == "regional-landscape",
        "specified_only": scope in {"institution-deep-dive", "institution-comparison"},
        "ask_region": True,
        "ask_include_owned_institution": scope == "regional-landscape",
        "allow_forced_owned_institution": scope == "regional-landscape",
        "include_ip_teacher_analysis": True,
        "auto_benchmark": False,
        "benchmark_label": None,
        "query_types": ["generic", "brand"],
    }


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def self_test() -> None:
    cases = [
        ("调查浙江公考机构GEO情况", "regional-landscape"),
        ("查一下上岸村的GEO表现", "institution-deep-dive"),
        ("对比广东的甲机构、乙机构、丙机构GEO", "institution-comparison"),
        ("找四川公考GEO空白机会词", "gap-analysis"),
    ]
    for prompt, expected in cases:
        routed = route_smoke_prompt(prompt)
        assert routed["route"] == "geo" and routed["scope"] == expected
    assert route_smoke_prompt("浙江公考哪家教学最好")["route"] == "not-geo"
    regional = route_smoke_prompt("调查浙江公考机构GEO情况")
    assert regional["auto_discovery"] is True and regional["specified_only"] is False
    assert regional["ask_region"] is True and regional["ask_include_owned_institution"] is True
    assert regional["allow_forced_owned_institution"] is True
    assert regional["include_ip_teacher_analysis"] is True
    deep = route_smoke_prompt("查一下上岸村的GEO表现")
    assert deep["specified_only"] is True and deep["auto_benchmark"] is False
    assert deep["include_ip_teacher_analysis"] is True
    comparison = route_smoke_prompt("对比广东的甲机构、乙机构、丙机构GEO")
    assert comparison["specified_only"] is True and comparison["auto_benchmark"] is False

    with tempfile.TemporaryDirectory(prefix="gongkao-geo-valid-") as temp:
        run = Path(temp)
        (run / "report.md").write_text(
            "观察日期：2026-09-08\nIP名师调查：是\nIP名师样本数：1\n自有机构纳入：否\n免责声明：GEO 观察指数不代表教学实力、市场份额或大模型官方推荐排名。\n",
            encoding="utf-8",
        )
        (run / "report.html").write_text("<!doctype html><html><body><h1>示例报告</h1></body></html>", encoding="utf-8")
        query_fields = ["query_id", "query_text", "query_type", "theme", "region", "city", "exam", "sampled_channel", "sampled_at", "notes"]
        _write_csv(run / "queries.csv", query_fields, [
            {"query_id": "Q1", "query_text": "浙江公考培训机构有哪些", "query_type": "generic", "theme": "发现", "region": "浙江", "city": "", "exam": "省考", "sampled_channel": "public-web", "sampled_at": "2026-09-08T10:00:00+08:00", "notes": ""},
            {"query_id": "Q2", "query_text": "示例机构是什么", "query_type": "brand", "theme": "实体", "region": "浙江", "city": "", "exam": "省考", "sampled_channel": "public-web", "sampled_at": "2026-09-08T10:01:00+08:00", "notes": ""},
        ])
        evidence_fields = sorted(REQUIRED_EVIDENCE)
        _write_csv(run / "evidence.csv", evidence_fields, [{
            "evidence_id": "E1", "institution": "示例机构", "query": "浙江公考培训机构有哪些", "query_type": "generic",
            "source_title": "示例来源", "source_url": "https://example.com/source", "source_domain": "example.com",
            "published_date": "2026-09-01", "accessed_date": "2026-09-08", "source_grade": "A2",
            "independent": "true", "claim_type": "fact", "concepts": "[\"本地考情\"]", "notes": "",
        }])
        ip_fields = [
            "teacher_name", "aliases", "institution", "relation_status", "relation_period",
            "subjects", "products", "regions", "platforms", "generic_hits", "brand_hits",
            "concepts", "source_ids", "evidence_confidence", "notes",
        ]
        _write_csv(run / "ip_entities.csv", ip_fields, [{
            "teacher_name": "示例老师", "aliases": "", "institution": "示例机构",
            "relation_status": "current", "relation_period": "2026", "subjects": "申论",
            "products": "示例课程", "regions": "浙江", "platforms": "B站", "generic_hits": 1,
            "brand_hits": 1, "concepts": "本地申论", "source_ids": "E1",
            "evidence_confidence": "High", "notes": "",
        }])
        score_fields = ["institution", "role", *WEIGHTS.keys(), "total", "tier", "evidence_confidence", "generic_hits", "generic_queries", "brand_hits", "evidence_count", "independent_domains", "notes"]
        _write_csv(run / "scores.csv", score_fields, [{
            "institution": "示例机构", "role": "Candidate", "query_coverage": 24, "entity_clarity": 20,
            "external_diversity": 13, "concept_ownership": 11, "freshness": 8,
            "total": 76, "tier": "A", "evidence_confidence": "High", "generic_hits": 1, "generic_queries": 1,
            "brand_hits": 1, "evidence_count": 1, "independent_domains": 1, "notes": "",
        }])
        valid_issues = validate_run(run)
        assert not [issue for issue in valid_issues if issue.level == "error"], valid_issues

        (run / "report.html").unlink()
        missing_html_codes = {issue.code for issue in validate_run(run)}
        assert "missing-html" in missing_html_codes

        draft_codes = {issue.code for issue in validate_run(run, require_deliverable=False)}
        assert "missing-html" not in draft_codes

        (run / "report.md").write_text(
            "观察日期：2026-09-08\nIP名师调查：是\nIP名师样本数：1\n自有机构纳入：是\n免责声明：GEO 观察指数不代表教学实力、市场份额或大模型官方推荐排名。\n",
            encoding="utf-8",
        )
        missing_owned_name_codes = {issue.code for issue in validate_run(run)}
        assert "missing-owned-institution-name" in missing_owned_name_codes
        (run / "report.md").write_text(
            "观察日期：2026-09-08\nIP名师调查：是\nIP名师样本数：1\n自有机构纳入：否\n免责声明：GEO 观察指数不代表教学实力、市场份额或大模型官方推荐排名。\n",
            encoding="utf-8",
        )

        # Deliberately violate independent requirements to prove detection.
        _write_csv(run / "queries.csv", query_fields, [
            {"query_id": "Q2", "query_text": "示例机构是什么", "query_type": "brand", "theme": "实体", "region": "浙江", "city": "", "exam": "省考", "sampled_channel": "public-web", "sampled_at": "2026-09-08T10:01:00+08:00", "notes": ""},
        ])
        _write_csv(run / "scores.csv", score_fields, [{
            "institution": "无证据机构", "role": "Unknown", "query_coverage": 25, "entity_clarity": 20,
            "external_diversity": 13, "concept_ownership": 11, "freshness": 8,
            "total": 77, "tier": "A", "evidence_confidence": "Low", "generic_hits": 0, "generic_queries": 0,
            "brand_hits": 1, "evidence_count": 1, "independent_domains": 1, "notes": "",
        }])
        invalid_codes = {issue.code for issue in validate_run(run)}
        assert {"no-generic-query", "score-without-evidence", "brand-only-high-coverage", "invalid-role"} <= invalid_codes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验公考 GEO 调研运行目录。")
    parser.add_argument("run_dir", nargs="?", type=Path, help="包含 report.md、report.html 和结构化 CSV 的运行目录")
    parser.add_argument("--strict", action="store_true", help="存在警告时返回非零状态")
    parser.add_argument("--draft", action="store_true", help="草稿检查：暂时允许缺少 report.html；不得用于最终交付")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    parser.add_argument("--self-test", action="store_true", help="运行路由和运行目录冒烟测试")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        try:
            self_test()
        except AssertionError as exc:
            print(f"validate_run 自测：失败：{exc}", file=sys.stderr)
            return 2
        print("validate_run 自测：通过（5 个路由场景 + 有效／无效运行目录检查）")
        return 0
    if args.run_dir is None:
        build_parser().error("除使用 --self-test 外，必须提供 run_dir")

    issues = validate_run(args.run_dir, require_deliverable=not args.draft)
    errors = sum(issue.level == "error" for issue in issues)
    warnings = sum(issue.level == "warning" for issue in issues)
    if args.json:
        print(json.dumps({"run_dir": str(args.run_dir), "errors": errors, "warnings": warnings, "issues": [asdict(item) for item in issues]}, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            print(f"{issue.level.upper()} [{issue.code}] {issue.message}")
        print(f"校验摘要：{errors} 个错误，{warnings} 个警告")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
