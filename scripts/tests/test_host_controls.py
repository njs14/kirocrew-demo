"""Offline safety tests: no SSH, AWS, authentication, real probes or root writes."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
ASSETS = ROOT / "infrastructure/host-controls"


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


setup = module(ASSETS / "setup.py", "host_setup")
cli = module(ROOT / "scripts/configure-host-controls.py", "host_cli")


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.crew = SimpleNamespace(pw_uid=42424, pw_gid=42424, pw_dir="/home/crew")
        self.tree = setup.Tree(self.crew.pw_uid, str(self.root), root_uid=os.getuid())
        self.chown = patch.object(setup.os, "fchown")
        self.chown.start()
        self.addCleanup(self.chown.stop)
        self.request = {"mode": "preflight", "state_dir": "/var/lib/kirocrew",
                        "remote_root": "/opt/demo", "workspace": "/srv/workspace", "port": 5476,
                        "payloads": {name: (ASSETS / name).read_text() for name in setup.PAYLOAD_NAMES}}
        self.write("/var/lib/kirocrew/config.json", json.dumps({"agent": {"approval_mode": "interactive"},
                   "hooks": {"auto_approve_tools": []}, "agents": {"enforcement-demo": {}},
                   "workspaces": {"default": {"dir": "/srv/workspace"}}}))
        self.write("/home/crew/.kiro/agents/enforcement-demo.json", '{"accepted":"unchanged"}')
        self.write("/etc/machine-id", "TEST-HOST-NOT-A-CREDENTIAL\n")
        for name in setup.SOURCE_FILES:
            self.write("/opt/package/" + name, "# source fixture " + name)
        for name in ("/srv/workspace", "/opt/demo"):
            (self.root / name.lstrip("/")).mkdir(mode=0o700, parents=True, exist_ok=True)

    def write(self, name, value):
        path = self.root / name.lstrip("/")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(value)
        path.chmod(0o600)
        return path

    def call(self):
        return setup.operate(self.request, tree=self.tree, crew=self.crew, source_root="/opt/package")

    def test_preflight_only_reads_and_hashes_sources(self):
        before = sorted(str(path) for path in self.root.rglob("*"))
        result = self.call()
        self.assertFalse(result["applied"])
        self.assertEqual(self.tree.created, [])
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob("*")))
        self.assertEqual(set(result["binding"]["sources"]), set(setup.SOURCE_FILES))

    def test_apply_is_additive_and_preserves_existing_mcp_agent_and_config(self):
        result = self.call()
        original_agent = (self.root / "home/crew/.kiro/agents/enforcement-demo.json").read_bytes()
        original_config = (self.root / "var/lib/kirocrew/config.json").read_bytes()
        self.request.update(mode="apply", expected=result["binding"])
        result = self.call()
        self.assertTrue(result["applied"])
        agent = json.loads((self.root / "home/crew/.kiro/agents/host-controls-demo.json").read_text())
        self.assertEqual(agent["tools"], ["fs_read", "fs_write", "execute_bash"])
        self.assertEqual(agent["allowedTools"], [])
        self.assertEqual(agent["mcpServers"], {})
        self.assertFalse(agent["includeMcpJson"])
        self.assertEqual((self.root / "home/crew/.kiro/agents/enforcement-demo.json").read_bytes(), original_agent)
        self.assertEqual((self.root / "var/lib/kirocrew/config.json").read_bytes(), original_config)
        self.assertEqual((self.root / "home/crew/.aws/kirocrew-demo-control-canary.txt").read_bytes(), setup.CANARY)
        self.assertIn("EXPECTED_CREW_UID = 42424", (self.root / "opt/demo/host-controls/imds-tcp.py").read_text())
        self.assertFalse((self.root / "home/crew/.kiro/agents/.demo-host-controls/write-probe.txt").exists())
        with self.assertRaisesRegex(ValueError, "destination_already_exists"):
            self.call()

    def test_apply_rejects_source_drift_before_creating_anything(self):
        result = self.call()
        self.request.update(mode="apply", expected=result["binding"])
        self.write("/opt/package/hooks.py", "# changed source")
        with self.assertRaisesRegex(ValueError, "preflight_binding_changed"):
            self.call()
        self.assertEqual(self.tree.created, [])

    def test_existing_sensitive_canary_is_never_overwritten(self):
        path = self.write("/home/crew/.aws/kirocrew-demo-control-canary.txt", "existing")
        with self.assertRaisesRegex(ValueError, "destination_already_exists"):
            self.call()
        self.assertEqual(path.read_text(), "existing")

    def test_symlink_ancestor_and_leaf_refused(self):
        (self.root / "home/crew/.aws").symlink_to(self.root / "srv/workspace", target_is_directory=True)
        with self.assertRaises(OSError):
            self.call()
        (self.root / "home/crew/.aws").unlink()
        (self.root / "home/crew/.kiro/agents/host-controls-demo.json").symlink_to("/nonexistent")
        with self.assertRaisesRegex(ValueError, "destination_already_exists"):
            self.call()

    def test_hardlinked_source_and_writable_parent_refused(self):
        source = self.root / "opt/package/hooks.py"
        os.link(source, self.root / "duplicate")
        with self.assertRaisesRegex(ValueError, "non_regular_or_linked_file"):
            self.call()
        (self.root / "duplicate").unlink()
        (self.root / "opt/package").chmod(0o777)
        with self.assertRaisesRegex(ValueError, "writable_directory_ancestor"):
            self.call()

    def test_partial_failure_reports_exact_created_paths_without_deleting(self):
        before = self.call()
        self.request.update(mode="apply", expected=before["binding"])
        with patch.object(self.tree, "write", side_effect=OSError("simulated")):
            result = self.call()
        self.assertFalse(result["applied"])
        self.assertEqual(result["error"], "setup_incomplete_review_created_paths")
        self.assertTrue(result["created"])
        self.assertTrue((self.root / "home/crew/.kiro/agents/.demo-host-controls").is_dir())

    def test_demo_command_readback_emits_only_safe_matching_rule_fields(self):
        self.write("/var/lib/kirocrew/denied_commands.json", json.dumps({"user_added": [
            {"id": "user-demo", "pattern": "KIROCREW_DEMO_COMMAND_CONTROL_20260913", "enabled": True,
             "note": "unrelated prose must not be copied"},
            {"id": "user-other", "pattern": "private operator rule", "enabled": True}]}))
        rows = self.call()["binding"]["demo_command_rules"]
        self.assertEqual(rows, [{"id": "user-demo", "pattern": "KIROCREW_DEMO_COMMAND_CONTROL_20260913", "enabled": True}])

    def test_interactive_mode_and_exact_workspace_required(self):
        self.request["workspace"] = "/srv/other"
        with self.assertRaisesRegex(ValueError, "workspace_configuration_mismatch"):
            self.call()
        self.request["workspace"] = "/srv/workspace"
        path = self.root / "var/lib/kirocrew/config.json"
        data = json.loads(path.read_text())
        data["agent"]["approval_mode"] = "yolo"
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "interactive_approval_required"):
            self.call()


class ProbeTests(unittest.TestCase):
    def probe(self, name):
        scope = {"__name__": "test_probe"}
        text = (ASSETS / name).read_text().replace("__EXPECTED_CREW_UID__", "42424").replace("__GATEWAY_PORT__", "5476")
        exec(compile(text, name, "exec"), scope)
        return scope

    def test_anonymous_http_discards_body_and_sends_no_auth(self):
        probe = self.probe("anonymous-http.py")
        connection = MagicMock()
        connection.getresponse.return_value.status = 403
        with patch("http.client.HTTPConnection", return_value=connection) as factory, patch("os.getuid", return_value=42424), \
                patch("os.geteuid", return_value=42424), patch.object(sys, "argv", ["probe"]), patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(probe["main"](), 0)
        factory.assert_called_once_with("127.0.0.1", 5476, timeout=3)
        connection.request.assert_called_once_with("GET", "/api/security/posture", headers={"Accept": "application/json", "Connection": "close"})
        connection.getresponse.return_value.read.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["http_status"], 403)

    def test_metadata_probe_is_exact_ipv4_connect_without_application_bytes(self):
        probe = self.probe("imds-tcp.py")
        connection = MagicMock()
        connection.connect_ex.return_value = 113
        context = MagicMock()
        context.__enter__.return_value = connection
        with patch("socket.socket", return_value=context) as factory, patch("os.getuid", return_value=42424), \
                patch("os.geteuid", return_value=42424), patch.object(sys, "argv", ["probe"]), patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(probe["main"](), 0)
        factory.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect_ex.assert_called_once_with(("169.254.169.254", 80))
        connection.send.assert_not_called()
        connection.sendall.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["application_bytes_sent"], 0)

    def test_helpers_refuse_arguments_and_wrong_uid_before_network(self):
        for name in setup.PAYLOAD_NAMES:
            probe = self.probe(name)
            for argv, uid, euid in ((["probe", "unexpected"], 42424, 42424),
                                    (["probe"], 0, 0), (["probe"], 42424, 0)):
                with patch("socket.socket") as connection, patch("http.client.HTTPConnection") as http, \
                        patch.object(sys, "argv", argv), patch("os.getuid", return_value=uid), \
                        patch("os.geteuid", return_value=euid), patch("sys.stdout", new_callable=io.StringIO):
                    self.assertEqual(probe["main"](), 2)
                    connection.assert_not_called()
                    http.assert_not_called()


class CliTests(unittest.TestCase):
    def test_apply_requires_both_flags_before_any_ssh(self):
        args = cli.parser().parse_args(["apply"])
        with patch.object(cli.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "apply_requires_explicit_flag"):
                cli.request_for(args, {"probe": {"remote_root": "/opt/demo"}, "ssh": {"remote_port": 5476}})
            run.assert_not_called()

    def test_paths_reject_traversal_shell_and_relative_values(self):
        for value in ("relative", "/tmp/../etc", "/tmp/$HOME", "/tmp/a;id", "/tmp/a\nb"):
            with self.assertRaises(argparse.ArgumentTypeError):
                cli.absolute(value)

    def test_apply_rejects_changed_local_setup_before_ssh(self):
        with tempfile.TemporaryDirectory() as folder:
            receipt = Path(folder) / "receipt.json"
            receipt.write_text(json.dumps({"kind": "host_controls_setup", "schema_version": 1,
                                          "applied": False, "binding": {}, "local_setup_sha256": "0" * 64}))
            args = cli.parser().parse_args(["apply", "--apply", "--preflight-receipt", str(receipt)])
            with patch.object(cli.subprocess, "run") as run:
                with self.assertRaisesRegex(ValueError, "setup_source_changed_since_preflight"):
                    cli.request_for(args, {"probe": {"remote_root": "/opt/demo"}, "ssh": {"remote_port": 5476}})
                run.assert_not_called()

    def test_wrong_receipt_kind_cannot_authorize_setup(self):
        with tempfile.TemporaryDirectory() as folder:
            receipt = Path(folder) / "receipt.json"
            receipt.write_text('{"kind":"other_tool", "applied": false}')
            args = cli.parser().parse_args(["apply", "--apply", "--preflight-receipt", str(receipt)])
            with self.assertRaisesRegex(ValueError, "invalid_preflight_receipt"):
                cli.request_for(args, {"probe": {"remote_root": "/opt/demo"}, "ssh": {"remote_port": 5476}})


if __name__ == "__main__":
    unittest.main()
