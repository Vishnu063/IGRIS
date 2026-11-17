"""Trusted native ARM64 profile selection; no model-supplied runtime parameters."""
import hashlib,json,platform,re,struct
from pathlib import Path
from .contracts import AdapterUnavailable,ContractError
from ..memory import private_file

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
    import subprocess
    result=subprocess.run(docker_command()+['image','inspect',image],env=docker_environment(),capture_output=True,text=True,check=True,timeout=10)
    rows=json.loads(result.stdout)
    if len(rows)!=1 or rows[0].get('Architecture')!=('arm64' if machine=='aarch64' else 'amd64') or rows[0].get('Os')!='linux' or rows[0].get('Id')!=image:
        raise ContractError('Native installed ARM64 Linux image required.')
    label=rows[0].get('Config',{}).get('Labels',{})
    if label.get('com.igris.recipe')!=digest(root/('integrations/hermes-inference/Dockerfile.arm64' if machine=='aarch64' else 'integrations/hermes-inference/Dockerfile')):
        raise ContractError('Reviewed ARM64 image recipe required.')
