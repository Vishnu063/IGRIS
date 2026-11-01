"""Private offline container worker; real Hermes and GGUF inference, no tools.

Launched by the shared isolated transport. No framework, model or SDK mock.
"""
from contextlib import contextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT/'runtime'


@contextmanager
def reasoning_session():
    os.umask(0o077)
    sys.path.insert(0, str(ROOT/'src'))
    from igris.guardian.secrets import redact
    Path('/tmp/igris-home').mkdir(exist_ok=True)
    profile = json.loads((ROOT/'integrations/hermes-inference/profile.json').read_text())
    model = RUNTIME/profile['model_file']
    digest = hashlib.sha256()
    with model.open('rb') as source:
        while chunk := source.read(1024*1024): digest.update(chunk)
    assert digest.hexdigest() == profile['model_sha256'], 'Model integrity check failed'
    assert os.getuid() != 0, 'Probe must not run as root'
    assert os.environ.get('HERMES_DISABLE_LAZY_INSTALLS') == '1'
    try:
        with (ROOT/'vendor/hermes-agent/.igris-write-probe').open('x'): pass
    except OSError as exc:
        assert exc.errno == errno.EROFS, 'Source must be mounted read-only'
    else: raise RuntimeError('Writable framework source refused')
    try: socket.create_connection(('192.0.2.1', 9), timeout=.2)
    except OSError as exc:
        assert exc.errno == errno.ENETUNREACH, 'No-network namespace required'
    else: raise RuntimeError('External network unexpectedly reachable')

    # Private ephemeral service credential stays in this container, never argv/output.
    local_secret = secrets.token_urlsafe(32)
    engine = RUNTIME/'llama-b11960/llama-b11960/llama-server'
    environment = {'PATH': '/usr/bin:/bin', 'HOME': '/tmp/igris-home',
                   'LLAMA_API_KEY': local_secret}
    log = Path('/tmp/llama.log').open('wb')
    process = subprocess.Popen([str(engine), '--model', str(model), '--host', '127.0.0.1',
        '--port', '8766', '--ctx-size', str(profile['served_context_tokens']), '--parallel', '1', '--threads', '2',
        '--batch-size', '128', '--n-gpu-layers', '0', '--alias', 'igris-local-qwen',
        '--chat-template-kwargs', '{"enable_thinking":true}', '--reasoning-budget', '128'],
        stdout=log, stderr=log, env=environment)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic()+45
        while True:
            if process.poll() is not None:
                detail = Path('/tmp/llama.log').read_text(errors='replace')[-4096:]
                raise RuntimeError('Local model process failed: '+redact(detail, known_secrets=(local_secret,)))
            try:
                with opener.open('http://127.0.0.1:8766/health', timeout=1) as response:
                    if response.status == 200: break
            except (OSError, urllib.error.HTTPError): pass
            if time.monotonic() > deadline: raise TimeoutError('Local model startup exceeded deadline')
            time.sleep(.2)
        # Prove model inference requires the private credential, not merely health.
        request = urllib.request.Request('http://127.0.0.1:8766/v1/chat/completions',
            data=b'{"model":"igris-local-qwen","messages":[{"role":"user","content":"hello"}]}',
            headers={'Content-Type': 'application/json'})
        try: opener.open(request, timeout=2)
        except urllib.error.HTTPError as exc: assert exc.code == 401
        else: raise RuntimeError('Unauthenticated model endpoint refused')

        sys.path.insert(0, str(ROOT/'vendor/hermes-agent'))
        sys.path.insert(1, str(ROOT/'src'))
        from agent.safe_worker_policy import _bind_safe_worker_policy
        # Actual upstream supported private worker policy; bind before runtime imports.
        _bind_safe_worker_policy(safe_mode=True, ignore_user_config=True, config={
            'agent': {'environment_probe': False, 'api_max_retries': 1,
                      'task_completion_guidance': False, 'parallel_tool_call_guidance': False},
            'model': {'context_length': profile['served_context_tokens']}, 'compression': {'enabled': False},
            'memory': {'memory_enabled': False, 'user_profile_enabled': False}})
        from igris.guardian.policy import Denied, Policy
        from run_agent import AIAgent
        guardian = Policy('hermes-inference')

        class ReasoningOnlyAgent(AIAgent):
            def _execute_tool_calls(self, *args, **kwargs):
                # Default-empty Guardian rejects at the actual agent dispatch method.
                # This probe deliberately grants no execution capability.
                guardian.require('python.version')
                raise RuntimeError('Inference profile must never grant tool authority')

        agent = ReasoningOnlyAgent(model='igris-local-qwen', provider='custom',
            api_mode='chat_completions', base_url='http://127.0.0.1:8766/v1',
            api_key=local_secret, enabled_toolsets=[], max_iterations=1, max_tokens=256,
            quiet_mode=True, skip_context_files=True, load_soul_identity=False,
            skip_memory=True, skip_background_review=True, save_trajectories=False,
            verbose_logging=False, checkpoints_enabled=False, run_budget_seconds=60,
            ephemeral_system_prompt='You are IGRIS. Answer the question briefly. You have no tools or execution permissions.',
            request_overrides={'temperature': 0, 'seed': 42})
        assert agent.tools == [] and agent.valid_tool_names == set()
        try: agent._execute_tool_calls(None, [], 'security-probe')
        except Denied: pass
        else: raise RuntimeError('Guardian did not deny tool dispatch')
        yield agent, profile, opener, local_secret
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        log.close()


