#!/usr/bin/env python3
"""Prepare/review/commit immutable source inventory; never mask changed old sources."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def snapshot(root,roots):
    result={}
    for name in roots:
        folder=root/name
        if folder.is_symlink() or root not in folder.resolve().parents: raise ValueError('unsafe source root')
        if not folder.is_dir(): raise ValueError('source root missing: '+name)
        for p in folder.rglob('*'):
            if p.is_symlink(): raise ValueError('source symlink: '+str(p))
            if p.is_file(): result[p.relative_to(root).as_posix()]=sha(p)
    return result


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('mode',choices=['prepare','commit','check']); ap.add_argument('candidate',nargs='?',type=Path)
    a=ap.parse_args(); here=Path(__file__).resolve().parent; c=json.loads((here/'治理配置.json').read_text())
    root=here.parent
    for _ in Path(c['governance_dir']).parts: root=root.parent
    baseline=here/'原件哈希基线.json'
    if baseline.is_symlink(): raise ValueError('baseline must not be a symlink')
    old=json.loads(baseline.read_text()) if baseline.exists() else None
    current=snapshot(root,c['source_roots'])
    if old is not None and any(current.get(k)!=v for k,v in old.items()): raise ValueError('existing source changed or missing; baseline not updated')
    if a.mode=='check':
        if old is None or old!=current: raise ValueError('baseline absent or new sources require review')
        print('PASS source hashes: '+str(len(current))); return
    if a.candidate is None: raise ValueError('candidate required')
    candidate=a.candidate.resolve()
    if candidate==root or root in candidate.parents: raise ValueError('candidate must be outside vault')
    if a.mode=='prepare':
        with candidate.open('x') as f: json.dump({'root':str(root),'baseline_sha':sha(baseline) if old is not None else None,'files':current},f,ensure_ascii=False,indent=2)
        print('Review added sources:', sorted(set(current)-set(old or {})))
    else:
        data=json.loads(candidate.read_text())
        if data['root']!=str(root) or data['files']!=current or data['baseline_sha']!=(sha(baseline) if baseline.exists() else None): raise ValueError('candidate or baseline stale')
        # Optimistic verification, not an atomic multi-process lock.
        baseline.write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n')
        print('Committed reviewed baseline; run check independently')
if __name__=='__main__':
    try: main()
    except (OSError,ValueError,KeyError) as e: raise SystemExit(str(e))
