#!/usr/bin/env python3
"""Portable installed checker. Checks links and configured wiki/Markdown full index."""
import json
from pathlib import Path
import subprocess
import sys
import importlib.util


def main():
    here=Path(__file__).resolve().parent
    c=json.loads((here/'治理配置.json').read_text())
    root=here
    for _ in Path(c['governance_dir']).parts: root=root.parent
    root=root.parent
    spec=importlib.util.spec_from_file_location('links',here/'链接检查.py')
    links=importlib.util.module_from_spec(spec); spec.loader.exec_module(links)
    command=[sys.executable,str(here/'链接检查.py'),str(root)]
    for scope in c['source_roots']+[c['governance_dir']+'/模板']:
        command.extend(['--exclude-content',scope])
    p=subprocess.run(command,capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr)
    report=json.loads(p.stdout)
    errors=report['warnings'][:]
    knowledge=[]
    for rel in c['knowledge_roots']:
        folder=root/rel
        if not folder.is_dir(): errors.append('missing knowledge root: '+rel); continue
        for f in folder.rglob('*.md'):
            if f.is_symlink() or root not in f.resolve().parents:
                errors.append('symlink in knowledge scope: '+str(f)); continue
            relfile=f.relative_to(root).as_posix()
            if relfile not in {c['full_index'],'AGENTS.md'}: knowledge.append(relfile)
    if c['full_index']:
        index=root/c['full_index']
        if not index.is_file(): errors.append('missing full index')
        else:
            counted=[link['target'] for link in report['resolved_links']
                     if link['from']==c['full_index'] and link['target'] in knowledge]
            missing=sorted(set(knowledge)-set(counted))
            duplicates=sorted({x for x in counted if counted.count(x)>1})
            if missing: errors.append({'index_missing':missing})
            if duplicates: errors.append({'index_duplicate':duplicates})
    report.update(knowledge_pages=len(knowledge),errors=errors,
                  coverage='local links and configured full index only; no semantic, source hash or external URL validation')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 2 if errors else 0
if __name__=='__main__':
    try: sys.exit(main())
    except (OSError,ValueError,KeyError,RuntimeError) as e: sys.exit(str(e))
