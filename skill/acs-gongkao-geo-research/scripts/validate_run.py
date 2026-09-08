#!/usr/bin/env python3
"""Validate a gongkao GEO research run directory."""

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
    "institution", "query", "query_type", "source_title", "source_url",
    "source_domain", "published_date", "accessed_date", "source_grade",
    "independent", "claim_type", "concepts", "notes",
}
REQUIRED_SCORE = {
    "institution", "role", *WEIGHTS.keys(), "total", "tier", "evidence_confidence",
    "generic_hits", "generic_queries", "brand_hits", "evidence_count",
    "independent_domains", "notes",
}
ALLOWED_ROLES = {"candidate", "specified", "benchmark"}
DATE_RE = re.compile(r"(?:观察日期|observation_date)\s*[：:]\s*\d{4}-\d{2}-\d{2}", re.I)
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
        issues.append(Issue("error", f"missing-{label}", f"missing required file: {path.name}"))
        return [], set()
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            return list(reader), set(reader.fieldnames or [])
    except (OSError, csv.Error, UnicodeError) as exc:
        issues.append(Issue("error", f"read-{label}", f"cannot read {path.name}: {exc}"))
        return [], set()


def _number(value: str, label: str, issues: list[Issue]) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        issues.append(Issue("error", "invalid-number", f"{label} is not numeric: {value!r}"))
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


