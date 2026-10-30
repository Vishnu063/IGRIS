from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.diagnosis import diagnose
from igris.adapters.ops_monitoring import parse_export
from test_ops_monitoring import BINDING, export_fixture


class DiagnosisTests(unittest.TestCase):
    def result(self, raw=None):
        return diagnose(parse_export(export_fixture() if raw is None else raw, BINDING))

    def test_stopped_is_observed_and_cause_is_a_hypothesis(self):
        result = self.result()
        self.assertIn('container_stopped', [x.code for x in result.observations])
        self.assertIn('stop_cause_unknown', [x.code for x in result.hypotheses])
        self.assertEqual(result.source_origin, 'provided_export')

    def test_oom_is_reported_without_claiming_memory_leak(self):
        raw = export_fixture()
        raw['report']['snapshot']['observations']['oom'] = [True]
        result = self.result(raw)
        self.assertIn('oom_termination_reported', [x.code for x in result.observations])
        self.assertIn('memory_pressure', [x.code for x in result.hypotheses])
        self.assertNotIn('confirmed memory leak', repr(result))

    def test_configuration_resource_and_application_cases_are_evidence_linked(self):
        raw = export_fixture()
        raw['report']['deep_evidence']['log_signals'] = {'disk': 1, 'authorization': 2, 'memory': 1}
        result = self.result(raw)
        codes = [x.code for x in result.hypotheses]
        for code in ('disk_exhaustion', 'configuration_or_permissions', 'memory_exhaustion', 'application_error'):
            self.assertIn(code, codes)
        for finding in result.observations + result.hypotheses:
            self.assertTrue(finding.evidence_refs)
            self.assertTrue(all(result.export_digest in ref for ref in finding.evidence_refs))

    def test_running_does_not_establish_health(self):
        raw = export_fixture()
        raw['report']['snapshot']['observations']['state'] = ['running']
        result = self.result(raw)
        self.assertIn('endpoint_failed', [x.code for x in result.observations])
        self.assertIn('running_but_unhealthy', [x.code for x in result.hypotheses])

    def test_incomplete_stale_evidence_is_not_confirmed(self):
        raw = export_fixture()
        raw['monitor']['checked_at'] = 1
        raw['report']['snapshot']['collected_at'] = 1
        result = self.result(raw)
        self.assertEqual(result.observations, ())
        self.assertEqual(result.hypotheses, ())
        self.assertIn('container_evidence_incomplete_or_stale', result.limitations)

    def test_restarts_are_not_automatically_a_loop(self):
        raw = export_fixture()
        raw['report']['snapshot']['observations']['restart_count'] = [20]
        result = self.result(raw)
        finding = next(x for x in result.observations if x.code == 'previous_restarts')
        self.assertIn('does not establish', finding.claim)
