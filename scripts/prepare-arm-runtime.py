#!/usr/bin/env python3
"""Prepare an offline ARM runtime bundle from an explicitly selected Crew package."""
from __future__ import annotations

import argparse
import gzip
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "infrastructure/install-runtime-bundle.py"
spec = importlib.util.spec_from_file_location("runtime_bundle", INSTALLER)
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)
baseline_spec = importlib.util.spec_from_file_location("demo_baseline", ROOT / "scripts/prepare-demo-baseline.py")
baseline = importlib.util.module_from_spec(baseline_spec)
baseline_spec.loader.exec_module(baseline)


def source_files(package: Path, metadata: Path) -> tuple[list[tuple[str, Path]], list[str], str]:
    bundle.no_links(package)
    bundle.no_links(metadata)
    if package.name != "kiro_crew" or metadata.name != bundle.DIST:
        raise ValueError("select the kiro_crew package and its matching kirocrew-0.7.0.dist-info directory")
    version = bundle.version(bundle.read_regular(package / "__init__.py"))
    if (package / "BUILD_VERSION").exists():
        raise ValueError("stamped enterprise builds require a reviewed dependency contract")
    if bundle.sha(bundle.read_regular(metadata / "METADATA")) != bundle.METADATA_SHA:
        raise ValueError("selected package metadata does not match the reviewed ARM dependency lock")
    inventory, excluded = baseline.inventory(package)
    selected = []
    for row in inventory:
        rel = PurePosixPath(row["path"])
        if len(rel.parts) >= 3 and rel.parts[:2] == ("_vendor", "llama_cpp_libs") and rel.parts[2] in bundle.FOREIGN:
            excluded.append(row["path"])
            continue
        selected.append(("kiro_crew/" + row["path"], package / row["path"]))
    for directory, dirs, files in os.walk(metadata, followlinks=False):
        for name in dirs:
            bundle.no_links(Path(directory) / name)
        for name in files:
            path = Path(directory) / name
            rel = path.relative_to(metadata).as_posix()
            bundle.no_links(path)
            if rel in {"METADATA", "entry_points.txt", "top_level.txt"} or rel.startswith("licenses/"):
                if baseline.excluded(PurePosixPath(rel)):
                    raise ValueError("unexpected state file in package license metadata")
                selected.append((bundle.DIST + "/" + rel, path))
    return sorted(selected), sorted(excluded), version


