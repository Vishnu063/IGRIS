"""Compare native target headers and probe every restricted syscall in a child.

No emulation or architecture override. The probe never relaxes the parent and
does not grant approvals. Successful output is boot/source-bound evidence only.
"""
import argparse,hashlib,json,os,platform,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.guardian.kernel import SYSCALLS,AUDIT_ARCH

def verify():
    machine=platform.machine()
    if platform.system()!='Linux' or machine not in SYSCALLS:raise RuntimeError('Native supported Linux guest required; no emulation fallback.')
    calls=SYSCALLS[machine]
    # Compiler sees the actual installed target headers, never model input.
    program='#include <sys/syscall.h>\n#include <linux/audit.h>\n#include <stdio.h>\nint main(void){\n'
    for name in calls:program+='printf("'+name+'=%ld\\n", (long)__NR_'+name+');\n'
    program+='printf("audit_arch=%lu\\n", (unsigned long)AUDIT_ARCH_'+('X86_64' if machine=='x86_64' else 'AARCH64')+');\nreturn 0;}\n'
    with tempfile.TemporaryDirectory(prefix='igris-headers-') as folder:
        source=Path(folder)/'check.c';binary=Path(folder)/'check';source.write_text(program)
        subprocess.run(['cc','-Wall','-Werror',str(source),'-o',str(binary)],check=True,capture_output=True,timeout=30)
        output=subprocess.check_output([str(binary)],text=True,timeout=5)
    observed={key:int(value) for key,value in (row.split('=') for row in output.splitlines())}
    if observed!=dict(calls,audit_arch=AUDIT_ARCH[machine]):raise RuntimeError('Guest UAPI syscall constants differ; activation denied.')
    child='''import ctypes,errno,json,os,sys
sys.path.insert(0,sys.argv[1])
from igris.guardian.kernel import restrict_readonly_process,SYSCALLS
import platform
calls=SYSCALLS[platform.machine()]
libc=ctypes.CDLL(None,use_errno=True)
libc.syscall.restype=ctypes.c_long
restrict_readonly_process()
for name,number in calls.items():
 ctypes.set_errno(0)
 value=libc.syscall(number,0,0,0,0,0,0)
 if value!=-1 or ctypes.get_errno()!=errno.EPERM:os._exit(23)
print(json.dumps({'denied':sorted(calls),'no_new_privileges':True}),flush=True)
'''
    result=subprocess.run([sys.executable,'-I','-c',child,str(ROOT/'src')],capture_output=True,text=True,check=True,timeout=10)
    proof=json.loads(result.stdout)
    if proof['denied']!=sorted(calls):raise RuntimeError('Incomplete restriction evidence.')
    return dict(status='PASS',native_architecture=machine,kernel_release=platform.release(),
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),headers=observed,
        source_sha256=hashlib.sha256((ROOT/'src/igris/guardian/kernel.py').read_bytes()).hexdigest(),
        actual_denied_syscalls=proof['denied'],emulated=False,full_sandbox=False)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=verify()
    if args.output:
        sys.path.insert(0,str(ROOT/'src'));from igris.memory import private_file
        path=private_file(args.output,create=True);path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
