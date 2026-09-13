#!/usr/bin/env python3
"""Read-only preflight or explicitly apply additive native host-control fixtures."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys

from demo_config import load_config, ssh_options

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "infrastructure/host-controls"
SOURCE_FILES = ("hooks.py", "security/paths.py", "sandbox.py", "platform/governance.py",
                "platform/governance_profiles.py", "dashboard/token_auth.py",
                "dashboard/handlers/_shared.py", "dashboard/handlers/core.py")


def absolute(value):
    if not re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", value) or {".", ".."}.intersection(value.split("/")):
        raise argparse.ArgumentTypeError("Use an absolute POSIX path without traversal or shell syntax.")
    return value


def bounded_file(path, limit=128000):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("symlink_file_refused")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("invalid_file_type_or_size")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("file_size_limit")
        return data
    finally:
        os.close(fd)


def request_for(args, config):
    payloads = {name: bounded_file(ASSETS / name, 16000).decode()
                for name in ("anonymous-http.py", "imds-tcp.py")}
    request = {"mode": args.action, "state_dir": args.state_dir,
               "remote_root": config["probe"]["remote_root"],
               "workspace": args.workspace, "port": config["ssh"]["remote_port"],
               "payloads": payloads}
    if args.action == "apply":
        if not args.apply or not args.preflight_receipt:
            raise ValueError("apply_requires_explicit_flag_and_preflight_receipt")
        receipt = json.loads(bounded_file(args.preflight_receipt))
        if (receipt.get("kind") != "host_controls_setup" or receipt.get("schema_version") != 1 or
                receipt.get("applied") is not False or "error" in receipt or not isinstance(receipt.get("binding"), dict)):
            raise ValueError("invalid_preflight_receipt")
        if receipt.get("local_setup_sha256") != hashlib.sha256(bounded_file(ASSETS / "setup.py")).hexdigest():
            raise ValueError("setup_source_changed_since_preflight")
        request["expected"] = receipt["binding"]
    elif args.apply or args.preflight_receipt:
        raise ValueError("apply_options_require_apply_action")
    return request


def execute(args):
    config = load_config(args.config, require_target=True)
    options = ssh_options(config)
    request = request_for(args, config)
    source = bounded_file(ASSETS / "setup.py")
    encoded = base64.b64encode(json.dumps(request, sort_keys=True).encode()).decode()
    argv = ["ssh", *options, "-o", "ConnectTimeout=10", config["ssh"]["admin_alias"],
            shlex.join(["sudo", "-n", args.remote_python, "-", "--request", encoded])]
    # The command contains only reviewed source/config values; no owner token,
    # AWS credential or browser session is transferred. stderr is never echoed.
    result = subprocess.run(argv, input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if len(result.stdout) > 128000:
        raise ValueError("remote_report_too_large")
    try:
        report = json.loads(result.stdout)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("remote_setup_failed_without_report") from None
    if not isinstance(report, dict) or report.get("kind") != "host_controls_setup":
        raise ValueError("invalid_remote_report")
    report["local_setup_sha256"] = hashlib.sha256(source).hexdigest()
    report["source_reference"] = "Hash entries identify inspected remote bytes; setup does not assert source parity or native enforcement."
    reference = args.reference_source_root or ROOT / ".build/installed-nightly/kiro_crew"
    comparison = {}
    for name in SOURCE_FILES:
        remote = report.get("binding", {}).get("sources", {}).get(name, {}).get("sha256")
        local = None
        try:
            local = hashlib.sha256(bounded_file(reference / name, 4_000_000)).hexdigest()
        except FileNotFoundError:
            pass
        comparison[name] = {"local_reference_sha256": local, "matches_local_reference": remote == local if remote and local else None}
    report["source_comparison"] = comparison
    if result.returncode != 0 and "error" not in report:
        report["error"] = "remote_setup_failed"
    return report


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("action", choices=("preflight", "apply"), nargs="?", default="preflight")
    result.add_argument("--config", type=Path, help="Explicit demo config, or KIRO_DEMO_CONFIG.")
    result.add_argument("--workspace", type=absolute, help="Optional exact assertion against the existing Gateway default workspace.")
    result.add_argument("--state-dir", type=absolute, default="/var/lib/kirocrew")
    result.add_argument("--remote-python", type=absolute, default="/opt/kirocrew/venv/bin/python3")
    result.add_argument("--reference-source-root", type=Path,
                        help="Local installed package for source comparison; defaults to .build/installed-nightly/kiro_crew when available.")
    result.add_argument("--apply", action="store_true", help="Required for additive remote file creation.")
    result.add_argument("--preflight-receipt", type=Path, help="Saved JSON from the successful read-only preflight.")
    return result


def main():
    args = parser().parse_args()
    try:
        report = execute(args)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[a-z_]+", str(exc)) else "local_configuration_or_transport_failed"
        report = {"kind": "host_controls_setup", "applied": False, "error": code}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if "error" in report else 0


if __name__ == "__main__":
    raise SystemExit(main())
