import json
import re
import unittest
from pathlib import Path

from backend.catalog import CONTESTS


class ContestEnglishNamesTests(unittest.TestCase):
    def test_english_names_cover_the_current_catalog(self):
        script = (Path(__file__).resolve().parents[1] / 'frontend' / 'contest-translations.js').read_text(encoding='utf-8')
        match = re.search(r'const byId = (\{[\s\S]*?\});\s*const byChinese', script)
        self.assertIsNotNone(match)
        translations = json.loads(match.group(1))
        self.assertEqual(set(translations), {c['id'] for c in CONTESTS})
        for contest in CONTESTS:
            with self.subTest(contest=contest['id']):
                english = translations[contest['id']]
                self.assertEqual(english['zhName'], contest['name'])
                self.assertEqual(english['zhShort'], contest['short'])
                self.assertEqual(english['zhReason'], contest['fit_reason'])
                self.assertTrue(english['name'].strip())
                self.assertIn(english['sourceKind'], {'organizer', 'organizer-republished', 'institution', 'institution-plus-track', 'working'})


if __name__ == '__main__':
    unittest.main()
