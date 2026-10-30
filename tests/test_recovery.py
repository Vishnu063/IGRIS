from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.adapters.contracts import AdapterUnavailable
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Permission, Policy
from igris.recovery import LiveOpsRecovery, SimulatedRecovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.TemporaryDirectory()
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.project.cleanup)
        self.addCleanup(self.private.cleanup)
        self.root = Path(self.project.name)
        (self.root / 'fixtures').mkdir(mode=0o700)
        self.state_path = self.root / 'fixtures/ops-state.json'
        self.lock = self.root / 'fixtures/ops.lock'
        self.lock.touch(mode=0o600)
        self.state = {'simulation': True, 'context': 'default', 'container_id': 'a' * 64,
                      'daemon_id': 'fixture-daemon', 'health_url': 'http://127.0.0.1:8080/',
                      'container_state': 'exited', 'healthy': False, 'maintenance': False,
                      'plan': {'id': 'b' * 32, 'approved': False, 'used': False, 'expires_at': time.time() + 300,
                               'command': ['docker', '--context', 'default', 'container', 'restart', '--time', '10', 'a' * 64]},
                      'scenario': 'success', 'dispatch_count': 0}
        self.save()
        self.approvals = ApprovalStore(Path(self.private.name) / 'approvals.db', initialize=True)
        self.policy = Policy('owner', frozenset({Permission.CLOUD, Permission.READ, Permission.FILE_MODIFY}))
        self.recovery = SimulatedRecovery(self.policy, self.root, self.approvals)

    def save(self):
        self.state_path.write_text(json.dumps(self.state, sort_keys=True))
        self.state_path.chmod(0o600)

    def arguments(self):
        return {'plan_id': 'b' * 32, 'state_sha256': hashlib.sha256(self.state_path.read_bytes()).hexdigest(),
                'context': 'default', 'container_id': 'a' * 64, 'daemon_id': 'fixture-daemon',
                'health_url': 'http://127.0.0.1:8080/'}

    def provider_approve(self):
        # Explicit synthetic owner decision in the simulated provider, never live.
        self.state['plan']['approved'] = True
        self.save()

    def guardian_decision(self, args, approve=True):
        record = self.recovery.request(args)
        self.approvals.decide(record['id'], approve=approve, reviewed_digest=record['action_sha256'])
        return record['id']

    def current(self):
        return json.loads(self.state_path.read_text())

    def test_separate_provider_and_guardian_approvals_required(self):
        args = self.arguments()
        record = self.guardian_decision(args)
        self.assertFalse(self.recovery.run(args, record).verified)
        self.assertEqual(self.current()['dispatch_count'], 0)
        self.provider_approve()
        args = self.arguments()
        self.assertFalse(self.recovery.run(args).verified)
        pending = self.recovery.request(args)
        self.assertFalse(self.recovery.run(args, pending['id']).verified)
        self.assertEqual(self.current()['dispatch_count'], 0)

    def test_approved_recovery_verifies_state_and_health_and_audits(self):
        self.provider_approve()
        args = self.arguments()
        approval = self.guardian_decision(args)
        self.assertEqual(self.current()['dispatch_count'], 0)  # approval is not dispatch
        result = self.recovery.run(args, approval)
        self.assertEqual((result.status, result.origin, result.verified), ('verified', 'simulated', True))
        self.assertTrue(result.container_running and result.application_healthy)
        self.assertFalse(result.retry_allowed)
        self.assertEqual(self.current()['dispatch_count'], 1)
        self.assertFalse(self.recovery.run(args, approval).verified)
        with sqlite3.connect(self.approvals.path) as db:
            self.assertIn(('execution_succeeded',), db.execute('SELECT event FROM audit').fetchall())

    def test_denied_forged_and_expired_guardian_approvals_do_not_dispatch(self):
        self.provider_approve()
        args = self.arguments()
        denied = self.guardian_decision(args, False)
        self.assertFalse(self.recovery.run(args, denied).verified)
        self.assertFalse(self.recovery.run(args, 'x' * 32).verified)
        self.approvals.clock = lambda: time.time() - 600
        expired = self.guardian_decision(args)
        self.assertFalse(self.recovery.run(args, expired).verified)
        self.assertEqual(self.current()['dispatch_count'], 0)

    def test_maintenance_expired_plan_and_altered_command_are_denied(self):
        for kind in ('maintenance', 'expired', 'command', 'not_simulation'):
            self.set_fixture(kind)
            args = self.arguments()
            approval = self.guardian_decision(args)
            with self.subTest(kind=kind):
                self.assertFalse(self.recovery.run(args, approval).verified)
                self.assertEqual(self.current()['dispatch_count'], 0)

    def set_fixture(self, kind):
        self.state['maintenance'] = kind == 'maintenance'
        self.state['simulation'] = kind != 'not_simulation'
        self.state['plan']['approved'] = True
        self.state['plan']['expires_at'] = time.time() + (-1 if kind == 'expired' else 300)
        self.state['plan']['command'] = ['sh', '-c', 'untrusted'] if kind == 'command' else [
            'docker', '--context', 'default', 'container', 'restart', '--time', '10', 'a' * 64]
        self.save()

    def test_changed_identity_or_state_digest_invalidates_approval(self):
        self.provider_approve()
        args = self.arguments()
        approval = self.guardian_decision(args)
        self.state['container_id'] = 'c' * 64
        self.save()
        self.assertFalse(self.recovery.run(args, approval).verified)
        changed = self.arguments()
        changed['state_sha256'] = hashlib.sha256(self.state_path.read_bytes()).hexdigest()
        self.assertFalse(self.recovery.run(changed, approval).verified)
        self.assertEqual(self.current()['dispatch_count'], 0)

    def test_running_container_with_failed_endpoint_is_not_recovery(self):
        self.provider_approve()
        self.state['scenario'] = 'health_failure'
        self.save()
        args = self.arguments()
        result = self.recovery.run(args, self.guardian_decision(args))
        self.assertEqual(result.status, 'needs_attention')
        self.assertTrue(result.container_running)
        self.assertFalse(result.application_healthy)
        self.assertFalse(result.verified)

    def test_failure_and_unknown_outcome_consume_without_automatic_retry(self):
        for scenario, expected in (('dispatch_failure', 'failed'), ('unknown_outcome', 'unknown')):
            self.state['scenario'] = scenario
            self.state['plan']['used'] = False
            self.state['dispatch_count'] = 0
            self.provider_approve()
            args = self.arguments()
            approval = self.guardian_decision(args)
            result = self.recovery.run(args, approval)
            self.assertEqual(result.status, expected)
            self.assertIsNone(result.application_healthy)
            self.assertFalse(result.verified or result.retry_allowed)
            self.assertFalse(self.recovery.run(args, approval).verified)
            self.assertEqual(self.current()['dispatch_count'], 1)

    def test_concurrent_same_plan_runs_once(self):
        self.provider_approve()
        args = self.arguments()
        approval = self.guardian_decision(args)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.recovery.run(args, approval), range(2)))
        self.assertEqual(sum(result.verified for result in results), 1)
        self.assertEqual(self.current()['dispatch_count'], 1)

    def test_missing_permissions_and_symlink_never_dispatch(self):
        self.provider_approve()
        args = self.arguments()
        approval = self.guardian_decision(args)
        restricted = SimulatedRecovery(Policy('owner', frozenset({Permission.CLOUD})), self.root, self.approvals)
        self.assertFalse(restricted.run(args, approval).verified)
        self.lock.unlink()
        self.lock.symlink_to(self.state_path)
        self.assertFalse(self.recovery.run(args, approval).verified)
        self.assertEqual(self.current()['dispatch_count'], 0)

    def test_live_provider_cannot_be_enabled_by_an_approval(self):
        with self.assertRaises(AdapterUnavailable):
            LiveOpsRecovery().run({}, 'x' * 32)
