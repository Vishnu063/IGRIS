"""Explicit, real CPU acceptance test. Disposable synthetic data; no mock backend."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from igris.conversations import ConversationMemory
from igris.guardian.policy import Denied
from igris.guardian.secrets import findings


def record(payload):
    with tempfile.NamedTemporaryFile('w', dir=ROOT/'runtime', encoding='utf-8', delete=False) as target:
        json.dump(payload, target, indent=2, sort_keys=True); target.write('\n')
        path = Path(target.name)
    path.replace(ROOT/'runtime/chat-live-evidence.json')


def main():
    if len(sys.argv) != 1 or platform.system() != 'Linux': raise ValueError('Explicit cloud acceptance only.')
    record({'status': 'RUNNING', 'origin': 'not_yet_verified'})
    env = dict(os.environ, PYTHONPATH=str(ROOT/'src'))
    docker_env = {key: value for key, value in env.items() if key not in ('DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH')}
    docker = ['docker', '--host=unix:///var/run/docker.sock']
    model_sha = json.loads((ROOT/'integrations/hermes-inference/profile.json').read_text())['model_sha256']
    observed = []
    with tempfile.TemporaryDirectory(prefix='chat-live-', dir=ROOT/'runtime') as directory:
        state = Path(directory)
        command = [sys.executable, '-m', 'igris.chat', '--remember', '--state-dir', directory, '--once', '--json']

        def turn(prompt, conversation=None):
            started = time.monotonic()
            args = command + (['--session', conversation] if conversation else [])
            result = subprocess.run(args, input=prompt, text=True, capture_output=True, env=env, cwd=ROOT, timeout=210)
            if result.returncode: raise RuntimeError('CLI acceptance failed: '+result.stdout[-2000:]+result.stderr[-1000:])
            payload = json.loads(result.stdout)
            assert payload['saved'] is True and payload['tools_enabled'] is False
            assert payload['mission']['state'] == 'succeeded' and payload['mission']['evidence_origin'] == 'real'
            assert payload['mission']['history'] == ['requested', 'planned', 'ready', 'running', 'verifying', 'succeeded']
            memory = ConversationMemory(state/'chat.sqlite3', 'owner')
            with memory._db() as db:
                row = db.execute('SELECT origin,model_sha256,api_calls,state FROM exchanges WHERE request_id=?', (payload['request_id'],)).fetchone()
            assert row['origin'] == 'real_local_inference' and row['model_sha256'] == model_sha and 1 <= row['api_calls'] <= 3 and row['state'] == 'completed'
            observed.append({'prompt': prompt, 'response': payload['reply'], 'mission': payload['mission'],
                             'inference': dict(row), 'elapsed_seconds': round(time.monotonic()-started, 4),
                             'separate_cli_process': True, 'fresh_offline_worker': True})
            return payload

        codeword = 'MAPLE'+uuid4().hex[:8].upper()
        first = turn('Remember this codeword for our conversation: '+codeword+'. Reply only NOTED.')
        second_prompt = 'What codeword did I ask you to remember? Reply only with that codeword.'
        assert codeword not in second_prompt
        second = turn(second_prompt, first['conversation_id'])
        assert codeword in second['reply'], 'Cross-process recall failed.'
        third = turn('What codeword did I ask you to remember in this conversation? If none was provided, reply only UNKNOWN.')
        assert third['conversation_id'] != first['conversation_id']
        assert codeword not in third['reply'] and 'UNKNOWN' in third['reply'].upper(), 'Conversation isolation acceptance failed.'
        memory = ConversationMemory(state/'chat.sqlite3', 'owner')
        assert len(memory.history('owner', first['conversation_id'])) == 4
        assert len(memory.history('owner', third['conversation_id'])) == 2
        try: ConversationMemory(state/'chat.sqlite3', 'intruder')
        except Denied: pass
        else: raise AssertionError('Persisted owner binding failed.')
        snapshot = memory.backup('owner', state/'snapshot.sqlite3')
        assert ConversationMemory(snapshot, 'owner').history('owner', first['conversation_id']) == memory.history('owner', first['conversation_id'])

        # Real SIGINT while a live worker exists: no fabricated cancellation result.
        with tempfile.TemporaryFile(mode='w+') as stdout, tempfile.TemporaryFile(mode='w+') as stderr:
            process = subprocess.Popen(command+['--session', first['conversation_id']], stdin=subprocess.PIPE,
                stdout=stdout, stderr=stderr, text=True, env=env, cwd=ROOT)
            try:
                process.stdin.write('Explain a long sequence of mathematical proofs.'); process.stdin.close()
                deadline = time.monotonic()+40
                while True:
                    containers = subprocess.run(docker+['container', 'ls', '--filter', 'label=com.igris.runtime=hermes-inference', '--format', '{{.ID}}'],
                                                capture_output=True, text=True, check=True, env=docker_env, timeout=10)
                    if containers.stdout.strip(): break
                    if process.poll() is not None: raise AssertionError('Cancellation process exited before a worker became active.')
                    if time.monotonic() > deadline: raise TimeoutError('Worker not observed for cancellation.')
                    time.sleep(.2)
                process.send_signal(signal.SIGINT)
                assert process.wait(timeout=35) == 130, 'CLI did not report manual stop.'
            finally:
                if process.poll() is None: process.kill(); process.wait(timeout=10)
        assert len(memory.history('owner', first['conversation_id'])) == 4
        assert all(row['active'] is None for row in memory.sessions('owner'))
        with memory._db() as db:
            assert db.execute("SELECT COUNT(*) FROM exchanges WHERE state='failed' AND assistant_text IS NULL").fetchone()[0] == 1
        remaining = subprocess.run(docker+['container', 'ls', '--all', '--filter', 'label=com.igris.runtime=hermes-inference', '--format', '{{.ID}}'],
                                   capture_output=True, text=True, check=True, env=docker_env, timeout=10)
        assert not remaining.stdout.strip(), 'Worker remained after stop.'
        memory.forget('owner', first['conversation_id'])
        try: memory.history('owner', first['conversation_id'])
        except KeyError: pass
        else: raise AssertionError('Explicit forgetting failed.')

    files = ['src/igris/chat.py', 'src/igris/conversations.py', 'src/igris/adapters/hermes_chat.py',
             'src/igris/controller.py', 'src/igris/memory.py', 'src/igris/guardian/policy.py',
             'scripts/hermes_inference_worker.py', 'scripts/hermes_chat_worker.py', 'scripts/test_chat_live.py',
             'integrations/hermes-inference/profile.json']
    evidence = {'status': 'PASS', 'origin': 'real_local_inference', 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        'model_sha256': model_sha, 'turns': observed, 'cross_process_recall': True, 'conversation_isolation': True,
        'persisted_owner_denial': True, 'sqlite_backup_restore': True, 'explicit_forget': True,
        'real_sigint_exit': 130, 'cancelled_turn_excluded_from_history': True, 'all_containers_removed': True,
        'native_tools_enabled': False, 'spend_inr': 0, 'mac_tested': False,
        'source_sha256': {path: hashlib.sha256((ROOT/path).read_bytes()).hexdigest() for path in files}}
    if findings(json.dumps(evidence)): raise ValueError('Evidence requires credential-pattern review.')
    record(evidence)
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == '__main__':
    try: main()
    except BaseException as exc:
        record({'status': 'STOPPED' if isinstance(exc, KeyboardInterrupt) else 'FAIL', 'origin': 'not_verified', 'error_class': type(exc).__name__})
        raise
