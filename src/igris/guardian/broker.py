"""One bounded request per process; no model, network listener or general shell."""
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys

# -I -S removes cwd/site imports. Only trusted application code is added.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from igris.guardian.policy import Denied, Permission, Policy
from igris.guardian.secrets import prompt_text
from igris.guardian.approvals import ApprovalStore

MAX_FILE = 8192


def apply_limits():
    for kind, limit in ((resource.RLIMIT_CPU, 2), (resource.RLIMIT_AS, 256 * 1024 * 1024),
                        (resource.RLIMIT_NOFILE, 64), (resource.RLIMIT_FSIZE, 1024 * 1024),
                        (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(kind, (limit, limit))


def path_parts(value):
    if type(value) is not str or not value or len(value) > 512:
        raise Denied('Invalid path.')
    parts = value.split('/')
    if len(parts) > 8 or any(not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,79}', p) for p in parts):
        raise Denied('Invalid path.')
    if any(any(word in p.lower() for word in ('secret', 'credential', 'password', 'token', 'customer')) for p in parts):
        raise Denied('Sensitive path denied.')
    if Path(parts[-1]).suffix.lower() not in {'.txt', '.md', '.json', '.toml', '.yaml', '.yml', '.py'}:
        raise Denied('Unsupported file type.')
    return parts


def open_parent(root, parts):
    """Hold no-follow directory descriptors throughout traversal."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_text(root, path):
    parts = path_parts(path)
    parent = open_parent(root, parts)
    try:
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_FILE:
                raise Denied('Unsafe file denied.')
            data = handle.read(MAX_FILE + 1)
            if len(data) > MAX_FILE:
                raise Denied('File too large.')
            return data.decode('utf-8')
    finally:
        os.close(parent)


def create_parts(args):
    if set(args) != {'path', 'text'}:
        raise Denied('Invalid file creation arguments.')
    parts = path_parts(args['path'])
    if parts[0] != 'artifacts' or len(parts) < 2 or Path(parts[-1]).suffix not in {'.txt', '.md'}:
        raise Denied('Only new text artifacts are supported.')
    text = args['text']
    if type(text) is not str or len(text.encode('utf-8')) > MAX_FILE or prompt_text(text) != text:
        raise Denied('Unsafe artifact content.')
    return parts


def create_text(root, parts, text):
    parent = open_parent(root, parts)
    try:
        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as handle:
            handle.write(text.encode('utf-8'))
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.close(parent)


def run_action(policy, root, request, approval_path='-', environment='development'):
    if (type(request) is not dict or set(request) not in
            ({'operation', 'arguments'}, {'operation', 'arguments', 'approval_id'})):
        raise Denied('Invalid request schema.')
    operation, args = request['operation'], request['arguments']
    policy.require(operation)
    if type(args) is not dict:
        raise Denied('Invalid arguments.')
    if operation == 'ops.recovery.fixture':
        from igris.guardian.fixture_recovery import recover
        return recover(policy, root, request, Path(approval_path), environment)
    if operation == 'file.create':
        parts = create_parts(args)
        if approval_path == '-':
            raise Denied('Approval required.')
        location = Path(approval_path).resolve(strict=True)
        if location.is_relative_to(root.resolve()):
            raise Denied('Approval store must be outside workspace.')
        store = ApprovalStore(location)
        action = {'operation': operation, 'arguments': args}
        identifier = request.get('approval_id')
        digest = store.consume(identifier, policy, root, action, environment=environment)
        try:
            create_text(root, parts, args['text'])
        except Exception:
            store.outcome(identifier, policy, operation, digest, succeeded=False)
            raise
        store.outcome(identifier, policy, operation, digest, succeeded=True)
        return {'created': args['path']}
    if operation == 'file.read':
        if set(args) != {'path'}:
            raise Denied('Invalid arguments.')
        return {'text': prompt_text(read_text(root, args['path']))}
    if operation == 'python.version':
        if args:
            raise Denied('Arguments are not allowed.')
        child = subprocess.run([sys.executable, '-I', '-S', '--version'], cwd=root,
                               env={'LANG': 'C.UTF-8'}, capture_output=True,
                               timeout=1, check=True, shell=False)
        return {'version': child.stdout.decode('ascii').strip()}
    raise Denied('Operation is not implemented.')


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Denied('Duplicate request key.')
        result[key] = value
    return result


def main():
    try:
        apply_limits()
        if len(sys.argv) != 6:
            raise Denied('Invalid trusted startup.')
        root = Path(sys.argv[1])
        policy = Policy(sys.argv[2], frozenset(Permission(p) for p in sys.argv[3].split(',') if p))
        if sys.argv[5] not in ('development', 'test'):
            raise Denied('Live production execution is unavailable.')
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            raise Denied('Request too large.')
        request = json.loads(raw, object_pairs_hook=_object)
        response = {'ok': True, 'result': run_action(policy, root, request, sys.argv[4], sys.argv[5])}
    except Denied as exc:
        response = {'ok': False, 'reason': str(exc)}
    except Exception:
        response = {'ok': False, 'reason': 'Execution rejected.'}
    sys.stdout.write(json.dumps(response, ensure_ascii=True))


if __name__ == '__main__':
    main()
