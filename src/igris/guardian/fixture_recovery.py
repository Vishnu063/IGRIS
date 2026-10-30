"""Guardian-side recovery SIMULATOR. Never invokes Docker, HTTP or provider code."""
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import time
from uuid import uuid4

from .approvals import ApprovalStore
from .policy import Denied


def _regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
        raise Denied('Private regular fixture file required.')


def _parse(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise Denied('Duplicate fixture key.')
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs)


def _validate(state, args):
    expected = {'simulation', 'context', 'container_id', 'daemon_id', 'health_url', 'container_state',
                'maintenance', 'plan', 'scenario', 'healthy', 'dispatch_count'}
    if type(state) is not dict or set(state) != expected or state['simulation'] is not True:
        raise Denied('Explicit simulation fixture required.')
    if any(state[k] != args[k] for k in ('context', 'container_id', 'daemon_id', 'health_url')):
        raise Denied('Fixture target identity changed.')
    if (state['maintenance'] is not False or state['container_state'] not in ('exited', 'stopped', 'dead', 'restarting')
            or state['healthy'] is not False or type(state['dispatch_count']) is not int or state['dispatch_count'] != 0):
        raise Denied('Recovery preconditions are not satisfied.')
    plan = state['plan']
    if type(plan) is not dict or set(plan) != {'id', 'approved', 'used', 'expires_at', 'command'}:
        raise Denied('Invalid provider fixture plan.')
    if plan['id'] != args['plan_id'] or plan['approved'] is not True or plan['used'] is not False:
        raise Denied('Separate unused provider-fixture approval required.')
    expiry = plan['expires_at']
    if type(expiry) not in (int, float) or not math.isfinite(expiry) or not time.time() < expiry <= time.time() + 300:
        raise Denied('Provider fixture plan expired or invalid.')
    # Audited command shape is DATA ONLY and is never executed by this module.
    expected_command = ['docker', '--context', args['context'], 'container', 'restart', '--time', '10', args['container_id']]
    if plan['command'] != expected_command:
        raise Denied('Provider fixture operation changed.')
    if state['scenario'] not in ('success', 'health_failure', 'dispatch_failure', 'unknown_outcome'):
        raise Denied('Unsupported simulator scenario.')


def recover(policy, root, request, approval_path, environment):
    policy.require('ops.recovery.fixture')
    policy.require('file.read')
    policy.require('file.create')
    args = request['arguments']
    if set(args) != {'plan_id', 'state_sha256', 'context', 'container_id', 'daemon_id', 'health_url'}:
        raise Denied('Invalid recovery arguments.')
    for key, pattern in (('plan_id', r'[a-f0-9]{32}'), ('state_sha256', r'[a-f0-9]{64}'),
                         ('context', r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}'), ('container_id', r'[a-f0-9]{64}'),
                         ('daemon_id', r'[A-Za-z0-9_.:-]{1,100}')):
        if type(args[key]) is not str or not re.fullmatch(pattern, args[key]):
            raise Denied('Invalid fixture target argument.')
    # The simulator never probes this URL; constrain it anyway to an explicit
    # local fixture identity, without credentials, path tokens or query data.
    if type(args['health_url']) is not str or not re.fullmatch(r'http://127\.0\.0\.1:[1-9][0-9]{0,4}/', args['health_url']):
        raise Denied('Only a local simulated health target is supported.')
    if int(args['health_url'].rsplit(':', 1)[1][:-1]) > 65535:
        raise Denied('Invalid simulated health port.')
    if str(approval_path) == '-':
        raise Denied('Guardian approval required.')
    location = approval_path.resolve(strict=True)
    if location.is_relative_to(root.resolve()):
        raise Denied('Approval store must be outside workspace.')
    store = ApprovalStore(location)
    # Reuse descriptor-based no-follow traversal; fixture files/lock must be
    # initialized explicitly by a trusted test operator, never by a request.
    from .broker import open_parent
    parent = open_parent(root, ['fixtures', 'ops-state.json'])
    lock = None
    try:
        lock = os.open('ops.lock', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        _regular(lock)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd = os.open('ops-state.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as handle:
            _regular(handle.fileno())
            raw = handle.read(8193)
        if len(raw) > 8192 or hashlib.sha256(raw).hexdigest() != args['state_sha256']:
            raise Denied('Fixture evidence changed or exceeds bounds.')
        state = _parse(raw)
        _validate(state, args)
        action = {'operation': 'ops.recovery.fixture', 'arguments': args}
        identifier = request.get('approval_id')
        digest = store.consume(identifier, policy, root, action, environment=environment)
        try:
            # Recheck provider expiry after possible approval-store lock waiting.
            if time.time() >= state['plan']['expires_at']:
                raise Denied('Provider fixture plan expired before dispatch.')
            state['plan']['used'] = True
            state['dispatch_count'] = 1
            scenario = state['scenario']
            if scenario in ('success', 'health_failure'):
                state['container_state'] = 'running'
                state['healthy'] = scenario == 'success'
            status = {'success': 'verified', 'health_failure': 'needs_attention',
                      'dispatch_failure': 'failed', 'unknown_outcome': 'unknown'}[scenario]
            encoded = json.dumps(state, sort_keys=True, allow_nan=False).encode()
            temporary = 'ops-' + uuid4().hex + '.tmp'
            try:
                out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                with os.fdopen(out, 'wb') as handle:
                    handle.write(encoded)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, 'ops-state.json', src_dir_fd=parent, dst_dir_fd=parent)
                os.fsync(parent)
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
            # Verify actual saved fixture content, not just the dispatch return.
            check_fd = os.open('ops-state.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(check_fd, 'rb') as handle:
                _regular(handle.fileno())
                actual = _parse(handle.read(8193))
            verified = (status == 'verified' and actual['container_state'] == 'running' and actual['healthy'] is True
                        and actual['container_id'] == args['container_id'] and actual['daemon_id'] == args['daemon_id'])
            if status == 'verified' and not verified:
                status = 'needs_attention'
            store.outcome(identifier, policy, action['operation'], digest, succeeded=verified)
            return {'origin': 'simulated', 'status': status, 'verified': verified,
                    'container_running': actual['container_state'] == 'running',
                    'application_healthy': actual['healthy'] if status not in ('failed', 'unknown') else None,
                    'retry_allowed': False, 'plan_id': args['plan_id'],
                    'reason': {'verified': 'Simulated state and endpoint checks passed.',
                               'needs_attention': 'Simulated endpoint/state verification failed.',
                               'failed': 'Simulated dispatch failed; inspect fixture state.',
                               'unknown': 'Simulated outcome unknown; reconcile before new approval.'}[status]}
        except Exception:
            store.outcome(identifier, policy, action['operation'], digest, succeeded=False)
            raise
    finally:
        if lock is not None:
            os.close(lock)
        os.close(parent)
