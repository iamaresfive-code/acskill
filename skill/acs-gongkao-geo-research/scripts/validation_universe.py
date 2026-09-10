#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from validation_common import *

def validate_universe(run:Path,meta:dict,issues:list[Issue],require_confirmed:bool):
    ureq={"entity_id","canonical_name","aliases","entity_type","user_seed","discovery_origin","market_scope","operating_region","market_role","activity_status","platform_native","salience_basis","universe_status","confirmation_status","downgrade_reason","notes"}
    universe,_=rcsv(run/"market_universe.csv",issues,"market-universe",ureq)
    review=rjson(run/"universe_review.json",issues,"universe-review")
    ids=set();names=set();seeds=[str(x).strip() for x in meta.get("seed_entities",[]) if str(x).strip()];seed_names={norm(x) for x in seeds};seen_seed=set();by_name={}
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
        reason=(r.get("downgrade_reason") or "").strip()
        if reason not in VALID_DOWNGRADE_REASONS:issues.append(Issue("error","downgrade-reason",f"{name} downgrade_reason 无效：{reason}"))
        if r.get("universe_status")=="included" and reason:issues.append(Issue("error","included-with-downgrade",f"{name} 已 included 但仍有 downgrade_reason={reason}"))
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
        expected_system=sum((not truth(r.get("user_seed"))) and ("system-discovery" in (r.get("discovery_origin") or "") or "platform-native" in (r.get("discovery_origin") or "")) for r in universe)
        if review.get("system_discovery_count")!=expected_system:issues.append(Issue("error","review-system-discovery-count",f"system_discovery_count={review.get('system_discovery_count')}，应为非 Seed 系统发现主体 {expected_system}"))
        expected_platform=sum(truth(r.get("platform_native")) for r in universe)
        if review.get("platform_native_count") is not None and review.get("platform_native_count")!=expected_platform:issues.append(Issue("error","review-platform-count",f"platform_native_count={review.get('platform_native_count')}，CSV={expected_platform}"))
        expected_ip=sum(r.get("universe_status")=="included" and r.get("market_role")=="expert-ip" for r in universe)
        if review.get("expert_ip_included_count") is not None and review.get("expert_ip_included_count")!=expected_ip:issues.append(Issue("error","review-expert-ip-count",f"expert_ip_included_count={review.get('expert_ip_included_count')}，CSV={expected_ip}"))
        expected_seo=sorted(r.get("canonical_name","") for r in universe if r.get("downgrade_reason")=="seo-only")
        if sorted(review.get("seo_only_downgraded") or [])!=expected_seo:issues.append(Issue("error","review-seo-downgrade",f"seo_only_downgraded 与结构化 downgrade_reason 不一致"))
        buckets=review.get("buckets") or {};expected_keys={"A_national_benchmarks","B_local_regional","C_expert_ip","D_observation_or_other"}
        if set(buckets)!=expected_keys:issues.append(Issue("error","review-bucket-schema",f"Universe Review buckets 必须精确为：{', '.join(sorted(expected_keys))}"))
        flat=[]
        for k in expected_keys:flat+=list(buckets.get(k) or [])
        dup=sorted({x for x in flat if flat.count(x)>1})
        if dup:issues.append(Issue("error","review-bucket-overlap",f"Universe Review 分桶重叠：{', '.join(dup)}"))
        if set(flat)!=set(by_name):issues.append(Issue("error","review-bucket-coverage",f"Universe Review 分桶未与 market_universe 一一覆盖；missing={sorted(set(by_name)-set(flat))}, extra={sorted(set(flat)-set(by_name))}"))
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
