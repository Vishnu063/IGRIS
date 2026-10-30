"""Map audited Ops Pilot exports; no raw logs, cloud calls or recovery transport."""
from dataclasses import dataclass
import hashlib
import http.client
import json
import math
import re
import time
from urllib.parse import urlsplit

from .contracts import AdapterUnavailable, ContractError


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class TargetBinding:
    container: str
    context: str
    health_url: str

    def __post_init__(self):
        if any(type(v) is not str or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', v) for v in (self.container, self.context)):
            raise ContractError('Invalid configured target.')
        parsed = urlsplit(self.health_url)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment
                or (parsed.scheme == 'http' and parsed.hostname not in ('127.0.0.1', 'localhost', '::1'))):
            raise ContractError('Invalid configured health URL.')


@dataclass(frozen=True)
class Monitoring:
    binding: TargetBinding
    origin: str
    digest: str
    generated_at: float
    health: str
    container_state: str
    container_id: str | None
    daemon_id: str | None
    oom_killed: bool | None
    exit_code: int | None
    restart_count: int | None
    signals: tuple[tuple[str, int], ...]
    issues: tuple[str, ...]
    restart_offered: bool
    maintenance_active: bool

    def ref(self, path):
        return 'ops-export:' + self.digest + ':' + path


def parse_export(raw, binding, *, origin='provided_export', now=None):
    if origin not in ('provided_export', 'simulated') or type(raw) is not dict:
        raise ContractError('Invalid evidence source.')
    try:
        encoded = json.dumps(raw, sort_keys=True, allow_nan=False).encode()
    except (ValueError, TypeError, RecursionError):
        raise ContractError('Invalid export JSON.') from None
    if len(encoded) > 65536:
        raise ContractError('Export exceeds size limit.')
    if type(raw.get('schema_version')) is not int or raw['schema_version'] != 1:
        raise ContractError('Unsupported export schema.')
    if any(raw.get(k) != v for k, v in (('container', binding.container), ('context', binding.context), ('health_url', binding.health_url))):
        raise ContractError('Export target mismatch.')
    now = time.time() if now is None else now
    def fresh(value):
        return _number(value) and _number(now) and -5 <= now - value <= 300
    if not fresh(raw.get('generated_at')):
        raise ContractError('Export is stale or has an invalid timestamp.')
    monitor, report = raw.get('monitor'), raw.get('report')
    if type(monitor) is not dict or type(report) is not dict:
        raise ContractError('Monitoring or investigation evidence is unavailable.')
    snapshot = report.get('snapshot')
    if type(snapshot) is not dict or type(snapshot.get('observations')) is not dict:
        raise ContractError('Invalid investigation snapshot.')
    errors = snapshot.get('errors', [])
    if type(errors) is not list or len(errors) > 32:
        raise ContractError('Invalid collection errors.')
    issues = []
    maintenance = raw.get('maintenance_until')
    maintenance_active = not _number(maintenance) or maintenance > now
    if not _number(maintenance):
        issues.append('maintenance_state_unknown')
    if monitor.get('enabled') is False:
        issues.append('monitor_disabled')
    health = 'unknown'
    if fresh(monitor.get('checked_at')) and type(monitor.get('healthy')) is bool and not monitor.get('error'):
        health = 'healthy' if monitor['healthy'] else 'unhealthy'
    else:
        issues.append('health_unavailable_or_stale')
    observations = snapshot['observations']
    def one(key):
        value = observations.get(key)
        return value[0] if type(value) is list and len(value) == 1 else None
    state, cid, daemon, oom, code, count = (one(k) for k in ('state', 'id', 'daemon_id', 'oom', 'exit_code', 'restart_count'))
    if state not in ('running', 'exited', 'stopped', 'dead', 'restarting', 'created', 'paused'):
        state = 'unknown'
    if type(cid) is not str or not re.fullmatch(r'[a-f0-9]{64}', cid):
        cid = None
    if type(daemon) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,200}', daemon):
        daemon = None
    if type(oom) is not bool:
        oom = None
    if type(code) is not int or not 0 <= code <= 255:
        code = None
    if type(count) is not int or not 0 <= count <= 1000000:
        count = None
    if errors or not fresh(snapshot.get('collected_at')):
        issues.append('container_evidence_incomplete_or_stale')
        state, cid, daemon, oom, code, count = 'unknown', None, None, None, None, None
    deep = report.get('deep_evidence', {})
    if type(deep) is not dict or type(deep.get('log_signals', {})) is not dict:
        raise ContractError('Invalid filtered log evidence.')
    signals = []
    for key, value in deep.get('log_signals', {}).items():
        if key not in ('memory', 'disk', 'dns', 'dependency', 'timeout', 'authorization', 'image') or type(value) is not int or not 0 <= value <= 1000000:
            raise ContractError('Invalid log signature count.')
        signals.append((key, value))
    if deep.get('errors') or not fresh(snapshot.get('collected_at')):
        issues.append('log_evidence_incomplete_or_stale')
        signals = []
    actions = report.get('actions', [])
    if type(actions) is not list or len(actions) > 8:
        raise ContractError('Invalid supported-action evidence.')
    offered = any(type(item) is dict and item.get('id') == 'restart' for item in actions)
    return Monitoring(binding, origin, hashlib.sha256(encoded).hexdigest(), raw['generated_at'], health,
                      state, cid, daemon, oom, code, count, tuple(sorted(signals)), tuple(issues), offered, maintenance_active)


class OpsMonitoringAdapter:
    def __init__(self, binding, transport=None):
        self.binding, self.transport = binding, transport

    def inspect(self):
        if self.transport is None:
            raise AdapterUnavailable('Ops Pilot monitoring is disabled.')
        return parse_export(self.transport.read_report(), self.binding, origin=self.transport.origin)


class LocalReportTransport:
    """Explicit contract fixture only; cookie supplied by trusted test launcher."""
    origin = 'simulated'

    def __init__(self, endpoint, session):
        url = urlsplit(endpoint)
        if (url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port or url.path != '/api/report'
                or url.query or url.fragment or url.username or url.password):
            raise ContractError('Only the local report contract endpoint is supported.')
        if type(session) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', session):
            raise ContractError('Private owner session required.')
        self._port, self._session = url.port, session

    def read_report(self):
        conn = http.client.HTTPConnection('127.0.0.1', self._port, timeout=1)
        try:
            conn.request('GET', '/api/report', headers={'Cookie': 'ops_pilot=' + self._session})
            response = conn.getresponse()
            if response.status != 200 or response.getheader('Content-Type', '').split(';')[0] != 'application/json':
                raise ContractError('Ops Pilot report request rejected.')
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ContractError('Report response exceeds limit.')
            def object_pairs(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ContractError('Duplicate report key.')
                    result[key] = value
                return result
            return json.loads(raw, object_pairs_hook=object_pairs)
        except (OSError, http.client.HTTPException):
            raise AdapterUnavailable('Ops Pilot report transport failed.') from None
        except (ValueError, RecursionError):
            raise ContractError('Invalid report response.') from None
        finally:
            conn.close()
