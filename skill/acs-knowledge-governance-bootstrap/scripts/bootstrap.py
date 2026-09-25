#!/usr/bin/env python3
"""Plan and install portable governance. Standard library; no network or locks."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
START = '<!-- acs-governance:start -->'
END = '<!-- acs-governance:end -->'
VERSION = '1.0'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local(root, value):
    root = root.resolve()
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('path must be a nonempty relative POSIX path')
    p = Path(value)
    if p.is_absolute() or any(x in {'.', '..'} for x in value.split('/')):
        raise ValueError(f'unsafe path: {value}')
    target = root / p
    for part in [target, *target.parents]:
        if part == root: break
        if part.is_symlink(): raise ValueError(f'symlink not allowed: {part}')
    target.resolve().relative_to(root)
    return target


def read(path):
    return path.read_bytes() if path.exists() else None


def fingerprint(path):
    data = read(path)
    return None if data is None else digest(data)


def config_for(root, mode, custom):
    c = dict(custom)
    allowed = {'knowledge_roots', 'source_roots', 'governance_dir', 'existing_rules',
               'full_index', 'modules', 'maintainer'}
    if set(c) - allowed: raise ValueError('unknown configuration keys')
    if mode == 'new':
        c.setdefault('knowledge_roots', ['知识'])
        c.setdefault('source_roots', ['原始材料'])
        c.setdefault('full_index', '索引/知识全量索引.md')
    elif not c.get('knowledge_roots'):
        raise ValueError('existing mode requires confirmed knowledge_roots; do not guess')
    c.setdefault('source_roots', [])
    c.setdefault('full_index', None)
    c.setdefault('governance_dir', '规范与工具')
    c.setdefault('existing_rules', [])
    c.setdefault('modules', [])
    c.setdefault('maintainer', '用户指定的主要维护者')
    if not isinstance(c['maintainer'], str) or not c['maintainer'].strip() or '\n' in c['maintainer']:
        raise ValueError('maintainer must be a single nonempty line')
    for key in ['knowledge_roots', 'source_roots', 'existing_rules', 'modules']:
        if not isinstance(c[key], list) or any(not isinstance(x, str) for x in c[key]):
            raise ValueError(f'{key} must be a list of strings')
        if len(set(c[key])) != len(c[key]): raise ValueError(f'duplicate {key}')
    if set(c['modules']) - {'web', 'files', 'projects', 'collaboration', 'source-hashes'}:
        raise ValueError('unknown optional module')
    if 'source-hashes' in c['modules'] and not c['source_roots']:
        raise ValueError('source-hashes requires confirmed source_roots')
    paths = [*c['knowledge_roots'], *c['source_roots'], c['governance_dir']]
    for value in paths: local(root, value)
    for i, a in enumerate(paths):
        for b in paths[i+1:]:
            if a == b or a.startswith(b+'/') or b.startswith(a+'/'):
                raise ValueError('knowledge/source/governance roots must not overlap')
    for value in c['existing_rules']:
        if not local(root, value).is_file(): raise ValueError('existing rule missing: '+value)
    if c['full_index']:
        local(root, c['full_index'])
        if c['full_index'] in {'AGENTS.md','目录.md'} or c['full_index'].startswith(c['governance_dir']+'/'):
            raise ValueError('index collides with governance targets')
    if mode == 'existing':
        for value in c['knowledge_roots'] + c['source_roots']:
            if not local(root, value).is_dir(): raise ValueError('mapped directory missing: '+value)
        if c['full_index'] and not local(root,c['full_index']).is_file():
            raise ValueError('map an existing index or use null; no automatic index creation in existing mode')
    elif any(not any('\u4e00' <= ch <= '\u9fff' for ch in part)
             for value in paths for part in Path(value).parts):
        raise ValueError('new vault directory names must be Chinese')
    return c


def render(root, mode, c):
    g = c['governance_dir']; rules = g+'/规范'; tools = g+'/工具'
    files = {}
    files[rules+'/结构约定.md'] = f'''# 知识库结构约定

本文件为治理安装器生成的适配规则。用户当前指令优先；现有权威规则为：{', '.join(c['existing_rules']) or '无'}。安装前须人工消解冲突，不能靠新增本文件覆盖旧约定。

- 知识目录：{', '.join(c['knowledge_roots'])}。
- 原始材料目录：{', '.join(c['source_roots']) or '尚未设置；保存新来源前先确认位置'}。
- 全量索引：{c['full_index'] or '沿用现有导航；没有统一索引时不强造第二套'}。
- 已有目录、命名、frontmatter与链接习惯优先；不得为治理批量搬动既有文件。
- 新库中文目录按用途扩展，不预置开发者行业、客户或项目。
- 页面类型可用entity、concept、source-summary、comparison、synthesis、case、procedure、tracker；type不决定目录。已有类型沿用。
- 新库知识页包含title、type、created、updated、sources、tags；来源用真实相对路径。治理文件不算知识页，AGENTS.md不加frontmatter。
- 来源事实、用户判断、Agent推断、用户决策与待核分开。原件保持原样；知识页维护当前可用版本，历史由原件与日志承担。
- 写入先读源、查重，选择更新、合并、新建、待核或仅留原件；先列完整方案，批准后一次完成必要关联页与索引维护。
- 只建立真实且有稳定导航价值的链接；双方都有价值才补返链，不机械补满。
- 日期不足不猜；updated不等于数据观察日期；项目不按日期自动完结。
- 有全量索引时每个知识页登记一次；新库首页只作常用导航。已有索引格式保持。
- 查询按名称、别名、标题由窄到宽；回答读取上下文，不凭孤立命中行。
- 普通写入后检查变更页的来源、链接和索引；结构迁移或工具变化再全量检查。自动检查不能代替语义审查。
'''
    files[rules+'/知识维护规范.md'] = (PACKAGE/'references/knowledge-model.md').read_text()
    files[tools+'/链接检查.py'] = (PACKAGE/'scripts/health_check.py').read_text()
    files[tools+'/治理检查.py'] = (PACKAGE/'scripts/check_governance.py').read_text()
    files[tools+'/治理配置.json'] = json.dumps(c, ensure_ascii=False, indent=2)+'\n'
    files[g+'/模板/知识页.md'] = '''---
title: 待填写
type: concept
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: []
tags: []
---

# 待填写

这是空白模板，不是已入库知识。按来源提炼当前可用结论，不能将空sources当作有证据。
'''
    optional = {'web': ('网页收录规范.md','web-ingestion.md'),
                'files': ('多格式读取规范.md','file-reading.md'),
                'collaboration': ('多Agent协作规范.md','concurrency-policy.md')}
    for module, (name, ref) in optional.items():
        if module in c['modules']: files[rules+'/'+name] = (PACKAGE/'references'/ref).read_text()
    if 'projects' in c['modules']:
        text = (PACKAGE/'references/project-memory.md').read_text().replace('../templates/project-memory.md','../模板/专项记忆.md')
        files[rules+'/专项记忆规范.md'] = text
        files[g+'/模板/专项记忆.md'] = (PACKAGE/'templates/project-memory.md').read_text()
    if 'source-hashes' in c['modules']:
        files[tools+'/原件校验.py'] = (PACKAGE/'scripts/source_integrity.py').read_text()
    block = f'''{START}
## 知识库治理入口

- 工作区为本AGENTS.md所在知识库，所有路径相对库根，不套用开发者路径或账号。
- 先读 `{rules}/结构约定.md` 及目标相关规范；现有明确规则与当前用户指令优先，冲突先核实。
- 主要维护者：{c['maintainer']}。其他执行者默认读取分析，只有用户当次授权可写；任务结束授权失效。
- 查询与讨论不授权写入；完整方案获批后端到端落盘和复校，不逐步骤重复确认。
- 原件不可覆盖，证据不足标待核；先读源查重再更新或建立真实关联，不堆聊天流水。
- 写回前比对读取时文件SHA-256，变化则重读合并；新文件确认不存在。此为乐观检查，不是原子锁。
- 不设置active/idle写锁、交接板或自动故障接管；若另一任务修改同一文件，协调范围和原执行者停止修改后再接续。
- 适用模块：{', '.join(c['modules']) or '仅基础治理'}；只加载任务相关模块，不默认全量审计。
- 工具：`python3 "{tools}/治理检查.py"`；有原件校验模块时按安装说明创建、核对基线。检查结果不代表事实正确。
- 日常维护直接遵循本库规则，不必再调用初始化Skill；治理升级须重新生成差异方案并批准。
{END}'''
    old = (root/'AGENTS.md').read_text() if (root/'AGENTS.md').is_file() else ''
    if START in old or END in old:
        if old.count(START)!=1 or old.count(END)!=1 or old.index(START)>old.index(END):
            raise ValueError('invalid AGENTS managed block')
        before, tail = old.split(START); _, after = tail.split(END)
        agents = before + block + after
    else: agents = old + ('\n\n' if old else '# AGENTS.md\n\n') + block + '\n'
    files['AGENTS.md'] = agents
    if mode == 'new':
        files[c['full_index']] = '# 知识全量索引\n\n当前无知识页；新页形成后按真实路径登记，来源和治理文件不计入。\n'
        files['目录.md'] = '# 知识库目录\n\n- [知识全量索引]('+c['full_index']+')\n- [结构约定]('+rules+'/结构约定.md)\n'
    files[tools+'/安装与使用.md'] = f'''# 治理安装与使用

安装版本：{VERSION}。此目录工具只依赖Python 3标准库，不依赖原Skill目录或网络。

日常从库根AGENTS.md进入；需要的规范放在 `{rules}`。已有用户规则须人工核对，不把结构检查当语义验收。

运行 `python3 "{tools}/治理检查.py"` 检查本地链接与已配置索引。退出0只说明检查范围内通过；不检查外链、标题锚点或事实真实性。原件目录不作为知识页统计。

启用原件校验时，先运行 `原件校验.py prepare <库外候选JSON>`，核对清单后运行 `原件校验.py commit <同候选JSON>`，再运行 `原件校验.py check`。新增文件需要批准后准备新候选；既有原件改动或丢失不能通过重建基线掩盖。

生成的规则与工具属于本库，可在授权下维护。再次安装遇到用户修改文件时会报冲突，先比较并合并；不强制恢复模板。安装方案目录保存before备份和after候选，包含原有规则内容，不公开上传。执行失败时检查方案的应用结果，不能宣称全部完成。
'''
    return files


def plan(root, mode, custom, output):
    root = root.resolve(); output = output.resolve()
    if not root.is_dir(): raise ValueError('root must exist')
    if output == root or root in output.parents: raise ValueError('plan output must be outside vault')
    c = config_for(root,mode,custom)
    receipt_rel = c['governance_dir']+'/工具/治理安装记录.json'
    receipt_path = local(root,receipt_rel)
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    if mode=='new' and not receipt and any(p.name not in {'.obsidian','.DS_Store'} for p in root.iterdir()):
        raise ValueError('new mode requires empty vault; existing content must use existing mode')
    if receipt and receipt.get('config') != c: raise ValueError('configuration changed; review existing installation before migration')
    files = render(root,mode,c)
    if len(files) != len(set(files)): raise ValueError('duplicate destination')
    output.mkdir(parents=True, exist_ok=False)
    (output/'before').mkdir(); (output/'after').mkdir()
    actions=[]; conflicts=[]; owned=dict(receipt.get('hashes',{}))
    for i,(rel,text) in enumerate(files.items()):
        path=local(root,rel); before=read(path); after=text.encode()
        if rel == c['governance_dir']+'/规范/结构约定.md' and rel in c['existing_rules']:
            continue
        # Existing indexes and home pages are user-maintained after initialization.
        if receipt and rel in {c['full_index'],'目录.md'}: continue
        if before == after: kind='unchanged'
        elif before is None: kind='create'
        elif rel=='AGENTS.md':
            previous=receipt.get('hashes',{}).get(rel)
            kind='merge' if not previous or previous==digest(before) else 'conflict'
        else:
            kind='update' if receipt.get('hashes',{}).get(rel)==digest(before) else 'conflict'
        if kind=='conflict': conflicts.append(rel)
        name=f'{i:03}.txt'; (output/'after'/name).write_bytes(after)
        if before is not None: (output/'before'/name).write_bytes(before)
        actions.append({'path':rel,'action':kind,'before':None if before is None else digest(before),
                        'after':digest(after),'payload':'after/'+name})
        owned[rel]=digest(after)
    receipt_data=json.dumps({'version':VERSION,'config':c,'hashes':owned},ensure_ascii=False,indent=2)+'\n'
    (output/'after/receipt.json').write_text(receipt_data)
    if receipt_path.exists(): (output/'before/receipt.json').write_bytes(receipt_path.read_bytes())
    actions.append({'path':receipt_rel,'action':'update' if receipt else 'create',
                    'before':fingerprint(receipt_path),'after':digest(receipt_data.encode()),'payload':'after/receipt.json'})
    dependencies={r:fingerprint(local(root,r)) for r in c['existing_rules']}
    data={'version':VERSION,'root':str(root),'mode':mode,'config':c,'actions':actions,
          'dependencies':dependencies,'conflicts':conflicts,
          'root_entries':sorted(p.name for p in root.iterdir())}
    (output/'plan.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (output/'方案.md').write_text('# 治理安装方案\n\n根目录：'+str(root)+'\n\n模式：'+mode+'\n\n'+
        '\n'.join('- '+x['action']+'：'+x['path'] for x in actions)+
        '\n\n逐项查看after候选和before备份，核对AGENTS与已有规则语义冲突。确认后才apply；有conflict不可执行。\n')
    return data


def atomic(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.acs-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)


def apply(plan_path, approved):
    if not approved: raise ValueError('user approval required; review plan before --approved')
    data=json.loads(plan_path.read_text()); root=Path(data['root']).resolve()
    if data['version']!=VERSION or data['conflicts']: raise ValueError('unresolved conflicts or unsupported plan')
    config_for(root,data['mode'],data['config'])
    if all(fingerprint(local(root,a['path']))==a['after'] for a in data['actions']):
        return {'installed':0,'root':str(root)}
    if data['mode']=='new' and sorted(p.name for p in root.iterdir())!=data['root_entries']:
        raise ValueError('new vault changed since plan')
    seen=set(); changes=[]
    for rel, expected in data['dependencies'].items():
        if fingerprint(local(root,rel))!=expected: raise ValueError('authority changed: '+rel)
    for a in data['actions']:
        if a['path'] in seen: raise ValueError('duplicate target')
        seen.add(a['path']); p=local(root,a['path'])
        blob=local(plan_path.parent,a['payload']).read_bytes()
        if digest(blob)!=a['after']: raise ValueError('candidate changed: '+a['path'])
        if fingerprint(p)!=a['before']: raise ValueError('target changed: '+a['path'])
        changes.append((p,blob,read(p)))
    if data['mode']=='new':
        for rel in data['config']['knowledge_roots']+data['config']['source_roots']:
            local(root,rel).mkdir(parents=True,exist_ok=True)
    written=[]
    try:
        for p,blob,before in changes:
            if read(p)!=before: raise ValueError('concurrent target change: '+str(p))
            if blob!=before:
                atomic(p,blob); written.append((p,before,digest(blob)))
    except Exception:
        # Restore only files still equal to this install; never overwrite a new concurrent edit.
        for p,before,expected in reversed(written):
            if fingerprint(p)==expected:
                if before is None: p.unlink()
                else: atomic(p,before)
        raise
    return {'installed':len(written),'root':str(root),'note':'semantic review and generated checker still required'}


def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('plan'); p.add_argument('root',type=Path); p.add_argument('--mode',choices=['new','existing'],required=True)
    p.add_argument('--config',type=Path); p.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('apply'); a.add_argument('plan',type=Path); a.add_argument('--approved',action='store_true')
    args=ap.parse_args()
    try:
        result=plan(args.root,args.mode,json.loads(args.config.read_text()) if args.config else {},args.output) if args.command=='plan' else apply(args.plan,args.approved)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as e: ap.exit(2,str(e)+'\n')
if __name__=='__main__': main()
