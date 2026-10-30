from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.deployment import DeploymentIntent, DeploymentGate, DeploymentBlocked
from igris.guardian.approvals import ApprovalStore
from igris.guardian.executor import execute
from igris.guardian.policy import Policy, Permission, Denied


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.root_dir = tempfile.TemporaryDirectory(); self.addCleanup(self.root_dir.cleanup)
        self.private = tempfile.TemporaryDirectory(); self.addCleanup(self.private.cleanup)
        self.root = Path(self.root_dir.name)
        self.store = ApprovalStore(Path(self.private.name) / 'approvals.db', initialize=True)
        self.policy = Policy('owner', frozenset({Permission.DEPLOY}))
        self.gate = DeploymentGate(self.policy, self.root, self.store)
        self.intent = DeploymentIntent('example-production', 'a' * 40, ('api',), ('Publish reviewed API build.',), 'b' * 64)

    def approve(self, *, decision=True):
        request = self.gate.request(self.intent)['approval']
        self.store.decide(request['id'], approve=decision, reviewed_digest=request['action_sha256'])
        return request['id']

    def test_request_is_reviewable_and_never_deploys(self):
        request = self.gate.request(self.intent)
        self.assertEqual(request['review']['target'], self.intent.target)
        self.assertEqual(request['review']['version'], self.intent.version)
        self.assertEqual(request['review']['scope'], ['api'])
        self.assertEqual(request['review']['expected_changes'], list(self.intent.expected_changes))
        self.assertFalse(request['deployed'])
        with self.assertRaises(Denied): self.gate.rehearse_approval(self.intent, request['approval']['id'])

    def test_missing_denied_expired_mismatched_and_used_approvals_rejected(self):
        for reference in (None, 'x' * 32, self.approve(decision=False)):
            with self.assertRaises(Denied): self.gate.rehearse_approval(self.intent, reference)
        reference = self.approve()
        for altered in (replace(self.intent,target='other'), replace(self.intent,version='c'*40),
                        replace(self.intent,scope=('frontend',)), replace(self.intent,expected_changes=('Different changes.',)),
                        replace(self.intent,artifact_sha256='d'*64)):
            with self.assertRaises(Denied): self.gate.rehearse_approval(altered, reference)
        result = self.gate.rehearse_approval(self.intent, reference)
        self.assertFalse(result['deployed'] or result['execution_available'])
        with self.assertRaises(Denied): self.gate.rehearse_approval(self.intent, reference)
        self.store.clock = lambda: time.time()-600
        expired = self.approve()
        self.store.clock = time.time
        with self.assertRaises(Denied): self.gate.rehearse_approval(self.intent, expired)

    def test_actual_broker_and_live_method_block_even_approved_production(self):
        reference = self.approve()
        for token in (None, reference):
            with self.assertRaises(DeploymentBlocked): self.gate.deploy(self.intent, token)
            result = execute(self.policy, self.root, dict(self.intent.action(), approval_id=token), approval_store=self.store.path)
            self.assertFalse(result['ok'])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_permission_and_mutable_versions_denied(self):
        gate = DeploymentGate(Policy('owner'), self.root, self.store)
        with self.assertRaises(Denied): gate.request(self.intent)
        with self.assertRaises(ValueError): replace(self.intent, version='latest')
        with self.assertRaises(ValueError): replace(self.intent, scope=())
