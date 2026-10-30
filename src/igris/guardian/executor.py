"""Trusted launcher for a bounded, independent execution broker.

This is not same-user OS containment. Never expose launch parameters to agents.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from .policy import Denied, Policy

MAX_REQUEST = 16384
WALL_TIMEOUT = 3


def execute(policy: Policy, workspace: Path, request: dict, *, approval_store: Path | None = None,
            environment='development') -> dict:
    """Trusted caller supplies policy/workspace; only request is untrusted."""
    try:
        payload = json.dumps(request, allow_nan=False).encode()
        if len(payload) > MAX_REQUEST:
            raise Denied('Request too large.')
        root = Path(workspace).resolve(strict=True)
        if not root.is_dir() or root == Path('/'):
            raise Denied('Invalid workspace.')
        if environment not in ('development', 'test'):
            raise Denied('Live production execution is unavailable.')
        store = '-'
        if approval_store is not None:
            location = Path(approval_store).resolve(strict=True)
            if location.is_relative_to(root):
                raise Denied('Approval store must be outside workspace.')
            store = str(location)
        broker = Path(__file__).with_name('broker.py').resolve()
        command = [sys.executable, '-I', '-S', str(broker), str(root), policy.actor,
                   ','.join(sorted(p.value for p in policy.permissions)), store, environment]
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, cwd=root, env={'LANG': 'C.UTF-8'},
                                start_new_session=True)
        try:
            output, _ = proc.communicate(payload, timeout=WALL_TIMEOUT)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            return {'ok': False, 'reason': 'Execution timeout.'}
        if proc.returncode or len(output) > 32768:
            return {'ok': False, 'reason': 'Broker failed.'}
        result = json.loads(output)
        if type(result) is not dict or type(result.get('ok')) is not bool:
            return {'ok': False, 'reason': 'Invalid broker response.'}
        return result
    except (OSError, ValueError, TypeError, RecursionError):
        return {'ok': False, 'reason': 'Execution rejected.'}
