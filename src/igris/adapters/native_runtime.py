"""Trusted native ARM64 profile selection; no model-supplied runtime parameters."""
import hashlib,json,platform,re,struct,subprocess
from pathlib import Path
from .contracts import AdapterUnavailable,ContractError
from ..memory import private_file

def validate_daemon_limits(info):
    required=('MemoryLimit','SwapLimit','CpuCfsPeriod','CpuCfsQuota','PidsLimit')
    if type(info) is not dict or any(info.get(key) is not True for key in required) or info.get('CgroupVersion')!='2' or info.get('CgroupDriver') not in ('systemd','cgroupfs'):
        raise AdapterUnavailable('CPU, memory, swap and PID cgroup v2 enforcement unavailable; runtime activation blocked.')
    return {key:info[key] for key in required}

def require_daemon_limits():
    from ..isolated import docker_command,docker_environment
    raw=subprocess.check_output(docker_command()+['info','--format','{{json .}}'],env=docker_environment(),text=True,timeout=10)
    return validate_daemon_limits(json.loads(raw))

def verify_worker_limits(directory='/sys/fs/cgroup'):
    root=Path(directory)
    try:
        values={name:(root/name).read_text().strip() for name in ('memory.max','memory.swap.max','pids.max','cpu.max')}
        memory=int(values['memory.max']);swap=int(values['memory.swap.max']);pids=int(values['pids.max'])
        quota,period=map(int,values['cpu.max'].split())
        if not (0<memory<=3*1024**3 and swap==0 and 0<pids<=128 and 0<quota<=2*period and period>0):raise ValueError()
    except (OSError,ValueError):raise AdapterUnavailable('Actual worker cgroup limits absent or exceed the reviewed profile.') from None
    return values

def digest(path):
    with Path(path).open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()

def elf_machine(path,expected):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ContractError('Native runtime executable required.')
    with path.open('rb') as source:header=source.read(20)
    if len(header)!=20 or header[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',header,18)[0]!=expected:
        raise ContractError('Native 64-bit little-endian ELF architecture mismatch; no emulation.')

def profile_path(root):
    root=Path(root)
    if platform.system()=='Linux' and platform.machine()=='aarch64':return root/'runtime/arm64/profile.json'
    rebuilt=root/'runtime/native-x86/profile.json'
    return rebuilt if rebuilt.exists() or rebuilt.is_symlink() else root/'integrations/hermes-inference/profile.json'

def arm_profile(root):
    root=Path(root);base=json.loads((root/'integrations/hermes-inference/profile.json').read_text())
    pins=json.loads((root/'packaging/macos/assets.json').read_text())
    engine=next(item for item in pins['engine'] if item['name'].endswith('ubuntu-arm64.tar.gz'))
    base.update(platform='linux-aarch64',scope='native ARM64 isolated guest reasoning; no native agent tools',
        python_archive_sha256=pins['python']['linux-arm64']['sha256'],engine_archive_sha256=engine['sha256'],container_image=None)
    return base

def validate_native_profile(root,profile,machine):
    if machine not in ('aarch64','x86_64'):raise AdapterUnavailable('Reviewed native architecture required.')
    root=Path(root);expected=arm_profile(root) if machine=='aarch64' else json.loads((root/'integrations/hermes-inference/profile.json').read_text())
    expected['container_image']=None
    actual=dict(profile);image=actual.get('container_image');actual['container_image']=None
    if actual!=expected or not re.fullmatch('sha256:[a-f0-9]{64}',image or ''):raise ContractError('Exact reviewed ARM64 runtime profile required.')
    folder=root/('runtime/arm64' if machine=='aarch64' else 'runtime/native-x86')
    private_file(folder/'profile.json')
    proof=json.loads(private_file(folder/'kernel-proof.json').read_text())
    from ..guardian.kernel import SYSCALLS,AUDIT_ARCH
    if (proof.get('status')!='PASS' or proof.get('native_architecture')!=machine
        or proof.get('boot_id')!=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        or proof.get('kernel_release')!=platform.release()
        or proof.get('source_sha256')!=digest(root/'src/igris/guardian/kernel.py')
        or proof.get('headers')!=dict(SYSCALLS[machine],audit_arch=AUDIT_ARCH[machine])
        or proof.get('actual_denied_syscalls')!=sorted(SYSCALLS[machine])):
        raise AdapterUnavailable('Current native guest header/kernel proof required; run verify_guardian_kernel.py.')
    elf_machine(root/'runtime/python3149/python/bin/python3.14',183 if machine=='aarch64' else 62)
    elf_machine(root/'runtime/llama-b11960/llama-b11960/llama-server',183 if machine=='aarch64' else 62)
    # Verify actual installed image metadata, not merely a claimed image tag.
    from ..isolated import docker_command,docker_environment
    result=subprocess.run(docker_command()+['image','inspect',image],env=docker_environment(),capture_output=True,text=True,check=True,timeout=10)
    rows=json.loads(result.stdout)
    if len(rows)!=1 or rows[0].get('Architecture')!=('arm64' if machine=='aarch64' else 'amd64') or rows[0].get('Os')!='linux' or rows[0].get('Id')!=image:
        raise ContractError('Native installed ARM64 Linux image required.')
    label=rows[0].get('Config',{}).get('Labels',{})
    if label.get('com.igris.recipe')!=digest(root/('integrations/hermes-inference/Dockerfile.arm64' if machine=='aarch64' else 'integrations/hermes-inference/Dockerfile')):
        raise ContractError('Reviewed ARM64 image recipe required.')
