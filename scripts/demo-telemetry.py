#!/usr/bin/env python3
"""Collect bounded client metrics for the demo. All changes require --apply.

This is a custom demo collector, separate from KiroCrew product analytics.
Read-only collection never reads command arguments, environment, or app state.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_FILE = ROOT / "infrastructure/observability-collector/collector.py"
LABEL = "com.kirocrew.demo-observability"
PLIST = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
STATE = Path.home() / "Library/Application Support/kirocrew-demo-observability"
SSH_ALIAS = "kirocrew-demo-admin"
HOST_KEY_ALIAS = None
KNOWN_HOSTS = Path.home() / ".ssh/kirocrew-demo-known_hosts"
REMOTE_RECEIVER = "sudo -n /usr/bin/python3 /opt/kirocrew-demo/observability/collector.py receive-client"
SSH_CONFIG = None
CONFIG_PATH = None
INTERVAL_SECONDS = 60
CLIENT_OPTIONS = {}


def configure(config):
    """Resolve reviewed, non-secret deployment settings through the shared loader."""
    global LABEL, PLIST, STATE, SSH_ALIAS, HOST_KEY_ALIAS, KNOWN_HOSTS, REMOTE_RECEIVER
    global SSH_CONFIG, CONFIG_PATH, INTERVAL_SECONDS, CLIENT_OPTIONS
    ssh, client, telemetry = config["ssh"], config["client"], config["telemetry"]
    LABEL = telemetry["launch_label"]
    PLIST = Path(telemetry["launch_plist_path"])
    STATE = Path(telemetry["state_dir"])
    SSH_ALIAS = ssh["admin_alias"]
    HOST_KEY_ALIAS = ssh["host_key_alias"]
    KNOWN_HOSTS = Path(ssh["known_hosts_path"]) if ssh.get("known_hosts_path") else None
    SSH_CONFIG = ssh.get("config_path")
    CONFIG_PATH = config.get("_config_path")
    INTERVAL_SECONDS = telemetry["interval_seconds"]
    REMOTE_RECEIVER = shlex.join(["sudo", "-n", "/usr/bin/python3", telemetry["remote_collector_path"], "receive-client"])
    CLIENT_OPTIONS = {"app_root": str(Path(client["app_path"]) / "Contents") if client["app_path"] else None,
                      "executable": client.get("executable"), "remote_gateway_port": ssh["local_port"],
                      "local_gateway_port": client["local_gateway_port"],
                      "check_local_gateway": client.get("check_local_gateway")}


def require_mac_timer():
    if sys.platform != "darwin":
        raise RuntimeError("macos_timer_only_use_collect_once")


def collector():
    spec = importlib.util.spec_from_file_location("demo_observability_collector", COLLECTOR_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(argv, payload=None, timeout=25):
    return subprocess.run(argv, input=payload, capture_output=True, text=True, timeout=timeout)


def atomic_local(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.parent.stat().st_uid != os.getuid() or path.parent.stat().st_mode & 0o022:
        raise RuntimeError("unsafe_local_directory")
    if path.is_symlink() or (path.exists() and path.stat().st_uid != os.getuid()):
        raise RuntimeError("unsafe_local_file")
    descriptor, temporary = tempfile.mkstemp(prefix=".telemetry-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def ssh_command():
    if KNOWN_HOSTS is None or not KNOWN_HOSTS.is_file() or KNOWN_HOSTS.is_symlink():
        raise RuntimeError("missing_pinned_host_keys")
    if not SSH_ALIAS or not HOST_KEY_ALIAS:
        raise RuntimeError("missing_ssh_target_configuration")
    argv = ["/usr/bin/ssh"]
    if SSH_CONFIG:
        argv.extend(["-F", SSH_CONFIG])
    return argv + ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "HostKeyAlias=" + HOST_KEY_ALIAS, "-o", "UserKnownHostsFile=" + str(KNOWN_HOSTS),
            "-o", "IdentitiesOnly=yes", "-o", "ConnectTimeout=8", "-o", "ConnectionAttempts=1",
            "-o", "ClearAllForwardings=yes", "-o", "ForwardAgent=no", SSH_ALIAS, REMOTE_RECEIVER]


def collect_once(apply):
    sample = collector().collect_client(**CLIENT_OPTIONS)
    if not apply:
        print(json.dumps({"applied": False, "sample": sample}, indent=2))
        return 0
    payload = json.dumps(sample, separators=(",", ":"), allow_nan=False)
    atomic_local(STATE / "client.json", (payload + "\n").encode())
    try:
        result = run(ssh_command(), payload=payload)
        acknowledged = result.returncode == 0 and json.loads(result.stdout) == {"stored": True, "source": "client"}
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        acknowledged = False
    receipt = {"schema_version": 1, "collected_at": sample["collected_at"], "uploaded": acknowledged,
               "code": "uploaded" if acknowledged else "upload_failed"}
    atomic_local(STATE / "upload-status.json", (json.dumps(receipt) + "\n").encode())
    print(json.dumps(receipt))
    return 0 if acknowledged else 1


def launch_definition():
    arguments = [str(Path(sys.executable).resolve()), str(Path(__file__).resolve()), "collect-once", "--apply"]
    if CONFIG_PATH:
        arguments.extend(["--config", str(CONFIG_PATH)])
    return {"Label": LABEL,
            "ProgramArguments": arguments,
            "StartInterval": INTERVAL_SECONDS, "RunAtLoad": True, "ProcessType": "Background",
            "StandardOutPath": "/dev/null", "StandardErrorPath": "/dev/null"}


def accepted_launch_arguments(allow_legacy=False):
    expected = launch_definition()["ProgramArguments"]
    choices = [expected]
    if allow_legacy and CONFIG_PATH:
        # Migration accepts only this interpreter + this script's original exact
        # invocation. Another config, script, arguments or job is never adopted.
        choices.append(expected[:4])
    return choices


def recognized_plist(allow_legacy=False):
    """Inspect only our exact user-owned plist; return its bytes for race checks."""
    if not PLIST.exists() and not PLIST.is_symlink():
        return None
    info = PLIST.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise RuntimeError("unsafe_launch_agent")
    data = PLIST.read_bytes()
    definition = plistlib.loads(data)
    if definition.get("Label") != LABEL or definition.get("ProgramArguments") not in accepted_launch_arguments(allow_legacy):
        raise RuntimeError("unrecognized_launch_agent")
    return data


def managed_launch_job(allow_legacy=False):
    """Verify the live job's executable/arguments even when its plist is missing.

    Output stays in memory, is limited to this one managed label and is never
    persisted as telemetry. Only explicit service absence counts as stopped.
    """
    target = "gui/" + str(os.getuid()) + "/" + LABEL
    result = run(["/bin/launchctl", "print", target], timeout=10)
    absent = 'Could not find service "' + LABEL + '" in domain for user gui: ' + str(os.getuid())
    if result.returncode == 113 and absent in result.stderr.splitlines():
        return False
    if result.returncode or len(result.stdout) > 65536:
        raise RuntimeError("launch_agent_state_unknown")
    program = re.search(r"^\s*program = (.+)$", result.stdout, re.MULTILINE)
    arguments = re.search(r"^\s*arguments = \{\n(.*?)^\s*\}\s*$", result.stdout, re.MULTILINE | re.DOTALL)
    expected = launch_definition()["ProgramArguments"]
    actual = [line.strip() for line in arguments.group(1).splitlines() if line.strip()] if arguments else None
    if not result.stdout.startswith(target + " = {") or not program or program.group(1).strip() != expected[0] or actual not in accepted_launch_arguments(allow_legacy):
        raise RuntimeError("unrecognized_live_launch_agent")
    return True


def setup(apply):
    require_mac_timer()
    definition = launch_definition()
    if not apply:
        print(json.dumps({"applied": False, "interval_seconds": INTERVAL_SECONDS, "ssh_alias": SSH_ALIAS,
                          "launch_agent": str(PLIST), "server_install_required": True,
                          "server_activation": "sudo systemctl enable --now kirocrew-demo-observability.timer",
                          "definition": definition}, indent=2))
        return 0
    # Verify ownership and exact invocation before changing an existing job.
    previous = recognized_plist(allow_legacy=True)
    loaded = managed_launch_job(allow_legacy=True)
    # Verify the installed receiver before creating a recurring job.
    result = collect_once(True)
    if result:
        raise RuntimeError("receiver_preflight_failed")
    if recognized_plist(allow_legacy=True) != previous:
        raise RuntimeError("launch_agent_changed")
    if loaded:
        run(["/bin/launchctl", "bootout", "gui/" + str(os.getuid()) + "/" + LABEL], timeout=10)
        if managed_launch_job(allow_legacy=True):
            raise RuntimeError("client_timer_stop_failed")
    atomic_local(PLIST, plistlib.dumps(definition))
    # The receiver rejects replayed whole-second timestamps. Keep RunAtLoad's
    # first sample distinct from the preflight that was just acknowledged.
    time.sleep(1.05)
    result = run(["/bin/launchctl", "bootstrap", "gui/" + str(os.getuid()), str(PLIST)], timeout=10)
    if result.returncode:
        raise RuntimeError("launch_agent_failed")
    print(json.dumps({"applied": True, "client_timer": LABEL, "interval_seconds": INTERVAL_SECONDS}))
    return 0


def stop(apply):
    require_mac_timer()
    if not apply:
        print(json.dumps({"applied": False, "client_timer": LABEL, "action": "unload_and_remove_launch_agent",
                          "server_stop": "sudo systemctl disable --now kirocrew-demo-observability.timer"}))
        return 0
    previous = recognized_plist()
    if managed_launch_job():
        # A LaunchAgent can remain loaded after its plist was removed. Address
        # the verified job by exact label rather than relying on that file.
        run(["/bin/launchctl", "bootout", "gui/" + str(os.getuid()) + "/" + LABEL], timeout=10)
    if managed_launch_job():
        raise RuntimeError("client_timer_stop_failed")
    if previous is not None:
        if recognized_plist() != previous:
            raise RuntimeError("launch_agent_changed")
        PLIST.unlink()
    print(json.dumps({"applied": True, "client_timer_stopped": True, "samples_retained": True}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["collect-once", "setup", "stop"])
    parser.add_argument("--apply", action="store_true", help="Upload once, activate, or stop the client timer.")
    parser.add_argument("--config", help="Deployment JSON; defaults to KIRO_DEMO_CONFIG when set.")
    args = parser.parse_args()
    if args.operation in {"setup", "stop"}:
        require_mac_timer()
    from demo_config import load_config
    config = load_config(args.config)
    # Read-only collection works with local defaults. Do not send samples or install
    # recurring uploads using an implicit target inherited from an old demo.
    if args.apply and args.operation in {"collect-once", "setup"} and not config.get("_config_path"):
        parser.error("--config or KIRO_DEMO_CONFIG is required before uploading or installing a timer")
    if config.get("_config_path") or args.operation != "stop":
        configure(config)
    return {"collect-once": collect_once, "setup": setup, "stop": stop}[args.operation](args.apply)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        # Fixed codes only; never echo host, path, subprocess error or input values.
        code = "macos_timer_only_use_collect_once" if str(error) == "macos_timer_only_use_collect_once" else "telemetry_operation_failed"
        print(json.dumps({"ok": False, "code": code}), file=sys.stderr)
        sys.exit(1)
