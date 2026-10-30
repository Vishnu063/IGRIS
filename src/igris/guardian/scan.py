"""Local tracked/unignored UTF-8 source scanner; emits no matched secret values."""
import os
import re
from pathlib import Path
import stat
import subprocess
import sys
from .secrets import findings


def scan_repository(root: Path):
    listing = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                             cwd=root, capture_output=True, check=True).stdout
    results = []
    for entry in sorted(set(listing.split(b'\0')) - {b''}):
        name = os.fsdecode(entry)
        try:
            path = root / name
            # Refuse symlink components rather than following them outside root.
            if any(part.is_symlink() for part in (path, *path.parents) if part != root.parent):
                raise ValueError('symlink')
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(fd, 'rb') as handle:
                info = os.fstat(handle.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size > 1048576:
                    raise ValueError('unsupported file')
                raw = handle.read(1048577)
                if len(raw) > 1048576:
                    raise ValueError('oversized file')
            text = raw.decode('utf-8')
            results.extend((name, line, kind) for line, kind in findings(text))
        except (OSError, ValueError, UnicodeError):
            results.append((name, 0, 'unscannable-file'))
    staged = subprocess.run(['git', 'ls-files', '--stage', '-z'], cwd=root,
                            capture_output=True, check=True).stdout
    for entry in staged.split(b'\0'):
        if not entry:
            continue
        metadata, name_bytes = entry.split(b'\t', 1)
        mode, oid, stage = metadata.decode('ascii').split()
        name = 'index:' + os.fsdecode(name_bytes)
        if mode not in ('100644', '100755') or not re.fullmatch(r'[0-9a-f]{40,64}', oid):
            results.append((name, 0, 'unscannable-index-entry'))
            continue
        size = int(subprocess.check_output(['git', 'cat-file', '-s', oid], cwd=root))
        if size > 1048576:
            results.append((name, 0, 'oversized-index-entry'))
            continue
        raw = subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=root)
        try:
            results.extend((name, line, kind) for line, kind in findings(raw.decode('utf-8')))
        except UnicodeError:
            results.append((name, 0, 'unscannable-index-entry'))
    return results


def main():
    try:
        results = scan_repository(Path.cwd())
    except Exception:
        print('FAIL: repository scan unavailable.')
        return 1
    for name, line, kind in results:
        # JSON escaping prevents control characters in paths injecting output.
        import json
        print(json.dumps({'file': name, 'line': line, 'kind': kind}))
    print('FAIL: findings require review.' if results else 'PASS: no configured credential patterns found.')
    return int(bool(results))


if __name__ == '__main__':
    sys.exit(main())
