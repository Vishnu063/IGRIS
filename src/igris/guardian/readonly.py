"""Three typed tools inside the EXISTING Guardian broker. No alternate executor."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from .policy import Denied
from .secrets import redact
from ..memory import private_file

TOOLS = frozenset({'get_current_time', 'list_workspace_files', 'read_workspace_file'})
MAX_FILE = 2048


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise Denied('Duplicate JSON field.')
        result[key] = value
    return result


def components(value, *, directory=False):
    if directory and value == '.': return ()
    from .broker import path_parts
    if directory:
        if type(value) is not str or len(value) > 512: raise Denied('Invalid directory.')
        # Reuse file-component validation by appending a fixed harmless leaf.
        parts = path_parts(value+'/scope.txt')[:-1]
    else: parts = path_parts(value)
    if any(any(word in p.lower() for word in ('key','passwd','private','env','config','auth','account')) for p in parts):
        raise Denied('Sensitive path denied.')
    return tuple(parts)


@dataclass(frozen=True)
class ToolScope:
    workspace: Path
    allowed_operations: tuple
    directories: tuple
    files: tuple
    approval_required: tuple

    @classmethod
    def load(cls, filename):
        path = private_file(filename)
        with path.open('rb') as handle: raw = handle.read(8193)
        if len(raw) > 8192: raise Denied('Tool configuration exceeds limit.')
        data = json.loads(raw, object_pairs_hook=unique)
        if type(data) is not dict or set(data) != {'version','workspace','allowed_operations','directories','files','approval_required'} or type(data['version']) is not int or data['version'] != 1:
            raise Denied('Invalid trusted tool configuration.')
        if type(data['workspace']) is not str or not Path(data['workspace']).is_absolute(): raise Denied('Absolute trusted workspace required.')
        root = Path(data['workspace'])
        info = root.stat()
        if root.resolve(strict=True) != root or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or root == Path('/') or (root/'.git').exists() or path.is_relative_to(root):
            raise Denied('Private isolated test workspace required.')
        for field, limit in (('allowed_operations',3),('directories',16),('files',64),('approval_required',3)):
            values = data[field]
            if type(values) is not list or len(values) > limit or any(type(x) is not str for x in values) or len(set(values)) != len(values):
                raise Denied('Invalid bounded allowlist.')
        if not set(data['allowed_operations']) <= TOOLS or not set(data['approval_required']) <= set(data['allowed_operations']):
            raise Denied('Unregistered operation in trusted profile.')
        for directory in data['directories']: components(directory, directory=True)
        for file in data['files']:
            parts = components(file)
            if ('/'.join(parts[:-1]) or '.') not in data['directories']: raise Denied('File parent not approved.')
        return cls(root, tuple(data['allowed_operations']), tuple(data['directories']), tuple(data['files']), tuple(data['approval_required']))

    @property
    def digest(self):
        return hashlib.sha256(json.dumps({'version':1,'workspace':str(self.workspace), 'allowed_operations':sorted(self.allowed_operations),
            'directories':sorted(self.directories),'files':sorted(self.files),'approval_required':sorted(self.approval_required),
            'max_file_bytes':MAX_FILE},sort_keys=True,separators=(',',':')).encode()).hexdigest()


def parse_proposal(raw):
    if type(raw) is not str or len(raw.encode()) > 8192: raise Denied('Invalid proposal size/type.')
    proposal = json.loads(raw, object_pairs_hook=unique)
    if type(proposal) is not dict or set(proposal) != {'operation','arguments'}:
        raise Denied('Invalid proposal schema.')
    operation, args = proposal['operation'], proposal['arguments']
    if type(operation) is not str or operation not in TOOLS or type(args) is not dict:
        raise Denied('Unregistered tool or malformed arguments.')
    if operation == 'get_current_time':
        if args: raise Denied('Time tool accepts no arguments.')
    else:
        if set(args) != {'path'}: raise Denied('Only a path argument is accepted.')
        components(args['path'], directory=operation == 'list_workspace_files')
    return proposal


def execute_tool(scope, operation, args):
    from .broker import open_parent, read_text
    if operation == 'get_current_time':
        return {'utc':datetime.now(timezone.utc).isoformat()}
    path = args['path']
    if operation == 'read_workspace_file':
        if path not in scope.files: raise Denied('File not explicitly approved.')
        text = redact(read_text(scope.workspace, path, maximum=MAX_FILE))
        text = ''.join(c for c in text if not ((ord(c)<32 and c not in '\n\t') or 127<=ord(c)<=159))
        return {'text':text}
    if path not in scope.directories: raise Denied('Directory not explicitly approved.')
    parts = components(path, directory=True)
    # A fixed sentinel lets existing descriptor traversal hold the final directory.
    parent = open_parent(scope.workspace, [*parts, 'scope.txt'])
    try:
        names = []
        for allowed in scope.files:
            leaf_parts = components(allowed)
            if leaf_parts[:-1] != parts: continue
            try: info = os.stat(leaf_parts[-1], dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError: continue
            if stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= MAX_FILE:
                names.append(allowed)
        return {'files':sorted(names)}
    finally: os.close(parent)


def run(policy, root, envelope, scope, store, environment):
    """All untrusted proposal parsing, authority checks and execution occur here."""
    from ..adapters.contracts import identifier
    request_id = mission_id = 'unavailable'
    operation, digest, start = 'unregistered', 'unavailable', time.monotonic()
    authorized = False
    try:
        if type(envelope) is not dict or set(envelope) != {'request_id','mission_id','proposal','approval_id'}:
            raise Denied('Invalid tool execution envelope.')
        request_id, mission_id = identifier(envelope['request_id']), identifier(envelope['mission_id'])
        raw = envelope['proposal']
        if type(raw) is str: digest = hashlib.sha256(raw.encode()).hexdigest()
        proposal = parse_proposal(raw)
        operation, args = proposal['operation'], proposal['arguments']
        if root != scope.workspace or operation not in scope.allowed_operations: raise Denied('Tool not explicitly allowed.')
        policy.require(operation)
        # Validate scope before any approval is consumed.
        if operation == 'read_workspace_file' and args['path'] not in scope.files: raise Denied('File not explicitly approved.')
        if operation == 'list_workspace_files' and args['path'] not in scope.directories: raise Denied('Directory not explicitly approved.')
        binding = {'request_id':request_id,'mission_id':mission_id,'scope_sha256':scope.digest}
        if operation in scope.approval_required:
            store.consume(envelope['approval_id'], policy, root, proposal, environment=environment, binding=binding)
        elif envelope['approval_id'] is not None:
            raise Denied('Unexpected approval reference.')
        authorization_ms = (time.monotonic()-start)*1000
        store.tool_event(policy, request_id, mission_id, operation, digest, 'authorized', authorization_ms=authorization_ms)
        authorized = True
        before = time.monotonic()
        result = execute_tool(scope, operation, args)
        execution_ms = (time.monotonic()-before)*1000
        store.tool_event(policy, request_id, mission_id, operation, digest, 'completed', execution_ms=execution_ms)
        return {'ok':True,'result':result,'operation':operation,'authorization_ms':authorization_ms,'execution_ms':execution_ms}
    except (KeyboardInterrupt, SystemExit): raise
    except Exception as exc:
        event = 'execution_failed' if authorized else 'denied'
        # Do not put raw argument/JSON/parser/OS exception text into errors or logs.
        store.tool_event(policy, request_id, mission_id, operation, digest, event)
        return {'ok':False,'reason': 'Tool execution failed.' if authorized else 'Guardian denied the tool request.',
                'decision':event,'operation':operation,'error_class':type(exc).__name__}
