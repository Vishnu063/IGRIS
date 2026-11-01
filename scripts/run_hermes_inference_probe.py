"""Explicit one-shot cloud acceptance probe. Never installs or starts on import."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from igris.guardian.secrets import findings


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
    from igris.adapters.hermes_chat import DockerHermesAdapter
    evidence = DockerHermesAdapter(root=ROOT).probe()
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
