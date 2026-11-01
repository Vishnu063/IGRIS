"""Explicit one-shot cloud acceptance probe. Never installs or starts on import."""
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from igris.guardian.secrets import findings, redact


def record_outcome(payload):
    runtime = ROOT/'runtime'
    if sys.platform != 'linux' or not runtime.is_dir(): return
    with tempfile.NamedTemporaryFile('w', dir=runtime, encoding='utf-8', delete=False) as handle:
        json.dump(payload, handle, sort_keys=True, indent=2)
        handle.write('\n')
        temporary = Path(handle.name)
    temporary.replace(runtime/'hermes-inference-evidence.json')


def main():
    if len(sys.argv) != 1 or sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise SystemExit('Manual Linux cloud probe only; no arguments accepted.')
    runtime = ROOT/'runtime'
    record_outcome({'status': 'RUNNING', 'origin': 'not_yet_verified'})
    profile = json.loads((ROOT/'integrations/hermes-inference/profile.json').read_text())
    if profile['enabled_tools'] != [] or profile['authorized_spend_inr'] != 0:
        raise SystemExit('Only zero-budget reasoning-only profile supported.')
    assets = [('cpython3149.tar.gz', profile['python_archive_sha256']),
              ('llama-b11960.tar.gz', profile['engine_archive_sha256']),
              (profile['model_file'], profile['model_sha256'])]
    for name, expected in assets:
        path = runtime/name
        if path.is_symlink() or not path.resolve().is_relative_to(runtime.resolve()):
            raise SystemExit('Unsafe local asset path.')
        digest = hashlib.sha256()
        with path.open('rb') as source:
            while chunk := source.read(1024*1024): digest.update(chunk)
        if digest.hexdigest() != expected: raise SystemExit('Local asset integrity mismatch.')
    # Validate all copied framework source before executing its real runtime.
    source_manifest = json.loads((ROOT/'docs/integrations/hermes-source-manifest.json').read_text())
    for name, expected in source_manifest['local_sha256'].items():
        path = ROOT/'vendor/hermes-agent'/name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Copied Hermes source changed; review before running.')
    docker = shutil.which('docker')
    if not docker: raise SystemExit('Managed Docker required; no unsandboxed fallback.')
    environment = {k:v for k,v in os.environ.items() if k not in (
        'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}
    base = [docker, '--host=unix:///var/run/docker.sock']
    subprocess.run(base+['image', 'inspect', profile['container_image']], env=environment,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=10)
    name = 'igris-hermes-probe-'+uuid4().hex[:12]
    args = base+['run', '--rm', '--pull=never', '--name', name, '--network', 'none',
        '--read-only', '--user', f'{os.getuid()}:{os.getgid()}', '--cap-drop', 'ALL',
        '--security-opt', 'no-new-privileges', '--pids-limit', '128', '--memory', '3g',
        '--cpus', '2', '--tmpfs', '/tmp:rw,noexec,nosuid,size=268435456,mode=1777',
        '--workdir', '/tmp', '--env', 'HOME=/tmp/igris-home',
        '--env', 'HERMES_HOME=/tmp/igris-home/hermes',
        '--env', 'HERMES_DISABLE_LAZY_INSTALLS=1', '--env', 'PYTHONDONTWRITEBYTECODE=1',
        '--env', 'NO_PROXY=127.0.0.1,localhost']
    mounts = ('runtime/python3149', 'runtime/hermes-venv', 'runtime/llama-b11960',
              'runtime/'+profile['model_file'], 'vendor/hermes-agent', 'src/igris',
              'integrations/hermes-inference/profile.json', 'scripts/hermes_inference_worker.py')
    for relative in mounts:
        path = ROOT/relative
        if not path.exists() or path.is_symlink(): raise SystemExit('Missing/unsafe probe mount.')
        args.extend(['--mount', f'type=bind,src={path},dst={path},readonly'])
    args.extend([profile['container_image'], str(ROOT/'runtime/hermes-venv/bin/python'),
                 '-I', str(ROOT/'scripts/hermes_inference_worker.py')])
    # Full output stays private; only the checked final evidence object is shown.
    with tempfile.TemporaryFile(dir=runtime) as output:
        try:
            process = subprocess.run(args, env=environment, stdout=output,
                                     stderr=subprocess.STDOUT, timeout=180)
        finally:
            subprocess.run(base+['rm', '--force', name], env=environment,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            remaining = subprocess.run(base+['container', 'ls', '--all', '--filter',
                'name=^/'+name+'$', '--format', '{{.ID}}'], env=environment,
                capture_output=True, text=True, check=True, timeout=10)
            if remaining.stdout.strip(): raise RuntimeError('Probe container cleanup not verified.')
        output.seek(0, 2)
        length = output.tell()
        output.seek(max(0, length-65536))
        raw = output.read().decode('utf-8', errors='replace')
    if process.returncode:
        # Synthetic probe only; retain safe diagnostics without printing credentials.
        diagnostic = runtime/'hermes-inference-failure.log'
        with diagnostic.open('w') as handle: handle.write('\n'.join(redact(line) for line in raw.splitlines()))
        diagnostic.chmod(0o600)
        raise SystemExit('Real inference probe failed; private diagnostic: runtime/hermes-inference-failure.log')
    evidence = None
    for line in reversed(raw.splitlines()):
        try: candidate = json.loads(line)
        except ValueError: continue
        if type(candidate) is dict and candidate.get('origin') == 'real_local_inference':
            evidence = candidate; break
    if evidence is None or evidence.get('status') != 'PASS': raise SystemExit('No verified live inference evidence.')
    if evidence.get('model_sha256') != profile['model_sha256']: raise SystemExit('Evidence model identity mismatch.')
    evidence['container_removed'] = True
    evidence['image'] = profile['container_image']
    evidence['profile_sha256'] = hashlib.sha256((ROOT/'integrations/hermes-inference/profile.json').read_bytes()).hexdigest()
    evidence['worker_sha256'] = hashlib.sha256((ROOT/'scripts/hermes_inference_worker.py').read_bytes()).hexdigest()
    evidence['verified_at_utc'] = datetime.now(timezone.utc).isoformat()
    serialized = json.dumps(evidence, indent=2, sort_keys=True)
    if findings(serialized): raise SystemExit('Evidence needs credential-pattern review; nothing published.')
    record_outcome(evidence)
    print(serialized)


def run():
    try: main()
    except (Exception, SystemExit, KeyboardInterrupt) as exc:
        record_outcome({'status': 'STOPPED' if isinstance(exc, KeyboardInterrupt) else 'FAIL',
                        'origin': 'not_verified', 'error_class': type(exc).__name__})
        raise


if __name__ == '__main__': run()
