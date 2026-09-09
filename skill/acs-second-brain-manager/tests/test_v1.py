#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'

def run(*args):
    p=subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True)
    if p.returncode != 0:
        raise AssertionError(f'command failed: {args}\nstdout={p.stdout}\nstderr={p.stderr}')
    return p.stdout

def main():
    with tempfile.TemporaryDirectory() as td:
        v=Path(td)/'vault'; v.mkdir(); (v/'.obsidian').mkdir(); (v/'原始材料').mkdir()
        (v/'目录.md').write_text('---\ntitle: 目录\ntype: index\n---\n# 目录\n- [[机构-A]]\n','utf-8')
        (v/'机构-A.md').write_text('---\ntitle: 机构-A\ntype: entity\n---\n# 机构-A\n[[不存在页面]]\n','utf-8')
        (v/'子目录').mkdir(); (v/'子目录'/'机构-A.md').write_text('# duplicate stem\n','utf-8')
        scan=json.loads(run(SCRIPTS/'scan_knowledge_base.py',v))
        assert scan['platform']=='obsidian'; assert scan['markdown_file_count']==3; assert '目录.md' in scan['index_files']
        health=json.loads(run(SCRIPTS/'health_check.py',v))
        assert health['markdown_pages']==3; assert health['signals']['broken_wikilinks']; assert health['signals']['duplicate_stems']
        sb=v/'.second-brain'; sb.mkdir()
        profile=sb/'profile.yaml'; profile.write_text('''schema_version: "1.0"\nknowledge_base:\n  name: "Test"\n  root: "."\n  platform: "obsidian"\ngovernance:\n  structure_mode: "adaptive"\n  write_mode: "confirm-first"\nsources:\n  immutable: true\nmarkdown:\n  frontmatter: true\nconcurrency:\n  mode: "single-agent"\n''','utf-8')
        valid=json.loads(run(SCRIPTS/'validate_profile.py',profile)); assert valid['valid'] is True
    print('PASS: acs-second-brain-manager v1 smoke tests')

if __name__=='__main__': main()
