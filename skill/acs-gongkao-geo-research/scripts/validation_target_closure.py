#!/usr/bin/env python3
"""Release-only Target Closure and Resolution Audit validation."""
from __future__ import annotations
from pathlib import Path
from validation_common import Issue,rcsv,rjsonl,truth
from measurement_target_utils import VALID_ENTITY_TARGETS,expanded_target,effective_emergent_target
from resolution_review_utils import risk_flags

RREQ={"review_id","mention_id","answer_id","entity_id","canonical_name","mentioned_name","match_method","risk_flags","first_resolution_status","first_entity_correct","reviewer_resolution_status","reviewer_entity_correct","disagreement","resolution_outcome","resolution","reviewer","review_status","notes"}
AREQ={"entity_id","canonical_name","entity_source","resolution_status","stage1_market_role","market_bucket","entity_type","current_explicit_target","candidate_target","institution_evidence","ip_evidence","hybrid_signal","hybrid_signal_basis","cross_target_ai_signal","new_explicit_target","evidence_basis","reviewer_reason","changed","review_status","notes"}


def validate_target_closure(run:Path,meta:dict,issues:list[Issue],universe:list,metrics:list,emergent:list):
    if meta.get("measurement_profile")!="release":return
    if meta.get("measurement_target_reviewed") is not True:issues.append(Issue("error","target-closure-not-reviewed","release Measurement 必须完成 Measurement Target Audit"))
    if meta.get("resolved_emergent_target_reviewed") is not True:issues.append(Issue("error","emergent-target-closure-not-reviewed","release Measurement 必须审定全部 resolved AI-emergent Target"))

    audit,_=rcsv(run/"measurement_target_audit.csv",issues,"measurement-target-audit",AREQ)
    aby={};
    for a in audit:
        eid=(a.get("entity_id") or "").strip()
        if not eid or eid in aby:issues.append(Issue("error","target-audit-id",f"measurement_target_audit entity_id 重复/为空：{eid}"));continue
        aby[eid]=a
    expected_sources={}
    for u in universe:expected_sources[u.get("entity_id")]=("universe",u.get("canonical_name") or u.get("entity_id"))
    resolved_emergent=[]
    for e in emergent:
        if (e.get("resolution_status") or "").lower()=="resolved":
            resolved_emergent.append(e);expected_sources[e.get("entity_id")]=("ai-emergent",e.get("canonical_name") or e.get("entity_id"))
    for eid,(source,name) in expected_sources.items():
        a=aby.get(eid)
        if not a:issues.append(Issue("error","target-audit-coverage",f"{name}: release Target Audit 缺行"));continue
        if a.get("entity_source")!=source:issues.append(Issue("error","target-audit-source",f"{name}: entity_source={a.get('entity_source')}，应为 {source}"))
        if a.get("review_status")!="confirmed":issues.append(Issue("error","target-audit-unreviewed",f"{name}: Target Audit review_status 必须 confirmed"))
        t=(a.get("new_explicit_target") or "").strip()
        if t not in VALID_ENTITY_TARGETS:issues.append(Issue("error","target-audit-target",f"{name}: new_explicit_target 必须 institution/ip/both"))
        if not str(a.get("evidence_basis") or "").strip():issues.append(Issue("error","target-audit-evidence",f"{name}: evidence_basis 不能为空"))
        if truth(a.get("hybrid_signal")) and not str(a.get("reviewer_reason") or "").strip():issues.append(Issue("error","target-audit-hybrid-reason",f"{name}: hybrid_signal=true 必须填写 reviewer_reason"))
    extra=set(aby)-set(expected_sources)
    if extra:issues.append(Issue("error","target-audit-extra",f"measurement_target_audit 含非 Universe/非 resolved emergent：{sorted(extra)[:20]}"))

    for e in resolved_emergent:
        eid=e.get("entity_id");name=e.get("canonical_name") or eid;t=effective_emergent_target(e)
        if t not in VALID_ENTITY_TARGETS:issues.append(Issue("error","emergent-reviewed-target",f"{name}: reviewed_measurement_target 必须 institution/ip/both"));continue
        if (e.get("measurement_target_review_status") or "")!="confirmed":issues.append(Issue("error","emergent-target-review-status",f"{name}: measurement_target_review_status 必须 confirmed"))
        a=aby.get(eid)
        if a and (a.get("new_explicit_target") or "").strip()!=t:issues.append(Issue("error","emergent-target-audit-mismatch",f"{name}: registry reviewed target 与 audit 不一致"))

    expected_metric_keys=set()
    for u in universe:
        for t in expanded_target(u.get("measurement_target")):expected_metric_keys.add((u.get("entity_id"),t))
    for e in resolved_emergent:
        for t in expanded_target(effective_emergent_target(e)):expected_metric_keys.add((e.get("entity_id"),t))
    actual_metric_keys={(m.get("entity_id"),m.get("measurement_target")) for m in metrics}
    missing=expected_metric_keys-actual_metric_keys;extra_metrics=actual_metric_keys-expected_metric_keys
    if missing:issues.append(Issue("error","target-closure-metric-missing",f"reviewed Target 缺 Metrics 行：{sorted(missing)[:30]}"))
    if extra_metrics:issues.append(Issue("error","target-closure-metric-extra",f"Metrics 含未被 reviewed Target 授权的 entity×target：{sorted(extra_metrics)[:30]}"))

    # Targeted Entity Resolution audit, separate from semantic annotation review.
    mentions,_=rcsv(run/"ai_mentions.csv",issues,"ai-mentions-resolution-audit")
    answers=rjsonl(run/"ai_answers.jsonl",issues,"ai-answers-resolution-audit");amap={a.get("answer_id"):a for a in answers};emergent_ids={e.get("entity_id") for e in emergent}
    risky={}
    for m in mentions:
        a=amap.get(m.get("answer_id"),{});flags=risk_flags(m,a.get("response_text","") or "",emergent_ids)
        if flags:risky[m.get("mention_id")]=(m,flags)
    rr,_=rcsv(run/"resolution_rechecks.csv",issues,"resolution-rechecks",RREQ)
    rby={}
    for r in rr:
        mid=(r.get("mention_id") or "").strip()
        if not mid or mid in rby:issues.append(Issue("error","resolution-recheck-id",f"resolution_rechecks mention_id 重复/为空：{mid}"));continue
        rby[mid]=r
    missing_risk=set(risky)-set(rby)
    if missing_risk:issues.append(Issue("error","resolution-recheck-coverage",f"高风险 Entity Resolution mention 未复核：{sorted(missing_risk)[:30]}"))
    extra_r=set(rby)-set(risky)
    if extra_r:issues.append(Issue("warning","resolution-recheck-extra",f"resolution_rechecks 含当前规则未标记为高风险的 mention：{sorted(extra_r)[:20]}"))
    for mid,(m,flags) in risky.items():
        r=rby.get(mid)
        if not r:continue
        if r.get("answer_id")!=m.get("answer_id") or r.get("entity_id")!=m.get("entity_id"):issues.append(Issue("error","resolution-recheck-identity",f"{mid}: recheck answer/entity 与 ai_mentions 不一致"));continue
        if r.get("review_status")!="confirmed":issues.append(Issue("error","resolution-recheck-unreviewed",f"{mid}: review_status 必须 confirmed"))
        rrstatus=(r.get("reviewer_resolution_status") or "").strip().lower();rcorrect=(r.get("reviewer_entity_correct") or "").strip().lower()
        if rrstatus not in {"resolved","unresolved"}:issues.append(Issue("error","resolution-recheck-status",f"{mid}: reviewer_resolution_status 必须 resolved/unresolved"))
        if rcorrect not in {"true","false"}:issues.append(Issue("error","resolution-recheck-entity-correct",f"{mid}: reviewer_entity_correct 必须 true/false"))
        differs=(rrstatus!=(m.get("resolution_status") or "").lower()) or (rcorrect!=("true" if truth(m.get("entity_correct")) else "false"))
        if truth(r.get("disagreement"))!=differs:issues.append(Issue("error","resolution-recheck-disagreement",f"{mid}: disagreement 与 reviewer/current 差异不一致"))
        outcome=(r.get("resolution_outcome") or "").strip()
        if outcome not in {"confirmed-existing","corrected-in-run","requires-upstream-fix"}:issues.append(Issue("error","resolution-recheck-outcome",f"{mid}: resolution_outcome 无效"))
        if outcome=="requires-upstream-fix":issues.append(Issue("error","resolution-recheck-upstream-fix",f"{mid}: Entity Resolution 尚需上游修复：{r.get('resolution','')}"))
        if differs and outcome!="requires-upstream-fix":issues.append(Issue("error","resolution-recheck-not-applied",f"{mid}: reviewer 结论与当前 ai_mentions 不一致；先修正上游/ai_mentions 后再确认"))
        if not str(r.get("reviewer") or "").strip():issues.append(Issue("error","resolution-recheck-reviewer",f"{mid}: reviewer 不能为空"))
        if not str(r.get("resolution") or "").strip():issues.append(Issue("error","resolution-recheck-reason",f"{mid}: resolution 必须记录判断依据"))
