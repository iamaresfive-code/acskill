#!/usr/bin/env python3
from __future__ import annotations
import csv,json,re
from dataclasses import dataclass
from pathlib import Path

TRUE={"1","true","yes","y","是"}
VERSION="2.2"
VALID_SCOPES={"national","regional","local","unknown"}
VALID_ROLES={"national-benchmark","local-core","local-active","expert-ip","historical","observation","unclassified"}
VALID_UNIVERSE={"included","observation","unresolved"}
VALID_CONFIRM={"needs-review","confirmed"}
VALID_TARGETS={"institution","ip"}
VALID_MATCH={"explicit-name","verified-alias","citation-only"}
VALID_MENTION_INTENTS={"recommended","listed","comparison","caveat","excluded"}
POSITIVE_INTENTS={"recommended","listed"}
VALID_CONTEXT_MODES={"native","engine-native-search","external-search-augmented"}
VALID_MEASUREMENT_PROFILES={"snapshot","release"}
VALID_DOWNGRADE_REASONS={"","seo-only","insufficient-evidence","unresolvable","user-ruling","historical","out-of-scope"}
STAGES={"universe","measurement","report","full"}

@dataclass
class Issue:
    level:str
    code:str
    message:str
    key:str=""

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

def intnum(v):
    try:
        x=int(str(v));return x if str(x)==str(v).strip() or isinstance(v,int) else None
    except:return None

def norm(s):return re.sub(r"\s+","",str(s or "").lower())
def truth(v):return str(v or "").strip().lower() in TRUE
def split_pipe(v):return [x.strip() for x in str(v or "").split("|") if x.strip()]

def citation_urls(answer:dict)->set[str]:
    out=set()
    for c in answer.get("citations") or []:
        if isinstance(c,str):out.add(c.strip())
        elif isinstance(c,dict):
            for k in ("url","href","link"):
                if c.get(k):out.add(str(c[k]).strip())
    return {x for x in out if x}
