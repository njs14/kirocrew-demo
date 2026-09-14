"""Desktop bootstrap behavior with isolated files and mocked OS commands only."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demo_config
import live_setup_desktop as desktop


class DesktopSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="desktop project with spaces ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.cfg = demo_config.defaults()
        self.cfg["_config_path"] = str(self.root / "project.json")
        self.ssh = self.root / ".ssh"
        self.ssh.mkdir(mode=0o700)
        self.cfg["ssh"].update(config_path=str(self.ssh / "config"), known_hosts_path=str(self.ssh / "pins"),
                               host_key_alias="fixed-key", gateway_alias="project-crew", admin_alias="project-admin",
                               aliases=["project-crew", "project-admin"])
        self.ssh_text = ('Host project-crew project-admin\n  HostName 10.1.2.3\n'
                         '  StrictHostKeyChecking yes\n  HostKeyAlias fixed-key\n  IdentitiesOnly yes\n'
                         f'  UserKnownHostsFile "{self.ssh / "pins"}"\n  ForwardAgent no\n'
                         'Host project-crew\n  User crew\nHost project-admin\n  User ubuntu\n')
        self.write(self.ssh / "config", self.ssh_text.encode())
        self.write(self.ssh / "pins", b"fixed-key ssh-ed25519 fixture\n")
        self.app = self.root / "KiroCrew Nightly.app"
        (self.app / "Contents").mkdir(parents=True)
        self.write(self.app / "Contents/Info.plist", plistlib.dumps({"CFBundleIdentifier": "com.amazon.kiro.crew"}))
        self.cfg["client"].update(app_path=str(self.app), process_pattern="^" + re.escape(str(self.app)) + "/Contents/MacOS/",
                                  config_path=str(self.root / "client.json"))
        self.client = Path(self.cfg["client"]["config_path"])
        self.original = {"theme": "dark", "unrelated": {"preserve": True}, "runLocalGateway": True,
                         "remoteHosts": {"6001": {"host": "other-host", "binPath": "keep"}}}
        self.write(self.client, json.dumps(self.original).encode())
        self.cfg["tunnel"]["launch_plist_path"] = str(self.root / "LaunchAgents/tunnel.plist")
        self.addCleanup(patch.stopall)
        patch.object(desktop.sys, "platform", "darwin").start()
        patch.object(desktop.Path, "home", return_value=self.root).start()
        self.run = patch.object(desktop._CLOUD, "run", side_effect=self.fake_run).start()

    def write(self, path, data):
        path.write_bytes(data)
        path.chmod(0o600)

    def fake_run(self, argv, **kwargs):
        if argv[0] == "/usr/bin/pgrep":
            return subprocess.CompletedProcess(argv, 1, "", "")
        if argv[0] == "/usr/bin/ssh-keygen":
            return subprocess.CompletedProcess(argv, 0, "pinned fixture", "")
        if argv[:2] == ["/usr/bin/ssh", "-G"]:
            user = "crew" if argv[-1] == "project-crew" else "ubuntu"
            output = (f'user {user}\nhostname 10.1.2.3\nport 22\nstricthostkeychecking true\nidentitiesonly yes\nforwardagent no\n'
                      f'hostkeyalias fixed-key\nuserknownhostsfile {self.ssh / "pins"}\npermitlocalcommand no\nremotecommand none\n')
            return subprocess.CompletedProcess(argv, 0, output, "")
        self.fail("Unexpected OS command: " + repr(argv))

    def test_definition_is_pure_and_config_bound(self):
        with patch.object(desktop, "_read_regular", side_effect=AssertionError("read")):
            self.cfg["ssh"].update(local_port=6123, remote_port=6124)
            result = desktop.desktop_definition(self.cfg)
        self.assertEqual(result["remote_port_key"], "6123")
        self.assertEqual(result["remote_entry"]["remotePort"], "6124")
        self.assertIn("127.0.0.1:6123:127.0.0.1:6124", result["tunnel_argv"])
        self.assertIn("ForwardAgent=no", result["tunnel_argv"])
        self.run.assert_not_called()

    def test_manual_apply_preserves_unrelated_settings_and_private_backup(self):
        original = self.client.read_bytes()
        result = desktop.apply_desktop(self.cfg)
        saved = json.loads(self.client.read_text())
        self.assertFalse(saved["runLocalGateway"])
        self.assertEqual(saved["unrelated"], self.original["unrelated"])
        self.assertEqual(saved["remoteHosts"]["6001"], self.original["remoteHosts"]["6001"])
        self.assertEqual(saved["remoteHosts"]["5599"]["host"], "project-admin")
        backup = Path(result["backup_path"])
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.client.stat().st_mode & 0o777, 0o600)
        self.assertFalse(result["native_connection_verified"])
        self.assertEqual(result["tunnel_state"], "manual_command_required")
        self.assertFalse(any("kirocrew-owner-token" in arg for call in self.run.call_args_list for arg in call.args[0]))

    def test_idempotence_and_host_metadata(self):
        entry = desktop.desktop_definition(self.cfg)["remote_entry"]
        value = {**self.original, "runLocalGateway": False, "remoteHosts": {"5599": {**entry, "defaultName": "Demo"}}}
        self.write(self.client, json.dumps(value).encode())
        original = self.client.read_bytes()
        result = desktop.apply_desktop(self.cfg)
        self.assertFalse(result["config_changed"])
        self.assertIsNone(result["backup_path"])
        self.assertEqual(self.client.read_bytes(), original)

    def test_mismatched_host_never_replaced(self):
        self.original["remoteHosts"]["5599"] = {"host": "other-admin", "defaultName": "Do not touch"}
        self.write(self.client, json.dumps(self.original).encode())
        original = self.client.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "another host"):
            desktop.apply_desktop(self.cfg)
        self.assertEqual(self.client.read_bytes(), original)

    def test_mismatched_remote_port_or_path_refused(self):
        for key, value in (("remotePort", "6000"), ("remotePath", "/tmp"), ("binPath", "/tmp/helper")):
            with self.subTest(key=key):
                self.original["remoteHosts"]["5599"] = {key: value}
                self.write(self.client, json.dumps(self.original).encode())
                with self.assertRaisesRegex(RuntimeError, "another host"):
                    desktop.apply_desktop(self.cfg)

    def test_running_app_refused_before_change(self):
        self.run.side_effect = lambda args, **kwargs: subprocess.CompletedProcess(args, 0, "44\n", "")
        with self.assertRaisesRegex(RuntimeError, "Quit"):
            desktop.apply_desktop(self.cfg)
        self.assertTrue(json.loads(self.client.read_text())["runLocalGateway"])

    def test_explicit_config_and_exact_process_required(self):
        self.cfg["_config_path"] = None
        with self.assertRaisesRegex(RuntimeError, "explicitly"):
            desktop.apply_desktop(self.cfg)
        self.cfg["_config_path"] = "explicit.json"
        self.cfg["client"]["process_pattern"] = "^unrelated"
        with self.assertRaisesRegex(RuntimeError, "exact anchored"):
            desktop.apply_desktop(self.cfg)

    def test_wrong_native_app_refused(self):
        self.write(self.app / "Contents/Info.plist", plistlib.dumps({"CFBundleIdentifier": "unrelated.app"}))
        with self.assertRaisesRegex(RuntimeError, "not KiroCrew"):
            desktop.apply_desktop(self.cfg)

    def test_custom_ssh_config_requires_manual_native_setup(self):
        self.cfg["ssh"]["config_path"] = str(self.root / "custom-ssh")
        with self.assertRaisesRegex(RuntimeError, "without -F"):
            desktop.apply_desktop(self.cfg)

    def test_ssh_include_refused_without_invoking_ssh(self):
        self.write(self.ssh / "config", (self.ssh_text + "Include other.conf\n").encode())
        with self.assertRaisesRegex(RuntimeError, "Include or Match"):
            desktop.apply_desktop(self.cfg)
        self.assertEqual(len(self.run.call_args_list), 1)

    def test_ssh_include_equals_is_refused_without_invoking_ssh(self):
        self.write(self.ssh / "config", (self.ssh_text + "Include=other.conf\n").encode())
        with self.assertRaisesRegex(RuntimeError, "Include or Match"):
            desktop.apply_desktop(self.cfg)
        self.assertEqual(len(self.run.call_args_list), 1)

    def test_effective_guard_drift_refused(self):
        original_run = self.fake_run
        def weak(argv, **kwargs):
            result = original_run(argv, **kwargs)
            return subprocess.CompletedProcess(argv, result.returncode, result.stdout.replace("forwardagent no", "forwardagent yes"), "")
        self.run.side_effect = weak
        with self.assertRaisesRegex(RuntimeError, "host-key guards"):
            desktop.apply_desktop(self.cfg)

    def test_symlink_duplicate_and_writable_config_refused(self):
        original = self.client.read_bytes()
        self.client.unlink()
        target = self.root / "target.json"
        self.write(target, original)
        self.client.symlink_to(target)
        with self.assertRaises(OSError):
            desktop.apply_desktop(self.cfg)
        self.client.unlink()
        self.write(self.client, b'{"remoteHosts": {}, "remoteHosts": {}}')
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            desktop.apply_desktop(self.cfg)
        self.write(self.client, original)
        self.client.chmod(0o666)
        self.client.parent.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, "regular user-owned"):
            desktop.apply_desktop(self.cfg)

    def test_private_native_store_permissions_are_tightened(self):
        self.client.chmod(0o666)
        result = desktop.apply_desktop(self.cfg)
        self.assertTrue(result["config_changed"])
        self.assertEqual(self.client.stat().st_mode & 0o777, 0o600)

    def test_permission_only_correction_with_equal_bytes(self):
        desired = {**self.original, "runLocalGateway": False,
                   "remoteHosts": {"5599": desktop.desktop_definition(self.cfg)["remote_entry"]}}
        raw = (json.dumps(desired, indent=2, ensure_ascii=False) + "\n").encode()
        self.write(self.client, raw)
        self.client.chmod(0o666)
        result = desktop.apply_desktop(self.cfg)
        self.assertTrue(result["config_changed"])
        self.assertIsNone(result["backup_path"])
        self.assertEqual(self.client.read_bytes(), raw)
        self.assertEqual(self.client.stat().st_mode & 0o777, 0o600)

    def test_default_process_pattern_with_literal_spaces(self):
        self.cfg["client"]["process_pattern"] = self.cfg["client"]["process_pattern"].replace("\\ ", " ")
        self.assertFalse(desktop._inspect_app(self.cfg, stopped=True)["running"])

    def test_exact_historical_launch_plist_is_accepted(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        desktop._create_plist(self.cfg)
        path = Path(self.cfg["tunnel"]["launch_plist_path"])
        wanted = desktop._plist_definition(self.cfg)
        logs = self.root / ".local/state/kirocrew-demo"
        logs.mkdir(parents=True)
        old = {"Label": wanted["Label"], "ProgramArguments": wanted["ProgramArguments"],
               "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 15,
               "StandardErrorPath": str(logs / "tunnel.stderr.log"),
               "StandardOutPath": str(logs / "tunnel.stdout.log")}
        self.write(path, plistlib.dumps(old))
        with patch.object(desktop._CLOUD, "managed_tunnel_job", return_value=True):
            self.assertEqual(desktop._inspect_tunnel(self.cfg)["state"], "loaded")
        (logs / "tunnel.stderr.log").symlink_to(self.client)
        with self.assertRaisesRegex(RuntimeError, "log is redirected"):
            desktop._inspect_tunnel(self.cfg)

    def test_symlink_parent_refused(self):
        link = self.root / "redirect"
        link.symlink_to(self.root, target_is_directory=True)
        self.cfg["client"]["config_path"] = str(link / "client.json")
        with self.assertRaisesRegex(RuntimeError, "redirected"):
            desktop.apply_desktop(self.cfg)

    def test_plan_reports_prerequisites_without_mutating(self):
        self.client.unlink()
        result = desktop.plan_desktop(self.cfg)
        self.assertFalse(result["ready_for_apply"])
        self.assertTrue(result["issues"])
        self.assertFalse(self.client.exists())
        self.assertFalse(Path(self.cfg["tunnel"]["launch_plist_path"]).exists())

    def test_port_80_is_not_a_supported_remote(self):
        self.cfg["ssh"]["local_port"] = 80
        with self.assertRaisesRegex(RuntimeError, "port 80"):
            desktop.apply_desktop(self.cfg)

    def test_launch_install_bootstraps_only_exact_new_job(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        with patch.object(desktop._CLOUD, "managed_tunnel_job", side_effect=[False, True]), patch.object(desktop._CLOUD, "tunnel") as load:
            result = desktop.apply_desktop(self.cfg)
        path = Path(self.cfg["tunnel"]["launch_plist_path"])
        self.assertEqual(plistlib.loads(path.read_bytes()), desktop._plist_definition(self.cfg))
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(result["tunnel_state"], "loaded")
        load.assert_called_once()
        self.assertEqual(desktop._CLOUD.tunnel_command(type("Args", (), {"config": self.cfg})()),
                         plistlib.loads(path.read_bytes())["ProgramArguments"])

    def test_matching_loaded_job_not_restarted(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        desktop._create_plist(self.cfg)
        with patch.object(desktop._CLOUD, "managed_tunnel_job", return_value=True), patch.object(desktop._CLOUD, "tunnel") as load:
            desktop.apply_desktop(self.cfg)
        load.assert_not_called()

    def test_unknown_job_and_plist_refused(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        with patch.object(desktop._CLOUD, "managed_tunnel_job", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "no matching"):
                desktop.apply_desktop(self.cfg)
        desktop._create_plist(self.cfg)
        path = Path(self.cfg["tunnel"]["launch_plist_path"])
        value = plistlib.loads(path.read_bytes())
        value["EnvironmentVariables"] = {"DYLD_INSERT_LIBRARIES": "/untrusted"}
        self.write(path, plistlib.dumps(value))
        with self.assertRaisesRegex(RuntimeError, "differs"):
            desktop.apply_desktop(self.cfg)

    def test_launch_failure_keeps_native_config_unchanged(self):
        self.cfg["tunnel"]["mode"] = "launchagent"
        original = self.client.read_bytes()
        with patch.object(desktop._CLOUD, "managed_tunnel_job", side_effect=[False, False]), patch.object(desktop._CLOUD, "tunnel"):
            with self.assertRaisesRegex(RuntimeError, "did not load"):
                desktop.apply_desktop(self.cfg)
        self.assertEqual(self.client.read_bytes(), original)

    def test_file_change_during_preparation_refused(self):
        calls = 0
        original = desktop._inspect_app
        def restart_guard(config, *, stopped):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.write(self.client, b'{"concurrent": true}')
            return original(config, stopped=stopped)
        with patch.object(desktop, "_inspect_app", side_effect=restart_guard):
            with self.assertRaisesRegex(RuntimeError, "changed while preparing"):
                desktop.apply_desktop(self.cfg)
        self.assertEqual(json.loads(self.client.read_text()), {"concurrent": True})


if __name__ == "__main__":
    unittest.main()
