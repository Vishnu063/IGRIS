"""Native selection/ELF and exact-profile denials; no emulated ARM execution."""
import json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from igris.adapters.native_runtime import profile_path,elf_machine,arm_profile,validate_native_profile,validate_daemon_limits,verify_worker_limits
from igris.adapters.contracts import ContractError,AdapterUnavailable
class NativeRuntimeTests(unittest.TestCase):
    def test_missing_or_disabled_daemon_limits_fail_closed(self):
        data=dict.fromkeys(('MemoryLimit','SwapLimit','CpuCfsPeriod','CpuCfsQuota','PidsLimit'),True);data.update(CgroupVersion='2',CgroupDriver='systemd')
        validate_daemon_limits(data)
        for field in data:
            bad=dict(data);bad[field]=False
            with self.assertRaises(AdapterUnavailable):validate_daemon_limits(bad)
    def test_actual_worker_files_require_real_bounds_and_no_swap(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);values={'memory.max':str(3*1024**3),'memory.swap.max':'0','pids.max':'128','cpu.max':'200000 100000'}
            for name,value in values.items():(root/name).write_text(value)
            verify_worker_limits(root)
            for name,value in [('memory.max','max'),('memory.max',str(4*1024**3)),('memory.swap.max','1'),('pids.max','max'),('cpu.max','max 100000'),('cpu.max','300000 100000')]:
                (root/name).write_text(value)
                with self.assertRaises(AdapterUnavailable):verify_worker_limits(root)
                (root/name).write_text(values[name])
    def test_arm_cannot_fall_back_to_legacy_x86_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch('igris.adapters.native_runtime.platform.system',return_value='Linux'),patch('igris.adapters.native_runtime.platform.machine',return_value='aarch64'):
                self.assertEqual(profile_path(root),root/'runtime/arm64/profile.json')
    def test_elf_architecture_and_symlink_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'worker';header=bytearray(20);header[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',header,18,183);path.write_bytes(header)
            elf_machine(path,183)
            with self.assertRaises(ContractError):elf_machine(path,62)
            link=Path(folder)/'link';link.symlink_to(path)
            with self.assertRaises(ContractError):elf_machine(link,183)
    def test_altered_arm_tools_model_and_context_do_not_authorize_preflight(self):
        profile=arm_profile(ROOT);profile['container_image']='sha256:'+'a'*64
        for field,value in [('enabled_tools',['shell']),('authorized_spend_inr',1),('served_context_tokens',4096),('model_sha256','b'*64)]:
            with self.assertRaises(ContractError):validate_native_profile(ROOT,dict(profile,**{field:value}),'aarch64')
