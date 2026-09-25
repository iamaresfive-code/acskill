import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bootstrap',BASE/'scripts/bootstrap.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)

class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name); self.v=self.home/'vault'; self.v.mkdir()
    def plan(self, mode='new', config=None, name='plan'):
        b.plan(self.v,mode,config or {},self.home/name)
        return self.home/name/'plan.json'
    def run_tool(self,name,*args):
        return subprocess.run([sys.executable,str(self.v/'规范与工具/工具'/name),*map(str,args)],capture_output=True,text=True)
    def test_new_chinese_and_portable(self):
        p=self.plan(config={'modules':['web','files','projects','collaboration','source-hashes']})
        self.assertEqual(list(self.v.iterdir()),[])
        with self.assertRaises(ValueError): b.apply(p,False)
        b.apply(p,True)
        self.assertFalse((self.v/'.second-brain').exists())
        for d in ['知识','原始材料','索引','规范与工具']: self.assertTrue((self.v/d).is_dir())
        result=self.run_tool('治理检查.py'); self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        (self.v/'知识/a.md').write_text('# A\n')
        self.assertEqual(self.run_tool('治理检查.py').returncode,2)
        (self.v/'索引/知识全量索引.md').write_text('# Index\n[[知识/a]]\n')
        self.assertEqual(self.run_tool('治理检查.py').returncode,0)
        (self.v/'索引/知识全量索引.md').write_text('[[知识/a]]\n[[知识/a]]')
        self.assertEqual(self.run_tool('治理检查.py').returncode,2)
    def test_existing_preserved_and_repeat(self):
        for d in ['Notes','Attachments']: (self.v/d).mkdir()
        (self.v/'Notes/n.md').write_text('# N\n')
        (self.v/'Attachments/raw.bin').write_bytes(b'original')
        (self.v/'Index.md').write_text('[[Notes/n]]\n')
        (self.v/'AGENTS.md').write_text('# User rules\nDo not move notes.\n')
        originals={str(p.relative_to(self.v)):p.read_bytes() for p in self.v.rglob('*') if p.is_file()}
        c={'knowledge_roots':['Notes'],'source_roots':['Attachments'],'full_index':'Index.md','existing_rules':['AGENTS.md']}
        p=self.plan('existing',c); b.apply(p,True)
        for rel,content in originals.items():
            if rel=='AGENTS.md': self.assertTrue((self.v/rel).read_bytes().startswith(content))
            else: self.assertEqual((self.v/rel).read_bytes(),content)
        self.assertFalse((self.v/'知识').exists())
        self.assertEqual(b.apply(p,True)['installed'],0)
        p2=self.plan('existing',c,'again'); self.assertEqual(b.apply(p2,True)['installed'],0)
    def test_new_repeat_preserves_index(self):
        b.apply(self.plan(),True)
        (self.v/'索引/知识全量索引.md').write_text('# user index\n')
        p=self.plan(name='again'); self.assertEqual(b.apply(p,True)['installed'],0)
        self.assertEqual((self.v/'索引/知识全量索引.md').read_text(),'# user index\n')
    def test_stale_plan_writes_nothing(self):
        p=self.plan(); (self.v/'unrelated.md').write_text('new work')
        with self.assertRaises(ValueError): b.apply(p,True)
        self.assertEqual(len(list(self.v.iterdir())),1)
    def test_existing_stale_authority(self):
        (self.v/'Notes').mkdir(); (self.v/'Rules.md').write_text('old')
        p=self.plan('existing',{'knowledge_roots':['Notes'],'existing_rules':['Rules.md']})
        (self.v/'Rules.md').write_text('changed')
        with self.assertRaises(ValueError): b.apply(p,True)
        self.assertFalse((self.v/'AGENTS.md').exists())
    def test_modified_owned_file_conflict(self):
        b.apply(self.plan(),True)
        rules=self.v/'规范与工具/规范/知识维护规范.md'; rules.write_text('user edit')
        p=self.plan(name='again')
        self.assertIn('规范与工具/规范/知识维护规范.md',json.loads(p.read_text())['conflicts'])
        with self.assertRaises(ValueError): b.apply(p,True)
        self.assertEqual(rules.read_text(),'user edit')
    def test_same_named_user_rule_reused(self):
        (self.v/'Notes').mkdir(); rules=self.v/'规范与工具/规范/结构约定.md'; rules.parent.mkdir(parents=True); rules.write_text('# User rules')
        p=self.plan('existing',{'knowledge_roots':['Notes'],'existing_rules':['规范与工具/规范/结构约定.md']})
        b.apply(p,True); self.assertEqual(rules.read_text(),'# User rules')
    def test_paths_overlap_and_symlink(self):
        for c in [{'governance_dir':'../outside'},{'governance_dir':'Tools'}, {'source_roots':['知识/raw']},{'full_index':'AGENTS.md'}]:
            with self.subTest(c=c), self.assertRaises(ValueError): self.plan(config=c)
        (self.v/'Notes').symlink_to(self.home)
        with self.assertRaises(ValueError): self.plan('existing',{'knowledge_roots':['Notes']})
    def test_candidate_tampering(self):
        p=self.plan(); data=json.loads(p.read_text()); payload=p.parent/data['actions'][0]['payload']; payload.write_text('changed')
        with self.assertRaises(ValueError): b.apply(p,True)
        self.assertEqual(list(self.v.iterdir()),[])
    def test_source_baseline_stale_and_immutable(self):
        b.apply(self.plan(config={'modules':['source-hashes']}),True)
        source=self.v/'原始材料/a.txt'; source.write_text('one')
        candidate=self.home/'hash.json'
        self.assertEqual(self.run_tool('原件校验.py','prepare',candidate).returncode,0)
        source.write_text('two')
        self.assertNotEqual(self.run_tool('原件校验.py','commit',candidate).returncode,0)
        source.write_text('one')
        self.assertEqual(self.run_tool('原件校验.py','commit',candidate).returncode,0)
        self.assertEqual(self.run_tool('原件校验.py','check').returncode,0)
        source.unlink()
        self.assertNotEqual(self.run_tool('原件校验.py','prepare',self.home/'next.json').returncode,0)
    def test_raw_markdown_not_treated_as_knowledge(self):
        b.apply(self.plan(),True)
        (self.v/'原始材料/raw.md').write_text('[[missing in original]]')
        self.assertEqual(self.run_tool('治理检查.py').returncode,0)
    def test_cli_and_nested_existing_governance(self):
        (self.v/'Notes').mkdir()
        c={'knowledge_roots':['Notes'],'governance_dir':'Admin/Governance'}
        config=self.home/'config.json'; config.write_text(json.dumps(c))
        script=BASE/'scripts/bootstrap.py'
        p=subprocess.run([sys.executable,str(script),'plan',str(self.v),'--mode','existing','--config',str(config),'--output',str(self.home/'cli')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        p=subprocess.run([sys.executable,str(script),'apply',str(self.home/'cli/plan.json'),'--approved'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        p=subprocess.run([sys.executable,str(self.v/'Admin/Governance/工具/治理检查.py')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertFalse((self.v/'Admin/Governance/规范/多Agent协作规范.md').exists())
    def test_apply_failure_restores_written_files(self):
        from unittest.mock import patch
        p=self.plan(); real=b.atomic; count=[0]
        def fail(path,data):
            count[0]+=1
            if count[0]==2: raise OSError('simulated disk failure')
            return real(path,data)
        with patch.object(b,'atomic',fail), self.assertRaises(OSError): b.apply(p,True)
        self.assertFalse(any(x.is_file() for x in self.v.rglob('*')))

if __name__=='__main__': unittest.main()
