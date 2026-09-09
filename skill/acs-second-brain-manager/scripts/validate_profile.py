#!/usr/bin/env python3
"""Validate core fields of .second-brain/profile.yaml without mutating the vault."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

REQUIRED = ['schema_version','knowledge_base','governance','sources','markdown','concurrency']

def top_keys(text):
    keys=[]
    for line in text.splitlines():
        if line and not line.startswith((' ','\t','#','-')):
            m=re.match(r'^([A-Za-z0-9_-]+)\s*:', line)
            if m: keys.append(m.group(1))
    return keys

def find_scalar(text, key):
    m=re.search(rf'^\s*{re.escape(key)}\s*:\s*["\']?([^\n"\']*)', text, re.M)
    return m.group(1).strip() if m else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('profile'); a=ap.parse_args()
    p=Path(a.profile).expanduser().resolve()
    if not p.is_file(): raise SystemExit(f'profile not found: {p}')
    text=p.read_text('utf-8', errors='replace')
    keys=top_keys(text); errors=[]; warnings=[]
    for k in REQUIRED:
        if k not in keys: errors.append(f'missing top-level key: {k}')
    mode=find_scalar(text,'write_mode')
    if mode and mode not in {'confirm-first','read-only','trusted-task'}: errors.append(f'invalid write_mode: {mode}')
    structure=find_scalar(text,'structure_mode')
    if structure and structure not in {'adaptive','custom','standard'}: errors.append(f'invalid structure_mode: {structure}')
    if 'root:' not in text: warnings.append('knowledge_base.root not found')
    print(json.dumps({'valid':not errors,'errors':errors,'warnings':warnings,'profile':str(p)},ensure_ascii=False,indent=2))
    raise SystemExit(0 if not errors else 2)

if __name__=='__main__': main()
