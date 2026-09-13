import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("demo_baseline", ROOT / "scripts/prepare-demo-baseline.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.package = self.root / "installed/kiro_crew"
        for file in baseline.REQUIRED:
            p = self.package / file
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# Test source, never imported\n")
        (self.package / "__init__.py").write_text('__version__ = "0.7.0-test"\nraise RuntimeError("preparation must not execute source")\n')
        self.output = self.root / ".build/demo-baselines/test"

    def tearDown(self):
        self.temp.cleanup()

    def prepared(self):
        return baseline.prepare(self.package, self.output, self.root)

    def test_exact_copy_version_scope_and_no_import(self):
        manifest_path = self.prepared()
        package, identity = baseline.validate_manifest(manifest_path, self.root)
        self.assertEqual(identity["installed_version"], "0.7.0-test")
        self.assertFalse(identity["accepted_baseline"])
        manifest = json.loads(manifest_path.read_text())
        self.assertFalse(manifest["package_imported"])
        for row in manifest["snapshot_files"]:
            self.assertEqual((package / row["path"]).read_bytes(), (self.package / row["path"]).read_bytes())

    def test_excludes_state_credentials_and_cache(self):
        for file in [".aws/credentials", ".env", "keys/private.pem", "__pycache__/hooks.pyc", "auth.json"]:
            p = self.package / file
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("must stay local")
        manifest = json.loads(self.prepared().read_text())
        self.assertEqual(len(manifest["snapshot_files"]), len(baseline.REQUIRED))
        self.assertIn(".aws/", manifest["excluded_paths"])

    def test_rejects_source_file_and_directory_links(self):
        for filename, target in [("linked.py", self.package / "hooks.py"), ("linked", self.package / "security")]:
            p = self.package / filename
            p.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "linked package"):
                self.prepared()
            p.unlink()

    def test_no_overwrite_or_output_escape_or_overlap(self):
        self.prepared()
        with self.assertRaisesRegex(ValueError, "fresh"):
            self.prepared()
        with self.assertRaisesRegex(ValueError, "ignored .build"):
            baseline.prepare(self.package, self.root / "outside", self.root)

    def test_tampered_bytes_and_extra_file_rejected(self):
        path = self.prepared()
        copied = self.output / "kiro_crew/hooks.py"
        original = copied.read_bytes()
        copied.write_text("changed")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            baseline.validate_manifest(path, self.root)
        copied.write_bytes(original)
        (self.output / "kiro_crew/injected.py").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            baseline.validate_manifest(path, self.root)

    def test_manifest_schema_paths_duplicates_and_digest(self):
        path = self.prepared()
        original = path.read_text()
        for mutate in [
            lambda d: d.update(schema=2),
            lambda d: d.update(snapshot="../kiro_crew"),
            lambda d: d["snapshot_files"][0].update(path="/etc/passwd"),
            lambda d: d["snapshot_files"].append(d["snapshot_files"][0]),
            lambda d: d.update(snapshot_digest="0" * 64),
            lambda d: d.update(version="another-build"),
        ]:
            data = json.loads(original)
            mutate(data)
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                baseline.validate_manifest(path, self.root)
        path.write_text(original)
        baseline.validate_manifest(path, self.root)

    def test_snapshot_link_rejected(self):
        path = self.prepared()
        target = self.output / "kiro_crew"
        target.rename(self.output / "saved")
        target.symlink_to(self.output / "saved", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "links"):
            baseline.validate_manifest(path, self.root)

    def test_unlisted_bytecode_cache_and_state_rejected(self):
        path = self.prepared()
        for rel in ["injected.pyc", "auth.json", "__pycache__/hooks.cpython-312.pyc"]:
            p = self.output / "kiro_crew" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"unverified bytes")
            with self.assertRaisesRegex(ValueError, "unlisted state or cache"):
                baseline.validate_manifest(path, self.root)
            p.unlink()
            if p.parent.name == "__pycache__":
                p.parent.rmdir()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "POSIX FIFO check")
    def test_fifo_fails_without_waiting_for_writer(self):
        fifo = self.package / "unexpected.fifo"
        os.mkfifo(fifo)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/prepare-demo-baseline.py"), "--package", str(self.package), "--output", str(ROOT / ".build/fifo-test-must-not-exist")], text=True, capture_output=True, timeout=3)
        self.assertEqual(result.returncode, 2)
        self.assertIn("bounded regular package file", result.stderr)

    def test_bounds_and_missing_required_files(self):
        with patch.object(baseline, "MAX_FILES", 2):
            with self.assertRaisesRegex(ValueError, "bound"):
                self.prepared()
        (self.package / "hooks.py").unlink()
        with self.assertRaisesRegex(ValueError, "installed kiro_crew"):
            self.prepared()

    def test_runner_explicit_manifest_and_environment_validate_without_import(self):
        path = self.prepared()
        env = dict(os.environ, KIRO_DEMO_BASELINE=str(path))
        for extra in [[], ["--baseline-manifest", str(path)]]:
            result = subprocess.run([sys.executable, str(ROOT / "scripts/run-live-demo.py"), "--validate-baseline", *extra], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)["controls_executed"])

    def test_runner_missing_manifest_and_conflicting_configuration_are_actionable(self):
        for extra, text in [(["--baseline-manifest", str(self.root / "missing.json")], "prepare-demo-baseline.py"),
                            (["--baseline", "pinned", "--baseline-manifest", "something.json"], "cannot be combined")]:
            result = subprocess.run([sys.executable, str(ROOT / "scripts/run-live-demo.py"), "--validate-baseline", *extra], text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn(text, result.stderr)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
