"""Trusted local CDP test driver, never exposed to IGRIS/model tools.

Requires a caller-owned offline network namespace. Keeps Chromium's sandbox on.
"""
import base64,hashlib,json,os,secrets,socket,struct,subprocess,tempfile,time
from pathlib import Path

class WebSocket:
 def __init__(self,host,port,path):
  self.sock=socket.create_connection((host,port),timeout=5);key=base64.b64encode(secrets.token_bytes(16)).decode()
  self.sock.sendall(('GET '+path+' HTTP/1.1\r\nHost: '+host+':'+str(port)+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: '+key+'\r\n\r\n').encode())
  header=b''
  while not header.endswith(b'\r\n\r\n'):
   chunk=self.sock.recv(1)
   if not chunk:raise EOFError('Browser closed during handshake.')
   header+=chunk
   if len(header)>8192:raise ValueError('Oversized local handshake.')
  expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
  if not header.startswith(b'HTTP/1.1 101') or expected.lower() not in header.lower():raise ValueError('Invalid local WebSocket handshake.')
 def read(self,count):
  result=b''
  while len(result)<count:
   data=self.sock.recv(count-len(result))
   if not data:raise EOFError('Local browser closed.')
   result+=data
  return result
 def send(self,data,opcode=1):
  mask=secrets.token_bytes(4);size=len(data)
  header=bytes([0x80|opcode,0x80|(size if size<126 else 126 if size<65536 else 127)])
  if size>=126:header+=struct.pack('!H' if size<65536 else '!Q',size)
  self.sock.sendall(header+mask+bytes(value^mask[i%4] for i,value in enumerate(data)))
 def receive(self):
  output=b''
  while True:
   first,second=self.read(2);length=second&127
   if length==126:length=struct.unpack('!H',self.read(2))[0]
   elif length==127:length=struct.unpack('!Q',self.read(8))[0]
   if length>8*1024**2:raise ValueError('Oversized local browser message.')
   if second&128:raise ValueError('Server must not mask frames.')
   body=self.read(length);opcode=first&15
   if opcode==8:raise EOFError('Local browser close frame.')
   if opcode==9:self.send(body,10);continue
   if opcode==10:continue
   output+=body
   if first&128:return json.loads(output)
 def close(self):self.sock.close()

class Browser:
 def __init__(self,directory):self.directory=Path(directory).absolute();self.process=None;self.ws=None;self.sequence=0
 def start(self):
  self.directory.mkdir(mode=0o700,parents=True,exist_ok=True);self.log=(self.directory/'browser.log').open('wb')
  env={'PATH':'/usr/bin:/bin','HOME':str(self.directory),'XDG_CONFIG_HOME':str(self.directory/'config'),'XDG_CACHE_HOME':str(self.directory/'cache'),'LANG':'C.UTF-8'}
  self.process=subprocess.Popen(['/usr/lib/chromium/chromium','--headless=new','--disable-gpu','--disable-background-networking','--disable-sync','--disable-extensions','--disable-component-update','--no-first-run','--no-default-browser-check','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+str(self.directory/'profile'),'about:blank'],env=env,stdout=self.log,stderr=self.log,start_new_session=True)
  deadline=time.monotonic()+20
  portfile=self.directory/'profile/DevToolsActivePort'
  while not portfile.exists():
   if self.process.poll() is not None:raise RuntimeError('Sandboxed Chromium startup failed; private log retained, no unsafe fallback.')
   if time.monotonic()>deadline:raise TimeoutError('Sandboxed browser startup deadline.')
   time.sleep(.05)
  port,path=portfile.read_text().splitlines()[:2];self.ws=WebSocket('127.0.0.1',int(port),path);return self
 def call(self,method,params=None,session=None):
  self.sequence+=1;packet={'id':self.sequence,'method':method,'params':params or {}}
  if session:packet['sessionId']=session
  self.ws.send(json.dumps(packet).encode())
  deadline=time.monotonic()+20
  while True:
   if time.monotonic()>deadline:raise TimeoutError('Bounded local browser RPC deadline.')
   result=self.ws.receive()
   if result.get('id')==self.sequence:
    if 'error' in result:raise RuntimeError('Local browser protocol failure: '+str(result['error'].get('code')))
    return result.get('result',{})
 def page(self,url='about:blank'):
  target=self.call('Target.createTarget',{'url':url})['targetId'];session=self.call('Target.attachToTarget',{'targetId':target,'flatten':True})['sessionId'];self.call('Page.enable',session=session);self.call('Runtime.enable',session=session);return session
 def evaluate(self,session,expression):
  result=self.call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True},session)
  if result.get('exceptionDetails'):raise RuntimeError('Test-page expression failed.')
  return result.get('result',{}).get('value')
 def close(self):
  import signal
  try:
   if self.ws and self.process and self.process.poll() is None:
    try:self.call('Browser.close')
    except (OSError,EOFError,RuntimeError):pass
   if self.process:
    try:self.process.wait(timeout=5)
    except subprocess.TimeoutExpired:
     try:os.killpg(self.process.pid,signal.SIGTERM)
     except ProcessLookupError:pass
     try:self.process.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=5)
  finally:
   if self.ws:self.ws.close()
   if hasattr(self,'log'):self.log.close()
