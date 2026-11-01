"""Disabled-by-default finite browser operation, with Guardian one-use authority."""
import hashlib,json,os,signal,subprocess,tempfile,time
from pathlib import Path
from ..guardian.activities import ExecutionProfile,ExecutionPermit
from ..guardian.policy import Denied
from ..isolated import Cancelled
from ..adapters.contracts import AdapterUnavailable,ContractError
ROOT=Path(__file__).resolve().parents[3]
class OwnedBrowser:
 def __init__(self,*,enabled=False):self.enabled=enabled is True;self.profile=ROOT/'integrations/playwright/profile.json'
 def normalize(self,raw):
  if type(raw) is not dict or raw!={'site':'owned_acceptance','action':'inspect_and_screenshot'}:raise Denied('Only fixed owned-site read-only inspection is registered.')
  return dict(raw)
 def scope(self,cancel):
  if not self.enabled:raise AdapterUnavailable('Playwright disabled; explicit owner configuration required.')
  if cancel.is_set():raise Cancelled('Browser cancelled.')
  data=json.loads(self.profile.read_text())
  for name,want in data['files'].items():
   file=Path(name) if name.startswith('/') else ROOT/name
   if file.is_symlink() or not file.is_file():raise Denied('Browser runtime asset unavailable.')
   with file.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
   if actual!=want:raise Denied('Pinned browser runtime asset changed.')
  digest=hashlib.sha256()
  for file in sorted(Path(data['package_root']).rglob('*')):
   if file.is_file() and '__pycache__' not in file.parts:digest.update(str(file.relative_to(data['package_root'])).encode()+b'\0'+hashlib.sha256(file.read_bytes()).digest())
  if digest.hexdigest()!=data['package_sha256']:raise Denied('Pinned Playwright package changed.')
  return {'profile_sha256':hashlib.sha256(self.profile.read_bytes()).hexdigest(),'network':'isolated_loopback_only','site':'owned_acceptance','chromium_sandbox':True}
 def execute(self,arguments,cancel,permit):
  if not self.enabled or type(permit) is not ExecutionPermit:raise Denied('Guardian browser lease required.')
  permit.consume('browser.inspect',self.normalize(arguments));profile=json.loads(self.profile.read_text())
  output=ROOT/'runtime/playwright';output.mkdir(mode=0o700,parents=True,exist_ok=True)
  with tempfile.TemporaryDirectory(dir=output,prefix='inspection-') as directory:
   args=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv','--setenv','HOME','/tmp','--setenv','PATH','/usr/bin','--setenv','LANG','C.UTF-8']
   for source,target in [('/usr','/usr'),('/lib','/lib'),('/lib64','/lib64'),(profile['python_root'],profile['python_root']),(profile['node'],profile['node']),(str(ROOT/'integrations/playwright/worker.py'),'/worker.py'),(str(ROOT/'integrations/playwright/site'),'/site')]:args+=['--ro-bind',source,target]
   args+=['--bind',directory,'/out','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--',profile['python'],'-I','/worker.py']
   # No shell, no host home/root mount, no controller DB/socket, no external network.
   started=time.monotonic();process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
   try:
    while True:
     if cancel.is_set():raise Cancelled('Browser cancelled.')
     if time.monotonic()-started>55:raise TimeoutError('Browser deadline exceeded.')
     try:stdout,stderr=process.communicate(timeout=.1);break
     except subprocess.TimeoutExpired:continue
    if process.returncode or len(stdout)>16384 or len(stderr)>65536:raise AdapterUnavailable('Isolated browser failed; no result accepted.')
    data=json.loads(stdout)
    if data.get('origin')!='real_playwright' or data.get('status')!='completed' or not data.get('network_denied') or data.get('blocked_requests')!=3:raise ContractError('Browser boundary proof missing.')
    image=Path(directory)/'inspection.png'
    if image.is_symlink() or not 0<image.stat().st_size<=4*1024*1024 or hashlib.sha256(image.read_bytes()).hexdigest()!=data['screenshot_sha256']:raise ContractError('Invalid screenshot artifact.')
    artifact=output/(data['screenshot_sha256']+'.png')
    if not artifact.exists():
     fd=os.open(artifact,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
     with os.fdopen(fd,'wb') as target:target.write(image.read_bytes())
    data['artifact']=str(artifact.relative_to(ROOT));return data
   finally:
    if process.poll() is None:
     os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
    process.stdout.close();process.stderr.close()
 def registration(self):return ExecutionProfile('browser.inspect',self.normalize,self.scope,self.execute)
