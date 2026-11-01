"""Explicit cloud-only download/extraction of reviewed public probe artifacts."""
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        while chunk := source.read(1024*1024): result.update(chunk)
    return result.hexdigest()


def fetch(runtime, name, url, expected, maximum):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', name): raise ValueError('Unsafe asset name.')
    target = runtime/name
    if target.is_symlink(): raise ValueError('Unsafe cached artifact.')
    if target.exists():
        if digest(target) != expected: raise ValueError('Cached artifact failed integrity; review before replacing.')
        print('Verified cached artifact:', name, flush=True); return target
    if shutil.disk_usage(runtime).free < maximum+512*1024*1024:
        raise ValueError('Insufficient free development storage.')
    temporary = None
    try:
        with urllib.request.urlopen(url, timeout=45) as response, tempfile.NamedTemporaryFile(dir=runtime, delete=False) as output:
            temporary = Path(output.name)
            if urllib.parse.urlsplit(response.url).scheme != 'https': raise ValueError('HTTPS download required.')
            size = 0
            while chunk := response.read(1024*1024):
                size += len(chunk)
                if size > maximum: raise ValueError('Artifact exceeds reviewed size limit.')
                output.write(chunk)
        if digest(temporary) != expected: raise ValueError('Downloaded artifact integrity failure.')
        temporary.replace(target); temporary = None
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    print('Verified downloaded artifact:', name, flush=True)
    return target


def main():
    if len(sys.argv) != 1 or sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise SystemExit('Explicit Linux x86_64 cloud use only; no Mac installation or service startup.')
    runtime = ROOT/'runtime'
    if runtime.is_symlink(): raise ValueError('Unsafe runtime directory.')
    runtime.mkdir(mode=0o700, exist_ok=True)
    profile = json.loads((ROOT/'integrations/hermes-inference/profile.json').read_text())
    if not re.fullmatch(r'[A-Za-z0-9_.-]+\.gguf', profile['model_file']) or not re.fullmatch(r'[a-f0-9]{40}', profile['model_revision']):
        raise ValueError('Invalid reviewed model reference.')
    python = json.loads((ROOT/'vendor/hermes-agent/pm/lock.json').read_text())['packages']['python']['artifacts']['linux-x64']
    if python['sha256'] != profile['python_archive_sha256']: raise ValueError('Reviewed Python pin mismatch.')
    py = fetch(runtime, 'cpython3149.tar.gz', python['url'], python['sha256'], 100*1024*1024)
    engine = fetch(runtime, 'llama-b11960.tar.gz',
        'https://github.com/ggml-org/llama.cpp/releases/download/b11960/llama-b11960-bin-ubuntu-x64.tar.gz',
        profile['engine_archive_sha256'], 32*1024*1024)
    fetch(runtime, profile['model_file'], 'https://huggingface.co/'+profile['model_repository']+
        '/resolve/'+profile['model_revision']+'/'+profile['model_file'], profile['model_sha256'], profile['model_bytes'])
    for archive, directory, executable in ((py, 'python3149', 'python/bin/python3.14'),
                                          (engine, 'llama-b11960', 'llama-b11960/llama-server')):
        target = runtime/directory
        if target.is_symlink(): raise ValueError('Unsafe extraction target.')
        if (target/executable).is_file(): continue
        target.mkdir(mode=0o700, exist_ok=True)
        with tarfile.open(archive) as source:
            if sum(entry.size for entry in source.getmembers()) > 1024*1024*1024:
                raise ValueError('Excessive archive expansion.')
            source.extractall(target, filter='data')
    print('Prepared public artifacts only. No model, daemon or paid service started.')


if __name__ == '__main__': main()
