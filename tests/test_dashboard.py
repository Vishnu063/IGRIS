import base64, json, secrets, sys, threading, unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from igris.dashboard import SECTIONS, Snapshot, make_server


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.owner = secrets.token_urlsafe(32); self.viewer = secrets.token_urlsafe(32)
        self.snapshot = Snapshot(tuple((s, ('pending-review',) if s == 'pending_approvals' else ('<script>unsafe</script>',) if s == 'missions' else ('password: fixture',) if s == 'warnings' else ('Not verified',)) for s in SECTIONS))
        self.server = make_server({'owner': (self.owner, 'owner'), 'viewer': (self.viewer, 'viewer')}, lambda: self.snapshot)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start(); self.addCleanup(self.close)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def close(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)

    def request(self, path='/', account=None, **kwargs):
        headers = {}
        if account:
            value = self.owner if account == 'owner' else self.viewer
            headers['Authorization'] = 'Basic '+base64.b64encode(f'{account}:{value}'.encode()).decode()
        return urlopen(Request(self.url+path, headers=headers, **kwargs), timeout=2)

    def test_real_http_authentication_role_views_and_read_only(self):
        with self.assertRaises(HTTPError) as denied: self.request()
        self.assertEqual(denied.exception.code, 401)
        with self.request('/api/state', 'owner') as response: owner = json.load(response)
        with self.request('/api/state', 'viewer') as response: viewer = json.load(response)
        self.assertEqual(owner['pending_approvals'], ['pending-review'])
        self.assertNotIn('pending_approvals', viewer)
        self.assertEqual(owner['warnings'], ['[REDACTED]'])
        with self.assertRaises(HTTPError) as denied: self.request('/api/state', 'owner', method='POST', data=b'{}')
        self.assertEqual(denied.exception.code, 405)

    def test_html_escaping_security_headers_and_unknown_default(self):
        with self.request('/', 'owner') as response:
            body = response.read().decode()
            self.assertNotIn('<script>', body)
            self.assertIn('&lt;script&gt;', body)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertTrue(all('Not verified' in values[0] for values in Snapshot().view('owner').values()))
