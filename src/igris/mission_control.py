"""Local interactive controller over existing chat, memory and Guardian services."""
import argparse,base64,binascii,hashlib,hmac,json,os,queue,re,secrets,shutil,socketserver,threading,time
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from uuid import uuid4
from .chat import ChatService
from .conversations import ConversationMemory
from .adapters.hermes_chat import DockerHermesAdapter
from .guardian.activities import OwnerActions,canonical
from .guardian.approvals import ApprovalStore
from .guardian.policy import Policy,Permission,Denied
from .guardian.tools import GuardianTools
from .guardian.review import ApprovalReviews
from .guardian.secrets import redact
from .memory import private_file

ROOT=Path(__file__).resolve().parents[2]
ASSETS=Path(__file__).with_name('web')

def validate_decision(data,pending):
    if type(data) is not dict or set(data)!={'mission_id','source','approve','action_sha256','confirmation'} or data['source'] not in ('chat','profile') or type(data['approve']) is not bool:raise Denied('Invalid owner decision.')
    from .adapters.contracts import identifier
    identifier(data['mission_id'])
    if not pending or pending['source']!=data['source']:raise Denied('No current pending snapshot.')
    review=pending['review']
    if data['action_sha256']!=review['action_sha256'] or data['confirmation']!=review['action_sha256'][:12]:raise Denied('Exact action digest confirmation required.')

