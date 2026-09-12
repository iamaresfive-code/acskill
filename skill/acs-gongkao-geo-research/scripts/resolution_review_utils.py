#!/usr/bin/env python3
"""Shared risk rules for targeted Entity Resolution rechecks."""
from __future__ import annotations
import re

CJK=re.compile(r"[\u3400-\u9fff]")


def cjk_len(text:str)->int:
    return sum(1 for ch in str(text or "") if CJK.fullmatch(ch))


def short_name_boundary_suspicion(response:str,name:str)->bool:
    name=str(name or "").strip();response=str(response or "")
    if not name or cjk_len(name)>2:return False
    start=0
    while True:
        i=response.find(name,start)
        if i<0:return False
        before=response[i-1] if i>0 else "";after=response[i+len(name)] if i+len(name)<len(response) else ""
        if (before and CJK.fullmatch(before)) or (after and CJK.fullmatch(after)):return True
        start=i+max(1,len(name))


def risk_flags(mention:dict,response:str,emergent_ids:set[str])->list[str]:
    flags=[];eid=mention.get("entity_id")
    if eid in emergent_ids:flags.append("ai-emergent")
    if (mention.get("resolution_status") or "").lower()=="unresolved":flags.append("unresolved")
    if mention.get("match_method")=="verified-alias":flags.append("verified-alias")
    if mention.get("match_method")=="citation-only":flags.append("citation-only")
    if short_name_boundary_suspicion(response,mention.get("mentioned_name")):flags.append("short-name-boundary")
    return flags
