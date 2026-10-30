from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import copy
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.guardian.approvals import ApprovalStore, RISK_CATEGORIES, action_record
from igris.guardian.executor import execute
from igris.guardian.policy import Denied, Permission, Policy


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.TemporaryDirectory()
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.project.cleanup)
        self.addCleanup(self.private.cleanup)
        self.root = Path(self.project.name)
        (self.root / 'artifacts').mkdir()
        self.path = Path(self.private.name) / 'approvals.db'
        self.now = time.time()
        self.store = ApprovalStore(self.path, initialize=True, clock=lambda: self.now)
        self.policy = Policy('owner', frozenset(Permission))
        self.action = {'operation': 'file.create', 'arguments': {'path': 'artifacts/result.txt', 'text': 'ordinary new artifact'}}

    def pending(self, action=None, **options):
        return self.store.request(self.policy, self.root, self.action if action is None else action, **options)

    def approved(self, action=None, **options):
        record = self.pending(action, **options)
        self.store.decide(record['id'], approve=True, reviewed_digest=record['action_sha256'])
        return record

    def execute(self, identifier=None, action=None, **options):
        request = copy.deepcopy(self.action if action is None else action)
        if identifier is not None:
            request['approval_id'] = identifier
        return execute(self.policy, self.root, request, approval_store=self.path, **options)

    def test_missing_pending_denied_and_forged_approval_block_execution(self):
        self.assertFalse(self.execute()['ok'])
        self.assertFalse(self.execute('X' * 32)['ok'])
        record = self.pending()
        self.assertFalse(self.execute(record['id'])['ok'])
        self.store.decide(record['id'], approve=False, reviewed_digest=record['action_sha256'])
        self.assertFalse(self.execute(record['id'])['ok'])
        self.assertFalse((self.root / 'artifacts/result.txt').exists())

    def test_exact_approval_executes_once_in_real_broker(self):
        record = self.approved()
        self.assertTrue(self.execute(record['id'])['ok'])
        self.assertEqual((self.root / 'artifacts/result.txt').read_text(), self.action['arguments']['text'])
        self.assertEqual((self.root / 'artifacts/result.txt').stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.execute(record['id'])['ok'])
        with sqlite3.connect(self.path) as db:
            events = [row[0] for row in db.execute('SELECT event FROM audit')]
        self.assertIn('execution_succeeded', events)
        self.assertIn('rejected', events)
        self.assertNotIn(self.action['arguments']['text'].encode(), self.path.read_bytes())

    def test_expired_approval_blocked_at_actual_boundary(self):
        self.now -= 600
        record = self.approved(ttl_seconds=300)
        self.assertFalse(self.execute(record['id'])['ok'])
        self.assertFalse((self.root / 'artifacts/result.txt').exists())

    def test_action_actor_workspace_and_environment_mismatch(self):
        record = self.approved()
        altered = copy.deepcopy(self.action)
        altered['arguments']['text'] = 'different artifact'
        self.assertFalse(self.execute(record['id'], altered)['ok'])
        for policy, root, environment in (
            (Policy('other', frozenset(Permission)), self.root, 'development'),
            (self.policy, Path(self.private.name), 'development'),
            (self.policy, self.root, 'test')):
            with self.subTest(actor=policy.actor, root=root, environment=environment), self.assertRaises(Denied):
                self.store.consume(record['id'], policy, root, self.action, environment=environment)
        self.assertTrue(self.execute(record['id'])['ok'])

    def test_permissions_still_required_with_valid_approval(self):
        record = self.approved()
        response = execute(Policy('owner'), self.root, dict(self.action, approval_id=record['id']), approval_store=self.path)
        self.assertFalse(response['ok'])
        self.assertFalse((self.root / 'artifacts/result.txt').exists())

    def test_all_required_risk_categories_can_request_approval_but_unsupported_actions_stay_blocked(self):
        for operation in RISK_CATEGORIES:
            if operation in ('file.create', 'ops.recovery.fixture'):
                continue
            action = {'operation': operation, 'arguments': {'target': 'synthetic-fixture', 'amount_inr': 0}}
            with self.subTest(operation=operation):
                record = self.approved(action)
                self.assertEqual(record['status'], 'pending')
                self.assertFalse(self.execute(record['id'], action)['ok'])
        self.assertFalse(execute(self.policy, self.root, self.action, environment='production')['ok'])

    def test_no_overwrite_sensitive_code_or_outside_scope_even_after_approval(self):
        (self.root / 'artifacts/result.txt').write_text('existing content')
        record = self.approved()
        self.assertFalse(self.execute(record['id'])['ok'])
        self.assertEqual((self.root / 'artifacts/result.txt').read_text(), 'existing content')
        for path in ('../outside.txt', 'src/config.py', '.env', 'artifacts/code.py'):
            action = copy.deepcopy(self.action)
            action['arguments']['path'] = path
            record = self.approved(action)
            self.assertFalse(self.execute(record['id'], action)['ok'])

    def test_sensitive_write_payload_denied(self):
        action = copy.deepcopy(self.action)
        action['arguments']['text'] = 'password: synthetic fixture'
        record = self.approved(action)
        self.assertFalse(self.execute(record['id'], action)['ok'])

    def test_concurrent_consumption_is_atomic(self):
        record = self.approved()
        def attempt(_):
            try:
                self.store.consume(record['id'], self.policy, self.root, self.action)
                return True
            except Denied:
                return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(pool.map(attempt, range(4))), 1)

    def test_concurrent_real_brokers_execute_once(self):
        record = self.approved()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.execute(record['id']), range(2)))
        self.assertEqual(sum(result['ok'] for result in results), 1)
        self.assertEqual((self.root / 'artifacts/result.txt').read_text(), self.action['arguments']['text'])

    def test_failed_execution_does_not_restore_approval(self):
        record = self.approved()
        (self.root / 'artifacts').rmdir()
        self.assertFalse(self.execute(record['id'])['ok'])
        (self.root / 'artifacts').mkdir()
        self.assertFalse(self.execute(record['id'])['ok'])
        with sqlite3.connect(self.path) as db:
            self.assertIn(('execution_failed',), db.execute('SELECT event FROM audit').fetchall())

    def test_expiry_checked_after_waiting_for_database(self):
        record = self.approved()
        original = self.store._db
        @contextmanager
        def delayed_access():
            with original() as db:
                self.now += 301  # Simulate elapsed time acquiring database access.
                yield db
        self.store._db = delayed_access
        with self.assertRaises(Denied):
            self.store.consume(record['id'], self.policy, self.root, self.action)

    def test_owner_review_digest_expiry_and_denial_are_enforced(self):
        record = self.pending()
        with self.assertRaises(Denied):
            self.store.decide(record['id'], approve=True, reviewed_digest='wrong')
        self.store.decide(record['id'], approve=False, reviewed_digest=record['action_sha256'])
        with self.assertRaises(Denied):
            self.store.decide(record['id'], approve=True, reviewed_digest=record['action_sha256'])
        for ttl in (0, -1, 3601, True, float('nan')):
            with self.assertRaises(Denied):
                self.pending(ttl_seconds=ttl)
        record = self.pending(ttl_seconds=1)
        self.now += 2
        with self.assertRaises(Denied):
            self.store.decide(record['id'], approve=True, reviewed_digest=record['action_sha256'])

    def test_canonical_key_order_and_extra_fields(self):
        action = {'arguments': dict(reversed(list(self.action['arguments'].items()))), 'operation': 'file.create'}
        self.assertEqual(action_record(self.policy, self.root, action), action_record(self.policy, self.root, self.action))
        with self.assertRaises(Denied):
            self.pending(dict(self.action, actor='admin'))

    def test_store_cannot_be_in_workspace_or_world_readable(self):
        local = self.root / 'approvals.db'
        ApprovalStore(local, initialize=True)
        self.assertFalse(execute(self.policy, self.root, self.action, approval_store=local)['ok'])
        os.chmod(self.path, 0o644)
        with self.assertRaises(Denied):
            ApprovalStore(self.path)
        os.chmod(self.path, 0o600)
        link = Path(self.private.name) / 'linked.db'
        link.symlink_to(self.path)
        with self.assertRaises(Denied):
            ApprovalStore(link)
