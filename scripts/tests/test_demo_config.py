"""Portable targeting tests; no AWS, login, application control or real probe runs."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from demo_config import load_config, ssh_options


def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.config = self.root / "demo.json"
        self.keys = self.root / "known_hosts"
        self.keys.write_text("test-host ssh-ed25519 TEST_PUBLIC_KEY\n")
        self.data = {"schema_version": 1, "aws": {"account_id": "123456789012", "stack_name": "other-demo"},
                     "ssh": {"known_hosts_path": "known_hosts", "host_key_alias": "test-host"}}
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def save(self):
        self.config.write_text(json.dumps(self.data))
        return self.config

    def test_defaults_never_choose_aws_account_or_stack(self):
        result = load_config()
        self.assertIsNone(result["aws"]["account_id"])
        self.assertIsNone(result["aws"]["stack_name"])
        with self.assertRaisesRegex(ValueError, "explicitly"):
            load_config(require_target=True)

    def test_paths_resolve_from_explicit_config_not_cwd(self):
        result = load_config(self.save(), require_target=True)
        self.assertEqual(result["ssh"]["known_hosts_path"], str(self.keys))
        self.assertEqual(result["_config_path"], str(self.config))

    def test_relative_app_path_derives_absolute_process_guard(self):
        self.data["client"] = {"app_path": "apps/KiroCrew.app"}
        config = load_config(self.save())
        expected = self.root / "apps/KiroCrew.app"
        self.assertEqual(config["client"]["app_path"], str(expected))
        import re
        self.assertIsNotNone(re.match(config["client"]["process_pattern"], str(expected / "Contents/MacOS/KiroCrew")))
        self.assertIsNone(re.match(config["client"]["process_pattern"], "apps/KiroCrew.app/Contents/MacOS/KiroCrew"))

    def test_environment_selector_is_explicit(self):
        with patch.dict(os.environ, {"KIRO_DEMO_CONFIG": str(self.save())}):
            self.assertEqual(load_config(require_target=True)["aws"]["stack_name"], "other-demo")

    def test_credentials_and_unknown_fields_rejected(self):
        for value in ({"aws_access_key_id": "TEST"}, {"aws": {"secret_access_key": "TEST"}}):
            with self.subTest(value=value):
                self.config.write_text(json.dumps({"schema_version": 1, **value}))
                with self.assertRaises(ValueError):
                    load_config(self.config)

    def test_duplicate_and_invalid_schema_rejected(self):
        for raw in ('{"schema_version":1,"schema_version":1}', '{"schema_version":true}', '[]'):
            self.config.write_text(raw)
            with self.assertRaises(ValueError):
                load_config(self.config)

    def test_cross_account_stack_arn_rejected(self):
        self.data["aws"]["stack_arn"] = "arn:aws:cloudformation:us-east-1:999999999999:stack/other-demo/11111111-1111-1111-1111-111111111111"
        with self.assertRaisesRegex(ValueError, "must match"):
            load_config(self.save())

    def test_ssh_option_injection_and_bad_ports_rejected(self):
        for section, key, value in (("ssh", "admin_alias", "-oProxyCommand=evil"), ("ssh", "aliases", [[], "x"]),
                                    ("ssh", "local_port", True), ("ssh", "local_port", 65536),
                                    ("probe", "remote_root", "/opt/../etc")):
            with self.subTest(key=key):
                self.config.write_text(json.dumps({"schema_version": 1, section: {key: value}}))
                with self.assertRaises(ValueError):
                    load_config(self.config)

    def test_strict_known_hosts_and_explicit_source_required(self):
        config = load_config(self.save())
        options = ssh_options(config)
        self.assertIn("StrictHostKeyChecking=yes", options)
        self.assertIn("UserKnownHostsFile=" + str(self.keys), options)
        self.keys.unlink()
        with self.assertRaises(ValueError):
            ssh_options(config)
        with self.assertRaises(ValueError):
            ssh_options(load_config())

    def test_relative_known_hosts_symlink_is_rejected(self):
        (self.root / "linked_hosts").symlink_to(self.keys)
        self.data["ssh"]["known_hosts_path"] = "linked_hosts"
        config = load_config(self.save())
        with self.assertRaisesRegex(ValueError, "regular pinned"):
            ssh_options(config)

    def test_invalid_client_process_regex_fails_cleanly(self):
        self.data["client"] = {"process_pattern": "^["}
        with self.assertRaisesRegex(ValueError, "valid anchored regex"):
            load_config(self.save())

    def test_configured_probe_target_has_fixed_command_and_receipt_directory(self):
        self.data["probe"] = {"port": 5687, "evidence_dir": "receipts", "remote_root": "/opt/other-demo",
                              "expected_allowed_sha256": "a" * 64}
        self.data["ssh"].update(admin_alias="other-admin", gateway_alias="other-client", aliases=["other-client", "other-admin"])
        config = load_config(self.save())
        presenter = module("serve-demo-probes.py", "config_probe_test")
        presenter.configure_runtime(config)
        command = presenter.COMMANDS["direct"]
        self.assertEqual(command[-2], "other-admin")
        self.assertIn("StrictHostKeyChecking=yes", command)
        remote = shlex.split(command[-1])
        self.assertEqual(remote[:4], ["sudo", "-u", "mcp-demo", "env"])
        self.assertIn("/opt/other-demo/mcp-enforcement/probe.py", remote)
        self.assertEqual(remote[-2:], ["--expected-allowed-sha256", "a" * 64])
        self.assertEqual(presenter.ORIGIN, "http://127.0.0.1:5687")
        self.assertEqual(presenter.OperatorState().evidence, self.root / "receipts")

    def test_login_protocol_gate_and_guardrails_retained(self):
        login = module("ec2-login.py", "config_login_test")
        self.assertIn("2.21.4", login.REMOTE_DRIVER)
        self.assertIn("ControlMaster=no", login.SSH_OPTIONS)
        self.assertIn("User=crew", login.SSH_OPTIONS)
        self.assertIn('"nonce"', login.REMOTE_DRIVER)


    def test_login_callback_uses_configured_alias(self):
        login = module("ec2-login.py", "callback_login_test")
        self.data["ssh"].update(gateway_alias="other-client", admin_alias="other-admin", aliases=["other-client", "other-admin"])
        config_path = self.save()
        nonce = "test-nonce"
        events = [
            {"event": "started", "directory": "/tmp/login-test", "pid": 123, "start": "1", "nonce": nonce},
            {"event": "url", "url": "https://login.test/ignored-by-validator-stub"},
            {"event": "authenticated", "method": "SocialGitHub", "existing": False},
        ]
        driver = MagicMock()
        driver.poll.return_value = 0
        tunnel = MagicMock()
        tunnel.poll.return_value = None
        tunnel.terminate.side_effect = lambda: setattr(tunnel.poll, "return_value", 0)
        selector = MagicMock()
        key = MagicMock()
        key.fileobj.fileno.return_value = 42
        selector.select.return_value = [(key, 1)]
        with patch.object(sys, "argv", ["ec2-login.py", "--config", str(config_path)]), \
             patch.object(sys.stdout, "isatty", return_value=True), \
             patch.object(login.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
             patch.object(login.secrets, "token_hex", return_value=nonce), \
             patch.object(login.selectors, "DefaultSelector", return_value=selector), \
             patch.object(login.os, "read", return_value=("\n".join(json.dumps(event) for event in events) + "\n").encode()), \
             patch.object(login, "validated_callback", return_value=4765), \
             patch.object(login, "reserve_loopback", return_value=[(MagicMock(), "127.0.0.1")]), \
             patch.object(login, "owned_listeners", return_value=True), \
             patch.object(login.subprocess, "Popen", side_effect=[driver, tunnel]) as popen, \
             patch.object(login.subprocess, "run") as cancel, \
             patch("builtins.print"):
            self.assertEqual(login.main(), 0)
        callback = popen.call_args_list[1].args[0]
        self.assertEqual(callback[-1], "other-client")
        self.assertIn("127.0.0.1:4765:127.0.0.1:4765", callback)
        self.assertIn("StrictHostKeyChecking=yes", callback)
        self.assertEqual(cancel.call_args.args[0][-2], "other-client")

    def test_shell_wrapper_keeps_selected_baseline_and_scrubs_credentials(self):
        fake = self.root / "fake-python"
        # Shell fixture substitutes only the interpreter; no KiroCrew code executes.
        fake.write_text("#!/bin/bash\nif [[ \"$*\" == *' -c '* ]]; then exit 0; fi\n"
                        "test \"${KIRO_DEMO_BASELINE:-}\" = /chosen/baseline.json || exit 41\n"
                        "test -z \"${AWS_SECRET_ACCESS_KEY:-}\" || exit 42\n"
                        "test -z \"${PYTHONPATH:-}\" || exit 43\n"
                        "printf '%s\\n' baseline-selector-preserved\n")
        fake.chmod(0o700)
        result = subprocess.run(["/bin/bash", str(SCRIPTS.parent / "demo.sh"), "--validate-baseline"],
                                capture_output=True, text=True,
                                env={"KIRO_DEMO_PYTHON": str(fake), "KIRO_DEMO_BASELINE": "/chosen/baseline.json",
                                     "AWS_SECRET_ACCESS_KEY": "TEST_SENTINEL", "PYTHONPATH": "/untrusted"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("baseline-selector-preserved", result.stdout)


if __name__ == "__main__":
    unittest.main()
