"""Actual local HTTP/SQLite/broker; inference fixture is explicitly synthetic."""
import base64,http.client,json,secrets,sys,tempfile,threading,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.dashboard import make_server
from igris.mission_control import MissionControl
from igris.adapters.hermes_chat import ToolProposal
class ProposalFixture:
 """Not real inference; only supplies a protocol object to test HTTP controls."""
 def __init__(self,*,cancel):self.cancel=cancel
 def propose(self,request,**kwargs):return ToolProposal(request.request_id,json.dumps({'operation':'get_current_time','arguments':{}}),'a'*64,1,.01,1,1)
 def reply(self,request):raise RuntimeError('No mocked real chat response.')
class MissionControlTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);root=Path(self.tmp.name);work=root/'work';work.mkdir(mode=0o700)
  config=root/'tools.json';config.write_text(json.dumps({'version':1,'workspace':str(work),'allowed_operations':['get_current_time'],'directories':[],'files':[],'approval_required':['get_current_time']}));config.chmod(0o600)
  self.control=MissionControl(root/'state',remember=True,tools_config=config,backend_factory=ProposalFixture)
  self.owner=secrets.token_urlsafe(32);self.viewer=secrets.token_urlsafe(32)
  self.server=make_server({'owner':(self.owner,'owner'),'viewer':(self.viewer,'viewer')},control=self.control)
  self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True);self.thread.start();self.addCleanup(self.close)
  self.origin='http://127.0.0.1:'+str(self.server.server_port);self.csrf=self.request('/api/state')[1]['csrf']
 def close(self):
  self.server.shutdown();self.server.server_close();self.thread.join(2)
  if getattr(self,'expected_cleanup_failure',False):
   with self.assertRaises(RuntimeError):self.control.close()
  else:self.control.close()
 def request(self,path,body=None,*,account='owner',headers=None):
  secret=self.owner if account=='owner' else self.viewer
  auth='Basic '+base64.b64encode((account+':'+secret).encode()).decode()
  values={'Authorization':auth}
  if body is not None:values.update(Origin=self.origin,**{'X-IGRIS-CSRF':getattr(self,'csrf',''),'Content-Type':'application/json'})
  values.update(headers or {});connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
  try:
   connection.request('POST' if body is not None else 'GET',path,body=None if body is None else json.dumps(body),headers=values);response=connection.getresponse();raw=response.read()
   return response.status,json.loads(raw) if 'application/json' in response.getheader('Content-Type','') else raw.decode()
  finally:connection.close()
 def wait(self,predicate):
  deadline=time.monotonic()+4
  while time.monotonic()<deadline:
   state=self.request('/api/state')[1]
   if predicate(state):return state
   time.sleep(.02)
  self.fail('Bounded controller condition not reached.')
 def test_auth_roles_csrf_origin_host_and_safe_assets(self):
  self.assertEqual(self.request('/api/state',headers={'Authorization':'Basic invalid'})[0],401)
  viewer=self.request('/api/state',account='viewer')[1]
  for field in ('csrf','jobs','sessions','pending_approvals','audit'):self.assertNotIn(field,viewer)
  for headers in ({'X-IGRIS-CSRF':''},{'X-IGRIS-CSRF':'é'},{'Origin':'http://foreign.invalid'},{'Host':'foreign.invalid'},{'Sec-Fetch-Site':'cross-site'}):
   self.assertEqual(self.request('/api/session',{},headers=headers)[0],403)
  self.assertEqual(self.request('/api/stop',{},account='viewer')[0],403)
  self.assertEqual(self.request('/')[0],200)
  js=self.request('/app.js')[1];self.assertNotIn('innerHTML',js);self.assertIn('textContent',js)
  html=self.request('/')[1];self.assertIn('name="viewport"',html)
  self.assertEqual(self.request('/api/prepare',{'operation':'shell','arguments':{}})[0],400)
 def test_actual_broker_after_owner_digest_and_replay_denied(self):
  session=self.request('/api/session',{})[1]['conversation_id']
  self.request('/api/chat',{'conversation_id':session,'prompt':'Synthetic planner fixture requests time.','mode':'tools'})
  state=self.wait(lambda state:bool(state['pending_approvals']));pending=state['pending_approvals'][0];review=pending['review']
  self.assertEqual(self.control.memory.history('owner',session),())
  decision={'mission_id':review['mission_id'],'source':'chat','approve':True,'action_sha256':review['action_sha256'],'confirmation':review['action_sha256'][:12]}
  self.assertEqual(self.request('/api/decision',dict(decision,confirmation='forged'))[0],400)
  self.assertEqual(self.request('/api/decision',decision)[0],202)
  self.wait(lambda state:not state['pending_approvals'])
  history=self.request('/api/history/'+session)[1]['history'];self.assertEqual(len(history),2);self.assertIn('Guardian executed get_current_time',history[1]['content'])
  self.assertEqual(self.request('/api/decision',decision)[0],400)
  self.assertEqual(self.request('/api/history/'+session,account='viewer')[0],403)
  with self.control.tools.store._db() as db:self.assertEqual(db.execute('SELECT used FROM approvals').fetchone()[0],1)
 def test_pending_reject_stop_and_no_auto_restart(self):
  session=self.request('/api/session',{})[1]['conversation_id'];payload={'conversation_id':session,'prompt':'Fixture time request','mode':'tools'}
  self.request('/api/chat',payload);self.wait(lambda s:bool(s['pending_approvals']))
  self.assertEqual(self.request('/api/stop',{})[0],202)
  state=self.wait(lambda s:s['igris']['state']=='stopped');self.assertEqual(state['pending_approvals'],[])
  self.assertEqual(self.control.memory.history('owner',session),());self.assertIsNone(self.control.memory.sessions('owner')[0]['active'])
  self.assertEqual(self.request('/api/chat',payload)[0],400)
  with self.control.tools.store._db() as db:self.assertEqual(db.execute('SELECT used FROM approvals').fetchone()[0],0)
 def test_no_storage_consent(self):
  with self.assertRaises(PermissionError):MissionControl(Path(self.tmp.name)/'other')
 def test_pending_timeout_releases_chat_reservation(self):
  session=self.request('/api/session',{})[1]['conversation_id']
  self.request('/api/chat',{'conversation_id':session,'prompt':'Fixture planner','mode':'tools'})
  self.wait(lambda state:bool(state['pending_approvals']))
  # Trusted test clock acceleration only; actual SQLite/HTTP/controller cleanup.
  self.control.tool_chat.reviews.monotonic=lambda:time.monotonic()+61
  self.wait(lambda state:not state['pending_approvals'])
  self.assertIsNone(self.control.memory.sessions('owner')[0]['active'])
  with self.control.tools.store._db() as db:self.assertEqual(db.execute('SELECT used FROM approvals').fetchone()[0],0)
 def test_duplicate_host_and_length_rejected(self):
  for duplicate in ('Host','Content-Length'):
   conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
   try:
    conn.putrequest('POST','/api/stop',skip_host=True)
    headers={'Host':'127.0.0.1:'+str(self.server.server_port),'Authorization':'Basic '+base64.b64encode(('owner:'+self.owner).encode()).decode(),'Origin':self.origin,'X-IGRIS-CSRF':self.csrf,'Content-Type':'application/json','Content-Length':'2'}
    for key,value in headers.items():conn.putheader(key,value)
    conn.putheader(duplicate,headers[duplicate]);conn.endheaders(b'{}');response=conn.getresponse();response.read()
    self.assertEqual(response.status,403 if duplicate=='Host' else 400)
   finally:conn.close()
  self.assertFalse(self.control.stop_event.is_set())

 def test_unconfirmed_creation_stops_and_requires_operator_review(self):
  from igris.owned_jobs import UnconfirmedLaunch
  def fixture(request):
   self.control.backend.cleanup_verified=False
   raise UnconfirmedLaunch('Synthetic unknown create response, no real resource.')
  self.control.backend.reply=fixture;self.expected_cleanup_failure=True
  session=self.request('/api/session',{})[1]['conversation_id']
  self.request('/api/chat',{'conversation_id':session,'prompt':'Fixture failure','mode':'chat'})
  state=self.wait(lambda state:state['igris']['state']=='stopped_with_errors')
  self.assertFalse(state['pending_approvals']);self.assertEqual(self.control.memory.history('owner',session),())
  self.assertEqual(self.request('/api/chat',{'conversation_id':session,'prompt':'Retry','mode':'chat'})[0],400)
