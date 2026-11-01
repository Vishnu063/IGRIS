"""Explicit optional cloud preparation from hash-locked wheels/model files."""
import argparse,hashlib,json,os,platform,shutil,subprocess,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.integrations.mem0_runtime import Mem0Index,PACKAGES,package_digest
import threading

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
 if not args.prepare:print('Disabled by default. No installation or download; use --prepare explicitly on cloud Linux x86_64.');return
 if platform.system()!='Linux' or platform.machine()!='x86_64':raise ValueError('This lock is Linux x86_64 only. No Mac/ARM installation or x86 fallback.')
 runtime=ROOT/'runtime/mem0';runtime.mkdir(mode=0o700,exist_ok=True);venv=runtime/'venv'
 if not (venv/'bin/python').exists():
  if shutil.disk_usage(ROOT).free<768*1024**2:raise ValueError('At least 768MiB free required; preserve verified runtime/user data.')
  subprocess.run([str(ROOT/'runtime/python3149/python/bin/python3.14'),'-m','venv','--without-pip',str(venv)],check=True,timeout=30)
 profile=json.loads((ROOT/'integrations/mem0/profile.json').read_text())
 if (PACKAGES/'mem0').exists():
  if package_digest(PACKAGES)!=profile['packages_sha256']:raise ValueError('Existing optional packages differ; preserved, not overwritten or re-pinned.')
 else:
  if shutil.disk_usage(ROOT).free<768*1024**2:raise ValueError('Insufficient free space for optional dependencies/model.')
  # Wheels only, no build hooks, no dependencies outside the complete hash lock.
  subprocess.run([sys.executable,'-m','pip','--isolated','--python',str(venv/'bin/python'),'install','--no-input','--no-compile','--no-cache-dir','--no-deps','--require-hashes','--only-binary=:all:','--index-url','https://pypi.org/simple','-r',str(ROOT/'integrations/mem0/requirements-linux-x86_64.lock')],check=True,timeout=300)
  if package_digest(PACKAGES)!=profile['packages_sha256']:raise ValueError('Installed package fingerprint differs; no automatic activation.')
 spec=json.loads((ROOT/'integrations/mem0/model.json').read_text());model=runtime/'model';model.mkdir(mode=0o700,exist_ok=True)
 for item in spec['files']:
  target=model/item['file']
  if target.exists():
   if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=item['sha256']:raise ValueError('Existing model asset differs; preserved.')
   continue
  if shutil.disk_usage(ROOT).free<item['bytes']+256*1024**2:raise ValueError('Model download would exhaust storage reserve.')
  url='https://huggingface.co/'+spec['repository']+'/resolve/'+spec['revision']+'/'+item['file'];temporary=target.with_suffix(target.suffix+'.download')
  if temporary.exists():raise ValueError('Unfinished task-owned download needs review.')
  try:
   size=0;digest=hashlib.sha256()
   with urllib.request.urlopen(url,timeout=60) as response,temporary.open('xb') as output:
    while chunk:=response.read(1024*1024):
     size+=len(chunk)
     if size>item['bytes']:raise ValueError('Model asset exceeds pinned size.')
     output.write(chunk);digest.update(chunk)
   if size!=item['bytes'] or digest.hexdigest()!=item['sha256']:raise ValueError('Pinned model hash/length mismatch.')
   temporary.chmod(0o400);temporary.replace(target)
  finally:temporary.unlink(missing_ok=True)
 Mem0Index(enabled=True).preflight(threading.Event())
 print('PASS: pinned optional Mem0 packages/model verified. No server, inference, paid provider or microphone started.')
if __name__=='__main__':main()
