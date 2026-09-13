#!/usr/bin/env python3
"""Freeze a user-provided installed kiro_crew package without importing it.

This command copies local package bytes only. It does not download, install,
authenticate, or establish acceptance of a different KiroCrew build.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "kirocrew-demo-baseline"
MAX_FILES = 20_000
MAX_BYTES = 512 * 1024 * 1024
MAX_FILE_BYTES = 128 * 1024 * 1024
REQUIRED = {"__init__.py", "hooks.py", "sel.py", "security/redaction.py", "platform/governance.py"}
EXCLUDED_DIRS = {"__pycache__", ".git", ".cache", "cache", "caches", ".aws", ".ssh", ".kirocrew", ".venv", "node_modules"}
EXCLUDED_FILES = {"credentials", "credentials.json", "credentials.yaml", "credentials.yml", "auth.json", "token.json", "tokens.json", "session.json", "id_rsa", "id_ed25519"}


def excluded(path: PurePosixPath) -> bool:
    return (any(part.lower() in EXCLUDED_DIRS for part in path.parts)
            or path.name.lower() in EXCLUDED_FILES
            or path.name.lower().startswith(".env")
            or path.suffix.lower() in {".pyc", ".pyo", ".pem", ".key", ".p12", ".pfx"})


def relative_path(value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("manifest file paths must be relative POSIX paths")
    posix = PurePosixPath(value)
    if posix.is_absolute() or any(p in {".", ".."} for p in posix.parts) or str(posix) != value:
        raise ValueError("manifest file paths must be normalized and cannot escape the snapshot")
    return Path(*posix.parts)


def read_regular(path: Path) -> bytes:
    # Do not follow links even if a package file is exchanged after inventory.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
            raise ValueError(f"not a bounded regular package file: {path.name}")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            value = handle.read(MAX_FILE_BYTES + 1)
        after = os.fstat(fd)
        if len(value) != before.st_size or len(value) > MAX_FILE_BYTES or (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise ValueError(f"package file changed while reading: {path.name}")
        return value
    finally:
        os.close(fd)


def inventory(package: Path, *, strict: bool = False) -> tuple[list[dict], list[str]]:
    if package.is_symlink() or not package.is_dir():
        raise ValueError("package must be a real kiro_crew directory, not a link")
    rows, skipped, total = [], [], 0
    for directory, directories, files in os.walk(package, followlinks=False):
        for name in list(directories):
            path = Path(directory) / name
            rel = path.relative_to(package).as_posix()
            if path.is_symlink():
                raise ValueError(f"linked package directory is not supported: {rel}")
            if excluded(PurePosixPath(rel)):
                if strict:
                    raise ValueError(f"unlisted state or cache directory in frozen snapshot: {rel}")
                directories.remove(name)
                skipped.append(rel + "/")
        for name in files:
            path = Path(directory) / name
            rel = path.relative_to(package).as_posix()
            relative_path(rel)
            if path.is_symlink():
                raise ValueError(f"linked package file is not supported: {rel}")
            if excluded(PurePosixPath(rel)):
                if strict:
                    raise ValueError(f"unlisted state or cache file in frozen snapshot: {rel}")
                skipped.append(rel)
                continue
            value = read_regular(path)
            total += len(value)
            if len(rows) >= MAX_FILES or total > MAX_BYTES:
                raise ValueError("package exceeds the 20,000-file / 512 MiB snapshot bound")
            rows.append({"path": rel, "sha256": hashlib.sha256(value).hexdigest(), "bytes": len(value)})
    rows.sort(key=lambda row: row["path"])
    if not REQUIRED.issubset({row["path"] for row in rows}):
        raise ValueError("select the installed kiro_crew package directory containing hooks.py, sel.py, security/redaction.py and platform/governance.py")
    return rows, sorted(skipped)


def tree_digest(rows: list[dict]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def package_version(package: Path) -> str:
    tree = ast.parse(read_regular(package / "__init__.py").decode("utf-8"))
    values = [n.value.value for n in tree.body if isinstance(n, ast.Assign)
              and any(isinstance(t, ast.Name) and t.id == "__version__" for t in n.targets)
              and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)]
    if len(values) != 1 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,99}", values[0]):
        raise ValueError("cannot read an unambiguous literal __version__ without executing the package")
    base = values[0]
    stamp = package / "BUILD_VERSION"
    if stamp.exists():
        if stamp.is_symlink():
            raise ValueError("BUILD_VERSION cannot be a link")
        raw = read_regular(stamp)
        candidate = raw.decode("utf-8").strip()
        if len(raw) > 64 or not (candidate == base or re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", base) and re.fullmatch(re.escape(base) + r"\.[0-9]+", candidate)):
            raise ValueError("BUILD_VERSION is ambiguous; use a package with a valid version stamp")
        return candidate
    return base


def validate_manifest(manifest_path: Path, repository_root: Path = ROOT) -> tuple[Path, dict]:
    manifest_path = manifest_path.expanduser().absolute()
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("baseline manifest is missing or linked; run python3 scripts/prepare-demo-baseline.py --package /path/to/site-packages/kiro_crew, then pass --baseline-manifest .build/demo-baselines/<name>/manifest.json")
    if manifest_path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("baseline manifest exceeds 8 MiB")
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict):
        raise ValueError("baseline manifest must be an object")
    legacy = manifest_path.resolve() == (repository_root / "evidence/nightly/installed-nightly-verification.json").resolve() and "schema" not in manifest
    if not legacy and (manifest.get("schema") != 1 or manifest.get("format") != FORMAT):
        raise ValueError("unsupported baseline manifest schema")
    snapshot = relative_path(manifest.get("snapshot"))
    base = repository_root if legacy else manifest_path.parent
    package = base / snapshot
    current = base
    for part in snapshot.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("snapshot path must not contain links")
    if package.name != "kiro_crew":
        raise ValueError("snapshot must name a kiro_crew package directory")
    if not package.is_dir():
        raise ValueError("baseline snapshot is not present on this machine; prepare your installed package with scripts/prepare-demo-baseline.py and select its --baseline-manifest")
    rows = manifest.get("snapshot_files")
    if not isinstance(rows, list) or not rows or len(rows) > MAX_FILES:
        raise ValueError("baseline snapshot_files must be a bounded nonempty list")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"path", "sha256", "bytes"}:
            raise ValueError("invalid snapshot file entry")
        relative_path(row["path"])
        if row["path"] in seen or not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) or type(row["bytes"]) is not int or not 0 <= row["bytes"] <= MAX_FILE_BYTES:
            raise ValueError("duplicate or invalid snapshot file entry")
        seen.add(row["path"])
    actual, _ = inventory(package, strict=True)
    if actual != sorted(rows, key=lambda row: row["path"]):
        raise ValueError("baseline snapshot changed: file set, bytes or SHA-256 differs from manifest")
    if not legacy and tree_digest(actual) != manifest.get("snapshot_digest"):
        raise ValueError("snapshot manifest digest mismatch")
    if package_version(package) != manifest.get("version"):
        raise ValueError("snapshot version differs from manifest")
    return package, {"installed_version": manifest["version"], "snapshot_digest": manifest["snapshot_digest"],
                     "source_commit": None, "scope": "frozen snapshot of user-installed package",
                     "accepted_baseline": False, "historical_manifest_selected": legacy,
                     "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest()}


def prepare(package: Path, output: Path, repository_root: Path = ROOT) -> Path:
    package = package.expanduser().absolute()
    if package.name != "kiro_crew":
        raise ValueError("--package must point directly to an installed kiro_crew directory, not an application or user home")
    if any(parent.is_symlink() for parent in [package, *package.parents]):
        raise ValueError("--package must use a resolved path without symlinks")
    package = package.resolve(strict=True)
    output = output.expanduser().absolute()
    build = (repository_root / ".build").resolve()
    if output.exists() or output.is_symlink():
        raise ValueError("choose a fresh output directory; snapshots are never overwritten")
    if not output.resolve().is_relative_to(build) or output.resolve() == build:
        raise ValueError("--output must be a new directory inside this checkout's ignored .build directory")
    if output.resolve().is_relative_to(package) or package.is_relative_to(output.resolve()):
        raise ValueError("source and output directories must not overlap")
    rows, skipped = inventory(package)
    version = package_version(package)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(mode=0o700)
    try:
        target = output / "kiro_crew"
        target.mkdir(mode=0o700)
        for row in rows:
            value = read_regular(package / row["path"])
            if len(value) != row["bytes"] or hashlib.sha256(value).hexdigest() != row["sha256"]:
                raise ValueError("source package changed during preparation")
            destination = target / row["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(value)
        if inventory(package)[0] != rows or inventory(target, strict=True)[0] != rows:
            raise ValueError("source or snapshot changed during preparation")
        manifest = {"schema": 1, "format": FORMAT, "version": version,
                    "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "snapshot": "kiro_crew", "snapshot_files": rows, "snapshot_digest": tree_digest(rows),
                    "digest_format": "sha256 of sorted compact JSON snapshot_files with sorted keys",
                    "source": {"kind": "user-provided-local-installed-package", "path": str(package)},
                    "excluded_paths": skipped, "package_imported": False, "package_downloaded": False,
                    "accepted_baseline": False,
                    "scope": "Local package provenance only; controls and backend acceptance require separate runs."}
        path = output / "manifest.json"
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        validate_manifest(path, repository_root)
        return path
    except BaseException:
        shutil.rmtree(output)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path, help="Existing installed kiro_crew package directory; never a user state directory")
    parser.add_argument("--output", type=Path, default=ROOT / ".build/demo-baselines" / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"), help="Fresh output directory under .build")
    args = parser.parse_args()
    try:
        path = prepare(args.package, args.output)
    except (OSError, ValueError, SyntaxError) as exc:
        parser.exit(2, f"Baseline preparation failed: {exc}\n")
    print(json.dumps({"manifest": str(path), "accepted_baseline": False, "package_imported": False}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
