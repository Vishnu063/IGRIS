"""Bounded local measurements and reliability assertions; never starts providers."""
from concurrent.futures import ThreadPoolExecutor
import io
import json
import logging
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from igris.controller import MissionController, TaskOutcome
from igris.guardian.approvals import ApprovalStore
from igris.guardian.executor import execute
from igris.guardian.policy import Permission, Policy
from igris.guardian.secrets import RedactingFormatter
from igris.specialists.registry import profile
from igris.specialists.scheduling import SpecialistScheduler


def timed(function, trials=5):
    measurements = []
    for _ in range(trials):
        start = time.perf_counter(); function(); measurements.append(time.perf_counter()-start)
    return {'trials': trials, 'median_seconds': statistics.median(measurements),
            'min_seconds': min(measurements), 'max_seconds': max(measurements)}


def measure():
    start_usage = resource.getrusage(resource.RUSAGE_SELF)
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    def startup():
        code = 'import igris.controller, igris.dashboard, igris.memory, igris.business, igris.specialists.registry'
        subprocess.run([sys.executable, '-c', code], check=True, capture_output=True,
                       env={'PYTHONPATH': str(ROOT/'src'), 'LANG': 'C.UTF-8'}, timeout=3)
    result = {'scope': 'Linux cloud local logic and simulated specialist fixtures only',
        'environment': {'system': platform.system(), 'machine': platform.machine(),
                        'python': platform.python_version(), 'visible_cpus': os.cpu_count()},
        'startup_imports': timed(startup)}
    core = MissionController('owner', {'local': lambda ctx: TaskOutcome('success', 'Local fixed result', 'local', True)})
    def mission():
        m = core.create('Benchmark local mission', 'local')
        assert core.run(m.id).state.value == 'succeeded'
    result['mission_execution'] = timed(mission)
    with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as private:
        root = Path(project); (root/'note.txt').write_text('Benchmark fixture')
        policy = Policy('owner', frozenset({Permission.READ, Permission.SPECIALIST}))
        store = ApprovalStore(Path(private)/'approvals.db', initialize=True)
        read_action = {'operation': 'file.read', 'arguments': {'path': 'note.txt'}}
        def broker_read(): assert execute(policy, root, read_action)['ok']
        result['broker_read'] = timed(broker_read)
        def denial_then_recover():
            assert not execute(Policy('owner'), root, read_action)['ok']
            assert execute(policy, root, read_action)['ok']
        result['denial_then_valid_request'] = timed(denial_then_recover)
        def ready(role):
            scheduler = SpecialistScheduler(policy, root, store)
            rec = scheduler.recommend('a'*32, [{'role': role, 'task': profile(role).task, 'context': 'Synthetic performance fixture'}])
            request = scheduler.request(rec.id)['approval']
            store.decide(request['id'], approve=True, reviewed_digest=request['action_sha256'])
            return scheduler, rec.id, request['id']
        def concurrent_fixture():
            jobs = [ready('frontend'), ready('testing')]
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(s.run, rid, aid) for s, rid, aid in jobs]
                outputs = [future.result(timeout=5) for future in futures]
            assert all(o['ok'] and o['result']['live_models_loaded'] == 0 for o in outputs)
            for s, rid, aid in jobs: assert not s.run(rid, aid)['ok']
        result['two_concurrent_fixture_brokers_with_replay_denials'] = timed(concurrent_fixture, 3)
    def log_batch(redacting):
        output = io.StringIO(); handler = logging.StreamHandler(output)
        handler.setFormatter(RedactingFormatter('%(message)s') if redacting else logging.Formatter('%(message)s'))
        logger = logging.Logger('benchmark'); logger.addHandler(handler)
        for _ in range(1000): logger.warning('Local measured event')
        handler.close()
    result['logging_1000_events_plain'] = timed(lambda: log_batch(False))
    result['logging_1000_events_redacted'] = timed(lambda: log_batch(True))
    record = logging.LogRecord('benchmark', logging.WARNING, '', 0, 'password: synthetic benchmark', (), None)
    assert RedactingFormatter().format(record) == '[REDACTED]'
    usage = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    result['resources'] = {'parent_cpu_seconds': usage.ru_utime+usage.ru_stime-start_usage.ru_utime-start_usage.ru_stime,
        'completed_children_cpu_seconds': children.ru_utime+children.ru_stime-child_start.ru_utime-child_start.ru_stime,
        'parent_peak_rss_kib': usage.ru_maxrss, 'largest_completed_child_peak_rss_kib': children.ru_maxrss,
        'src_bytes': sum(p.stat().st_size for p in (ROOT/'src').rglob('*.py'))}
    result['reliability_assertions'] = {'mission_success': True, 'broker_read': True,
        'denial_does_not_poison_next_valid_request': True, 'two_concurrent_simulations': True,
        'replays_denied': True, 'redaction_retained': True}
    result['mac_m1_verified'] = False
    return result


if __name__ == '__main__': print(json.dumps(measure(), indent=2, sort_keys=True))
