"""Explicit native ARM64 guest acceptance and fail-closed startup receipt.

Run on the actual guest after preparation. --cloud-x86 is a separately labelled
Linux regression campaign and can NEVER satisfy the ARM64 startup gate.
"""
import argparse,hashlib,json,os,platform,subprocess,sys,threading,time
from datetime import datetime,timezone
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.adapters.native_runtime import digest
from igris.memory import private_file
from verify_guardian_kernel import verify as kernel_verify

def source_digest():
    sha=hashlib.sha256()
    files=[p for pattern in ('src/**/*.py','src/igris/web/*','scripts/*.py','packaging/macos/*','integrations/hermes-inference/*') for p in ROOT.glob(pattern) if p.is_file()]
    for path in sorted(set(files)):
        if path.is_symlink():raise RuntimeError('Symlinked source denied.')
        sha.update(str(path.relative_to(ROOT)).encode()+b'\0'+path.read_bytes())
    return sha.hexdigest()

def kernel_receipt():
    proof=kernel_verify();folder=ROOT/('runtime/arm64' if platform.machine()=='aarch64' else 'runtime/native-x86');path=folder/'kernel-proof.json'
    private_file(path).write_text(json.dumps(proof,indent=2)+'\n');return proof

def reject_host_shares():
    result=subprocess.run(['findmnt','-rn','-t','9p,virtiofs'],capture_output=True,text=True,timeout=5)
    if result.returncode not in (0,1) or result.stdout.strip():raise RuntimeError('Absent host filesystem sharing must be verified; activation denied.')

def current_check(receipt):
    if receipt.get('status')!='PASS' or receipt.get('architecture')!='aarch64' or receipt.get('source_digest')!=source_digest():raise RuntimeError('Current complete native ARM64 acceptance receipt required.')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise RuntimeError('Guest source changes require review/reverification.')
    if receipt.get('tested_commit')!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip():raise RuntimeError('Exact tested commit required; update remains blocked until verified.')
    reject_host_shares();proof=kernel_receipt()
    if proof['kernel_release']!=receipt['kernel']['kernel_release']:raise RuntimeError('Changed guest kernel requires full verification.')
    from igris.adapters.hermes_chat import DockerHermesAdapter
    adapter=DockerHermesAdapter();adapter._preflight()
    from igris.owned_jobs import assert_no_pending_launches
    assert_no_pending_launches(ROOT/'runtime')
    from igris.isolated import docker_command,docker_environment
    remaining=subprocess.check_output(docker_command()+['ps','--all','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],env=docker_environment(),text=True,timeout=10)
    if remaining.strip():raise RuntimeError('An unfinished owned model worker requires cleanup review.')
    if adapter.profile['container_image']!=receipt['image']:raise RuntimeError('Runtime image changed; reverify.')
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');parser.add_argument('--cloud-x86',action='store_true');args=parser.parse_args()
    machine=platform.machine()
    if platform.system()!='Linux' or machine not in ('aarch64','x86_64') or machine=='x86_64' and (not args.cloud_x86 or args.check):raise SystemExit('BLOCKED: native ARM64 guest required. Cloud x86 cannot satisfy Mac startup.')
    folder=ROOT/('runtime/arm64' if machine=='aarch64' else 'runtime/native-x86');receipt_path=folder/'acceptance.json'
    if args.check:
        current_check(json.loads(private_file(receipt_path).read_text()));print('PASS: current native ARM64 prerequisites and acceptance receipt.');return
    if receipt_path.exists():
        private_file(receipt_path);receipt_path.rename(folder/('acceptance-previous-'+uuid4().hex+'.json'))
    if machine=='aarch64':reject_host_shares()
    proof=kernel_receipt()
    from igris.adapters.hermes_chat import DockerHermesAdapter
    adapter=DockerHermesAdapter();adapter._preflight()
    target=ROOT/'runtime/mac-readiness';target.mkdir(mode=0o700,exist_ok=True)
    samples=[];done=threading.Event()
    def sample():
        while not done.is_set():
            values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.split(':')[0] in ('MemTotal','MemAvailable','SwapTotal','SwapFree')};samples.append(values);done.wait(.5)
    monitor=threading.Thread(target=sample,daemon=True);monitor.start();checks=[]
    try:
        for name,command,timeout in [('regression',[sys.executable,'-m','unittest','discover','-s','tests','-q'],180),('guardian_scan',[sys.executable,'-m','igris.guardian.scan'],180),('chat',[sys.executable,'scripts/test_chat_live.py'],1800),('tools',[sys.executable,'scripts/test_guardian_tools_live.py'],1800),('backup',[sys.executable,'scripts/test_chat_backup_live.py'],900),('dashboard',[sys.executable,'scripts/verify_dashboard_http.py'],600)]:
            started=time.monotonic();env=dict(os.environ,PYTHONPATH=str(ROOT/'src'))
            with (target/(name+'-acceptance.txt')).open('wb') as log:result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            checks.append({'check':name,'command':'$ '+' '.join(command),'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-started})
            print(name+': '+('PASS' if result.returncode==0 else 'FAIL'),flush=True)
            if result.returncode:raise RuntimeError('Acceptance failed: '+name+'; retained private log. No startup receipt granted.')
    finally:done.set();monitor.join(2)
    result={'status':'PASS','architecture':machine,'guest_only':True,'mac_host_acceptance':'BLOCKED: requires actual host measurements and human voice acceptance','tested_at_utc':datetime.now(timezone.utc).isoformat(),'tested_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'working_tree_clean':not bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),'source_digest':source_digest(),'kernel':proof,'image':adapter.profile['container_image'],'checks':checks,'peak_guest_estimated_used_bytes':max(row['MemTotal']-row['MemAvailable'] for row in samples),'peak_guest_swap_used_bytes':max(row['SwapTotal']-row['SwapFree'] for row in samples),'memory_method':'Guest /proc/meminfo sampled every 0.5 seconds; not host VM RSS, unique physical RAM or Mac swap.','voice_human_acceptance':False}
    path=private_file(receipt_path,create=not receipt_path.exists());path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
