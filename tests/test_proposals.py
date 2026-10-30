import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.proposals import Proposal, ProposalGate
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Denied, Permission, Policy


class ProposalTests(unittest.TestCase):
    def test_draft_estimates_and_private_data(self):
        p = Proposal('Build a sample site', ('Frontend', 'Tests'), 5, 10000, 4)
        self.assertIn('Estimated working days: 2', p.draft())
        self.assertIn('INR 600.00', p.draft())
        self.assertIn('[REDACTED]', Proposal('password: fixture', ('Scope',), 1, 0).draft())

    def test_exact_approval_content_and_recipient_no_transport(self):
        with tempfile.TemporaryDirectory() as private, tempfile.TemporaryDirectory() as workspace:
            store = ApprovalStore(Path(private)/'approvals.db', initialize=True)
            gate = ProposalGate(Policy('owner', frozenset({Permission.COMMUNICATE})), Path(workspace), store)
            p = Proposal('Sample requirements', ('API',), 8, 10000)
            record = gate.request(p, 'sample-client')
            with self.assertRaises(Denied): gate.rehearse(p, 'sample-client', record['id'])
            store.decide(record['id'], approve=True, reviewed_digest=record['action_sha256'])
            for other, recipient in ((p, 'other-client'), (Proposal('Changed', ('API',), 8, 10000), 'sample-client')):
                with self.assertRaises(Denied): gate.rehearse(other, recipient, record['id'])
            self.assertFalse(gate.rehearse(p, 'sample-client', record['id'])['submitted'])
            with self.assertRaises(Denied): gate.rehearse(p, 'sample-client', record['id'])
            with self.assertRaises(Denied): gate.submit(p, 'sample-client', record['id'])
