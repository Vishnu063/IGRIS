import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.guardian.executor import execute
from igris.guardian.policy import Permission, Policy


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / 'note.txt').write_text('ordinary fixture')
        self.policy = Policy('owner', frozenset(Permission))

    def run_action(self, operation, **args):
        return execute(self.policy, self.root, {'operation': operation, 'arguments': args})

    def test_real_broker_read_and_fixed_subprocess(self):
        self.assertEqual(self.run_action('file.read', path='note.txt')['result']['text'], 'ordinary fixture')
        self.assertTrue(self.run_action('python.version')['result']['version'].startswith('Python '))

    def test_injection_cannot_execute(self):
        for request in (
            {'operation': 'shell', 'arguments': {'command': 'touch injected'}},
            {'operation': 'python.version', 'arguments': {'argv': ['-c', 'print(1)']}},
            {'operation': 'python.version;touch injected', 'arguments': {}},
            {'operation': 'file.read', 'arguments': {'path': 'note.txt'}, 'actor': 'admin'},
            {'operation': 'python.version', 'arguments': {}, 'permissions': ['terminal']},
        ):
            with self.subTest(request=request):
                self.assertFalse(execute(self.policy, self.root, request)['ok'])
        self.assertFalse((self.root / 'injected').exists())

    def test_traversal_symlink_and_hardlink_denied(self):
        (self.root / 'link.txt').symlink_to(self.root / 'note.txt')
        os.link(self.root / 'note.txt', self.root / 'hard.txt')
        (self.root / 'sub').symlink_to(self.root, target_is_directory=True)
        for path in ('../note.txt', '/etc/passwd', '.env', 'sub/note.txt', 'link.txt', 'hard.txt',
                     'secret.txt', 'note.txt;touch injected', 'a//b.txt'):
            with self.subTest(path=path):
                self.assertFalse(self.run_action('file.read', path=path)['ok'])

    def test_resource_and_schema_bounds(self):
        (self.root / 'big.txt').write_text('x' * 8193)
        self.assertFalse(self.run_action('file.read', path='big.txt')['ok'])
        self.assertFalse(execute(self.policy, self.root, {'x': 'x' * 17000})['ok'])
        os.mkfifo(self.root / 'pipe.txt')
        self.assertFalse(self.run_action('file.read', path='pipe.txt')['ok'])
        self.assertFalse(self.run_action('file.create', path='new.txt', text='data')['ok'])

    def test_missing_permissions_and_unsupported_actions(self):
        result = execute(Policy('owner'), self.root, {'operation': 'file.read', 'arguments': {'path': 'note.txt'}})
        self.assertFalse(result['ok'])
        for operation in ('deployment.production', 'financial.transaction', 'message.send', 'file.delete'):
            self.assertFalse(self.run_action(operation)['ok'])

    def test_environment_and_cwd_import_poisoning_not_inherited(self):
        (self.root / 'sitecustomize.py').write_text("raise RuntimeError('injected')")
        with patch.dict(os.environ, {'PYTHONPATH': str(self.root), 'PYTHONSTARTUP': str(self.root / 'sitecustomize.py')}):
            self.assertTrue(self.run_action('python.version')['ok'])

    def test_timeout_kills_broker_and_fails_closed(self):
        # Test double covers the timeout branch; not a real service performance test.
        with patch('igris.guardian.executor.subprocess.Popen') as spawn, patch('igris.guardian.executor.os.killpg') as kill:
            process = spawn.return_value
            process.pid = 12345
            process.communicate.side_effect = [subprocess.TimeoutExpired('test', 3), (b'', b'')]
            response = self.run_action('python.version')
            self.assertFalse(response['ok'])
            kill.assert_called_once()

    def test_real_worker_has_resource_limits(self):
        # Independent OS inspection of the same limit setup, in a child process.
        code = "import resource; from igris.guardian.broker import apply_limits; apply_limits(); print(resource.getrlimit(resource.RLIMIT_CPU)[0], resource.getrlimit(resource.RLIMIT_AS)[0], resource.getrlimit(resource.RLIMIT_NOFILE)[0])"
        source = Path(__file__).resolve().parents[1] / 'src'
        output = subprocess.check_output([sys.executable, '-c', code], env={'PYTHONPATH': str(source)}, text=True)
        self.assertEqual(output.strip(), '2 268435456 64')
