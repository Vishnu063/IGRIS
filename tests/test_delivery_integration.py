"""Local component composition with explicitly simulated external services."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from igris.adapters.hermes import MockHermesAdapter, UnavailableHermesAdapter
from igris.adapters.ops_pilot import MockOpsPilotAdapter
from igris.business import BusinessController
from igris.controller import MissionController, State
from igris.costs import CostGuardian, CostEstimate
from igris.dashboard import Snapshot, SECTIONS
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy, Permission
from igris.memory import Memory
from igris.orchestration import SimulatedInspection
from igris.specialists.registry import profile
from igris.specialists.scheduling import SpecialistScheduler
from test_n8n import FixtureServer


class DeliveryIntegrationTests(unittest.TestCase):
    def test_business_core_guardian_adapters_specialists_memory_dashboard(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as private, FixtureServer() as fixture:
            root = Path(project); (root/'artifacts').mkdir()
            store = ApprovalStore(Path(private)/'approvals.db', initialize=True)
            policy = Policy('owner', frozenset({Permission.READ, Permission.FILE_MODIFY, Permission.SPECIALIST}))
            route = SimulatedInspection(policy, root, store, MockHermesAdapter(), fixture.adapter(), MockOpsPilotAdapter())
            core = MissionController('owner', {'inspect': route})
            task = core.create('Inspect only the synthetic application', 'inspect')
            business = BusinessController(); mission = business.create('maintenance', 'Evaluate a synthetic maintenance project')
            business.link_technical(mission.id, task.id)
            cost = CostGuardian(); cost.check(CostEstimate('resource', 0))
            pending = core.run(task.id)
            self.assertEqual(pending.state, State.AWAITING_APPROVAL)
            import sqlite3
            with sqlite3.connect(store.path) as db:
                digest = db.execute('SELECT digest FROM approvals WHERE id=?', (pending.approval_request_id,)).fetchone()[0]
            store.decide(pending.approval_request_id, approve=True, reviewed_digest=digest)
            result = core.run(task.id, approval_id=pending.approval_request_id)
            self.assertEqual(result.state, State.SUCCEEDED)
            self.assertEqual(result.origin, 'simulated')
            scheduler = SpecialistScheduler(policy, root, store)
            rec = scheduler.recommend(task.id, [{'role': 'testing', 'task': profile('testing').task, 'context': 'Review synthetic inspection evidence'}])
            request = scheduler.request(rec.id)['approval']
            self.assertFalse(scheduler.run(rec.id)['ok'])
            store.decide(request['id'], approve=True, reviewed_digest=request['action_sha256'])
            self.assertTrue(scheduler.run(rec.id, request['id'])['ok'])
            memory = Memory(Path(private)/'memory.db', 'owner', initialize=True)
            ident = memory.put('owner', 'incident', 'Synthetic inspection completed; no real application checked',
                classification='verified_fact', evidence='Disposable integration test assertion', approved=True)
            self.assertEqual(memory.get('owner', ident)['classification'], 'verified_fact')
            summaries = {'missions': ('succeeded; external origin simulated',),
                'guardian': ('Approved local artifact verified; external boundaries unverified',),
                'projects': ('Synthetic maintenance business mission',),
                'agents': ('One approved testing fixture; zero live models',),
                'n8n': ('Local HTTP contract server, simulated workflow',),
                'ops_pilot': ('Synthetic response only',)}
            view = Snapshot(tuple((s, summaries.get(s, ('Not verified / no data',))) for s in SECTIONS)).view('viewer')
            self.assertNotIn('pending_approvals', view)
            self.assertIn('simulated', view['missions'][0])
            self.assertFalse(cost.report()['actual_billing_verified'])
            self.assertEqual(len(list((root/'artifacts').iterdir())), 1)

    def test_missing_real_adapter_cannot_fall_back_to_simulated_success(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as private, FixtureServer() as fixture:
            root = Path(project); (root/'artifacts').mkdir()
            store = ApprovalStore(Path(private)/'approvals.db', initialize=True)
            policy = Policy('owner', frozenset({Permission.READ, Permission.FILE_MODIFY}))
            route = SimulatedInspection(policy, root, store, UnavailableHermesAdapter(), fixture.adapter(), MockOpsPilotAdapter())
            core = MissionController('owner', {'inspect': route})
            task = core.create('Request real connectivity', 'inspect')
            self.assertEqual(core.run(task.id).state, State.BLOCKED)
            self.assertEqual(fixture.calls, [])
            self.assertEqual(list((root/'artifacts').iterdir()), [])
