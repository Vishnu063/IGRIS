import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.adapters.contracts import AdapterUnavailable, ContractError
from igris.adapters.ops_monitoring import TargetBinding, parse_export, OpsMonitoringAdapter, LocalReportTransport

BINDING = TargetBinding('fixture-app', 'default', 'http://127.0.0.1:8080/')


def export_fixture():
    now = time.time()
    return {'schema_version': 1, 'generated_at': now, 'name': 'Synthetic fixture', 'container': BINDING.container,
            'context': BINDING.context, 'health_url': BINDING.health_url,
            'monitor': {'checked_at': now, 'healthy': False, 'error': None},
            'report': {'snapshot': {'collected_at': now, 'errors': [], 'observations': {
                'state': ['exited'], 'id': ['a' * 64], 'daemon_id': ['fixture-daemon'],
                'oom': [False], 'exit_code': [1], 'restart_count': [0]}},
                'deep_evidence': {'log_signals': {'dependency': 2}, 'errors': []},
                'actions': [{'id': 'restart', 'risk': 'upstream risk text'}]},
            'diagnosis': {}, 'maintenance_until': 0, 'plan': None, 'result': None, 'history': [], 'alerts': []}


class MonitoringTests(unittest.TestCase):
    def test_actual_export_shape_maps_filtered_evidence(self):
        snapshot = parse_export(export_fixture(), BINDING)
        self.assertEqual(snapshot.origin, 'provided_export')
        self.assertEqual((snapshot.health, snapshot.container_state), ('unhealthy', 'exited'))
        self.assertEqual(snapshot.signals, (('dependency', 2),))
        self.assertTrue(snapshot.restart_offered)
        self.assertIn(snapshot.digest, snapshot.ref('monitor.healthy'))

    def test_stale_sources_are_independent_and_never_healthy(self):
        raw = export_fixture()
        raw['monitor']['checked_at'] -= 301
        result = parse_export(raw, BINDING)
        self.assertEqual(result.health, 'unknown')
        self.assertEqual(result.container_state, 'exited')
        raw['report']['snapshot']['collected_at'] -= 301
        result = parse_export(raw, BINDING)
        self.assertEqual(result.container_state, 'unknown')
        self.assertEqual(result.signals, ())

    def test_mismatch_old_export_and_incomplete_data_rejected(self):
        for key, value in (('context', 'other'), ('container', 'other'), ('health_url', 'https://example.invalid/'),
                           ('schema_version', True), ('generated_at', 1), ('report', None)):
            raw = export_fixture()
            raw[key] = value
            with self.subTest(key=key), self.assertRaises(ContractError):
                parse_export(raw, BINDING)

    def test_collection_errors_and_bad_types_do_not_establish_health(self):
        raw = export_fixture()
        raw['report']['snapshot']['errors'] = ['SYNTHETIC_PRIVATE_DETAIL']
        raw['monitor']['healthy'] = 'true'
        result = parse_export(raw, BINDING)
        self.assertEqual(result.health, 'unknown')
        self.assertEqual(result.container_state, 'unknown')
        self.assertNotIn('SYNTHETIC_PRIVATE_DETAIL', repr(result))

    def test_raw_logs_and_unselected_data_never_reach_output(self):
        raw = export_fixture()
        raw['report']['raw_logs'] = 'SYNTHETIC_PRIVATE_DETAIL'
        raw['alerts'] = [{'message': 'SYNTHETIC_PRIVATE_DETAIL'}]
        self.assertNotIn('SYNTHETIC_PRIVATE_DETAIL', repr(parse_export(raw, BINDING)))
        raw['report']['deep_evidence']['log_signals']['execute_shell'] = 1
        with self.assertRaises(ContractError):
            parse_export(raw, BINDING)

    def test_disabled_and_live_origin_not_claimed(self):
        with self.assertRaises(AdapterUnavailable):
            OpsMonitoringAdapter(BINDING).inspect()
        with self.assertRaises(ContractError):
            parse_export(export_fixture(), BINDING, origin='real')

    def test_real_local_cookie_get_uses_audited_route_without_mutation(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                calls.append(self.path)
                good = self.headers.get('Cookie') == 'ops_pilot=' + 'x' * 32
                self.send_response(200 if good else 401)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(export_fixture() if good else {}).encode())
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f'http://127.0.0.1:{server.server_port}/api/report'
            result = OpsMonitoringAdapter(BINDING, LocalReportTransport(url, 'x' * 32)).inspect()
            self.assertEqual(result.origin, 'simulated')
            self.assertEqual(calls, ['/api/report'])
            with self.assertRaises(ContractError):
                LocalReportTransport(url, 'y' * 32).read_report()
        finally:
            server.shutdown(); server.server_close(); thread.join()
