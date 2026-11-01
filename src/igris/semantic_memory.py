"""Existing Guardian controls mutations; approved facts remain SQLite authority."""
import hashlib,json,re,threading
from pathlib import Path
from .adapters.contracts import ContractError,identifier
from .guardian.activities import ExecutionProfile,ExecutionPermit
from .guardian.policy import Policy,Denied
from .integrations.mem0_runtime import Mem0Index
from .owned_jobs import UnconfirmedLaunch
from .memory import CATEGORIES,knowledge_text
from .scoped_memory import ScopedFacts

class PartialMemoryCommit(RuntimeError):pass

class SemanticMemory:
    def __init__(self,facts,policy,*,enabled=False,cancel=None):
        if type(facts) is not ScopedFacts or type(policy) is not Policy or facts.owner!=policy.actor:raise Denied('Existing scoped owner authority required.')
        self.facts,self.policy=facts,policy;self.index=Mem0Index(enabled=enabled);self.cancel=cancel if cancel is not None else threading.Event();self.last_backend='not_queried'
    def search(self,actor,conversation,query,*,probe=False,cancel=None):
        effective_cancel=cancel if cancel is not None else self.cancel
        self.policy.require('memory.search');self.facts._scope(actor,conversation)
        if actor!=self.policy.actor:raise Denied('Owner search required.')
        knowledge_text(query,512) if query else None
        self.last_backend='querying'
        try:result=self.index.query(self.policy,self.facts,conversation,query,cancel=effective_cancel,probe=probe)
        except UnconfirmedLaunch:
            self.last_backend='blocked_unconfirmed_launch';raise
        except (OSError,ValueError,RuntimeError) as exc:
            if effective_cancel.is_set():raise
            rows=self.facts.review(actor,conversation);terms=set(re.findall(r'\w{3,}',query.casefold()))-{'the','where','what','which','our','are','was','with','for','and'}
            ranked=sorted(((len(terms&set(re.findall(r'\w{3,}',row['text'].casefold()))),row) for row in rows),key=lambda pair:pair[0],reverse=True)
            result={'backend':'sqlite_keyword_fallback','facts':[row for score,row in ranked if score>0][:3],'reason':type(exc).__name__}
        self.last_backend=result['backend'];return result
    def normalize(self,raw):
        if type(raw) is not dict or 'kind' not in raw:raise ContractError('Typed memory management action required.')
        kind=raw['kind'];expected={'kind','conversation_id','category','text','classification','evidence'} if kind=='save' else {'kind','conversation_id','id','revision','text'} if kind=='correct' else {'kind','conversation_id','id','revision'} if kind=='delete' else set()
        if not expected or set(raw)!=expected:raise ContractError('Unsupported memory action/schema.')
        self.facts._scope(self.policy.actor,raw['conversation_id']);result=dict(raw,project=self.facts.project)
        if kind=='save':
            if type(raw['category']) is not str or raw['category'] not in CATEGORIES or type(raw['classification']) is not str or raw['classification'] not in ('assumption','verified_fact') or type(raw['evidence']) is not str:raise ContractError('Supported category/classification required.')
            knowledge_text(raw['text'],512)
            if raw['classification']=='verified_fact' or raw['evidence']:knowledge_text(raw['evidence'],512)
        else:
            identifier(raw['id']);current=self.facts.get(self.policy.actor,raw['conversation_id'],raw['id'])
            if type(raw['revision']) is not int or raw['revision']!=current['revision']:raise Denied('Current exact fact revision required.')
            result['current']=current
            if kind=='correct':knowledge_text(raw['text'],512)
        return result
    def scope(self,cancel):
        if cancel.is_set():raise Denied('Memory action cancelled.')
        self.policy.require('memory.manage');self.policy.require('memory.search')
        path=Path(__file__).resolve().parents[2]/'integrations/mem0/profile.json'
        return {'owner':self.policy.actor,'project':self.facts.project,'facts_revision_sha256':self.facts.revision_digest(self.policy.actor),'runtime_profile_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'authority':'scoped_sqlite','model_grants_permissions':False}
    def execute(self,arguments,cancel,permit):
        if type(permit) is not ExecutionPermit:raise Denied('Exact owner memory lease required.')
        permit.consume('memory.manage',arguments);self.policy.require('memory.manage');self.policy.require('memory.search')
        if cancel.is_set():raise Denied('Memory action cancelled before mutation.')
        kind=arguments['kind'];conversation=arguments['conversation_id'];actor=self.policy.actor
        if kind=='save':row=self.facts.save(actor,conversation,arguments['category'],arguments['text'],classification=arguments['classification'],evidence=arguments['evidence'],approved=True)
        elif kind=='correct':row=self.facts.correct(actor,conversation,arguments['id'],arguments['revision'],arguments['text'],approved=True)
        else:self.facts.delete(actor,conversation,arguments['id'],arguments['revision'],approved=True);row={'id':arguments['id'],'deleted':True}
        # SQLite is committed authority. An unavailable derived index does not
        # turn a successful save/delete into a false "nothing was changed" error.
        result={'origin':'real_sqlite','kind':kind,'fact':row,'conversation_id':conversation,'project':self.facts.project}
        if not cancel.is_set():
            try:index=self.search(actor,conversation,'',cancel=cancel);result['index_backend']=index['backend']
            except UnconfirmedLaunch:raise
            except Exception as exc:raise PartialMemoryCommit('Approved SQLite change committed; indexing interrupted. Review facts before retrying.') from exc
        else:result['index_backend']='cancelled_after_sqlite_commit'
        return result
    def registration(self):return ExecutionProfile('memory.manage',self.normalize,self.scope,self.execute)
