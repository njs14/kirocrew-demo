"""Offline tests for privacy boundaries, unknowns, bounded storage and transfer."""
import copy
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("collector", HERE / "collector.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
spec2 = importlib.util.spec_from_file_location("client_cli", HERE.parents[1] / "scripts/demo-telemetry.py")
cli = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(cli)


def good_sample():
    sample = c.envelope("client")
    sample["metrics"] = {"process_count": 5, "cpu_percent": 1.2, "rss_mib": 234.5}
    sample["checks"] = {"client_running": True, "remote_gateway_reachable": True, "local_gateway_off": True}
    return c.finish(sample)


class CollectorTests(unittest.TestCase):
    @staticmethod
    def launch_present(arguments=None):
        arguments = arguments or cli.launch_definition()["ProgramArguments"]
        target = "gui/" + str(os.getuid()) + "/" + cli.LABEL
        output = target + " = {\n\tprogram = " + arguments[0] + "\n\targuments = {\n"
        output += "".join("\t\t" + value + "\n" for value in arguments) + "\t}\n}\n"
        return subprocess.CompletedProcess([], 0, output, "")

    @staticmethod
    def launch_absent():
        return subprocess.CompletedProcess([], 113, "", 'Bad request.\nCould not find service "' + cli.LABEL + '" in domain for user gui: ' + str(os.getuid()) + '\n')

    def test_stop_missing_plist_unloads_verified_live_job(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", Path(temporary) / "missing.plist"), patch.object(cli, "run", side_effect=[self.launch_present(), subprocess.CompletedProcess([], 0, "", ""), self.launch_absent()]) as run, patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(cli.stop(True), 0)
            self.assertEqual(run.call_args_list[1].args[0], ["/bin/launchctl", "bootout", "gui/" + str(os.getuid()) + "/" + cli.LABEL])
            self.assertTrue(json.loads(output.getvalue())["client_timer_stopped"])

    def test_stop_missing_plist_confirms_already_absent(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", Path(temporary) / "missing.plist"), patch.object(cli, "run", side_effect=[self.launch_absent(), self.launch_absent()]) as run, patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.stop(True), 0)
            self.assertTrue(all(call.args[0][1] == "print" for call in run.call_args_list))

    def test_stop_unknown_state_cannot_claim_success(self):
        failure = subprocess.CompletedProcess([], 1, "", "permission denied")
        with tempfile.TemporaryDirectory() as temporary, patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", Path(temporary) / "missing.plist"), patch.object(cli, "run", return_value=failure) as run, patch("sys.stdout", new_callable=io.StringIO) as output:
            with self.assertRaisesRegex(RuntimeError, "state_unknown"):
                cli.stop(True)
            self.assertEqual(run.call_count, 1)
            self.assertEqual(output.getvalue(), "")

    def test_stop_refuses_other_live_job_with_same_label(self):
        arguments = cli.launch_definition()["ProgramArguments"]
        arguments[1] = "/tmp/unrelated.py"
        with tempfile.TemporaryDirectory() as temporary, patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", Path(temporary) / "missing.plist"), patch.object(cli, "run", return_value=self.launch_present(arguments)) as run:
            with self.assertRaisesRegex(RuntimeError, "unrecognized_live"):
                cli.stop(True)
            self.assertEqual(run.call_count, 1)

    def test_stop_live_job_remaining_is_failure(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", Path(temporary) / "missing.plist"), patch.object(cli, "run", side_effect=[self.launch_present(), subprocess.CompletedProcess([], 1, "", "denied"), self.launch_present()]), patch("sys.stdout", new_callable=io.StringIO) as output:
            with self.assertRaisesRegex(RuntimeError, "stop_failed"):
                cli.stop(True)
            self.assertEqual(output.getvalue(), "")

    def test_stop_removes_only_recognized_plist_after_absence(self):
        with tempfile.TemporaryDirectory() as temporary:
            plist = Path(temporary) / "ours.plist"
            plist.write_bytes(plistlib.dumps(cli.launch_definition()))
            plist.chmod(0o600)
            with patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", plist), patch.object(cli, "run", side_effect=[self.launch_absent(), self.launch_absent()]), patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(cli.stop(True), 0)
            self.assertFalse(plist.exists())

    def test_stop_rejects_same_label_wrong_plist_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            plist = Path(temporary) / "other.plist"
            definition = cli.launch_definition()
            definition["ProgramArguments"][1] = "/tmp/unrelated.py"
            plist.write_bytes(plistlib.dumps(definition))
            plist.chmod(0o600)
            with patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", plist), patch.object(cli, "run", side_effect=AssertionError("must not mutate job")):
                with self.assertRaisesRegex(RuntimeError, "unrecognized_launch_agent"):
                    cli.stop(True)
            self.assertTrue(plist.exists())

    def test_exact_process_scope_and_no_identity_output(self):
        result = c.parse_mac_processes("1 0 0.0 2048 /bin/other\n2 1 2.4 1024 " + c.MAC_MAIN + "\n3 2 1.0 2048 " + c.MAC_APP_ROOT + "Frameworks/KiroCrew Nightly Helper.app/Contents/MacOS/KiroCrew Nightly Helper\n4 1 9.0 4000 /tmp/KiroCrew Nightly\n")
        self.assertEqual(result, {"process_count": 2, "cpu_percent": 3.4, "rss_mib": 3.0})
        self.assertNotIn("KiroCrew", json.dumps(result))

    def test_no_processes_is_known_zero(self):
        self.assertEqual(c.parse_mac_processes("1 0 0 10 /bin/other")["process_count"], 0)

    def test_failed_process_probe_is_unknown(self):
        with patch.object(c.platform, "system", return_value="Darwin"), patch.object(c, "command", side_effect=RuntimeError()), patch.object(c, "probe_port", return_value=True):
            sample = c.collect_client()
        self.assertIsNone(sample["metrics"]["process_count"])
        self.assertIsNone(sample["checks"]["client_running"])
        self.assertEqual(sample["status"], "partial")
        self.assertEqual(sample["errors"], ["process_probe_failed"])

    def test_unknown_port_is_not_reported_off(self):
        with patch.object(c.platform, "system", return_value="Darwin"), patch.object(c, "command", return_value=""), patch.object(c, "probe_port", return_value=None):
            sample = c.collect_client()
        self.assertIsNone(sample["checks"]["local_gateway_off"])
        self.assertIn("port_probe_failed", sample["errors"])

    def test_custom_mac_bundle_scope(self):
        root = "/Applications/KiroCrew Stable.app/Contents/"
        output = ("10 1 2.0 1024 " + root + "MacOS/KiroCrew Stable\n"
                  "11 10 3.0 2048 " + root + "Frameworks/Helper\n"
                  "12 1 8.0 9000 " + c.MAC_MAIN + "\n")
        self.assertEqual(c.parse_mac_processes(output, root),
                         {"process_count": 2, "cpu_percent": 5.0, "rss_mib": 3.0})

    def test_linux_process_metrics_include_only_exact_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            proc = Path(temporary)
            for pid, target in ((101, "/opt/demo/crew"), (102, "/opt/other/crew")):
                (proc / str(pid)).mkdir()
                (proc / str(pid) / "exe").symlink_to(target)
            with patch.object(c, "Path", side_effect=lambda value: proc if value == "/proc" else Path(value)), patch.object(c, "process_ticks", side_effect=[(100, 12, 500), (105, 20, 500)]) as ticks, patch.object(c.os, "sysconf", return_value=100), patch.object(c.time, "monotonic", side_effect=[10, 10.2]), patch.object(c.time, "sleep"):
                metrics = c.collect_linux_processes("/opt/demo/crew")
        self.assertEqual([call.args[0] for call in ticks.call_args_list], [101, 101])
        self.assertEqual(metrics, {"process_count": 1, "cpu_percent": 25.0, "rss_mib": 20.0})
        self.assertNotIn("/opt", json.dumps(metrics))

    def test_linux_metrics_do_not_claim_mac_gateway_state(self):
        metrics = {"process_count": 2, "cpu_percent": 3.0, "rss_mib": 40.0}
        with patch.object(c.platform, "system", return_value="Linux"), patch.object(c, "collect_linux_processes", return_value=metrics) as processes, patch.object(c, "probe_port", return_value=True) as port:
            sample = c.collect_client(app_root=None, executable="/opt/demo/crew", remote_gateway_port=6500)
        processes.assert_called_once_with("/opt/demo/crew")
        port.assert_called_once_with(6500)
        self.assertEqual(sample["metrics"], metrics)
        self.assertTrue(sample["checks"]["client_running"])
        self.assertIsNone(sample["checks"]["local_gateway_off"])
        self.assertEqual(sample["status"], "partial")
        self.assertEqual(sample["errors"], [])

    def test_linux_without_executable_retains_tunnel_check(self):
        with patch.object(c.platform, "system", return_value="Linux"), patch.object(c, "probe_port", return_value=True):
            sample = c.collect_client(app_root=None)
        self.assertIsNone(sample["metrics"]["process_count"])
        self.assertIsNone(sample["checks"]["local_gateway_off"])
        self.assertTrue(sample["checks"]["remote_gateway_reachable"])
        self.assertEqual(sample["errors"], ["process_probe_failed"])

    def test_explicit_linux_port_check_uses_chosen_ports(self):
        metrics = {"process_count": 0, "cpu_percent": 0.0, "rss_mib": 0.0}
        with patch.object(c.platform, "system", return_value="Linux"), patch.object(c, "collect_linux_processes", return_value=metrics), patch.object(c, "probe_port", side_effect=[True, False]) as port:
            sample = c.collect_client(executable="/opt/demo/crew", remote_gateway_port=6500,
                                      local_gateway_port=6501, check_local_gateway=True)
        self.assertEqual([call.args[0] for call in port.call_args_list], [6500, 6501])
        self.assertTrue(sample["checks"]["local_gateway_off"])

    def test_client_options_reject_invalid_ports_and_flags(self):
        for options in ({"remote_gateway_port": 0}, {"local_gateway_port": True}, {"check_local_gateway": "yes"}):
            with self.assertRaises(ValueError), patch.object(c, "command", side_effect=AssertionError("must not probe")):
                c.collect_client(**options)

    def test_timer_commands_fail_clearly_on_linux_even_for_plan(self):
        with patch.object(cli.sys, "platform", "linux"), patch.object(cli, "run", side_effect=AssertionError("must not run launchctl")):
            for operation in (cli.setup, cli.stop):
                for apply in (False, True):
                    with self.assertRaisesRegex(RuntimeError, "macos_timer_only_use_collect_once"):
                        operation(apply)

    def test_configured_launchagent_carries_config_path_and_interval(self):
        with patch.object(cli, "CONFIG_PATH", "/tmp/other machine/demo.json"), patch.object(cli, "INTERVAL_SECONDS", 120):
            definition = cli.launch_definition()
        self.assertEqual(definition["ProgramArguments"][-2:], ["--config", "/tmp/other machine/demo.json"])
        self.assertEqual(definition["StartInterval"], 120)

    def test_setup_refuses_unrecognized_agent_before_any_upload(self):
        with tempfile.TemporaryDirectory() as temporary:
            plist = Path(temporary) / "other.plist"
            definition = cli.launch_definition()
            definition["ProgramArguments"][1] = "/tmp/something-else.py"
            plist.write_bytes(plistlib.dumps(definition))
            plist.chmod(0o600)
            with patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", plist), patch.object(cli, "collect_once", side_effect=AssertionError("no upload")), patch.object(cli, "run", side_effect=AssertionError("no mutation")):
                with self.assertRaisesRegex(RuntimeError, "unrecognized_launch_agent"):
                    cli.setup(True)

    def test_setup_migrates_only_exact_legacy_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            plist = Path(temporary) / "ours.plist"
            legacy = cli.launch_definition()
            legacy["ProgramArguments"] = legacy["ProgramArguments"][:4]
            plist.write_bytes(plistlib.dumps(legacy))
            plist.chmod(0o600)
            with patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", plist), patch.object(cli, "CONFIG_PATH", "/tmp/demo.local.json"), patch.object(cli, "collect_once", return_value=0) as upload, patch.object(cli.time, "sleep"), patch.object(cli, "run", side_effect=[self.launch_present(legacy["ProgramArguments"]), subprocess.CompletedProcess([], 0, "", ""), self.launch_absent(), subprocess.CompletedProcess([], 0, "", "")]) as run, patch("sys.stdout", new_callable=io.StringIO):
                self.assertEqual(cli.setup(True), 0)
                self.assertIsNotNone(cli.recognized_plist())
            upload.assert_called_once_with(True)
            self.assertEqual([call.args[0][1] for call in run.call_args_list], ["print", "bootout", "print", "bootstrap"])
            migrated = plistlib.loads(plist.read_bytes())
            self.assertEqual(migrated["ProgramArguments"][-2:], ["--config", "/tmp/demo.local.json"])

    def test_setup_will_not_adopt_another_config_bound_job(self):
        with tempfile.TemporaryDirectory() as temporary:
            plist = Path(temporary) / "other.plist"
            definition = cli.launch_definition()
            definition["ProgramArguments"] = definition["ProgramArguments"][:4] + ["--config", "/tmp/another.json"]
            plist.write_bytes(plistlib.dumps(definition))
            plist.chmod(0o600)
            with patch.object(cli.sys, "platform", "darwin"), patch.object(cli, "PLIST", plist), patch.object(cli, "CONFIG_PATH", "/tmp/demo.local.json"), patch.object(cli, "collect_once", side_effect=AssertionError("no upload")), patch.object(cli, "run", side_effect=AssertionError("no mutation")):
                with self.assertRaisesRegex(RuntimeError, "unrecognized_launch_agent"):
                    cli.setup(True)

    def test_server_custom_service_port_and_disk_probes(self):
        with patch.object(c.platform, "system", return_value="Linux"), patch.object(c, "cpu_ticks", side_effect=OSError()), patch.object(c, "service_state", return_value=(False, 0)) as services, patch.object(c, "probe_port", return_value=True) as ports, patch.object(c.time, "sleep"):
            sample = c.collect_server(gateway_service="crew-other.service", mcp_service="mcp-other.service", gateway_port=6502, mcp_port=6503, disk_path="/var")
        self.assertEqual([call.args[0] for call in services.call_args_list], ["crew-other.service", "mcp-other.service"])
        self.assertEqual([call.args[0] for call in ports.call_args_list], [6502, 6503])
        self.assertFalse(sample["checks"]["gateway_service_active"])

    def test_server_rejects_options_before_probing(self):
        for options in ({"gateway_service": "--help"}, {"mcp_port": -1}, {"disk_path": "relative"}):
            with self.assertRaises(ValueError), patch.object(c, "service_state", side_effect=AssertionError("must not probe")):
                c.collect_server(**options)

    def test_private_or_extra_fields_rejected(self):
        for target, key in (("root", "token"), ("metrics", "pid"), ("checks", "session")):
            sample = good_sample()
            (sample if target == "root" else sample[target])[key] = "secret"
            with self.assertRaises(ValueError):
                c.validate_sample(sample, "client")

    def test_nonfinite_bool_negative_metric_rejected(self):
        for value in (float("nan"), float("inf"), True, -1, "secret"):
            sample = good_sample()
            sample["metrics"]["cpu_percent"] = value
            with self.assertRaises(ValueError):
                c.validate_sample(sample, "client")

    def test_arbitrary_errors_rejected(self):
        sample = good_sample()
        sample["errors"] = ["Bearer raw-secret"]
        with self.assertRaises(ValueError):
            c.validate_sample(sample, "client")

    def test_source_swap_rejected(self):
        with self.assertRaises(ValueError):
            c.validate_sample(good_sample(), "server")

    def test_clock_skew_and_status_lie_rejected(self):
        sample = good_sample()
        sample["collected_at"] = "2000-01-01T00:00:00Z"
        with self.assertRaises(ValueError):
            c.validate_sample(sample, "client")
        sample = good_sample()
        sample["status"] = "unknown"
        with self.assertRaises(ValueError):
            c.validate_sample(sample, "client")

    def test_oversized_input_rejected(self):
        with self.assertRaises(ValueError):
            c.read_client_input(io.BytesIO(b"x" * (c.MAX_PAYLOAD + 1)))

    def test_noisy_events_are_suppressed(self):
        sample = good_sample()
        self.assertEqual(c.transition_events(sample, sample), [])
        changed = copy.deepcopy(sample)
        changed["checks"]["client_running"] = False
        self.assertEqual(c.transition_events(sample, changed)[0]["code"], "checks_changed")

    def test_failed_metric_recovers(self):
        previous = good_sample()
        previous["errors"] = ["process_probe_failed"]
        self.assertEqual(c.transition_events(previous, good_sample())[0]["code"], "sample_recovered")

    def test_bounded_store_atomic_modes_and_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "data"
            sample = good_sample()
            now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
            for index in range(245):
                sample["collected_at"] = (now - dt.timedelta(seconds=245 - index)).strftime("%Y-%m-%dT%H:%M:%SZ")
                sample["checks"]["client_running"] = bool(index % 2)
                c.store_sample(sample, directory, os.getuid(), os.getgid())
            self.assertEqual(len((directory / "client-history.jsonl").read_text().splitlines()), 240)
            self.assertEqual(len((directory / "events.jsonl").read_text().splitlines()), 200)
            self.assertEqual((directory / "client.json").stat().st_mode & 0o777, 0o640)
            self.assertEqual(directory.stat().st_mode & 0o777, 0o750)
            with self.assertRaises(ValueError):
                c.store_sample(sample, directory, os.getuid(), os.getgid())

    def test_symlink_and_writable_directory_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            actual = base / "actual"
            actual.mkdir()
            (base / "link").symlink_to(actual)
            with self.assertRaises(RuntimeError):
                c.store_sample(good_sample(), base / "link", os.getuid(), os.getgid())
            actual.chmod(0o777)
            with self.assertRaises(RuntimeError):
                c.store_sample(good_sample(), actual, os.getuid(), os.getgid())

    def test_fixed_receiver_pinned_transport(self):
        with tempfile.TemporaryDirectory() as temporary:
            known = Path(temporary) / "known"
            known.touch()
            with patch.object(cli, "KNOWN_HOSTS", known), patch.object(cli, "HOST_KEY_ALIAS", "demo-test-pinned"):
                command = cli.ssh_command()
            self.assertIn("StrictHostKeyChecking=yes", command)
            self.assertIn("BatchMode=yes", command)
            self.assertIn("ClearAllForwardings=yes", command)
            self.assertEqual(command[-2], "kirocrew-demo-admin")
            self.assertEqual(command[-1], cli.REMOTE_RECEIVER)

    def test_dry_run_has_no_write_or_network(self):
        fake = type("Probe", (), {"collect_client": staticmethod(good_sample)})
        with patch.object(cli, "collector", return_value=fake), patch.object(cli, "atomic_local", side_effect=AssertionError("write")), patch.object(cli, "run", side_effect=AssertionError("network")), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.collect_once(False), 0)
            self.assertEqual(cli.setup(False), 0)
            self.assertEqual(cli.stop(False), 0)

    def test_ssh_failure_receipt_has_no_raw_error(self):
        fake = type("Probe", (), {"collect_client": staticmethod(good_sample)})
        writes = {}
        with patch.object(cli, "collector", return_value=fake), patch.object(cli, "atomic_local", side_effect=lambda path, data: writes.update({path.name: data})), patch.object(cli, "ssh_command", return_value=["ssh"]), patch.object(cli, "run", side_effect=RuntimeError("private host secret")), patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.collect_once(True), 1)
        self.assertNotIn("private", writes["upload-status.json"].decode())
        self.assertFalse(json.loads(writes["upload-status.json"])["uploaded"])


if __name__ == "__main__":
    unittest.main()
