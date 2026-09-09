#!/usr/bin/env python3
"""Read-only structural health check for a Markdown/Obsidian vault."""
from __future__ import annotations
import argparse, json, os, re
from collections import Counter, defaultdict
from pathlib import Path

SKIP_DIRS={'.git','.obsidian','.trash','.second-brain','node_modules','__pycache__'}
WIKI_RE=re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]')

def norm(s): return re.sub(r'\s+',' ',s).strip().casefold()
def has_frontmatter(text): return text.startswith('---\n') and '\n---' in text[4:]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--output'); a=ap.parse_args()
    root=Path(a.root).expanduser().resolve()
    if not root.is_dir(): raise SystemExit(f'root is not a directory: {root}')
    pages=[]
    for dp,dns,fns in os.walk(root):
        dns[:]=[d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            if fn.lower().endswith('.md'): pages.append(Path(dp)/fn)
    by_stem=defaultdict(list)
    for p in pages: by_stem[norm(p.stem)].append(p.relative_to(root).as_posix())
    dup={k:v for k,v in by_stem.items() if len(v)>1}
    known=set(by_stem)
    broken=[]; outbound=Counter(); inbound=Counter(); no_fm=[]
    for p in pages:
        rel=p.relative_to(root).as_posix()
        try: text=p.read_text('utf-8',errors='replace')
        except OSError: continue
        if not has_frontmatter(text): no_fm.append(rel)
        for target in WIKI_RE.findall(text):
            t=norm(Path(target).name)
            outbound[rel]+=1
            if t in known:
                for dest in by_stem[t]: inbound[dest]+=1
            else: broken.append({'from':rel,'target':target})
    orphans=[p.relative_to(root).as_posix() for p in pages if outbound[p.relative_to(root).as_posix()]==0 and inbound[p.relative_to(root).as_posix()]==0]
    result={'schema_version':'1.0','root':str(root),'markdown_pages':len(pages),
            'critical':[], 'warnings':[], 'suggestions':[],
            'signals':{'duplicate_stems':dup,'broken_wikilinks':broken[:500],'orphan_pages':orphans[:500],'pages_without_frontmatter':no_fm[:500]},
            'notes':['This script reports structural signals only; semantic conflicts, stale facts and entity equivalence require agent review.', 'No files were modified.']}
    if broken: result['warnings'].append(f'{len(broken)} broken wikilink(s) detected')
    if dup: result['warnings'].append(f'{len(dup)} duplicate filename stem group(s) detected')
    if orphans: result['suggestions'].append(f'{len(orphans)} orphan page(s) detected; review before linking')
    payload=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        out=Path(a.output).expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(payload+'\n','utf-8')
    else: print(payload)

if __name__=='__main__': main()
