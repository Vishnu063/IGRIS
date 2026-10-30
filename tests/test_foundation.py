"""Verify foundation Git behavior in a disposable repository."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FoundationTests(unittest.TestCase):
    def test_layout(self):
        for name in ('README.md', '.gitignore', 'src/igris', 'tests',
                     'docs/governance/branches.md', 'docs/execution/step-01.md'):
            with self.subTest(path=name):
                self.assertTrue((ROOT / name).exists())

    def test_disposable_git_and_ignore_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.run(['git', *args], cwd=directory, check=True,
                                      capture_output=True, text=True).stdout
            git('init', '--initial-branch=main')
            path = Path(directory)
            (path / '.gitignore').write_text((ROOT / '.gitignore').read_text())
            for name in ('.env', '.env.production', 'private.key', 'state.sqlite3'):
                (path / name).touch()
                self.assertEqual(git('check-ignore', name).strip(), name)
            (path / '.env.example').write_text('PLACEHOLDER_ONLY=1\n')
            self.assertIn('.env.example', git('ls-files', '--others', '--exclude-standard'))
            git('add', '.gitignore', '.env.example')
            git('-c', 'user.name=IGRIS Test', '-c', 'user.email=test@example.invalid',
                '-c', 'commit.gpgsign=false', 'commit', '-m', 'Disposable verification')
            git('switch', '-c', 'develop')
            self.assertEqual(git('branch', '--show-current').strip(), 'develop')
            self.assertEqual(git('status', '--porcelain'), '')
            self.assertTrue(git('rev-parse', '--verify', 'HEAD').strip())


if __name__ == '__main__':
    unittest.main()
