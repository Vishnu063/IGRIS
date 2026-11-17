"""ABI/BPF validation; ARM instructions simulated, native kernel probe is real."""
import errno,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.guardian.kernel import AUDIT_ARCH,SYSCALLS,instructions_for,restrict_readonly_process
from igris.guardian.policy import Denied

def evaluate(program,arch,number):
    pc=0;acc=0
    while True:
        code,jt,jf,k=program[pc]
        if code==0x20:acc={4:arch,0:number}[k];pc+=1
        elif code==0x15:pc+=1+(jt if acc==k else jf)
        elif code==0x35:pc+=1+(jt if acc>=k else jf)
        elif code==0x06:return k
        else:raise AssertionError('Unexpected BPF instruction')

class KernelProfileTests(unittest.TestCase):
    def test_every_blocked_syscall_and_architecture_mismatch(self):
        for arch,calls in SYSCALLS.items():
            program=instructions_for(arch)
            for number in calls.values():self.assertEqual(evaluate(program,AUDIT_ARCH[arch],number),0x50000|errno.EPERM)
            self.assertEqual(evaluate(program,AUDIT_ARCH[arch],0x40000000),0x50000|errno.EPERM)
            self.assertEqual(evaluate(program,0,0),0x80000000)
            self.assertEqual(evaluate(program,AUDIT_ARCH[arch],1),0x7fff0000)
    def test_native_platform_gate_keeps_unsupported_systems_denied(self):
        for system,arch in [('Darwin','arm64'),('Linux','armv7l'),('Linux','i686')]:
            with patch('igris.guardian.kernel.platform.system',return_value=system),patch('igris.guardian.kernel.platform.machine',return_value=arch):
                with self.assertRaises(Denied):restrict_readonly_process()
    def test_reference_arm_numbers_are_not_x86_aliases(self):
        self.assertEqual(SYSCALLS['aarch64']['socket'],198)
        self.assertEqual(SYSCALLS['aarch64']['execveat'],281)
        self.assertEqual(AUDIT_ARCH['aarch64'],0xc00000b7)
        with self.assertRaises(Denied):instructions_for('arm64-emulated')
