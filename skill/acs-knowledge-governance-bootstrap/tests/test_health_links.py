"""Regression fixtures for local file link resolution; no real vault writes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'health_check.py'


class HealthLinks(unittest.TestCase):
    def test_attachment_names_and_ambiguity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for rel in ('assets/chart.png', 'assets/report.pdf', 'assets/my image.png',
                        'a/duplicate.png', 'b/duplicate.png'):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
            (root / 'index.md').write_text(
                '![[chart.png]] [[report.pdf]] ![[my%20image.png]] '
                '![[duplicate.png]] ![[assets/chart.png]] ![[missing.png]]', encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPT), str(root)],
                                    capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            self.assertEqual(data['markdown_pages'], 1)
            self.assertEqual(data['signals']['broken_wikilinks'],
                             [{'from': 'index.md', 'target': 'missing.png'}])
            ambiguous = data['signals']['ambiguous_links']
            self.assertEqual(len(ambiguous), 1)
            self.assertEqual(ambiguous[0]['from'], 'index.md')
            self.assertEqual(ambiguous[0]['target'], 'duplicate.png')
            self.assertEqual(set(ambiguous[0]['candidates']), {'a/duplicate.png', 'b/duplicate.png'})

    def test_paths_extensions_markdown_and_examples(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = {
                'index.md': '''[[a/note.md]] [[missing/note]] [[note]]
[[a/方案v1.2]] [[a/方案v1.2.md]] [[方案v1.2]]
[space](<a/with space.md>) [encoded](a/with%20space.md#heading)
[nested](a/file(1).md) [bad](missing.md)
![asset](a/pic.png) [web](https://example.com/a) [self](#title)
`[[inline-missing]]` `[ignored](inline-missing.md)`
```md
[[fenced-missing]] [ignored](fenced-missing.md)
```
''',
                'a/note.md': '[[note.md]] [relative](../index.md)\n',
                'b/note.md': '# Other\n',
                'a/with space.md': '# Space\n',
                'a/file(1).md': '# Parentheses\n',
                'a/pic.png': 'fixture',
                'a/方案v1.2.md': '# Dotted name\n',
            }
            for rel, content in files.items():
                dest = root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding='utf-8')
            before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            result = subprocess.run([sys.executable, str(SCRIPT), str(root)],
                                    capture_output=True, text=True, check=True)
            signals = json.loads(result.stdout)['signals']
            self.assertEqual(signals['broken_wikilinks'], [{'from': 'index.md', 'target': 'missing/note'}])
            self.assertEqual(signals['broken_markdown_links'], [{'from': 'index.md', 'target': 'missing.md'}])
            self.assertEqual(len(signals['ambiguous_links']), 1)
            self.assertEqual(set(signals['ambiguous_links'][0]['candidates']), {'a/note.md', 'b/note.md'})
            self.assertNotIn('a/with space.md', signals['orphan_pages'])
            self.assertNotIn('a/file(1).md', signals['orphan_pages'])
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*') if p.is_file()})


if __name__ == '__main__':
    unittest.main()
