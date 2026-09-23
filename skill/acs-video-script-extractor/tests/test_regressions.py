"""Behavioral regressions with synthetic artifacts; no ASR models or network needed."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
SOURCE_HASH = 'a' * 64
FINALS = ('逐字稿-校对版.md', '文案-还原整理版.md', '待确认疑点.md')


def put(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def run(script, *args, env=None):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, env=env)


def raw(model, text='金额1.5万元'):
    return {'model': model, 'source_sha256': SOURCE_HASH, 'duration': 3.0,
            'segments': [{'start': 0.0, 'end': 3.0, 'text': text}]}


def artifacts(root):
    results = []
    for model in ('large-v3', 'medium'):
        put(root / f'raw-{model}.json', raw(model))
        (root / f'raw-{model}.txt').write_text('金额1.5万元', encoding='utf-8')
        results.append({'model': model, 'json': f'raw-{model}.json',
                        'timestamped_text': f'raw-{model}.txt'})
    data = {
        'run-manifest.json': {'source_sha256': SOURCE_HASH, 'results': results, 'failures': []},
        'source-probe.json': {'source_sha256': SOURCE_HASH, 'duration': 3.0},
        'review-points.json': {'source_sha256': SOURCE_HASH, 'duration': 3.0,
                               'overall_similarity': 1.0, 'points': []},
    }
    for name, value in data.items():
        put(root / name, value)
    for name in FINALS:
        (root / name).write_text('测试交付内容', encoding='utf-8')
    return data


class NumericDifferences(unittest.TestCase):
    def compare(self, first, second):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            put(root / 'first.json', raw('large-v3', first))
            put(root / 'second.json', raw('medium', second))
            result = run('compare_transcripts.py', root / 'first.json', root / 'second.json',
                         '--output-dir', root)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads((root / 'review-points.json').read_text(encoding='utf-8'))

    def test_numeric_symbols_trigger_high_risk_review(self):
        for first, second in [('金额1.5万元', '金额15万元'), ('下降-5%', '下降5%'),
                              ('涨幅5%', '涨幅5'), ('增量+5', '增量-5'),
                              ('利率5‰', '利率5%'), ('金额.5万元', '金额5万元')]:
            with self.subTest(first=first, second=second):
                points = self.compare(first, second)['points']
                self.assertTrue(points)
                self.assertTrue(any(p['priority'] == 'high' and '数字/日期风险' in p['reasons'] for p in points))

    def test_prose_punctuation_and_unicode_equivalence(self):
        self.assertEqual(self.compare('你好，世界！', '你好世界。')['points'], [])
        self.assertEqual(self.compare('金额１．５，下降−５％', '金额1.5下降-5%')['points'], [])


class OutputValidation(unittest.TestCase):
    def test_valid_zero_difference_delivery(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifacts(root)
            for options in ((), ('--machine-only',)):
                result = run('validate_outputs.py', root, *options)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hashes_are_required_and_must_match(self):
        names = ('run-manifest.json', 'source-probe.json', 'review-points.json',
                 'raw-large-v3.json', 'raw-medium.json')
        for name in names:
            for value in (None, '', 'abc123', 'b' * 64):
                with self.subTest(name=name, value=value), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    artifacts(root)
                    data = json.loads((root / name).read_text(encoding='utf-8'))
                    data['source_sha256'] = value
                    put(root / name, data)
                    result = run('validate_outputs.py', root)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertNotIn('PASS', result.stdout)

    def test_duplicates_and_raw_model_mismatch(self):
        for case in ('duplicate-model', 'duplicate-json', 'duplicate-text', 'raw-model-mismatch'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                data = artifacts(root)
                results = data['run-manifest.json']['results']
                if case == 'duplicate-model':
                    results[1]['model'] = results[0]['model']
                    put(root / 'raw-medium.json', raw('large-v3'))
                elif case == 'raw-model-mismatch':
                    put(root / 'raw-medium.json', raw('unexpected'))
                else:
                    key = 'json' if case == 'duplicate-json' else 'timestamped_text'
                    results[1][key] = results[0][key]
                put(root / 'run-manifest.json', data['run-manifest.json'])
                result = run('validate_outputs.py', root)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_malformed_review_and_raw_objects_fail_cleanly(self):
        cases = [('review-points.json', {}), ('review-points.json', {'points': []}),
                 ('review-points.json', {'source_sha256': SOURCE_HASH, 'duration': 3,
                  'overall_similarity': 1, 'points': [{}]}),
                 ('review-points.json', {'source_sha256': SOURCE_HASH, 'duration': 3,
                  'overall_similarity': 1, 'points': [{'first_model': []}]}),
                 ('raw-medium.json', []), ('run-manifest.json', {'results': [None, None]}),
                 ('run-manifest.json', {'results': [], 'failures': 3})]
        for name, value in cases:
            with self.subTest(name=name, value=value), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                artifacts(root)
                put(root / name, value)
                result = run('validate_outputs.py', root)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('FAIL', result.stdout)
                self.assertNotIn('Traceback', result.stderr)


class RuntimeSelection(unittest.TestCase):
    def test_configured_venv_keeps_its_site_packages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            env_root = root / 'venv'
            venv.EnvBuilder(with_pip=False, symlinks=os.name != 'nt').create(env_root)
            python = env_root / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            site = subprocess.check_output([str(python), '-c',
                'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip()
            # A local stand-in tests interpreter selection, not model accuracy.
            (Path(site) / 'faster_whisper.py').write_text(
                'from types import SimpleNamespace\n'
                'class WhisperModel:\n'
                '    def __init__(self, *args, **kwargs): pass\n'
                '    def transcribe(self, *args, **kwargs):\n'
                '        return [SimpleNamespace(start=0, end=3, text="test")], '
                'SimpleNamespace(language="zh", language_probability=1, duration=3)\n',
                encoding='utf-8')
            env = os.environ.copy()
            env.pop('ACS_TRANSCRIPT_REEXEC', None)
            env.pop('PYTHONPATH', None)
            env['ACS_TRANSCRIBE_PYTHON'] = str(python)
            source = root / 'source.wav'
            source.write_bytes(b'fixture')
            result = run('transcribe_local.py', source, '--output-dir', root / 'out', env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manifest = json.loads((root / 'out/run-manifest.json').read_text(encoding='utf-8'))
            self.assertEqual({item['model'] for item in manifest['results']}, {'large-v3', 'medium'})

    def test_duplicate_models_rejected_before_transcription(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source.wav'
            source.write_bytes(b'fixture')
            result = run('transcribe_local.py', source, '--output-dir', Path(temp) / 'out',
                         '--models', 'medium,medium')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('模型名称不能重复', result.stderr)
            self.assertFalse((Path(temp) / 'out').exists())


if __name__ == '__main__':
    unittest.main()
