"""Deterministic development-source artifact; not a production deployment."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile


def build_bundle(destination, *, source=None):
    root = Path(source) if source is not None else Path(__file__).resolve().parents[2]
    paths = [root / 'README.md', *sorted((root / 'src').rglob('*.py')),
             *sorted((root / 'config').glob('*.json'))]
    entries = {}
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in path.parents):
            raise ValueError('Unsafe artifact source.')
        if path.stat().st_size > 1048576:
            raise ValueError('Artifact source too large.')
        entries[path.relative_to(root).as_posix()] = path.read_bytes()
    manifest = {'schema_version': 1, 'kind': 'development_source', 'production_ready': False,
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}}
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
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
