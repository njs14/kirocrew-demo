#!/usr/bin/env python3
"""Validate and install a project ARM repack; never start or authenticate Crew."""
from __future__ import annotations

import argparse
import ast
import base64
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import sqlite3
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile

FORMAT = "kirocrew-arm-runtime-bundle"
VERSIONS = {"0.7.0-nightly.20260912t060850", "0.7.0-nightly.20260913t061222"}
METADATA_SHA = "f583e911cbfbe6547e9df5b1894d9ce6d3a053fbae81b9e947bc05d273b37e47"
LOCK_SHA = "ec8fbe5784220eb94a51d44b2d28734dbe2d21a1080d1d7645408bb69ac12427"
CLI_SHA = "f582eac0e002b4d11bbd061d41fcb49d1d37626a2c1fe230373fcbf97755df6f"
CLI_URL = "https://prod.download.cli.kiro.dev/stable/2.21.4/kirocli-aarch64-linux.tar.xz"
MAX_FILE = 512 * 1024 * 1024
MAX_TOTAL = 2 * 1024 * 1024 * 1024
MAX_FILES = 20000
DIST = "kirocrew-0.7.0.dist-info"
FOREIGN = {"linux_x86_64", "macos_arm64", "macos_x86_64", "win_amd64"}
REQUIRED = {"kiro_crew/__init__.py", "kiro_crew/_bootstrap.py", "kiro_crew/hooks.py",
            "kiro_crew/platform/governance.py", f"{DIST}/METADATA"}
ARM_LIBS = {f"kiro_crew/_vendor/llama_cpp_libs/linux_aarch64/{name}" for name in
            ("libggml-base.so.0", "libggml-cpu.so.0", "libggml.so.0", "libllama.so", "libgomp-d22c30c5.so.1.0.0")}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relpath(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("expected a normalized relative POSIX path")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or str(p) != value or value == ".":
        raise ValueError("unsafe relative path")
    return value


def no_links(path: Path) -> None:
    if any(p.is_symlink() for p in [path, *path.parents]):
        raise ValueError(f"linked path is not supported: {path.name}")


def read_regular(path: Path, limit: int = MAX_FILE) -> bytes:
    no_links(path)
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError(f"not a bounded regular file: {path.name}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        after = os.fstat(fd)
        if len(data) != before.st_size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f"file changed while reading: {path.name}")
        return data
    finally:
        os.close(fd)


def binary_arch(data: bytes, name: str) -> bool:
    if data[:4] == b"\x7fELF":
        if len(data) < 20 or data[4:6] != b"\x02\x01" or struct.unpack("<H", data[18:20])[0] != 183:
            raise ValueError(f"non-AArch64 ELF: {name}")
        return True
    if data[:2] == b"MZ" or data[:4] in {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xfe\xed\xfa\xce", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}:
        raise ValueError(f"foreign executable: {name}")
    return False


def version(data: bytes) -> str:
    nodes = ast.parse(data.decode()).body
    versions = [n.value.value for n in nodes if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets)
                and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)]
    if len(versions) != 1 or versions[0] not in VERSIONS:
        raise ValueError("unsupported Crew runtime version; the dependency contract must be reviewed before adding another release")
    return versions[0]


def lock_entries(data: bytes) -> dict[str, tuple[str, set[str]]]:
    entries: dict[str, tuple[str, set[str]]] = {}
    name = None
    for line in data.decode().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([a-zA-Z0-9_.-]+)==([^\s]+)(?: \\)?", line)
        if match:
            name = re.sub(r"[-_.]+", "-", match[1]).lower()
            if name in entries:
                raise ValueError("duplicate dependency")
            entries[name] = (match[2], set())
        elif name and (match := re.fullmatch(r"\s+--hash=sha256:([a-f0-9]{64})(?: \\)?", line)):
            entries[name][1].add(match[1])
        else:
            raise ValueError("dependency lock contains unsupported directives")
    if not entries or any(not hashes for _, hashes in entries.values()):
        raise ValueError("every dependency needs a version and SHA-256")
    return entries


