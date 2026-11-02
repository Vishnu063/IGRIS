"""Real SQLite/Guardian leases; fixed local time handler is a fixture, not n8n."""
import json,sys,tempfile,threading,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.guardian.activities import OwnerActions,ExecutionProfile,ExecutionPermit
from igris.guardian.approvals import ApprovalStore
from igris.guardian.policy import Policy,Permission,Denied
from igris.adapters.contracts import ContractError
from igris.isolated import Cancelled

class OwnerActionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.now=[time.time()];self.mono=[0.0];self.scopefile=self.root/'scope';self.scopefile.write_text('reviewed')
        self.store=ApprovalStore(self.root/'guardian.sqlite3',initialize=True,clock=lambda:self.now[0])
        self.policy=Policy('owner',frozenset({Permission.READ}));self.count=0
        def normalize(raw):
            if raw!={}:raise ContractError('No arguments accepted.')
            return {}
        def scope(cancel):return {'version':self.scopefile.read_text()}
        def execute(raw,cancel,permit):
            permit.consume('get_current_time',raw)
            with self.assertRaises(Denied):permit.consume('get_current_time',raw)
            self.count+=1;return {'epoch':time.time()}
        self.profile=ExecutionProfile('get_current_time',normalize,scope,execute)
        self.actions=OwnerActions(self.policy,self.root,self.store,[self.profile],monotonic=lambda:self.mono[0]);self.addCleanup(self.actions.close)
    def prepare(self):return self.actions.prepare('owner','get_current_time',{})
    def approve(self,r):self.actions.decide('owner',r.mission_id,approve=True,reviewed_digest=r.digest)
    def test_missing_owner_decision_then_one_real_execution(self):
        r=self.prepare()
        with self.assertRaises(Denied):self.actions.run('owner',r.mission_id)
        self.assertEqual(self.count,0);self.approve(r)
        self.assertLess(abs(self.actions.run('owner',r.mission_id)['epoch']-time.time()),1)
        self.assertEqual(self.count,1)
        with self.assertRaises(Denied):self.actions.run('owner',r.mission_id)
        with self.store._db() as db:self.assertEqual(db.execute('SELECT used FROM approvals').fetchone()[0],1)
    def test_model_decision_digest_forgery_and_db_tamper_denied(self):
        r=self.prepare()
        with self.assertRaises(Denied):self.actions.decide('model',r.mission_id,approve=True,reviewed_digest=r.digest)
        with self.assertRaises(Denied):self.actions.decide('owner',r.mission_id,approve=True,reviewed_digest='a'*64)
        with self.store._db() as db:db.execute("UPDATE approvals SET status='approved'")
        with self.assertRaises(Denied):self.actions.run('owner',r.mission_id)
        self.assertEqual(self.count,0)
    def test_changed_scope_denies_before_consumption(self):
        r=self.prepare();self.approve(r);self.scopefile.write_text('changed')
        with self.assertRaises(Denied):self.actions.run('owner',r.mission_id)
        self.assertEqual(self.count,0)
        with self.store._db() as db:self.assertEqual(db.execute('SELECT used FROM approvals').fetchone()[0],0)
    def test_reject_expire_timeout_cancel_and_restart(self):
        for mode in ('reject','expire','cancel','restart'):
            self.mono[0]=0;r=self.prepare()
            if mode=='reject':self.actions.decide('owner',r.mission_id,approve=False,reviewed_digest=r.digest)
            else:
                self.approve(r)
                if mode=='expire':self.now[0]+=301
                elif mode=='timeout':self.mono[0]=61
                elif mode=='cancel':self.actions.cancel('owner',r.mission_id)
                else:
                    replacement=OwnerActions(self.policy,self.root,self.store,[self.profile])
                    with self.assertRaises(Denied):replacement.run('owner',r.mission_id)
                    self.actions.cancel('owner',r.mission_id);replacement.close()
            with self.assertRaises(Denied):self.actions.run('owner',r.mission_id)
        self.assertEqual(self.count,0)
    def test_decision_timeout_is_separate_from_approved_expiry(self):
        r=self.prepare();self.mono[0]=61
        with self.assertRaises(Denied):self.approve(r)
        self.mono[0]=0;r=self.prepare();self.approve(r);self.mono[0]=61
        self.assertIn('epoch',self.actions.run('owner',r.mission_id))
        self.mono[0]=0;r=self.prepare();self.approve(r);self.now[0]+=301
        with self.assertRaises(Denied):self.actions.run('owner',r.mission_id)
    def test_unregistered_malformed_sensitive_requests_and_untrusted_lease(self):
        for operation,args in [('shell.execute',{}),('get_current_time',{'shell':'injection'}),('get_current_time',{'password':'synthetic-not-secret'})]:
            with self.subTest(operation=operation),self.assertRaises((Denied,ContractError)):
                self.actions.prepare('owner',operation,args)
        r=self.prepare();forged=ExecutionPermit(object(),r)
        with self.assertRaises(Denied):forged.consume('get_current_time',{})
        with self.assertRaises(Denied):self.actions._consume_permit(ExecutionPermit(self.actions,r),'get_current_time',{})
        self.assertNotIn(b'synthetic-not-secret',self.store.path.read_bytes())
    def test_stop_interrupts_preparation_and_cannot_autoresume(self):
        entered=threading.Event()
        def scope(cancel):entered.set();cancel.wait(2);raise Cancelled('fixture cancellation')
        profile=ExecutionProfile('get_current_time',lambda raw:{},scope,self.profile.execute)
        manager=OwnerActions(self.policy,self.root,self.store,[profile])
        with ThreadPoolExecutor(1) as pool:
            pending=pool.submit(manager.prepare,'owner','get_current_time',{})
            self.assertTrue(entered.wait(1));started=time.monotonic();manager.stop('owner')
            self.assertLess(time.monotonic()-started,.2)
            with self.assertRaises(Cancelled):pending.result(timeout=1)
        with self.assertRaises(Denied):manager.prepare('owner','get_current_time',{})
