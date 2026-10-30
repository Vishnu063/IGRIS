from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.adapters.hermes import MockHermesAdapter, UnavailableHermesAdapter
from igris.adapters.ops_pilot import InspectionRequest, MockOpsPilotAdapter, Snapshot, UnavailableOpsPilotAdapter
from igris.adapters.contracts import AdapterUnavailable, ContractError
from igris.controller import MissionController, State
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Permission, Policy
from igris.orchestration import SimulatedInspection
from test_n8n import FixtureServer


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.project = tempfile.TemporaryDirectory()
        self.private = tempfile.TemporaryDirectory()
        self.addCleanup(self.project.cleanup)
        self.addCleanup(self.private.cleanup)
        self.root = Path(self.project.name)
        (self.root / 'artifacts').mkdir()
        self.approvals = ApprovalStore(Path(self.private.name) / 'approvals.db', initialize=True)
        self.policy = Policy('owner', frozenset({Permission.READ, Permission.FILE_MODIFY}))

    def prepare(self, fixture, *, hermes=None, ops=None, policy=None):
        route = SimulatedInspection(policy or self.policy, self.root, self.approvals,
                                    hermes or MockHermesAdapter(), fixture.adapter(), ops or MockOpsPilotAdapter())
        controller = MissionController('owner', {'fixture_inspection': route})
        mission = controller.create('Inspect the synthetic fixture and prepare a report.', 'fixture_inspection')
        return controller, mission

    def decide(self, identifier, approve=True):
        # Synthetic owner decision for disposable test action, never a live approval.
        with sqlite3.connect(self.approvals.path) as db:
            digest = db.execute('SELECT digest FROM approvals WHERE id=?', (identifier,)).fetchone()[0]
        self.approvals.decide(identifier, approve=approve, reviewed_digest=digest)

    def test_end_to_end_simulation_waits_then_executes_through_real_guardian(self):
        with FixtureServer() as fixture:
            controller, mission = self.prepare(fixture)
            pending = controller.run(mission.id)
            self.assertEqual(pending.state, State.AWAITING_APPROVAL)
            self.assertEqual(list((self.root / 'artifacts').iterdir()), [])
            self.decide(pending.approval_request_id)
            result = controller.run(mission.id, approval_id=pending.approval_request_id)
            self.assertEqual(result.state, State.SUCCEEDED)
            self.assertEqual(result.origin, 'simulated')
            files = list((self.root / 'artifacts').iterdir())
            self.assertEqual(len(files), 1)
            self.assertIn('NOT A REAL SERVICE CHECK', files[0].read_text())
            self.assertEqual(len(fixture.calls), 1)  # Resume never replays orchestration.
            with sqlite3.connect(self.approvals.path) as db:
                self.assertEqual(db.execute("SELECT count(*) FROM audit WHERE event='execution_succeeded'").fetchone()[0], 1)

    def test_denied_and_forged_approvals_cannot_write(self):
        for denied in (False, True):
            with self.subTest(denied=denied), FixtureServer() as fixture:
                controller, mission = self.prepare(fixture)
                pending = controller.run(mission.id)
                if denied:
                    self.decide(pending.approval_request_id, False)
                    reference = pending.approval_request_id
                else:
                    reference = 'x' * 32
                self.assertEqual(controller.run(mission.id, approval_id=reference).state, State.FAILED)
                self.assertEqual(list((self.root / 'artifacts').iterdir()), [])

    def test_unavailable_real_integrations_block_without_fallback(self):
        for options in ({'hermes': UnavailableHermesAdapter()}, {'ops': UnavailableOpsPilotAdapter()}):
            with FixtureServer() as fixture:
                controller, mission = self.prepare(fixture, **options)
                self.assertEqual(controller.run(mission.id).state, State.BLOCKED)
                self.assertEqual(list((self.root / 'artifacts').iterdir()), [])

    def test_failed_workflow_and_ungranted_permission_never_request_write(self):
        with FixtureServer(mode='injection') as fixture:
            controller, mission = self.prepare(fixture)
            self.assertEqual(controller.run(mission.id).state, State.FAILED)
        with FixtureServer() as fixture:
            controller, mission = self.prepare(fixture, policy=Policy('owner'))
            self.assertEqual(controller.run(mission.id).state, State.BLOCKED)
            self.assertEqual(len(fixture.calls), 0)
        with sqlite3.connect(self.approvals.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM approvals').fetchone()[0], 0)

    def test_post_approval_failure_does_not_claim_success(self):
        with FixtureServer() as fixture:
            controller, mission = self.prepare(fixture)
            pending = controller.run(mission.id)
            self.decide(pending.approval_request_id)
            (self.root / 'artifacts').rmdir()
            self.assertEqual(controller.run(mission.id, approval_id=pending.approval_request_id).state, State.FAILED)

    def test_changed_action_after_owner_review_is_rejected_by_broker(self):
        with FixtureServer() as fixture:
            controller, mission = self.prepare(fixture)
            pending = controller.run(mission.id)
            self.decide(pending.approval_request_id)
            route = controller.routes['fixture_inspection']
            action, _ = route._pending[mission.id]
            action['arguments']['text'] = 'changed after owner review'
            self.assertEqual(controller.run(mission.id, approval_id=pending.approval_request_id).state, State.FAILED)
            self.assertEqual(list((self.root / 'artifacts').iterdir()), [])

    def test_ops_stub_is_not_a_real_connection(self):
        request = InspectionRequest('a' * 32, 'fixture-app')
        snapshot = MockOpsPilotAdapter().inspect(request)
        self.assertEqual(snapshot.origin, 'simulated')
        with self.assertRaises(AdapterUnavailable):
            UnavailableOpsPilotAdapter().inspect(request)
        with self.assertRaises(ContractError):
            Snapshot(request.mission_id, request.application, 'healthy', 'running', ('fixture',), 'real')
