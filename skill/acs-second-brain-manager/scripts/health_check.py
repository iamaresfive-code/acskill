#!/usr/bin/env python3
"""Read-only structural health check for a Markdown/Obsidian vault."""
from __future__ import annotations
import argparse, json, os, re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

SKIP_DIRS={'.git','.obsidian','.trash','.second-brain','node_modules','__pycache__'}
WIKI_RE=re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]')

def norm(s): return re.sub(r'\s+',' ',s).strip().casefold()
def has_frontmatter(text): return text.startswith('---\n') and '\n---' in text[4:]

def prose(text):
    """Exclude fenced and inline code examples from link checks."""
    lines=[]; fence=None
    for line in text.splitlines():
        marker=re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            token, tail=marker.groups()
            if fence is None: fence=token; continue
            if token[0]==fence[0] and len(token)>=len(fence) and not tail.strip(): fence=None; continue
        if fence is None: lines.append(line)
    return re.sub(r'(`+).*?\1', '', '\n'.join(lines), flags=re.S)

def markdown_targets(text):
    # Inline destinations, including angle-bracket paths and one nested pair.
    pattern=r'!?\[[^\]\n]*\]\(\s*(<[^>\n]*>|(?:[^\s()\\]|\\.|\([^()]*\))+)\s*(?:"[^"\n]*"|\x27[^\x27\n]*\x27)?\s*\)'
    for match in re.finditer(pattern, text):
        yield match.group(1).strip('<>')

def candidates(root, page, target, wiki):
    """Resolve explicit paths without falling back to an unrelated basename."""
    raw=unquote(target.split('|',1)[0]) if wiki else target
    if wiki: raw=raw.split('#',1)[0]
    else:
        try: parsed=urlsplit(raw)
        except ValueError: return []
        if parsed.scheme or parsed.netloc: return None
        raw=unquote(parsed.path)
    raw=raw.strip()
    if not raw: return None  # same-page anchor
    paths=[root / raw.lstrip('/')] if raw.startswith('/') else [page.parent / raw]
    if wiki and '/' in raw and not raw.startswith(('./','../','/')): paths.insert(0,root / raw)
    found=[]
    for path in paths:
        options=[path]
        if (wiki and path.suffix.lower() != '.md') or not path.suffix:
            options.append(path.with_name(path.name + '.md'))
        for option in options:
            resolved=option.resolve()
            try: rel=resolved.relative_to(root).as_posix()
            except ValueError: continue
            if resolved.is_file() and rel not in found: found.append(rel)
    return found

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--output'); a=ap.parse_args()
    root=Path(a.root).expanduser().resolve()
    if not root.is_dir(): raise SystemExit(f'root is not a directory: {root}')
    pages=[]; by_name=defaultdict(list)
    for dp,dns,fns in os.walk(root):
        dns[:]=[d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            path=Path(dp)/fn
            if not path.is_file(): continue
            by_name[norm(fn)].append(path.relative_to(root).as_posix())
            if fn.lower().endswith('.md'): pages.append(path)
    by_stem=defaultdict(list)
    for p in pages: by_stem[norm(p.stem)].append(p.relative_to(root).as_posix())
    dup={k:v for k,v in by_stem.items() if len(v)>1}
    broken=[]; broken_md=[]; ambiguous=[]; outbound=Counter(); inbound=Counter(); no_fm=[]
    for p in pages:
        rel=p.relative_to(root).as_posix()
        try: text=p.read_text('utf-8',errors='replace')
        except OSError: continue
        if not has_frontmatter(text): no_fm.append(rel)
        text=prose(text)
        links=[(target,True) for target in WIKI_RE.findall(text)]
        links.extend((target,False) for target in markdown_targets(text))
        for target,wiki in links:
            found=candidates(root,p,target,wiki)
            if found is None: continue
            if wiki and not found and '/' not in target:
                name=unquote(target).strip()
                stem=Path(name).stem if name.lower().endswith('.md') else name
                found=list(dict.fromkeys(by_stem.get(norm(stem),[]) + by_name.get(norm(name),[])))
            outbound[rel]+=1
            if len(found)>1: ambiguous.append({'from':rel,'target':target,'candidates':found})
            elif found: inbound[found[0]]+=1
            else: (broken if wiki else broken_md).append({'from':rel,'target':target})
    orphans=[p.relative_to(root).as_posix() for p in pages if outbound[p.relative_to(root).as_posix()]==0 and inbound[p.relative_to(root).as_posix()]==0]
    result={'schema_version':'1.0','root':str(root),'markdown_pages':len(pages),
            'critical':[], 'warnings':[], 'suggestions':[],
            'signals':{'duplicate_stems':dup,'broken_wikilinks':broken[:500],'broken_markdown_links':broken_md[:500],'ambiguous_links':ambiguous[:500],'orphan_pages':orphans[:500],'pages_without_frontmatter':no_fm[:500]},
            'notes':['Checks local wiki and inline Markdown file links; not heading anchors, reference-style links or remote URLs. Code examples are excluded. Semantic conflicts require agent review.', 'No source files were modified.']}
    if broken: result['warnings'].append(f'{len(broken)} broken wikilink(s) detected')
    if broken_md: result['warnings'].append(f'{len(broken_md)} broken Markdown link(s) detected')
    if ambiguous: result['warnings'].append(f'{len(ambiguous)} ambiguous link(s) detected')
    if dup: result['warnings'].append(f'{len(dup)} duplicate filename stem group(s) detected')
    if orphans: result['suggestions'].append(f'{len(orphans)} orphan page(s) detected; review before linking')
    payload=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        out=Path(a.output).expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(payload+'\n','utf-8')
    else: print(payload)

if __name__=='__main__': main()
