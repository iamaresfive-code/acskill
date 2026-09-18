"""Regression fixtures for local file link resolution; no real vault writes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'health_check.py'


class HealthLinks(unittest.TestCase):
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
