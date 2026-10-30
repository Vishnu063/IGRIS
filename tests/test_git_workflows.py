from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.git_workflows import GitWorkflow
from igris.guardian.policy import Policy, Permission, Denied


class GitWorkflowTests(unittest.TestCase):
    def policy(self): return Policy('owner', frozenset({Permission.GIT, Permission.FILE_MODIFY}))
    def test_branch_commit_review_pr_and_revert_in_real_disposable_repo(self):
        with tempfile.TemporaryDirectory() as d:
            repo = GitWorkflow.initialize(d, 'sample', self.policy())
            file = repo.root / 'note.txt'; file.write_text('first\n')
            self.assertIn('+first', repo.prepare(['note.txt']))
            repo.commit('Initial development baseline')
            repo.branch('feature')
            file.write_text('second\n'); repo.prepare(['note.txt'])
            head = repo.commit('Change sample')
            self.assertFalse(repo.pull_request_draft()['submitted'])
            self.assertFalse(repo.conflicts())
            repo.rollback(head)
            self.assertEqual(file.read_text(), 'first\n')
            with self.assertRaises(ValueError): repo.rollback(head)
            with self.assertRaises(ValueError): repo.branch('--delete')
            with self.assertRaises(ValueError): repo.prepare(['../outside'])
    def test_actual_conflict_is_detected(self):
        with tempfile.TemporaryDirectory() as d:
            repo = GitWorkflow.initialize(d, 'sample', self.policy())
            file = repo.root / 'note.txt'; file.write_text('base\n')
            repo.prepare(['note.txt']); repo.commit('Baseline'); repo.branch('feature')
            file.write_text('feature\n'); repo.prepare(['note.txt']); repo.commit('Feature')
            repo._git('switch', 'main')
            file.write_text('main\n'); repo.prepare(['note.txt']); repo.commit('Main')
            with self.assertRaises(subprocess.CalledProcessError): repo._git('merge', '--no-edit', 'feature')
            self.assertTrue(repo.conflicts())
            with self.assertRaises(ValueError): repo.commit('Unresolved conflict')
    def test_default_policy_denies(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(Denied): GitWorkflow.initialize(d, 'sample', Policy('owner'))
