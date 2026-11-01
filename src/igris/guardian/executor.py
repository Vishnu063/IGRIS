"""Trusted launcher for a bounded, independent execution broker.

This is not same-user OS containment. Never expose launch parameters to agents.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .policy import Denied, Policy

MAX_REQUEST = 16384
WALL_TIMEOUT = 3


def _kill_group(proc):
    try: os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError: pass  # Child may have exited between poll and kill.


def execute(policy: Policy, workspace: Path, request: dict, *, approval_store: Path | None = None,
            environment='development', tool_config: Path | None = None, prepare=False) -> dict:
    """Trusted caller supplies policy/workspace; only request is untrusted."""
    try:
        started = time.monotonic()
        if type(request) is not dict:
            raise Denied('Typed request envelope required.')
        if type(prepare) is not bool or (prepare and tool_config is None):
            raise Denied('Preparation requires a trusted tools-only profile.')
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
        if tool_config is not None:
            from .readonly import ToolScope
            config = Path(tool_config).absolute()
            scope = ToolScope.load(config)
            if scope.workspace != root or approval_store is None: raise Denied('Trusted tools-only scope/store required.')
            # Do not resolve away symlinks before private-store validation.
            from .approvals import ApprovalStore
            ApprovalStore(Path(approval_store).absolute())
            command[7] = str(Path(approval_store).absolute())
            command.append(str(config))
            if prepare: command.append('prepare')
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, cwd=root, env={'LANG': 'C.UTF-8'},
                                start_new_session=True)
        try:
            output, _ = proc.communicate(payload, timeout=WALL_TIMEOUT)
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            proc.communicate()
            if tool_config is not None:
                ApprovalStore(Path(approval_store)).tool_event(policy, request.get('request_id'), request.get('mission_id'), 'unregistered','unavailable','timeout')
            return {'ok': False, 'reason': 'Execution timeout.'}
        except BaseException:
            if proc.poll() is None:
                _kill_group(proc)
            proc.communicate()
            if tool_config is not None:
                try:
                    ApprovalStore(Path(approval_store)).tool_event(policy, request.get('request_id'), request.get('mission_id'), 'unregistered','unavailable','interrupted')
                except Exception: pass  # Preserve cancellation; never report successful execution.
            raise
        if proc.returncode or len(output) > 32768:
            if tool_config is not None:
                ApprovalStore(Path(approval_store)).tool_event(policy, request.get('request_id'), request.get('mission_id'), 'unregistered','unavailable','broker_failed')
            return {'ok': False, 'reason': 'Broker failed.'}
        result = json.loads(output)
        if type(result) is not dict or type(result.get('ok')) is not bool:
            return {'ok': False, 'reason': 'Invalid broker response.'}
        if tool_config is not None: result['broker_wall_ms'] = (time.monotonic()-started)*1000
        return result
    except (OSError, ValueError, TypeError, RecursionError):
        if tool_config is not None and approval_store is not None:
            try:
                from .approvals import ApprovalStore
                details = request if type(request) is dict else {}
                ApprovalStore(Path(approval_store)).tool_event(policy,details.get('request_id'),details.get('mission_id'),'unregistered','unavailable','denied')
            except Exception: pass  # No execution if required audit storage is unavailable.
        return {'ok': False, 'reason': 'Execution rejected.'}
