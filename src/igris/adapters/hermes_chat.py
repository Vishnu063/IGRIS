"""Typed chat protocol and one-shot offline Docker transport for real Hermes."""
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
from uuid import uuid4

from .contracts import AdapterUnavailable, ContractError, identifier
from ..costs import CostEstimate, CostGuardian
from ..guardian.secrets import redact
from ..memory import knowledge_text, private_file

ROOT = Path(__file__).resolve().parents[3]
MAX_PACKET = 32768
CONTROLS = {'non_root': True, 'source_read_only': True, 'external_network_absent': True,
            'model_authentication_checked': True, 'tools_exposed': 0,
            'guardian_tool_dispatch_denied': True, 'automatic_install_disabled': True}


class RuntimeBusy(AdapterUnavailable): pass


def chat_text(value):
    knowledge_text(value, 4096)
    if len(value.encode('utf-8')) > 8192 or any((ord(c) < 32 and c not in '\n\t') or 127 <= ord(c) <= 159 for c in value):
        raise ContractError('Invalid bounded chat text.')
    return value


def response_text(value):
    if type(value) is not str: raise ContractError('Invalid generated response.')
    value = ''.join(c for c in value if not ((ord(c) < 32 and c not in '\n\t') or 127 <= ord(c) <= 159))
    value = redact(value)
    return chat_text(value)


@dataclass(frozen=True)
class ChatRequest:
    request_id: str
    prompt: str
    history: tuple = ()

    def __post_init__(self):
        identifier(self.request_id); chat_text(self.prompt)
        if type(self.history) is not tuple or len(self.history) > 12 or len(self.history) % 2:
            raise ContractError('Only bounded complete conversation pairs supported.')
        for index, item in enumerate(self.history):
            if type(item) is not tuple or len(item) != 2 or item[0] != ('user' if index % 2 == 0 else 'assistant'):
                raise ContractError('History cannot grant system/tool roles.')
            chat_text(item[1])
        if len(json.dumps(self.payload(), ensure_ascii=False).encode()) > MAX_PACKET:
            raise ContractError('Chat packet exceeds limit.')

    def payload(self):
        return {'schema_version': 1, 'request_id': self.request_id, 'prompt': self.prompt,
                'history': [{'role': role, 'content': content} for role, content in self.history]}

    @classmethod
    def parse(cls, raw):
        if type(raw) is not dict or set(raw) != {'schema_version', 'request_id', 'prompt', 'history'} or type(raw['schema_version']) is not int or raw['schema_version'] != 1:
            raise ContractError('Invalid chat request schema.')
        if type(raw['history']) is not list or any(type(m) is not dict or set(m) != {'role', 'content'} for m in raw['history']):
            raise ContractError('Invalid history schema.')
        return cls(raw['request_id'], raw['prompt'], tuple((m['role'], m['content']) for m in raw['history']))


@dataclass(frozen=True)
class ChatReply:
    request_id: str
    text: str
    model_sha256: str
    api_calls: int
    origin: str = 'real_local_inference'

    def __post_init__(self):
        identifier(self.request_id); chat_text(self.text)
        if type(self.model_sha256) is not str or not re.fullmatch('[a-f0-9]{64}', self.model_sha256) or type(self.api_calls) is not int or not 1 <= self.api_calls <= 3:
            raise ContractError('Invalid inference evidence.')
        if self.origin not in ('real_local_inference', 'simulated'): raise ContractError('Invalid response origin.')


@dataclass(frozen=True)
class ToolProposal:
    request_id: str
    raw: str
    model_sha256: str
    api_calls: int
    generation_seconds: float
    hermes_maxrss_kib: int
    model_maxrss_kib: int
    origin: str = 'real_local_inference'

    def __post_init__(self):
        identifier(self.request_id)
        if type(self.raw) is not str or not self.raw or len(self.raw.encode()) > 8192:
            raise ContractError('Invalid bounded model proposal.')
        if type(self.model_sha256) is not str or not re.fullmatch('[a-f0-9]{64}',self.model_sha256) or type(self.api_calls) is not int or not 1 <= self.api_calls <= 3 or self.origin != 'real_local_inference':
            raise ContractError('Invalid proposal provenance.')
        import math
        if type(self.generation_seconds) not in (int,float) or not math.isfinite(self.generation_seconds) or not 0 <= self.generation_seconds <= 180:
            raise ContractError('Invalid generation timing.')
        if any(type(value) is not int or value <= 0 for value in (self.hermes_maxrss_kib,self.model_maxrss_kib)):
            raise ContractError('Invalid measured memory.')