class MissionControl:
    """One bounded worker; only it mutates ChatService's process-local missions."""
    owner='owner'
    def __init__(self,state,*,remember=False,tools_config=None,enable_specialists=False,enable_n8n=False,ops_instance=None,enable_mem0=False,backend_factory=DockerHermesAdapter,foreground=None,ops_mode='manual'):
        from .foreground import default_foreground
        self.foreground=foreground if foreground is not None else default_foreground()
        self.wake=threading.Event()
        if remember is not True:raise Denied('Explicit conversation storage consent required.')
        self.state=Path(state).absolute();self.state.mkdir(mode=0o700,parents=True,exist_ok=True)
        self.stop_event=threading.Event();self.lock=threading.RLock();self.queue=queue.Queue(8);self.decisions=queue.Queue(8)
        self.jobs={};self.task_signals={};self.waiting={};self.errors=[];self.stopped=False;self.cleanup_errors=[];self.started=time.time()
        db=self.state/'chat.sqlite3';self.memory=ConversationMemory(db,self.owner,initialize=not db.exists())
        self.backend=backend_factory(cancel=self.stop_event)
        self.chat=ChatService(self.owner,self.memory,self.backend,cancel=self.stop_event,foreground=self.foreground)
        self.tools=GuardianTools(self.owner,tools_config,self.state/'guardian.sqlite3') if tools_config else None
        self.tool_chat=ChatService(self.owner,self.memory,self.backend,tools=self.tools,reviews=ApprovalReviews(self.tools),cancel=self.stop_event,foreground=self.foreground) if self.tools else None
        self.components={'n8n':{'status':'disabled','last_result':None},'ops_pilot':{'status':'disabled','last_result':None},'voice':{'status':'hardware_blocked','dashboard_microphone':'disabled','native_capture':'not_connected','detail':'Use the separate manually started Handy/text entry point; browser microphone is not enabled.'},'specialists':{'status':'disabled','active':None}}
        profiles=[];permissions=set();self.semantic=None
        if enable_mem0:
            from .scoped_memory import ScopedFacts
            from .semantic_memory import SemanticMemory
            facts_path=self.state/'facts.sqlite3';facts=ScopedFacts(facts_path,self.owner,self.memory,initialize=not facts_path.exists())
            self.semantic=SemanticMemory(facts,Policy(self.owner,frozenset({Permission.READ,Permission.FILE_MODIFY})),enabled=True,cancel=self.stop_event)
            profiles.append(self.semantic.registration());permissions.update({Permission.READ,Permission.FILE_MODIFY})
            self.chat.knowledge=self.semantic
            if self.tool_chat:self.tool_chat.knowledge=self.semantic
        from .specialists.live import LiveSpecialists
        self.specialists=LiveSpecialists(enabled=enable_specialists)
        if enable_specialists:profiles.append(self.specialists.registration());permissions.add(Permission.SPECIALIST);self.components['specialists']['status']='enabled_on_request'
        if enable_n8n:raise Denied('n8n is excluded from single-task architecture; quarantine remains enforced.')
        from .integrations.catalog import default_catalog
        self.integrations=default_catalog(ops_instance=ops_instance,ops_mode=ops_mode)
        if ops_instance:
            from .guardian.activities import ExecutionProfile
            raw=json.loads(private_file(ops_instance).read_text())
            target=raw.get('container_id')
            if type(target) is not str or not re.fullmatch('[a-f0-9]{64}',target):raise Denied('Exact configured Ops target required.')
            def selected():return self.integrations.resolve('ops_pilot')
            profiles.append(ExecutionProfile('ops.lifecycle',lambda args:selected().normalize(args),lambda cancel:selected().scope(cancel),lambda args,cancel,permit:selected().execute(args,cancel,permit)))
            permissions.add(Permission.READ);self.components['ops_pilot'].update(status='configured_stopped',target_container_id=target,mode=ops_mode)
        path=self.state/'activities.sqlite3';store=ApprovalStore(path,initialize=not path.exists())
        self.actions=OwnerActions(Policy(self.owner,frozenset(permissions)),self.state,store,profiles,foreground=self.foreground)
        self.worker=threading.Thread(target=self._loop,name='igris-mission-worker',daemon=False);self.worker.start()

    def submit(self,kind,data):
        with self.lock:
            if self.stop_event.is_set():raise Denied('Emergency stop active; restart explicitly.')
            if kind not in ('chat','prepare','decision'):raise Denied('Unregistered dashboard action.')
            if type(data) is not dict:raise Denied('Typed action required.')
            # Validate and detach before enqueue; no caller-owned mutable arguments.
            data=json.loads(canonical(data)) if kind!='decision' else json.loads(json.dumps(data,allow_nan=False))
            request_id=data.pop('request_id',None)
            if request_id is not None:
                from .adapters.contracts import identifier
                identifier(request_id)
                if kind=='decision':raise Denied('Decision references must use their existing action snapshot.')
            if kind=='chat':
                if set(data)!={'conversation_id','prompt','mode'} or data['mode'] not in ('chat','tools'):raise Denied('Invalid chat action.')
                if data['mode']=='tools' and self.tool_chat is None:raise Denied('No approved tools profile configured.')
                self.memory.history(self.owner,data['conversation_id'])
                from .adapters.hermes_chat import chat_text
                chat_text(data['prompt'])
            elif kind=='prepare':
                if set(data)!={'operation','arguments'} or data['operation'] not in self.actions.profiles:raise Denied('Unregistered execution profile.')
            else:
                validate_decision(data,self.waiting.get(data.get('mission_id')))
            target=self.decisions if kind=='decision' else self.queue
            if target.full():raise Denied('Bounded queue full.')
            from .foreground import fingerprint
            ident=request_id or uuid4().hex;identity=fingerprint(kind,data)
            if ident in self.jobs:
                if self.jobs[ident].get('identity')!=identity:raise Denied('Retry body changed.')
                return {'job_id':ident,'status':self.jobs[ident]['status'],'duplicate':True}
            prior=self.foreground.lookup(self.owner,ident,identity=identity)
            if prior:return {'job_id':ident,'status':prior['status'],'task':prior,'duplicate':True}
            self.task_signals[ident]=threading.Event()
            self.jobs[ident]={'id':ident,'kind':kind,'identity':identity,'status':'queued','created_at':time.time()}
            if len(self.jobs)>64:
                removable=next((key for key,val in self.jobs.items() if val['status'] not in ('queued','running','awaiting_approval')),None)
                if removable:self.jobs.pop(removable);self.task_signals.pop(removable,None)
                else:self.jobs.pop(ident);raise Denied('Job capacity reached.')
            target.put_nowait((ident,kind,data));self.wake.set();return {'job_id':ident,'status':'queued'}

    def _pending(self,ident,source,review):
        with self.lock:
            original=self.tool_chat.reviews.get(self.owner,review['mission_id']) if source=='chat' else self.actions.review(self.owner,review['mission_id'])
            self.waiting[review['mission_id']]={'source':source,'review':review,'job_id':ident,'decision_deadline_unix':time.time()+max(0,original.deadline-time.monotonic())}
            self.jobs[ident].update(status='awaiting_approval',review=review,source=source)

    def _finish(self,ident,result):
        status=result.get('mission',{}).get('state') or (result.get('status') if result.get('status') in ('rejected','expired','timed_out','cancelled') else 'completed')
        with self.lock:self.jobs[ident].update(status=status,result=result,completed_at=time.time(),task=self.foreground.lookup(self.owner,ident))

    def _expire(self):
        # Single worker owns all chat review snapshots; no concurrent inference
        # starts while an approval is pending, so deadlines cannot be starved.
        with self.lock:items=list(self.waiting.items())
        for mid,pending in items:
            if self.stop_event.is_set():return
            if pending['source']=='chat':
                review=self.tool_chat.reviews.get(self.owner,mid);reason='cancelled' if self.foreground.active and self.foreground.active.cancel.is_set() else self.tool_chat.reviews.expiry(review)
                if reason:result=self.tool_chat.cancel(self.owner,mid,reason=reason)
            else:
                review=self.actions.review(self.owner,mid);reason='cancelled' if self.foreground.active and self.foreground.active.cancel.is_set() else self.actions._expiry(review)
                if reason:self.actions.cancel(self.owner,mid,reason=reason);result={'status':reason}
            if reason:
                with self.lock:self.waiting.pop(mid,None)
                self._finish(pending['job_id'],result)

    def _perform(self,ident,kind,data):
        with self.lock:self.jobs[ident]['status']='running'
        if kind=='chat':
            service=self.chat if data['mode']=='chat' else self.tool_chat
            result=service.ask(self.owner,data['conversation_id'],data['prompt'],task_id=ident,task_identity=self.jobs[ident]['identity'],task_cancel=self.task_signals[ident])
            if getattr(self.backend,'cleanup_verified',True) is not True:
                from .owned_jobs import UnconfirmedLaunch
                raise UnconfirmedLaunch('Worker cleanup requires operator review.')
            if result['mission']['state']=='awaiting_approval':self._pending(ident,'chat',result['approval']);return
        elif kind=='prepare':
            args=data['arguments']
            if data['operation']=='specialists.reason':args=self.specialists.arguments(args['role'],args['context']) if type(args) is dict and set(args)=={'role','context'} else args
            review=self.actions.prepare(self.owner,data['operation'],args,mission_id=ident,request_id=ident,task_identity=self.jobs[ident]['identity'],task_cancel=self.task_signals[ident])
            self._pending(ident,'profile',review.public());return
        else:
            mid=data['mission_id']
            with self.lock:pending=self.waiting.get(mid)
            if not pending:raise Denied('Pending action already consumed or cancelled.')
            if pending['source']=='chat':result=self.tool_chat.decide(self.owner,mid,approve=data['approve'],reviewed_digest=data['action_sha256'])
            else:
                self.actions.decide(self.owner,mid,approve=data['approve'],reviewed_digest=data['action_sha256'])
                if data['approve']:
                    operation=pending['review']['action']['operation']
                    with self.lock:
                        if operation=='specialists.reason':self.components['specialists']['active']=pending['review']['action']['arguments']['role']
                    component={'ops.lifecycle':'ops_pilot'}.get(operation)
                    if component:
                        with self.lock:self.components[component]['status']='running'
                    try:result=self.actions.run(self.owner,mid)
                    except BaseException:
                        if component:
                            with self.lock:self.components[component]['status']='failed_or_cancelled'
                        raise
                    finally:
                        with self.lock:self.components['specialists']['active']=None
                    if operation=='specialists.reason':
                        from .specialists.journal import record
                        record(self.state/'specialists.sqlite3',self.owner,self._review_object(pending),result)
                    component={'ops.lifecycle':'ops_pilot'}.get(operation)
                    if component:
                        with self.lock:self.components[component].update(status='last_verified_execution',last_result=result,observed_at=time.time())
                else:result={'status':'rejected','executed':False}
            with self.lock:self.waiting.pop(mid,None)
            self._finish(pending['job_id'],result)
        self._finish(ident,result)

    @staticmethod
    def _review_object(pending):
        # Journal needs the immutable review, not user/model fields. This adapter
        # is used only after the existing Guardian run has consumed its lease.
        from types import SimpleNamespace
        raw=pending['review'];return SimpleNamespace(actor=raw['actor'],mission_id=raw['mission_id'],digest=raw['action_sha256'])

    def _loop(self):
        try:
            while not self.stop_event.is_set():
                self.wake.clear()
                if self.stop_event.is_set():break
                self._expire()
                try:job=self.decisions.get_nowait()
                except queue.Empty:
                    if self.waiting:
                        timeout=max(.01,min(p['decision_deadline_unix'] for p in self.waiting.values())-time.time())
                        self.wake.wait(timeout);continue
                    try:job=self.queue.get_nowait()
                    except queue.Empty:self.wake.wait();continue
                ident,kind,data=job
                with self.lock:
                    if self.jobs[ident]['status']=='cancelled':continue
                    self.jobs[ident]['status']='running'
                try:self._perform(ident,kind,data)
                except Exception as exc:
                    from .owned_jobs import UnconfirmedLaunch
                    if isinstance(exc,UnconfirmedLaunch):
                        self.cleanup_errors.append(type(exc).__name__);self.emergency_stop()
                    with self.lock:
                        self.jobs[ident].update(status='failed',error='Action failed or denied: '+type(exc).__name__)
                        self.errors.append({'at':time.time(),'job_id':ident,'type':type(exc).__name__});self.errors=self.errors[-32:]
                    if kind=='decision':
                        with self.lock:pending=self.waiting.pop(data.get('mission_id'),None)
                        if pending:
                            try:
                                if pending['source']=='chat':self.tool_chat.cancel(self.owner,data['mission_id'])
                                else:self.actions.cancel(self.owner,data['mission_id'])
                            except (Denied,KeyError):pass
                            with self.lock:self.jobs[pending['job_id']].update(status='failed',error='Decision failed; no reusable authority.')
        finally:
            self.stop_event.set()
            for cleanup in [self.actions.close,self.chat.close,self.integrations.shutdown]+([self.tool_chat.close] if self.tool_chat else []):
                try:cleanup()
                except Exception as exc:
                    self.cleanup_errors.append(type(exc).__name__)
                    self.foreground.block_cleanup(self.owner,'component.cleanup')
            with self.lock:
                for job in self.jobs.values():
                    if job['status'] in ('queued','running','awaiting_approval'):job.update(status='cancelled',error='Emergency stop or shutdown.')
                self.waiting.clear();self.components['specialists']['active']=None;self.stopped=True

    def emergency_stop(self):
        self.stop_event.set();self.wake.set();self.actions.stop(self.owner)
        active=self.foreground.active
        if active:
            try:self.foreground.request_cancel(self.owner,active.task_id)
            except Denied:
                if self.foreground.active is not None:raise
        return {'status':'stop_requested','automatic_restart':False}

    def cancel_task(self,task_id):
        from .adapters.contracts import identifier
        identifier(task_id)
        with self.lock:
            job=self.jobs.get(task_id)
            if not job or job['status'] not in ('queued','running','awaiting_approval'):raise Denied('No active or queued owned task.')
            self.task_signals[task_id].set()
            if job['status']=='queued':
                job['task']=self.foreground.record_cancelled(self.owner,job['kind'],task_id,job['identity'])
                job['status']='cancelled';job['error']='Cancelled before execution.'
                self.wake.set();return {'status':'cancelled','job_id':task_id}
        active=self.foreground.active
        if active and active.task_id==task_id:
            try:self.foreground.request_cancel(self.owner,task_id)
            except Denied:
                if self.foreground.active is not None:raise
        self.wake.set();return {'status':'stop_requested','job_id':task_id}

    def close(self):
        self.emergency_stop();self.worker.join(timeout=35)
        if self.worker.is_alive() or self.cleanup_errors:raise RuntimeError('Tracked job cleanup not yet verified.')

    def snapshot(self,role):
        usage=shutil.disk_usage(self.state);rss=None
        try:
            fields=Path('/proc/self/status').read_text();match=re.search(r'^VmRSS:\s+(\d+)',fields,re.M);rss=int(match[1])*1024
        except (OSError,AttributeError):pass
        with self.lock:
            result={'igris':{'state':'stopped_with_errors' if self.stopped and self.cleanup_errors else 'stopped' if self.stopped else 'stopping' if self.stop_event.is_set() else 'manual_running','started_at':self.started},
                    'guardian':{'tools_profile_configured':self.tools is not None,'default_deny':True,'native_hermes_tools':False},
                    'foreground':self.foreground.snapshot(self.owner),
                    'components':json.loads(json.dumps(self.components)),
                    'resources':{'dashboard_rss_bytes':rss,'load_average':list(os.getloadavg()),'disk_free_bytes':usage.free},
                    'memory':{'backend':'private_sqlite','session_count':len(self.memory.sessions(self.owner)),'semantic_backend':self.semantic.last_backend if self.semantic else 'disabled'}}
            if 'ops_pilot' in self.integrations.loaded:result['components']['ops_pilot']['lifecycle']=self.integrations.loaded['ops_pilot'].health()
            if role=='owner':
                result.update(jobs=list(self.jobs.values()),pending_approvals=list(self.waiting.values()),sessions=list(self.memory.sessions(self.owner)),errors=list(self.errors),specialist_choices=self.specialists.choices())
                with self.actions.store._db() as db:result['audit']=[dict(zip(('at','operation','event'),row)) for row in db.execute('SELECT at,operation,event FROM audit ORDER BY sequence DESC LIMIT 20')]
                if self.tools:
                    with self.tools.store._db() as db:result['tool_audit']=[dict(zip(('at','operation','event'),row)) for row in db.execute('SELECT at,operation,event FROM tool_audit ORDER BY sequence DESC LIMIT 20')]
            else:
                result['job_counts']={key:sum(j['status']==key for j in self.jobs.values()) for key in ('queued','running','awaiting_approval')}
                # Raw observations, conversations, decisions, task/results and logs
                # are owner data, not public viewer status.
                for value in result['components'].values():value.pop('last_result',None);value.pop('target_container_id',None)
            return json.loads(json.dumps(result))


