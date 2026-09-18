#!/usr/bin/env python3
"""Validate core fields of .second-brain/profile.yaml without mutating the vault."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def validate(data):
    if not isinstance(data, dict): return ['profile must be a mapping']
    errors=[]
    if data.get('schema_version') != '1.0': errors.append('schema_version must be string "1.0"')
    schema={
        'knowledge_base': {'name': str, 'root': str, 'platform': {'markdown-folder','obsidian'}},
        'governance': {'structure_mode': {'adaptive','custom','standard'}, 'write_mode': {'read-only','confirm-first','trusted-task'}},
        'sources': {'immutable': bool}, 'markdown': {'frontmatter': bool},
        'concurrency': {'mode': {'single-agent','multi-agent'}},
    }
    for section, fields in schema.items():
        obj=data.get(section)
        if not isinstance(obj,dict):
            errors.append(f'{section} must be a mapping'); continue
        for field,rule in fields.items():
            value=obj.get(field)
            valid=(isinstance(value,str) and value in rule) if isinstance(rule,set) else type(value) is rule
            if isinstance(value,str) and not value.strip(): valid=False
            if not valid: errors.append(f'{section}.{field} is missing or has an invalid type/value')
    return errors

def load_profile(path):
    import yaml
    class UniqueLoader(yaml.SafeLoader): pass
    def mapping(loader,node,deep=False):
        result={}
        for key_node,value_node in node.value:
            key=loader.construct_object(key_node,deep=deep)
            if not isinstance(key,str): raise ValueError('mapping keys must be strings')
            if key in result: raise ValueError(f'duplicate mapping key: {key}')
            result[key]=loader.construct_object(value_node,deep=deep)
        return result
    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
    try: return validate(yaml.load(path.read_text(encoding='utf-8'),Loader=UniqueLoader))
    except (OSError,UnicodeError,ValueError,yaml.YAMLError) as exc: return [f'cannot validate profile: {exc}']

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('profile'); a=ap.parse_args()
    p=Path(a.profile).expanduser().resolve()
    warnings=[]
    try: errors=load_profile(p)
    except ImportError: errors=['PyYAML required: install requirements.txt in your Python environment']
    print(json.dumps({'valid':not errors,'errors':errors,'warnings':warnings,'profile':str(p)},ensure_ascii=False,indent=2))
    raise SystemExit(0 if not errors else 2)

if __name__=='__main__': main()
