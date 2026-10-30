"""Authenticated loopback read-only Mission Control, with explicit unknowns."""
import base64
import binascii
from dataclasses import dataclass
import hmac
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re

from .guardian.secrets import redact

SECTIONS = ('igris', 'guardian', 'missions', 'agents', 'n8n', 'ops_pilot',
            'projects', 'pending_approvals', 'errors', 'warnings')


@dataclass(frozen=True)
class Snapshot:
    rows: tuple = tuple((name, ('Not verified / no data',)) for name in SECTIONS)

    def __post_init__(self):
        if type(self.rows) is not tuple or tuple(row[0] for row in self.rows) != SECTIONS:
            raise ValueError('Exact dashboard sections required.')
        for name, values in self.rows:
            if type(values) is not tuple or len(values) > 50 or any(type(v) is not str or len(v) > 512 for v in values):
                raise ValueError('Invalid bounded dashboard rows.')

    def view(self, role):
        return {name: [redact(v) for v in values] for name, values in self.rows
                if role == 'owner' or name != 'pending_approvals'}


def make_server(accounts, snapshot_provider):
    """Trusted operator API. Does not start serving or print credentials.

    accounts: username -> (private secret >=32 characters, owner/viewer).
    Authenticated snapshots must exclude raw customer details and action bodies.
    """
    if type(accounts) is not dict or not accounts or len(accounts) > 10 or not callable(snapshot_provider):
        raise ValueError('Trusted dashboard configuration required.')
    credentials = {}
    for name, entry in accounts.items():
        if type(name) is not str or not re.fullmatch('[a-z][a-z0-9_-]{0,31}', name) or type(entry) is not tuple or len(entry) != 2:
            raise ValueError('Invalid dashboard account.')
        secret, role = entry
        if type(secret) is not str or not 32 <= len(secret) <= 128 or not secret.isascii() or ':' in secret or role not in ('owner', 'viewer'):
            raise ValueError('Invalid dashboard credential.')
        credentials[name] = (secret, role)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'IGRIS'
        sys_version = ''

        def log_message(self, *args): pass  # Never log headers, paths or credentials.

        def reply(self, status, payload, content_type='text/plain; charset=utf-8'):
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.send_header('X-Content-Type-Options', 'nosniff')
            if status == 401: self.send_header('WWW-Authenticate', 'Basic realm="IGRIS"')
            self.end_headers(); self.wfile.write(payload)

        def do_GET(self):
            if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
                return self.reply(403, b'Host denied')
            header = self.headers.get('Authorization', '')
            role = None
            try:
                if not header.startswith('Basic ') or len(header) > 512: raise ValueError()
                name, supplied = base64.b64decode(header[6:], validate=True).decode('ascii').split(':', 1)
                expected, candidate = credentials.get(name, ('', None))
                if expected and hmac.compare_digest(supplied, expected): role = candidate
            except (ValueError, UnicodeError, binascii.Error): pass
            if role is None: return self.reply(401, b'Authentication required')
            if self.path not in ('/', '/api/state'): return self.reply(404, b'Not found')
            try:
                snapshot = snapshot_provider()
                if type(snapshot) is not Snapshot: raise ValueError()
                view = snapshot.view(role)
            except Exception:
                return self.reply(503, b'Status unavailable')
            if self.path == '/api/state':
                return self.reply(200, json.dumps(view).encode(), 'application/json')
            body = '<!doctype html><html lang="en"><meta charset="utf-8"><title>IGRIS Mission Control</title><h1>Mission Control</h1><p>Read-only status snapshot. External connectivity is not implied.</p>'
            for name, values in view.items():
                body += '<h2>'+escape(name.replace('_', ' '))+'</h2><ul>'+''.join('<li>'+escape(v)+'</li>' for v in values)+'</ul>'
            self.reply(200, (body+'</html>').encode(), 'text/html; charset=utf-8')

        def do_POST(self): self.reply(405, b'Read-only dashboard')

    server = HTTPServer(('127.0.0.1', 0), Handler)
    server.timeout = 1
    return server
