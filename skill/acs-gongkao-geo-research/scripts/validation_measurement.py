#!/usr/bin/env python3
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from validation_common import *

def validate_measurement(run:Path,meta:dict,issues:list[Issue],ids:set,mode:str):
    qreq={"query_id","query_text","query_group","measurement_target","region","status"}
    mreq={"mention_id","answer_id","entity_id","mention_rank","nomination_rank","mentioned_name","match_method","resolution_status","mention_intent","top3","first_mention","entity_correct","citation_linked","citation_refs","concepts","notes"}
    sreq={"result_id","query_id","engine","rank","url","title","snippet","sampled_at"}
    smreq={"serp_mention_id","result_id","entity_id","matched_text","match_surface","notes"}
    pmreq={"page_mention_id","result_id","entity_id","matched_text","page_url","notes"}
    ereq={"evidence_id","entity_id","source_url","source_title","source_grade","source_owner","claim_type","counting_scope","notes"}
    rreq={"recheck_id","sample_type","source_id","first_decision","second_decision","disagreement","resolution","recheck_by","notes"}
    xreq={"entity_id","canonical_name","aliases","measurement_target","market_scope","operating_region","resolution_status","source_answer_ids","source_result_ids","notes"}
    areq={"review_id","answer_id","first_positive_set","second_positive_set","first_intents","second_intents","disagreement","resolution","reviewer","notes"}
    universe,_=rcsv(run/"market_universe.csv",issues,"market-universe-measurement",{"entity_id","canonical_name","measurement_target","universe_status"})
    queries,_=rcsv(run/"queries.csv",issues,"queries",qreq)
    answers=rjsonl(run/"ai_answers.jsonl",issues,"ai-answers")
    mentions,_=rcsv(run/"ai_mentions.csv",issues,"ai-mentions",mreq)
    serp,_=rcsv(run/"serp_results.csv",issues,"serp-results",sreq)
    serp_mentions,_=rcsv(run/"serp_mentions.csv",issues,"serp-mentions",smreq)
    page_mentions,_=rcsv(run/"page_mentions.csv",issues,"page-mentions",pmreq)
    rcsv(run/"evidence.csv",issues,"evidence",ereq)
    rechecks,_=rcsv(run/"rechecks.csv",issues,"rechecks",rreq)
    metrics,_=rcsv(run/"ai_metrics.csv",issues,"ai-metrics",{"entity_id","measurement_target","raw_mention_rate","nomination_rate","top3_rate","first_mention_rate","citation_rate","answer_cells","engines_sampled","engine_coverage_rate","cross_model_consistency"})
    emergent,_=rcsv(run/"ai_emergent_entities.csv",issues,"ai-emergent-entities",xreq)

    if meta.get("ai_engine_access_checked") is not True:issues.append(Issue("error","engine-access-not-checked","Stage 2 前必须完成 AI 引擎可达性检查并写 ai_engine_access_checked=true"))
    declared_engines=[str(x).strip() for x in (meta.get("ai_engines_expected") or []) if str(x).strip()]
    expected_sampling="asset-audit-only" if len(declared_engines)==0 else "single-engine" if len(declared_engines)==1 else "limited-multi-engine" if len(declared_engines)==2 else "multi-engine"
    if (meta.get("sampling_mode") or "")!=expected_sampling:issues.append(Issue("error","sampling-mode-mismatch",f"sampling_mode={meta.get('sampling_mode')}，按 ai_engines_expected 数量应为 {expected_sampling}"))
    profile=meta.get("measurement_profile") or ""
    if profile not in VALID_MEASUREMENT_PROFILES:issues.append(Issue("error","measurement-profile","measurement_profile 必须 snapshot/release"))
    expected_mode=meta.get("answer_context_mode_expected") or ""
    if expected_mode not in VALID_CONTEXT_MODES:issues.append(Issue("error","answer-context-mode-meta","answer_context_mode_expected 无效"))
    repeats=intnum(meta.get("repeat_runs_expected"))
    if repeats is None or repeats<1:issues.append(Issue("error","repeat-runs-meta","repeat_runs_expected 必须 >=1"));repeats=1
    if profile=="release" and repeats<3:issues.append(Issue("error","release-repeat-minimum","release profile 至少要求每 query×engine 3 次采样"))
    fresh_required=bool(meta.get("fresh_context_required"))
    if profile=="release" and not fresh_required:issues.append(Issue("error","release-fresh-context","release profile 必须 fresh_context_required=true"))
    isolation=meta.get("context_isolation_level") or ""
    if isolation not in {"api-isolated","product-isolated","programmatic"}:issues.append(Issue("error","context-isolation-level","context_isolation_level 必须 api-isolated/product-isolated/programmatic"))
    if isolation=="programmatic" and profile=="release" and not str(meta.get("fresh_context_note") or "").strip():issues.append(Issue("error","programmatic-context-disclosure","程序性 fresh context 必须填写 fresh_context_note，披露无法物理重置上下文的残余风险"))
    variant_mode=meta.get("query_variant_mode") or ""
    if variant_mode not in {"exact-query-repeat","semantic-retrieval-variants"}:issues.append(Issue("error","query-variant-mode","query_variant_mode 无效"))
    page_status=meta.get("page_collection_status") or ""
    if page_status not in VALID_PAGE_COLLECTION:issues.append(Issue("error","page-collection-status","page_collection_status 必须 collected/not-collected/partial"))
    if page_status=="not-collected" and page_mentions:issues.append(Issue("error","page-status-contradiction","page_collection_status=not-collected 但 page_mentions.csv 非空"))
    if page_status=="collected" and not page_mentions:issues.append(Issue("warning","page-collected-empty","Page Collection 标记为 collected 但 page_mentions.csv 为空；确认这是实际 0 命中而非未抓取"))

    qmap={q.get("query_id"):q for q in queries};answer_ids=set();answers_by_query=defaultdict(list);cell_keys=set();context_ids=set();variant_keys=defaultdict(set)
    for q in queries:
        if q.get("measurement_target") not in VALID_QUERY_TARGETS:issues.append(Issue("error","measurement-target",f"{q.get('query_id')} measurement_target 必须 institution/ip"))
    for a in answers:
        aid=str(a.get("answer_id","")).strip();qid=str(a.get("query_id","")).strip()
        if not aid or aid in answer_ids:issues.append(Issue("error","answer-id",f"ai_answers 行 {a.get('_line')} answer_id 重复/为空"));continue
        answer_ids.add(aid)
        if qid not in qmap:issues.append(Issue("error","answer-query",f"{aid} 引用不存在 query_id {qid}"));continue
        if not str(a.get("response_text","")).strip():issues.append(Issue("error","empty-answer",f"{aid} 缺原始 response_text"))
        sr=intnum(a.get("sample_run"));sr=-1 if sr is None or sr<1 else sr
        if sr==-1:issues.append(Issue("error","sample-run",f"{aid} sample_run 必须 >=1"))
        qv=str(a.get("query_variant_id") or "").strip()
        if profile=="release" and not qv:issues.append(Issue("error","query-variant-id",f"{aid} release 采样必须记录 query_variant_id"))
        if qv:variant_keys[(qid,str(a.get("engine") or ""))].add(qv)
        cm=a.get("answer_context_mode") or ""
        if cm not in VALID_CONTEXT_MODES:issues.append(Issue("error","answer-context-mode",f"{aid} answer_context_mode 无效"))
        elif expected_mode in VALID_CONTEXT_MODES and cm!=expected_mode:issues.append(Issue("error","answer-context-mode-mismatch",f"{aid} answer_context_mode={cm} 与 run_metadata={expected_mode} 不一致"))
        cid=str(a.get("context_id") or "").strip()
        if not cid:issues.append(Issue("error","context-id",f"{aid} 缺 context_id"))
        if fresh_required and not truth(a.get("fresh_context")):issues.append(Issue("error","fresh-context",f"{aid} fresh_context 必须为 true"))
        if truth(a.get("fresh_context")) and cid:
            if cid in context_ids:issues.append(Issue("error","context-reused",f"fresh_context=true 时 context_id 不得复用：{cid}"))
            context_ids.add(cid)
        key=(qid,str(a.get("engine") or ""),str(a.get("model") or ""),sr)
        if key in cell_keys:issues.append(Issue("error","answer-cell-duplicate",f"重复 Answer Cell：{key}"))
        cell_keys.add(key);answers_by_query[qid].append(a)
    if mode=="scoped-geo-landscape" and not answers:issues.append(Issue("error","no-ai-measurement","正式 GEO Landscape 必须有 AI Answer Measurement"))
    declared=set(declared_engines)
    if declared:
        for q in queries:
            if q.get("status")=="sampled":
                qas=answers_by_query.get(q.get("query_id"),[]);qeng={str(a.get("engine","")).strip() for a in qas};miss=declared-qeng
                if miss:issues.append(Issue("error","engine-coverage",f"{q.get('query_id')} 缺 AI 引擎采样：{', '.join(sorted(miss))}"))
                for eng in declared:
                    runs={intnum(a.get("sample_run")) for a in qas if str(a.get("engine","")).strip()==eng};expected=set(range(1,repeats+1))
                    if runs!=expected:issues.append(Issue("error","repeat-run-coverage",f"{q.get('query_id')}/{eng} sample_run={sorted(x for x in runs if x is not None)}，应为 {sorted(expected)}"))
                    if profile=="release" and variant_mode=="semantic-retrieval-variants" and len(variant_keys[(q.get('query_id'),eng)])<repeats:issues.append(Issue("error","variant-coverage",f"{q.get('query_id')}/{eng} semantic variants 少于 repeat_runs_expected"))

    amap={a.get("answer_id"):a for a in answers};result_ids=set();serp_rank_keys=set();rmap={}
    for r in serp:
        rid=r.get("result_id");key=(r.get("query_id"),r.get("engine"),r.get("rank"))
        if not rid or rid in result_ids:issues.append(Issue("error","serp-result-id",f"serp_results result_id 重复/为空：{rid}"))
        result_ids.add(rid);rmap[rid]=r
        if key in serp_rank_keys:issues.append(Issue("error","serp-rank-duplicate",f"同一 query/engine/rank 只能有一个真实 Result Item：{key}"))
        serp_rank_keys.add(key)
        if not r.get("title") and not r.get("snippet"):issues.append(Issue("error","serp-no-surface",f"{rid} title/snippet 均为空"))
    emergent_ids=set();resolved_emergent=set()
    for i,e in enumerate(emergent,2):
        eid=(e.get("entity_id") or "").strip();name=(e.get("canonical_name") or "").strip()
        if not eid or eid in ids or eid in emergent_ids:issues.append(Issue("error","emergent-id",f"ai_emergent_entities 第{i}行 entity_id 为空或冲突：{eid}"))
        else:emergent_ids.add(eid)
        if not name:issues.append(Issue("error","emergent-name",f"{eid or i} canonical_name 为空"))
        if e.get("measurement_target") not in VALID_QUERY_TARGETS:issues.append(Issue("error","emergent-target",f"{name} measurement_target 必须 institution/ip"))
        if e.get("market_scope") not in VALID_SCOPES:issues.append(Issue("error","emergent-scope",f"{name} market_scope 无效"))
        if e.get("resolution_status") not in {"resolved","unresolved"}:issues.append(Issue("error","emergent-resolution",f"{name} resolution_status 必须 resolved/unresolved"))
        src_a=split_pipe(e.get("source_answer_ids"));src_r=split_pipe(e.get("source_result_ids"))
        if not src_a and not src_r:issues.append(Issue("error","emergent-source",f"{name} source_answer_ids/source_result_ids 至少一个非空"))
        if [x for x in src_a if x not in answer_ids]:issues.append(Issue("error","emergent-source",f"{name} 引用不存在 answer_id"))
        if [x for x in src_r if x not in result_ids]:issues.append(Issue("error","emergent-serp-source",f"{name} 引用不存在 result_id"))
        if e.get("resolution_status")=="resolved":resolved_emergent.add(eid)

    valid_raw_entity_ids=ids|emergent_ids;mention_ids=set();raw_rank_keys=set();nomination_rank_keys=set();nomination_pairs=set();positive_by_answer=defaultdict(list)
    for m in mentions:
        mid=m.get("mention_id");aid=m.get("answer_id");eid=m.get("entity_id")
        if not mid or mid in mention_ids:issues.append(Issue("error","mention-id",f"ai_mentions mention_id 重复/为空：{mid}"))
        mention_ids.add(mid)
        if aid not in amap:issues.append(Issue("error","mention-answer",f"{mid} 引用不存在 answer_id"));continue
        if eid not in valid_raw_entity_ids:issues.append(Issue("error","mention-entity",f"{mid} 引用不存在 entity_id；新主体先登记 emergent"));continue
        method=m.get("match_method");intent=m.get("mention_intent");res=(m.get("resolution_status") or "").lower()
        if method not in VALID_MATCH:issues.append(Issue("error","match-method",f"{mid} match_method 无效"))
        if intent not in VALID_MENTION_INTENTS:issues.append(Issue("error","mention-intent",f"{mid} mention_intent 无效"))
        expected_res="resolved" if eid in ids or eid in resolved_emergent else "unresolved"
        if res!=expected_res:issues.append(Issue("error","mention-resolution-status",f"{mid} resolution_status={res}，应为 {expected_res}"))
        if method in {"explicit-name","verified-alias"}:
            needle=norm(m.get("mentioned_name"));text=norm(amap[aid].get("response_text"));rr=num(m.get("mention_rank"))
            if not needle or needle not in text:issues.append(Issue("error","mention-not-in-answer",f"{mid} 的 mentioned_name 未出现在原始回答"))
            if rr is None or rr<1:issues.append(Issue("error","mention-rank",f"{mid} mention_rank 无效"))
            else:
                rk=(aid,rr)
                if rk in raw_rank_keys:issues.append(Issue("error","mention-rank-duplicate",f"{aid} 出现重复 raw mention_rank={rr:g}"))
                raw_rank_keys.add(rk)
        eligible=(method in {"explicit-name","verified-alias"} and res=="resolved" and intent in POSITIVE_INTENTS and truth(m.get("entity_correct")));nr=num(m.get("nomination_rank"))
        if eligible:
            if nr is None or nr<1:issues.append(Issue("error","nomination-rank",f"{mid} 正向提名必须有 nomination_rank"))
            else:
                rk=(aid,nr)
                if rk in nomination_rank_keys:issues.append(Issue("error","nomination-rank-duplicate",f"{aid} 出现重复 nomination_rank={nr:g}"))
                nomination_rank_keys.add(rk);positive_by_answer[aid].append(m)
            pair=(aid,eid)
            if pair in nomination_pairs:issues.append(Issue("error","duplicate-answer-entity-nomination",f"同一 answer/entity 只能有一个正向提名：{aid}/{eid}"))
            nomination_pairs.add(pair)
            if nr is not None and truth(m.get("top3"))!=(nr<=3):issues.append(Issue("error","top3-rank-mismatch",f"{mid} top3 与 nomination_rank={nr:g} 不一致"))
        else:
            if str(m.get("nomination_rank") or "").strip():issues.append(Issue("error","nonpositive-has-nomination-rank",f"{mid} 非正向/未解析提及不得有 nomination_rank"))
            if truth(m.get("top3")) or truth(m.get("first_mention")):issues.append(Issue("error","nonpositive-ranked",f"{mid} 非正向/未解析提及不得标 top3/first_mention"))
        refs=split_pipe(m.get("citation_refs"));linked=truth(m.get("citation_linked"));answer_refs=citation_urls(amap[aid])
        if linked:
            if not refs:issues.append(Issue("error","citation-ref-missing",f"{mid} citation_linked=true 但 citation_refs 为空"))
            elif not any(r in answer_refs for r in refs):issues.append(Issue("error","citation-ref-not-in-answer",f"{mid} citation_refs 未出现在该 Answer Cell citations"))
        elif refs:issues.append(Issue("error","citation-ref-without-link",f"{mid} citation_linked=false 但仍填写 citation_refs"))
    for aid,ms in positive_by_answer.items():
        ranks=sorted(num(m.get("nomination_rank")) for m in ms if num(m.get("nomination_rank")) is not None)
        if ranks and ranks!=list(range(1,len(ranks)+1)):issues.append(Issue("error","nomination-rank-gap",f"{aid} nomination_rank 应从 1 连续编号，实际 {ranks}"))
        for m in ms:
            nr=num(m.get("nomination_rank"))
            if truth(m.get("first_mention"))!=(nr==1):issues.append(Issue("error","first-rank-mismatch",f"{m.get('mention_id')} first_mention 与 nomination_rank={nr:g} 不一致"))

    valid_serp_entity_ids=ids|emergent_ids
    for m in serp_mentions:
        rid=m.get("result_id");surface=m.get("match_surface");eid=m.get("entity_id")
        if rid not in rmap:issues.append(Issue("error","serp-mention-result",f"{m.get('serp_mention_id')} 引用不存在 result_id"));continue
        if eid not in valid_serp_entity_ids:issues.append(Issue("error","serp-mention-entity",f"{m.get('serp_mention_id')} entity_id 未在 Universe/emergent registry"))
        if surface not in {"title","snippet","both"}:issues.append(Issue("error","serp-match-surface",f"{m.get('serp_mention_id')} match_surface 必须 title/snippet/both"));continue
        text=(rmap[rid].get("title","") if surface in {"title","both"} else "")+(rmap[rid].get("snippet","") if surface in {"snippet","both"} else "")
        if norm(m.get("matched_text")) not in norm(text):issues.append(Issue("error","serp-mention-not-visible",f"{m.get('serp_mention_id')} matched_text 不在 title/snippet；网页正文提及必须写 page_mentions.csv"))
    for p in page_mentions:
        if p.get("result_id") and p.get("result_id") not in rmap:issues.append(Issue("error","page-mention-result",f"{p.get('page_mention_id')} 引用不存在 result_id"))

    # Target-specific metrics contract: one row per entity × target; hybrid entities require two rows.
    metric_keys=set();answer_den=defaultdict(int)
    for a in answers:answer_den[qmap.get(a.get("query_id"),{}).get("measurement_target","")]+=1
    expected_metric_keys=set()
    for u in universe:
        t=(u.get("measurement_target") or "").strip()
        for x in (["institution","ip"] if t=="both" else [t]):
            if x in VALID_QUERY_TARGETS:expected_metric_keys.add((u.get("entity_id"),x))
    for e in emergent:
        if e.get("resolution_status")=="resolved":expected_metric_keys.add((e.get("entity_id"),e.get("measurement_target")))
    for m in metrics:
        key=(m.get("entity_id"),m.get("measurement_target"))
        if key in metric_keys:issues.append(Issue("error","metric-target-duplicate",f"ai_metrics 重复 entity×target：{key}"))
        metric_keys.add(key)
        if m.get("measurement_target") not in VALID_QUERY_TARGETS:issues.append(Issue("error","metric-target",f"ai_metrics {key} target 无效"))
        den=intnum(m.get("answer_cells"));expected_den=answer_den.get(m.get("measurement_target"),0)
        if den!=expected_den:issues.append(Issue("error","metric-denominator",f"{key} answer_cells={den}，按 target 应为 {expected_den}"))
    if expected_metric_keys-metric_keys:issues.append(Issue("error","metric-target-missing",f"ai_metrics 缺 entity×target：{sorted(expected_metric_keys-metric_keys)}"))

    ai_rechecks=[r for r in rechecks if r.get("sample_type")=="ai-answer" and r.get("source_id") in answer_ids]
    if len(answers)>=10 and len({r.get("source_id") for r in ai_rechecks})/len(answers)<0.20:issues.append(Issue("error","recheck-coverage","AI Answer 复判覆盖低于 20%"))
    for r in ai_rechecks:
        if truth(r.get("disagreement")) and not r.get("resolution","").strip():issues.append(Issue("error","unresolved-recheck",f"{r.get('recheck_id')} 存在分歧但无 resolution"))

    if profile=="release":
        annotation,_=rcsv(run/"annotation_rechecks.csv",issues,"annotation-rechecks",areq)
        if annotation:
            covered={r.get("answer_id") for r in annotation if r.get("answer_id") in answer_ids}
            if len(answers)>=10 and len(covered)/len(answers)<0.20:issues.append(Issue("error","annotation-recheck-coverage","Annotation Blind Recheck 覆盖低于 20%"))
            for r in annotation:
                if truth(r.get("disagreement")) and not str(r.get("resolution") or "").strip():issues.append(Issue("error","annotation-recheck-unresolved",f"{r.get('review_id')} 有分歧但无 resolution"))
        vr=run/"variant_robustness.csv";rs=run/"robustness_summary.json"
        if not vr.is_file():issues.append(Issue("error","missing-variant-robustness","release profile 必须生成 variant_robustness.csv"))
        if not rs.is_file():issues.append(Issue("error","missing-robustness-summary","release profile 必须生成 robustness_summary.json"))
    return metrics,emergent
