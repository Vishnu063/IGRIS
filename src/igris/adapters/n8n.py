"""Authenticated loopback contract client. Live n8n activation is unsupported."""
from collections import deque
from dataclasses import dataclass
import hashlib
import http.client
import json
import logging
import re
from urllib.parse import urlsplit

from .contracts import AdapterUnavailable, ContractError, identifier, safe_text


@dataclass(frozen=True)
class WorkflowRequest:
    mission_id: str
    application: str

    def __post_init__(self):
        identifier(self.mission_id)
        if type(self.application) is not str or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', self.application):
            raise ContractError('Invalid fixture application.')

    def payload(self):
        return {'schema_version': 1, 'mission_id': self.mission_id,
                'workflow': 'inspect_fixture', 'input': {'application': self.application}}


@dataclass(frozen=True)
class WorkflowResult:
    mission_id: str
    status: str
    summary: str
    origin: str = 'simulated'


def parse_response(raw, request):
    if type(raw) is not dict or set(raw) != {'schema_version', 'mission_id', 'workflow', 'status', 'output'}:
        raise ContractError('Invalid workflow response schema.')
    if type(raw['schema_version']) is not int or raw['schema_version'] != 1:
        raise ContractError('Unsupported workflow schema.')
    if raw['mission_id'] != request.mission_id or raw['workflow'] != 'inspect_fixture':
        raise ContractError('Workflow correlation mismatch.')
    if raw['status'] not in ('completed', 'failed') or type(raw['output']) is not dict or set(raw['output']) != {'summary'}:
        raise ContractError('Invalid workflow outcome.')
    return WorkflowResult(request.mission_id, raw['status'], safe_text(raw['output']['summary'], 1024))


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError('Duplicate workflow response key.')
        result[key] = value
    return result


class N8nAdapter:
    def __init__(self, endpoint=None, secret=None, *, mode='disabled', timeout=1, retries=1):
        self._events = deque(maxlen=128)
        self._enabled = mode == 'local_contract'
        if mode not in ('disabled', 'local_contract'):
            raise AdapterUnavailable('Live n8n integration is not verified.')
        if not self._enabled:
            return
        if type(endpoint) is not str:
            raise ContractError('Invalid trusted workflow endpoint.')
        try:
            url = urlsplit(endpoint)
            port = url.port
        except (TypeError, ValueError):
            raise ContractError('Invalid trusted workflow endpoint.') from None
        if (url.scheme != 'http' or url.hostname != '127.0.0.1' or not port or
                url.path != '/webhook/igris-readonly' or url.query or url.fragment or url.username or url.password):
            raise ContractError('Only the isolated loopback contract endpoint is supported.')
        if type(secret) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{24,128}', secret):
            raise ContractError('Workflow authentication is required.')
        if type(timeout) not in (int, float) or not 0 < timeout <= 3 or type(retries) is not int or not 0 <= retries <= 2:
            raise ContractError('Invalid workflow I/O limits.')
        self._port, self._secret, self._timeout, self._retries = port, secret, timeout, retries

    @property
    def events(self):
        return tuple(self._events)

    def run(self, request):
        if not self._enabled:
            raise AdapterUnavailable('n8n is disabled; no connection was attempted.')
        if type(request) is not WorkflowRequest:
            raise ContractError('Invalid workflow request.')
        body = json.dumps(request.payload(), sort_keys=True, separators=(',', ':')).encode()
        key = hashlib.sha256(body).hexdigest()
        for attempt in range(self._retries + 1):
            status = 'transport_failed'
            conn = http.client.HTTPConnection('127.0.0.1', self._port, timeout=self._timeout)
            try:
                conn.request('POST', '/webhook/igris-readonly', body, {
                    'Content-Type': 'application/json', 'X-IGRIS-Key': self._secret,
                    'Idempotency-Key': key})
                response = conn.getresponse()
                status = str(response.status)
                if response.status in (502, 503, 504):
                    if attempt < self._retries:
                        continue
                    raise AdapterUnavailable('Workflow retry limit reached.')
                if response.status != 200:
                    raise ContractError('Workflow HTTP request rejected.')
                if response.getheader('Content-Type', '').split(';')[0].strip() != 'application/json':
                    raise ContractError('Workflow response must be JSON.')
                raw = response.read(16385)
                if len(raw) > 16384:
                    raise ContractError('Workflow response exceeds limit.')
                try:
                    parsed = json.loads(raw, object_pairs_hook=_object)
                except (ValueError, RecursionError):
                    raise ContractError('Invalid workflow JSON.') from None
                return parse_response(parsed, request)
            except (OSError, http.client.HTTPException):
                if attempt == self._retries:
                    raise AdapterUnavailable('Workflow transport failed or timed out.') from None
            finally:
                conn.close()
                event = (request.mission_id, attempt + 1, status)
                self._events.append(event)
                logging.getLogger('igris.adapters.n8n').info('workflow_attempt %s %s %s', *event)
        raise AdapterUnavailable('Workflow unavailable.')
