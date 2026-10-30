import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from igris.business_tools import CATALOG, recommend


class BusinessToolsTests(unittest.TestCase):
    def test_all_twenty_have_actual_license_evidence(self):
        evidence = json.loads((ROOT/'docs/integrations/business-tool-evidence.json').read_text())
        self.assertEqual(len(CATALOG), 20)
        self.assertEqual(len({t.name for t in CATALOG}), 20)
        self.assertEqual(len(evidence), 20)
        for row in evidence:
            self.assertEqual(len(row['license']['git_blob']), 40)
            self.assertTrue(row['license']['url'].startswith('https://github.com/'))

    def test_requirements_do_not_authorize_install_or_spending(self):
        tools = recommend('workflows')
        self.assertEqual([t['name'] for t in tools], ['n8n', 'Activepieces'])
        self.assertTrue(all(not t['activation_authorized'] and not t['expense_verified'] for t in tools))
        with self.assertRaises(ValueError): recommend('install_everything')
