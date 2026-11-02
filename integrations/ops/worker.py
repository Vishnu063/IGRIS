"""Pinned unmodified Ops Pilot library, real Docker CLI, exact-target read proxy."""
import hashlib,http.client,json,os,re,resource,socket,subprocess,sys,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
sys.dont_write_bytecode=True
os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(8*1024**2,8*1024**2));resource.setrlimit(resource.RLIMIT_CPU,(30,30))

class Session:
    def __init__(self,request):
        if type(request) is not dict or set(request)!={'container_id','read_key','fixture_marker','request_id','mission_id'}:raise ValueError('Invalid fixed monitoring request.')
        for key in ('container_id','read_key','fixture_marker'):
            if type(request[key]) is not str or not re.fullmatch('[a-f0-9]{64}',request[key]):raise ValueError('Invalid monitoring scope.')
        for key in ('request_id','mission_id'):
            if type(request[key]) is not str or not re.fullmatch('[a-f0-9]{32}',request[key]):raise ValueError('Invalid monitoring correlation.')
        private=Path('/tmp/ops-home');private.mkdir(mode=0o700)
        config=private/'.docker';config.mkdir(mode=0o700)
        settings={'HttpHeaders':{'X-IGRIS-Read-Key':request['read_key']}}
        (config/'config.json').write_text(json.dumps(settings));(config/'config.json').chmod(0o600)
        os.environ.clear();os.environ.update({'PATH':'/opt/igris/bin:/usr/bin:/bin','HOME':str(private),'DOCKER_CONFIG':str(config),'PYTHONDONTWRITEBYTECODE':'1','NO_PROXY':'127.0.0.1,localhost'})
        subprocess.run(['/opt/igris/bin/docker','context','create','igris-readonly','--docker','host=unix:///input/docker.sock'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=True)
        (config/'config.json').write_text(json.dumps(settings))
        class UnixHealth(http.client.HTTPConnection):
            def __init__(self):super().__init__('localhost',timeout=2)
            def connect(self):
                self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(2);self.sock.connect('/input/app.sock')
        class HealthHandler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                if self.path!='/health':self.send_error(404);return
                connection=UnixHealth();status=502
                try:
                    connection.request('GET','/health');response=connection.getresponse();payload=response.read(2049)
                    if response.status==200 and len(payload)<=2048 and json.loads(payload)=={'status':'ok','marker':request['fixture_marker']}:status=200
                except (OSError,ValueError,http.client.HTTPException):pass
                finally:connection.close()
                body=b'{}';self.send_response(status);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        health=ThreadingHTTPServer(('127.0.0.1',8789),HealthHandler);health.daemon_threads=True
        thread=threading.Thread(target=health.serve_forever,kwargs={'poll_interval':.1},daemon=True);thread.start()
        sys.path[:0]=['/opt/igris/ops','/opt/igris/triage']
        from ops_pilot.service import Pilot
        pilot=Pilot({'name':'IGRIS disposable app','docker_context':'igris-readonly','container':request['container_id'],
            'health_url':'http://127.0.0.1:8789/health','interval_seconds':15,'health_attempts':3,'health_interval':0},Path('/tmp/ops-state'))
        self.pilot,self.health,self.thread=pilot,health,thread
    def monitor(self,request_id,mission_id):
        for value in (request_id,mission_id):
            if type(value) is not str or not re.fullmatch('[a-f0-9]{32}',value):raise ValueError('Invalid monitoring correlation.')
        self.pilot.tick()
        if self.pilot.report is None:self.pilot.action('investigate')
        return {'schema_version':1,'origin':'real_ops_pilot','request_id':request_id,'mission_id':mission_id,'export':self.pilot.export_report()}
    def close(self):
        self.pilot.close();self.health.shutdown();self.health.server_close();self.thread.join(timeout=2)

def main():
    request=json.loads(sys.stdin.buffer.read(8193));session=Session(request)
    try:print(json.dumps(session.monitor(request['request_id'],request['mission_id'])),flush=True)
    finally:session.close()
if __name__=='__main__':main()
