"""Explicit owner-only migration of the original dedicated Lima policy.

No guest command, package installation, disk replacement or automatic restart.
Unknown configuration is inspected, never silently normalized or overwritten.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

from mac_package import Blocked, PACKAGE, check, digest
from mac_vm import read_instance, validate_instance

EXPRESSION = ('del(.rosetta) | .vmOpts.vz.rosetta = {"enabled": false, "binfmt": false}'
              ' | .portForwards[0].proto = "tcp"'
              ' | .portForwards[1].guestIP = "0.0.0.0"'
              ' | .portForwards[1].guestIPMustBeZero = false'
              ' | .portForwards[1].proto = "any"')


def private_read(path):
    path = Path(path)
    if path.resolve() != path:
        raise Blocked('Configuration symlink/parent redirection denied.')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_nlink != 1 or info.st_mode & 0o022 or info.st_size > 65536):
            raise Blocked('Unknown configuration ownership/type/size; preserved.')
        return stream.read(65537)


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def replace_known(path, before, after):
    if private_read(path) != before:
        raise Blocked('Concurrent configuration modification; preserved for review.')
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix='.vm-policy-')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(after)
            stream.flush()
            os.fsync(stream.fileno())
        if private_read(path) != before:
            raise Blocked('Concurrent configuration modification; preserved for review.')
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def inspect_policy(binary, env, root):
    """Output only finite policy fields, never env/proxies/keys or guest content."""
    instance = read_instance(binary, env)
    validate_instance(instance, root, legacy=True)
    config = instance['config']
    path = Path(root)/'vm-state/igris/lima.yaml'
    try:
        validate_instance(instance, root)
        policy = 'PASS'
    except Blocked:
        policy = 'BLOCKED_REQUIRES_MIGRATION'
    return {
        'status': instance.get('status'), 'arch': instance['arch'],
        'vm_type': instance['vmType'], 'cpus': instance['cpus'],
        'memory_bytes': instance['memory'], 'disk_bytes': instance['disk'],
        'configuration_sha256': hashlib.sha256(private_read(path)).hexdigest(),
        'recognized_original_yaml': digest(path) == digest(PACKAGE/'migrations/lima-v1.yaml'),
        'effective_rosetta': {key: config['vmOpts']['vz']['rosetta'].get(key)
                             for key in ('enabled', 'binfmt')},
        'policy': policy, 'host_mounts': len(config.get('mounts', [])),
        'forwards': [{key: row.get(key) for key in
                      ('proto', 'guestIP', 'guestIPMustBeZero', 'guestPortRange',
                       'hostIP', 'hostPortRange', 'ignore')}
                     for row in config['portForwards']],
        'inspection_started_guest_commands_or_models': False,
    }


def migrate_policy(binary, env, root):
    root = Path(root)
    manifest = check(root, allow_legacy=True)
    marker = root/'vm-policy-migration.json'
    if marker.exists() or marker.is_symlink():
        record = json.loads(private_read(marker))
        if record.get('status') == 'PASS':
            check(root)
            result = inspect_policy(binary, env, root)
            if result['policy'] == 'PASS':
                return dict(result, migration='ALREADY_APPLIED')
        raise Blocked('Previous migration incomplete or modified; preserve its snapshots for review. No automatic retry.')
    instance = read_instance(binary, env)
    validate_instance(instance, root, legacy=True)
    if instance.get('status') not in ('Running', 'Stopped'):
        raise Blocked('VM must be Running or Stopped before explicit migration.')
    path = root/'vm-state/igris/lima.yaml'
    original = private_read(path)
    if original != (PACKAGE/'migrations/lima-v1.yaml').read_bytes():
        raise Blocked('Instance YAML is not the exact shipped original. Run inspect-vm and review; no files changed.')
    before_config = private_read(root/'lima.yaml')
    before_manifest = private_read(root/'manifest.json')
    # A private immutable snapshot plus a pending marker makes interruption fail
    # closed. Never restore/start a partially migrated VM automatically.
    snapshot = Path(tempfile.mkdtemp(prefix='vm-policy-before-', dir=root))
    for name, raw in (('instance.yaml', original), ('lima.yaml', before_config),
                      ('manifest.json', before_manifest)):
        write_new(snapshot/name, raw)
    pending = (json.dumps({'schema': 1, 'status': 'PENDING',
                          'snapshot_directory': snapshot.name})+'\n').encode()
    write_new(marker, pending)
    try:
        if instance['status'] == 'Running':
            subprocess.run([binary, 'stop', 'igris'], env=env, check=True, timeout=60)
        stopped = read_instance(binary, env)
        validate_instance(stopped, root, legacy=True)
        if stopped.get('status') != 'Stopped' or private_read(path) != original:
            raise Blocked('VM did not stop or its configuration changed. Migration left blocked.')
        subprocess.run([binary, 'edit', '--tty=false', '--set', EXPRESSION, 'igris'],
                       env=env, check=True, timeout=60)
        updated = read_instance(binary, env)
        validate_instance(updated, root)
        if updated.get('status') != 'Stopped':
            raise Blocked('Unexpected VM state after policy edit; review required.')
        expected = copy.deepcopy(stopped['config'])
        expected.pop('rosetta', None)
        expected['vmOpts']['vz']['rosetta'] = {'enabled': False, 'binfmt': False}
        expected['portForwards'][0]['proto'] = 'tcp'
        expected['portForwards'][1].update(guestIP='0.0.0.0', guestIPMustBeZero=False, proto='any')
        actual = copy.deepcopy(updated['config'])
        actual.pop('rosetta', None)
        if actual != expected:
            raise Blocked('Unexpected effective policy changes; snapshots preserved and startup blocked.')
        replace_known(root/'lima.yaml', before_config, (PACKAGE/'lima.yaml').read_bytes())
        manifest['files']['lima.yaml'] = digest(PACKAGE/'lima.yaml')
        replace_known(root/'manifest.json', before_manifest,
                      (json.dumps(manifest, indent=2)+'\n').encode())
        complete = (json.dumps({'schema': 1, 'status': 'PASS',
                               'snapshot_directory': snapshot.name,
                               'instance_sha256': digest(path)})+'\n').encode()
        replace_known(marker, pending, complete)
        check(root)
        return dict(inspect_policy(binary, env, root), migration='PASS_VM_LEFT_STOPPED',
                    snapshot_directory=snapshot.name)
    except BaseException as error:
        # edit may have launched a driver helper before failing/interruption.
        # Address only this pinned binary/private profile; never a global kill.
        try:
            subprocess.run([binary, 'stop', 'igris'], env=env, check=True, timeout=60)
            cleaned = read_instance(binary, env)
            validate_instance(cleaned, root, legacy=True)
            if cleaned.get('status') != 'Stopped':
                raise Blocked('Dedicated VM has not confirmed Stopped.')
        except BaseException:
            raise Blocked('Migration failed and owned-VM cleanup is NOT VERIFIED. '
                          'Use stop-vm and inspect-vm; snapshots and guest disk preserved.') from None
        if isinstance(error, (Blocked, KeyboardInterrupt, SystemExit)):
            raise
        raise Blocked('VM policy migration interrupted or failed ('+type(error).__name__+
                      '); snapshots preserved, startup remains blocked. No guest disk deleted.') from None
