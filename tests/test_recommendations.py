from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.adapters.contracts import ContractError
from igris.adapters.ops_monitoring import parse_export
from igris.diagnosis import diagnose
from igris.recommendations import recommend
from test_ops_monitoring import BINDING, export_fixture


class RecommendationTests(unittest.TestCase):
    def recommendation(self, raw):
        snapshot = parse_export(raw, BINDING)
        return recommend(snapshot, diagnose(snapshot))

    def test_supported_restart_is_a_risk_labeled_approval_required_proposal(self):
        result = self.recommendation(export_fixture())
        self.assertEqual(result.supported_operation, 'docker.restart')
        self.assertTrue(result.requires_owner_approval)
        self.assertFalse(result.execution_available)
        self.assertIn('cloud', result.required_permissions)
        self.assertTrue(result.risks and result.prerequisites and result.evidence_refs)

    def test_running_unhealthy_has_no_restart_option(self):
        raw = export_fixture()
        raw['report']['snapshot']['observations']['state'] = ['running']
        result = self.recommendation(raw)
        self.assertEqual(result.code, 'investigate_application')
        self.assertIsNone(result.supported_operation)

    def test_maintenance_stale_or_unknown_monitoring_blocks_repair_proposal(self):
        for change in ('maintenance', 'stale', 'unknown_maintenance', 'collection_error'):
            raw = export_fixture()
            if change == 'maintenance': raw['maintenance_until'] = raw['generated_at'] + 60
            if change == 'stale': raw['monitor']['checked_at'] = 1
            if change == 'unknown_maintenance': del raw['maintenance_until']
            if change == 'collection_error': raw['report']['snapshot']['errors'] = ['incomplete']
            with self.subTest(change=change):
                self.assertIsNone(self.recommendation(raw).supported_operation)

    def test_absent_provider_action_or_identity_never_invents_repair(self):
        raw = export_fixture()
        raw['report']['actions'] = []
        self.assertIsNone(self.recommendation(raw).supported_operation)
        raw = export_fixture()
        raw['report']['snapshot']['observations']['id'] = []
        self.assertIsNone(self.recommendation(raw).supported_operation)

    def test_conflicting_healthy_endpoint_stopped_container_is_not_auto_restarted(self):
        raw = export_fixture()
        raw['monitor']['healthy'] = True
        self.assertIsNone(self.recommendation(raw).supported_operation)

    def test_old_diagnosis_cannot_authorize_new_evidence(self):
        first = parse_export(export_fixture(), BINDING)
        raw = export_fixture()
        raw['monitor']['healthy'] = True
        second = parse_export(raw, BINDING)
        with self.assertRaises(ContractError):
            recommend(second, diagnose(first))
