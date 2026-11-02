"""Actual authenticated browser, real Hermes proposal, owner approval and stop/cancel."""
import base64,hashlib,json,secrets,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from browser_test_client import Browser
from igris.mission_control import MissionControl
from igris.dashboard import make_server
from igris.foreground import Foreground
from igris.isolated import docker_command,docker_environment

def model_running():
 result=subprocess.run(docker_command()+['ps','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5);return bool(result.stdout.strip())
def main():
 assert [x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','address'],text=True))]==['lo'];subprocess.run(['ip','link','set','lo','up'],check=True)
 try:socket.create_connection(('192.0.2.1',9),timeout=.1)
 except OSError as error:assert error.errno==101
 else:raise AssertionError('Offline namespace required.')
 with tempfile.TemporaryDirectory(dir=ROOT/'runtime/single-task',prefix='browser-') as folder:
  root=Path(folder);workspace=root/'workspace';workspace.mkdir(mode=0o700);config=root/'tools.json';config.write_text(json.dumps({'version':1,'workspace':str(workspace),'allowed_operations':['get_current_time'],'directories':[],'files':[],'approval_required':['get_current_time']}));config.chmod(0o600)
  foreground=Foreground(root/'foreground');control=MissionControl(root/'state',remember=True,tools_config=config,foreground=foreground);secret=secrets.token_urlsafe(32);server=make_server({'owner':(secret,'owner')},control=control);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True);thread.start();browser=Browser(root/'browser')
  try:
   browser.start();page=browser.page();browser.call('Network.enable',session=page);browser.call('Network.setExtraHTTPHeaders',{'headers':{'Authorization':'Basic '+base64.b64encode(('owner:'+secret).encode()).decode()}},page);browser.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True},page);browser.call('Page.navigate',{'url':'http://127.0.0.1:'+str(server.server_port)},page)
   def wait(predicate,timeout=20):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
     if predicate():return
     time.sleep(.1)
    raise TimeoutError('Real single-task UI condition not reached.')
   wait(lambda:browser.evaluate(page,"!document.getElementById('owner').hidden"));browser.evaluate(page,"document.getElementById('new').click()");wait(lambda:len(control.memory.sessions('owner'))==1)
   def send(text,mode='chat'):
    browser.evaluate(page,"document.getElementById('mode').value="+json.dumps(mode)+";document.getElementById('prompt').value="+json.dumps(text)+";document.getElementById('chat').requestSubmit()")
   send('Explain safe software development in detail.');wait(model_running,45);wait(lambda:browser.evaluate(page,"JSON.parse(document.getElementById('status').textContent).foreground.active!==null"));active=foreground.active.task_id;tick=time.monotonic();browser.evaluate(page,"document.getElementById('cancel-task').click()");wait(lambda:foreground.lookup('owner',active)['status']=='cancelled',20);cancel_seconds=time.monotonic()-tick;assert not model_running() and not control.stop_event.is_set();print('Actual UI foreground cancellation PASS',flush=True)
   send('IGRIS, tell me the current time using your tool.','tools');wait(lambda:bool(control.waiting),180);assert not model_running();assert foreground.snapshot('owner')['state']=='waiting_for_approval'
   wait(lambda:browser.evaluate(page,"Boolean(document.querySelector('#approvals input'))"));digest=next(iter(control.waiting.values()))['review']['action_sha256'][:12];browser.evaluate(page,"document.querySelector('#approvals input').value="+json.dumps(digest)+";document.querySelector('#approvals button').click()")
   wait(lambda:not control.waiting,20);assert len(control.memory.history('owner',control.memory.sessions('owner')[0]['id']))==2
   print('Actual Hermes -> GUI approval -> real Guardian time PASS',flush=True)
   send('Explain reliable deployment verification in detail.');wait(model_running,45);tick=time.monotonic();browser.evaluate(page,"document.getElementById('stop').click()");wait(lambda:control.stopped,20);stop_seconds=time.monotonic()-tick;assert not model_running() and control.stop_event.is_set()
   dimensions=browser.evaluate(page,'({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})');assert dimensions['width']==dimensions['scrollWidth']==390
   proof={'status':'PASS','actual_hermes_time_proposal':True,'actual_owner_gui_approval_and_guardian_execution':True,'actual_cancel_then_new_task':True,'actual_emergency_stop':True,'cancel_seconds':cancel_seconds,'emergency_stop_seconds':stop_seconds,'dimensions':dimensions,'n8n_loaded_or_started':False,'optional_integrations_loaded':list(control.integrations.loaded),'owner_inputs':'Automated trusted browser fixtures, not AI authorization.','source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['src/igris/mission_control.py','src/igris/foreground.py','src/igris/chat.py','src/igris/web/control.js','src/igris/web/control.html','scripts/test_single_task_dashboard_live.py']}}
  finally:
   try:browser.close()
   finally:
    try:server.shutdown();server.server_close();thread.join(2)
    finally:control.close()
 (ROOT/'docs/validation/single-task-dashboard-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
