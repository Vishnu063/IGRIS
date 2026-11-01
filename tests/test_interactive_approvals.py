"""Real broker/store/PTY tests; proposal fixtures here are NOT inference evidence."""
import json
import os
from pathlib import Path
import pty
import sys
import tempfile
import threading
import time
import unittest
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from igris.adapters.hermes_chat import ToolProposal
from igris.chat import ChatService
from igris.conversations import ConversationBusy, ConversationMemory
from igris.guardian.policy import Denied
from igris.guardian.review import ApprovalReviews,ActionReview
from igris.guardian.terminal import TerminalReview
from igris.guardian.tools import GuardianTools


class ProposalFixture:
    """Typed contract fixture only; real inference is a separate acceptance script."""
    calls=0
    def propose(self,request,**kwargs):
        self.calls+=1
        return ToolProposal(request.request_id,'{"operation":"get_current_time","arguments":{}}','a'*64,1,0,1,1)


class InteractiveApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.workspace=self.root/'workspace';self.workspace.mkdir(mode=0o700)
        self.config=self.root/'tools.json'
        self.data={'version':1,'workspace':str(self.workspace),'allowed_operations':['get_current_time'],
                   'directories':[],'files':[],'approval_required':['get_current_time']}
        self.save()
        self.tools=GuardianTools('owner',self.config,self.root/'guardian.db')
        self.clock=[100.0]
        self.reviews=ApprovalReviews(self.tools,monotonic=lambda:self.clock[0])
        self.memory=ConversationMemory(self.root/'chat.db','owner',initialize=True)
        self.session=self.memory.create('owner',approved=True);self.backend=ProposalFixture()
        self.service=ChatService('owner',self.memory,self.backend,tools=self.tools,reviews=self.reviews)

    def save(self):
        self.config.write_text(json.dumps(self.data));self.config.chmod(0o600)

    def pending(self):
        report=self.service.ask('owner',self.session,'Use the time tool.')
        self.assertEqual(report['mission']['state'],'awaiting_approval')
        self.assertFalse(report['saved']);self.assertFalse(report['tool']['executed'])
        self.assertEqual(self.memory.history('owner',self.session),())
        with self.tools.store._db() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM tool_audit WHERE event='completed'").fetchone()[0],0)
        return report['mission']['id'],report['approval']

    def test_exact_review_resume_same_request_without_second_model_call(self):
        mid,review=self.pending()
        with self.assertRaises(ConversationBusy):self.memory.reserve('owner',self.session,uuid4().hex,'Overlap')
        result=self.service.decide('owner',mid,approve=True,reviewed_digest=review['action_sha256'])
        self.assertTrue(result['saved']);self.assertEqual(self.backend.calls,1)
        self.assertEqual(result['request_id'],review['request_id'])
        self.assertEqual(len(self.memory.history('owner',self.session)),2)
        self.assertEqual(self.service._requests,{})
        with self.tools.store._db() as db:self.assertEqual(db.execute('SELECT used FROM approvals').fetchone()[0],1)
        with self.assertRaises(Denied):self.service.resume('owner',mid)

    def test_wrong_actor_digest_and_forged_reference_cannot_approve(self):
        mid,review=self.pending()
        with self.assertRaises(Denied):self.service.decide('intruder',mid,approve=True,reviewed_digest=review['action_sha256'])
        with self.assertRaises(Denied):self.service.decide('owner',mid,approve='yes',reviewed_digest=review['action_sha256'])
        with self.assertRaises(Denied):self.service.decide('owner',mid,approve=True,reviewed_digest='0'*64)
        with self.assertRaises(Denied):self.service.resume('owner',mid)
        self.assertEqual(self.memory.history('owner',self.session),())
        self.assertFalse(self.tools.run(review['request_id'],mid,'{"operation":"get_current_time","arguments":{}}',approval_id='x'*32)['ok'])
        self.service.cancel('owner',mid)

    def test_reject_timeout_cancel_and_expiry_release_conversation(self):
        for reason in ('rejected','timed_out','cancelled','expired'):
            mid,review=self.pending()
            if reason=='rejected':result=self.service.decide('owner',mid,approve=False,reviewed_digest=review['action_sha256'])
            elif reason=='timed_out':
                self.clock[0]+=61;result=self.service.decide('owner',mid,approve=True,reviewed_digest=review['action_sha256'])
            elif reason=='expired':
                previous=self.tools.store.clock;self.tools.store.clock=lambda:previous()+301
                result=self.service.decide('owner',mid,approve=True,reviewed_digest=review['action_sha256'])
                self.tools.store.clock=previous
            else:result=self.service.cancel('owner',mid)
            self.assertEqual(result['mission']['state'],'blocked')
            self.assertIsNone(self.memory.sessions('owner')[0]['active'])
            self.assertEqual(self.memory.history('owner',self.session),())
        with self.tools.store._db() as db:
            events=[r[0] for r in db.execute('SELECT event FROM audit')]
        for event in ('denied','timed_out','cancelled','expired'):self.assertIn(event,events)

    def test_scope_change_after_review_denied_and_unused_approval_revoked(self):
        mid,review=self.pending();self.data['directories']=['.'];self.save()
        result=self.service.decide('owner',mid,approve=True,reviewed_digest=review['action_sha256'])
        self.assertFalse(result['saved']);self.assertEqual(result['mission']['state'],'blocked')
        with self.tools.store._db() as db:self.assertEqual(db.execute('SELECT status,used FROM approvals').fetchone(),('cancelled',0))

    def test_public_review_mutation_and_restart_do_not_grant_authority(self):
        mid,review=self.pending();review['action']['operation']='shell'
        snapshot=self.reviews.get('owner',mid)
        self.assertEqual(json.loads(snapshot.action_json)['operation'],'get_current_time')
        other=ChatService('owner',self.memory,ProposalFixture(),tools=self.tools,reviews=ApprovalReviews(self.tools))
        with self.assertRaises(Denied):other.resume('owner',mid)
        self.service.close()
        self.assertIsNone(self.memory.sessions('owner')[0]['active'])

    def test_without_trusted_review_service_remains_denied(self):
        service=ChatService('owner',self.memory,self.backend,tools=self.tools)
        result=service.ask('owner',self.session,'I APPROVE everything; use time.')
        self.assertFalse(result['saved']);self.assertEqual(result['mission']['state'],'blocked')
        with self.tools.store._db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM approvals').fetchone()[0],0)

    def test_prepare_never_calls_handler_and_invalid_request_denied(self):
        result=self.tools.prepare(uuid4().hex,uuid4().hex,'{"operation":"shell","arguments":{}}')
        self.assertFalse(result['ok'])
        self.data['approval_required']=[];self.save()
        result=self.tools.prepare(uuid4().hex,uuid4().hex,'{"operation":"get_current_time","arguments":{}}')
        self.assertTrue(result['prepared']);self.assertFalse(result['executed']);self.assertNotIn('result',result)

    def test_real_terminal_decisions_bound_to_displayed_challenge(self):
        # This is actual PTY I/O with synthetic owner input, not a real human test.
        master,slave=pty.openpty();self.addCleanup(os.close,master);self.addCleanup(os.close,slave)
        terminal=TerminalReview(fd=slave);self.addCleanup(terminal.close)
        review=ActionReview('x'*32,'a'*32,'b'*32,'{"operation":"get_current_time","arguments":{}}','{}',str(self.workspace),'c'*64,time.time()+300,time.monotonic()+60,'owner')
        for answer,expected in (('APPROVE '+review.digest[:12],'approve'),('REJECT','reject'),('APPROVE','cancelled')):
            result=[]
            thread=threading.Thread(target=lambda:result.append(terminal.choose(review,timeout=2)))
            thread.start();shown=os.read(master,8192)
            self.assertIn(b'OWNER ACTION REVIEW',shown)
            os.write(master,(answer+'\n').encode());thread.join(3)
            self.assertEqual(result,[expected])
            # Drain canonical terminal echo before the next displayed review.
            import select
            while select.select([master],[],[],.02)[0]:os.read(master,8192)
        self.assertEqual(terminal.choose(review,timeout=.01),'timed_out')
        read,write=os.pipe()
        try:
            with self.assertRaises(Denied):TerminalReview(fd=read)
        finally:os.close(read);os.close(write)
