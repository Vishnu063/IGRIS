"""Future authorized Mac preparation only; no cloud-to-Mac installation pathway."""
import argparse,hashlib,json,os,platform,shutil,stat,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PACKAGE=ROOT/'packaging/macos';NAME='igris';LIMA_VERSION='2.2.1'
class Blocked(RuntimeError):pass

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def native_gate():
 if platform.system()!='Darwin' or platform.machine()!='arm64':raise Blocked('Requires explicitly authorized native Apple Silicon macOS; no Linux/x86 substitution.')
 if sys.version_info<(3,11):raise Blocked('Existing native Python >=3.11 required; installer does not bootstrap Python.')

def inventory():
 return {'system':platform.system(),'architecture':platform.machine(),'python':platform.python_version(),'lima_installed':bool(shutil.which('limactl')),'free_bytes':shutil.disk_usage(Path.home()).free,'hardware_acceptance':'BLOCKED','assistant_startup':'BLOCKED: ARM64 Guardian/runtime not verified','autostart':False,'mac_modified':False}

def install(root):
 root=Path(root).absolute()
 if root.exists() or root.is_symlink():raise Blocked('Existing installation/user files preserved; no overwrite.')
 if root.parent.resolve(strict=True)!=root.parent:raise Blocked('Canonical existing parent required.')
 root.mkdir(mode=0o700);created=[]
 for name in ('lima.yaml','assets.json','guardian-arm64-candidate.json'):
  target=root/name;fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as stream:stream.write((PACKAGE/name).read_bytes())
  created.append(name)
 manifest={'schema_version':1,'installation_id':'igris-mac-preparation','files':{name:digest(root/name) for name in created},'vm_name':NAME,'assistant_verified':False,'autostart':False}
 fd=os.open(root/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as stream:json.dump(manifest,stream,indent=2);stream.write('\n')
 return manifest

def check(root):
 root=Path(root).absolute();info=root.lstat()
 if root.resolve(strict=True)!=root or not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:raise Blocked('Private canonical preparation directory required.')
 for name in ('manifest.json','lima.yaml','assets.json','guardian-arm64-candidate.json'):
  info=(root/name).lstat()
  if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:raise Blocked('Unexpected preparation file; preserved.')
 manifest=json.loads((root/'manifest.json').read_text())
 if set(manifest)!={'schema_version','installation_id','files','vm_name','assistant_verified','autostart'} or manifest['schema_version']!=1 or manifest['installation_id']!='igris-mac-preparation' or manifest['vm_name']!=NAME or manifest['assistant_verified'] is not False or manifest['autostart'] is not False or set(manifest['files'])!={'lima.yaml','assets.json','guardian-arm64-candidate.json'}:raise Blocked('Unknown preparation manifest; preserved.')
 for name,want in manifest['files'].items():
  if digest(root/name)!=want or digest(root/name)!=digest(PACKAGE/name):raise Blocked('Modified configuration preserved; review before continuing.')
 return manifest

def uninstall(root):
 manifest=check(root);root=Path(root)
 if (root/'vm-state').exists():raise Blocked('VM state preserved: stop, back up and review the dedicated VM before uninstalling its control files.')
 for name in manifest['files']:(root/name).unlink()
 (root/'manifest.json').unlink();retained=sorted(p.name for p in root.iterdir())
 if not retained:root.rmdir()
 return {'removed':'unchanged manifest-listed preparation files only','retained':retained,'vm_deleted':False,'user_data_deleted':False}

def vm_command(root,action):
 check(root)
 for name in ('default.yaml','override.yaml'):
  if (Path(root)/'vm-state/_config'/name).exists():raise Blocked('Unreviewed Lima defaults/overrides could change isolation; preserved and blocked.')
 binary=shutil.which('limactl')
 if not binary:raise Blocked('Lima 2.2.1 must be explicitly installed/reviewed by the owner first; no automatic Homebrew installation.')
 version=subprocess.check_output([binary,'--version'],text=True,timeout=5).strip()
 if version!='limactl version '+LIMA_VERSION:raise Blocked('Pinned Lima 2.2.1 required; other versions need review.')
 env=dict(os.environ,LIMA_HOME=str(Path(root)/'vm-state'));args=[binary]
 if action=='start-vm':args+=['start','--name='+NAME,'--tty=false',str(Path(root)/'lima.yaml')]
 elif action=='stop-vm':args+=['stop',NAME]
 else:raise Blocked('Unsupported VM action.')
 return args,env

def main():
 parser=argparse.ArgumentParser(description='Read-only plan by default; no actual Mac installation is authorized by this package.')
 parser.add_argument('action',choices=('plan','preflight','configure','start-vm','stop-vm','start','uninstall'));parser.add_argument('--allow-changes',action='store_true',help='Use only after separate owner authorization on the actual Mac.')
 args=parser.parse_args()
 if args.action=='plan':print(json.dumps(inventory(),indent=2));return 0
 native_gate()
 if args.action=='preflight':print(json.dumps(inventory(),indent=2));return 2
 if not args.allow_changes:raise Blocked('Later explicit Mac authorization and --allow-changes required.')
 if args.action=='start':raise Blocked('ARM64 runtime, kernel enforcement and hardware acceptance remain unverified; assistant startup disabled.')
 root=Path.home()/'Library'/'Application Support'/'IGRIS'
 if args.action in ('configure','start-vm'):
  memory=int(subprocess.check_output(['/usr/sbin/sysctl','-n','hw.memsize'],text=True,timeout=5))
  if memory<8*1024**3 or int(platform.mac_ver()[0].split('.')[0])<13:raise Blocked('At least 8 GiB RAM and macOS 13 are required for this candidate VZ profile.')
  if shutil.disk_usage(root.parent).free<20*1024**3:raise Blocked('At least 20 GiB free required for preparation; estimates remain unverified.')
 if args.action=='configure':
  if shutil.disk_usage(root.parent).free<20*1024**3:raise Blocked('At least 20 GiB free recommended for bounded VM preparation.')
  print(json.dumps(install(root),indent=2));return 0
 if args.action=='uninstall':print(json.dumps(uninstall(root),indent=2));return 0
 command,environment=vm_command(root,args.action)
 return subprocess.run(command,env=environment,check=False).returncode
if __name__=='__main__':
 try:raise SystemExit(main())
 except Blocked as error:print('BLOCKED: '+str(error),file=sys.stderr);raise SystemExit(2)
