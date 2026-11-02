"""On-demand real Ops Pilot library with exact-target read-only Docker delegation."""
from dataclasses import asdict
import hashlib,json,os,platform,re,secrets,subprocess,tempfile,time
from pathlib import Path
from ..adapters.contracts import AdapterUnavailable,ContractError
from ..adapters.ops_monitoring import TargetBinding,parse_export
from ..guardian.activities import ExecutionProfile,ExecutionPermit
from ..guardian.policy import Denied
from ..guardian.docker_read_proxy import ExactDockerReads,daemon_read
from ..guardian.readonly import unique
from ..isolated import IsolatedWorker,docker_command,docker_environment,Cancelled
from ..memory import private_file
ROOT=Path(__file__).resolve().parents[3]
HEALTH='http://127.0.0.1:8789/health'


def source_digest(path):
    digest=hashlib.sha256()
    for file in sorted(Path(path).rglob('*')):
        if file.is_symlink():raise ContractError('Source symlinks unsupported.')
        if not file.is_file():continue
        digest.update(str(file.relative_to(path)).encode()+b'\0')
        with file.open('rb') as source:digest.update(hashlib.file_digest(source,'sha256').digest())
    return digest.hexdigest()


def inspect_target(cid):
    if not re.fullmatch('[a-f0-9]{64}',cid):raise ContractError('Immutable target ID required.')
    status,_,raw=daemon_read('/containers/'+cid+'/json')
    if status!=200:raise AdapterUnavailable('Owned monitoring target unavailable.')
    return json.loads(raw)


class DisposableOpsFixture:
    """Explicit development/test setup only, never registered as a model tool."""
    def __init__(self):self.name='igris-ops-fixture-'+secrets.token_hex(6);self.directory=None;self.cid=None;self.launch=None
    def start(self):
        if platform.system()!='Linux' or platform.machine()!='x86_64':raise AdapterUnavailable('Reviewed cloud Linux x86_64 fixture only; no Mac/ARM substitution.')
        self.temporary=tempfile.TemporaryDirectory(dir=ROOT/'runtime/ops',prefix='instance-');self.directory=Path(self.temporary.name)
        appdata=self.directory/'appdata';appdata.mkdir(mode=0o700);marker=secrets.token_hex(32);self.marker=marker
        image='sha256:71ed6a3c8bc579133b3983e8e61599e7b1ecfba0a4985045451c6e8ec36fd855'
        args=docker_command()+['create','--pull=never','--name',self.name,'--label','com.igris.fixture=completion-task-05',
             '--label','com.igris.fixture-marker='+marker,'--label','com.igris.owner='+marker[:32],'--network','none','--read-only','--user',f'{os.getuid()}:{os.getgid()}',
             '--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--cpus','.25','--pids-limit','32',
             '--tmpfs','/tmp:rw,noexec,nosuid,size=33554432,mode=1777','--env','IGRIS_FIXTURE_MARKER='+marker]
        for source,target,readonly in [(ROOT/'runtime/python3149/python','/opt/igris/python',True),(ROOT/'integrations/ops/fixture_app.py','/opt/igris/app.py',True),(appdata,'/appdata',False)]:
            args+=['--mount',f'type=bind,src={source},dst={target}'+(',readonly' if readonly else '')]
        args+=[image,'/opt/igris/python/bin/python3.14','-I','-S','/opt/igris/app.py']
        try:
            from ..owned_jobs import OwnedLaunch,assert_no_pending_launches
            assert_no_pending_launches(ROOT/'runtime/ops')
            self.launch=OwnedLaunch(ROOT/'runtime/ops',docker_command(),docker_environment(),self.name,marker[:32])
            self.cid=self.launch.create(args)
            subprocess.run(docker_command()+['start',self.cid],env=docker_environment(),capture_output=True,check=True,timeout=15)
            if not re.fullmatch('[a-f0-9]{64}',self.cid):raise ContractError('No actual fixture ID.')
            deadline=time.monotonic()+15
            while not (appdata/'app.sock').exists():
                if time.monotonic()>deadline:raise TimeoutError('Real application socket unavailable.')
                time.sleep(.1)
            code,_,raw=daemon_read('/info')
            if code!=200:raise AdapterUnavailable('Daemon identity unavailable.')
            config={'container_id':self.cid,'daemon_id':json.loads(raw)['ID'],'fixture_marker':marker,'image':image,'app_socket':str(appdata/'app.sock')}
            self.config_path=private_file(self.directory/'instance.json',create=True);self.config_path.write_text(json.dumps(config));return self
        except BaseException:self.close();raise
    def stop_application(self):subprocess.run(docker_command()+['stop','--time','2',self.cid],env=docker_environment(),capture_output=True,check=True,timeout=10)
    def close(self):
        if self.launch is not None and self.launch.request_sent and self.launch.cid is None:self.launch.cleanup()
        if self.name:
            status,_,raw=daemon_read('/containers/'+(self.cid or self.name)+'/json')
            if status==200:
                observed=json.loads(raw)
                if not getattr(self,'marker',None) or observed.get('Config',{}).get('Labels',{}).get('com.igris.fixture-marker')!=self.marker:raise Denied('Unrelated container preserved; fixture name/identity mismatch.')
                if self.launch is None:raise Denied('No acknowledged fixture ownership; preserved.')
            if self.launch is not None:self.launch.cleanup()
            remaining=subprocess.run(docker_command()+['ps','--all','--filter','name=^/'+self.name+'$','--format','{{.ID}}'],env=docker_environment(),capture_output=True,text=True,check=True,timeout=5)
            if remaining.stdout.strip():raise RuntimeError('Fixture removal not verified; storage preserved.')
            self.name=None
        if self.directory:self.temporary.cleanup();self.directory=None