def main():
    with reasoning_session() as (agent, profile, opener, local_secret):
        from igris.guardian.secrets import redact
        left, right = 10+secrets.randbelow(10), 10+secrets.randbelow(10)
        word = secrets.choice(('river', 'window', 'planet'))
        cases = [('What is 18 plus 13? Reply with only the integer.', '31'),
                 (f'What is {left} plus {right}? Reply with only the integer.', str(left+right)),
                 (f'Write {word} in uppercase. Reply with only that word.', word.upper())]
        direct_body = json.dumps({'model': 'igris-local-qwen',
            'messages': [{'role': 'system', 'content': 'Answer the user briefly. No tools are available.'},
                         {'role': 'user', 'content': cases[0][0]}],
            'temperature': 0, 'max_tokens': 256}).encode()
        direct_request = urllib.request.Request('http://127.0.0.1:8766/v1/chat/completions', data=direct_body,
            headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+local_secret})
        with opener.open(direct_request, timeout=60) as direct_result:
            direct_answer = json.load(direct_result)['choices'][0]['message'].get('content', '')
        observed = []
        for prompt, expected in cases:
            started = time.monotonic()
            result = agent.run_conversation(prompt, system_message='Answer the user briefly. No tools are available.')
            response = result.get('final_response', '')
            assert type(response) is str and response.strip(), 'No generated answer'
            assert result.get('api_calls', 0) >= 1, 'No real inference API call'
            if not re.search(r'\b'+re.escape(expected)+r'\b', response):
                diagnostic = {'acceptance': 'failed', 'prompt': prompt, 'expected': expected,
                              'response': redact(response, known_secrets=(local_secret,)),
                              'error': redact(str(result.get('error', '')), known_secrets=(local_secret,)),
                              'api_calls': result.get('api_calls'), 'direct_control_response': direct_answer}
                raise ValueError(json.dumps(diagnostic))
            assert agent.tools == [] and agent.valid_tool_names == set()
            observed.append({'prompt': prompt, 'response': response, 'expected': expected,
                'api_calls': result['api_calls'], 'elapsed_seconds': round(time.monotonic()-started, 4)})
        print(json.dumps({'status': 'PASS', 'origin': 'real_local_inference',
            'framework': 'Hermes AIAgent.run_conversation', 'hermes_revision': profile['hermes_revision'],
            'python': sys.version.split()[0], 'model': profile['model_repository'],
            'model_sha256': profile['model_sha256'], 'responses': observed,
            'direct_control_response': direct_answer,
            'controls': {'non_root': True, 'source_read_only': True, 'external_network_absent': True,
                         'model_authentication_checked': True, 'tools_exposed': 0,
                         'guardian_tool_dispatch_denied': True, 'automatic_install_disabled': True},
            'spend_inr': 0, 'full_assistant_operational': False}, sort_keys=True), flush=True)


if __name__ == '__main__': main()
