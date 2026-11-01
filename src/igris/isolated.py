"""Trusted fixed-worker container transport. Never expose image/argv/mounts to AI."""
import os
from pathlib import Path,PurePosixPath
import re
import selectors
import signal
import subprocess
import time
from uuid import uuid4

from .adapters.contracts import AdapterUnavailable,ContractError
from .adapters.hermes_chat import DockerHermesAdapter

ROOT=Path(__file__).resolve().parents[2]


class Cancelled(AdapterUnavailable):pass


def docker_command():
    return ['docker','--host=unix:///var/run/docker.sock']


def docker_environment():
    return {k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}


class IsolatedWorker:
    def __init__(self,*,cancel=None):
        import threading
        self.cancel=cancel if cancel is not None else threading.Event()
        self.name=None

    def run(self,image,program,mounts,*,component,timeout=180,memory='2g',payload=b''):
        """All selectors are trusted startup values; only payload/input files are data."""
        if not re.fullmatch('sha256:[a-f0-9]{64}',image or ''):raise ContractError('Pinned installed worker image required.')
        if not re.fullmatch('[a-z][a-z0-9-]{0,20}',component) or memory not in ('1g','2g','3g') or not 0<timeout<=300:
            raise ContractError('Invalid trusted worker limits.')
        if type(payload) is not bytes or len(payload)>32768:raise ContractError('Bounded worker request required.')
        base=docker_command();env=docker_environment()
        # Reuse the existing cross-process heavy-inference slot and orphan label.
        with DockerHermesAdapter()._slot():
            if self.cancel.is_set():raise Cancelled('Worker cancelled before launch.')
            existing=subprocess.run(base+['container','ls','--all','--filter','label=com.igris.runtime=hermes-inference','--format','{{.ID}}'],
                env=env,capture_output=True,text=True,check=True,timeout=10)
            if existing.stdout.strip():raise AdapterUnavailable('An unfinished inference worker needs operator review.')
            subprocess.run(base+['image','inspect',image],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=10)
            name='igris-'+component+'-'+uuid4().hex[:12];self.name=name
            args=base+['run','--rm','--pull=never','--interactive','--name',name,'--label','com.igris.runtime=hermes-inference',
                '--label','com.igris.component='+component,'--network','none','--read-only','--user',f'{os.getuid()}:{os.getgid()}',
                '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','128','--memory',memory,'--cpus','2',
                '--tmpfs','/tmp:rw,noexec,nosuid,size=536870912,mode=1777','--workdir','/tmp']
            for source,destination in mounts:
                source=Path(source).absolute();target=PurePosixPath(destination)
                if source.resolve(strict=True)!=source or not source.is_relative_to(ROOT) or not target.is_absolute() or '..' in target.parts or not str(target).startswith(('/input/','/models/','/opt/igris/')):
                    raise ContractError('Invalid fixed worker mount.')
                args+=['--mount',f'type=bind,src={source},dst={target},readonly']
            args += [image,*program]
            process=None;started=time.monotonic();output=bytearray();total=0
            try:
                process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,start_new_session=True)
                with selectors.DefaultSelector() as events:
                    for pipe in (process.stdout,process.stderr):
                        os.set_blocking(pipe.fileno(),False);events.register(pipe,selectors.EVENT_READ)
                    if payload:
                        os.set_blocking(process.stdin.fileno(),False);events.register(process.stdin,selectors.EVENT_WRITE)
                    else:process.stdin.close()
                    pending=memoryview(payload)
                    while events.get_map():
                        if self.cancel.is_set():raise Cancelled('Worker cancelled.')
                        if time.monotonic()-started>timeout:raise TimeoutError('Isolated worker deadline elapsed.')
                        for key,flag in events.select(.2):
                            pipe=key.fileobj
                            if flag & selectors.EVENT_WRITE:
                                count=os.write(pipe.fileno(),pending);pending=pending[count:]
                                if not pending:events.unregister(pipe);pipe.close()
                            else:
                                chunk=os.read(pipe.fileno(),8192)
                                if not chunk:events.unregister(pipe);pipe.close();continue
                                total+=len(chunk)
                                if total>131072:raise ContractError('Worker output exceeds limit.')
                                if pipe is process.stdout:output.extend(chunk)
                code=process.wait(timeout=5)
                if code:raise AdapterUnavailable('Isolated worker failed; private output not published.')
                return bytes(output)
            finally:
                # Reap the client first; --rm can still be removing the owned container.
                if process is not None:
                    if process.poll() is None:
                        try:os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                    process.wait(timeout=5)
                    for pipe in (process.stdin,process.stdout,process.stderr):
                        if not pipe.closed:pipe.close()
                absent=0
                for _ in range(5):
                    subprocess.run(base+['rm','--force',name],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
                    remaining=subprocess.run(base+['container','ls','--all','--filter','name=^/'+name+'$','--format','{{.ID}}'],
                        env=env,capture_output=True,text=True,check=True,timeout=5)
                    absent=absent+1 if not remaining.stdout.strip() else 0
                    if absent>=2:
                        self.name=None
                        break
                    time.sleep(.2)
                if self.name is not None:raise AdapterUnavailable('Worker cleanup could not be verified; owned name retained.')
