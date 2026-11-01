"""Actual owner browser approval + Mem0 indexing; no model inference claimed."""
import base64,hashlib,json,secrets,socket,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from browser_test_client import Browser
from igris.mission_control import MissionControl
from igris.dashboard import make_server

def main():
 assert [x['ifname'] for x in json.loads(subprocess.check_output(['ip','-j','address'],text=True))]==['lo']
 subprocess.run(['ip','link','set','lo','up'],check=True)
 try:socket.create_connection(('192.0.2.1',9),timeout=.2)
 except OSError as exc:assert exc.errno==101
 else:raise AssertionError('Dedicated offline namespace required.')
 out=ROOT/'runtime/mem0'
 with tempfile.TemporaryDirectory(dir=out,prefix='dashboard-') as folder:
  root=Path(folder);control=MissionControl(root/'state',remember=True,enable_mem0=True);secret=secrets.token_urlsafe(32);server=make_server({'owner':(secret,'owner')},control=control);thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start();browser=Browser(root/'browser')
  try:
   browser.start();page=browser.page();browser.call('Network.enable',session=page);browser.call('Network.setExtraHTTPHeaders',{'headers':{'Authorization':'Basic '+base64.b64encode(('owner:'+secret).encode()).decode()}},page)
   browser.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True},page);browser.call('Page.navigate',{'url':'http://127.0.0.1:'+str(server.server_port)},page)
   def wait(predicate,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
     if predicate():return
     time.sleep(.1)
    raise TimeoutError('Current memory UI condition not reached.')
   wait(lambda:browser.evaluate(page,"document.getElementById('owner')&&!document.getElementById('owner').hidden"))
   browser.evaluate(page,"document.getElementById('new').click()")
   wait(lambda:len(control.memory.sessions('owner'))==1);session=control.memory.sessions('owner')[0]['id']
   wait(lambda:browser.evaluate(page,"!document.getElementById('facts-panel').hidden"))
   browser.evaluate(page,"document.getElementById('fact-text').value='Prefer a dark interface theme.';document.getElementById('fact-category').value='preference';document.getElementById('save-fact').requestSubmit()")
   wait(lambda:bool(control.waiting));assert not control.semantic.facts.review('owner',session)
   wait(lambda:browser.evaluate(page,"Boolean(document.querySelector('#approvals input'))"))
   digest=next(iter(control.waiting.values()))['review']['action_sha256'][:12]
   browser.evaluate(page,"document.querySelector('#approvals input').value="+json.dumps(digest)+";document.querySelector('#approvals button').click()")
   wait(lambda:not control.waiting,timeout=45);rows=control.semantic.facts.review('owner',session);assert len(rows)==1
   assert control.semantic.last_backend=='real_mem0_local'
   wait(lambda:browser.evaluate(page,"document.querySelectorAll('#facts article').length===1"))
   # Correcting/deleting are prepared and independently reviewed; no mutation
   # occurs merely by clicking the Prepare deletion button.
   browser.evaluate(page,"document.querySelectorAll('#facts article button')[1].click()")
   wait(lambda:bool(control.waiting));assert len(control.semantic.facts.review('owner',session))==1
   wait(lambda:browser.evaluate(page,"document.querySelector('#approvals pre')&&document.querySelector('#approvals pre').textContent.includes('delete')"))
   digest=next(iter(control.waiting.values()))['review']['action_sha256'][:12]
   browser.evaluate(page,"document.querySelector('#approvals input').value="+json.dumps(digest)+";document.querySelectorAll('#approvals button')[1].click()")
   wait(lambda:not control.waiting);assert len(control.semantic.facts.review('owner',session))==1
   dimensions=browser.evaluate(page,'({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth})');assert dimensions['width']==dimensions['clientWidth']==dimensions['scrollWidth']==390
   with control.actions.store._db() as db:
    approvals=[list(row) for row in db.execute('SELECT status,used FROM approvals ORDER BY rowid')]
   assert approvals==[['approved',1],['denied',0]]
   proof={'status':'PASS','actual_browser_save_approval':True,'real_mem0_index':True,'delete_rejected_fact_preserved':True,'before_approval_no_fact':True,'approvals':approvals,'dimensions':dimensions,'inference':'Not invoked in this UI test; separate real memory-enriched Hermes acceptance exists.','owner_inputs':'Automated trusted owner fixtures, not model decisions.','source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['src/igris/mission_control.py','src/igris/web/control.html','src/igris/web/control.js','scripts/test_mem0_dashboard_live.py']}}
  finally:
   try:browser.close()
   finally:
    try:server.shutdown();server.server_close();thread.join(2)
    finally:control.close()
 proof['cleanup_verified']=True;(out/'dashboard-live.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'status':'PASS','cases':4}))
if __name__=='__main__':main()
