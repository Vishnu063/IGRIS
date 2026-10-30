from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from igris.adapters.contracts import AdapterUnavailable, ContractError
from igris.adapters.n8n import N8nAdapter, WorkflowRequest


class FixtureServer:
    def __init__(self, *, failures=0, mode='normal', delay=0):
        self.calls = []
        fixture = self
        self.failures, self.mode, self.delay = failures, mode, delay
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.calls.append((self.headers.get('Idempotency-Key'), payload))
                if self.headers.get('X-IGRIS-Key') != 'synthetic-local-contract-key-0000':
                    self.send_response(401)
                    self.end_headers()
                    return
                if fixture.failures:
                    fixture.failures -= 1
                    self.send_response(503)
                    self.end_headers()
                    return
                if fixture.delay:
                    time.sleep(fixture.delay)
                result = {'schema_version': 1, 'mission_id': payload['mission_id'], 'workflow': 'inspect_fixture',
                          'status': 'completed', 'output': {'summary': 'simulated workflow completed'}}
                if fixture.mode == 'mismatch':
                    result['mission_id'] = 'f' * 32
                if fixture.mode == 'injection':
                    result['command'] = 'untrusted command'
                if fixture.mode == 'sensitive':
                    result['output']['summary'] = 'password: synthetic fixture'
                raw = json.dumps(result).encode()
                if fixture.mode == 'oversize':
                    raw = b'x' * 16385
                if fixture.mode == 'invalid_json':
                    raw = b'{'
                if fixture.mode == 'redirect':
                    self.send_response(302)
                    self.send_header('Location', 'http://example.invalid/')
                else:
                    self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except BrokenPipeError:
                    pass
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    def __enter__(self):
        self.thread.start()
        return self
    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
    def adapter(self, **kwargs):
        return N8nAdapter(f'http://127.0.0.1:{self.server.server_port}/webhook/igris-readonly',
                          kwargs.pop('secret', 'synthetic-local-contract-key-0000'), mode='local_contract', **kwargs)


class N8nTests(unittest.TestCase):
    def request(self):
        return WorkflowRequest('a' * 32, 'fixture-app')

    def test_real_local_http_contract_and_simulation_label(self):
        with FixtureServer() as fixture:
            adapter = fixture.adapter()
            result = adapter.run(self.request())
            self.assertEqual(result.origin, 'simulated')
            self.assertEqual(result.status, 'completed')
            self.assertEqual(adapter.events, (('a' * 32, 1, '200'),))
            self.assertEqual(len(fixture.calls), 1)

    def test_authentication_is_required_and_denial_is_not_retried(self):
        with FixtureServer() as fixture:
            with self.assertRaises(ContractError):
                fixture.adapter(secret='different-synthetic-contract-key').run(self.request())
            self.assertEqual(len(fixture.calls), 1)

    def test_retry_is_bounded_and_idempotency_key_is_stable(self):
        with FixtureServer(failures=1) as fixture:
            fixture.adapter().run(self.request())
            self.assertEqual(len(fixture.calls), 2)
            self.assertEqual(fixture.calls[0], fixture.calls[1])
        with FixtureServer(failures=10) as fixture:
            with self.assertRaises(AdapterUnavailable):
                fixture.adapter(retries=2).run(self.request())
            self.assertEqual(len(fixture.calls), 3)

    def test_malformed_redirect_injected_and_mismatched_responses(self):
        for mode in ('mismatch', 'injection', 'oversize', 'invalid_json', 'redirect'):
            with self.subTest(mode=mode), FixtureServer(mode=mode) as fixture:
                with self.assertRaises(ContractError):
                    fixture.adapter().run(self.request())
                self.assertEqual(len(fixture.calls), 1)

    def test_timeout_and_sensitive_response(self):
        with FixtureServer(delay=0.15) as fixture:
            with self.assertRaises(AdapterUnavailable):
                fixture.adapter(timeout=0.02, retries=0).run(self.request())
        with FixtureServer(mode='sensitive') as fixture:
            self.assertEqual(fixture.adapter().run(self.request()).summary, '[REDACTED]')

    def test_default_disabled_and_endpoint_scope(self):
        with self.assertRaises(AdapterUnavailable):
            N8nAdapter().run(self.request())
        for url in ('https://example.invalid/webhook/igris-readonly', 'http://localhost:80/webhook/igris-readonly',
                    'http://127.0.0.1:80/other', 'http://127.0.0.1:80/webhook/igris-readonly?token=x'):
            with self.assertRaises(ContractError):
                N8nAdapter(url, 'synthetic-local-contract-key-0000', mode='local_contract')
        with self.assertRaises(ContractError):
            WorkflowRequest('a' * 32, 'app;command')
