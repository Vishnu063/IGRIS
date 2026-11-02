"""Actual browser and lazily loaded Ops component, with real Guardian decisions."""
import base64,hashlib,json,secrets,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from browser_test_client import Browser
from igris.mission_control import MissionControl
from igris.dashboard import make_server
from igris.foreground import Foreground
from igris.integrations.ops_runtime import DisposableOpsFixture

def main():
 assert [x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','address'],text=True))]==['lo'];subprocess.run(['ip','link','set','lo','up'],check=True)
 fixture=DisposableOpsFixture().start()
 try:
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime/single-task',prefix='ops-ui-') as folder:
   root=Path(folder);control=MissionControl(root/'state',remember=True,ops_instance=fixture.config_path,foreground=Foreground(root/'foreground'));assert control.integrations.loaded=={};secret=secrets.token_urlsafe(32);server=make_server({'owner':(secret,'owner')},control=control);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);thread.start();browser=Browser(root/'browser')
   try:
    browser.start();page=browser.page();browser.call('Network.enable',session=page);browser.call('Network.setExtraHTTPHeaders',{'headers':{'Authorization':'Basic '+base64.b64encode(('owner:'+secret).encode()).decode()}},page);browser.call('Page.navigate',{'url':'http://127.0.0.1:'+str(server.server_port)},page)
    def wait(predicate):
     end=time.monotonic()+30
     while time.monotonic()<end:
      if predicate():return
      time.sleep(.1)
     raise TimeoutError('Real Ops UI condition timed out.')
    wait(lambda:browser.evaluate(page,"!document.getElementById('owner').hidden"));observations=[]
    for button,approve in [('ops-start',False),('ops-start',True),('ops',True),('ops-stop',True)]:
     browser.evaluate(page,"document.getElementById("+json.dumps(button)+").click()");wait(lambda:bool(control.waiting));wait(lambda:browser.evaluate(page,"Boolean(document.querySelector('#approvals input'))"));adapter=control.integrations.loaded['ops_pilot']
     if button=='ops-start':assert adapter.process is None
     full_digest=next(iter(control.waiting.values()))['review']['action_sha256'];wait(lambda:browser.evaluate(page,"document.querySelector('#approvals pre').textContent.includes("+json.dumps(full_digest)+")"));digest=full_digest[:12];browser.evaluate(page,"document.querySelector('#approvals input').value="+json.dumps(digest)+";document.querySelectorAll('#approvals button')["+str(0 if approve else 1)+"].click()");wait(lambda:not control.waiting)
     if button=='ops-start':assert (adapter.process is not None)==approve
     if button=='ops':assert control.components['ops_pilot']['last_result']['observation']['health']=='healthy'
     if button=='ops-stop':assert adapter.process is None
     observations.append({'button':button,'approved':approve,'health':adapter.health()});print(button+': '+str(approve)+' actual Ops UI PASS',flush=True)
    wait(lambda:browser.evaluate(page,"document.getElementById('overview').textContent.includes('stopped (manual)')"));assert not browser.evaluate(page,"document.getElementById('overview').textContent.includes('undefined')")
    assert 'igris.integrations.n8n_runtime' not in sys.modules
    proof={'status':'PASS','real_browser_and_ops':True,'lazy_until_requested':True,'manual_mode':True,'reject_starts_no_worker':True,'observations':observations,'n8n_imported_or_started':False,'owner_inputs':'Automated trusted browser decisions, not model authorization.','source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/igris/mission_control.py','src/igris/web/control.js','src/igris/integrations/ops_lifecycle.py','scripts/test_single_task_ops_dashboard.py']}}
   finally:
    try:browser.close()
    finally:
     try:server.shutdown();server.server_close();thread.join(2)
     finally:control.close()
 finally:fixture.close()
 (ROOT/'docs/validation/single-task-ops-dashboard.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
