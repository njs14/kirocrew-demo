import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


m = load('test_live_setup', ROOT / 'scripts/setup-live-demo.py')
r = load('test_live_setup_remote', ROOT / 'infrastructure/live-setup/remote.py')
from demo_config import defaults, load_config


class SetupTests(unittest.TestCase):
    def config(self):
        config = defaults()
        config['aws'].update(account_id='123456789012', stack_name='Demo')
        config['_config_path'] = '/tmp/config with spaces.json'
        return config

    def args(self, stage='fixtures', **extra):
        return argparse.Namespace(stage=stage, bundle=None, allowed_file=None, denied_file=None,
                                  restart_gateway=False, receipt_dir=None, retire_mutable_deny=False, **extra)

    def test_fixture_plan_is_offline_and_exact(self):
        with patch.object(m.subprocess, 'run', side_effect=AssertionError('network/process forbidden')):
            result = m.plan(self.config(), self.args())
        self.assertFalse(result['network_calls'])
        self.assertEqual([entry['key'] for entry in result['objects']], list(m.FIXTURES))
        self.assertTrue(all(entry['bytes'] <= 4096 for entry in result['objects']))

    def test_unknown_remote_layout_rejected_before_network(self):
        config = self.config()
        config['ssh']['remote_port'] = 9999
        with self.assertRaisesRegex(RuntimeError, 'documented_demo_layout'):
            m.plan(config, self.args())

    def test_apply_requires_reviewed_bundle_digest_before_process(self):
        args = self.args('runtime')
        args.apply, args.bundle = True, '/missing/bundle'
        with patch.object(m.subprocess, 'run', side_effect=AssertionError('must not run')):
            with self.assertRaisesRegex(RuntimeError, 'reviewed_--manifest-sha256'):
                m.plan(self.config(), args)

    def test_changed_bundle_rejected_before_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve()
            (path / 'manifest.json').write_bytes(b'{"replaced":true}')
            with patch.object(m.subprocess, 'run', side_effect=AssertionError('must not run')):
                with self.assertRaisesRegex(RuntimeError, 'bundle_changed_since_reviewed_plan'):
                    m.verify_bundle(path, 'a' * 64)

    def test_installer_changed_after_verification_refused_before_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory).resolve()
            installer = bundle / 'install-runtime-bundle.py'
            installer.write_bytes(b'reviewed installer')
            manifest = json.dumps({'files': [{'path': installer.name, 'bytes': installer.stat().st_size,
                                              'sha256': hashlib.sha256(installer.read_bytes()).hexdigest()}]}).encode()
            (bundle / 'manifest.json').write_bytes(manifest)
            expected = hashlib.sha256(manifest).hexdigest()
            args = self.args('runtime')
            args.bundle, args.manifest_sha256 = str(bundle), expected
            def verified_then_changed(*unused):
                installer.write_bytes(b'changed installer')
                return bundle, expected
            with patch.object(m, 'validated_context', return_value={}), \
                 patch.object(m, 'verify_bundle', side_effect=verified_then_changed), \
                 patch.object(m, 'upload_stage') as upload:
                with self.assertRaisesRegex(RuntimeError, 'bundle_member_changed_during_staging'):
                    m.apply(self.config(), args)
            upload.assert_not_called()

    def test_manifest_changed_after_verification_refused_before_staging(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory).resolve()
            (bundle / 'manifest.json').write_bytes(b'{"files":[]}')
            with self.assertRaisesRegex(RuntimeError, 'bundle_manifest_changed_during_staging'):
                m.stage_inputs(self.config(), 'runtime', bundle, 'a' * 64)

    def test_file_with_spaces_and_symlink(self):
        with tempfile.TemporaryDirectory(prefix='setup space ') as directory:
            path = Path(directory) / 'canary data.txt'
            path.write_bytes(b'public fixture\n')
            args = self.args()
            args.allowed_file = str(path)
            self.assertEqual(m.fixture_payloads(args)['allowed/sentinel.txt'], b'public fixture\n')
            alias = Path(directory) / 'alias'
            alias.symlink_to(path)
            args.allowed_file = str(alias)
            with self.assertRaisesRegex(RuntimeError, 'symlink'):
                m.fixture_payloads(args)

    def test_large_or_empty_fixtures_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture'
            args = self.args()
            args.allowed_file = str(path)
            for raw in (b'', b'x' * 4097):
                path.write_bytes(raw)
                with self.assertRaises(RuntimeError):
                    m.fixture_payloads(args)

    def test_stage_parameters_and_hashes(self):
        config = self.config()
        config['ssh']['local_port'] = 6500
        files, manifest = m.stage_inputs(config, 'services')
        self.assertIn(b'KIROCREW_ALLOWED_LOOPBACK_PORTS=6500', files['infrastructure/kirocrew-demo.service'])
        for entry in json.loads(manifest)['files']:
            self.assertEqual(entry['sha256'], hashlib.sha256(files[entry['path']]).hexdigest())
        config['telemetry']['interval_seconds'] = 90
        files, _ = m.stage_inputs(config, 'server-integrations')
        self.assertIn(b'OnUnitActiveSec=90s', files['infrastructure/observability-collector/kirocrew-demo-observability.timer'])

    def test_collision_checks_both_before_any_write(self):
        config = self.config()
        context = {'outputs': {'DemoBucketName': 'demo-bucket'}}
        with patch.object(m, 'existing_fixture', side_effect=[None, b'other']), patch.object(m, 'run') as execute:
            with self.assertRaisesRegex(RuntimeError, 'existing_fixture_differs'):
                m.seed_fixtures(config, context, m.FIXTURES)
        execute.assert_not_called()

    def test_fixture_creation_conditional_and_readback(self):
        config = self.config()
        context = {'outputs': {'DemoBucketName': 'demo-bucket'}}
        with patch.object(m, 'existing_fixture', side_effect=[None, None, *m.FIXTURES.values()]), \
             patch.object(m, 'run', return_value=b'{}') as execute, patch.object(m, 'save_fixture_digest', return_value=True):
            result = m.seed_fixtures(config, context, m.FIXTURES)
        self.assertEqual(len(execute.call_args_list), 2)
        for call in execute.call_args_list:
            argv = call.args[0]
            payload = json.loads(argv[argv.index('--cli-input-json') + 1])
            self.assertEqual(payload['IfNoneMatch'], '*')
            self.assertEqual(payload['ExpectedBucketOwner'], config['aws']['account_id'])
            self.assertIn('--body', argv)
        self.assertFalse(result['native_enforcement_verified'])

    def test_same_fixtures_not_rewritten(self):
        values = list(m.FIXTURES.values())
        with patch.object(m, 'existing_fixture', side_effect=values + values), \
             patch.object(m, 'run') as execute, patch.object(m, 'save_fixture_digest', return_value=False):
            result = m.seed_fixtures(self.config(), {'outputs': {'DemoBucketName': 'demo-bucket'}}, m.FIXTURES)
        execute.assert_not_called()
        self.assertTrue(all(not row['created'] for row in result['objects']))

    def test_digest_update_preserves_config_and_creates_backup(self):
        with tempfile.TemporaryDirectory(prefix='live config space ') as directory:
            path = Path(directory) / 'deployment.json'
            raw = {'schema_version': 1, 'aws': {'account_id': '123456789012', 'stack_name': 'Demo'},
                   'ssh': {'local_port': 6500}, 'probe': {'port': 5609}}
            path.write_text(json.dumps(raw))
            config = load_config(path, require_target=True)
            self.assertTrue(m.save_fixture_digest(config, 'a' * 64))
            changed = json.loads(path.read_text())
            self.assertEqual(changed['ssh'], raw['ssh'])
            self.assertEqual(changed['probe']['port'], 5609)
            self.assertEqual(changed['probe']['expected_allowed_sha256'], 'a' * 64)
            self.assertEqual(len(list(path.parent.glob('*.before-demo-cloud-*'))), 1)

    def test_access_denied_is_not_absence(self):
        reply = argparse.Namespace(returncode=254, stderr=b'An error occurred (403)', stdout=b'')
        with patch.object(m.subprocess, 'run', return_value=reply):
            with self.assertRaisesRegex(RuntimeError, 'fixture_head_failed'):
                m.existing_fixture(self.config(), 'demo-bucket', 'allowed/sentinel.txt', Path('/tmp/unused'))

    def test_managed_policy_plan_does_not_activate(self):
        with patch.object(m.subprocess, 'run', side_effect=AssertionError('network forbidden')):
            result = m.plan(self.config(), self.args('managed-policy'))
        self.assertFalse(result['restart_gateway'])
        self.assertIn('activate only with --restart-gateway', result['steps'])

    def test_client_timer_multiple_receipts(self):
        raw = b'{"uploaded":true}\n{"applied":true,"client_timer":"demo.timer","interval_seconds":60}\n'
        self.assertEqual(m.telemetry_result(raw)['client_timer'], 'demo.timer')
        with self.assertRaisesRegex(RuntimeError, 'client_timer_receipt_missing'):
            m.telemetry_result(b'{"uploaded":true}')

    def test_managed_policy_activation_is_explicit(self):
        for activation in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                args = self.args('managed-policy')
                args.restart_gateway = activation
                args.receipt_dir = str(Path(directory).resolve() / 'receipts with spaces')
                with patch.object(m, 'run', return_value=b'{"kind":"receipt"}') as execute:
                    result = m.policy_stage(self.config(), args)
                actions = [call.args[0][2] for call in execute.call_args_list]
                self.assertEqual('activate' in actions, activation)
                self.assertEqual(result['activation_requested'], activation)
                self.assertEqual((Path(args.receipt_dir) / 'apply.json').stat().st_mode & 0o777, 0o600)

    def test_host_fixture_stage_uses_saved_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            args = self.args('host-controls')
            args.receipt_dir = str(Path(directory).resolve() / 'new host receipts')
            with patch.object(m, 'run', return_value=b'{"kind":"host_controls_setup"}') as execute:
                result = m.policy_stage(self.config(), args)
            self.assertEqual([call.args[0][2] for call in execute.call_args_list], ['preflight', 'apply'])
            self.assertIn('--preflight-receipt', execute.call_args_list[-1].args[0])
            self.assertFalse(result['native_enforcement_verified'])


