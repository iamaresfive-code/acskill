"""Positive/negative regressions for the September 26 audit, no model downloads."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from test_regressions import artifacts, raw, put, run, SCRIPTS, SOURCE_HASH

spec=importlib.util.spec_from_file_location('frames',SCRIPTS/'extract_review_frames.py')
frames=importlib.util.module_from_spec(spec); spec.loader.exec_module(frames)

class AuditFixes(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def scenario(self,segments,duration):
        artifacts(self.root)
        for model in ('large-v3','medium'):
            data=raw(model);data.update(segments=segments,duration=duration);put(self.root/f'raw-{model}.json',data)
        for filename in ('source-probe.json','review-points.json'):
            p=self.root/filename; data=json.loads(p.read_text());data['duration']=duration;put(p,data)
    def test_raw_and_review_time_bounds(self):
        self.scenario([{'start':900,'end':1000,'text':'bad'}],3)
        p=run('validate_outputs.py',self.root); self.assertNotEqual(p.returncode,0);self.assertIn('超出媒体时长',p.stdout)
        self.scenario([{'start':0,'end':3.05,'text':'rounding tolerance'}],3)
        self.assertEqual(run('validate_outputs.py',self.root).returncode,0)
        review=json.loads((self.root/'review-points.json').read_text())
        review['points']=[{'id':'Q1','start':0,'end':999,'frame_time':1,'first_model':'large-v3','second_model':'medium','first_diff':'甲','second_diff':'乙'}]
        put(self.root/'review-points.json',review)
        p=run('validate_outputs.py',self.root);self.assertNotEqual(p.returncode,0);self.assertIn('超出媒体时长',p.stdout)
    def test_review_duration_bound(self):
        artifacts(self.root);p=self.root/'review-points.json';data=json.loads(p.read_text());data['duration']=600;put(p,data)
        out=run('validate_outputs.py',self.root);self.assertNotEqual(out.returncode,0);self.assertIn('时长与媒体时长不一致',out.stdout)
    def test_common_gap_requires_review_not_automatic_speech_claim(self):
        self.scenario([{'start':0,'end':1,'text':'开始'},{'start':599,'end':600,'text':'结束'}],600)
        p=run('validate_outputs.py',self.root);self.assertNotEqual(p.returncode,0);self.assertIn('双模型共同空缺候选',p.stdout)
        p=run('validate_outputs.py',self.root,'--machine-only');self.assertEqual(p.returncode,0);self.assertIn('长空缺候选',p.stdout)
        hashes={m:hashlib.sha256((self.root/f'raw-{m}.json').read_bytes()).hexdigest() for m in ('large-v3','medium')}
        review={'source_sha256':SOURCE_HASH,'input_sha256':hashes,'gaps':[{'model':m,'start':1,'end':599,'status':'silence','reason':'test fixture contains silence','evidence':'reviewed synthetic interval'} for m in hashes]}
        put(self.root/'coverage-review.json',review)
        self.assertEqual(run('validate_outputs.py',self.root).returncode,0)
        data=json.loads((self.root/'raw-medium.json').read_text());data['segments'][0]['text']='changed';put(self.root/'raw-medium.json',data)
        p=run('validate_outputs.py',self.root);self.assertNotEqual(p.returncode,0);self.assertIn('当前模型原稿不一致',p.stdout)
    def test_head_gap_and_short_gap(self):
        self.scenario([{'start':20,'end':30,'text':'hello'}],30)
        self.assertNotEqual(run('validate_outputs.py',self.root).returncode,0)
        self.scenario([{'start':0,'end':1,'text':'a'},{'start':16,'end':30,'text':'b'}],30)
        self.assertEqual(run('validate_outputs.py',self.root).returncode,0)
    def test_generated_review_window_clips_to_probe(self):
        artifacts(self.root)
        first=raw('large-v3','甲');first['duration']=3.2
        second=raw('medium','乙');second['duration']=3.2
        put(self.root/'raw-large-v3.json',first);put(self.root/'raw-medium.json',second)
        p=run('compare_transcripts.py',self.root/'raw-large-v3.json',self.root/'raw-medium.json','--output-dir',self.root)
        self.assertEqual(p.returncode,0,p.stderr)
        review=json.loads((self.root/'review-points.json').read_text())
        self.assertEqual(review['duration'],3)
        self.assertTrue(all(0 <= x['start'] <= x['frame_time'] <= x['end'] <= 3 for x in review['points']))
        self.assertEqual(run('validate_outputs.py',self.root).returncode,0)
    def test_blank_gap_review_does_not_clear_candidate(self):
        self.scenario([{'start':20,'end':30,'text':'hello'}],30)
        hashes={m:hashlib.sha256((self.root/f'raw-{m}.json').read_bytes()).hexdigest() for m in ('large-v3','medium')}
        review={'source_sha256':SOURCE_HASH,'input_sha256':hashes,'gaps':[{'model':m,'start':0,'end':20,'status':'silence','reason':'','evidence':''} for m in hashes]}
        put(self.root/'coverage-review.json',review)
        p=run('validate_outputs.py',self.root)
        self.assertNotEqual(p.returncode,0);self.assertIn('缺少复核结论或依据',p.stdout)
    def frame_case(self,id='Q001',source_hash=None,existing=False):
        video=self.root/'video.mp4';video.write_bytes(b'synthetic video')
        digest=hashlib.sha256(video.read_bytes()).hexdigest()
        review=self.root/'review.json';put(review,{'source_sha256':source_hash or digest,'duration':1,'points':[{'id':id,'start':0,'end':1,'frame_time':0.5}]})
        output=self.root/'frames'
        if existing: output.mkdir();(output/'old.png').write_bytes(b'old')
        def fake_ffmpeg(command,**kwargs):
            self.assertIn('-n',command);Path(command[-1]).write_bytes(b'fake PNG');return subprocess.CompletedProcess(command,0)
        argv=['extract',str(video),str(review),'--output-dir',str(output),'--offsets','0']
        with patch.object(sys,'argv',argv),patch.object(frames,'find_ffmpeg',return_value='ffmpeg'),patch.object(frames.subprocess,'run',side_effect=fake_ffmpeg) as call:
            try: value=frames.main();failure=None
            except SystemExit as e: value=None;failure=str(e)
        return value,failure,call.call_count,output,digest
    def test_frame_escape_and_source_mismatch_reject_before_writes(self):
        outside=self.root/'escape-1-0.50s.png';outside.write_bytes(b'old')
        for invalid in ('../escape','/tmp/escape','..\\escape'):
            _,error,calls,output,_=self.frame_case(id=invalid)
            self.assertIn('安全标识',error);self.assertEqual(calls,0);self.assertFalse(output.exists())
        self.assertEqual(outside.read_bytes(),b'old')
        _,error,calls,output,_=self.frame_case(source_hash='b'*64)
        self.assertIn('来源哈希不匹配',error);self.assertEqual(calls,0);self.assertFalse(output.exists())
    def test_valid_frame_manifest_and_existing_output(self):
        result,error,calls,output,digest=self.frame_case()
        self.assertEqual(result,0);self.assertIsNone(error);self.assertEqual(calls,1)
        self.assertEqual(json.loads((output/'frames-manifest.json').read_text())['source_sha256'],digest)
        _,error,calls,_,_=self.frame_case()
        self.assertIn('不覆盖',error);self.assertEqual(calls,0)
    def test_transcription_preserves_old_and_allows_probe_only(self):
        source=self.root/'source.wav';source.write_bytes(b'fixture');output=self.root/'out';output.mkdir()
        (output/'raw-large-v3.json').write_text('old')
        p=run('transcribe_local.py',source,'--output-dir',output)
        self.assertNotEqual(p.returncode,0);self.assertIn('不会覆盖',p.stderr)
        self.assertEqual((output/'raw-large-v3.json').read_text(),'old');self.assertFalse((output/'run-manifest.json').exists())
        fresh=self.root/'fresh';fresh.mkdir();(fresh/'source-probe.json').write_text('preflight')
        mock=self.root/'mock';mock.mkdir();(mock/'faster_whisper.py').write_text('from types import SimpleNamespace\nclass WhisperModel:\n def __init__(self,*a,**k): pass\n def transcribe(self,*a,**k): return [SimpleNamespace(start=0,end=3,text="new")],SimpleNamespace(language="zh",language_probability=1,duration=3)\n')
        env=os.environ.copy();env['PYTHONPATH']=str(mock)
        p=run('transcribe_local.py',source,'--output-dir',fresh,env=env);self.assertEqual(p.returncode,0,p.stderr)
        before={p.name:p.read_bytes() for p in fresh.iterdir()}
        p=run('transcribe_local.py',source,'--output-dir',fresh,env=env);self.assertNotEqual(p.returncode,0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in fresh.iterdir()})

if __name__=='__main__': unittest.main()
