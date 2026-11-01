"""Actual browser/HTTP/Hermes/Guardian/n8n/Ops acceptance in an offline namespace.

Owner clicks/credentials are explicit automated fixtures. No model/browser mock.
No product browser capability is enabled by this trusted development test.
"""
import base64,errno,hashlib,http.client,json,os,re,secrets,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from browser_test_client import Browser
from igris.dashboard import make_server
from igris.mission_control import MissionControl
from igris.integrations.ops_runtime import DisposableOpsFixture
from igris.isolated import docker_command,docker_environment

class Progress(list):
 def append(self,item):
  super().append(item);print(item['case']+': '+item['result'],flush=True)
  (ROOT/'runtime/task7/partial.json').write_text(json.dumps(list(self),indent=2)+'\n')

def main():
 # Caller must explicitly create a new user+network namespace; never change host
 # networking. Only bring up the namespace's initially isolated loopback.
 addresses=json.loads(subprocess.check_output(['ip','-j','address'],text=True))
 if [row['ifname'] for row in addresses]!=['lo']:raise RuntimeError('Dedicated offline namespace required; do not run directly.')
 subprocess.run(['ip','link','set','lo','up'],check=True)
 try:socket.create_connection(('192.0.2.1',9),timeout=.2)
 except OSError as exc:assert exc.errno==errno.ENETUNREACH
 else:raise AssertionError('External network unexpectedly available.')
 out=ROOT/'runtime/task7';out.mkdir(mode=0o700,exist_ok=True);observations=Progress();control=None;server=None;browser=None;fixture=None
 started=time.monotonic()
 with tempfile.TemporaryDirectory(dir=out,prefix='acceptance-') as folder:
  root=Path(folder)
  try:
   fixture=DisposableOpsFixture().start();work=root/'workspace';work.mkdir(mode=0o700)
   config=root/'tools.json';config.write_text(json.dumps({'version':1,'workspace':str(work),'allowed_operations':['get_current_time'],'directories':[],'files':[],'approval_required':['get_current_time']}));config.chmod(0o600)
   control=MissionControl(root/'state',remember=True,tools_config=config,enable_specialists=True,enable_n8n=True,ops_instance=fixture.config_path)
   owner=secrets.token_urlsafe(32);viewer=secrets.token_urlsafe(32);accounts={'owner':(owner,'owner'),'viewer':(viewer,'viewer')}
   server=make_server(accounts,control=control);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start();origin='http://127.0.0.1:'+str(server.server_port)
   auth='Basic '+base64.b64encode(('owner:'+owner).encode()).decode()
   def request(path,body=None,*,role='owner',extra=None):
    headers={'Authorization':'Basic '+base64.b64encode((role+':'+accounts[role][0]).encode()).decode()}
    if body is not None:headers.update(Origin=origin,**{'Content-Type':'application/json','X-IGRIS-CSRF':csrf})
    headers.update(extra or {});conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
    try:
     conn.request('GET' if body is None else 'POST',path,body=None if body is None else json.dumps(body),headers=headers);response=conn.getresponse();data=response.read();return response.status,json.loads(data)
    finally:conn.close()
   csrf=request('/api/state')[1]['csrf']
   def wait(predicate,timeout=220):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
     state=request('/api/state')[1]
     if predicate(state):return state
     if control.stopped:raise RuntimeError('Controller stopped during acceptance.')
     time.sleep(.15)
    raise TimeoutError('Live dashboard condition not reached; no success fabricated.')
   browser=Browser(root/'browser').start();sandbox_page=browser.page('chrome://sandbox');time.sleep(.3);sandbox=browser.evaluate(sandbox_page,'document.body.innerText')
   assert 'adequately sandboxed' in sandbox and re.search(r'Seccomp-BPF sandbox\s+Yes',sandbox) and re.search(r'PID namespaces\s+Yes',sandbox)
   page=browser.page();browser.call('Network.enable',session=page);browser.call('Network.setExtraHTTPHeaders',{'headers':{'Authorization':auth}},page)
   browser.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True},page);browser.call('Page.navigate',{'url':origin},page)
   deadline=time.monotonic()+10
   while not browser.evaluate(page,"document.getElementById('owner') && !document.getElementById('owner').hidden"):
    if time.monotonic()>deadline:raise TimeoutError('Authenticated real UI failed to load.')
    time.sleep(.1)
   browser.evaluate(page,"document.getElementById('new').click()")
   wait(lambda state:len(state['sessions'])==1)
   session=request('/api/state')[1]['sessions'][0]['id']
   time.sleep(.3);browser.evaluate(page,"document.getElementById('prompt').value='What is 7 plus 5? Reply only with the integer.';document.getElementById('chat').requestSubmit()")
   state=wait(lambda state:any(job.get('result',{}).get('saved') for job in state['jobs']))
   chat=next(job['result'] for job in state['jobs'] if job.get('result',{}).get('saved'));assert re.search(r'\b12\b',chat['reply']);observations.append({'case':'browser_real_chat','result':'PASS','reply':chat['reply']})
   time.sleep(.3);browser.evaluate(page,"document.getElementById('mode').value='tools';document.getElementById('prompt').value='IGRIS, tell me the current time using your tool.';document.getElementById('chat').requestSubmit()")
   state=wait(lambda state:bool(state['pending_approvals']));pending=state['pending_approvals'][0];review=pending['review'];assert review['action']['operation']=='get_current_time'
   with control.tools.store._db() as db:assert db.execute('SELECT COUNT(*) FROM tool_audit WHERE event=\'completed\'').fetchone()[0]==0
   decision={'mission_id':review['mission_id'],'source':'chat','approve':True,'action_sha256':review['action_sha256'],'confirmation':review['action_sha256'][:12]}
   assert request('/api/decision',dict(decision,confirmation='forged'))[0]==400
   assert request('/api/decision',decision,role='viewer')[0]==403
   def click_decision(approve=True):
    current=request('/api/state')[1]['pending_approvals'][0];digest=current['review']['action_sha256'][:12]
    deadline=time.monotonic()+8
    while not browser.evaluate(page,"Boolean(document.querySelector('.approval input'))"):
     if time.monotonic()>deadline:raise TimeoutError('Approval UI not rendered.')
     time.sleep(.1)
    # Confirm the rendered action has the expected digest before actual click.
    expected=current['review']['action_sha256'];rendered=browser.evaluate(page,"document.querySelector('.approval pre').textContent")
    if expected not in rendered:
     time.sleep(2.1);rendered=browser.evaluate(page,"document.querySelector('.approval pre').textContent")
    assert expected in rendered
    browser.evaluate(page,"document.querySelector('.approval input').value="+json.dumps(digest)+";document.querySelectorAll('.approval button')["+('0' if approve else '1')+"].click()")
   click_decision();state=wait(lambda state:not state['pending_approvals'])
   history=request('/api/history/'+session)[1]['history'];assert len(history)==4 and 'Guardian executed get_current_time' in history[-1]['content']
   assert request('/api/decision',decision)[0]==400;observations.append({'case':'browser_real_hermes_time_proposal_guardian_approval_execution','result':'PASS','forged_confirmation':400,'viewer_decision':403,'replay':400})
   browser.evaluate(page,"document.getElementById('workflow').requestSubmit()")
   state=wait(lambda state:bool(state['pending_approvals']));assert state['pending_approvals'][0]['review']['action']['operation']=='n8n.calculate';click_decision()
   state=wait(lambda state:not state['pending_approvals']);workflow=state['components']['n8n']['last_result'];assert workflow and workflow['output']['total']==12
   observations.append({'case':'browser_approved_real_n8n','result':'PASS','response':workflow})
   browser.evaluate(page,"document.getElementById('ops').click()")
   state=wait(lambda state:bool(state['pending_approvals']));assert state['pending_approvals'][0]['review']['action']['operation']=='ops.monitor';click_decision()
   state=wait(lambda state:not state['pending_approvals']);monitor=state['components']['ops_pilot']['last_result'];assert monitor['origin']=='real_ops_pilot' and monitor['health']=='healthy' and not monitor['remediation_enabled']
   observations.append({'case':'browser_approved_real_ops_monitor','result':'PASS','container_state':monitor['container_state'],'health':monitor['health']})
   browser.evaluate(page,"document.getElementById('role').value='frontend';document.getElementById('context').value='Propose an accessible form label; no execution.';document.getElementById('specialist').requestSubmit()")
   state=wait(lambda state:bool(state['pending_approvals']));click_decision(False);wait(lambda state:not state['pending_approvals']);observations.append({'case':'browser_specialist_reject','result':'PASS','model_executed':False})
   # Actual mobile viewport and safe rendering, including full owner controls.
   dimensions=browser.evaluate(page,'({innerWidth:innerWidth,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,ownerVisible:!document.getElementById("owner").hidden})')
   assert dimensions['ownerVisible'] and dimensions['scrollWidth']<=dimensions['clientWidth'] and dimensions['innerWidth']<=390
   png=base64.b64decode(browser.call('Page.captureScreenshot',{'format':'png','captureBeyondViewport':False},page)['data']);(out/'mobile.png').write_bytes(png)
   observations.append({'case':'actual_mobile_viewport','result':'PASS','dimensions':dimensions,'screenshot_sha256':hashlib.sha256(png).hexdigest()})
   browser.evaluate(page,"document.getElementById('role').value='backend';document.getElementById('context').value='Write a small title validation function. Advice only.';document.getElementById('specialist').requestSubmit()")
   state=wait(lambda state:bool(state['pending_approvals']));click_decision();wait(lambda state:state['components']['specialists']['active']=='backend')
   deadline=time.monotonic()+30
   while True:
    active=subprocess.run(docker_command()+['ps','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5)
    if active.stdout.strip():break
    if time.monotonic()>deadline:raise TimeoutError('No real specialist worker observed before stop.')
    time.sleep(.1)
   stop_start=time.monotonic();browser.evaluate(page,"document.getElementById('stop').click()")
   deadline=time.monotonic()+30
   while request('/api/state')[1]['igris']['state']!='stopped':
    if time.monotonic()>deadline:raise TimeoutError('Emergency stop cleanup not verified.')
    time.sleep(.1)
   stop_seconds=time.monotonic()-stop_start
   assert request('/api/chat',{'conversation_id':session,'prompt':'Do not restart.','mode':'chat'})[0]==400
   remaining=subprocess.run(docker_command()+['ps','--all','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5);assert not remaining.stdout.strip()
   state=request('/api/state')[1];assert not state['pending_approvals'] and state['components']['specialists']['active'] is None
   assert all(item['active'] is None for item in control.memory.sessions('owner'))
   observations.append({'case':'browser_emergency_stop_real_specialist_worker','result':'PASS','seconds':stop_seconds,'cleanup_verified':True,'new_execution_denied':400})
   viewer_state=request('/api/state',role='viewer')[1];assert all(key not in viewer_state for key in ('csrf','jobs','sessions','audit','pending_approvals'));assert request('/api/history/'+session,role='viewer')[0]==403
   proof={'status':'PASS','observations':observations,'browser_sandbox_status':sandbox,'browser_version':browser.call('Browser.getVersion'),'offline_namespace':True,'external_network_error':'ENETUNREACH','owner_interaction':'Automated trusted owner browser clicks and fixture credentials; no model authorization.','mocked_integrations':False,'voice':'Not connected; no physical microphone or Mac playback tested.','seconds':time.monotonic()-started,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/igris/mission_control.py','src/igris/dashboard.py','src/igris/chat.py','src/igris/owned_jobs.py','src/igris/adapters/hermes_chat.py','src/igris/isolated.py','src/igris/web/control.html','src/igris/web/control.js','src/igris/web/control.css','scripts/browser_test_client.py','scripts/test_mission_control_live.py']}}
  finally:
   errors=[]
   callbacks=[]
   if browser:callbacks.append(browser.close)
   if server:callbacks.extend([server.shutdown,server.server_close,lambda:thread.join(2)])
   if control:callbacks.append(control.close)
   if fixture:callbacks.append(fixture.close)
   for cleanup in callbacks:
    try:cleanup()
    except Exception as exc:errors.append(type(exc).__name__)
   if errors:raise RuntimeError('Task-owned acceptance cleanup failed: '+','.join(errors))
   if server and thread.is_alive():raise RuntimeError('Local server cleanup not verified.')
 proof['cleanup_verified']=True
 (out/'live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'status':'PASS','cases':len(observations),'seconds':proof['seconds']}),flush=True)
if __name__=='__main__':main()
