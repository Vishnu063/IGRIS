"""Deterministic development-source artifact; not a production deployment."""
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile
from .guardian.secrets import findings

SOURCE_DIRS = ('src', 'config', 'docs', 'tests', 'scripts', 'workflows', 'integrations', 'vendor', '.github')
TEXT_SUFFIXES = frozenset({'.py', '.json', '.md', '.toml', '.yaml', '.yml', '.j2', '.js', '.html', '.txt', '.ini', '.cfg'})
ROOT_FILES = ('README.md', 'THIRD_PARTY_NOTICES.md', 'LICENSE', 'SECURITY.md', '.gitignore', '.gitattributes', '.env.example')
OMIT_DIRS = frozenset({'__pycache__', '.git', '.venv', 'node_modules', 'runtime', 'backups', 'dist', 'build'})


def build_bundle(destination, *, source=None):
    root = Path(source).absolute() if source is not None else Path(__file__).resolve().parents[2]
    if not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Unsafe artifact source root.')
    paths = [root/name for name in ROOT_FILES if (root/name).exists()]
    for directory in SOURCE_DIRS:
        base = root/directory
        if base.is_symlink(): raise ValueError('Unsafe artifact source directory.')
        for path in sorted(base.rglob('*')):
            relative = path.relative_to(root)
            if any(p in OMIT_DIRS for p in relative.parts): continue
            if path.suffix in TEXT_SUFFIXES or path.name in ('LICENSE', 'SECURITY', 'README'):
                if path.is_file() or path.is_symlink(): paths.append(path)
    if len(paths) > 10000: raise ValueError('Too many artifact entries.')
    entries = {}
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in path.parents):
            raise ValueError('Unsafe artifact source.')
        if path.stat().st_size > 1048576:
            raise ValueError('Artifact source too large.')
        data = path.read_bytes()
        if findings(data.decode('utf-8')): raise ValueError('Credential-pattern review required before bundling.')
        entries[path.relative_to(root).as_posix()] = data
    if sum(map(len, entries.values())) > 128 * 1024 * 1024:
        raise ValueError('Artifact total capacity exceeded.')
    manifest = {'schema_version': 1, 'kind': 'development_source', 'production_ready': False,
                'hermes_runtime': 'curated source subset; not installed or fully runnable',
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as output, zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        entries['MANIFEST.json'] = json.dumps(manifest, sort_keys=True).encode()
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100600 << 16
            archive.writestr(info, data)
    return manifest


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Supply one new development artifact path.')
    build_bundle(sys.argv[1])
    print('Prepared development-source artifact; no deployment performed.')
