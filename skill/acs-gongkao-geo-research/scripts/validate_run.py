#!/usr/bin/env python3
"""GEO v2.2 validator with stage-aware gates.

Stages:
- universe: Preflight + Market Universe draft/review only; Measurement files are not required.
- measurement: confirmed Universe + AI/SERP/recheck/metrics integrity; report files are not required.
- report/full: measurement checks + report_model + single DOCX delivery.
"""
from __future__ import annotations
import argparse,csv,json,re,zipfile
from collections import defaultdict
from dataclasses import dataclass,asdict
from pathlib import Path

TRUE={"1","true","yes","y","是"};FALSE={"0","false","no","n","否",""}
VERSION="2.2"
VALID_SCOPES={"national","regional","local","unknown"}
VALID_ROLES={"national-benchmark","local-core","local-active","expert-ip","historical","observation","unclassified"}
# v2.2 intentionally has no silent hard-exclusion state: Observation / unresolved remain measurable.
VALID_UNIVERSE={"included","observation","unresolved"}
VALID_CONFIRM={"needs-review","confirmed"}
VALID_TARGETS={"institution","ip"};VALID_MATCH={"explicit-name","verified-alias","citation-only"}
STAGES={"universe","measurement","report","full"}

@dataclass
class Issue:level:str;code:str;message:str;key:str=""

def rcsv(path:Path,issues,label,required=()):
    if not path.is_file():issues.append(Issue("error","missing-"+label,f"缺少 {path.name}"));return [],set()
    try:
        with path.open("r",encoding="utf-8-sig",newline="") as f:r=csv.DictReader(f);rows=list(r);fields=set(r.fieldnames or [])
    except Exception as e:issues.append(Issue("error","read-"+label,f"{path.name} 读取失败：{e}"));return [],set()
    miss=set(required)-fields
    if miss:issues.append(Issue("error",label+"-schema",f"{path.name} 缺字段：{', '.join(sorted(miss))}"))
    return rows,fields

def rjson(path:Path,issues,label,default=None):
    if not path.is_file():issues.append(Issue("error","missing-"+label,f"缺少 {path.name}"));return {} if default is None else default
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:issues.append(Issue("error","invalid-"+label,f"{path.name} JSON 无效：{e}"));return {} if default is None else default

def rjsonl(path:Path,issues,label):
    if not path.is_file():issues.append(Issue("error","missing-"+label,f"缺少 {path.name}"));return []
    out=[]
    try:
        for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
            if line.strip():obj=json.loads(line);obj["_line"]=n;out.append(obj)
    except Exception as e:issues.append(Issue("error","invalid-"+label,f"{path.name} JSONL 无效：{e}"))
    return out

def num(v):
    try:return float(v)
    except:return None
def norm(s):return re.sub(r"\s+","",str(s or "").lower())
def truth(v):return str(v or "").strip().lower() in TRUE