def check_wheels(directory: Path, lock: bytes) -> list[dict]:
    expected, found, rows = lock_entries(lock), set(), []
    for path in sorted(directory.iterdir()):
        data = read_regular(path)
        parts = path.name.split("-")
        if path.suffix != ".whl" or len(parts) not in {5, 6}:
            raise ValueError("wheelhouse must contain only wheel files")
        name = re.sub(r"[-_.]+", "-", parts[0]).lower()
        if name in found or name not in expected or parts[1] != expected[name][0] or sha(data) not in expected[name][1]:
            raise ValueError(f"wheel differs from pinned dependency lock: {path.name}")
        if not (parts[-1] == "any.whl" or ("aarch64" in parts[-1] and "linux" in parts[-1])):
            raise ValueError(f"wheel platform is not Linux ARM: {path.name}")
        binaries, size, names = [], 0, set()
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > MAX_FILES:
                raise ValueError("wheel member limit exceeded")
            for item in archive.infolist():
                relpath(item.filename.rstrip("/"))
                if item.filename in names or stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError("linked or duplicate wheel member")
                names.add(item.filename)
                size += item.file_size
                if item.file_size > MAX_FILE or size > MAX_TOTAL:
                    raise ValueError("wheel exceeds extraction bounds")
                if not item.is_dir():
                    with archive.open(item) as stream:
                        head = stream.read(20)
                    if binary_arch(head, item.filename):
                        binaries.append(item.filename)
        found.add(name)
        rows.append({"path": "wheels/" + path.name, "bytes": len(data), "sha256": sha(data), "aarch64_binaries": binaries})
    if found != set(expected):
        raise ValueError("wheelhouse is incomplete for the pinned lock")
    return rows


def archive_inventory(path: Path, *, cli: bool = False) -> tuple[list[dict], dict[str, bytes]]:
    rows, small, names, total = [], {}, set(), 0
    with tarfile.open(path, "r:*") as archive:
        for item in archive:
            name = relpath(item.name.rstrip("/"))
            if name in names or not (item.isfile() or item.isdir()):
                raise ValueError("archive contains a link, special file or duplicate path")
            names.add(name)
            if len(names) > MAX_FILES or item.size > (1024 * 1024 * 1024 if cli else MAX_FILE):
                raise ValueError("archive exceeds member bounds")
            if cli:
                if PurePosixPath(name).parts[0] != "kirocli":
                    raise ValueError("unexpected Kiro CLI archive root")
            elif PurePosixPath(name).parts[0] not in {"kiro_crew", DIST}:
                raise ValueError("runtime archive contains non-package state")
            if not item.isfile():
                continue
            total += item.size
            if total > MAX_TOTAL:
                raise ValueError("archive exceeds extraction bounds")
            stream = archive.extractfile(item)
            head = stream.read(20)
            arm = binary_arch(head, name)
            digest = hashlib.sha256(head)
            count = len(head)
            keep = name in {"kiro_crew/__init__.py", f"{DIST}/METADATA", "kiro_crew/BUILD_VERSION"}
            chunks = [head] if keep else []
            while chunk := stream.read(1024 * 1024):
                count += len(chunk)
                digest.update(chunk)
                if keep:
                    if count > 8 * 1024 * 1024:
                        raise ValueError("runtime version or metadata exceeds its size bound")
                    chunks.append(chunk)
            if count != item.size:
                raise ValueError("archive member length differs from its header")
            if any(part in FOREIGN for part in PurePosixPath(name).parts):
                raise ValueError("runtime includes foreign vendor directory")
            rows.append({"path": name, "bytes": count, "sha256": digest.hexdigest(), "mode": 0o755 if item.mode & 0o111 else 0o644, "aarch64_binary": arm})
            if keep:
                small[name] = b"".join(chunks)
    if cli:
        required = {"kirocli/bin/kiro-cli", "kirocli/bin/kiro-cli-chat", "kirocli/bin/kiro-cli-term"}
        if not required.issubset({row["path"] for row in rows if row["aarch64_binary"]}):
            raise ValueError("official Kiro CLI archive lacks expected ARM executables")
    else:
        paths = {row["path"] for row in rows}
        if not REQUIRED.issubset(paths) or not ARM_LIBS.issubset({row["path"] for row in rows if row["aarch64_binary"]}):
            raise ValueError("runtime package or ARM vendored libraries are incomplete")
        version(small["kiro_crew/__init__.py"])
        if "kiro_crew/BUILD_VERSION" in paths:
            raise ValueError("stamped enterprise build needs separate compatibility review")
        if sha(small[f"{DIST}/METADATA"]) != METADATA_SHA:
            raise ValueError("upstream dependency metadata differs from reviewed lock contract")
    return sorted(rows, key=lambda row: row["path"]), small


