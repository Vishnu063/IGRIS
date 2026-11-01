"""Real broker/kernel/filesystem/SQLite tests. No inference claimed here."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from igris.guardian.approvals import ApprovalStore
from igris.guardian.executor import execute
from igris.guardian.policy import Denied, Permission, Policy
from igris.guardian.readonly import ToolScope
from igris.guardian.tools import GuardianTools


class GuardianToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root/'workspace';self.workspace.mkdir(mode=0o700)
        (self.workspace/'note.txt').write_text('Approved ordinary text')
        (self.workspace/'unlisted.txt').write_text('Not approved')
        (self.root/'outside.txt').write_text('Synthetic outside boundary marker')
        self.config = self.root/'tools.json'
        self.data = {'version':1,'workspace':str(self.workspace),'allowed_operations':['get_current_time','list_workspace_files','read_workspace_file'],
                     'directories':['.'],'files':['note.txt'],'approval_required':[]}
        self.save()
        self.tools = GuardianTools('owner',self.config,self.root/'guardian.db')
        self.policy = self.tools.policy

    def save(self):
        self.config.write_text(json.dumps(self.data));self.config.chmod(0o600)

    def send(self, operation, arguments=None, *, request=None, mission=None, approval=None, policy=None):
        return execute(policy or self.policy,self.workspace,
            {'request_id':request or uuid4().hex,'mission_id':mission or uuid4().hex,
             'proposal':json.dumps({'operation':operation,'arguments':arguments or {}}),'approval_id':approval},
            approval_store=self.tools.store.path,tool_config=self.config)

    def audit(self):
        with self.tools.store._db() as db: return db.execute('SELECT operation,event FROM tool_audit').fetchall()

    def test_three_real_tools_and_explicit_policy(self):
        self.assertIn('utc',self.send('get_current_time')['result'])
        self.assertEqual(self.send('list_workspace_files',{'path':'.'})['result'],{'files':['note.txt']})
        self.assertEqual(self.send('read_workspace_file',{'path':'note.txt'})['result']['text'],'Approved ordinary text')
        self.assertFalse(self.send('get_current_time',policy=Policy('owner'))['ok'])
        self.data['allowed_operations']=[];self.save()
        self.assertFalse(self.send('get_current_time')['ok'])
        self.assertIn(('get_current_time','denied'),self.audit())

    def test_malformed_unknown_injection_and_legacy_tools_denied(self):
        for operation,args in [('shell',{'command':'touch injected'}),('file.create',{'path':'artifacts/new.txt','text':'x'}),
            ('python.version',{}),('get_current_time',{'shell':'touch injected'}),('read_workspace_file',{'path':'note.txt','actor':'root'}),
            ('git.status',{}),('specialists.fixture',{}),('deployment.production',{})]:
            with self.subTest(operation=operation): self.assertFalse(self.send(operation,args)['ok'])
        self.assertFalse((self.workspace/'injected').exists())
        for raw in ('not json','{"operation":"get_current_time","operation":"shell","arguments":{}}',
                    '{"operation":"get_current_time","arguments":{},"approval_id":"forged"}',json.dumps({'operation':'get_current_time','arguments':[]})):
            self.assertFalse(self.tools.run(uuid4().hex,uuid4().hex,raw)['ok'])
        self.assertEqual(len(self.audit()),12)
        self.assertTrue(all(event=='denied' for _,event in self.audit()))

    def test_containment_traversal_unlisted_absolute_sensitive_and_directory(self):
        for path in ('../outside.txt',str(self.root/'outside.txt'),'.env','note.txt;touch injected','unlisted.txt','sub/../note.txt','a//b.txt'):
            self.assertFalse(self.send('read_workspace_file',{'path':path})['ok'])
        for path in ('..','/tmp','unlisted','.'):
            result=self.send('list_workspace_files',{'path':path})
            self.assertEqual(result['ok'],path=='.')
        for path in ('private.txt','api_key.txt','env.txt'):
            self.data['files']=[path];self.save()
            with self.assertRaises(Denied): ToolScope.load(self.config)

    def test_symlinks_hardlinks_fifo_large_binary_and_nonexistent(self):
        for kind in ('symlink','hardlink','fifo','large','binary','missing'):
            leaf=self.workspace/'allowed.txt'
            if leaf.exists() or leaf.is_symlink(): leaf.unlink()
            if kind=='symlink': leaf.symlink_to(self.root/'outside.txt')
            if kind=='hardlink': os.link(self.root/'outside.txt',leaf)
            if kind=='fifo': os.mkfifo(leaf)
            if kind=='large': leaf.write_text('x'*2049)
            if kind=='binary': leaf.write_bytes(b'\xff')
            self.data['files']=['allowed.txt'];self.save()
            result=self.send('read_workspace_file',{'path':'allowed.txt'})
            self.assertFalse(result['ok'],kind)
        (self.workspace/'nested').symlink_to(self.root,target_is_directory=True)
        self.data['directories']=['nested'];self.data['files']=['nested/outside.txt'];self.save()
        self.assertFalse(self.send('read_workspace_file',{'path':'nested/outside.txt'})['ok'])
        self.assertFalse(self.send('list_workspace_files',{'path':'nested'})['ok'])

    def test_approval_exact_action_scope_intent_single_use_and_forgery(self):
        self.data['approval_required']=['get_current_time'];self.save()
        action={'operation':'get_current_time','arguments':{}}
        request,mission=uuid4().hex,uuid4().hex
        binding={'request_id':request,'mission_id':mission,'scope_sha256':ToolScope.load(self.config).digest}
        pending=self.tools.store.request(self.policy,self.workspace,action,binding=binding)
        self.assertFalse(self.send('get_current_time',request=request,mission=mission)['ok'])
        self.assertFalse(self.send('get_current_time',request=request,mission=mission,approval='x'*32)['ok'])
        self.assertFalse(self.send('get_current_time',request=request,mission=mission,approval=pending['id'])['ok'])
        self.tools.store.decide(pending['id'],approve=True,reviewed_digest=pending['action_sha256'])
        self.assertFalse(self.send('get_current_time',request=uuid4().hex,mission=mission,approval=pending['id'])['ok'])
        # Same operation but changed schema/args never consumes the approval.
        self.assertFalse(self.send('get_current_time',{'zone':'UTC'},request=request,mission=mission,approval=pending['id'])['ok'])
        self.data['files']=[];self.save()
        self.assertFalse(self.send('get_current_time',request=request,mission=mission,approval=pending['id'])['ok'])
        self.data['files']=['note.txt'];self.save()
        self.assertTrue(self.send('get_current_time',request=request,mission=mission,approval=pending['id'])['ok'])
        self.assertFalse(self.send('get_current_time',request=request,mission=mission,approval=pending['id'])['ok'])
        with self.tools.store._db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE event='consumed'").fetchone()[0],1)

    def test_expired_denied_and_old_unbound_approval_do_not_execute(self):
        self.data['approval_required']=['get_current_time'];self.save()
        action={'operation':'get_current_time','arguments':{}}
        request,mission=uuid4().hex,uuid4().hex
        binding={'request_id':request,'mission_id':mission,'scope_sha256':ToolScope.load(self.config).digest}
        for kind in ('denied','expired','old'):
            store=self.tools.store
            if kind=='expired': store=ApprovalStore(store.path,clock=lambda:time.time()-10)
            pending=store.request(self.policy,self.workspace,action,binding=None if kind=='old' else binding,ttl_seconds=1 if kind=='expired' else 300)
            store.decide(pending['id'],approve=kind!='denied',reviewed_digest=pending['action_sha256'])
            self.assertFalse(self.send('get_current_time',request=request,mission=mission,approval=pending['id'])['ok'])

    def test_audit_no_raw_arguments_results_or_sensitive_values(self):
        fixture='password: synthetic-test-value'
        self.tools.run(uuid4().hex,uuid4().hex,json.dumps({'operation':'shell','arguments':{'command':fixture}}))
        (self.workspace/'note.txt').write_text(fixture)
        self.assertEqual(self.send('read_workspace_file',{'path':'note.txt'})['result']['text'],'[REDACTED]')
        with self.tools.store._db() as db: rows=db.execute('SELECT * FROM tool_audit').fetchall()
        self.assertNotIn('synthetic-test-value',json.dumps(rows))
        self.assertNotIn('note.txt',json.dumps(rows))
        self.assertNotIn('command',json.dumps(rows))
        self.assertIn(('unregistered','denied'),self.audit())

    def test_audit_failure_denies_before_execution_and_private_store(self):
        with self.tools.store._db() as db: db.execute('DROP TABLE tool_audit')
        self.assertFalse(self.send('get_current_time')['ok'])
        self.tools.store.enable_tool_audit()
        os.chmod(self.tools.store.path,0o644)
        self.assertFalse(self.send('get_current_time')['ok'])
        os.chmod(self.tools.store.path,0o600)
        link=self.root/'linked.json';link.symlink_to(self.config)
        with self.assertRaises(Denied): ToolScope.load(link)

    def test_real_timeout_kills_worker_and_audits(self):
        with patch('igris.guardian.executor.WALL_TIMEOUT',.0001):
            result=self.send('get_current_time')
        self.assertFalse(result['ok']);self.assertIn('timeout',result['reason'].lower())
        self.assertIn(('unregistered','timeout'),self.audit())
        self.assertTrue(self.send('get_current_time')['ok'])

    def test_kernel_restrictions_really_deny_network_and_child_processes(self):
        # Real isolated test process: no patched sockets, Popen, seccomp or permissions.
        code='''import socket,subprocess,sys,errno,ctypes
from igris.guardian.kernel import restrict_readonly_process
restrict_readonly_process()
for action in (lambda:socket.socket(),lambda:subprocess.run([sys.executable,'--version'])):
 try: action()
 except OSError as exc:
  assert exc.errno==errno.EPERM,exc
 else: raise AssertionError('Kernel boundary bypassed')
libc=ctypes.CDLL(None,use_errno=True)
for number in (425,426,427):
 assert libc.syscall(number,0,0,0,0,0,0)==-1
 assert ctypes.get_errno()==errno.EPERM
print('network and child process creation denied')'''
        result=subprocess.run([sys.executable,'-c',code],env={'PYTHONPATH':str(ROOT/'src')},text=True,capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('denied',result.stdout)

    def test_listing_excludes_unsafe_and_unapproved_entries(self):
        (self.workspace/'link.txt').symlink_to(self.root/'outside.txt')
        (self.workspace/'big.txt').write_text('x'*2049)
        os.link(self.root/'outside.txt',self.workspace/'hard.txt')
        self.data['files']=['note.txt','link.txt','big.txt','hard.txt'];self.save()
        self.assertEqual(self.send('list_workspace_files',{'path':'.'})['result']['files'],['note.txt'])

    def test_valid_changed_read_arguments_and_actor_do_not_match_approval(self):
        (self.workspace/'second.txt').write_text('Another allowed document')
        self.data['files'].append('second.txt');self.data['approval_required']=['read_workspace_file'];self.save()
        request,mission=uuid4().hex,uuid4().hex
        binding={'request_id':request,'mission_id':mission,'scope_sha256':ToolScope.load(self.config).digest}
        action={'operation':'read_workspace_file','arguments':{'path':'note.txt'}}
        record=self.tools.store.request(self.policy,self.workspace,action,binding=binding)
        self.tools.store.decide(record['id'],approve=True,reviewed_digest=record['action_sha256'])
        self.assertFalse(self.send('read_workspace_file',{'path':'second.txt'},request=request,mission=mission,approval=record['id'])['ok'])
        self.assertFalse(self.send('read_workspace_file',{'path':'note.txt'},request=request,mission=mission,approval=record['id'],
            policy=Policy('other',frozenset({Permission.READ})))['ok'])
        self.assertTrue(self.send('read_workspace_file',{'path':'note.txt'},request=request,mission=mission,approval=record['id'])['ok'])

    def test_outer_schema_types_fail_closed_and_output_controls_removed(self):
        for value in ([],None,'shell',123):
            result=execute(self.policy,self.workspace,value,approval_store=self.tools.store.path,tool_config=self.config)
            self.assertFalse(result['ok'])
        (self.workspace/'note.txt').write_text('Hello\x1b\x9b world')
        self.assertEqual(self.send('read_workspace_file',{'path':'note.txt'})['result']['text'],'Hello world')

    def test_interruption_reaps_real_child_and_audits(self):
        original=subprocess.Popen.communicate
        interrupted=[]
        def interrupt_once(process,*args,**kwargs):
            if not interrupted:
                interrupted.append(process.pid)
                raise KeyboardInterrupt()
            return original(process,*args,**kwargs)
        # Only inject the interrupt; the broker, process, kill and audit are real.
        with patch.object(subprocess.Popen,'communicate',interrupt_once):
            with self.assertRaises(KeyboardInterrupt): self.send('get_current_time')
        with self.assertRaises(ProcessLookupError): os.kill(interrupted[0],0)
        self.assertIn(('unregistered','interrupted'),self.audit())
        self.assertTrue(self.send('get_current_time')['ok'])

    def test_registered_profiles_cannot_widen_readonly_broker(self):
        for operation,arguments in [('n8n.calculate',{'left':7,'right':5}),('ops.monitor',{'container_id':'a'*64}),('specialists.reason',{'role':'frontend'}),('memory.search',{'query':'secret'}),('memory.manage',{'kind':'save'})]:
            result=self.send(operation,arguments)
            self.assertFalse(result['ok'])
        self.assertIn(('unregistered','denied'),self.audit())