def validate_universe(run:Path,meta:dict,issues:list[Issue],require_confirmed:bool):
    ureq={"entity_id","canonical_name","aliases","entity_type","user_seed","discovery_origin","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","universe_status","confirmation_status","notes"}
    universe,_=rcsv(run/"market_universe.csv",issues,"market-universe",ureq)
    review=rjson(run/"universe_review.json",issues,"universe-review")
    ids=set();names=set();seeds=[str(x).strip() for x in meta.get("seed_entities",[]) if str(x).strip()];seed_names={norm(x) for x in seeds};seen_seed=set()
    by_name={}
    for i,r in enumerate(universe,2):
        eid=(r.get("entity_id") or "").strip();name=(r.get("canonical_name") or "").strip();by_name[name]=r
        if not eid or eid in ids:issues.append(Issue("error","universe-id",f"market_universe 第{i}行 entity_id 重复或为空"))
        else:ids.add(eid)
        if not name:issues.append(Issue("error","universe-name",f"{eid or i} canonical_name 为空"))
        elif name in names:issues.append(Issue("error","universe-name-duplicate",f"canonical_name 重复：{name}"))
        names.add(name)
        if r.get("market_scope") not in VALID_SCOPES:issues.append(Issue("error","market-scope",f"{name} market_scope 无效"))
        if r.get("market_role") not in VALID_ROLES:issues.append(Issue("error","market-role",f"{name} market_role 无效"))
        if r.get("universe_status") not in VALID_UNIVERSE:issues.append(Issue("error","universe-status",f"{name} universe_status 无效；v2.2 仅允许 included/observation/unresolved"))
        if r.get("confirmation_status") not in VALID_CONFIRM:issues.append(Issue("error","confirmation-status",f"{name} confirmation_status 无效"))
        if require_confirmed and r.get("confirmation_status")!="confirmed":issues.append(Issue("error","universe-row-unconfirmed",f"{name} 尚未 confirmation_status=confirmed"))
        if r.get("market_role") in {"local-core","local-active"} and r.get("market_scope") not in {"local","regional"}:issues.append(Issue("error","local-role-without-scope",f"{name} 被标为本土角色，但 market_scope={r.get('market_scope')}"))
        if r.get("universe_status")=="included" and r.get("market_role") in {"national-benchmark","local-core","local-active","expert-ip","historical"} and not (r.get("salience_basis") or "").strip():issues.append(Issue("error","included-without-basis",f"{name} 已纳入正式研究但缺 salience_basis"))
        if truth(r.get("user_seed")):
            seen_seed.add(norm(name));seen_seed.update(norm(x) for x in (r.get("aliases") or "").split("|") if x)
    missing=sorted(x for x in seed_names if x not in seen_seed)
    if missing:issues.append(Issue("error","seed-disappeared",f"用户 Seed 未进入 Market Universe：{', '.join(missing)}"))

    if review:
        if str(review.get("schema_version"))!=VERSION:issues.append(Issue("error","review-version","universe_review.schema_version 必须为 2.2"))
        if review.get("total_entities")!=len(universe):issues.append(Issue("error","review-total-mismatch",f"universe_review total_entities={review.get('total_entities')}，CSV={len(universe)}"))
        expected_system=sum(
            (not truth(r.get("user_seed"))) and ("system-discovery" in (r.get("discovery_origin") or "") or "platform-native" in (r.get("discovery_origin") or ""))
            for r in universe
        )
        if review.get("system_discovery_count")!=expected_system:issues.append(Issue("error","review-system-discovery-count",f"system_discovery_count={review.get('system_discovery_count')}，应为非 Seed 系统发现主体 {expected_system}"))
        if review.get("platform_native_count") is not None:
            expected_platform=sum(truth(r.get("platform_native")) for r in universe)
            if review.get("platform_native_count")!=expected_platform:issues.append(Issue("error","review-platform-count",f"platform_native_count={review.get('platform_native_count')}，CSV={expected_platform}"))
        if review.get("expert_ip_included_count") is not None:
            expected_ip=sum(r.get("universe_status")=="included" and r.get("market_role")=="expert-ip" for r in universe)
            if review.get("expert_ip_included_count")!=expected_ip:issues.append(Issue("error","review-expert-ip-count",f"expert_ip_included_count={review.get('expert_ip_included_count')}，CSV={expected_ip}"))
        buckets=review.get("buckets") or {}
        expected_keys={"A_national_benchmarks","B_local_regional","C_expert_ip","D_observation_or_other"}
        if set(buckets)!=expected_keys:issues.append(Issue("error","review-bucket-schema",f"Universe Review buckets 必须精确为：{', '.join(sorted(expected_keys))}"))
        flat=[]
        for k in expected_keys:flat += list(buckets.get(k) or [])
        dup=sorted({x for x in flat if flat.count(x)>1})
        if dup:issues.append(Issue("error","review-bucket-overlap",f"Universe Review 分桶重叠：{', '.join(dup)}"))
        if set(flat)!=set(by_name):
            miss=sorted(set(by_name)-set(flat));extra=sorted(set(flat)-set(by_name))
            issues.append(Issue("error","review-bucket-coverage",f"Universe Review 分桶未与 market_universe 一一覆盖；missing={miss}, extra={extra}"))
        for name in buckets.get("A_national_benchmarks",[]):
            r=by_name.get(name,{})
            if r.get("universe_status")!="included" or r.get("market_role")!="national-benchmark":issues.append(Issue("error","review-bucket-A",f"{name} 不满足 A 桶条件"))
        for name in buckets.get("B_local_regional",[]):
            r=by_name.get(name,{})
            if r.get("universe_status")!="included" or r.get("market_role") not in {"local-core","local-active"} or r.get("market_scope") not in {"local","regional"}:issues.append(Issue("error","review-bucket-B",f"{name} 不满足 B 桶条件"))
        for name in buckets.get("C_expert_ip",[]):
            r=by_name.get(name,{})
            if r.get("universe_status")!="included" or r.get("market_role")!="expert-ip":issues.append(Issue("error","review-bucket-C",f"{name} 不满足 C 桶条件"))
        if len(buckets.get("A_national_benchmarks",[]))>8:issues.append(Issue("warning","benchmark-sprawl","全国 Benchmark 超过 8 家；Benchmark 应是代表性基准，不应等于所有在本地有网点的全国品牌"))
    return universe,ids

