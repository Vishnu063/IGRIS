"""Fixed owned-site inspection inside a rootless offline filesystem container."""
import hashlib,http.server,json,os,resource,socket,threading,time
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(4*1024*1024,)*2)
resource.setrlimit(resource.RLIMIT_CPU,(45,45))
from playwright.sync_api import sync_playwright
class Site(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  if self.path!='/':self.send_error(404);return
  raw=Path('/site/index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Security-Policy',"default-src 'none'; connect-src 'self'; form-action 'none'");self.end_headers();self.wfile.write(raw)
 def do_POST(self):self.send_error(405)
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Site);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
origin='http://127.0.0.1:'+str(server.server_port);started=time.monotonic();denied=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/lib/chromium/chromium',chromium_sandbox=True,headless=True,args=['--disable-dev-shm-usage'])
  try:
   context=browser.new_context(accept_downloads=False,service_workers='block',viewport={'width':800,'height':600});page=context.new_page();page.set_default_timeout(8000)
   page.goto('chrome://sandbox');sandbox=page.locator('body').inner_text()
   if not all(x in sandbox for x in ('Namespace','PID namespaces\tYes','Network namespaces\tYes','Seccomp-BPF sandbox\tYes')):raise RuntimeError('Required Chromium sandbox unavailable.')
   def route(request):
    if request.request.method in ('GET','HEAD') and request.request.url==origin+'/':request.continue_()
    else:denied.append({'method':request.request.method,'destination':'outside_allowlist'});request.abort()
   context.route('**/*',route);context.route_web_socket('**/*',lambda ws:ws.close())
   page.goto(origin+'/');text=page.locator('body').inner_text();title=page.title();page.screenshot(path='/out/inspection.png',full_page=False)
   # Actual adversarial network attempts, made by this trusted acceptance worker only.
   for url in ('https://example.org/','http://127.0.0.1:1/private'):
    probe=context.new_page()
    try:probe.goto(url,timeout=1500)
    except Exception:pass
    finally:probe.close()
   page.evaluate("fetch('/submit',{method:'POST',body:'test fixture'}).catch(()=>null)")
   try:socket.create_connection(('192.0.2.1',9),timeout=.1)
   except OSError as error:network_denied=error.errno==101
   else:raise RuntimeError('External networking available.')
   if len(denied)!=3 or not network_denied:raise RuntimeError('Boundary verification failed.')
   result={'status':'completed','origin':'real_playwright','title':title,'text':text[:1500],'screenshot_sha256':hashlib.sha256(Path('/out/inspection.png').read_bytes()).hexdigest(),'sandbox':sandbox,'network_denied':network_denied,'blocked_requests':len(denied),'seconds':round(time.monotonic()-started,3),'peak_rss_kib':None}
  finally:browser.close()
finally:server.shutdown();server.server_close();thread.join(2)
result['peak_rss_kib']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
print(json.dumps(result))
