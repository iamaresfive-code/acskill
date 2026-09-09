#!/usr/bin/env python3
"""Read-only structural scan for a Markdown/Obsidian knowledge base."""
from __future__ import annotations
import argparse, json, os, re
from collections import Counter
from pathlib import Path

SKIP_DIRS = {'.git', '.obsidian', '.trash', '.DS_Store', 'node_modules', '__pycache__'}
GOVERNANCE_NAMES = {'AGENTS.md','README.md','结构约定.md','knowledge-rules.md','structure-contract.md','profile.yaml'}
SOURCE_NAMES = {'原始材料','source','sources','raw','raw-materials','attachments'}
INDEX_NAMES = {'目录.md','index.md','INDEX.md','知识全量索引.md','项目索引.md'}

def frontmatter_keys(text: str):
    if not text.startswith('---\n'):
        return []
    end = text.find('\n---', 4)
    if end < 0:
        return []
    keys=[]
    for line in text[4:end].splitlines():
        m=re.match(r'^([A-Za-z0-9_\-\u4e00-\u9fff]+)\s*:', line)
        if m: keys.append(m.group(1))
    return keys

def main():
    p=argparse.ArgumentParser()
    p.add_argument('root')
    p.add_argument('--max-depth', type=int, default=4)
    p.add_argument('--sample-md', type=int, default=200)
    p.add_argument('--output')
    a=p.parse_args()
    root=Path(a.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f'root is not a directory: {root}')

    ext_counts=Counter(); fm_keys=Counter(); md_files=[]; governance=[]; indices=[]; source_roots=[]
    wiki_links=0; markdown_links=0; obsidian=(root/'.obsidian').is_dir()
    top_dirs=[]
    for child in sorted(root.iterdir(), key=lambda x:x.name.lower()):
        if child.is_dir() and child.name not in SKIP_DIRS:
            top_dirs.append(child.name)
            if child.name.lower() in SOURCE_NAMES or child.name in SOURCE_NAMES:
                source_roots.append(child.name)

    for dirpath, dirnames, filenames in os.walk(root):
        rel=Path(dirpath).relative_to(root)
        depth=len(rel.parts)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and (depth < a.max_depth)]
        if depth > a.max_depth: continue
        for fn in filenames:
            path=Path(dirpath)/fn
            relp=path.relative_to(root).as_posix()
            ext=path.suffix.lower() or '[no-ext]'
            ext_counts[ext]+=1
            if fn in GOVERNANCE_NAMES or relp.startswith('.second-brain/'):
                governance.append(relp)
            if fn in INDEX_NAMES:
                indices.append(relp)
            if ext == '.md':
                md_files.append(path)

    for path in md_files[:a.sample_md]:
        try: text=path.read_text('utf-8', errors='replace')[:200000]
        except OSError: continue
        fm_keys.update(frontmatter_keys(text))
        wiki_links += len(re.findall(r'\[\[[^\]]+\]\]', text))
        markdown_links += len(re.findall(r'\[[^\]]+\]\([^\)]+\)', text))

    result={
        'schema_version':'1.0', 'root':str(root), 'platform':'obsidian' if obsidian else 'markdown-folder',
        'top_level_directories':top_dirs, 'file_counts_by_extension':dict(ext_counts), 'markdown_file_count':len(md_files),
        'sampled_markdown_files':min(len(md_files),a.sample_md), 'frontmatter_keys':dict(fm_keys.most_common()),
        'link_signals':{'wikilink_count':wiki_links,'markdown_link_count':markdown_links,
                        'likely_style':'wikilink' if wiki_links>markdown_links else ('markdown' if markdown_links>wiki_links else 'unknown')},
        'governance_files':sorted(set(governance)), 'index_files':sorted(set(indices)),
        'candidate_source_roots':sorted(set(source_roots)),
        'notes':['Read-only scan; no knowledge-base files were modified.', 'Detected patterns are observations, not confirmed governance rules.']
    }
    payload=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        out=Path(a.output).expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(payload+'\n','utf-8')
    else: print(payload)

if __name__=='__main__': main()
