import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from igris.delivery import DeliveryTracker, ops_job_snapshot


class DeliveryTests(unittest.TestCase):
    def test_complete_simulated_lifecycle_with_revision_and_artifact_checks(self):
        t = DeliveryTracker()
        p = t.create('Sample client site', ('Homepage', 'Tests'))
        with self.assertRaises(ValueError):
            t.advance(p.id, p.revision, 'delivered', evidence_ref='sample', origin='simulated')
        for target in ('scoped', 'developing', 'testing', 'awaiting_approval', 'approved', 'deployment_prepared', 'maintenance', 'delivered'):
            old = p
            p = t.advance(p.id, p.revision, target, evidence_ref='synthetic scenario evidence', origin='simulated', artifact_sha256='a'*64)
            with self.assertRaises(ValueError):
                t.advance(p.id, old.revision, target, evidence_ref='replay', origin='simulated')
        self.assertEqual(p.state, 'delivered')
        self.assertTrue(all(e[2] == 'simulated' for e in p.history))

    def test_upstream_snapshot_cannot_import_approvals_or_completion(self):
        job = dict(id='a'*12, title='Synthetic starter', state='delivered', revision=4, approvals={'anything': True})
        view = ops_job_snapshot(job)
        self.assertFalse(view['permissions_imported'])
        self.assertEqual(view['origin'], 'imported_unverified')
        self.assertNotIn('approvals', view)
        t = DeliveryTracker(); p = t.create('Sample', ('API',))
        for target in ('scoped', 'developing', 'testing', 'awaiting_approval'):
            p = t.advance(p.id, p.revision, target, evidence_ref='test', origin='simulated', artifact_sha256='a'*64)
        with self.assertRaises(ValueError):
            t.advance(p.id, p.revision, 'approved', evidence_ref='changed', origin='simulated', artifact_sha256='b'*64)
