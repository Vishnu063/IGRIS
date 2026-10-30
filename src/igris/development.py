"""Reviewed sample development workflow; no dependency installs or deployments."""
from pathlib import Path
from .projects import create_sample, plan_project

APP_SOURCE = '''import json
from pathlib import Path
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class Store:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, title TEXT NOT NULL)')
    def add(self, title):
        if type(title) is not str or not 1 <= len(title) <= 100:
            raise ValueError('Invalid title')
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO items(title) VALUES (?)', (title,))
    def items(self):
        with sqlite3.connect(self.path) as db:
            return [{'id': i, 'title': t} for i,t in db.execute('SELECT id,title FROM items ORDER BY id LIMIT 100')]

def server(store, port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            if self.path == '/api/items':
                body, mime = json.dumps(store.items()).encode(), 'application/json'
            elif self.path == '/':
                body, mime = Path(__file__).with_name('index.html').read_bytes(), 'text/html; charset=utf-8'
            else:
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(body)
    return ThreadingHTTPServer(('127.0.0.1', port), Handler)
'''
FRONTEND = '''<!doctype html><html lang="en"><meta charset="utf-8"><title>Development items</title>
<h1>Development items</h1><p>Disposable sample data only.</p><ul id="items"></ul>
<script>fetch('/api/items').then(r=>{if(!r.ok)throw Error('Request failed');return r.json()})
.then(items=>{for(const item of items){const li=document.createElement('li');li.textContent=item.title;document.querySelector('#items').append(li)}})
.catch(()=>{document.querySelector('#items').textContent='Data unavailable'});</script></html>
'''


def create_webapp(parent: Path, name, policy):
    root = create_sample(parent, plan_project(name, 'website'), policy)
    # The just-created sample is exclusively owned by this trusted workflow.
    (root / 'index.html').write_text(FRONTEND)
    for path, text in {'app.py': APP_SOURCE, 'requirements.txt': '# Python standard library only; no packages to install.\n',
                       '.gitignore': '*.db\n__pycache__/\n',
                       'API.md': '# Local API\nGET /api/items returns at most 100 synthetic item records. No external API is configured.\n',
                       'README.md': '# Disposable development web app\n\nPython frontend/API/SQLite sample; no authentication or production hardening.\nNever use customer data or expose publicly. No dependencies or deployments.\nThe Store API is local-only; HTTP permits reads only.\n'}.items():
        (root / path).write_text(text)
        (root / path).chmod(0o600)
    return root
