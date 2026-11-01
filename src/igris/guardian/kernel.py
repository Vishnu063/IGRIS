"""Linux x86_64 defense in depth for the existing read-only broker, not a sandbox."""
import ctypes
import errno
import platform
from .policy import Denied


def restrict_readonly_process():
    """Irreversibly prohibit network and new executable/child processes in this worker."""
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise Denied('Verified kernel restrictions unavailable.')
    class Filter(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte), ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]
    class Program(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ushort), ('filters', ctypes.POINTER(Filter))]
    # Architecture check; refuse x32 and networking/process creation syscalls.
    instructions = [(0x20,0,0,4), (0x15,1,0,0xc000003e), (0x06,0,0,0x80000000),
                    (0x20,0,0,0), (0x35,0,1,0x40000000), (0x06,0,0,0x50000|errno.EPERM)]
    # io_uring can perform socket operations without the corresponding socket
    # syscalls; disable its setup/enter/register path as well.
    denied = (41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,288,299,307,322,425,426,427,435)
    for number in denied:
        instructions.extend(((0x15,0,1,number), (0x06,0,0,0x50000|errno.EPERM)))
    instructions.append((0x06,0,0,0x7fff0000))
    filters = (Filter*len(instructions))(*(Filter(*item) for item in instructions))
    program = Program(len(instructions), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise Denied('Kernel restrictions could not be applied.')
