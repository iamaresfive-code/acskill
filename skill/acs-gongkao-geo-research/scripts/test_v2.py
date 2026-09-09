#!/usr/bin/env python3
"""v2.0 行为回归：验证召回、计数隔离、实体治理和报告一致性。"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = load_module("validate_run_v2", HERE / "validate_run.py")
scorer = load_module("score_geo_v2", HERE / "score_geo.py")
resolver = load_module("resolve_entities_v2", HERE / "resolve_entities.py")
generator = load_module("generate_report_html_v2", HERE / "generate_report_html.py")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_valid_run(run: Path) -> None:
    qf = sorted(validator.QUERY_FIELDS_V2)
    queries = [
        {"query_id":"QD1","query_text":"示例省公考机构有哪些","query_type":"generic","query_purpose":"discovery","discovery_channel":"user-query","discovery_round":1,"theme":"发现","region":"示例省","city":"","exam":"省考","sampled_channel":"public-web","sampled_at":"2026-09-09T10:00:00+08:00","status":"sampled","notes":""},
        {"query_id":"QD2","query_text":"示例省事业单位培训机构","query_type":"generic","query_purpose":"discovery","discovery_channel":"exam-vertical","discovery_round":1,"theme":"考试","region":"示例省","city":"","exam":"事业单位","sampled_channel":"public-web","sampled_at":"2026-09-09T10:01:00+08:00","status":"sampled","notes":""},
        {"query_id":"QD3","query_text":"site:gov.cn 示例省 公考 培训","query_type":"generic","query_purpose":"discovery","discovery_channel":"institutional","discovery_round":2,"theme":"机构性来源","region":"示例省","city":"","exam":"省考","sampled_channel":"public-web","sampled_at":"2026-09-09T10:02:00+08:00","status":"sampled","notes":""},
        {"query_id":"QD4","query_text":"示例教育 公司名 简称","query_type":"brand","query_purpose":"discovery","discovery_channel":"entity-alias","discovery_round":2,"theme":"别名","region":"示例省","city":"","exam":"省考","sampled_channel":"public-web","sampled_at":"2026-09-09T10:03:00+08:00","status":"sampled","notes":""},
        {"query_id":"QM1","query_text":"示例省公务员笔试培训机构","query_type":"generic","query_purpose":"measurement","discovery_channel":"","discovery_round":"","theme":"笔试","region":"示例省","city":"","exam":"省考","sampled_channel":"public-web","sampled_at":"2026-09-09T10:04:00+08:00","status":"sampled","notes":""},
        {"query_id":"QM2","query_text":"示例省公务员面试培训机构","query_type":"generic","query_purpose":"measurement","discovery_channel":"","discovery_round":"","theme":"面试","region":"示例省","city":"","exam":"省考","sampled_channel":"public-web","sampled_at":"2026-09-09T10:05:00+08:00","status":"sampled","notes":""},
        {"query_id":"QV1","query_text":"示例教育官网和老师","query_type":"brand","query_purpose":"verification","discovery_channel":"","discovery_round":"","theme":"实体","region":"示例省","city":"","exam":"省考","sampled_channel":"public-web","sampled_at":"2026-09-09T10:06:00+08:00","status":"sampled","notes":""},
    ]
    write_csv(run/"queries.csv", qf, queries)
    rf=sorted(validator.RESULT_FIELDS_V2)
    results=[
        {"result_id":"R1","query_id":"QD1","entity_id":"I001","result_rank":1,"source_url":"https://example.com/discovery","source_title":"发现页","matched_name":"示例教育","observed_at":"2026-09-09T10:00:00+08:00","channel":"public-web","matched":"true","counts_as_measurement_hit":"false","notes":""},
        {"result_id":"R2","query_id":"QD3","entity_id":"T001","result_rank":1,"source_url":"https://gov.example.org/event","source_title":"活动页","matched_name":"示例老师","observed_at":"2026-09-09T10:02:00+08:00","channel":"public-web","matched":"true","counts_as_measurement_hit":"false","notes":""},
        {"result_id":"R3","query_id":"QM1","entity_id":"I001","result_rank":2,"source_url":"https://result.example.net/list","source_title":"测量结果","matched_name":"示例教育","observed_at":"2026-09-09T10:04:00+08:00","channel":"public-web","matched":"true","counts_as_measurement_hit":"true","notes":""},
        {"result_id":"R4","query_id":"QV1","entity_id":"I001","result_rank":1,"source_url":"https://example.com/about","source_title":"官网","matched_name":"示例教育","observed_at":"2026-09-09T10:06:00+08:00","channel":"public-web","matched":"true","counts_as_measurement_hit":"false","notes":""},
    ]
    write_csv(run/"query_results.csv",rf,results)
    ef=sorted(validator.ENTITY_FIELDS_V2)
    entities=[
        {"entity_id":"I001","canonical_name":"示例教育","entity_type":"institution","aliases":"示例公考教育","legal_name":"示例教育科技有限公司","former_names":"","official_domain":"example.com","region":"示例省","parent_entity_id":"","entity_status":"active","disambiguation_notes":"已排除同名示例学校","source_ids":"E001|E002","notes":""},
        {"entity_id":"T001","canonical_name":"示例老师","entity_type":"teacher","aliases":"","legal_name":"","former_names":"","official_domain":"","region":"示例省","parent_entity_id":"","entity_status":"active","disambiguation_notes":"","source_ids":"E001","notes":""},
    ]
    write_csv(run/"entities.csv",ef,entities)
    cf=sorted(validator.CANDIDATE_FIELDS_V2)
    candidates=[
        {"candidate_id":"C001","entity_id":"I001","display_name":"示例教育","candidate_type":"institution","discovery_round":1,"discovery_channel":"user-query","discovery_query_id":"QD1","discovery_result_id":"R1","first_seen_at":"2026-09-09T10:00:00+08:00","evidence_strength":"medium","status":"scored","merged_into_entity_id":"","exclusion_reason":"","notes":""},
        {"candidate_id":"C002","entity_id":"T001","display_name":"示例老师","candidate_type":"teacher","discovery_round":2,"discovery_channel":"institutional","discovery_query_id":"QD3","discovery_result_id":"R2","first_seen_at":"2026-09-09T10:02:00+08:00","evidence_strength":"medium","status":"evidence-insufficient","merged_into_entity_id":"","exclusion_reason":"","notes":""},
    ]
    write_csv(run/"candidate_pool.csv",cf,candidates)
    evf=sorted(validator.EVIDENCE_FIELDS_V2)
    evidence=[
        {"evidence_id":"E001","entity_id":"I001","institution":"示例教育","query_id":"QV1","query":"示例教育官网和老师","query_type":"brand","source_title":"示例教育官网","source_url":"https://example.com/about","source_domain":"example.com","published_date":"2026-08-01","accessed_date":"2026-09-09","source_grade":"A2","independent":"false","claim_type":"institution-claim","concepts":"[\"课程\"]","duplicate_group":"","duplicate_reason":"","review_status":"","counting_scope":"entity","notes":""},
        {"evidence_id":"E002","entity_id":"I001","institution":"示例教育","query_id":"QD3","query":"site:gov.cn 示例省 公考 培训","query_type":"generic","source_title":"示例活动","source_url":"https://gov.example.org/event","source_domain":"gov.example.org","published_date":"2026-07-01","accessed_date":"2026-09-09","source_grade":"A1","independent":"true","claim_type":"fact","concepts":"[\"活动\"]","duplicate_group":"","duplicate_reason":"","review_status":"","counting_scope":"entity","notes":"只支持该次活动"},
    ]
    write_csv(run/"evidence.csv",evf,evidence)
    relf=sorted(validator.RELATION_FIELDS_V2)
    write_csv(run/"entity_relations.csv",relf,[{"relation_id":"REL1","source_entity_id":"T001","relation_type":"teaches-at","target_entity_id":"I001","relation_status":"current","valid_from":"2026","valid_to":"","evidence_ids":"E001","confidence":"Medium","notes":"机构官方页面"}])
    ipf=sorted(validator.IP_FIELDS)
    write_csv(run/"ip_entities.csv",ipf,[{"teacher_name":"示例老师","aliases":"","institution":"示例教育","relation_status":"current","relation_period":"2026","subjects":"申论","products":"示例课","regions":"示例省","platforms":"官网","generic_hits":0,"brand_hits":1,"concepts":"申论","source_ids":"E001","evidence_confidence":"Medium","notes":""}])
    sf=sorted(validator.SCORE_FIELDS_V2)
    write_csv(run/"scores.csv",sf,[{"institution":"示例教育","entity_id":"I001","inclusion_basis":"discovered","query_coverage":18,"entity_clarity":18,"external_diversity":10,"concept_ownership":8,"freshness":7,"total":61,"tier":"B+","evidence_confidence":"Medium","generic_hits":1,"generic_queries":2,"brand_hits":1,"evidence_count":2,"independent_domains":1,"notes":""}])
    dims={"query_coverage":{"score":18,"reason":"1/2题命中","query_ids":["QM1"]},"entity_clarity":{"score":18,"reason":"主体与老师可确认","evidence_ids":["E001"]},"external_diversity":{"score":10,"reason":"一个独立域名","evidence_ids":["E002"]},"concept_ownership":{"score":8,"reason":"申论关联可确认","evidence_ids":["E001"]},"freshness":{"score":7,"reason":"近90天有内容","evidence_ids":["E001"]}}
    (run/"score_details.json").write_text(json.dumps([{"entity_id":"I001","dimensions":dims}],ensure_ascii=False,indent=2),encoding="utf-8")
    report="""# 示例省公考机构 GEO 调研

