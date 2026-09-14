"""Adversarial package/archive validation without installing or importing Crew."""
import importlib.util
import io
import json
from pathlib import Path
import struct
from contextlib import redirect_stdout
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("arm_bundle", ROOT / "infrastructure/install-runtime-bundle.py")
arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arm)
prep_spec = importlib.util.spec_from_file_location("prepare_arm", ROOT / "scripts/prepare-arm-runtime.py")
prep = importlib.util.module_from_spec(prep_spec)
prep_spec.loader.exec_module(prep)


def elf(machine=183):
    data = bytearray(24)
    data[:6] = b"\x7fELF\x02\x01"
    struct.pack_into("<H", data, 18, machine)
    return bytes(data)


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def archive(self, members):
        path = self.root / "runtime.tar.gz"
        with tarfile.open(path, "w:gz") as tar:
            for name, data, kind in members:
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.type = kind
                if kind == tarfile.SYMTYPE:
                    info.linkname = "/etc/passwd"
                tar.addfile(info, io.BytesIO(data))
        return path

    def test_rejects_escape_and_ambiguous_paths(self):
        for value in ("../x", "/etc/passwd", "x/../y", "x//y", "./x", "x\\y", ".", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                arm.relpath(value)

    def test_reads_neither_symlink_nor_fifo(self):
        import os
        (self.root / "real").write_text("fixture")
        (self.root / "linked").symlink_to(self.root / "real")
        os.mkfifo(self.root / "pipe")
        for name in ("linked", "pipe"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                arm.read_regular(self.root / name)

    def test_rejects_archive_links_traversal_duplicates_foreign_binaries(self):
        cases = [
            [("kiro_crew/link", b"", tarfile.SYMTYPE)],
            [("kiro_crew/../../escape", b"x", tarfile.REGTYPE)],
            [("kiro_crew/x", b"x", tarfile.REGTYPE)] * 2,
            [("kiro_crew/x.so", elf(62), tarfile.REGTYPE)],
            [("kiro_crew/x.dylib", b"\xcf\xfa\xed\xfe", tarfile.REGTYPE)],
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                arm.archive_inventory(self.archive(case))

    def test_supported_version_is_parsed_without_executing_source(self):
        source = b'__version__ = "0.7.0-nightly.20260913t061222"\nraise RuntimeError("must not execute")\n'
        self.assertEqual(arm.version(source), "0.7.0-nightly.20260913t061222")
        with self.assertRaisesRegex(ValueError, "unsupported"):
            arm.version(b'__version__ = "99.0.0"')

    def test_lock_parser_refuses_extra_indexes_or_unhashed_packages(self):
        for data in (b"thing==1\n", b"--extra-index-url https://example.invalid\n", b"-e .\n"):
            with self.assertRaises(ValueError):
                arm.lock_entries(data)
        self.assertEqual(len(arm.lock_entries((ROOT / "infrastructure/crew-requirements-linux-arm64.lock").read_bytes())), 48)

    def test_wheel_hash_and_inner_architecture_both_enforced(self):
        wheels = self.root / "wheels"
        wheels.mkdir()
        path = wheels / "fixture-1-py3-none-manylinux2014_aarch64.whl"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("fixture/native.so", elf(62))
        data = path.read_bytes()
        lock = f"fixture==1 \\\n    --hash=sha256:{arm.sha(data)}\n".encode()
        with self.assertRaisesRegex(ValueError, "non-AArch64"):
            arm.check_wheels(wheels, lock)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("fixture/native.so", elf())
        with self.assertRaisesRegex(ValueError, "pinned dependency"):
            arm.check_wheels(wheels, lock)
        lock = f"fixture==1 \\\n    --hash=sha256:{arm.sha(path.read_bytes())}\n".encode()
        self.assertEqual(arm.check_wheels(wheels, lock)[0]["aarch64_binaries"], ["fixture/native.so"])

    def test_runtime_archive_is_deterministic_for_same_source(self):
        source = self.root / "source.py"
        source.write_text("# harmless source fixture\n")
        first, second = self.root / "first.tar.gz", self.root / "second.tar.gz"
        prep.runtime_archive([("kiro_crew/source.py", source)], first)
        prep.runtime_archive([("kiro_crew/source.py", source)], second)
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_prepare_rejects_lexically_contained_parent_traversal(self):
        with self.assertRaisesRegex(ValueError, "parent traversal"):
            prep.prepare(self.root / "kiro_crew", self.root / arm.DIST,
                         ROOT / ".build/../escape-proof", None, None, plan=True)

    def test_manifest_hash_is_checked_before_parsing_or_execution(self):
        (self.root / "manifest.json").write_text("not JSON")
        with self.assertRaisesRegex(ValueError, "expected SHA-256"):
            arm.verify(self.root, "0" * 64)

    def test_wrong_host_fails_before_runtime_creation(self):
        with patch.object(arm.platform, "machine", return_value="x86_64"), self.assertRaisesRegex(ValueError, "Linux aarch64"):
            arm.host_check(self.root / "must-not-be-created")
        self.assertFalse((self.root / "must-not-be-created").exists())

    def test_install_keeps_callers_digest_when_manifest_changes(self):
        reviewed = "1" * 64
        replacement = b'{"other": "valid bundle"}'
        with patch.object(arm, "verify", return_value={}), patch.object(arm, "read_regular", return_value=replacement), patch.object(arm, "install", return_value={}) as install, patch("sys.argv", ["install-runtime-bundle.py", "install", "--bundle", str(self.root), "--manifest-sha256", reviewed]):
            with redirect_stdout(io.StringIO()):
                arm.main()
        self.assertEqual(install.call_args.args[1], reviewed)

    def test_verify_reports_the_digest_bound_before_validation(self):
        original = b'{"original": "bundle"}'
        payload = {"runtime_version": "0.7.0-nightly.20260913t061222", "runtime_files": [], "wheels": []}
        output = io.StringIO()
        with patch.object(arm, "read_regular", side_effect=[original, b"changed"]), patch.object(arm, "verify", return_value=payload) as verify, patch("sys.argv", ["installer", "verify", "--bundle", str(self.root)]), redirect_stdout(output):
            arm.main()
        self.assertEqual(verify.call_args.args[1], arm.sha(original))
        self.assertEqual(json.loads(output.getvalue())["manifest_sha256"], arm.sha(original))


if __name__ == "__main__":
    unittest.main()