class RemoteTests(unittest.TestCase):
    def entry(self, name='file', raw=b'public'):
        return {'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def archive(self, entries):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for name, raw in entries:
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                archive.addfile(info, io.BytesIO(raw))
        stream.seek(0)
        return stream

    def test_inventory_rejects_traversal_duplicates_ancestor_collision(self):
        for entries in ([self.entry('../escape')], [self.entry(), self.entry()],
                        [self.entry('folder'), self.entry('folder/file')], [self.entry('/absolute')]):
            with self.assertRaises(RuntimeError):
                r.validate_inventory({'schema_version': 1, 'files': entries})

    def test_stream_receiver_hash_bound_and_idempotent(self):
        raw = b'public'
        manifest = json.dumps({'schema_version': 1, 'files': [self.entry('nested/file', raw)]}).encode()
        expected = hashlib.sha256(manifest).hexdigest()
        with tempfile.TemporaryDirectory() as directory, patch.object(r, 'STAGE_ROOT', Path(directory)), \
             patch.object(r, 'trusted_dir'), patch.object(r, 'verify_stage'):
            result = r.receive(expected, self.archive([('stage-manifest.json', manifest), ('nested/file', raw)]))
            self.assertEqual((Path(result['stage']) / 'nested/file').read_bytes(), raw)
            r.receive(expected, self.archive([('stage-manifest.json', manifest), ('nested/file', raw)]))

    def test_stream_rejects_extra_before_publication(self):
        manifest = json.dumps({'schema_version': 1, 'files': []}).encode()
        expected = hashlib.sha256(manifest).hexdigest()
        with tempfile.TemporaryDirectory() as directory, patch.object(r, 'STAGE_ROOT', Path(directory)), patch.object(r, 'trusted_dir'):
            with self.assertRaisesRegex(RuntimeError, 'unexpected_archive_entry'):
                r.receive(expected, self.archive([('stage-manifest.json', manifest), ('extra', b'no')]))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_telemetry_preserves_other_values_and_is_idempotent(self):
        original = {'default_agent': 'enforcement-demo', 'hooks': {'custom': 'preserve'},
                    'telemetry': {'extra': 'preserve', 'enabled': False}}
        changed = r.telemetry_replacement(json.dumps(original).encode())
        data = json.loads(changed)
        self.assertEqual(data['hooks'], original['hooks'])
        self.assertEqual(data['telemetry']['extra'], 'preserve')
        self.assertEqual(data['telemetry']['otlp_endpoint'], '')
        self.assertFalse(data['telemetry']['beacon_enabled'])
        self.assertEqual(r.telemetry_replacement(changed), changed)


if __name__ == '__main__':
    unittest.main()