def runtime_archive(files: list[tuple[str, Path]], target: Path) -> None:
    # Fixed timestamps/owners and preserved executable bits make the archive
    # repeatable for the same source bytes without importing the package.
    with target.open("xb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed, tarfile.open(fileobj=compressed, mode="w") as archive:
        for name, path in files:
            data = bundle.read_regular(path)
            item = tarfile.TarInfo(name)
            item.size = len(data)
            item.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
            archive.addfile(item, io.BytesIO(data))


def wheel_command(output: Path) -> list[str]:
    return [sys.executable, "-m", "pip", "--isolated", "download", "--index-url", "https://pypi.org/simple", "--disable-pip-version-check", "--require-hashes", "--only-binary=:all:", "--no-deps",
            "--platform", "manylinux2014_aarch64", "--platform", "manylinux_2_28_aarch64", "--platform", "manylinux_2_34_aarch64",
            "--python-version", "3.12", "--implementation", "cp", "--abi", "cp312", "--abi", "abi3", "--dest", str(output / "wheels"),
            "-r", str(ROOT / "infrastructure/crew-requirements-linux-arm64.lock")]


def prepare(package: Path, metadata: Path, output: Path, wheelhouse: Path | None, cli_archive: Path | None, *, plan: bool = False) -> dict:
    package, metadata, output = (path.expanduser().absolute() for path in (package, metadata, output))
    if any(".." in path.parts for path in (package, metadata, output)):
        raise ValueError("source/output paths must not contain parent traversal")
    bundle.no_links(output)
    if output.exists():
        raise ValueError("choose a fresh bundle directory; preparation never overwrites an existing output")
    if not output.is_relative_to(ROOT / ".build") or output == ROOT / ".build":
        raise ValueError("bundle output must be a fresh directory under this checkout's ignored .build")
    if output.is_relative_to(package) or package.is_relative_to(output):
        raise ValueError("source and output paths overlap")
    files, excluded, version = source_files(package, metadata)
    lock = bundle.read_regular(ROOT / "infrastructure/crew-requirements-linux-arm64.lock")
    if bundle.sha(lock) != bundle.LOCK_SHA:
        raise ValueError("repository dependency lock differs from the reviewed contract")
    result = {"runtime_version": version, "source_files": len(files), "output": str(output), "packaging": "Custom Linux ARM64 repack of an explicitly selected installed KiroCrew package; not an official Linux release artifact.",
              "wheel_command": wheel_command(output) if wheelhouse is None else None,
              "kiro_cli": {"version": "2.21.4", "url": bundle.CLI_URL, "sha256": bundle.CLI_SHA, "download": cli_archive is None},
              "native_runtime_executed": False, "credentials_or_user_configuration_copied": False}
    if plan:
        result["status"] = "plan_only"
        return result
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(mode=0o700)
    try:
        runtime_archive(files, output / "runtime.tar.gz")
        runtime_files, small = bundle.archive_inventory(output / "runtime.tar.gz")
        if bundle.version(small["kiro_crew/__init__.py"]) != version:
            raise ValueError("source package version changed during preparation")
        # Ensure the live source still matches every captured file, including modes.
        if source_files(package, metadata) != (files, excluded, version):
            raise ValueError("source package file set changed during preparation")
        for row, (name, path) in zip(runtime_files, files, strict=True):
            data = bundle.read_regular(path)
            if name != row["path"] or bundle.sha(data) != row["sha256"] or len(data) != row["bytes"]:
                raise ValueError("source package bytes changed during preparation")
        (output / "crew-requirements-linux-arm64.lock").write_bytes(lock)
        (output / "install-runtime-bundle.py").write_bytes(bundle.read_regular(INSTALLER))
        wheels = output / "wheels"
        wheels.mkdir()
        if wheelhouse is None:
            subprocess.run(wheel_command(output), check=True, stdout=sys.stderr)
        else:
            wheelhouse = wheelhouse.expanduser().absolute()
            bundle.check_wheels(wheelhouse, lock)
            for path in sorted(wheelhouse.iterdir()):
                (wheels / path.name).write_bytes(bundle.read_regular(path))
        wheel_rows = bundle.check_wheels(wheels, lock)
        cli = output / "kirocli-aarch64-linux.tar.xz"
        if cli_archive is None:
            with urllib.request.urlopen(bundle.CLI_URL, timeout=60) as response, cli.open("xb") as stream:
                if not response.url.startswith("https://prod.download.cli.kiro.dev/"):
                    raise ValueError("official CLI download redirected outside the approved host")
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > bundle.MAX_FILE:
                        raise ValueError("Kiro CLI archive exceeds the size bound")
                    stream.write(chunk)
        else:
            cli.write_bytes(bundle.read_regular(cli_archive.expanduser().absolute()))
        if bundle.sha(bundle.read_regular(cli)) != bundle.CLI_SHA:
            raise ValueError("Kiro CLI archive differs from the official pinned checksum")
        bundle.archive_inventory(cli, cli=True)
        rows = []
        for path in sorted(output.rglob("*")):
            if path.is_file():
                data = bundle.read_regular(path)
                rows.append({"path": path.relative_to(output).as_posix(), "bytes": len(data), "sha256": bundle.sha(data)})
        manifest = {"schema_version": 1, "format": bundle.FORMAT, "runtime_version": version,
                    "target": {"os": "Ubuntu 24.04", "architecture": "aarch64", "python": "3.12"},
                    "packaging": result["packaging"], "distribution_metadata_version": "0.7.0",
                    "source": {"kind": "user-provided-installed-package", "package_imported": False, "user_state_copied": False},
                    "upstream_metadata_sha256": bundle.METADATA_SHA, "files": rows,
                    "runtime_files": runtime_files, "excluded_package_paths": excluded,
                    "wheels": wheel_rows, "kiro_cli": result["kiro_cli"],
                    "acceptance": "Preparation and static validation only; native ARM runtime and control acceptance require the live demo checks."}
        # A local cache changes acquisition, not the content manifest.
        manifest["kiro_cli"].pop("download")
        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        digest = bundle.sha(bundle.read_regular(manifest_path))
        bundle.verify(output, digest)
        result.update(status="prepared_and_verified", manifest=str(manifest_path), manifest_sha256=digest,
                      runtime_files=len(runtime_files), wheels=len(wheel_rows))
        return result
    except BaseException:
        shutil.rmtree(output)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "prepare"))
    parser.add_argument("--package", type=Path, required=True, help="Explicit installed kiro_crew directory; not a user home/state directory")
    parser.add_argument("--metadata", type=Path, help="Matching dist-info directory; defaults to the package's sibling")
    parser.add_argument("--output", type=Path, required=True, help="Fresh directory inside this checkout's ignored .build")
    parser.add_argument("--wheelhouse", type=Path, help="Optional previously downloaded cache; all 48 wheels must match the pinned lock")
    parser.add_argument("--kiro-cli-archive", type=Path, help="Optional official ARM 2.21.4 archive; checksum and ELF architecture are checked")
    args = parser.parse_args()
    try:
        result = prepare(args.package, args.metadata or args.package.parent / bundle.DIST, args.output, args.wheelhouse, args.kiro_cli_archive, plan=args.command == "plan")
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, SyntaxError, tarfile.TarError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"ARM preparation failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