def validate_measurement(run:Path,meta:dict,issues:list[Issue],ids:set,mode:str):
    qreq={"query_id","query_text","query_group","measurement_target","region","status"}
    mreq={"mention_id","answer_id","entity_id","mention_rank","mentioned_name","match_method","top3","first_mention","entity_correct","citation_linked","concepts","notes"}
    sreq={"result_id","query_id","engine","rank","url","title","snippet","sampled_at"}
    smreq={"serp_mention_id","result_id","entity_id","matched_text","match_surface","notes"}
    pmreq={"page_mention_id","result_id","entity_id","matched_text","page_url","notes"}
    ereq={"evidence_id","entity_id","source_url","source_title","source_grade","source_owner","claim_type","counting_scope","notes"}
    rreq={"recheck_id","sample_type","source_id","first_decision","second_decision","disagreement","resolution","recheck_by","notes"}
    xreq={"entity_id","canonical_name","aliases","measurement_target","market_scope","operating_region","resolution_status","source_answer_ids","notes"}

    queries,_=rcsv(run/"queries.csv",issues,"queries",qreq)
    answers=rjsonl(run/"ai_answers.jsonl",issues,"ai-answers")
    mentions,_=rcsv(run/"ai_mentions.csv",issues,"ai-mentions",mreq)
    serp,_=rcsv(run/"serp_results.csv",issues,"serp-results",sreq)
    serp_mentions,_=rcsv(run/"serp_mentions.csv",issues,"serp-mentions",smreq)
    page_mentions,_=rcsv(run/"page_mentions.csv",issues,"page-mentions",pmreq)
    rcsv(run/"evidence.csv",issues,"evidence",ereq)
    rechecks,_=rcsv(run/"rechecks.csv",issues,"rechecks",rreq)
    metrics,_=rcsv(run/"ai_metrics.csv",issues,"ai-metrics",{"entity_id","nomination_rate","top3_rate","first_mention_rate","citation_rate","answer_cells","engines_sampled","engine_coverage_rate","cross_model_consistency"})
    emergent,_=rcsv(run/"ai_emergent_entities.csv",issues,"ai-emergent-entities",xreq)

    qmap={q.get("query_id"):q for q in queries};answer_ids=set();answers_by_query=defaultdict(list)
    for a in answers:
        aid=str(a.get("answer_id","")).strip();qid=str(a.get("query_id","")).strip()
        if not aid or aid in answer_ids:issues.append(Issue("error","answer-id",f"ai_answers 行 {a.get('_line')} answer_id 重复/为空"));continue
        answer_ids.add(aid)
        if qid not in qmap:issues.append(Issue("error","answer-query",f"{aid} 引用不存在 query_id {qid}"));continue
        if qmap[qid].get("measurement_target") not in VALID_TARGETS:issues.append(Issue("error","measurement-target",f"{qid} measurement_target 必须 institution/ip"))
        if not str(a.get("response_text","")).strip():issues.append(Issue("error","empty-answer",f"{aid} 缺原始 response_text"))
        answers_by_query[qid].append(a)
    if mode=="scoped-geo-landscape" and not answers:issues.append(Issue("error","no-ai-measurement","正式 GEO Landscape 必须有 AI Answer Measurement；否则只能做 Asset Audit"))

    declared=set(meta.get("ai_engines_expected") or [])
    if declared:
        for q in queries:
            if q.get("status")=="sampled" and q.get("measurement_target") in VALID_TARGETS:
                qeng={str(a.get("engine","")).strip() for a in answers_by_query.get(q.get("query_id"),[])};miss=declared-qeng
                if miss:issues.append(Issue("error","engine-coverage",f"{q.get('query_id')} 缺 AI 引擎采样：{', '.join(sorted(miss))}"))

    amap={a.get("answer_id"):a for a in answers}
    emergent_ids=set();resolved_emergent=set()
    for i,e in enumerate(emergent,2):
        eid=(e.get("entity_id") or "").strip();name=(e.get("canonical_name") or "").strip()
        if not eid or eid in ids or eid in emergent_ids:issues.append(Issue("error","emergent-id",f"ai_emergent_entities 第{i}行 entity_id 为空或与现有主体冲突：{eid}"))
        else:emergent_ids.add(eid)
        if not name:issues.append(Issue("error","emergent-name",f"{eid or i} canonical_name 为空"))
        if e.get("measurement_target") not in VALID_TARGETS:issues.append(Issue("error","emergent-target",f"{name} measurement_target 必须 institution/ip"))
        if e.get("market_scope") not in VALID_SCOPES:issues.append(Issue("error","emergent-scope",f"{name} market_scope 无效"))
        if e.get("resolution_status") not in {"resolved","unresolved"}:issues.append(Issue("error","emergent-resolution",f"{name} resolution_status 必须 resolved/unresolved"))
        src=[x for x in (e.get("source_answer_ids") or "").split("|") if x]
        if not src:issues.append(Issue("error","emergent-source",f"{name} 缺 source_answer_ids"))
        missing_src=[x for x in src if x not in answer_ids]
        if missing_src:issues.append(Issue("error","emergent-source",f"{name} 引用不存在 answer_id：{', '.join(missing_src)}"))
        if e.get("resolution_status")=="resolved":
            resolved_emergent.add(eid)
            needles=[name]+[x for x in (e.get("aliases") or "").split("|") if x]
            if src and not any(any(norm(n) and norm(n) in norm(amap[s].get("response_text","")) for n in needles) for s in src if s in amap):
                issues.append(Issue("error","emergent-not-in-answer",f"{name} 在 source_answer_ids 的原始回答中未找到 canonical/alias"))

    valid_entity_ids=ids|resolved_emergent
    mention_pairs=set();rank_keys=set();eligible_by_answer=defaultdict(list)
    for m in mentions:
        aid=m.get("answer_id");eid=m.get("entity_id");pair=(aid,eid)
        if aid not in amap:issues.append(Issue("error","mention-answer",f"{m.get('mention_id')} 引用不存在 answer_id"));continue
        if eid in emergent_ids and eid not in resolved_emergent:issues.append(Issue("error","mention-unresolved-emergent",f"{m.get('mention_id')} 引用尚未解析的 AI-emergent 主体 {eid}"));continue
        if eid not in valid_entity_ids:issues.append(Issue("error","mention-entity",f"{m.get('mention_id')} 引用不存在 entity_id；若为 AI 新出现主体，先写 ai_emergent_entities.csv"));continue
        if pair in mention_pairs:issues.append(Issue("error","duplicate-answer-entity-mention",f"同一 answer/entity 重复计提：{aid}/{eid}"))
        mention_pairs.add(pair)
        method=m.get("match_method")
        if method not in VALID_MATCH:issues.append(Issue("error","match-method",f"{m.get('mention_id')} match_method 无效"))
        if method in {"explicit-name","verified-alias"}:
            needle=norm(m.get("mentioned_name"));text=norm(amap[aid].get("response_text"))
            if not needle or needle not in text:issues.append(Issue("error","mention-not-in-answer",f"{m.get('mention_id')} 的 mentioned_name 未出现在原始回答"))
            rank=num(m.get("mention_rank"))
            if rank is None or rank<1:issues.append(Issue("error","mention-rank",f"{m.get('mention_id')} mention_rank 无效"))
            else:
                rk=(aid,rank)
                if rk in rank_keys:issues.append(Issue("error","mention-rank-duplicate",f"{aid} 出现重复 mention_rank={rank:g}"))
                rank_keys.add(rk);eligible_by_answer[aid].append(m)
                if truth(m.get("top3")) != (rank<=3):issues.append(Issue("error","top3-rank-mismatch",f"{m.get('mention_id')} top3 与 mention_rank={rank:g} 不一致"))
        if m.get("entity_correct","").lower() not in TRUE:issues.append(Issue("warning","entity-correctness",f"{m.get('mention_id')} 未确认实体正确，不应进入正式提名统计"))

    for aid,ms in eligible_by_answer.items():
        ranks=[num(m.get("mention_rank")) for m in ms];ranks=[r for r in ranks if r is not None]
        if not ranks:continue
        first=min(ranks)
        for m in ms:
            rank=num(m.get("mention_rank"))
            if truth(m.get("first_mention")) != (rank==first):issues.append(Issue("error","first-rank-mismatch",f"{m.get('mention_id')} first_mention 与该回答最小 mention_rank={first:g} 不一致"))

    result_ids=set();rank_keys=set();rmap={}
    for r in serp:
        rid=r.get("result_id");key=(r.get("query_id"),r.get("engine"),r.get("rank"))
        if rid in result_ids:issues.append(Issue("error","serp-result-id",f"serp_results result_id 重复：{rid}"))
        result_ids.add(rid);rmap[rid]=r
        if key in rank_keys:issues.append(Issue("error","serp-rank-duplicate",f"同一 query/engine/rank 只能有一个真实 Result Item：{key}"))
        rank_keys.add(key)
        if not r.get("title") and not r.get("snippet"):issues.append(Issue("error","serp-no-surface",f"{rid} title/snippet 均为空"))
    for m in serp_mentions:
        rid=m.get("result_id");surface=m.get("match_surface")
        if rid not in rmap:issues.append(Issue("error","serp-mention-result",f"{m.get('serp_mention_id')} 引用不存在 result_id"));continue
        if m.get("entity_id") not in ids:issues.append(Issue("error","serp-mention-entity",f"{m.get('serp_mention_id')} 引用不存在 Market Universe entity_id"))
        if surface not in {"title","snippet","both"}:issues.append(Issue("error","serp-match-surface",f"{m.get('serp_mention_id')} match_surface 必须 title/snippet/both"));continue
        text=(rmap[rid].get("title","") if surface in {"title","both"} else "")+(rmap[rid].get("snippet","") if surface in {"snippet","both"} else "")
        if norm(m.get("matched_text")) not in norm(text):issues.append(Issue("error","serp-mention-not-visible",f"{m.get('serp_mention_id')} matched_text 不在 title/snippet；网页正文提及必须写 page_mentions.csv"))
    for p in page_mentions:
        if p.get("result_id") and p.get("result_id") not in rmap:issues.append(Issue("error","page-mention-result",f"{p.get('page_mention_id')} 引用不存在 result_id"))

    ai_rechecks=[r for r in rechecks if r.get("sample_type")=="ai-answer" and r.get("source_id") in answer_ids]
    if len(answers)>=10:
        coverage=len({r.get("source_id") for r in ai_rechecks})/len(answers)
        if coverage<0.20:issues.append(Issue("error","recheck-coverage",f"AI Answer 复判覆盖仅 {coverage:.1%}，最低要求 20%"))
    for r in ai_rechecks:
        if truth(r.get("disagreement")) and not r.get("resolution","").strip():issues.append(Issue("error","unresolved-recheck",f"{r.get('recheck_id')} 存在分歧但无 resolution"))
    return metrics,emergent

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
    resolved_emergent={r.get("entity_id") for r in emergent if r.get("resolution_status")=="resolved"}
    rendered_emergent={r.get("entity_id") for r in (model.get("ai_visible_emergent") or [])}
    visible_resolved={eid for eid in resolved_emergent if num((mm.get(eid) or {}).get("nomination_rate")) and num((mm.get(eid) or {}).get("nomination_rate"))>0}
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