Schema版本：2.0
Skill版本：2.0
观察日期：2026-09-09
研究模式：地区全景（regional-landscape）
研究范围：示例省
采样模式：公开网页代理观察
Discovery问题数：4
Measurement问题数：2
Verification问题数：1
Discovery渠道覆盖：user-query|exam-vertical|institutional|entity-alias
漏项审计轮数：2
候选记录数：2
第一轮候选实体数：1
第二轮新增实体数：1
去重后实体数：2
正式评分数：1
待观察/证据不足数：1
证据数：2
IP名师调查：是
IP名师样本数：1
自有机构纳入：否
第二轮新增占比说明：第二轮新增率较高；本夹具用于门禁验证，非真实研究交付。
免责声明：GEO 观察指数不代表教学实力、市场份额或大模型官方推荐排名。

## 结论

示例教育主体可由官网核验 [E001]，一次公开活动由独立来源确认 [E002]。
"""
    (run/"report.md").write_text(report,encoding="utf-8")
    (run/"report.html").write_text(generator.render_document(report,"示例省公考机构 GEO 调研",evidence),encoding="utf-8")


def codes(run: Path) -> set[str]:
    return {issue.code for issue in validator.validate_run(run) if issue.level in {"error","warning"}}


def main() -> int:
    passed=[]
    with tempfile.TemporaryDirectory(prefix="geo-v2-tests-") as temp:
        base=Path(temp); build_valid_run(base)
        assert not codes(base); passed.append("01-valid-v2")

        rows=read_csv(base/"query_results.csv"); rows[0]["counts_as_measurement_hit"]="true"; write_csv(base/"query_results.csv",list(rows[0]),rows)
        assert "measurement-isolation" in codes(base); passed.append("02-discovery-isolation")
        build_valid_run(base); rows=read_csv(base/"query_results.csv"); rows[-1]["counts_as_measurement_hit"]="true"; write_csv(base/"query_results.csv",list(rows[0]),rows)
        assert "measurement-isolation" in codes(base); passed.append("03-verification-isolation")

        build_valid_run(base); rows=read_csv(base/"queries.csv"); rows=[r for r in rows if r["discovery_round"]!="2"]; write_csv(base/"queries.csv",list(rows[0]),rows)
        assert "missing-discovery-round" in codes(base); passed.append("04-two-round-gate")
        build_valid_run(base); rows=read_csv(base/"scores.csv"); rows[0]["entity_id"]="I999"; write_csv(base/"scores.csv",list(rows[0]),rows)
        assert "score-entity-missing" in codes(base); passed.append("05-score-entity-integrity")
        build_valid_run(base); rows=read_csv(base/"candidate_pool.csv"); rows[0]["status"]="eligible"; write_csv(base/"candidate_pool.csv",list(rows[0]),rows)
        assert "unfinished-candidate-status" in codes(base); passed.append("06-final-candidate-state")

        fixture=json.loads((HERE.parent/"tests/fixtures/tianjin-entity-cases.json").read_text(encoding="utf-8")); index=resolver.build_alias_index(fixture["entities"])
        for case in fixture["cases"]:
            got=resolver.resolve_name(case["input"],index); assert got["status"]==case["status"]
            if "entity_id" in case: assert got["entity_id"]==case["entity_id"]
        passed.append("07-tianjin-alias-and-anti-overfit")

        build_valid_run(base); rows=read_csv(base/"entities.csv"); rows[0]["aliases"]="示例"; rows[0]["disambiguation_notes"]=""; write_csv(base/"entities.csv",list(rows[0]),rows)
        assert "missing-short-alias-disambiguation" in codes(base); passed.append("08-short-alias-disambiguation")
        build_valid_run(base); text=(base/"report.md").read_text(encoding="utf-8").replace("第二轮新增占比说明：第二轮新增率较高；本夹具用于门禁验证，非真实研究交付。\n",""); (base/"report.md").write_text(text,encoding="utf-8")
        assert "candidate-saturation" in codes(base); passed.append("09-saturation-warning")
        build_valid_run(base); text=(base/"report.md").read_text(encoding="utf-8").replace("证据数：2","证据数：9"); (base/"report.md").write_text(text,encoding="utf-8")
        assert "report-count-mismatch" in codes(base); passed.append("10-report-count-consistency")

        result=scorer.score_record({"query_coverage":24,"entity_clarity":20,"external_diversity":13,"concept_ownership":11,"freshness":8}); assert result["total"]==76 and result["tier"]=="A"; passed.append("11-score-backward-stability")
        build_valid_run(base); rows=read_csv(base/"scores.csv"); rows[0]["inclusion_basis"]="owned-forced"; write_csv(base/"scores.csv",list(rows[0]),rows)
        assert "unexpected-owned-forced" in codes(base); passed.append("12-owned-inclusion-gate")
        build_valid_run(base); rows=read_csv(base/"scores.csv"); rows[0]["inclusion_basis"]="discovered"; write_csv(base/"scores.csv",list(rows[0]),rows); text=(base/"report.md").read_text(encoding="utf-8").replace("地区全景（regional-landscape）","单主体深挖（institution-deep-dive）"); (base/"report.md").write_text(text,encoding="utf-8")
        assert "specified-mode-expanded" in codes(base); passed.append("13-specified-mode-no-expansion")

        build_valid_run(base); rows=read_csv(base/"query_results.csv"); rows[2]["matched"]="false"; rows[2]["counts_as_measurement_hit"]="false"; write_csv(base/"query_results.csv",list(rows[0]),rows)
        assert "generic-hit-mismatch" in codes(base); passed.append("14-query-log-derived-metrics")

    print(f"v2 行为测试：通过 {len(passed)} 项")
    for item in passed: print("- "+item)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
