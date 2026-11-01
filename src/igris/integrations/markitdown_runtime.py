"""Explicit allowlisted documents -> isolated optional MarkItDown worker."""
import hashlib,io,json,os,re,stat,tempfile,zipfile
from pathlib import Path,PurePosixPath
from ..guardian.activities import ExecutionProfile,ExecutionPermit
from ..guardian.policy import Denied
from ..guardian.broker import open_parent
from ..guardian.secrets import redact
from ..isolated import IsolatedWorker,Cancelled
from ..adapters.contracts import AdapterUnavailable,ContractError
ROOT=Path(__file__).resolve().parents[3];FORMATS=frozenset({'.pdf','.docx','.xlsx','.pptx','.html'});MAX_INPUT=4*1024*1024

def document_parts(value):
 if type(value) is not str or len(value)>256:raise Denied('Bounded document path required.')
 parts=value.split('/')
 if len(parts)>4 or any(not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,63}',p) or p in ('.','..') for p in parts) or Path(value).suffix not in FORMATS:raise Denied('Unsupported document path.')
 if any(any(w in p.casefold() for w in ('secret','credential','private','password','token','.env')) for p in parts):raise Denied('Sensitive document path denied.')
 return parts

def validate_document(raw,suffix):
 if not 0<len(raw)<=MAX_INPUT:raise Denied('Document size limit.')
 if suffix in ('.docx','.xlsx','.pptx'):
  try:
   with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    entries=archive.infolist();total=0;names=set()
    if len(entries)>500:raise Denied('Archive entry limit.')
    for entry in entries:
     parts=PurePosixPath(entry.filename)
     if parts.is_absolute() or '..' in parts.parts or '\\' in entry.filename or entry.filename in names or (entry.external_attr>>16)&0o170000==stat.S_IFLNK or entry.flag_bits&1:raise Denied('Unsafe archive entry.')
     names.add(entry.filename);total+=entry.file_size
     if total>32*1024*1024 or entry.file_size>8*1024*1024 or entry.file_size>max(1,entry.compress_size)*100:raise Denied('Archive expansion limit.')
     if any(x in entry.filename.casefold() for x in ('vbaproject','embeddings/','activex/')):raise Denied('Embedded executable content unsupported.')
     if entry.filename.endswith(('.xml','.rels')):
      data=archive.read(entry)
      if any(x in data.lower() for x in (b'<!doctype',b'<!entity',b'targetmode="external"',b"targetmode='external'")):raise Denied('External relationship or XML entity denied.')
  except (zipfile.BadZipFile,RuntimeError,ValueError):raise Denied('Malformed document archive.') from None
 elif suffix=='.pdf' and not raw.startswith(b'%PDF-'):raise Denied('Invalid PDF signature.')
 return raw

def package_digest(path):
 digest=hashlib.sha256()
 for file in sorted(Path(path).rglob('*')):
  if '__pycache__' in file.parts or file.name in ('RECORD','INSTALLER','REQUESTED') and file.parent.name.endswith('.dist-info'):continue
  if file.is_symlink():raise Denied('Unexpected dependency symlink.')
  if file.is_file():digest.update(str(file.relative_to(path)).encode()+b'\0'+hashlib.sha256(file.read_bytes()).digest())
 return digest.hexdigest()

class Documents:
 def __init__(self,workspace,files,*,enabled=False):
  self.enabled=enabled is True;self.workspace=Path(workspace).absolute();self.files=tuple(files);self.profile=ROOT/'integrations/markitdown/profile.json'
  info=self.workspace.stat()
  if self.workspace.resolve(strict=True)!=self.workspace or not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o077 or (self.workspace/'.git').exists() or not self.workspace.is_relative_to(ROOT/'runtime') or not 0<len(self.files)<=10 or len(set(self.files))!=len(self.files):raise Denied('Private explicit task-owned document workspace required.')
  for name in self.files:document_parts(name)
 def read(self,name):
  if name not in self.files:raise Denied('Document not explicitly allowlisted.')
  parts=document_parts(name);parent=open_parent(self.workspace,parts)
  try:
   fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
   with os.fdopen(fd,'rb') as handle:
    info=os.fstat(handle.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>MAX_INPUT:raise Denied('Unsafe document file.')
    return validate_document(handle.read(MAX_INPUT+1),Path(name).suffix)
  finally:os.close(parent)
 def normalize(self,raw):
  if type(raw) is not dict or set(raw)!={'path'} or type(raw['path']) is not str or raw['path'] not in self.files:raise Denied('Exact configured document required.')
  document_parts(raw['path']);return dict(raw)
 def scope(self,cancel):
  if not self.enabled:raise AdapterUnavailable('MarkItDown disabled until explicitly configured.')
  if cancel.is_set():raise Cancelled('Document conversion cancelled.')
  profile=json.loads(self.profile.read_text());packages=ROOT/'runtime/markitdown/venv/lib/python3.14/site-packages'
  if package_digest(packages)!=profile['packages_sha256']:raise Denied('Pinned optional converters changed.')
  for name,want in profile['files'].items():
   if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=want:raise Denied('Document worker asset changed.')
  return {'workspace':str(self.workspace),'documents':{name:hashlib.sha256(self.read(name)).hexdigest() for name in self.files},'profile_sha256':hashlib.sha256(self.profile.read_bytes()).hexdigest(),'network':'none','plugins':False}
 def execute(self,arguments,cancel,permit):
  if not self.enabled or type(permit) is not ExecutionPermit:raise Denied('Guardian document lease required.')
  review=permit.consume('documents.convert',self.normalize(arguments));raw=self.read(arguments['path']);suffix=Path(arguments['path']).suffix
  # Bind actual snapshot once more to the scope approved by Guardian.
  from ..guardian.activities import canonical
  snapshot=self.scope(cancel)
  if snapshot['documents'][arguments['path']]!=hashlib.sha256(raw).hexdigest() or hashlib.sha256(canonical(snapshot).encode()).hexdigest()!=json.loads(review.binding_json)['scope_sha256']:raise Denied('Document scope changed after authorization.')
  profile=json.loads(self.profile.read_text())
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime/markitdown',prefix='input-') as folder:
   file=Path(folder)/('document'+suffix);file.write_bytes(raw);file.chmod(0o600)
   output=IsolatedWorker(cancel=cancel).run(profile['image'],['/opt/igris/python/bin/python3.14','-I','-S','/opt/igris/worker.py'],[(ROOT/'runtime/python3149/python','/opt/igris/python'),(ROOT/'runtime/markitdown/venv/lib/python3.14/site-packages','/opt/igris/packages'),(ROOT/'integrations/markitdown/worker.py','/opt/igris/worker.py'),(file,'/input/document'+suffix)],component='documents',timeout=60,memory='1g',payload=json.dumps({'suffix':suffix}).encode())
  result=json.loads(output)
  if result.get('origin')!='real_markitdown' or result.get('format')!=suffix or result.get('network_denied') is not True or type(result.get('markdown')) is not str or len(result['markdown'].encode())>6000:raise ContractError('Invalid conversion output.')
  result['markdown']=redact(result['markdown']);result['untrusted_content']=True;result['input_sha256']=hashlib.sha256(raw).hexdigest();return result
 def registration(self):return ExecutionProfile('documents.convert',self.normalize,self.scope,self.execute)