class DockerHermesAdapter:
    """Trusted operator transport. No worker paths, flags or endpoints from chat."""
    def __init__(self, *, root=None, cancel=None):
        self.cancel = cancel if cancel is not None else threading.Event()
        self.root = Path(root) if root is not None else ROOT
        self.runtime = self.root/'runtime'
        self.profile = json.loads((self.root/'integrations/hermes-inference/profile.json').read_text())

    def _preflight(self):
        if platform.system() != 'Linux' or platform.machine() != 'x86_64': raise AdapterUnavailable('Verified cloud Linux x86_64 runtime required.')
        p = self.profile
        if p['enabled_tools'] != [] or p['authorized_spend_inr'] != 0 or not re.fullmatch('sha256:[a-f0-9]{64}', p['container_image']):
            raise ContractError('Reasoning-only zero-budget pinned profile required.')
        CostGuardian().check(CostEstimate('resource', 0))
        for name, expected in [('cpython3149.tar.gz', p['python_archive_sha256']),
                               ('llama-b11960.tar.gz', p['engine_archive_sha256']),
                               (p['model_file'], p['model_sha256'])]:
            path = self.runtime/name
            if path.is_symlink() or not path.resolve().is_relative_to(self.runtime.resolve()): raise ContractError('Unsafe model/runtime asset.')
            sha = hashlib.sha256()
            with path.open('rb') as source:
                while chunk := source.read(1024*1024): sha.update(chunk)
            if sha.hexdigest() != expected: raise ContractError('Runtime asset integrity failure.')
        manifest = json.loads((self.root/'docs/integrations/hermes-source-manifest.json').read_text())
        for name, expected in manifest['local_sha256'].items():
            path = self.root/'vendor/hermes-agent'/name
            if path.is_symlink() or not path.resolve().is_relative_to(self.root/'vendor/hermes-agent') or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ContractError('Copied Hermes source requires review.')

    @contextmanager
    def _slot(self):
        directory = self.runtime/'locks'
        directory.mkdir(mode=0o700, exist_ok=True)
        path = directory/'hermes-execution.lock'
        try: private_file(path, create=True)
        except FileExistsError: pass
        private_file(path)
        with path.open('rb') as handle:
            try: fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: raise RuntimeBusy('Another local inference turn is active.') from None
            try: yield
            finally: fcntl.flock(handle, fcntl.LOCK_UN)

    def _run(self, mode, payload=None):
        if mode not in ('probe', 'chat', 'tools', 'specialist'): raise ContractError('Unsupported fixed worker.')
        self._preflight()
        with self._slot():
            docker = shutil.which('docker')
            if not docker: raise AdapterUnavailable('Managed Docker unavailable; no host fallback.')
            env = {k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}
            base = [docker, '--host=unix:///var/run/docker.sock']
            idle = subprocess.run(base+['container', 'ls', '--all', '--filter', 'label=com.igris.runtime=hermes-inference', '--format', '{{.ID}}'],
                                  capture_output=True, text=True, check=True, env=env, timeout=10)
            if idle.stdout.strip(): raise RuntimeBusy('A previous inference container needs cleanup.')
            subprocess.run(base+['image', 'inspect', self.profile['container_image']], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=10)
            name = 'igris-hermes-'+uuid4().hex[:12]
            worker = {'probe':'hermes_inference_worker.py','chat':'hermes_chat_worker.py','tools':'hermes_tool_worker.py','specialist':'hermes_specialist_worker.py'}[mode]
            args = base+['run', '--rm', '--pull=never', '--interactive', '--name', name,
                '--label', 'com.igris.runtime=hermes-inference', '--network', 'none', '--read-only',
                '--user', f'{os.getuid()}:{os.getgid()}', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                '--pids-limit', '128', '--memory', '3g', '--cpus', '2',
                '--tmpfs', '/tmp:rw,noexec,nosuid,size=268435456,mode=1777', '--workdir', '/tmp',
                '--env', 'HOME=/tmp/igris-home', '--env', 'HERMES_HOME=/tmp/igris-home/hermes',
                '--env', 'HERMES_DISABLE_LAZY_INSTALLS=1', '--env', 'PYTHONDONTWRITEBYTECODE=1',
                '--env', 'NO_PROXY=127.0.0.1,localhost']
            mounts = ['runtime/python3149', 'runtime/hermes-venv', 'runtime/llama-b11960',
                      'runtime/'+self.profile['model_file'], 'vendor/hermes-agent', 'src/igris',
                      'integrations/hermes-inference/profile.json', 'scripts/hermes_inference_worker.py']
            if mode == 'chat': mounts.append('scripts/hermes_chat_worker.py')
            if mode == 'tools': mounts.append('scripts/hermes_tool_worker.py')
            if mode == 'specialist': mounts += ['scripts/hermes_specialist_worker.py', 'integrations/agency-agents']
            for relative in mounts:
                path = self.root/relative
                if not path.exists() or path.is_symlink(): raise ContractError('Unsafe/missing worker mount.')
                args += ['--mount', f'type=bind,src={path},dst={path},readonly']
            args += [self.profile['container_image'], str(self.root/'runtime/hermes-venv/bin/python'), '-I', str(self.root/'scripts'/worker)]
            encoded = b'' if payload is None else json.dumps(payload, ensure_ascii=False).encode()
            if len(encoded) > MAX_PACKET: raise ContractError('Request too large.')
            with tempfile.TemporaryFile(dir=self.runtime) as output:
                try:
                    if self.cancel.is_set(): raise AdapterUnavailable('Reasoning cancelled before launch.')
                    process = subprocess.Popen(args, env=env, stdin=subprocess.PIPE, stdout=output, stderr=subprocess.STDOUT)
                    deadline = time.monotonic()+180
                    try:
                        first = True
                        while True:
                            if self.cancel.is_set(): raise AdapterUnavailable('Reasoning cancelled; response discarded.')
                            if time.monotonic() >= deadline: raise subprocess.TimeoutExpired(args,180)
                            try:
                                process.communicate(encoded if first else None, timeout=.2)
                                break
                            except subprocess.TimeoutExpired: first = False
                    finally:
                        if process.poll() is None: process.kill()
                        process.wait(timeout=5)
                        if process.stdin is not None: process.stdin.close()
                finally:
                    subprocess.run(base+['rm', '--force', name], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                    absent = 0
                    for _ in range(10):
                        remaining = subprocess.run(base+['container', 'ls', '--all', '--filter', 'name=^/'+name+'$', '--format', '{{.ID}}'],
                                                   capture_output=True, text=True, check=True, env=env, timeout=10)
                        absent = absent+1 if not remaining.stdout.strip() else 0
                        if absent == 2: break
                        if remaining.stdout.strip(): subprocess.run(base+['rm','--force',name],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15)
                        time.sleep(.1)
                    if absent != 2: raise AdapterUnavailable('Worker cleanup not verified.')
                output.seek(0, 2); length = output.tell(); output.seek(max(0, length-65536))
                raw = output.read().decode('utf-8', errors='replace')
            if process.returncode: raise AdapterUnavailable('Isolated reasoning worker failed; no reply accepted.')
            for line in reversed(raw.splitlines()):
                try: result = json.loads(line)
                except ValueError: continue
                if type(result) is dict and result.get('origin') == 'real_local_inference':
                    if result.get('model_sha256') != self.profile['model_sha256'] or result.get('controls') != CONTROLS:
                        raise ContractError('Worker identity or security controls mismatch.')
                    return result
            raise ContractError('Missing verified worker response.')

    def reply(self, request):
        if type(request) is not ChatRequest: raise ContractError('Typed chat request required.')
        result = self._run('chat', request.payload())
        if set(result) != {'schema_version', 'request_id', 'origin', 'model_sha256', 'text', 'api_calls', 'controls'} or type(result['schema_version']) is not int or result['schema_version'] != 1 or result['request_id'] != request.request_id:
            raise ContractError('Chat reply schema/correlation mismatch.')
        return ChatReply(result['request_id'], response_text(result['text']), result['model_sha256'], result['api_calls'])

    def probe(self):
        result = self._run('probe')
        if result.get('status') != 'PASS': raise ContractError('Probe did not pass.')
        result['container_removed'] = True
        return result

    def propose(self, request, *, file_hints=()):
        if type(request) is not ChatRequest: raise ContractError('Typed proposal request required.')
        from ..guardian.readonly import components
        if type(file_hints) is not tuple or len(file_hints)>64: raise ContractError('Invalid bounded file hints.')
        for name in file_hints: components(name)
        payload=dict(request.payload(),file_hints=list(file_hints))
        result = self._run('tools', payload)
        expected = {'schema_version','request_id','origin','model_sha256','proposal','api_calls','controls',
                    'generation_seconds','hermes_maxrss_kib','model_maxrss_kib'}
        if set(result) != expected or type(result['schema_version']) is not int or result['schema_version'] != 1 or result['request_id'] != request.request_id:
            raise ContractError('Invalid proposal transport schema/correlation.')
        return ToolProposal(request.request_id,result['proposal'],result['model_sha256'],result['api_calls'],
                            result['generation_seconds'],result['hermes_maxrss_kib'],result['model_maxrss_kib'],result['origin'])

    def specialist(self, request, role):
        from ..reused_agents import specialist_definition
        if type(request) is not ChatRequest: raise ContractError('Typed specialist request required.')
        digest=hashlib.sha256(specialist_definition(role).encode()).hexdigest()
        result=self._run('specialist',dict(request.payload(),role=role,definition_sha256=digest))
        expected={'schema_version','request_id','origin','model_sha256','text','api_calls','controls','role','definition_sha256'}
        if set(result)!=expected or type(result['schema_version']) is not int or result['schema_version']!=1 or result['request_id']!=request.request_id or result['role']!=role or result['definition_sha256']!=digest: raise ContractError('Specialist identity/correlation mismatch.')
        reply=ChatReply(request.request_id,response_text(result['text']),result['model_sha256'],result['api_calls'])
        return {'role':role,'definition_sha256':digest,'text':reply.text,'model_sha256':reply.model_sha256,'origin':reply.origin,'api_calls':reply.api_calls}
