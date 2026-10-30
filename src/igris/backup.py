"""Fixed-format private development snapshots; no credentials or approvals."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import zipfile

from .config import Settings
from .guardian.policy import Denied
from .guardian.secrets import redact
from .memory import CATEGORIES, Memory, knowledge_text, private_file

NAMES = frozenset({'configuration.json', 'project-state.json', 'memory.db'})
MAX_BYTES = 4 * 1024 * 1024


def _json(data): return json.dumps(data, sort_keys=True, allow_nan=False).encode()


def _state(data):
    if type(data) is not dict or not set(data) <= {'projects', 'missions', 'business'}:
        raise ValueError('Only non-executable project state may be backed up.')
    for rows in data.values():
        if type(rows) is not list or len(rows) > 200: raise ValueError('Invalid state rows.')
        for row in rows:
            if type(row) is not dict or set(row) != {'id', 'state', 'origin'}:
                raise ValueError('Only state references, never approvals or action bodies.')
            if type(row['id']) is not str or not re.fullmatch('[a-f0-9]{32}', row['id']) or row['origin'] not in ('simulated', 'operator_recorded'):
                raise ValueError('Invalid state origin/reference.')
            knowledge_text(row['state'], 80)
    return data


def _configuration(data):
    if type(data) is not dict or set(data) != {'profile', 'bind_host', 'budget_inr', 'log_level', 'features'}:
        raise ValueError('Invalid safe configuration.')
    if data['profile'] not in ('test', 'development') or data['bind_host'] != '127.0.0.1' or type(data['budget_inr']) is not int or data['budget_inr'] != 0:
        raise ValueError('Unsafe restored configuration.')
    if data['log_level'] not in ('INFO', 'WARNING', 'ERROR', 'CRITICAL') or type(data['features']) is not dict or set(data['features']) != {'hermes', 'n8n', 'ops_pilot', 'specialists', 'voice', 'dashboard', 'business'} or any(v is not False for v in data['features'].values()):
        raise ValueError('Restored integrations must remain disabled.')
    return data


def _memory_check(data):
    # Validate actual SQLite in a disposable private file; no extension loading.
    with tempfile.TemporaryDirectory() as directory:
        path = private_file(Path(directory)/'memory.db', create=True); path.write_bytes(data)
        db = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
        try:
            db.execute('PRAGMA trusted_schema=OFF')
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Corrupt memory snapshot.')
            schema = db.execute("SELECT type,name,tbl_name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
            if schema != [('table', 'knowledge', 'knowledge')]: raise ValueError('Unsupported memory schema.')
            columns = [r[1] for r in db.execute('PRAGMA table_info(knowledge)')]
            if columns != ['id', 'category', 'text', 'classification', 'evidence', 'revision']: raise ValueError('Unsupported memory columns.')
            rows = db.execute('SELECT * FROM knowledge LIMIT 10001').fetchall()
            if len(rows) > 10000: raise ValueError('Memory snapshot too large.')
            for ident, category, text, classification, evidence, revision in rows:
                if type(ident) is not str or not re.fullmatch('[a-f0-9]{32}', ident) or category not in CATEGORIES or classification not in ('assumption', 'verified_fact') or type(revision) is not int or revision < 1:
                    raise ValueError('Invalid memory record.')
                knowledge_text(text)
                if evidence or classification == 'verified_fact': knowledge_text(evidence, 512)
        finally: db.close()


def create_backup(destination, *, settings, state, memory, actor):
    if type(settings) is not Settings or type(memory) is not Memory: raise ValueError('Trusted local components required.')
    entries = {'configuration.json': _json(_configuration(asdict(settings))),
               'project-state.json': _json(_state(state))}
    with tempfile.TemporaryDirectory() as directory:
        path = memory.backup(actor, Path(directory)/'memory.db')
        entries['memory.db'] = path.read_bytes()
    if any(len(data) > MAX_BYTES for data in entries.values()): raise ValueError('Backup capacity exceeded.')
    _memory_check(entries['memory.db'])
    manifest = {'schema_version': 1, 'files': {n: hashlib.sha256(d).hexdigest() for n, d in entries.items()}}
    entries['manifest.json'] = _json(manifest)
    target = private_file(destination, create=True)
    try:
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries.items(): archive.writestr(name, data)
    except Exception:
        target.unlink(); raise
    return {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'kind': 'development_state', 'credentials_included': False}


def restore_backup(archive_path, destination, *, expected_sha256, environment='development'):
    if environment not in ('development', 'test'): raise Denied('Production restoration unavailable.')
    path = private_file(archive_path)
    if path.stat().st_size > MAX_BYTES * 4 or type(expected_sha256) is not str or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError('Backup identity verification failed.')
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != 4 or {i.filename for i in infos} != NAMES | {'manifest.json'} or any(i.file_size > MAX_BYTES for i in infos):
            raise ValueError('Unsupported backup entries.')
        entries = {name: archive.read(name) for name in NAMES}
        manifest = json.loads(archive.read('manifest.json'))
    if type(manifest) is not dict or set(manifest) != {'schema_version', 'files'} or manifest['schema_version'] != 1 or manifest['files'] != {n: hashlib.sha256(d).hexdigest() for n, d in entries.items()}:
        raise ValueError('Backup content verification failed.')
    _configuration(json.loads(entries['configuration.json'])); _state(json.loads(entries['project-state.json']))
    _memory_check(entries['memory.db'])
    target = Path(destination).absolute()
    parent = target.parent
    if parent.resolve(strict=True) != parent or parent.stat().st_uid != os.getuid() or parent.stat().st_mode & 0o077:
        raise Denied('Restore parent must be private and trusted.')
    target.mkdir(mode=0o700)  # Never overwrite a live directory.
    try:
        for name, data in entries.items(): private_file(target/name, create=True).write_bytes(data)
    except Exception:
        shutil.rmtree(target); raise
    return {'restored': True, 'location': str(target), 'execution_resumed': False}


def rollback_plan(version, artifact_sha256):
    if type(version) is not str or not re.fullmatch('[a-f0-9]{40}', version) or type(artifact_sha256) is not str or not re.fullmatch('[a-f0-9]{64}', artifact_sha256):
        raise ValueError('Exact prior version and artifact required.')
    return {'version': version, 'artifact_sha256': artifact_sha256,
            'approval_required': True, 'production_execution_available': False,
            'checks': ['Review rollback impact', 'Review data compatibility', 'Obtain exact owner approval', 'Verify health after separately authorized execution']}
