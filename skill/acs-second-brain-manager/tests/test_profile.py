"""Schema regressions using isolated temporary profiles."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]

class Profiles(unittest.TestCase):
    def check_profile(self, text, expected):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'profile.yaml'
            path.write_text(text, encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_profile.py'), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0 if expected else 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)['valid'], expected)
            self.assertEqual(path.read_text(encoding='utf-8'), text)

    def test_schema(self):
        base = yaml.safe_load((ROOT / 'templates/profile.yaml').read_text(encoding='utf-8'))
        base['knowledge_base']['name'] = 'Demo'
        self.check_profile(yaml.safe_dump(base), True)
        for section, field in [('governance','write_mode'), ('knowledge_base','root'), ('sources','immutable'), ('markdown','frontmatter'), ('concurrency','mode')]:
            for value in (None, [], {}, '', 'invalid', 1):
                if field == 'root' and value == 'invalid': continue
                with self.subTest(section=section, field=field, value=value):
                    data = yaml.safe_load(yaml.safe_dump(base))
                    data[section][field] = value
                    self.check_profile(yaml.safe_dump(data), False)
        del base['governance']['write_mode']
        base['write_mode'] = 'confirm-first'
        self.check_profile(yaml.safe_dump(base), False)

    def test_invalid_yaml(self):
        for text in ('x: [', '[]', '', 'a: 1\na: 2\n'):
            with self.subTest(text=text): self.check_profile(text, False)

if __name__ == '__main__': unittest.main()
