"""Explicit, native Linux ARM64 preparation, never native Mac or emulation.

Downloads only pinned public assets; installs only the reviewed hash lock into
the checkout's private runtime. Does not start an assistant or clear any approval.
"""
import argparse,hashlib,json,os,platform,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.adapters.native_runtime import arm_profile,digest,elf_machine
from igris.memory import private_file
from fetch_hermes_probe_assets import fetch
from verify_guardian_kernel import verify

def unpack(archive,target):
    if target.exists():raise RuntimeError('Existing asset tree preserved; review before replacing.')
    target.mkdir(mode=0o700)
    with tarfile.open(archive) as source:
        if sum(item.size for item in source.getmembers())>1024**3:raise RuntimeError('Archive expansion limit.')
        source.extractall(target,filter='data')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--allow-downloads',action='store_true',required=True);args=parser.parse_args()
    if platform.system()!='Linux' or platform.machine()!='aarch64':raise RuntimeError('Actual native ARM64 Linux guest required; no cross-architecture preparation execution.')
    from igris.adapters.native_runtime import require_daemon_limits
    require_daemon_limits() # No model download when enforcement is unavailable.
    runtime=ROOT/'runtime';runtime.mkdir(mode=0o700,exist_ok=True)
    if runtime.resolve()!=runtime or (runtime/'arm64').exists():raise RuntimeError('Existing preparation preserved; verify/review it instead of overwriting.')
    proof=verify() # Actual target headers and irreversible syscall tests FIRST.
    folder=runtime/'arm64';folder.mkdir(mode=0o700)
    profile=arm_profile(ROOT);pins=json.loads((ROOT/'packaging/macos/assets.json').read_text())
    py=pins['python']['linux-arm64'];engine=next(p for p in pins['engine'] if p['name'].endswith('ubuntu-arm64.tar.gz'))
    python=fetch(runtime,'cpython3149.tar.gz',py['url'],py['sha256'],100*1024**2)
    llama=fetch(runtime,'llama-b11960.tar.gz',engine['url'],engine['sha256'],32*1024**2)
    fetch(runtime,profile['model_file'],'https://huggingface.co/'+profile['model_repository']+'/resolve/'+profile['model_revision']+'/'+profile['model_file'],profile['model_sha256'],profile['model_bytes'])
    unpack(python,runtime/'python3149');unpack(llama,runtime/'llama-b11960')
    executable=runtime/'python3149/python/bin/python3.14';elf_machine(executable,183)
    elf_machine(runtime/'llama-b11960/llama-b11960/llama-server',183)
    subprocess.run([str(executable),'-m','venv',str(runtime/'hermes-venv')],check=True,timeout=60)
    vpython=runtime/'hermes-venv/bin/python'
    subprocess.run([str(vpython),'-m','pip','install','--require-hashes','--only-binary=:all:','--disable-pip-version-check','-r',str(ROOT/'integrations/hermes-inference/requirements.lock.txt')],check=True,timeout=600)
    subprocess.run([str(vpython),'-m','pip','check'],check=True,timeout=30)
    from igris.isolated import docker_command,docker_environment
    base=docker_command();env=docker_environment()
    arch=subprocess.check_output(base+['info','--format','{{.Architecture}}'],env=env,text=True,timeout=10).strip()
    if arch not in ('aarch64','arm64'):raise RuntimeError('Native ARM64 daemon required; remote x86 daemon denied.')
    recipe=ROOT/'integrations/hermes-inference/Dockerfile.arm64'
    subprocess.run(base+['build','--platform=linux/arm64','--label','com.igris.recipe='+digest(recipe),'--iidfile',str(folder/'image-id'),'-f',str(recipe),str(ROOT/'integrations/hermes-inference')],env=env,check=True,timeout=600)
    profile['container_image']=(folder/'image-id').read_text().strip()
    for name,data in [('kernel-proof.json',proof),('profile.json',profile)]:
        path=private_file(folder/name,create=True);path.write_text(json.dumps(data,indent=2)+'\n')
    print('PREPARED, not accepted: run scripts/verify_native_guest.py. Assistant startup remains gated.')
if __name__=='__main__':main()
