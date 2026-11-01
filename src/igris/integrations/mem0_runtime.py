"""Pinned offline Mem0 index; authoritative scoped SQLite is never mounted."""
import fcntl,hashlib,json,math,os,re,tempfile,time
from pathlib import Path
from ..adapters.contracts import AdapterUnavailable,ContractError,identifier
from ..guardian.policy import Denied
from ..guardian.readonly import unique
from ..isolated import IsolatedWorker,Cancelled
from ..memory import private_file,knowledge_text
ROOT=Path(__file__).resolve().parents[3]
PACKAGES=ROOT/'runtime/mem0/venv/lib/python3.14/site-packages'


def package_digest(root):
    root=Path(root);digest=hashlib.sha256()
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ContractError('Unexpected optional-package symlink.')
        if not path.is_file():continue
        if path.name in ('RECORD','INSTALLER','REQUESTED') and path.parent.name.endswith('.dist-info'):continue
        digest.update(str(path.relative_to(root)).encode()+b'\0')
        with path.open('rb') as source:digest.update(hashlib.file_digest(source,'sha256').digest())
    return digest.hexdigest()


class Mem0Index:
    def __init__(self,*,enabled=False):
        self.enabled=enabled is True;self.profile_path=ROOT/'integrations/mem0/profile.json'
        self.profile=json.loads(self.profile_path.read_text()) if self.profile_path.exists() else None
    def preflight(self,cancel):
        if not self.enabled or self.profile is None:raise AdapterUnavailable('Optional Mem0 runtime disabled or unprepared.')
        if cancel.is_set():raise Cancelled('Memory operation cancelled.')
        for name,expected in self.profile['files'].items():
            path=ROOT/name
            if path.is_symlink():raise Denied('Unsafe memory asset.')
            with path.open('rb') as source:actual=hashlib.file_digest(source,'sha256').hexdigest()
            if actual!=expected:raise Denied('Pinned memory asset changed.')
        if package_digest(PACKAGES)!=self.profile['packages_sha256']:raise Denied('Pinned optional memory packages changed.')
    def query(self,policy,facts,conversation,query,*,cancel,probe=False):
        policy.require('memory.search')
        if policy.actor!=facts.owner:raise Denied('Memory owner policy mismatch.')
        knowledge_text(query,512) if query else None
        rows=facts.review(policy.actor,conversation);scope=facts.token(policy.actor,conversation)
        if not rows and not (ROOT/'runtime/mem0/index'/scope).exists():return {'backend':'sqlite_no_approved_facts','facts':[],'indexed_facts':0}
        self.preflight(cancel)
        folder=ROOT/'runtime/mem0';requests=folder/'requests';requests.mkdir(mode=0o700,exist_ok=True)
        index=folder/'index';index.mkdir(mode=0o700,exist_ok=True);state=index/scope;state.mkdir(mode=0o700,exist_ok=True)
        locks=folder/'index-locks';locks.mkdir(mode=0o700,exist_ok=True);lock=locks/(scope+'.lock')
        try:private_file(lock,create=True)
        except FileExistsError:pass
        private_file(lock)
        with lock.open('rb') as handle:
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise AdapterUnavailable('Scoped semantic index busy.') from None
            try:
                with tempfile.TemporaryDirectory(dir=requests) as temporary:
                    path=private_file(Path(temporary)/'facts.json',create=True)
                    snapshot={'scope':scope,'facts':[{key:row[key] for key in ('id','revision','text')} for row in rows]}
                    raw=json.dumps(snapshot,ensure_ascii=False,separators=(',',':')).encode()
                    if len(raw)>8*1024**2:raise ContractError('Bounded approved fact snapshot required.')
                    path.write_bytes(raw);digest=hashlib.sha256(raw).hexdigest()
                    packet={'scope':scope,'snapshot_sha256':digest,'query':query,'probe_extraction_denial':probe}
                    start=time.monotonic()
                    output=IsolatedWorker(cancel=cancel).run(self.profile['image'],['/opt/igris/python/bin/python3.14','-I','-S','/opt/igris/worker.py'],
                      [(ROOT/'runtime/python3149/python','/opt/igris/python'),(PACKAGES,'/opt/igris/packages'),(folder/'model','/models/minilm'),(ROOT/'integrations/mem0/worker.py','/opt/igris/worker.py'),(path,'/input/facts.json')],
                      component='mem0',timeout=180,memory='1g',mount_profile='mem0-semantic-index',state_directory=state,payload=json.dumps(packet).encode())
                    data=json.loads(output,object_pairs_hook=unique)
                    expected={'origin','scope','snapshot_sha256','results','indexed_facts','embedding_calls','extraction_calls','extraction_probe_denied','telemetry_enabled','elapsed_seconds','maxrss_kib'}
                    if type(data) is not dict or set(data)!=expected or data['origin']!='real_mem0_local' or data['scope']!=scope or data['snapshot_sha256']!=digest or data['telemetry_enabled'] is not False or data['extraction_probe_denied'] is not probe or data['extraction_calls']!=int(probe):raise ContractError('Unverified memory response.')
                    if type(data['results']) is not list or len(data['results'])>8 or type(data['indexed_facts']) is not int or data['indexed_facts']!=len(rows):raise ContractError('Invalid memory result bounds.')
                    if type(data['maxrss_kib']) is not int or data['maxrss_kib']<=0 or type(data['embedding_calls']) is not int or data['embedding_calls']<0 or type(data['elapsed_seconds']) not in (int,float) or not math.isfinite(data['elapsed_seconds']) or not 0<data['elapsed_seconds']<=180:raise ContractError('Invalid memory measurement.')
                    rebound=[];seen=set()
                    for hit in data['results']:
                        if type(hit) is not dict or set(hit)!={'id','revision','score'} or type(hit['revision']) is not int or type(hit['score']) not in (int,float) or not math.isfinite(hit['score']):raise ContractError('Invalid indexed fact reference.')
                        identifier(hit['id'])
                        try:row=facts.get(policy.actor,conversation,hit['id'])
                        except KeyError:continue
                        if row['revision']!=hit['revision'] or row['id'] in seen or hit['score']<0.15:continue
                        seen.add(row['id']);rebound.append(dict(row,score=hit['score']))
                    return {'backend':'real_mem0_local','facts':rebound[:3],'indexed_facts':len(rows),'metrics':{'worker_seconds':data['elapsed_seconds'],'wall_seconds':time.monotonic()-start,'maxrss_kib':data['maxrss_kib'],'embedding_calls':data['embedding_calls'],'index_disk_bytes':sum(p.lstat().st_size for p in state.rglob('*') if not p.is_symlink() and p.is_file())},'extraction_probe_denied':probe}
            finally:fcntl.flock(handle,fcntl.LOCK_UN)
