"""Disposable real Docker application with one private Unix HTTP health endpoint."""
import json,os,signal,socket,socketserver
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
os.umask(0o077)
class Server(HTTPServer):
    address_family=socket.AF_UNIX
    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name='igris-fixture';self.server_port=0
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path!='/health':self.send_error(404);return
        payload=json.dumps({'status':'ok','marker':os.environ['IGRIS_FIXTURE_MARKER']}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
server=Server('/appdata/app.sock',Handler)
os.chmod('/appdata/app.sock',0o600)
signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(SystemExit(0)))
print('IGRIS disposable application ready',flush=True)
try:server.serve_forever(poll_interval=.1)
finally:server.server_close()
