from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.projects import KINDS, plan_project, create_sample
from igris.guardian.policy import Policy, Permission, Denied


class ProjectTests(unittest.TestCase):
    def test_plans_cover_requested_kinds_with_honest_scope(self):
        for kind in KINDS:
            plan = plan_project('sample', kind)
            self.assertEqual(plan.kind, kind)
            self.assertTrue(plan.limitations)
        with self.assertRaises(ValueError): plan_project('../outside', 'website')

    def test_real_disposable_generation_no_overwrite_or_unauthorized_write(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            plan = plan_project('sample', 'website')
            with self.assertRaises(Denied): create_sample(parent, plan, Policy('owner'))
            self.assertEqual(list(parent.iterdir()), [])
            policy = Policy('owner', frozenset({Permission.FILE_MODIFY}))
            root = create_sample(parent, plan, policy)
            self.assertIn('<h1>', (root / 'index.html').read_text())
            with self.assertRaises(FileExistsError): create_sample(parent, plan, policy)
            with self.assertRaises(ValueError): create_sample(parent, plan_project('api', 'api'), policy)
