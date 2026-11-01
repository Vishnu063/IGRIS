"""Actual current UI/HTTP in offline namespace; no model inference claimed."""
import base64,hashlib,json,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from browser_test_client import Browser
from igris.mission_control import MissionControl
from igris.dashboard import make_server

def main():
 assert [row['ifname'] for row in json.loads(subprocess.check_output(['ip','-j','address'],text=True))]==['lo']
 subprocess.run(['ip','link','set','lo','up'],check=True)
 try:socket.create_connection(('192.0.2.1',9),timeout=.2)
 except OSError as exc:assert exc.errno==101
 else:raise AssertionError('Dedicated offline namespace required.')
 out=ROOT/'runtime/task7';out.mkdir(mode=0o700,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=out,prefix='layout-') as directory:
  root=Path(directory);control=MissionControl(root/'state',remember=True,enable_specialists=True);secret=__import__('secrets').token_urlsafe(32);server=make_server({'owner':(secret,'owner')},control=control)
  thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start();browser=Browser(root/'browser')
  try:
   browser.start();page=browser.page();browser.call('Network.enable',session=page);browser.call('Network.setExtraHTTPHeaders',{'headers':{'Authorization':'Basic '+base64.b64encode(('owner:'+secret).encode()).decode()}},page)
   browser.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True},page);browser.call('Page.navigate',{'url':'http://127.0.0.1:'+str(server.server_port)},page)
   deadline=time.monotonic()+10
   while not browser.evaluate(page,"document.querySelectorAll('#overview li').length===8 && !document.getElementById('owner').hidden"):
    if time.monotonic()>deadline:raise TimeoutError('Real UI failed to load summary.')
    time.sleep(.1)
   browser.evaluate(page,"document.getElementById('new').click()")
   deadline=time.monotonic()+5
   while len(control.memory.sessions('owner'))!=1:
    if time.monotonic()>deadline:raise TimeoutError('Current UI conversation control failed.')
    time.sleep(.1)
   browser.evaluate(page,"document.getElementById('role').value='frontend';document.getElementById('context').value='Review a supplied form label. Advice only.';document.getElementById('specialist').requestSubmit()")
   deadline=time.monotonic()+8
   while not control.waiting or not browser.evaluate(page,"Boolean(document.querySelector('.approval input'))"):
    if time.monotonic()>deadline:raise TimeoutError('Current approval UI failed to render.')
    time.sleep(.1)
   pending=next(iter(control.waiting.values()));digest=pending['review']['action_sha256'][:12]
   browser.evaluate(page,"document.querySelector('.approval input').value="+json.dumps(digest)+";document.querySelectorAll('.approval button')[1].click()")
   deadline=time.monotonic()+5
   while control.waiting:
    if time.monotonic()>deadline:raise TimeoutError('Current UI Reject failed.')
    time.sleep(.1)
   assert any(job['status']=='rejected' for job in control.jobs.values())
   dimensions=browser.evaluate(page,'({width:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,technicalDetailsClosed:!document.getElementById("status").parentElement.open,chatTop:document.getElementById("owner").getBoundingClientRect().top})')
   assert dimensions['scrollWidth']==dimensions['clientWidth'] and dimensions['width']==390 and dimensions['technicalDetailsClosed'] and dimensions['chatTop']<844
   png=base64.b64decode(browser.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False},page)['data']);(out/'mobile-overview.png').write_bytes(png)
   proof={'status':'PASS','dimensions':dimensions,'actual_authenticated_ui':True,'actual_new_conversation':True,'actual_guardian_reject':True,'model_inference':'Not invoked in this layout check; full live acceptance recorded separately.','screenshot_sha256':hashlib.sha256(png).hexdigest(),'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/igris/web/control.html','src/igris/web/control.css','src/igris/web/control.js','scripts/browser_test_client.py','scripts/test_dashboard_layout_live.py']}}
  finally:
   try:browser.close()
   finally:
    try:server.shutdown();server.server_close();thread.join(2)
    finally:control.close()
 proof['cleanup_verified']=True;(out/'layout-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
