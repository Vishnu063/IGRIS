"""Native Linux ABI restrictions for the existing broker, not a complete sandbox.

Numbers reviewed against Linux v6.17 UAPI. Actual guest headers and irreversible
execution probes must also pass before ARM64 runtime activation.
"""
import ctypes
import errno
import platform
from .policy import Denied
from types import MappingProxyType

NETWORK = ('socket','connect','accept','sendto','recvfrom','sendmsg','recvmsg',
           'shutdown','bind','listen','getsockname','getpeername','socketpair',
           'setsockopt','getsockopt','accept4','recvmmsg','sendmmsg')
COMMON = {'io_uring_setup':425,'io_uring_enter':426,'io_uring_register':427,'clone3':435}
SYSCALLS = MappingProxyType({
    'x86_64': MappingProxyType(dict(zip(NETWORK,(41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,288,299,307)),
        clone=56,fork=57,vfork=58,execve=59,execveat=322,**COMMON)),
    'aarch64': MappingProxyType(dict(zip(NETWORK,(198,203,202,206,207,211,212,210,200,201,204,205,199,208,209,242,243,269)),
        clone=220,execve=221,execveat=281,**COMMON)),
})
AUDIT_ARCH = MappingProxyType({'x86_64':0xc000003e,'aarch64':0xc00000b7})


def instructions_for(machine):
    if machine not in SYSCALLS:raise Denied('Unsupported native Linux syscall ABI.')
    # Kill on ABI mismatch. x32/high-bit syscall numbers always fail closed.
    instructions = [(0x20,0,0,4), (0x15,1,0,AUDIT_ARCH[machine]), (0x06,0,0,0x80000000),
                    (0x20,0,0,0), (0x35,0,1,0x40000000), (0x06,0,0,0x50000|errno.EPERM)]
    for number in sorted(set(SYSCALLS[machine].values())):
        instructions.extend(((0x15,0,1,number), (0x06,0,0,0x50000|errno.EPERM)))
    instructions.append((0x06,0,0,0x7fff0000))
    return tuple(instructions)


def restrict_readonly_process():
    """Irreversibly prohibit network and new executable/child processes in this worker."""
    if platform.system() != 'Linux' or platform.machine() not in SYSCALLS:
        raise Denied('Verified kernel restrictions unavailable.')
    class Filter(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte), ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]
    class Program(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ushort), ('filters', ctypes.POINTER(Filter))]
    instructions = instructions_for(platform.machine())
    filters = (Filter*len(instructions))(*(Filter(*item) for item in instructions))
    program = Program(len(instructions), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise Denied('Kernel restrictions could not be applied.')
