#!/usr/bin/env python3
"""Plan, install, activate or roll back the root-managed EC2 demo policy."""
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

from demo_config import load_config, ssh_options

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "infrastructure/enterprise-policy"


def read(path, limit=128000):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("invalid_local_file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("local_file_size_limit")
        return data
    finally:
        os.close(fd)


def absolute(value):
    if not re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", value) or {".", ".."}.intersection(value.split("/")):
        raise argparse.ArgumentTypeError("Use an absolute POSIX path without traversal or shell syntax.")
    return value


def request_for(args, config, source):
    result = {"mode": args.action, "service": args.service, "state_dir": args.state_dir,
              "installer_sha256": hashlib.sha256(source).hexdigest(), "apply": args.apply,
              "deployment": {key: config["aws"][key] for key in ("region", "account_id", "stack_name", "instance_id")},
              "template": read(ASSETS / "policy.template.json", 16000).decode()}
    if args.action in {"apply", "activate", "rollback"} and not args.apply:
        raise ValueError("mutation_requires_apply_flag")
    if args.action in {"preflight", "plan"}:
        if args.apply or args.receipt:
            raise ValueError("read_only_action_rejects_mutation_options")
    else:
        if not args.receipt:
            raise ValueError("prior_receipt_required")
        receipt = json.loads(read(args.receipt))
        if args.action == "apply":
            if receipt.get("kind") != "enterprise_policy_plan" or receipt.get("schema_version") != 1:
                raise ValueError("prior_plan_required")
            result["expected_plan"] = receipt
        else:
            if receipt.get("kind") != "enterprise_policy_install" or receipt.get("schema_version") != 1:
                raise ValueError("prior_install_receipt_required")
            result["expected_plan_id"] = receipt["plan"]["plan_id"]
    return result


def execute(args):
    config = load_config(args.config, require_target=True)
    options = ssh_options(config)
    source = read(ASSETS / "manage.py", 100000)
    request = request_for(args, config, source)
    encoded_request = base64.b64encode(json.dumps(request, sort_keys=True).encode()).decode()
    command = shlex.join(["sudo", "-n", args.remote_python, "-", "--request", encoded_request])
    response = subprocess.run(["ssh", *options, "-o", "ConnectTimeout=10", config["ssh"]["admin_alias"], command],
                              input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=110)
    if len(response.stdout) > 128000:
        raise ValueError("remote_report_size_limit")
    try:
        result = json.loads(response.stdout)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("remote_operation_failed_without_report") from None
    if not isinstance(result, dict) or not str(result.get("kind", "")).startswith("enterprise_policy_"):
        raise ValueError("invalid_remote_report")
    if response.returncode != 0 and "error" not in result:
        result["error"] = "remote_operation_failed"
    return result


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("action", choices=("preflight", "plan", "apply", "activate", "verify", "rollback"),
                        nargs="?", default="preflight")
    result.add_argument("--config", type=Path, help="Explicit deployment config, or KIRO_DEMO_CONFIG.")
    result.add_argument("--service", default="kirocrew-demo.service")
    result.add_argument("--state-dir", type=absolute, default="/var/lib/kirocrew")
    result.add_argument("--remote-python", type=absolute, default="/opt/kirocrew/venv/bin/python3")
    result.add_argument("--receipt", type=Path, help="Exact prior plan for apply; original install receipt for verify/activate/rollback.")
    result.add_argument("--apply", action="store_true", help="Required for each mutation. Activate and rollback restart the named Gateway service.")
    return result


def main():
    args = parser().parse_args()
    try:
        report = execute(args)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[a-z_]+", str(exc)) else "local_configuration_or_transport_failed"
        report = {"kind": "enterprise_policy_error", "error": code}
    print(json.dumps(report, indent=2, sort_keys=True))
    return int("error" in report)


if __name__ == "__main__":
    raise SystemExit(main())