def validate(run:Path,strict=False,stage="full"):
    issues=[]
    if stage not in STAGES:return [Issue("error","invalid-stage",f"stage 必须是 {', '.join(sorted(STAGES))}")]
    if not run.is_dir():return [Issue("error","missing-run-dir",f"不是目录：{run}")]
    meta=rjson(run/"run_metadata.json",issues,"run-metadata")
    if str(meta.get("schema_version"))!=VERSION or str(meta.get("skill_version"))!=VERSION:issues.append(Issue("error","version","run_metadata schema_version / skill_version 必须为 2.2"))
    if meta.get("official_output_format")!="docx":issues.append(Issue("error","output-contract","v2.2 唯一正式输出必须是 docx"))
    for k in ("region_confirmed","seed_entities_confirmed","discovery_supplement_confirmed"):
        if meta.get(k) is not True:issues.append(Issue("error","preflight-incomplete",f"Preflight 未确认：{k}",k))
    mode=meta.get("research_mode");seeds=[str(x).strip() for x in meta.get("seed_entities",[]) if str(x).strip()]
    if mode=="scoped-geo-landscape" and not seeds:issues.append(Issue("error","seed-required","scoped-geo-landscape 必须至少有一个用户 Seed"))
    if mode not in {"scoped-geo-landscape","blind-discovery-scan"}:issues.append(Issue("error","research-mode","research_mode 无效"))
    require_confirmed=stage in {"measurement","report","full"}
    if require_confirmed:
        if meta.get("market_universe_confirmed") is not True:issues.append(Issue("error","universe-not-confirmed","Market Universe 未经用户确认，不得进入正式 Measurement"))
        if meta.get("measurement_allowed") is not True:issues.append(Issue("error","measurement-not-authorized","measurement_allowed 必须为 true"))
    universe,ids=validate_universe(run,meta,issues,require_confirmed)
    metrics=[];emergent=[]
    if stage in {"measurement","report","full"}:metrics,emergent=validate_measurement(run,meta,issues,ids,mode)
    if stage in {"report","full"}:validate_report(run,issues,universe,metrics,emergent)
    return issues

def main():
    p=argparse.ArgumentParser();p.add_argument("run_dir",nargs="?",type=Path);p.add_argument("--strict",action="store_true");p.add_argument("--json",action="store_true");p.add_argument("--stage",choices=sorted(STAGES),default="full");a=p.parse_args()
    if not a.run_dir:p.error("必须提供 run_dir")
    issues=validate(a.run_dir,a.strict,a.stage);errors=sum(x.level=="error" for x in issues);warnings=sum(x.level=="warning" for x in issues)
    if a.json:print(json.dumps({"stage":a.stage,"errors":errors,"warnings":warnings,"issues":[asdict(x) for x in issues]},ensure_ascii=False,indent=2))
    else:
        for x in issues:print(f"{x.level.upper()} [{x.code}] {x.message}")
        print(f"校验摘要（stage={a.stage}）：{errors} 个错误，{warnings} 个警告")
    return 1 if errors or (a.strict and warnings) else 0
if __name__=="__main__":raise SystemExit(main())
