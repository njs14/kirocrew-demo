"""Offline lifecycle checks for the additive root-managed demo policy.

The fake resolver is a fixture for orchestration only. These tests do not claim
to validate KiroCrew's real policy parser or native enforcement.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MANAGE = load_module("enterprise_policy_manage", ROOT / "infrastructure/enterprise-policy/manage.py")
WRAPPER = load_module("enterprise_policy_wrapper", ROOT / "scripts/manage-enterprise-policy.py")
TEMPLATE = (ROOT / "infrastructure/enterprise-policy/policy.template.json").read_text()
BUILTIN_PATTERN = r"aws(?:\s+--?[a-z-]+(?:[= ]\S+)?)*\s+s3(?:\s+--?[a-z-]+(?:[= ]\S+)?)*\s+cp .* s3://.*"


class FixtureGovernance:
    @staticmethod
    def parse_policy(value):
        result = dict(value)
        result["sandbox.min_level"] = SimpleNamespace(value=value["sandbox"]["min_level"])
        return result

    @staticmethod
    def resolve(ceiling, _local, scope, item):
        entry = ceiling.get(scope, {})
        denied = any(fnmatch.fnmatchcase(item, pattern) for pattern in entry.get("deny", []))
        return SimpleNamespace(permitted=not denied, layer="enterprise" if denied else "default")


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tree = MANAGE.Tree(str(self.root), root_uid=os.getuid())
        self.source_root = "/opt/kirocrew/package/kiro_crew"
        self.crew = SimpleNamespace(pw_uid=os.getuid() or 999, pw_gid=os.getgid(), pw_dir="/home/crew")
        self.service = "demo-gateway.service"
        self.unit = "/etc/systemd/system/" + self.service
        self.unrelated = self.unit + ".d/20-existing-observability.conf"
        self.dropin = self.unit + ".d/60-kirocrew-enterprise-policy.conf"
        self.state = "/var/lib/kirocrew"
        self.config = {"agent": {"approval_mode": "interactive"}, "hooks": {},
                       "presentation_fixture": {"preserve": [1, 2, 3]}}
        self.write("/etc/machine-id", b"fixture-machine-id\n")
        self.write(self.unit, b"[Service]\nUser=crew\nExecStart=/opt/kirocrew/run\n")
        self.write(self.unrelated, b"[Service]\nEnvironment=UNRELATED_SETTING=keep\n")
        self.write(self.state + "/config.json", MANAGE.encoded(self.config), 0o600)
        for name in MANAGE.SOURCE_FILES:
            self.write(self.source_root + "/" + name, ("# fixture " + name + "\n").encode())
        self.write(self.source_root + "/security/denied_rules.py",
                   ("BUILTIN_DENIED_RULES = [DeniedCommandRule(id='credential-exfil-s3-cp', pattern=" +
                    repr(BUILTIN_PATTERN) + ")]\n").encode())
        self.request = {"mode": "plan", "service": self.service, "state_dir": self.state,
                        "installer_sha256": MANAGE.sha(b"fixture-reviewed-installer"),
                        "deployment": {"region": "us-east-1", "account_id": "111122223333",
                                       "stack_name": "fixture-demo", "instance_id": "i-0123456789abcdef0"},
                        "template": TEMPLATE, "apply": False}
        self.active = False
        self.process_stale = False
        self.fail_closed = "fail_closed"
        self.device_policy = "auto"
        self.device_allow = ""
        self.started = "1000"
        self.commands = []
        self.run_patch = mock.patch.object(MANAGE, "run", side_effect=self.fake_run)
        self.run_patch.start()
        self.addCleanup(self.run_patch.stop)
        self.sleep_patch = mock.patch.object(MANAGE.time, "sleep")
        self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

    def path(self, path):
        return self.root / path.lstrip("/")

    def write(self, path, data, mode=0o644):
        local = self.path(path)
        local.parent.mkdir(parents=True, exist_ok=True)
        for ancestor in [local.parent, *local.parent.parents]:
            if ancestor == self.root:
                break
            ancestor.chmod(0o755)
        local.write_bytes(data)
        local.chmod(mode)

    def inventory(self):
        return {str(path.relative_to(self.root)): (stat.S_IMODE(path.lstat().st_mode),
                path.read_bytes() if path.is_file() else None)
                for path in self.root.rglob("*")}

    def snapshot(self, service, tree):
        self.assertEqual(service, self.service)
        files = {path: tree.read(path)[1] for path in (self.unit, self.unrelated)}
        if self.path(self.dropin).exists():
            files[self.dropin] = tree.read(self.dropin)[1]
        environment = {"KIROCREW_POLICY_URL": "file://" + MANAGE.POLICY,
                       "KIROCREW_POLICY_ON_UNAVAILABLE": self.fail_closed} if self.active else {}
        return {"files": files, "unit_environment_sha256": MANAGE.sha(MANAGE.encoded(environment)),
                "policy_environment": environment,
                "process_policy_environment": {} if self.process_stale else dict(environment),
                "state_dir": self.state, "main_pid": 42, "active_state": "active",
                "started": self.started, "user": "crew", "device_policy": self.device_policy,
                "device_allow": self.device_allow}

    def fake_run(self, command):
        self.commands.append(command)
        if command == ["systemctl", "restart", self.service]:
            self.started = str(int(self.started) + 1)
            self.active = self.path(self.dropin).exists()
            self.device_policy = "strict" if self.active else "auto"
            self.device_allow = " ".join(device + " rw" for device in MANAGE.DEVICES) if self.active else ""
        return ""

    def operate(self, mode="plan", *, snapshotter=None, **fields):
        request = {**self.request, "mode": mode, **fields}
        return MANAGE.operate(request, tree=self.tree, crew=self.crew, source_root=self.source_root,
                              governance=FixtureGovernance, snapshotter=snapshotter or self.snapshot)

    def install(self):
        plan = self.operate()
        result = self.operate("apply", apply=True, expected_plan=plan)
        return plan, result

    def test_plan_and_preflight_are_read_only_and_deterministic(self):
        before = self.inventory()
        plan = self.operate()
        self.assertEqual(plan, self.operate("preflight"))
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)
        self.assertTrue(plan["restart_required"])
        self.assertFalse(plan["native_enforcement_verified"])
        policy = json.loads(plan["files"][MANAGE.POLICY]["content"])
        self.assertIn(self.crew.pw_dir + "/.aws/**", policy["filesystem"]["read"]["deny"])
        self.assertIn(self.source_root + "/**", policy["filesystem"]["write"]["deny"])

    def test_apply_requires_exact_plan_and_explicit_flag(self):
        plan = self.operate()
        before = self.inventory()
        for fields in ({"expected_plan": plan}, {"apply": True},
                       {"apply": True, "expected_plan": {**plan, "plan_id": "0" * 64}}):
            with self.subTest(fields=fields.keys()), self.assertRaisesRegex(ValueError, "exact_prior_plan_required"):
                self.operate("apply", **fields)
            self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_source_drift_between_plan_and_apply_rejects_without_writes(self):
        plan = self.operate()
        self.write(self.source_root + "/hooks.py", b"# changed since plan\n")
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "exact_prior_plan_required"):
            self.operate("apply", apply=True, expected_plan=plan)
        self.assertEqual(before, self.inventory())

    def test_user_config_drift_between_plan_and_apply_rejects_without_writes(self):
        plan = self.operate()
        self.config["presentation_fixture"]["new"] = True
        self.write(self.state + "/config.json", MANAGE.encoded(self.config), 0o600)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "exact_prior_plan_required"):
            self.operate("apply", apply=True, expected_plan=plan)
        self.assertEqual(before, self.inventory())

    def test_terminal_patch_rejects_concurrent_chmod_without_overwriting_config(self):
        config_path = self.state + "/config.json"
        local = self.path(config_path)
        original = local.read_bytes()
        original_info = local.stat()
        reader = self.tree.read
        reads = []
        def chmod_before_recheck(path, **kwargs):
            if path == config_path:
                reads.append(path)
                if len(reads) == 2:
                    local.chmod(0o640)
            return reader(path, **kwargs)
        with mock.patch.object(self.tree, "read", side_effect=chmod_before_recheck), \
             mock.patch.object(MANAGE.os, "replace", wraps=os.replace) as replace:
            with self.assertRaisesRegex(ValueError, "configuration_changed_during_patch"):
                MANAGE.patch_terminal(self.tree, self.state, self.crew,
                                      expected_sha=MANAGE.sha(original))
            replace.assert_not_called()
        self.assertEqual(2, len(reads))
        self.assertEqual(original, local.read_bytes())
        current_info = local.stat()
        self.assertEqual(0o640, stat.S_IMODE(current_info.st_mode))
        self.assertEqual((original_info.st_ino, original_info.st_uid, original_info.st_gid),
                         (current_info.st_ino, current_info.st_uid, current_info.st_gid))
        self.assertEqual([], list(local.parent.glob(".enterprise-config-*")))
        self.assertEqual([], self.commands)

    def test_boot_context_link_drift_invalidates_plan_and_installed_binding(self):
        plan = self.operate()
        context_path = self.source_root + "/platform/context.py"
        original = self.path(context_path).read_bytes()
        self.write(context_path, b"# changed context provider\n")
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "exact_prior_plan_required"):
            self.operate("apply", apply=True, expected_plan=plan)
        self.assertEqual(before, self.inventory())
        self.write(context_path, original)
        plan, _ = self.install()
        self.write(self.source_root + "/platform/bootstrap.py", b"# changed bootstrap loader\n")
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "runtime_binding_changed"):
            self.operate("verify", expected_plan_id=plan["plan_id"])
        self.assertEqual(before, self.inventory())

    def test_symlink_in_destination_ancestry_is_rejected(self):
        self.path("/etc/kirocrew-demo").symlink_to(self.path(self.state), target_is_directory=True)
        with self.assertRaises(OSError):
            self.operate()
        self.assertFalse(self.path(self.state + "/security-policy.json").exists())

    def test_writable_destination_ancestor_is_rejected(self):
        self.path("/etc/systemd").chmod(0o777)
        with self.assertRaisesRegex(ValueError, "unprotected_directory_ancestor"):
            self.operate()
        self.assertFalse(self.path(MANAGE.POLICY).exists())

    def test_symlink_or_writable_source_is_rejected(self):
        source = self.path(self.source_root + "/hooks.py")
        source.unlink()
        source.symlink_to(self.path(self.source_root + "/sandbox.py"))
        with self.assertRaises(OSError):
            self.operate()
        source.unlink()
        self.write(self.source_root + "/hooks.py", b"# mutable source\n", 0o666)
        with self.assertRaisesRegex(ValueError, "unprotected_file"):
            self.operate()

    def test_config_with_automatic_approval_is_not_adopted(self):
        self.config["agent"]["dangerouslySkipPermissions"] = True
        self.write(self.state + "/config.json", MANAGE.encoded(self.config), 0o600)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "interactive_approval_required"):
            self.operate()
        self.assertEqual(before, self.inventory())

    def test_existing_policy_configuration_is_not_overwritten(self):
        self.active = True
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "existing_policy_environment_requires_manual_review"):
            self.operate()
        self.assertEqual(before, self.inventory())

    def test_existing_device_exceptions_are_not_adopted(self):
        self.device_allow = "/dev/pts/ptmx rw"
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "existing_device_rules_require_manual_review"):
            self.operate()
        self.assertEqual(before, self.inventory())

    def test_changed_builtin_command_pattern_requires_manual_reconciliation(self):
        self.write(self.source_root + "/security/denied_rules.py",
                   b"BUILTIN_DENIED_RULES = [DeniedCommandRule(id='credential-exfil-s3-cp', pattern='changed')]\n")
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "builtin_command_pattern_mismatch"):
            self.operate()
        self.assertEqual(before, self.inventory())

    def test_service_snapshot_excludes_unrelated_environment_values(self):
        unit_environment = ('KIROCREW_HOME=/var/lib/kirocrew '
                            'KIROCREW_POLICY_URL=file:///etc/kirocrew-demo/security-policy.json '
                            'KIROCREW_POLICY_ON_UNAVAILABLE=fail_closed '
                            'UNRELATED_AUTH=unit-fixture-secret-value')
        raw = (f"User=crew\nGroup=crew\nFragmentPath={self.unit}\nDropInPaths={self.unrelated}\n"
               f"Environment={unit_environment}\nMainPID=42\nActiveState=active\n"
               "ExecMainStartTimestampMonotonic=1000\n")
        proc = (b"KIROCREW_POLICY_URL=file:///etc/kirocrew-demo/security-policy.json\0"
                b"KIROCREW_POLICY_ON_UNAVAILABLE=fail_closed\0"
                b"UNRELATED_AUTH=process-fixture-secret-value\0")
        with mock.patch.object(MANAGE, "run", return_value=raw), \
             mock.patch("builtins.open", return_value=io.BytesIO(proc)) as opened:
            result = MANAGE.service_snapshot(self.service, self.tree)
        opened.assert_called_once_with("/proc/42/environ", "rb")
        self.assertEqual({"KIROCREW_POLICY_URL": "file://" + MANAGE.POLICY,
                          "KIROCREW_POLICY_ON_UNAVAILABLE": "fail_closed"}, result["process_policy_environment"])
        self.assertEqual(result["process_policy_environment"], result["policy_environment"])
        serialized = json.dumps(result)
        self.assertNotIn("unit-fixture-secret-value", serialized)
        self.assertNotIn("process-fixture-secret-value", serialized)
        self.assertNotIn("UNRELATED_AUTH", serialized)

    def test_repeated_systemctl_device_allow_lines_verify_all_five_rules(self):
        plan, _ = self.install()
        raw = (f"User=crew\nGroup=crew\nFragmentPath={self.unit}\n"
               f"DropInPaths={self.unrelated} {self.dropin}\n"
               f"Environment=KIROCREW_HOME={self.state} "
               f"KIROCREW_POLICY_URL=file://{MANAGE.POLICY} "
               "KIROCREW_POLICY_ON_UNAVAILABLE=fail_closed\n"
               "MainPID=133032\nActiveState=active\nExecMainStartTimestampMonotonic=1002\n"
               "DevicePolicy=strict\n" +
               "".join(f"DeviceAllow={device} rw\n" for device in MANAGE.DEVICES))
        proc = (f"KIROCREW_POLICY_URL=file://{MANAGE.POLICY}\0"
                "KIROCREW_POLICY_ON_UNAVAILABLE=fail_closed\0").encode()
        with mock.patch.object(MANAGE, "run", return_value=raw), \
             mock.patch("builtins.open", side_effect=lambda *a, **k: io.BytesIO(proc)):
            snapshot = MANAGE.service_snapshot(self.service, self.tree)
            self.assertEqual(" ".join(device + " rw" for device in MANAGE.DEVICES), snapshot["device_allow"])
            verified = self.operate("verify", expected_plan_id=plan["plan_id"], snapshotter=MANAGE.service_snapshot)
            self.assertTrue(verified["unit_device_policy_matches"])
            raw += "DeviceAllow=/dev/pts/ptmx rw\n"
        with mock.patch.object(MANAGE, "run", return_value=raw), \
             mock.patch("builtins.open", side_effect=lambda *a, **k: io.BytesIO(proc)):
            verified = self.operate("verify", expected_plan_id=plan["plan_id"], snapshotter=MANAGE.service_snapshot)
            self.assertFalse(verified["unit_device_policy_matches"])

    def test_install_changes_only_terminal_flag_and_preserves_dropins_without_activation(self):
        before = self.inventory()
        plan, receipt = self.install()
        self.assertFalse(receipt["activation_performed"])
        self.assertEqual([], self.commands)
        after = self.inventory()
        for path, value in before.items():
            if path == (self.state + "/config.json").lstrip("/"):
                self.assertEqual(value[0], after[path][0])
                continue
            self.assertEqual(value, after[path], path)
        expected_config = {**self.config, "dashboard": {"terminal": {"enabled": False}}}
        self.assertEqual(expected_config, json.loads(self.path(self.state + "/config.json").read_bytes()))
        for path, item in plan["files"].items():
            data, meta = self.tree.read(path)
            self.assertEqual(item["sha256"], MANAGE.sha(data))
            self.assertEqual(item["mode"], meta["mode"])
        self.assertEqual("0o600", self.tree.read(receipt["backup_path"])[1]["mode"])
        config_backup, backup_meta = self.tree.read(receipt["config_backup_path"])
        self.assertEqual("0o600", backup_meta["mode"])
        self.assertEqual(self.config, json.loads(config_backup))
        self.assertEqual(MANAGE.sha(config_backup), receipt["config_backup_sha256"])
        self.assertEqual("0o600", self.tree.read(MANAGE.MANIFEST)[1]["mode"])
        with self.assertRaisesRegex(ValueError, "destination_exists"):
            self.operate("apply", apply=True, expected_plan=plan)
        self.assertEqual(after, self.inventory())

    def test_existing_managed_destination_is_never_overwritten(self):
        original = b"unrelated pre-existing file\n"
        self.write(MANAGE.POLICY, original)
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "destination_exists"):
            self.operate()
        self.assertEqual(before, self.inventory())
        self.assertEqual(original, self.path(MANAGE.POLICY).read_bytes())

    def test_verify_before_activation_does_not_restart_or_claim_active(self):
        plan, _ = self.install()
        before = self.inventory()
        result = self.operate("verify", expected_plan_id=plan["plan_id"])
        self.assertTrue(result["root_protected_managed_files_verified"])
        self.assertFalse(result["unit_and_process_policy_environment_active"])
        self.assertFalse(result["activation_performed"])
        self.assertFalse(result["native_enforcement_verified"])
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_activation_is_explicit_and_observes_new_service_start(self):
        plan, _ = self.install()
        with self.assertRaisesRegex(ValueError, "explicit_mutation_flag_required"):
            self.operate("activate", expected_plan_id=plan["plan_id"])
        self.assertEqual([], self.commands)
        result = self.operate("activate", apply=True, expected_plan_id=plan["plan_id"])
        self.assertEqual([["systemctl", "daemon-reload"], ["systemctl", "restart", self.service]], self.commands)
        self.assertTrue(result["unit_and_process_policy_environment_active"])
        self.assertTrue(result["activation_performed"])
        self.assertTrue(result["unit_device_policy_matches"])
        self.assertTrue(result["dashboard_terminal_disabled"])
        self.assertFalse(result["service_cgroup_pty_denial_verified"])
        self.assertEqual("1001", result["service_start"])
        self.assertFalse(result["native_enforcement_verified"])

    def test_activation_rejects_policy_url_without_fail_closed_environment(self):
        plan, _ = self.install()
        self.fail_closed = "fail_open"
        with self.assertRaisesRegex(ValueError, "managed_environment_not_active"):
            self.operate("activate", apply=True, expected_plan_id=plan["plan_id"])

    def test_loaded_unit_with_stale_running_process_is_not_verified_active(self):
        plan, _ = self.install()
        self.active = True
        self.process_stale = True
        result = self.operate("verify", expected_plan_id=plan["plan_id"])
        self.assertFalse(result["unit_and_process_policy_environment_active"])
        self.assertFalse(result["native_enforcement_verified"])
        self.assertEqual([], self.commands)
        with self.assertRaisesRegex(ValueError, "managed_environment_not_active"):
            self.operate("activate", apply=True, expected_plan_id=plan["plan_id"])

    def test_activation_rejects_unchanged_service_start(self):
        plan, _ = self.install()
        with mock.patch.object(MANAGE, "run", return_value=""):
            with self.assertRaisesRegex(ValueError, "new_service_start_not_observed"):
                self.operate("activate", apply=True, expected_plan_id=plan["plan_id"])

    def test_activation_waits_through_activating_pid_zero_until_active_process(self):
        plan, _ = self.install()
        observations = []
        def restarting_snapshot(service, tree):
            value = self.snapshot(service, tree)
            if self.started == "1000":
                observations.append("before_restart")
            elif len(observations) < 3:
                value.update(active_state="activating", main_pid=0, process_policy_environment={})
                observations.append("activating")
            else:
                observations.append("active")
            return value
        with mock.patch.object(MANAGE.time, "sleep") as wait:
            result = self.operate("activate", apply=True, expected_plan_id=plan["plan_id"],
                                  snapshotter=restarting_snapshot)
        self.assertEqual(["before_restart", "activating", "activating", "active"], observations)
        self.assertEqual(3, wait.call_count)
        self.assertTrue(all(call.args == (0.25,) for call in wait.call_args_list))
        self.assertTrue(result["unit_and_process_policy_environment_active"])
        self.assertEqual("active", result["service_active_state"])
        self.assertGreater(result["main_pid"], 0)
        self.assertEqual("1001", result["service_start"])
        self.assertFalse(result["native_enforcement_verified"])

    def test_activation_rejects_extra_device_grants(self):
        plan, _ = self.install()
        def device_drift(command):
            self.fake_run(command)
            if command == ["systemctl", "restart", self.service]:
                self.device_allow += " /dev/pts/ptmx rw"
            return ""
        with mock.patch.object(MANAGE, "run", side_effect=device_drift):
            with self.assertRaisesRegex(ValueError, "managed_device_policy_not_active"):
                self.operate("activate", apply=True, expected_plan_id=plan["plan_id"])

    def test_failed_manifest_write_restores_terminal_and_removes_only_new_managed_files(self):
        original_config = self.path(self.state + "/config.json").read_bytes()
        original_unrelated = self.path(self.unrelated).read_bytes()
        plan = self.operate()
        writer = self.tree.write_new
        def fail_manifest(path, data, mode=0o644):
            if path == MANAGE.MANIFEST:
                raise OSError("fixture write failure")
            return writer(path, data, mode)
        with mock.patch.object(self.tree, "write_new", side_effect=fail_manifest):
            with self.assertRaisesRegex(OSError, "fixture write failure"):
                self.operate("apply", apply=True, expected_plan=plan)
        self.assertEqual(original_config, self.path(self.state + "/config.json").read_bytes())
        self.assertEqual(original_unrelated, self.path(self.unrelated).read_bytes())
        for path in (*plan["files"], MANAGE.MANIFEST):
            self.assertFalse(self.path(path).exists(), path)
        retained = list(self.path("/etc/kirocrew-demo").glob("enterprise-policy-before-*.json"))
        self.assertEqual(2, len(retained))
        self.assertTrue(all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in retained))
        self.assertEqual([], self.commands)

    def test_verify_and_rollback_require_original_plan_id(self):
        _, _ = self.install()
        before = self.inventory()
        for mode in ("verify", "activate", "rollback"):
            for expected in (None, "0" * 64):
                with self.subTest(mode=mode, expected=expected), self.assertRaisesRegex(ValueError, "exact_installation_receipt_required"):
                    self.operate(mode, apply=True, expected_plan_id=expected)
                self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_changed_managed_file_blocks_verification_and_rollback(self):
        plan, _ = self.install()
        self.path(MANAGE.POLICY).write_bytes(b"{}\n")
        before = self.inventory()
        for mode in ("verify", "activate", "rollback"):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "managed_file_changed"):
                self.operate(mode, apply=True, expected_plan_id=plan["plan_id"])
            self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_changed_managed_mode_blocks_rollback(self):
        plan, _ = self.install()
        self.path(self.dropin).chmod(0o600)
        with self.assertRaisesRegex(ValueError, "managed_file_changed"):
            self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"])
        self.assertTrue(self.path(MANAGE.POLICY).exists())

    def test_machine_or_source_drift_blocks_post_install_actions(self):
        plan, _ = self.install()
        self.write("/etc/machine-id", b"different-host\n")
        before = self.inventory()
        for mode in ("verify", "activate", "rollback"):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "runtime_binding_changed"):
                self.operate(mode, apply=True, expected_plan_id=plan["plan_id"])
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_different_deployment_cannot_reuse_install_receipt(self):
        plan, _ = self.install()
        variants = ({"deployment": {**self.request["deployment"], "account_id": "444455556666"}},)
        before = self.inventory()
        for fields in variants:
            with self.subTest(fields=fields), self.assertRaisesRegex(ValueError, "installation_target_mismatch"):
                self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"], **fields)
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_updated_tool_verifies_older_unchanged_install_without_rebinding_manifest(self):
        plan, _ = self.install()
        before = self.inventory()
        result = self.operate("verify", expected_plan_id=plan["plan_id"], installer_sha256="0" * 64)
        self.assertTrue(result["root_protected_managed_files_verified"])
        self.assertEqual(plan["plan_id"], result["plan_id"])
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_updated_tool_cannot_apply_an_old_plan(self):
        plan = self.operate()
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "exact_prior_plan_required"):
            self.operate("apply", apply=True, expected_plan=plan, installer_sha256="0" * 64)
        self.assertEqual(before, self.inventory())

    def test_unrelated_service_change_blocks_restart_and_rollback(self):
        plan, _ = self.install()
        self.write(self.unrelated, b"[Service]\nEnvironment=CHANGED=1\n")
        before = self.inventory()
        for mode in ("activate", "rollback"):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, "unrelated_service_files_changed"):
                self.operate(mode, apply=True, expected_plan_id=plan["plan_id"])
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_changed_backup_blocks_rollback_without_deleting_managed_files(self):
        plan, receipt = self.install()
        self.path(receipt["backup_path"]).write_bytes(b"changed backup\n")
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "backup_changed"):
            self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"])
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_rollback_restores_only_terminal_flag_preserving_later_config_edits(self):
        self.config["dashboard"] = {"theme": "dark", "terminal": {"enabled": True, "font_size": 14}}
        self.write(self.state + "/config.json", MANAGE.encoded(self.config), 0o640)
        plan, receipt = self.install()
        installed = json.loads(self.path(self.state + "/config.json").read_bytes())
        installed["dashboard"]["theme"] = "light"
        installed["dashboard"]["terminal"]["font_size"] = 16
        installed["later_setting"] = {"keep": True}
        self.write(self.state + "/config.json", MANAGE.encoded(installed), 0o640)
        expected = json.loads(json.dumps(installed))
        expected["dashboard"]["terminal"]["enabled"] = True
        self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"])
        restored, restored_meta = self.tree.read(self.state + "/config.json", root_only=False)
        self.assertEqual(expected, json.loads(restored))
        self.assertEqual("0o640", restored_meta["mode"])
        self.assertEqual(os.getuid(), restored_meta["uid"])
        self.assertEqual(self.config, json.loads(self.tree.read(receipt["config_backup_path"])[0]))

    def test_changed_terminal_flag_is_reported_and_rollback_does_not_override_it(self):
        plan, _ = self.install()
        current = json.loads(self.path(self.state + "/config.json").read_bytes())
        current["dashboard"]["terminal"]["enabled"] = True
        self.write(self.state + "/config.json", MANAGE.encoded(current), 0o600)
        before = self.inventory()
        result = self.operate("verify", expected_plan_id=plan["plan_id"])
        self.assertFalse(result["dashboard_terminal_disabled"])
        with self.assertRaisesRegex(ValueError, "terminal_field_changed"):
            self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"])
        self.assertEqual(before, self.inventory())
        self.assertEqual([], self.commands)

    def test_rollback_removes_only_managed_files_and_retains_backup(self):
        original = self.inventory()
        plan, receipt = self.install()
        backup = self.path(receipt["backup_path"]).read_bytes()
        with self.assertRaisesRegex(ValueError, "explicit_mutation_flag_required"):
            self.operate("rollback", expected_plan_id=plan["plan_id"])
        result = self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"])
        self.assertTrue(result["removed_only_managed_files"])
        self.assertTrue(result["service_restarted"])
        self.assertFalse(result["native_enforcement_verified"])
        for path in (*plan["files"], MANAGE.MANIFEST):
            self.assertFalse(self.path(path).exists(), path)
        remaining = self.inventory()
        for path, value in original.items():
            self.assertEqual(value, remaining[path], path)
        self.assertEqual(backup, self.path(receipt["backup_path"]).read_bytes())
        self.assertEqual([["systemctl", "daemon-reload"], ["systemctl", "restart", self.service]], self.commands)

    def test_failed_pid_zero_service_can_roll_back_without_relaxing_unit_guards(self):
        original_config = self.path(self.state + "/config.json").read_bytes()
        original_unrelated = self.path(self.unrelated).read_bytes()
        plan, receipt = self.install()
        service_user = "crew"
        def failed_service(command):
            if command[:2] == ["systemctl", "show"]:
                return (f"User={service_user}\nGroup=crew\nFragmentPath={self.unit}\n"
                        f"DropInPaths={self.unrelated} {self.dropin}\n"
                        f"Environment=KIROCREW_HOME={self.state} "
                        f"KIROCREW_POLICY_URL=file://{MANAGE.POLICY} "
                        "KIROCREW_POLICY_ON_UNAVAILABLE=fail_closed\n"
                        "MainPID=0\nActiveState=failed\nExecMainStartTimestampMonotonic=1001\n"
                        "DevicePolicy=strict\nDeviceAllow=" +
                        " ".join(device + " rw" for device in MANAGE.DEVICES) + "\n")
            return self.fake_run(command)
        with mock.patch.object(MANAGE, "run", side_effect=failed_service), \
             mock.patch("builtins.open", side_effect=AssertionError("PID zero must not read /proc")) as opened:
            failed_snapshot = MANAGE.service_snapshot(self.service, self.tree)
            self.assertEqual("failed", failed_snapshot["active_state"])
            self.assertEqual(0, failed_snapshot["main_pid"])
            self.assertEqual({}, failed_snapshot["process_policy_environment"])
            before = self.inventory()
            service_user = "root"
            with self.assertRaisesRegex(ValueError, "crew_service_required"):
                self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"],
                             snapshotter=MANAGE.service_snapshot)
            self.assertEqual(before, self.inventory())
            service_user = "crew"
            self.path(self.unrelated).chmod(0o666)
            with self.assertRaisesRegex(ValueError, "unprotected_file"):
                self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"],
                             snapshotter=MANAGE.service_snapshot)
            self.assertTrue(self.path(MANAGE.POLICY).exists())
            self.path(self.unrelated).chmod(0o644)
            result = self.operate("rollback", apply=True, expected_plan_id=plan["plan_id"],
                                  snapshotter=MANAGE.service_snapshot)
            opened.assert_not_called()
        self.assertTrue(result["service_restarted"])
        for path in (*plan["files"], MANAGE.MANIFEST):
            self.assertFalse(self.path(path).exists(), path)
        self.assertEqual(original_config, self.path(self.state + "/config.json").read_bytes())
        self.assertEqual(original_unrelated, self.path(self.unrelated).read_bytes())
        self.assertTrue(self.path(receipt["backup_path"]).exists())
        self.assertEqual([["systemctl", "daemon-reload"], ["systemctl", "restart", self.service]], self.commands)


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = b"# reviewed installer source\n"
        self.config = {"aws": {"region": "us-east-1", "account_id": "111122223333",
                               "stack_name": "fixture-demo", "instance_id": "i-0123456789abcdef0"},
                       "ssh": {"admin_alias": "fixture-demo-admin"}}

    def args(self, action="plan", *extra):
        return WRAPPER.parser().parse_args([action, *extra])

    def receipt(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value))
        return str(path)

    def test_read_only_actions_reject_mutation_flags_or_receipts(self):
        for action in ("preflight", "plan"):
            for extra in (("--apply",), ("--receipt", "unused.json")):
                with self.subTest(action=action, extra=extra), self.assertRaisesRegex(ValueError, "read_only_action_rejects_mutation_options"):
                    WRAPPER.request_for(self.args(action, *extra), self.config, self.source)

    def test_every_mutation_needs_explicit_apply_and_a_prior_receipt(self):
        for action in ("apply", "activate", "rollback"):
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "mutation_requires_apply_flag"):
                WRAPPER.request_for(self.args(action), self.config, self.source)
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "prior_receipt_required"):
                WRAPPER.request_for(self.args(action, "--apply"), self.config, self.source)

    def test_plan_request_binds_only_chosen_deployment_and_reviewed_source(self):
        result = WRAPPER.request_for(self.args("plan", "--service", "other-demo.service",
                                              "--state-dir", "/var/lib/other-demo"), self.config, self.source)
        self.assertEqual(self.config["aws"], result["deployment"])
        self.assertEqual(MANAGE.sha(self.source), result["installer_sha256"])
        self.assertEqual("other-demo.service", result["service"])
        self.assertEqual("/var/lib/other-demo", result["state_dir"])
        self.assertFalse(result["apply"])

    def test_apply_accepts_only_plan_and_other_actions_only_install_receipt(self):
        plan = {"kind": "enterprise_policy_plan", "schema_version": 1, "plan_id": "a" * 64}
        install = {"kind": "enterprise_policy_install", "schema_version": 1, "plan": plan}
        plan_path = self.receipt("plan.json", plan)
        install_path = self.receipt("install.json", install)
        result = WRAPPER.request_for(self.args("apply", "--apply", "--receipt", plan_path), self.config, self.source)
        self.assertEqual(plan, result["expected_plan"])
        with self.assertRaisesRegex(ValueError, "prior_plan_required"):
            WRAPPER.request_for(self.args("apply", "--apply", "--receipt", install_path), self.config, self.source)
        for action in ("verify", "activate", "rollback"):
            extra = () if action == "verify" else ("--apply",)
            result = WRAPPER.request_for(self.args(action, *extra, "--receipt", install_path), self.config, self.source)
            self.assertEqual(plan["plan_id"], result["expected_plan_id"])
            with self.subTest(action=action), self.assertRaisesRegex(ValueError, "prior_install_receipt_required"):
                WRAPPER.request_for(self.args(action, *extra, "--receipt", plan_path), self.config, self.source)

    def test_remote_path_arguments_reject_traversal_or_shell_syntax(self):
        for value in ("relative/path", "/tmp/../policy", "/tmp/with space", "/tmp/$(id)", "/tmp/x;id"):
            with self.subTest(value=value), self.assertRaises(argparse.ArgumentTypeError):
                WRAPPER.absolute(value)

    def test_execute_uses_explicit_target_pinned_options_and_source_stdin(self):
        args = self.args("plan", "--config", str(self.directory / "deployment.json"))
        response = SimpleNamespace(returncode=0, stdout=b'{"kind":"enterprise_policy_plan"}', stderr=b"")
        with mock.patch.object(WRAPPER, "load_config", return_value=self.config) as load, \
             mock.patch.object(WRAPPER, "ssh_options", return_value=["-o", "StrictHostKeyChecking=yes"]) as options, \
             mock.patch.object(WRAPPER.subprocess, "run", return_value=response) as transport:
            result = WRAPPER.execute(args)
        load.assert_called_once_with(args.config, require_target=True)
        options.assert_called_once_with(self.config)
        self.assertEqual("enterprise_policy_plan", result["kind"])
        argv = transport.call_args.args[0]
        self.assertEqual(["ssh", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10",
                          "fixture-demo-admin"], argv[:-1])
        remote = shlex.split(argv[-1])
        self.assertEqual(["sudo", "-n", "/opt/kirocrew/venv/bin/python3", "-", "--request"], remote[:-1])
        request = json.loads(base64.b64decode(remote[-1]))
        self.assertEqual(self.config["aws"], request["deployment"])
        self.assertEqual((WRAPPER.ASSETS / "manage.py").read_bytes(), transport.call_args.kwargs["input"])


if __name__ == "__main__":
    unittest.main()