def validate_run(run_dir: Path, require_pdf: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if not run_dir.is_dir():
        return [Issue("error", "missing-run-dir", f"not a directory: {run_dir}")]

    report_path = run_dir / "report.md"
    if not report_path.is_file():
        issues.append(Issue("error", "missing-report", "missing required file: report.md"))
        report = ""
    else:
        try:
            report = report_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            issues.append(Issue("error", "read-report", f"cannot read report.md: {exc}"))
            report = ""
    if report and not DATE_RE.search(report):
        issues.append(Issue("error", "missing-observation-date", "report.md has no YYYY-MM-DD observation date"))
    if report and not any(term in report for term in DISCLAIMER_TERMS):
        issues.append(Issue("error", "missing-disclaimer", "report must state that GEO is not teaching quality"))

    if require_pdf:
        pdf_path = run_dir / "report.pdf"
        if not pdf_path.is_file():
            issues.append(Issue("error", "missing-pdf", "missing required final deliverable: report.pdf"))
        else:
            try:
                pdf_data = pdf_path.read_bytes()
            except OSError as exc:
                issues.append(Issue("error", "read-pdf", f"cannot read report.pdf: {exc}"))
            else:
                if not pdf_data.startswith(b"%PDF-") or b"%%EOF" not in pdf_data[-1024:]:
                    issues.append(Issue("error", "invalid-pdf", "report.pdf has no valid PDF header or EOF marker"))

    queries, query_fields = _read_csv(run_dir / "queries.csv", issues, "queries")
    required_query_fields = {"query_id", "query_text", "query_type", "theme", "region", "city", "exam", "sampled_channel", "sampled_at", "notes"}
    missing_query_fields = required_query_fields - query_fields
    if missing_query_fields:
        issues.append(Issue("error", "query-schema", "queries.csv missing fields: " + ", ".join(sorted(missing_query_fields))))
    if not queries and (run_dir / "queries.csv").is_file():
        issues.append(Issue("error", "empty-queries", "queries.csv contains no query rows"))
    if queries and not any(row.get("query_type", "").strip().lower() == "generic" for row in queries):
        issues.append(Issue("error", "no-generic-query", "queries.csv must contain at least one Generic Query"))

    evidence, evidence_fields = _read_csv(run_dir / "evidence.csv", issues, "evidence")
    missing_evidence_fields = REQUIRED_EVIDENCE - evidence_fields
    if missing_evidence_fields:
        issues.append(Issue("error", "evidence-schema", "evidence.csv missing fields: " + ", ".join(sorted(missing_evidence_fields))))
    if not evidence and (run_dir / "evidence.csv").is_file():
        issues.append(Issue("error", "empty-evidence", "evidence.csv contains no evidence rows"))

    evidence_institutions: set[str] = set()
    urls: list[str] = []
    for line_no, row in enumerate(evidence, start=2):
        institution = row.get("institution", "").strip()
        if institution:
            evidence_institutions.add(institution)
        url = row.get("source_url", "").strip()
        if not re.match(r"^https?://\S+$", url, re.I):
            issues.append(Issue("error", "invalid-source-url", f"evidence.csv line {line_no} has invalid source_url"))
        else:
            urls.append(url)
        if row.get("query_type", "").strip().lower() not in {"generic", "brand"}:
            issues.append(Issue("error", "invalid-query-type", f"evidence.csv line {line_no} query_type must be generic or brand"))
        if row.get("source_grade", "").strip().upper() not in {"A1", "A2", "B", "C"}:
            issues.append(Issue("error", "invalid-source-grade", f"evidence.csv line {line_no} has invalid source_grade"))
        if row.get("independent", "").strip().lower() not in {"true", "false"}:
            issues.append(Issue("error", "invalid-independent", f"evidence.csv line {line_no} independent must be true or false"))
        if row.get("claim_type", "").strip().lower() not in {"fact", "institution-claim", "proxy-metric", "analysis"}:
            issues.append(Issue("error", "invalid-claim-type", f"evidence.csv line {line_no} has invalid claim_type"))

    for url, count in Counter(urls).items():
        if count > 1:
            issues.append(Issue("warning", "duplicate-url", f"source URL appears {count} times; verify it is not double-counted: {url}"))

    scores, score_fields = _read_csv(run_dir / "scores.csv", issues, "scores")
    missing_score_fields = REQUIRED_SCORE - score_fields
    if missing_score_fields:
        issues.append(Issue("error", "score-schema", "scores.csv missing fields: " + ", ".join(sorted(missing_score_fields))))
    if not scores and (run_dir / "scores.csv").is_file():
        issues.append(Issue("error", "empty-scores", "scores.csv contains no scored institutions"))

    has_low_confidence = False
    for line_no, row in enumerate(scores, start=2):
        institution = row.get("institution", "").strip()
        if institution and institution not in evidence_institutions:
            issues.append(Issue("error", "score-without-evidence", f"{institution} is scored but has no evidence row"))
        confidence = row.get("evidence_confidence", "").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            issues.append(Issue("error", "invalid-confidence", f"scores.csv line {line_no} has invalid evidence_confidence"))
        has_low_confidence = has_low_confidence or confidence == "low"
        role = row.get("role", "").strip().lower()
        if role not in ALLOWED_ROLES:
            issues.append(Issue("error", "invalid-role", f"scores.csv line {line_no} role must be Candidate, Specified, or Benchmark"))

        values: dict[str, float] = {}
        for field, maximum in WEIGHTS.items():
            value = _number(row.get(field, ""), f"scores.csv line {line_no} {field}", issues)
            if value is not None:
                values[field] = value
                if value < 0 or value > maximum:
                    issues.append(Issue("error", "score-out-of-range", f"{institution or line_no} {field} must be 0..{maximum:g}"))
        total = _number(row.get("total", ""), f"scores.csv line {line_no} total", issues)
        if total is not None and len(values) == len(WEIGHTS):
            calculated = sum(values.values())
            if abs(total - calculated) > 0.0001:
                issues.append(Issue("error", "score-sum", f"{institution or line_no} total {total:g} != five-dimension sum {calculated:g}"))
            expected = _expected_tier(total)
            if row.get("tier", "").strip() != expected:
                issues.append(Issue("error", "score-tier", f"{institution or line_no} tier should be {expected}"))

        query_coverage = values.get("query_coverage")
        if query_coverage is not None and query_coverage >= 24:
            generic_hits = _number(row.get("generic_hits", ""), f"scores.csv line {line_no} generic_hits", issues)
            generic_queries = _number(row.get("generic_queries", ""), f"scores.csv line {line_no} generic_queries", issues)
            if generic_hits is not None and generic_queries is not None and (generic_hits <= 0 or generic_queries <= 0):
                issues.append(Issue("error", "brand-only-high-coverage", f"{institution or line_no} has high Query Coverage without Generic Query support"))

    if report and has_low_confidence:
        found = [term for term in DETERMINISTIC_TERMS if term in report]
        if found:
            issues.append(Issue("warning", "low-confidence-strong-language", "low-confidence scores coexist with deterministic wording: " + ", ".join(found)))

    if report:
        for line_no, line in enumerate(report.splitlines(), start=1):
            if STRONG_FACT_RE.search(line) and not LINK_RE.search(line) and not any(term in line for term in DISCLAIMER_TERMS):
                issues.append(Issue("warning", "unsourced-strong-fact", f"report.md line {line_no} may contain a strong fact without an inline source"))

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
    deep = route_smoke_prompt("查一下上岸村的GEO表现")
    assert deep["specified_only"] is True and deep["auto_benchmark"] is False
    comparison = route_smoke_prompt("对比广东的甲机构、乙机构、丙机构GEO")
    assert comparison["specified_only"] is True and comparison["auto_benchmark"] is False

    with tempfile.TemporaryDirectory(prefix="gongkao-geo-valid-") as temp:
        run = Path(temp)
        (run / "report.md").write_text(
            "观察日期：2026-09-08\n免责声明：GEO 观察指数不代表教学实力、市场份额或大模型官方推荐排名。\n",
            encoding="utf-8",
        )
        (run / "report.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
        query_fields = ["query_id", "query_text", "query_type", "theme", "region", "city", "exam", "sampled_channel", "sampled_at", "notes"]
        _write_csv(run / "queries.csv", query_fields, [
            {"query_id": "Q1", "query_text": "浙江公考培训机构有哪些", "query_type": "generic", "theme": "发现", "region": "浙江", "city": "", "exam": "省考", "sampled_channel": "public-web", "sampled_at": "2026-09-08T10:00:00+08:00", "notes": ""},
            {"query_id": "Q2", "query_text": "示例机构是什么", "query_type": "brand", "theme": "实体", "region": "浙江", "city": "", "exam": "省考", "sampled_channel": "public-web", "sampled_at": "2026-09-08T10:01:00+08:00", "notes": ""},
        ])
        evidence_fields = sorted(REQUIRED_EVIDENCE)
        _write_csv(run / "evidence.csv", evidence_fields, [{
            "institution": "示例机构", "query": "浙江公考培训机构有哪些", "query_type": "generic",
            "source_title": "示例来源", "source_url": "https://example.com/source", "source_domain": "example.com",
            "published_date": "2026-09-01", "accessed_date": "2026-09-08", "source_grade": "A2",
            "independent": "true", "claim_type": "fact", "concepts": "[\"本地考情\"]", "notes": "",
        }])
        score_fields = ["institution", "role", *WEIGHTS.keys(), "total", "tier", "evidence_confidence", "generic_hits", "generic_queries", "brand_hits", "evidence_count", "independent_domains", "notes"]
        _write_csv(run / "scores.csv", score_fields, [{
            "institution": "示例机构", "role": "Candidate", "query_coverage": 24, "entity_clarity": 20,
            "external_diversity": 13, "concept_ownership": 11, "freshness": 8,
            "total": 76, "tier": "A", "evidence_confidence": "High", "generic_hits": 1, "generic_queries": 1,
            "brand_hits": 1, "evidence_count": 1, "independent_domains": 1, "notes": "",
        }])
        valid_issues = validate_run(run, require_pdf=True)
        assert not [issue for issue in valid_issues if issue.level == "error"], valid_issues

        (run / "report.pdf").unlink()
        missing_pdf_codes = {issue.code for issue in validate_run(run, require_pdf=True)}
        assert "missing-pdf" in missing_pdf_codes

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
    parser = argparse.ArgumentParser(description="Validate a gongkao GEO research run directory.")
    parser.add_argument("run_dir", nargs="?", type=Path, help="directory containing report.md and the three CSV files")
    parser.add_argument("--strict", action="store_true", help="return nonzero when warnings are present")
    parser.add_argument("--require-pdf", action="store_true", help="require report.pdf and check basic PDF file markers")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--self-test", action="store_true", help="run routing and run-directory smoke tests")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        try:
            self_test()
        except AssertionError as exc:
            print(f"validate_run self-test: FAIL: {exc}", file=sys.stderr)
            return 2
        print("validate_run self-test: PASS (5 routing scenarios + valid/invalid run checks)")
        return 0
    if args.run_dir is None:
        build_parser().error("run_dir is required unless --self-test is used")

    issues = validate_run(args.run_dir, require_pdf=args.require_pdf)
    errors = sum(issue.level == "error" for issue in issues)
    warnings = sum(issue.level == "warning" for issue in issues)
    if args.json:
        print(json.dumps({"run_dir": str(args.run_dir), "errors": errors, "warnings": warnings, "issues": [asdict(item) for item in issues]}, ensure_ascii=False, indent=2))
    else:
        for issue in issues:
            print(f"{issue.level.upper()} [{issue.code}] {issue.message}")
        print(f"validation summary: {errors} error(s), {warnings} warning(s)")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