class RealOpsMonitor:
    def __init__(self,instance_path,*,enabled=False):
        self.enabled=enabled is True
        self.path=private_file(Path(instance_path).absolute());self.config_bytes=self.path.read_bytes();self.config=json.loads(self.config_bytes)
        if set(self.config)!={'container_id','daemon_id','fixture_marker','image','app_socket'}:raise ContractError('Invalid monitoring instance.')
        for key in ('container_id','fixture_marker'):
            if type(self.config[key]) is not str or not re.fullmatch('[a-f0-9]{64}',self.config[key]):raise ContractError('Invalid fixture identity.')
        self.socket_path=Path(self.config['app_socket'])
        if self.socket_path.parent!=self.path.parent/'appdata' or self.socket_path.resolve(strict=True)!=self.socket_path:raise ContractError('Unexpected fixture socket.')
        self.profile_path=ROOT/'integrations/ops/profile.json';self.profile_bytes=self.profile_path.read_bytes();self.profile=json.loads(self.profile_bytes)
        self.read_key=secrets.token_hex(32)

    def normalize(self,raw):
        if type(raw) is not dict or set(raw)!={'container_id'} or raw['container_id']!=self.config['container_id']:raise ContractError('Only the explicitly configured disposable target is authorized.')
        return raw

    def scope(self,cancel):
        if not self.enabled:raise AdapterUnavailable('Ops Pilot live monitoring disabled.')
        if cancel.is_set():raise Cancelled('Monitoring cancelled.')
        if self.path.read_bytes()!=self.config_bytes or self.profile_path.read_bytes()!=self.profile_bytes:raise Denied('Monitoring configuration changed.')
        for name,expected in self.profile['sources'].items():
            if source_digest(ROOT/'runtime/ops'/name)!=expected:raise Denied('Pinned unmodified upstream source changed.')
        for name,expected in self.profile['files'].items():
            with (ROOT/name).open('rb') as source:
                if hashlib.file_digest(source,'sha256').hexdigest()!=expected:raise Denied('Reviewed monitoring worker changed.')
        target=inspect_target(self.config['container_id']);labels=target.get('Config',{}).get('Labels',{})
        if target.get('Id')!=self.config['container_id'] or target.get('Image')!=self.config['image'] or labels.get('com.igris.fixture')!='completion-task-05' or labels.get('com.igris.fixture-marker')!=self.config['fixture_marker']:raise Denied('Target is outside this disposable development scope.')
        code,_,raw=daemon_read('/info')
        if code!=200 or json.loads(raw)['ID']!=self.config['daemon_id']:raise Denied('Daemon identity changed.')
        return {'instance_sha256':hashlib.sha256(self.config_bytes).hexdigest(),'profile_sha256':hashlib.sha256(self.profile_bytes).hexdigest(),
                'read_credential_sha256':hashlib.sha256(self.read_key.encode()).hexdigest(),'container_id':self.config['container_id'],'daemon_id':self.config['daemon_id'],'network':'none','remediation_enabled':False}

    def execute(self,arguments,cancel,permit):
        if not self.enabled or type(permit) is not ExecutionPermit:raise Denied('Guardian monitoring lease required.')
        review=permit.consume('ops.monitor',arguments)
        with tempfile.TemporaryDirectory(dir=ROOT/'runtime/ops',prefix='read-proxy-') as folder:
            proxy=ExactDockerReads(Path(folder)/'docker.sock',self.config['container_id'],self.config['daemon_id'],self.read_key).start()
            try:
                packet={'container_id':self.config['container_id'],'read_key':self.read_key,'fixture_marker':self.config['fixture_marker'],'request_id':review.request_id,'mission_id':review.mission_id}
                raw=IsolatedWorker(cancel=cancel).run(self.profile['image'],['/opt/igris/python/bin/python3.14','-I','-S','/opt/igris/worker.py'],
                    [(ROOT/'runtime/python3149/python','/opt/igris/python'),(ROOT/'runtime/ops/docker','/opt/igris/bin/docker'),
                     (ROOT/'runtime/ops/ops-pilot','/opt/igris/ops'),(ROOT/'runtime/ops/triage','/opt/igris/triage'),
                     (ROOT/'integrations/ops/worker.py','/opt/igris/worker.py'),(proxy.path,'/input/docker.sock'),(self.socket_path,'/input/app.sock')],
                    component='ops-monitor',timeout=90,memory='1g',payload=json.dumps(packet).encode())
                return self.parse(json.loads(raw,object_pairs_hook=unique),review,proxy.events)
            finally:proxy.close()
    def parse(self,data,review,events):
        if type(data) is not dict or set(data)!={'schema_version','origin','request_id','mission_id','export'} or data['origin']!='real_ops_pilot' or data['request_id']!=review.request_id or data['mission_id']!=review.mission_id or type(data['schema_version']) is not int or data['schema_version']!=1:raise ContractError('Unverified or uncorrelated Ops Pilot result.')
        binding=TargetBinding(self.config['container_id'],'igris-readonly',HEALTH)
        observation=parse_export(data['export'],binding,origin='real_ops_pilot')
        view=json.loads(json.dumps(asdict(observation)))
        view.update(remediation_enabled=False,transport_audit=list(events))
        return view

    def registration(self):return ExecutionProfile('ops.monitor',self.normalize,self.scope,self.execute)