def verify(bundle: Path, manifest_sha: str | None = None) -> dict:
    raw = read_regular(bundle / "manifest.json", 16 * 1024 * 1024)
    if manifest_sha is not None and sha(raw) != manifest_sha:
        raise ValueError("manifest differs from caller's expected SHA-256")
    manifest = json.loads(raw)
    if manifest.get("format") != FORMAT or manifest.get("schema_version") != 1 or manifest.get("runtime_version") not in VERSIONS:
        raise ValueError("unsupported bundle format or runtime version")
    files = manifest.get("files")
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError("bundle file list is missing or unbounded")
    names, total = set(), 0
    for row in files:
        name = relpath(row["path"])
        if name in names or name == "manifest.json":
            raise ValueError("duplicate manifest file path")
        names.add(name)
        data = read_regular(bundle / name)
        total += len(data)
        if total > MAX_TOTAL or row["bytes"] != len(data) or row["sha256"] != sha(data):
            raise ValueError(f"bundle member differs from manifest: {name}")
    actual = set()
    for directory, dirs, items in os.walk(bundle, followlinks=False):
        for name in dirs:
            no_links(Path(directory) / name)
        for name in items:
            path = Path(directory) / name
            no_links(path)
            actual.add(path.relative_to(bundle).as_posix())
    if actual != names | {"manifest.json"}:
        raise ValueError("bundle contains unlisted or missing files")
    required = {"runtime.tar.gz", "crew-requirements-linux-arm64.lock", "kirocli-aarch64-linux.tar.xz", "install-runtime-bundle.py"}
    if not required.issubset(names) or any(name not in required and not name.startswith("wheels/") for name in names):
        raise ValueError("unexpected bundle layout")
    lock = read_regular(bundle / "crew-requirements-linux-arm64.lock")
    if sha(lock) != LOCK_SHA or sha(read_regular(bundle / "kirocli-aarch64-linux.tar.xz")) != CLI_SHA:
        raise ValueError("lock or official CLI checksum differs from reviewed contract")
    runtime, small = archive_inventory(bundle / "runtime.tar.gz")
    if runtime != manifest.get("runtime_files") or version(small["kiro_crew/__init__.py"]) != manifest["runtime_version"]:
        raise ValueError("runtime inventory/version differs from manifest")
    wheels = check_wheels(bundle / "wheels", lock)
    if wheels != manifest.get("wheels"):
        raise ValueError("wheel inventory differs from manifest")
    archive_inventory(bundle / "kirocli-aarch64-linux.tar.xz", cli=True)
    return manifest


def host_check(prefix: Path) -> None:
    if os.geteuid() != 0 or sys.platform != "linux" or platform.machine() != "aarch64" or sys.version_info[:2] != (3, 12):
        raise ValueError("install requires root on Linux aarch64 with CPython 3.12")
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE VIRTUAL TABLE fts_probe USING fts5(content)")
    if not prefix.is_absolute() or prefix == Path("/"):
        raise ValueError("prefix must be an absolute directory below a root-owned parent")
    no_links(prefix)
    for parent in [prefix, *prefix.parents]:
        if parent.exists():
            info = parent.stat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError("runtime parent must be root-owned and not group/world writable")
    if any(path.exists() or path.is_symlink() for path in (prefix / "venv", prefix / "runtime-installation.json")):
        raise ValueError("runtime destination exists; replacement/upgrade is a separate reviewed operation")


