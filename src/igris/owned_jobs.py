"""Remove only immutable IDs bearing this launch's exact ownership marker.

Markers prevent accidental name collisions, not attacks by a Docker administrator.
"""
import re,subprocess,time
from .adapters.contracts import AdapterUnavailable

class UnconfirmedLaunch(AdapterUnavailable):pass

def remove_owned(base,environment,name,marker,*,expected_cid=None):
    if not re.fullmatch(r'igris-[a-z0-9-]{1,60}',name) or not re.fullmatch('[a-f0-9]{32}',marker):raise ValueError('Invalid owned-job identity.')
    if expected_cid is not None and not re.fullmatch('[a-f0-9]{64}',expected_cid):raise ValueError('Immutable owned ID required.')
    absent=0
    for _ in range(10):
        identity=['--filter','id='+expected_cid] if expected_cid else []
        result=subprocess.run(base+['container','ls','--all','--no-trunc','--filter','name=^/'+name+'$','--filter','label=com.igris.owner='+marker,'--format','{{.ID}}']+identity,env=environment,capture_output=True,text=True,check=True,timeout=5)
        ids=result.stdout.split()
        if len(ids)>1 or any(not re.fullmatch('[a-f0-9]{64}',value) or (expected_cid is not None and value!=expected_cid) for value in ids):raise RuntimeError('Unexpected owned-container identity; preserved.')
        # --rm may finish between listing and removal. A nonzero rm is not
        # evidence of cleanup: the following repeated ID queries must be empty.
        for cid in ids:subprocess.run(base+['rm','--force',cid],env=environment,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False,timeout=10)
        absent=absent+1 if not ids else 0
        if absent>=2:return
        time.sleep(.2)
    raise RuntimeError('Owned-container removal not verified.')


def _launch_directory(runtime):
    import os,stat
    from pathlib import Path
    directory=Path(runtime).absolute()/'locks'/'launches'
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    info=directory.lstat()
    if directory.resolve()!=directory or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:raise RuntimeError('Private launch directory required.')
    return directory


def assert_no_pending_launches(runtime):
    if any(_launch_directory(runtime).iterdir()):raise UnconfirmedLaunch('An unconfirmed owned launch requires operator review; no automatic restart.')


class OwnedLaunch:
    """Create acknowledgement precedes any start; unknown creation fails closed.

    A private ledger survives crashes/unknown create responses. It contains only
    ownership metadata, never approvals. Restart cannot resume a recorded action.
    """
    def __init__(self,runtime,base,environment,name,marker):
        import re
        if not re.fullmatch(r'igris-[a-z0-9-]{1,60}',name) or not re.fullmatch('[a-f0-9]{32}',marker):raise ValueError('Invalid owned launch identity.')
        self.base,self.environment,self.name,self.marker=base,environment,name,marker
        self.path=_launch_directory(runtime)/(marker+'.json');self.cid=None;self.record_created=False;self.request_sent=False
    def _write(self):
        import json
        from .memory import private_file
        private_file(self.path).write_text(json.dumps({'schema_version':1,'name':self.name,'marker':self.marker,'phase':'created' if self.cid else 'creating','container_id':self.cid})+'\n')
    def create(self,args):
        from .memory import private_file
        private_file(self.path,create=True);self.record_created=True;self._write();self.request_sent=True
        result=subprocess.run(args,env=self.environment,capture_output=True,check=True,timeout=30)
        cid=result.stdout.decode('ascii').strip()
        if not re.fullmatch('[a-f0-9]{64}',cid):raise RuntimeError('No acknowledged immutable container ID; no start issued.')
        self.cid=cid;self._write();return cid
    def cleanup(self):
        from .memory import private_file
        if not self.record_created:return
        if self.request_sent and self.cid is None:raise UnconfirmedLaunch('Creation unconfirmed; no start issued. Private launch record retained for operator review.')
        if self.cid:remove_owned(self.base,self.environment,self.name,self.marker,expected_cid=self.cid)
        private_file(self.path).unlink();self.record_created=False
