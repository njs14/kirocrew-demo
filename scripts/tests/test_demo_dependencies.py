"""Dependency plans, isolation and fresh-checkout readiness; no real installs."""
import importlib.util
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("demo_dependencies", ROOT / "scripts/demo-dependencies.py")
deps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deps)


class DependenciesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="demo checkout with spaces ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "package.json").write_text(json.dumps({"devDependencies": {"playwright": "1.63.0", "sharp": "0.35.4"}}))
        (self.root / "requirements-demo.txt").write_text("# package pins\naiohttp==3.14.3\nPyYAML==6.0.3\n")
        self.fake_python = str(self.root / "tools/python3.12")
        self.python_patch = patch.object(deps, "python_executable", return_value=self.fake_python)
        self.python_patch.start()
        self.addCleanup(self.python_patch.stop)

    def test_playback_requires_no_cloud_app_node_or_network(self):
        output = self.root / "output"
        output.mkdir()
        content = b"<html>test fixture</html>"
        (output / "deck.html").write_bytes(content)
        (output / "kirocrew-native-controls-build.json").write_text(json.dumps({"serveFiles": {"/": {
            "path": "output/deck.html", "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}}}))
        with patch.object(deps.shutil, "which", return_value=None), patch.object(deps.subprocess, "run", side_effect=AssertionError("no subprocess expected")):
            plan = deps.installation_plan("playback", self.root)
            self.assertEqual(plan["steps"], [])
            status = deps.inspect("preview", self.root)
            self.assertTrue(status["passed"])
            self.assertEqual(status["feature"], "playback")
        (output / "deck.html").write_text("changed")
        self.assertFalse(deps.inspect("playback", self.root)["passed"])

    def test_plan_includes_only_selected_dependencies_and_no_installs(self):
        with patch.object(deps.shutil, "which", side_effect=lambda command: "/usr/bin/" + command if command in {"brew", "ssh", "lsof", "screencapture"} else None), \
                patch.object(deps.subprocess, "run", side_effect=AssertionError("plan must not install")):
            plan = deps.installation_plan("all", self.root, with_browser=True)
        system = plan["steps"][0]["argv"]
        self.assertEqual(system, ["/usr/bin/brew", "install", "awscli", "ffmpeg", "node"])
        self.assertFalse(plan["network_or_install_performed"])
        self.assertEqual(plan["steps"][1]["argv"][-1], str(self.root / ".venv"))
        self.assertIn("--ignore-scripts", plan["steps"][3]["argv"])
        self.assertFalse(any("grok" in step["argv"] or "claude" in step["argv"] for step in plan["steps"]))
        self.assertEqual(plan["steps"][-1]["argv"][-2:], ["install", "chromium"])

    def test_missing_homebrew_blocks_apply_without_bootstrap(self):
        with patch.object(deps.shutil, "which", return_value=None):
            plan = deps.installation_plan("cloud", self.root)
        self.assertFalse(plan["can_apply"])
        with patch.object(deps.subprocess, "run", side_effect=AssertionError("blocked apply must not run")):
            with self.assertRaisesRegex(ValueError, "Homebrew"):
                deps.apply_plan(plan)
        self.assertFalse(any("curl" in part for step in plan["steps"] for part in step["argv"]))

    def test_native_is_mac_only_and_council_is_optional(self):
        with patch.object(deps.sys, "platform", "linux"), patch.object(deps.shutil, "which", return_value="/usr/bin/tool"):
            plan = deps.installation_plan("native", self.root)
        self.assertFalse(plan["can_apply"])
        council = deps.installation_plan("council", self.root)
        self.assertEqual(council["steps"], [])
        self.assertTrue(any("own authentication" in step for step in council["manual_steps"]))
        self.assertNotIn("council", deps.groups("all"))

    def test_external_linked_and_occupied_venvs_rejected(self):
        for venv in (self.root.parent / "external-env", self.root):
            with self.assertRaises(ValueError):
                deps.project_paths(self.root, venv)
        occupied = self.root / "important"
        occupied.mkdir()
        (occupied / "file").write_text("keep me")
        with self.assertRaisesRegex(ValueError, "non-venv"):
            deps.project_paths(self.root, occupied)
        linked = self.root / "link"
        linked.symlink_to(occupied, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "unlinked"):
            deps.project_paths(self.root, linked)
        self.assertEqual((occupied / "file").read_text(), "keep me")

    def test_apply_stops_at_failure_and_uses_argument_arrays(self):
        plan = {"blockers": [], "project_root": str(self.root), "steps": [
            {"id": "one", "argv": ["python", "argument with spaces"]},
            {"id": "two", "argv": ["npm", "ci"]},
            {"id": "three", "argv": ["never-run"]}]}
        results = [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 1)]
        with patch.object(deps.subprocess, "run", side_effect=results) as run:
            with self.assertRaisesRegex(RuntimeError, "stopped at two; earlier completed stages: one"):
                deps.apply_plan(plan)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(run.call_args_list[0].args[0], ["python", "argument with spaces"])
        self.assertNotIn("shell", run.call_args_list[0].kwargs)
        self.assertEqual(run.call_args_list[0].kwargs["cwd"], self.root)

    def test_native_reports_permission_scope_and_no_auth_claim(self):
        app = self.root / "KiroCrew Nightly.app"
        (app / "Contents").mkdir(parents=True)
        (app / "Contents/Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "com.amazon.kiro.crew", "CFBundleShortVersionString": "test"}))
        with patch.object(deps.sys, "platform", "darwin"), patch.object(deps.shutil, "which", return_value="/usr/bin/tool"), \
                patch.object(deps, "python_packages", return_value={"aiohttp": "3.14.3", "PyYAML": "6.0.3"}), \
                patch.object(deps, "permission_status", return_value={"screen_recording": False, "accessibility": True}):
            result = deps.inspect("native", self.root, app_path=app)
        self.assertFalse(result["passed"])
        checks = {row["name"]: row for row in result["checks"]}
        self.assertTrue(checks["kirocrew_app"]["passed"])
        self.assertFalse(checks["screen_recording"]["passed"])
        self.assertIn("responsible application", checks["screen_recording"]["detail"]["observed_for"])
        self.assertFalse(checks["native_acceptance"]["required"])
        self.assertFalse(checks["native_acceptance"]["passed"])

    def test_bad_receipt_escape_and_symlink_are_not_read(self):
        output = self.root / "output"
        output.mkdir()
        receipt = output / "kirocrew-native-controls-build.json"
        receipt.write_text(json.dumps({"serveFiles": {"/": {"path": "../outside.html", "bytes": 1, "sha256": "0" * 64}}}))
        self.assertFalse(deps.artifact_status(self.root)[0])
        receipt.unlink()
        receipt.symlink_to(self.root / "package.json")
        self.assertFalse(deps.artifact_status(self.root)[0])

    def test_browser_download_requires_authoring_selection(self):
        with self.assertRaisesRegex(ValueError, "authoring or all"):
            deps.installation_plan("native", self.root, with_browser=True)

    def test_existing_old_venv_and_explicit_invalid_python_do_not_get_replaced(self):
        venv = self.root / ".venv"
        venv.mkdir()
        (venv / "pyvenv.cfg").write_text("version = 3.9.0\n")
        with patch.object(deps, "venv_compatible", return_value=False):
            with self.assertRaisesRegex(ValueError, "does not replace"):
                deps.installation_plan("cloud", self.root)
        with patch.object(deps, "python_executable", return_value=None):
            with self.assertRaisesRegex(ValueError, "explicit --python"):
                deps.installation_plan("playback", self.root, python="/missing/python")

    def test_new_system_tool_prefix_applies_only_to_install_process(self):
        plan = {"blockers": [], "project_root": str(self.root), "steps": [
            {"id": "system_tools", "argv": ["/opt/homebrew/bin/brew", "install", "node"]},
            {"id": "node_packages", "argv": ["npm", "ci", "--ignore-scripts"]}]}
        with patch.object(deps.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run, \
                patch.object(deps, "run_read", return_value=(True, "/opt/homebrew")), \
                patch.object(deps.shutil, "which", return_value="/opt/homebrew/bin/npm"):
            result = deps.apply_plan(plan)
        self.assertEqual(result["completed"], ["system_tools", "node_packages"])
        self.assertEqual(run.call_args_list[1].args[0][0], "/opt/homebrew/bin/npm")
        self.assertTrue(run.call_args_list[1].kwargs["env"]["PATH"].startswith("/opt/homebrew/bin:"))


if __name__ == "__main__":
    unittest.main()