class _InteractiveHTTP(socketserver.ThreadingMixIn,HTTPServer):
    daemon_threads=True;request_queue_size=8
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):request.close();return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise
    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.slots.release()


def interactive_server(credentials,control,*,port=0):
    if type(control) is not MissionControl or type(port) is not int or not 0<=port<=65535:raise ValueError('Trusted local controller and port required.')
    if not any(name==control.owner and role=='owner' for name,(_,role) in credentials.items()):raise ValueError('Configured owner account required.')
    csrf={name:secrets.token_urlsafe(32) for name in credentials}
    class Handler(BaseHTTPRequestHandler):
        server_version='IGRIS';sys_version=''
        def setup(self):super().setup();self.connection.settimeout(2)
        def log_message(self,*args):pass
        def reply(self,status,payload,content_type='application/json'):
            if type(payload) is not bytes:payload=json.dumps(payload,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(payload)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            if status==401:self.send_header('WWW-Authenticate','Basic realm="IGRIS local owner"')
            self.end_headers();self.wfile.write(payload)
        def authenticate(self):
            host=f'127.0.0.1:{self.server.server_port}'
            if self.headers.get_all('Host',[])!=[host]:self.reply(403,{'error':'Host denied'});return None
            try:
                entries=self.headers.get_all('Authorization',[])
                if len(entries)!=1 or not entries[0].startswith('Basic ') or len(entries[0])>512:raise ValueError()
                name,supplied=base64.b64decode(entries[0][6:],validate=True).decode('ascii').split(':',1)
                expected,role=credentials.get(name,('',None))
                if not expected or not hmac.compare_digest(supplied,expected):raise ValueError()
                return name,role
            except (ValueError,UnicodeError,binascii.Error):self.reply(401,{'error':'Authentication required'});return None
        def do_GET(self):
            principal=self.authenticate()
            if principal is None:return
            name,role=principal
            try:
                if self.path in ('/','/app.js','/style.css'):
                    file,kind={'/':('control.html','text/html; charset=utf-8'),'/app.js':('control.js','text/javascript; charset=utf-8'),'/style.css':('control.css','text/css; charset=utf-8')}[self.path]
                    return self.reply(200,(ASSETS/file).read_bytes(),kind)
                if self.path=='/api/state':
                    view=control.snapshot(role)
                    if role=='owner' and name==control.owner:view['csrf']=csrf[name]
                    return self.reply(200,view)
                if self.path.startswith('/api/facts/'):
                    if role!='owner' or name!=control.owner or control.semantic is None:return self.reply(403,{'error':'Scoped memory not enabled for this owner'})
                    session=self.path[len('/api/facts/'):]
                    if not re.fullmatch('[a-f0-9]{32}',session):return self.reply(400,{'error':'Invalid session'})
                    control.semantic.policy.require('memory.search')
                    return self.reply(200,{'facts':control.semantic.facts.review(control.owner,session)})
                if self.path.startswith('/api/history/'):
                    if role!='owner' or name!=control.owner:return self.reply(403,{'error':'Owner required'})
                    session=self.path[len('/api/history/'):]
                    if not re.fullmatch('[a-f0-9]{32}',session):return self.reply(400,{'error':'Invalid session'})
                    return self.reply(200,{'history':[{'role':a,'content':b} for a,b in control.memory.history(control.owner,session)]})
                return self.reply(404,{'error':'Not found'})
            except Exception:return self.reply(503,{'error':'Requested data unavailable'})
        def do_POST(self):
            principal=self.authenticate()
            if principal is None:return
            name,role=principal
            if role!='owner' or name!=control.owner:return self.reply(403,{'error':'Owner required'})
            origin=f'http://127.0.0.1:{self.server.server_port}'
            if self.headers.get_all('Origin',[])!=[origin] or self.headers.get('Sec-Fetch-Site') not in (None,'same-origin','none'):return self.reply(403,{'error':'Origin denied'})
            supplied=self.headers.get_all('X-IGRIS-CSRF',[])
            if len(supplied)!=1 or not supplied[0].isascii() or len(supplied[0])>128 or not hmac.compare_digest(supplied[0],csrf[name]):return self.reply(403,{'error':'CSRF denied'})
            try:
                lengths=self.headers.get_all('Content-Length',[])
                if len(lengths)!=1 or not re.fullmatch('[0-9]{1,5}',lengths[0]) or not 0<int(lengths[0])<=16384 or self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type')!='application/json':raise ValueError()
                from .guardian.readonly import unique
                data=json.loads(self.rfile.read(int(lengths[0])),object_pairs_hook=unique)
                if type(data) is not dict:raise ValueError()
                if self.path=='/api/stop':
                    if data!={}:raise ValueError()
                    return self.reply(202,control.emergency_stop())
                if self.path=='/api/cancel':
                    if set(data)!={'task_id'}:raise ValueError()
                    return self.reply(202,control.cancel_task(data['task_id']))
                if self.path=='/api/session':
                    if data!={} or control.stop_event.is_set():raise Denied('Session creation stopped.')
                    return self.reply(201,{'conversation_id':control.memory.create(control.owner,approved=True)})
                kinds={'/api/chat':'chat','/api/prepare':'prepare','/api/decision':'decision'}
                if self.path not in kinds:return self.reply(404,{'error':'Not found'})
                return self.reply(202,control.submit(kinds[self.path],data))
            except (ValueError,TypeError,KeyError,Denied):
                try:control.actions._deny('unavailable','unavailable')
                except Exception:return self.reply(503,{'error':'Denial audit unavailable; execution blocked'})
                return self.reply(400,{'error':'Invalid, unauthorized or stale action'})
            except Exception:return self.reply(503,{'error':'Action unavailable; no success assumed'})
    server=_InteractiveHTTP(('127.0.0.1',port),Handler);server.slots=threading.BoundedSemaphore(8);return server


def main():
    parser=argparse.ArgumentParser(description='Manually start local authenticated Mission Control; no public bind or automatic restart.')
    parser.add_argument('--remember',action='store_true',required=True);parser.add_argument('--accounts-file',type=Path,required=True);parser.add_argument('--state-dir',type=Path,default=ROOT/'runtime/chat');parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--tools-config',type=Path);parser.add_argument('--enable-specialists',action='store_true');parser.add_argument('--enable-n8n',action='store_true',help='Unsupported; retained solely to reject old startup requests.');parser.add_argument('--ops-mode',choices=('manual','on_demand','monitoring'),default='manual');parser.add_argument('--enable-mem0',action='store_true');targets=parser.add_mutually_exclusive_group();targets.add_argument('--ops-instance',type=Path);targets.add_argument('--ops-demo',action='store_true',help='Explicitly create a disposable local monitoring target, removed on dashboard exit.')
    args=parser.parse_args();raw=json.loads(private_file(args.accounts_file).read_text());accounts={key:tuple(value) for key,value in raw.items()}
    from .dashboard import make_server
    server=None;control=None;fixture=None
    try:
        if args.ops_demo:
            from .integrations.ops_runtime import DisposableOpsFixture
            fixture=DisposableOpsFixture().start()
        control=MissionControl(args.state_dir,remember=args.remember,tools_config=args.tools_config,enable_specialists=args.enable_specialists,enable_n8n=args.enable_n8n,ops_mode=args.ops_mode,enable_mem0=args.enable_mem0,ops_instance=fixture.config_path if fixture else args.ops_instance)
        server=make_server(accounts,control=control,port=args.port);print(f'IGRIS local dashboard: http://127.0.0.1:{server.server_port} (credentials remain in private account file)',flush=True);server.serve_forever(poll_interval=.1)
    except KeyboardInterrupt:pass
    finally:
        try:
            if server:server.server_close()
        finally:
            try:
                if control:control.close()
            finally:
                if fixture:fixture.close()
if __name__=='__main__':
    from igris.mission_control import main as entry
    entry()
