#!/usr/bin/env python3
"""将公考 GEO 调研的 report.md 转为自包含 report.html。"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import tempfile
from pathlib import Path


TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
LINK_RE = re.compile(r"(!?)\[([^\]]+)\]\(([^)\s]+)(?:\s+[\"']([^\"']+)[\"'])?\)")
CODE_RE = re.compile(r"`([^`]+)`")
EVIDENCE_REF_RE = re.compile(r"\[(E\d+)\]")


STYLE = """
:root { color-scheme: light; --ink:#172033; --muted:#657086; --line:#dbe2ec; --brand:#225ea8; --soft:#f4f7fb; }
* { box-sizing: border-box; }
body { margin:0; color:var(--ink); background:#eef2f7; font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; }
main { width:min(1040px,calc(100% - 96px)); margin:48px auto; padding:56px 72px; background:white; border-radius:16px; box-shadow:0 10px 35px rgba(29,43,68,.08); }
h1,h2,h3,h4 { line-height:1.35; margin:1.45em 0 .65em; color:#10233f; }
h1 { margin-top:0; font-size:2rem; border-bottom:3px solid var(--brand); padding-bottom:.4em; }
h2 { font-size:1.5rem; border-bottom:1px solid var(--line); padding-bottom:.3em; }
h3 { font-size:1.18rem; }
p,ul,ol,blockquote,pre,.table-wrap { margin:.8em 0; }
a { color:#1769aa; overflow-wrap:anywhere; }
code { padding:.12em .35em; border-radius:5px; background:#edf1f7; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
pre { overflow:auto; padding:16px; border-radius:10px; background:#172033; color:#f4f7fb; }
pre code { padding:0; background:transparent; color:inherit; }
blockquote { margin-left:0; padding:10px 18px; border-left:4px solid var(--brand); background:var(--soft); color:#3e4b61; }
.table-wrap { width:100%; overflow-x:auto; border:1px solid var(--line); border-radius:10px; }
table { width:100%; border-collapse:collapse; min-width:680px; }
th,td { padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { position:sticky; top:0; background:#eaf1f8; white-space:nowrap; }
tr:nth-child(even) td { background:#fafbfd; }
img { max-width:100%; height:auto; }
.meta { margin-top:36px; padding-top:14px; border-top:1px solid var(--line); color:var(--muted); font-size:.9rem; }
.machine-fields { display:grid; grid-template-columns:repeat(auto-fit,minmax(270px,1fr)); gap:4px 18px; margin:.9em 0; padding:12px 16px; border-left:4px solid var(--brand); background:var(--soft); color:#334158; }
.machine-fields > div { min-width:0; overflow-wrap:anywhere; }
.evidence-ref { font-size:.86em; white-space:nowrap; }
.evidence-index td:first-child { white-space:nowrap; font-weight:600; }
@media (max-width:960px) { main { width:calc(100% - 32px); margin:16px auto; padding:40px 36px; } }
@media (max-width:720px) { main { width:100%; margin:0; padding:28px 20px; border-radius:0; } }
@page { size:A4 portrait; margin:12mm; }
@media print { body { background:white; font-size:10pt; } main { width:auto; margin:0; padding:0; box-shadow:none; } a { color:inherit; text-decoration:none; } h1,h2,h3 { break-after:avoid; } blockquote,pre { break-inside:avoid; } .machine-fields { grid-template-columns:1fr 1fr; padding:7px 10px; break-inside:avoid; } .table-wrap { overflow:visible; border-radius:0; } table { min-width:0; width:100%; table-layout:auto; font-size:7.5pt; break-inside:auto; } tr { break-inside:avoid; } th,td { padding:3px 4px; overflow-wrap:anywhere; word-break:break-word; } th { position:static; white-space:normal; } }
""".strip()


def inline_markup(text: str) -> str:
    escaped = html.escape(text, quote=True)
    code_tokens: list[str] = []

    def stash_code(match: re.Match[str]) -> str:
        code_tokens.append(f"<code>{match.group(1)}</code>")
        return f"\x00CODE{len(code_tokens) - 1}\x00"

    escaped = CODE_RE.sub(stash_code, escaped)

    def replace_link(match: re.Match[str]) -> str:
        image, label, url, title = match.groups()
        title_attr = f' title="{title}"' if title else ""
        if image:
            return f'<img src="{url}" alt="{label}"{title_attr}>'
        return f'<a href="{url}"{title_attr}>{label}</a>'

    escaped = LINK_RE.sub(replace_link, escaped)
    escaped = EVIDENCE_REF_RE.sub(r'<a class="evidence-ref" href="#evidence-\1">[\1]</a>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", escaped)
    for index, token in enumerate(code_tokens):
        escaped = escaped.replace(f"\x00CODE{index}\x00", token)
    return escaped


def split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def markdown_to_html(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    output: list[str] = []
    paragraph: list[str] = []
    list_tag: str | None = None
    in_code = False
    code_lines: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            parts = [part.strip() for part in paragraph]
            is_machine_fields = len(parts) >= 2 and all(
                0 < min((position for position in (part.find("："), part.find(":")) if position >= 0), default=10_000) <= 30
                for part in parts
            )
            if is_machine_fields:
                output.append('<div class="machine-fields">' + "".join(f"<div>{inline_markup(part)}</div>" for part in parts) + "</div>")
            else:
                output.append("<p>" + inline_markup(" ".join(parts)) + "</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            output.append(f"</{list_tag}>")
            list_tag = None

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph(); close_list()
            if in_code:
                output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear(); in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line); index += 1; continue
        if not stripped:
            flush_paragraph(); close_list(); index += 1; continue
        if index + 1 < len(lines) and "|" in line and TABLE_SEPARATOR_RE.match(lines[index + 1]):
            flush_paragraph(); close_list()
            headers = split_table_row(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(split_table_row(lines[index])); index += 1
            output.append('<div class="table-wrap"><table><thead><tr>' + "".join(f"<th>{inline_markup(cell)}</th>" for cell in headers) + "</tr></thead><tbody>")
            for row in rows:
                padded = row + [""] * max(0, len(headers) - len(row))
                output.append("<tr>" + "".join(f"<td>{inline_markup(cell)}</td>" for cell in padded[:len(headers)]) + "</tr>")
            output.append("</tbody></table></div>")
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph(); close_list()
            level = len(heading.group(1)); output.append(f"<h{level}>{inline_markup(heading.group(2))}</h{level}>")
            index += 1; continue
        if re.match(r"^([-*_])(?:\s*\1){2,}$", stripped):
            flush_paragraph(); close_list(); output.append("<hr>"); index += 1; continue
        if stripped.startswith(">"):
            flush_paragraph(); close_list()
            output.append("<blockquote>" + inline_markup(stripped[1:].strip()) + "</blockquote>")
            index += 1; continue
        item = re.match(r"^[-+*]\s+(.+)$", stripped)
        ordered = re.match(r"^\d+[.)]\s+(.+)$", stripped)
        if item or ordered:
            flush_paragraph()
            wanted = "ol" if ordered else "ul"
            if list_tag != wanted:
                close_list(); list_tag = wanted; output.append(f"<{wanted}>")
            content = (ordered or item).group(1)
            output.append(f"<li>{inline_markup(content)}</li>")
            index += 1; continue
        paragraph.append(stripped)
        index += 1

    flush_paragraph(); close_list()
    if in_code:
        output.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(output)


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            return re.sub(r"[*_`]", "", match.group(1)).strip()
    return fallback


def evidence_appendix(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    parts = ['<section class="evidence-index"><h2>证据索引</h2>', '<div class="table-wrap"><table><thead><tr><th>编号</th><th>实体</th><th>来源</th><th>等级</th><th>访问日期</th></tr></thead><tbody>']
    for row in rows:
        evidence_id = html.escape(row.get("evidence_id", "").strip())
        institution = html.escape(row.get("institution", "").strip())
        title = html.escape(row.get("source_title", "").strip())
        url = html.escape(row.get("source_url", "").strip(), quote=True)
        grade = html.escape(row.get("source_grade", "").strip())
        accessed = html.escape(row.get("accessed_date", "").strip())
        source = f'<a href="{url}">{title or url}</a>' if url else title
        parts.append(f'<tr id="evidence-{evidence_id}"><td>{evidence_id}</td><td>{institution}</td><td>{source}</td><td>{grade}</td><td>{accessed}</td></tr>')
    parts.append("</tbody></table></div></section>")
    return "\n".join(parts)


def render_document(markdown: str, title: str, evidence_rows: list[dict[str, str]] | None = None) -> str:
    body = markdown_to_html(markdown)
    appendix = evidence_appendix(evidence_rows or [])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{STYLE}</style>
</head>
<body><main>
{body}
{appendix}
<p class="meta">本报告由公考机构 GEO 调研 Skill v2.0 生成；请以报告中的观察日期、样本范围和证据链接为准。</p>
</main></body>
</html>
"""


def resolve_paths(source: Path, output: Path | None) -> tuple[Path, Path]:
    report_md = source / "report.md" if source.is_dir() else source
    report_html = output or report_md.with_name("report.html")
    return report_md, report_html


def self_test() -> None:
    sample = "# 示例报告\n\n观察日期：2026-09-09\n报告版本：2.0\n\n| 机构 | 分数 |\n|---|---:|\n| 甲机构 | 80 |\n\n结论 [E001]。\n"
    evidence = [{"evidence_id":"E001","institution":"甲机构","source_title":"来源","source_url":"https://example.com","source_grade":"A1","accessed_date":"2026-09-09"}]
    rendered = render_document(sample, "示例报告", evidence)
    required = ("<html lang=\"zh-CN\">", "<h1>示例报告</h1>", "<table>", "https://example.com", "Skill v2.0", 'class="machine-fields"', 'href="#evidence-E001"', 'id="evidence-E001"', "min-width:0")
    assert all(fragment in rendered for fragment in required)
    with tempfile.TemporaryDirectory(prefix="gongkao-geo-html-") as temp:
        run = Path(temp)
        (run / "report.md").write_text(sample, encoding="utf-8")
        with (run / "evidence.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(evidence[0])); writer.writeheader(); writer.writerows(evidence)
        report_md, report_html = resolve_paths(run, None)
        report_html.write_text(render_document(report_md.read_text(encoding="utf-8"), extract_title(sample, "报告"), evidence), encoding="utf-8")
        assert report_html.is_file() and report_html.stat().st_size > 500


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将 report.md 转为自包含的中文 report.html。")
    parser.add_argument("source", nargs="?", type=Path, help="运行目录或 report.md 路径")
    parser.add_argument("--output", type=Path, help="输出 HTML 路径；默认与 report.md 同目录")
    parser.add_argument("--title", help="覆盖 HTML 标题")
    parser.add_argument("--self-test", action="store_true", help="运行转换器自测")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        try:
            self_test()
        except AssertionError as exc:
            print(f"generate_report_html 自测：失败：{exc}", file=sys.stderr)
            return 2
        print("generate_report_html 自测：通过")
        return 0
    if args.source is None:
        build_parser().error("除使用 --self-test 外，必须提供运行目录或 report.md")
    report_md, report_html = resolve_paths(args.source, args.output)
    if not report_md.is_file():
        print(f"缺少输入文件：{report_md}", file=sys.stderr)
        return 1
    markdown = report_md.read_text(encoding="utf-8")
    title = args.title or extract_title(markdown, report_md.stem)
    evidence_rows: list[dict[str, str]] = []
    evidence_path = report_md.with_name("evidence.csv")
    if evidence_path.is_file():
        with evidence_path.open("r", encoding="utf-8-sig", newline="") as handle:
            evidence_rows = list(csv.DictReader(handle))
    report_html.write_text(render_document(markdown, title, evidence_rows), encoding="utf-8")
    print(f"已生成：{report_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