def install(bundle: Path, digest: str, prefix: Path) -> dict:
    host_check(prefix)
    validated = verify(bundle, digest)
    installer_row = next(row for row in validated["files"] if row["path"] == "install-runtime-bundle.py")
    if sha(read_regular(Path(__file__).absolute())) != installer_row["sha256"]:
        raise ValueError("executing installer differs from the reviewed bundle installer")
    # Validate a root-private copy again, so pip/extraction never consume an
    # upload directory that the uploading SSH account can change mid-install.
    temporary_parent = Path("/tmp")
    no_links(temporary_parent)
    temporary_info = temporary_parent.stat()
    if temporary_info.st_uid != 0 or (temporary_info.st_mode & 0o022 and not temporary_info.st_mode & stat.S_ISVTX):
        raise ValueError("/tmp must be root-owned with its sticky bit when writable by others")
    with tempfile.TemporaryDirectory(prefix="kirocrew-runtime-", dir=temporary_parent) as private:
        snapshot = Path(private) / "bundle"
        snapshot.mkdir(mode=0o700)
        expected = [{"path": "manifest.json", "sha256": digest}, *validated["files"]]
        for row in expected:
            name = row["path"]
            target = snapshot / relpath(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            data = read_regular(bundle / name)
            if sha(data) != row["sha256"] or ("bytes" in row and len(data) != row["bytes"]):
                raise ValueError("upload changed while copying the reviewed bundle")
            target.write_bytes(data)
        manifest = verify(snapshot, digest)
        prefix.mkdir(mode=0o755, parents=True, exist_ok=True)
        venv = prefix / "venv"
        venv.mkdir(mode=0o755)  # Exclusive creation: never erase an existing runtime.
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            python = venv / "bin/python3"
            subprocess.run([str(python), "-m", "pip", "--isolated", "install", "--no-index", "--find-links", str(snapshot / "wheels"), "--require-hashes", "--only-binary=:all:", "-r", str(snapshot / "crew-requirements-linux-arm64.lock")], check=True)
            site = venv / "lib/python3.12/site-packages"
            with tarfile.open(snapshot / "runtime.tar.gz") as archive:
                for item in archive:
                    target = site / relpath(item.name.rstrip("/"))
                    if item.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with target.open("xb") as output:
                            shutil.copyfileobj(archive.extractfile(item), output)
                        target.chmod(0o755 if item.mode & 0o111 else 0o644)
            launcher = venv / "bin/kirocrew"
            launcher.write_text(f"#!{python}\nfrom kiro_crew import platform_compat\nfrom kiro_crew._ssl_compat import _ensure_ssl_certs\nplatform_compat.ensure_utf8_console()\n_ensure_ssl_certs()\nfrom kiro_crew._bootstrap import main\nmain()\n")
            launcher.chmod(0o755)
            metadata = site / DIST
            (metadata / "INSTALLER").write_text("kirocrew-project-arm-repack\n")
            provenance = {"bundle_manifest_sha256": digest, "runtime_version": manifest["runtime_version"], "packaging": manifest["packaging"], "runtime_files": manifest["runtime_files"], "service_started": False, "kiro_cli_installed": False}
            (metadata / "ARM_REPACK.json").write_text(json.dumps(provenance, indent=2) + "\n")
            record = metadata / "RECORD"
            with record.open("w", newline="") as stream:
                writer = csv.writer(stream)
                for path in sorted(p for top in (site / "kiro_crew", metadata) for p in top.rglob("*") if p.is_file() and p != record):
                    data = path.read_bytes()
                    writer.writerow([str(path.relative_to(site)), "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("="), len(data)])
                data = launcher.read_bytes()
                writer.writerow([os.path.relpath(launcher, site), "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("="), len(data)])
                writer.writerow([str(record.relative_to(site)), "", ""])
            for directory, dirs, files in os.walk(venv):
                for name in [directory, *(str(Path(directory) / file) for file in files)]:
                    path = Path(name)
                    if not path.is_symlink():
                        path.chmod(path.stat().st_mode & ~0o022)
            subprocess.run([str(python), "-m", "pip", "check"], check=True)
            subprocess.run([str(python), "-c", "import kiro_crew, aiohttp, cryptography, jsonschema, lxml.etree, numpy, PIL.Image; import sys; sys.exit(0 if kiro_crew.__version__ == " + repr(manifest["runtime_version"]) + " else 1)"], check=True)
            (prefix / "runtime-installation.json").write_text(json.dumps(provenance, indent=2) + "\n")
            return provenance
        except BaseException:
            shutil.rmtree(venv)  # Only the directory exclusively created above.
            raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "plan", "install"))
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--prefix", type=Path, default=Path("/opt/kirocrew"))
    args = parser.parse_args()
    try:
        bundle = args.bundle.expanduser().absolute()
        digest = args.manifest_sha256 or sha(read_regular(bundle / "manifest.json", 16 * 1024 * 1024))
        manifest = verify(bundle, digest)
        if args.command == "install":
            if args.manifest_sha256 is None:
                raise ValueError("install requires --manifest-sha256 from the reviewed local preparation result")
            result = install(bundle, args.manifest_sha256, args.prefix)
        else:
            result = {"status": "verified", "manifest_sha256": digest, "runtime_version": manifest["runtime_version"], "runtime_file_count": len(manifest["runtime_files"]), "wheel_count": len(manifest["wheels"]), "native_runtime_executed": False, "install_prefix": str(args.prefix), "required_host": "root, Linux aarch64, CPython 3.12 + venv + SQLite FTS5", "service_started": False}
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, KeyError, SyntaxError, tarfile.TarError, zipfile.BadZipFile, subprocess.CalledProcessError, sqlite3.Error) as exc:
        parser.exit(2, f"Runtime bundle failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
