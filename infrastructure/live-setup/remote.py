#!/usr/bin/env python3
"""Root-only fixed deployment bridges. No credential values enter the result."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

STAGE_ROOT = Path('/opt/kirocrew-demo/setup-stages')
MAX_TOTAL = 2_000_000_000


def require(value, code):
    if not value:
        raise RuntimeError(code)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def trusted_dir(path, create=False):
    for item in reversed((path, *path.parents)):
        if not item.exists() and not item.is_symlink() and create:
            item.mkdir(mode=0o755)
        info = item.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                'untrusted_root_directory')


def read_regular(path, limit=MAX_TOTAL, root=False):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'unsafe_file')
        if root:
            require(info.st_uid == 0 and not info.st_mode & 0o022, 'untrusted_root_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            data = stream.read(limit + 1)
        require(len(data) <= limit, 'file_too_large')
        return data
    finally:
        os.close(fd)


def valid_name(name):
    parts = PurePosixPath(name).parts
    return bool(parts) and not name.startswith('/') and '..' not in parts and str(PurePosixPath(name)) == name


def validate_inventory(manifest):
    require(manifest.get('schema_version') == 1 and isinstance(manifest.get('files'), list), 'invalid_stage_manifest')
    result = {}
    total = 0
    for entry in manifest['files']:
        require(isinstance(entry, dict) and set(entry) == {'path', 'bytes', 'sha256'}, 'invalid_stage_entry')
        name = entry['path']
        require(isinstance(name, str) and valid_name(name) and name != 'stage-manifest.json' and name not in result,
                'unsafe_stage_path')
        require(type(entry['bytes']) is int and 0 <= entry['bytes'] <= MAX_TOTAL, 'invalid_stage_size')
        require(isinstance(entry['sha256'], str) and len(entry['sha256']) == 64
                and all(c in '0123456789abcdef' for c in entry['sha256']), 'invalid_stage_hash')
        result[name] = entry
        total += entry['bytes']
    require(len(result) <= 1000 and total <= MAX_TOTAL, 'stage_too_large')
    for name in result:
        require(not any(str(parent) in result for parent in PurePosixPath(name).parents if str(parent) != '.'),
                'stage_path_collision')
    return result


def verify_stage(stage, expected):
    trusted_dir(stage)
    raw = read_regular(stage / 'stage-manifest.json', 256_000, root=True)
    require(digest(raw) == expected, 'stage_manifest_changed')
    inventory = validate_inventory(json.loads(raw))
    files = set()
    for path in stage.rglob('*'):
        info = path.lstat()
        require(info.st_uid == 0 and not info.st_mode & 0o022, 'stage_ownership_changed')
        if stat.S_ISDIR(info.st_mode):
            continue
        require(stat.S_ISREG(info.st_mode), 'stage_contains_special_file')
        name = path.relative_to(stage).as_posix()
        files.add(name)
        if name == 'stage-manifest.json':
            continue
        require(name in inventory, 'unexpected_staged_file')
        raw_file = read_regular(path)
        require(len(raw_file) == inventory[name]['bytes'] and digest(raw_file) == inventory[name]['sha256'],
                'staged_file_changed')
    require(files == set(inventory) | {'stage-manifest.json'}, 'staged_file_missing')
    return inventory


def receive(expected, stream=None):
    """Extract only individually hashed regular entries into an exclusive root directory."""
    require(len(expected) == 64 and all(c in '0123456789abcdef' for c in expected), 'invalid_expected_hash')
    trusted_dir(STAGE_ROOT, create=True)
    target = STAGE_ROOT / expected
    temporary = Path(tempfile.mkdtemp(prefix='.incoming-', dir=STAGE_ROOT))
    try:
        seen = set()
        with tarfile.open(fileobj=stream or sys.stdin.buffer, mode='r|') as archive:
            entries = iter(archive)
            first = next(entries, None)
            require(first is not None and first.name == 'stage-manifest.json' and first.isfile()
                    and first.size <= 256_000, 'stage_manifest_must_be_first')
            raw = archive.extractfile(first).read()
            require(digest(raw) == expected, 'stage_manifest_hash_mismatch')
            inventory = validate_inventory(json.loads(raw))
            (temporary / 'stage-manifest.json').write_bytes(raw)
            for entry in entries:
                require(entry.isfile() and entry.name in inventory and entry.name not in seen, 'unexpected_archive_entry')
                spec = inventory[entry.name]
                require(entry.size == spec['bytes'], 'archive_size_mismatch')
                destination = temporary / entry.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                checksum = hashlib.sha256()
                with archive.extractfile(entry) as source, destination.open('xb') as output:
                    while chunk := source.read(1024 * 1024):
                        checksum.update(chunk)
                        output.write(chunk)
                require(checksum.hexdigest() == spec['sha256'], 'archive_hash_mismatch')
                destination.chmod(0o644)
                seen.add(entry.name)
        require(seen == set(inventory), 'archive_file_missing')
        temporary.chmod(0o755)
        if target.exists() or target.is_symlink():
            verify_stage(target, expected)
        else:
            os.rename(temporary, target)
        verify_stage(target, expected)
        return {'stage': str(target), 'stage_sha256': expected, 'files': len(inventory)}
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def file_plan(source, target, mode=0o644):
    raw = read_regular(source, root=True)
    trusted_dir(target.parent, create=False)
    if target.exists() or target.is_symlink():
        current = read_regular(target, root=True)
        require(current == raw, 'existing_integration_file_differs_' + target.name)
        require(stat.S_IMODE(target.stat().st_mode) == mode, 'existing_integration_mode_differs')
        return None
    return target, raw, mode


def write_new(plan):
    if plan is None:
        return
    path, raw, mode = plan
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def telemetry_replacement(raw):
    config = json.loads(raw)
    require(isinstance(config, dict) and config.get('default_agent') == 'enforcement-demo', 'dedicated_demo_identity_mismatch')
    require(isinstance(config.get('telemetry', {}), dict), 'invalid_existing_telemetry')
    fields = dict(enabled=True, local_dir='', export_interval_seconds=10, retention_days=7,
                  max_total_mb=64, otlp_endpoint='', beacon_enabled=False)
    if all(config.get('telemetry', {}).get(key) == value for key, value in fields.items()):
        return raw
    config.setdefault('telemetry', {}).update(fields)
    return (json.dumps(config, indent=2) + '\n').encode()


def command(argv):
    result = subprocess.run(argv, capture_output=True, timeout=60)
    require(result.returncode == 0, 'integration_command_failed_' + Path(argv[0]).name)


def integrate(stage, expected, restart=False):
    verify_stage(stage, expected)
    crew = pwd.getpwnam('crew')
    require(crew.pw_uid != 0, 'crew_must_be_unprivileged')
    # Root paths are fixed by the existing product/service contract, not user input.
    folders = ['/usr/local/bin', '/opt/kirocrew-demo/observability', '/opt/kirocrew-demo/observability-app/backend',
               '/opt/kirocrew-demo/observability-app/ui/dist', '/etc/systemd/system', '/var/lib/kirocrew-demo-observability']
    for folder in folders:
        trusted_dir(Path(folder), create=True)
    store = Path('/var/lib/kirocrew-demo-observability')
    os.chown(store, 0, crew.pw_gid)
    store.chmod(0o750)
    mappings = [
        ('infrastructure/kirocrew-owner-token.py', '/usr/local/bin/kirocrew-owner-token', 0o755),
        ('infrastructure/observability-collector/collector.py', '/opt/kirocrew-demo/observability/collector.py', 0o644),
        ('infrastructure/observability-collector/kirocrew-demo-observability.service', '/etc/systemd/system/kirocrew-demo-observability.service', 0o644),
        ('infrastructure/observability-collector/kirocrew-demo-observability.timer', '/etc/systemd/system/kirocrew-demo-observability.timer', 0o644),
        ('infrastructure/observability/app/app.json', '/opt/kirocrew-demo/observability-app/app.json', 0o644),
        ('infrastructure/observability/app/backend/server.py', '/opt/kirocrew-demo/observability-app/backend/server.py', 0o644),
        ('infrastructure/observability/app/ui/dist/index.mjs', '/opt/kirocrew-demo/observability-app/ui/dist/index.mjs', 0o644),
    ]
    plans = [file_plan(stage / source, Path(target), mode) for source, target, mode in mappings]
    config_path = Path('/var/lib/kirocrew/config.json')
    require(config_path.resolve(strict=True) == config_path and config_path.lstat().st_uid == crew.pw_uid,
            'unsafe_crew_config')
    original = read_regular(config_path, 1_000_000)
    replacement = telemetry_replacement(original)
    require(original == replacement or restart, 'telemetry_change_requires_restart_gateway_flag')
    for plan in plans:
        write_new(plan)
    if original != replacement:
        backup = stage / ('config-before-telemetry-' + digest(original) + '.json')
        # Configuration backup is private and deliberately outside the verified staging inventory.
        backup = Path('/var/lib/kirocrew-demo-observability') / backup.name
        write_new((backup, original, 0o600))
        fd, temporary = tempfile.mkstemp(prefix='.live-telemetry-', dir=config_path.parent)
        try:
            os.fchown(fd, crew.pw_uid, crew.pw_gid)
            with os.fdopen(fd, 'wb') as output:
                output.write(replacement)
                output.flush()
                os.fsync(output.fileno())
            require(read_regular(config_path, 1_000_000) == original, 'crew_config_changed')
            os.replace(temporary, config_path)
        finally:
            Path(temporary).unlink(missing_ok=True)
    command(['/usr/bin/systemctl', 'daemon-reload'])
    command(['/usr/bin/python3', '/opt/kirocrew-demo/observability/collector.py', 'server', '--store'])
    command(['/usr/bin/systemctl', 'enable', '--now', 'kirocrew-demo-observability.timer'])
    if original != replacement:
        command(['/usr/bin/systemctl', 'restart', 'kirocrew-demo.service'])
    command(['/usr/bin/systemctl', 'is-active', 'kirocrew-demo-observability.timer', 'kirocrew-demo.service'])
    return {'installed_files': sum(plan is not None for plan in plans), 'native_telemetry_configured': True,
            'gateway_restarted': original != replacement, 'server_timer_active': True,
            'observability_app_staged': True, 'app_install_required': True}


def services(stage, expected, bucket, region):
    verify_stage(stage, expected)
    require(re.fullmatch(r'[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', bucket or '')
            and re.fullmatch(r'[a-z]{2}(?:-[a-z0-9]+)+-[0-9]+', region or ''), 'invalid_bucket_or_region')
    for path in ('/etc/kirocrew-demo/mcp.env', '/etc/kirocrew-demo/mcp-token', '/var/lib/kirocrew/config.json',
                 '/home/crew/.kiro/agents/enforcement-demo.json', '/opt/kirocrew-demo/mcp-venv'):
        require(not Path(path).exists() and not Path(path).is_symlink(), 'services_require_fresh_host')
    for name in ('kiro-cli', 'kiro-cli-chat', 'kiro-cli-term'):
        require(not Path('/usr/local/bin', name).exists(), 'cli_already_installed')
    install = Path('/opt/kirocrew-demo/install')
    trusted_dir(install, create=True)
    trusted_dir(install / 'mcp-enforcement', create=True)
    paths = ['configure-demo.py', 'configure-arm-services.sh', 'kirocrew-demo-wrapper.sh',
             'kirocrew-demo.service', 'kirocrew-mcp-demo.service', 'mcp-enforcement/server.py',
             'mcp-enforcement/probe.py', 'mcp-enforcement/requirements.txt']
    plans = [file_plan(stage / 'infrastructure' / name, install / name) for name in paths]
    plans.append(file_plan(stage / 'bundle/kirocli-aarch64-linux.tar.xz', install / 'kirocli-aarch64-linux.tar.xz'))
    for plan in plans:
        write_new(plan)
    result = subprocess.run(['/bin/bash', str(install / 'configure-arm-services.sh'), '--bucket', bucket,
                             '--region', region], capture_output=True, timeout=1200)
    require(result.returncode == 0, 'service_install_failed_inspect_host_state_before_retry')
    return {'services_installed': True, 'native_cli_authentication_required': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('receive', 'integrate', 'services'))
    parser.add_argument('--stage-sha256', required=True)
    parser.add_argument('--restart-gateway', action='store_true')
    parser.add_argument('--bucket')
    parser.add_argument('--region')
    args = parser.parse_args()
    require(os.geteuid() == 0 and sys.platform == 'linux', 'root_linux_required')
    if args.operation == 'receive':
        result = receive(args.stage_sha256)
    elif args.operation == 'integrate':
        result = integrate(STAGE_ROOT / args.stage_sha256, args.stage_sha256, args.restart_gateway)
    else:
        result = services(STAGE_ROOT / args.stage_sha256, args.stage_sha256, args.bucket, args.region)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError, tarfile.TarError) as error:
        print(json.dumps({'status': 'refused', 'code': str(error) if isinstance(error, RuntimeError) else type(error).__name__}))
        raise SystemExit(1)
