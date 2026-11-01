"""Exact-target delegated read capability; no approval issuer or mutation route."""
import hashlib,hmac,http.client,json,os,re,socket,socketserver,threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,parse_qs


class UnixHTTP(http.client.HTTPConnection):
    def __init__(self,path,*,timeout=3):super().__init__('localhost',timeout=timeout);self.path=str(path)
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(self.timeout);self.sock.connect(self.path)


def daemon_read(path):
    connection=UnixHTTP('/var/run/docker.sock')
    try:
        connection.request('GET',path);response=connection.getresponse();body=response.read(1048577)
        if len(body)>1048576:raise ValueError('Docker response exceeds scope limit.')
        return response.status,dict(response.getheaders()),body
    finally:connection.close()


class _Server(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
    daemon_threads=True;request_queue_size=8
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):request.close();return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()


class ExactDockerReads:
    """Trusted parent delegates only observed daemon ID and one immutable target ID.

    The credential is RAM-only here, transmitted through private worker stdin.
    No headers, raw logs, arguments or supplied URLs enter the audit list.
    """
    def __init__(self,path,container_id,daemon_id,read_key,*,backend=daemon_read):
        if not re.fullmatch('[a-f0-9]{64}',container_id) or not re.fullmatch('[a-f0-9]{64}',read_key):raise ValueError('Exact target and private read credential required.')
        self.path=Path(path).absolute();self.cid=container_id;self.daemon_id=daemon_id;self._key=read_key;self.backend=backend;self.events=[];self.lock=threading.Lock()
        if self.path.exists() or self.path.is_symlink() or self.path.parent.resolve()!=self.path.parent or self.path.parent.stat().st_uid!=os.getuid() or self.path.parent.stat().st_mode&0o077:raise ValueError('Fresh private socket path required.')
        owner=self
        class Handler(BaseHTTPRequestHandler):
            server_version='IGRIS-read-profile';sys_version='';protocol_version='HTTP/1.0'
            def setup(self):self.request.settimeout(3);super().setup()
            def log_message(self,*args):pass
            def do_GET(self):self.dispatch()
            def do_HEAD(self):self.dispatch()
            def do_POST(self):self.dispatch()
            def do_PUT(self):self.dispatch()
            def do_PATCH(self):self.dispatch()
            def do_DELETE(self):self.dispatch()
            def send(self,status,body=b'',headers=None):
                self.close_connection=True;self.send_response(status)
                for key,value in (headers or {}).items():
                    if key.lower() in ('api-version','ostype','docker-experimental','content-type') and len(value)<256 and not any(ord(c)<32 for c in value):self.send_header(key,value)
                self.send_header('Content-Length',str(len(body)));self.end_headers()
                if self.command!='HEAD' and body:self.wfile.write(body)
            def dispatch(self):
                kind='unregistered';status=403
                with owner.lock:
                    available=len(owner.events)<128
                    # Reserve before I/O so concurrent clients cannot exceed capacity.
                    record={'method':self.command if self.command in ('GET','HEAD','POST','PUT','PATCH','DELETE') else 'other','kind':kind,'status':status}
                    if available:owner.events.append(record)
                if not available:
                    try:self.send(429)
                    except OSError:pass
                    return
                try:
                    supplied=self.headers.get('X-IGRIS-Read-Key','')
                    if len(self.headers.get_all('X-IGRIS-Read-Key',[]))!=1 or not re.fullmatch('[a-f0-9]{64}',supplied) or not hmac.compare_digest(supplied,owner._key):status=401;return self.send(status)
                    if self.command not in ('GET','HEAD') or self.headers.get('Transfer-Encoding') or self.headers.get('Content-Length') not in (None,'0'):return self.send(status)
                    parsed=urlsplit(self.path)
                    if parsed.scheme or parsed.netloc or '%' in self.path or '..' in self.path or '//' in parsed.path:return self.send(status)
                    path=re.sub(r'^/v1\.[0-9]{1,3}(?=/)','',parsed.path)
                    query=parse_qs(parsed.query,keep_blank_values=True)
                    if any(len(v)!=1 for v in query.values()):return self.send(status)
                    if path=='/_ping' and not query:kind='ping'
                    elif self.command=='GET' and path in ('/version','/info') and not query:kind=path[1:]
                    elif self.command=='GET' and path=='/containers/'+owner.cid+'/json' and set(query)<= {'size'} and all(v[0] in ('0','false') for v in query.values()):kind='inspect'
                    elif self.command=='GET' and path=='/containers/'+owner.cid+'/logs':
                        if 'tail' not in query:return self.send(status)
                        allowed={'stdout':('0','1','false','true'),'stderr':('0','1','false','true'),'follow':('0','false'),'timestamps':('0','false'),'details':('0','false'),'since':('','0'),'until':('','0')}
                        if set(query)-set(allowed)-{'tail'}:return self.send(status)
                        if any(k!='tail' and v[0] not in allowed[k] for k,v in query.items()):return self.send(status)
                        tail=query.get('tail',['100'])[0]
                        if not re.fullmatch('[0-9]{1,3}',tail) or not 0<=int(tail)<=100:return self.send(status)
                        kind='logs'
                    else:return self.send(status)
                    status,headers,body=owner.backend(self.path)
                    if status==200 and kind in ('info','inspect','version'):
                        value=json.loads(body)
                        if kind=='info':
                            if value.get('ID')!=owner.daemon_id:raise ValueError('Daemon changed.')
                            value={'ID':value['ID']}
                        elif kind=='inspect':
                            if value.get('Id')!=owner.cid:raise ValueError('Target changed.')
                            state=value.get('State',{});config=value.get('Config',{})
                            value={key:value.get(key) for key in ('Id','Name','Image','RestartCount')}
                            value['State']={key:state.get(key) for key in ('Status','Running','ExitCode','OOMKilled','StartedAt','FinishedAt')}
                            if type(state.get('Health')) is dict:value['State']['Health']={'Status':state['Health'].get('Status')}
                            value['Config']={'Image':config.get('Image'),'Tty':config.get('Tty')}
                        else:value={key:value.get(key) for key in ('ApiVersion','MinAPIVersion','Version','Os','Arch','KernelVersion')}
                        body=json.dumps(value).encode()
                    self.send(status,body,headers)
                except (BrokenPipeError,ConnectionResetError):pass
                except (OSError,ValueError,KeyError,TypeError,AttributeError,http.client.HTTPException):
                    status=502
                    try:self.send(status)
                    except OSError:pass
                finally:
                    with owner.lock:record.update(kind=kind,status=status)
        self.server=_Server(str(self.path),Handler);self.server.slots=threading.BoundedSemaphore(4);os.chmod(self.path,0o600)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.1},daemon=True)
    def start(self):self.thread.start();return self
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=4);self.path.unlink(missing_ok=True)
