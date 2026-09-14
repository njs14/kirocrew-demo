#!/usr/bin/env python3
"""Plan or apply one config-bound live-demo setup stage. Plans perform no network I/O."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace

from demo_config import load_config, ssh_options

ROOT = Path(__file__).resolve().parents[1]
REMOTE = ROOT / 'infrastructure/live-setup/remote.py'
STAGES = ('runtime', 'services', 'fixtures', 'server-integrations', 'managed-policy', 'mcp-user-ui', 'host-controls', 'desktop', 'app', 'client-telemetry')
FIXTURES = {'allowed/sentinel.txt': b'KiroCrew demo: the instance role may read this public canary.\n',
            'denied/sentinel.txt': b'KiroCrew demo: this public canary exists and IAM denies its read.\n'}
INTEGRATION_FILES = ['kirocrew-owner-token.py', 'observability-collector/collector.py',
                     'observability-collector/kirocrew-demo-observability.service',
                     'observability-collector/kirocrew-demo-observability.timer',
                     'observability/app/app.json', 'observability/app/backend/server.py',
                     'observability/app/ui/dist/index.mjs']
SERVICE_FILES = ['configure-demo.py', 'configure-arm-services.sh', 'kirocrew-demo-wrapper.sh',
                 'kirocrew-demo.service', 'kirocrew-mcp-demo.service', 'mcp-enforcement/server.py',
                 'mcp-enforcement/probe.py', 'mcp-enforcement/requirements.txt']


def require(value, code):
    if not value:
        raise RuntimeError(code)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(path, limit=2_000_000_000):
    path = Path(path)
    require(not path.is_symlink(), 'symlink_input_refused')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= limit, 'input_must_be_bounded_regular_file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            raw = stream.read(limit + 1)
        require(len(raw) <= limit, 'input_too_large')
        return raw
    finally:
        os.close(fd)


def run(argv, *, input=None, timeout=60):
    result = subprocess.run(argv, input=input, capture_output=True, timeout=timeout,
                            env={**os.environ, 'AWS_PAGER': '', 'AWS_CLI_AUTO_PROMPT': 'off'})
    require(result.returncode == 0, 'command_failed_' + Path(argv[0]).name)
    require(len(result.stdout) <= 1_000_000, 'command_output_too_large')
    return result.stdout


def cloud_args(config):
    return SimpleNamespace(config=config, offline=False, evidence_dir=None, profile=None)


def validated_context(config):
    cloud = module('live_setup_cloud', ROOT / 'scripts/demo-cloud.py')
    args = cloud_args(config)
    # Setup creates the new tunnel plist later. Validate SSH independently first.
    check_args = cloud_args(copy.deepcopy(config))
    check_args.config['tunnel']['mode'] = 'manual'
    cloud.check_local_files(check_args)
    context = cloud.get_context(args)
    require(context['instance']['State']['Name'] == 'running', 'instance_must_be_running')
    require(context['instance']['Architecture'] == 'arm64', 'arm_instance_required')
    expected = cloud.instance_address(context['instance'], config)
    require(expected, 'configured_address_unavailable')
    effective = run(['ssh', *ssh_options(config), '-G', config['ssh']['admin_alias']]).decode()
    hostnames = [line.split(' ', 1)[1] for line in effective.splitlines() if line.startswith('hostname ')]
    require(hostnames == [expected], 'ssh_hostname_does_not_match_bound_instance_run_demo_cloud_start')
    return context


def layout(config):
    require(config['ssh']['remote_port'] == 5476 and config['probe']['remote_root'] == '/opt/kirocrew-demo'
            and config['telemetry']['remote_collector_path'] == '/opt/kirocrew-demo/observability/collector.py',
            'server_install_requires_documented_demo_layout')


def fixture_payloads(args):
    result = dict(FIXTURES)
    for key, path in (('allowed/sentinel.txt', args.allowed_file), ('denied/sentinel.txt', args.denied_file)):
        if path:
            result[key] = read_regular(Path(path).expanduser().absolute(), 4096)
        require(0 < len(result[key]) <= 4096, 'fixture_must_contain_1_to_4096_bytes')
    return result


def verify_bundle(path, expected=None):
    path = Path(path).expanduser().absolute()
    require(path.is_dir() and path.resolve(strict=True) == path, 'bundle_must_be_real_directory')
    raw = read_regular(path / 'manifest.json', 1_000_000)
    require(expected is None or isinstance(expected, str) and re.fullmatch(r'[a-f0-9]{64}', expected),
            'invalid_reviewed_manifest_sha256')
    require(expected is None or sha(raw) == expected, 'bundle_changed_since_reviewed_plan')
    installer = ROOT / 'infrastructure/install-runtime-bundle.py'
    require(installer.is_file(), 'manifest_bundle_installer_missing')
    run([sys.executable, str(installer), 'verify', '--bundle', str(path), '--manifest-sha256', sha(raw)], timeout=180)
    return path, sha(raw)


def stage_inputs(config, stage, bundle=None, bundle_sha=None):
    files = {'infrastructure/live-setup/remote.py': read_regular(REMOTE)}
    names = SERVICE_FILES if stage == 'services' else INTEGRATION_FILES if stage == 'server-integrations' else []
    for name in names:
        raw = read_regular(ROOT / 'infrastructure' / name)
        if name in ('kirocrew-demo-wrapper.sh', 'kirocrew-demo.service'):
            require(raw.count(b'KIROCREW_ALLOWED_LOOPBACK_PORTS=5599') == 1, 'loopback_template_changed')
            raw = raw.replace(b'KIROCREW_ALLOWED_LOOPBACK_PORTS=5599',
                              ('KIROCREW_ALLOWED_LOOPBACK_PORTS=' + str(config['ssh']['local_port'])).encode())
        if name == 'observability-collector/kirocrew-demo-observability.timer':
            require(raw.count(b'OnUnitActiveSec=60s') == 1, 'timer_template_changed')
            raw = raw.replace(b'OnUnitActiveSec=60s',
                              ('OnUnitActiveSec=' + str(config['telemetry']['interval_seconds']) + 's').encode())
        files['infrastructure/' + name] = raw
    if bundle:
        require(bundle_sha, 'reviewed_bundle_digest_required_for_staging')
        captured_manifest = read_regular(bundle / 'manifest.json', 1_000_000)
        require(sha(captured_manifest) == bundle_sha, 'bundle_manifest_changed_during_staging')
        inventory = json.loads(captured_manifest)['files']
        expected_files = {entry['path']: entry for entry in inventory}
        require(len(expected_files) == len(inventory), 'duplicate_bundle_inventory')
        captured = {}
        for path in sorted(bundle.rglob('*')):
            if path.is_dir() and not path.is_symlink():
                continue
            name = path.relative_to(bundle).as_posix()
            require(name == 'manifest.json' or name in expected_files, 'unexpected_bundle_member_during_staging')
            if stage == 'services' and name not in ('manifest.json', 'kirocli-aarch64-linux.tar.xz'):
                continue
            raw = captured_manifest if name == 'manifest.json' else read_regular(path)
            if name != 'manifest.json':
                expected = expected_files[name]
                require(len(raw) == expected['bytes'] and sha(raw) == expected['sha256'],
                        'bundle_member_changed_during_staging')
            captured[name] = raw
        wanted = {'manifest.json', 'kirocli-aarch64-linux.tar.xz'} if stage == 'services' else set(expected_files) | {'manifest.json'}
        require(set(captured) == wanted, 'bundle_member_missing_during_staging')
        files.update({'bundle/' + name: raw for name, raw in captured.items()})
    require(sum(len(raw) for raw in files.values()) <= 2_000_000_000, 'staging_payload_too_large')
    manifest = {'schema_version': 1, 'files': [{'path': name, 'bytes': len(raw), 'sha256': sha(raw)}
                                            for name, raw in sorted(files.items())]}
    raw_manifest = (json.dumps(manifest, sort_keys=True, separators=(',', ':')) + '\n').encode()
    return files, raw_manifest


def ssh_run(config, argv, payload=None, timeout=60):
    command = ['ssh', *ssh_options(config), '-o', 'ConnectTimeout=10', '-o', 'ClearAllForwardings=yes',
               config['ssh']['admin_alias'], shlex.join(argv)]
    return run(command, input=payload, timeout=timeout)


def upload_stage(config, files, manifest):
    expected = sha(manifest)
    with tempfile.TemporaryFile() as archive_file:
        with tarfile.open(fileobj=archive_file, mode='w') as archive:
            for name, raw in [('stage-manifest.json', manifest), *sorted(files.items())]:
                info = tarfile.TarInfo(name)
                info.size, info.mode = len(raw), 0o644
                archive.addfile(info, io.BytesIO(raw))
        archive_file.seek(0)
        command = ['ssh', *ssh_options(config), '-o', 'ConnectTimeout=10', '-o', 'ClearAllForwardings=yes',
                   config['ssh']['admin_alias'], shlex.join(['sudo', '-n', '/usr/bin/python3', '-c',
                   files['infrastructure/live-setup/remote.py'].decode(), 'receive', '--stage-sha256', expected])]
        result = subprocess.run(command, stdin=archive_file, capture_output=True, timeout=600)
    require(result.returncode == 0 and len(result.stdout) <= 65536, 'stage_upload_failed')
    response = json.loads(result.stdout)
    require(response.get('stage_sha256') == expected
            and response.get('stage') == '/opt/kirocrew-demo/setup-stages/' + expected, 'stage_receipt_mismatch')
    return response


def aws_command(config, operation, **payload):
    args = ['aws', '--region', config['aws']['region'], '--output', 'json', '--no-cli-pager']
    if config['aws']['profile']:
        args += ['--profile', config['aws']['profile']]
    args += ['s3api', operation, '--cli-input-json', json.dumps(payload)]
    return args


def existing_fixture(config, bucket, key, target):
    args = aws_command(config, 'head-object', Bucket=bucket, Key=key, ExpectedBucketOwner=config['aws']['account_id'])
    result = subprocess.run(args, capture_output=True, timeout=45,
                            env={**os.environ, 'AWS_PAGER': '', 'AWS_CLI_AUTO_PROMPT': 'off'})
    if result.returncode:
        # Only the explicit S3 not-found response permits creation. AccessDenied stays an error.
        text = result.stderr.decode('utf-8', 'replace')
        require('An error occurred (404)' in text or 'An error occurred (NoSuchKey)' in text,
                'fixture_head_failed')
        return None
    head = json.loads(result.stdout)
    require(type(head.get('ContentLength')) is int and 0 <= head['ContentLength'] <= 4096, 'existing_fixture_too_large')
    run(aws_command(config, 'get-object', Bucket=bucket, Key=key, ExpectedBucketOwner=config['aws']['account_id'])
        + [str(target)], timeout=45)
    return read_regular(target, 4096)


def save_fixture_digest(config, digest):
    path = Path(config['_config_path'])
    original = read_regular(path, 65536)
    data = json.loads(original)
    data.setdefault('probe', {})['expected_allowed_sha256'] = digest
    replacement = (json.dumps(data, indent=2) + '\n').encode()
    if original == replacement:
        return False
    cloud = module('live_setup_cloud_fixture', ROOT / 'scripts/demo-cloud.py')
    cloud.atomic_backup_write(path, original, replacement)
    return True


def seed_fixtures(config, context, payloads):
    bucket = context['outputs']['DemoBucketName']
    results = []
    with tempfile.TemporaryDirectory(prefix='kirocrew-fixtures-') as directory:
        directory = Path(directory)
        observed = {}
        for index, (key, raw) in enumerate(payloads.items()):
            observed[key] = existing_fixture(config, bucket, key, directory / ('existing-' + str(index)))
            require(observed[key] is None or observed[key] == raw, 'existing_fixture_differs_no_overwrite_' + key)
        for index, (key, raw) in enumerate(payloads.items()):
            created = observed[key] is None
            if created:
                source = directory / ('input-' + str(index))
                source.write_bytes(raw)
                source.chmod(0o600)
                run(aws_command(config, 'put-object', Bucket=bucket, Key=key,
                                ExpectedBucketOwner=config['aws']['account_id'], IfNoneMatch='*', ContentType='text/plain',
                                ChecksumAlgorithm='SHA256') + ['--body', str(source)], timeout=45)
            actual = existing_fixture(config, bucket, key, directory / ('verified-' + str(index)))
            require(actual == raw, 'fixture_post_write_mismatch')
            results.append({'key': key, 'bytes': len(raw), 'sha256': sha(raw), 'created': created})
    updated = save_fixture_digest(config, sha(payloads['allowed/sentinel.txt']))
    return {'bucket': bucket, 'objects': results, 'config_digest_updated': updated,
            'native_enforcement_verified': False}


def plan(config, args):
    layout(config)
    info = {'schema_version': 1, 'stage': args.stage, 'applied': False, 'network_calls': False,
            'target': {'account': config['aws']['account_id'], 'region': config['aws']['region'],
                       'stack': config['aws']['stack_name'], 'admin_alias': config['ssh']['admin_alias']},
            'apply_checks': ['account and stack ownership', 'existing VPC and subnet', 'single SSH /32 ingress',
                             'pinned SSH host identity', 'SSH address matches stack instance'],
            'manual_acceptance': ['Kiro CLI sign-in through its own fresh login flow',
                                  'Reopen KiroCrew and select the configured remote host',
                                  'Observe actual native control denials and admin telemetry in the UI']}
    if args.stage in ('runtime', 'services'):
        require(args.bundle, 'select_verified_bundle_with_--bundle')
        expected = getattr(args, 'manifest_sha256', None)
        require(not getattr(args, 'apply', False) or expected, 'applied_install_requires_reviewed_--manifest-sha256')
        bundle, bound = verify_bundle(args.bundle, expected)
        info.update(bundle_manifest_sha256=bound, bundle_path=str(bundle), fresh_install_only=True)
    if args.stage == 'fixtures':
        info['objects'] = [{'key': key, 'bytes': len(raw), 'sha256': sha(raw)} for key, raw in fixture_payloads(args).items()]
        info['collision_behavior'] = 'Identical objects are accepted; different existing bytes are refused. Creation is conditional.'
        info['updates'] = 'Backup config and set probe.expected_allowed_sha256 after both object readbacks match.'
    if args.stage == 'server-integrations':
        info.update(root_owner_helper=True, server_timer_seconds=config['telemetry']['interval_seconds'],
                    native_telemetry={'enabled': True, 'otlp_endpoint': '', 'beacon_enabled': False},
                    app='Stage reviewed demo-observability 1.0.1 bytes; app stage installs and enables them.',
                    gateway_restart='Required only if native telemetry configuration changes; supply --restart-gateway.')
    if args.stage == 'desktop':
        from live_setup_desktop import desktop_definition
        info['desktop'] = desktop_definition(config)
    if args.stage == 'app':
        from live_setup_app import install_app
        info['app'] = asyncio.run(install_app(config, apply=False))
    if args.stage == 'client-telemetry':
        info['command'] = [sys.executable, str(ROOT / 'scripts/demo-telemetry.py'), 'setup',
                           '--config', config['_config_path'], '--apply']
    if args.stage == 'managed-policy':
        info['entrypoint'] = 'scripts/manage-enterprise-policy.py'
        info['steps'] = ['preflight', 'apply from saved preflight receipt',
                         'activate only with --restart-gateway', 'verify']
        info['restart_gateway'] = args.restart_gateway
    if args.stage == 'mcp-user-ui':
        info['entrypoint'] = 'scripts/manage-demo-mcp.py'
        info['steps'] = ['plan', 'apply from saved plan receipt', 'verify']
        info['retire_mutable_deny'] = args.retire_mutable_deny
    if args.stage == 'host-controls':
        info['entrypoint'] = 'scripts/configure-host-controls.py'
        info['steps'] = ['preflight', 'additive apply from saved preflight receipt']
        info['native_enforcement_verified'] = False
    return info


def policy_stage(config, args):
    """Delegate to the policy owner; store its nonsecret results in a private fresh directory."""
    require(args.receipt_dir, 'policy_stages_require_fresh_--receipt-dir')
    directory = Path(args.receipt_dir).expanduser().absolute()
    require(not directory.exists() and not directory.is_symlink(), 'receipt_directory_must_be_new')
    directory.parent.mkdir(parents=True, exist_ok=True)
    require(directory.parent.resolve() == directory.parent and directory.parent.stat().st_uid == os.getuid()
            and not directory.parent.stat().st_mode & 0o022, 'unsafe_receipt_parent')
    directory.mkdir(mode=0o700)
    entry = ROOT / 'scripts' / {'managed-policy': 'manage-enterprise-policy.py', 'mcp-user-ui': 'manage-demo-mcp.py',
                                'host-controls': 'configure-host-controls.py'}[args.stage]
    base = [sys.executable, str(entry)]
    common = ['--config', config['_config_path']]
    def operation(name, options=()):
        raw = run(base + [name] + common + list(options), timeout=180)
        result = json.loads(raw)
        require(isinstance(result, dict), 'delegated_receipt_must_be_object')
        path = directory / (name + '.json')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(raw)
        return path
    if args.stage == 'host-controls':
        preflight = operation('preflight')
        operation('apply', ['--apply', '--preflight-receipt', str(preflight)])
        return {'receipts': str(directory), 'host_fixtures_installed': True, 'native_enforcement_verified': False}
    if args.stage == 'managed-policy':
        preflight = operation('preflight')
        installed = operation('apply', ['--apply', '--receipt', str(preflight)])
        if args.restart_gateway:
            operation('activate', ['--apply', '--receipt', str(installed)])
        operation('verify', ['--receipt', str(installed)])
        return {'receipts': str(directory), 'policy_installed': True, 'activation_requested': args.restart_gateway,
                'native_enforcement_verified': False}
    options = ['--retire-mutable-deny'] if args.retire_mutable_deny else []
    require(not args.retire_mutable_deny or args.restart_gateway, 'mutable_hook_retirement_requires_--restart-gateway')
    planned = operation('plan', options)
    apply_options = options + ['--apply', '--plan-receipt', str(planned)]
    if args.restart_gateway:
        apply_options += ['--restart-gateway']
    installed = operation('apply', apply_options)
    operation('verify', options)
    return {'receipts': str(directory), 'mcp_user_ui_configured': True, 'native_enforcement_verified': False}


def telemetry_result(raw):
    """Existing setup prints one upload receipt followed by its timer receipt."""
    decoder = json.JSONDecoder()
    text = raw.decode()
    receipts = []
    while text.strip():
        text = text.lstrip()
        receipt, offset = decoder.raw_decode(text)
        require(isinstance(receipt, dict) and len(receipts) < 3, 'unexpected_telemetry_output')
        receipts.append(receipt)
        text = text[offset:]
    require(receipts and receipts[-1].get('applied') is True and isinstance(receipts[-1].get('client_timer'), str),
            'client_timer_receipt_missing')
    return receipts[-1]


def apply(config, args):
    context = validated_context(config)
    if args.stage == 'fixtures':
        result = seed_fixtures(config, context, fixture_payloads(args))
    elif args.stage == 'desktop':
        from live_setup_desktop import apply_desktop
        result = apply_desktop(config)
    elif args.stage == 'app':
        from live_setup_app import install_app
        result = asyncio.run(install_app(config, apply=True))
    elif args.stage == 'client-telemetry':
        require(sys.platform == 'darwin', 'macos_endpoint_required')
        result = {'client_timer': telemetry_result(run([sys.executable, str(ROOT / 'scripts/demo-telemetry.py'), 'setup',
                      '--config', config['_config_path'], '--apply'], timeout=90))}
    elif args.stage in ('managed-policy', 'mcp-user-ui', 'host-controls'):
        result = policy_stage(config, args)
    else:
        bundle, bundle_sha = verify_bundle(args.bundle, args.manifest_sha256) if args.stage in ('runtime', 'services') else (None, None)
        files, manifest = stage_inputs(config, args.stage, bundle, bundle_sha)
        staged = upload_stage(config, files, manifest)
        stage = staged['stage']
        if args.stage == 'runtime':
            argv = ['sudo', '-n', '/usr/bin/python3', stage + '/bundle/install-runtime-bundle.py', 'install',
                    '--bundle', stage + '/bundle', '--manifest-sha256', bundle_sha]
            # Install logs can include paths. Return only the bounded install receipt from its JSON output.
            response = ssh_run(config, argv, timeout=1500)
            result = {'runtime_installed': True, 'bundle_manifest_sha256': bundle_sha,
                      'installer_output_sha256': sha(response), 'native_acceptance_verified': False}
        else:
            argv = ['sudo', '-n', '/usr/bin/python3', stage + '/infrastructure/live-setup/remote.py',
                    'services' if args.stage == 'services' else 'integrate', '--stage-sha256', staged['stage_sha256']]
            if args.stage == 'services':
                argv += ['--bucket', context['outputs']['DemoBucketName'], '--region', config['aws']['region']]
            if args.restart_gateway:
                argv += ['--restart-gateway']
            result = json.loads(ssh_run(config, argv, timeout=1300))
        result['stage_sha256'] = staged['stage_sha256']
    return {'schema_version': 1, 'stage': args.stage, 'applied': True, 'result': result,
            'instance': context['instance']['InstanceId'], 'native_ui_acceptance': 'requires new observation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=STAGES)
    parser.add_argument('--config', help='Explicit project deployment JSON or KIRO_DEMO_CONFIG.')
    parser.add_argument('--bundle', help='Prepared manifest-driven ARM bundle directory.')
    parser.add_argument('--manifest-sha256', help='Reviewed bundle digest; required for applied runtime/services stages.')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restart-gateway', action='store_true', help='Permit the native telemetry configuration restart.')
    parser.add_argument('--allowed-file', help='Optional exact non-sensitive allow fixture, 1–4096 bytes.')
    parser.add_argument('--denied-file', help='Optional exact non-sensitive deny fixture, 1–4096 bytes.')
    parser.add_argument('--receipt-dir', help='Fresh private directory for delegated managed-policy or MCP setup receipts.')
    parser.add_argument('--retire-mutable-deny', action='store_true', help='MCP stage only: retire the exact duplicate hook after managed policy verification.')
    args = parser.parse_args()
    config = load_config(args.config, require_target=True)
    planned = plan(config, args)
    result = apply(config, args) if args.apply else planned
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        # Child output, owner tokens and cookie values never appear in errors.
        print(json.dumps({'status': 'refused', 'code': str(error) if isinstance(error, RuntimeError) else type(error).__name__}), file=sys.stderr)
        raise SystemExit(1)
