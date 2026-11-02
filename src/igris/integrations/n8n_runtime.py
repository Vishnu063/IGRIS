"""Opt-in real n8n CLI: one reviewed arithmetic workflow, Guardian approval first."""
import hashlib,json,math,os,re,stat
from pathlib import Path
from ..adapters.contracts import AdapterUnavailable,ContractError
from ..guardian.activities import ExecutionProfile,ExecutionPermit
from ..guardian.policy import Denied
from ..guardian.readonly import unique
from ..isolated import IsolatedWorker,Cancelled
ROOT=Path(__file__).resolve().parents[3]
RUNTIME=Path('/tmp/igris-task4-n8n')


def tree_digest(root,cancel):
    root=Path(root)
    if root!=RUNTIME or root.resolve(strict=True)!=root or root.stat().st_uid!=os.getuid() or stat.S_IMODE(root.stat().st_mode)!=0o700:raise ContractError('Private task-owned runtime required.')
    digest=hashlib.sha256()
    for directory,folders,files in os.walk(root,followlinks=False):
        for name in sorted(folders+files):
            if cancel.is_set():raise Cancelled('Runtime verification cancelled.')
            path=Path(directory)/name;info=path.lstat();relative=str(path.relative_to(root))
            if stat.S_ISLNK(info.st_mode):
                if not path.resolve(strict=True).is_relative_to(root):raise ContractError('Runtime symlink escape denied.')
                digest.update(('L\0'+relative+'\0'+os.readlink(path)+'\0').encode());continue
            if info.st_mode & 0o022:raise ContractError('Writable shared runtime file denied.')
            if stat.S_ISDIR(info.st_mode):continue
            if not stat.S_ISREG(info.st_mode):raise ContractError('Unsupported runtime file.')
            digest.update(('F\0'+relative+'\0'+str(stat.S_IMODE(info.st_mode))+'\0'+str(info.st_size)+'\0').encode())
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
            with os.fdopen(fd,'rb') as source:
                while chunk:=source.read(1024*1024):
                    if cancel.is_set():raise Cancelled('Runtime verification cancelled.')
                    digest.update(chunk)
        folders.sort()
    return digest.hexdigest()


def render(template,left,right):
    value=json.loads(template)
    assignments=value['nodes'][1]['parameters']['assignments']['assignments']
    assignments[0]['value']=left;assignments[1]['value']=right
    assignments[2]['value']='={{ ('+str(left)+') + ('+str(right)+') }}'
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


class RealN8n:
    def __init__(self,*,enabled=False):
        self.enabled=enabled is True
        self.profile_path=ROOT/'integrations/n8n/profile.json'
        self.template_path=ROOT/'workflows/n8n-bounded-calculation.json'
        self.profile_bytes=self.profile_path.read_bytes();self.profile=json.loads(self.profile_bytes)
        self.template=self.template_path.read_text()

    def security_status(self):
        try:
            data=json.loads((ROOT/'integrations/n8n/security-status.json').read_text(),object_pairs_hook=unique)
            if data.get('status')=='PASS' and data.get('runtime_tree_sha256')==self.profile['runtime_tree_sha256']:
                return 'PASS'
        except (OSError,ValueError,AttributeError):pass
        return 'BLOCKED_SECURITY_AUDIT'

    def require_security_review(self):
        if self.security_status()!='PASS':raise AdapterUnavailable('Pinned n8n quarantined after dependency audit; no workflow execution permitted.')

    def normalize(self,raw):
        if type(raw) is not dict or set(raw)!={'left','right'} or any(type(raw[k]) is not int or not -1000<=raw[k]<=1000 for k in raw):raise ContractError('Only two bounded integer operands are allowed.')
        return dict(raw,workflow_sha256=hashlib.sha256(render(self.template,raw['left'],raw['right'])).hexdigest())

    def scope(self,cancel):
        if not self.enabled:raise AdapterUnavailable('Real n8n disabled; no invocation attempted.')
        self.require_security_review()
        profile=self.profile
        if self.profile_path.read_bytes()!=self.profile_bytes or hashlib.sha256(self.template_path.read_bytes()).hexdigest()!=profile['template_sha256']:raise ContractError('Workflow or runtime profile changed.')
        worker=ROOT/'integrations/n8n/worker.py'
        if hashlib.sha256(worker.read_bytes()).hexdigest()!=profile['worker_sha256']:raise ContractError('Reviewed workflow worker changed.')
        if tree_digest(RUNTIME,cancel)!=profile['runtime_tree_sha256']:raise ContractError('Pinned n8n dependency tree changed.')
        return {'profile_sha256':hashlib.sha256(self.profile_bytes).hexdigest(),'runtime_tree_sha256':profile['runtime_tree_sha256'],
                'template_sha256':profile['template_sha256'],'worker_sha256':profile['worker_sha256'],'image':profile['image'],'network':'none','spend_inr':0}

    def execute(self,arguments,cancel,permit):
        if not self.enabled or type(permit) is not ExecutionPermit:raise Denied('Current Guardian execution lease required.')
        self.require_security_review()
        review=permit.consume('n8n.calculate',arguments)
        payload={'schema_version':1,'request_id':review.request_id,'mission_id':review.mission_id,'arguments':arguments}
        raw=IsolatedWorker(cancel=cancel).run(self.profile['image'],['/opt/igris/python/bin/python3.14','-I','-S','/opt/igris/worker.py'],
            [(ROOT/'runtime/python3149/python','/opt/igris/python'),(RUNTIME/'node','/opt/igris/node'),(RUNTIME/'node_modules','/opt/igris/node_modules'),
             (ROOT/'integrations/n8n/worker.py','/opt/igris/worker.py'),(self.template_path,'/opt/igris/template.json')],
            component='n8n',timeout=180,memory='2g',mount_profile='n8n-test-runtime',payload=json.dumps(payload).encode())
        data=json.loads(raw,object_pairs_hook=unique)
        if type(data) is not dict or set(data)!={'schema_version','request_id','mission_id','workflow_sha256','execution_id','status','output','origin','elapsed_seconds'}:raise ContractError('Invalid n8n result schema.')
        if (type(data['schema_version']) is not int or data['schema_version']!=1 or data['request_id']!=review.request_id or data['mission_id']!=review.mission_id or data['workflow_sha256']!=arguments['workflow_sha256'] or data['status']!='completed' or data['origin']!='real_n8n_cli' or type(data['execution_id']) is not str or not re.fullmatch('[0-9]{1,20}',data['execution_id'])):raise ContractError('Uncorrelated n8n result.')
        expected={'left':arguments['left'],'right':arguments['right'],'total':arguments['left']+arguments['right']}
        if type(data['output']) is not dict or set(data['output'])!=set(expected) or any(type(data['output'][k]) is not int or data['output'][k]!=value for k,value in expected.items()):raise ContractError('Actual workflow calculation did not match expected result.')
        if type(data['elapsed_seconds']) not in (int,float) or not math.isfinite(data['elapsed_seconds']) or not 0<data['elapsed_seconds']<=180:raise ContractError('Invalid workflow duration.')
        return data

    def registration(self):return ExecutionProfile('n8n.calculate',self.normalize,self.scope,self.execute)
