#!/usr/bin/env python3
"""Verify the managed Gateway's cgroup using only this tool's disposable child.

No service is restarted, no existing process is moved, and the policy is never
written. The child alone joins the observed service cgroup, drops to crew, tests
PTY creation and policy write access, reports bounded results, and exits.
Native Kiro CLI descendants are inspected without command lines or environment.
"""
from __future__ import annotations

import argparse
import base64
import ctypes
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import select
import shlex
import signal
import stat
import subprocess
import sys
import time

POLICY = "/etc/kirocrew-demo/security-policy.json"
MANIFEST = "/etc/kirocrew-demo/enterprise-policy-install.json"


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_directory(path):
    require(isinstance(path, str) and path.startswith("/") and
            not {".", ".."}.intersection(path.split("/")), "invalid_absolute_path")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in PurePosixPath(path).parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            info = os.fstat(child)
            if info.st_uid != 0 or info.st_mode & 0o022:
                os.close(child)
                raise ValueError("unprotected_ancestor")
            os.close(fd)
            fd = child
        return fd
    except Exception:
        os.close(fd)
        raise


def protected_read(path, limit=4_000_000):
    item = PurePosixPath(path)
    parent = safe_directory(str(item.parent))
    try:
        fd = os.open(item.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == 0 and
                    not info.st_mode & 0o022 and info.st_size <= limit, "unprotected_file")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(limit + 1)
            require(len(data) <= limit, "file_size_limit")
            return data, {"sha256": sha(data), "uid": info.st_uid, "gid": info.st_gid,
                          "mode": oct(stat.S_IMODE(info.st_mode)), "bytes": len(data)}
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def proc_status(pid):
    result = {}
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        key, _, value = line.partition(":")
        if key in {"Name", "Pid", "PPid", "Uid", "Gid", "NoNewPrivs", "Seccomp"}:
            result[key] = value.strip()
    return result


def unified_cgroup(pid):
    rows = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
    matches = [row[3:] for row in rows if row.startswith("0::")]
    require(len(matches) == 1 and matches[0].startswith("/") and
            not {".", ".."}.intersection(matches[0].split("/")), "unified_cgroup_required")
    return matches[0]


def start_ticks(pid):
    return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19]


def service_state(service):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.service", service), "invalid_service")
    result = subprocess.run(["systemctl", "show", service,
                             "--property=MainPID,ActiveState,User,ControlGroup,DevicePolicy,DeviceAllow"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"})
    require(result.returncode == 0 and len(result.stdout) < 32000, "service_inspection_failed")
    rows = [line.split("=", 1) for line in result.stdout.decode().splitlines() if "=" in line]
    props = dict(rows)
    props["DeviceAllow"] = [value for key, value in rows if key == "DeviceAllow"]
    require(props.get("ActiveState") == "active" and props.get("User") == "crew", "active_crew_gateway_required")
    pid = int(props.get("MainPID", 0))
    require(pid > 0 and props.get("ControlGroup") == unified_cgroup(pid), "gateway_cgroup_mismatch")
    return {"pid": pid, "start_ticks": start_ticks(pid), "cgroup": props["ControlGroup"],
            "device_policy": props.get("DevicePolicy"), "device_allow": props["DeviceAllow"]}


def own_child_check(gateway, crew):
    """Write only the newly forked child's own PID to the observed cgroup."""
    cgroup_path = "/sys/fs/cgroup" + gateway["cgroup"]
    cgroup_fd = safe_directory(cgroup_path)
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(read_fd)
        try:
            signal.alarm(4)
            require(start_ticks(gateway["pid"]) == gateway["start_ticks"] and
                    unified_cgroup(gateway["pid"]) == gateway["cgroup"], "gateway_changed_before_child_join")
            own_pid = os.getpid()
            membership = os.open("cgroup.procs", os.O_WRONLY | os.O_NOFOLLOW, dir_fd=cgroup_fd)
            try:
                os.write(membership, (str(own_pid) + "\n").encode())
            finally:
                os.close(membership)
            os.close(cgroup_fd)
            os.setgroups([])
            os.setgid(crew.pw_gid)
            os.setuid(crew.pw_uid)
            require(os.getuid() == os.geteuid() == crew.pw_uid and os.getgid() == os.getegid() == crew.pw_gid
                    and not os.getgroups(), "child_identity_drop_failed")
            require(ctypes.CDLL(None, use_errno=True).prctl(38, 1, 0, 0, 0) == 0, "child_no_new_privs_failed")
            require(unified_cgroup(own_pid) == gateway["cgroup"], "child_cgroup_membership_failed")
            result = {"pid": own_pid, "uid": os.getuid(), "gid": os.getgid(), "supplementary_groups": os.getgroups(),
                      "cgroup": unified_cgroup(own_pid), "no_new_privs": proc_status(own_pid).get("NoNewPrivs"),
                      "policy_write_access": os.access(POLICY, os.W_OK), "policy_write_attempted": False}
            try:
                master, slave = os.openpty()
            except OSError as exc:
                result.update(pty_created=False, pty_errno=exc.errno, pty_expected_eperm=exc.errno == errno.EPERM)
            else:
                os.close(master); os.close(slave)
                result.update(pty_created=True, pty_errno=None, pty_expected_eperm=False)
        except Exception as exc:
            result = {"error": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}
        try:
            os.write(write_fd, json.dumps(result, sort_keys=True).encode())
        finally:
            os.close(write_fd)
            os._exit(0)
    os.close(write_fd)
    os.close(cgroup_fd)
    data = bytearray()
    deadline = time.monotonic() + 6
    reaped = False
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([read_fd], [], [], min(0.25, max(0, deadline - time.monotonic())))
            if ready:
                chunk = os.read(read_fd, 16001 - len(data))
                if not chunk:
                    break
                data.extend(chunk)
                require(len(data) <= 16000, "child_report_limit")
        child_pid, status = os.waitpid(pid, os.WNOHANG)
        if child_pid:
            reaped = True
            require(os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, "probe_child_failed")
        else:
            # The child has its own alarm. A short wait after pipe EOF covers
            # the report-to-exit scheduling interval without moving any peer.
            while time.monotonic() < deadline:
                child_pid, status = os.waitpid(pid, os.WNOHANG)
                if child_pid:
                    reaped = True
                    require(os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, "probe_child_failed")
                    break
                time.sleep(0.02)
        require(reaped, "probe_child_timeout")
        result = json.loads(data)
        require(isinstance(result, dict) and "error" not in result, "probe_child_check_failed")
        result["exited_and_reaped"] = True
        return result
    finally:
        os.close(read_fd)
        if not reaped:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)


def native_descendants(gateway):
    statuses = {}
    for path in Path("/proc").iterdir():
        if path.name.isdigit():
            try:
                statuses[int(path.name)] = proc_status(int(path.name))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass
    descendants = {gateway["pid"]}
    for _ in range(30):
        new = {pid for pid, row in statuses.items() if int(row.get("PPid", 0)) in descendants}
        if new <= descendants:
            break
        descendants |= new
    gateway_ns = os.readlink(f"/proc/{gateway['pid']}/ns/mnt")
    found = []
    for pid in sorted(descendants - {gateway["pid"]}):
        try:
            executable = Path(os.readlink(f"/proc/{pid}/exe")).name
            if executable not in {"kiro-cli", "kiro-cli-chat", "kiro-cli-term"}:
                continue
            row = proc_status(pid)
            mount_ns = os.readlink(f"/proc/{pid}/ns/mnt")
            found.append({"pid": pid, "executable_basename": executable, "uid": row.get("Uid"),
                          "no_new_privs": row.get("NoNewPrivs"), "seccomp": row.get("Seccomp"),
                          "mount_namespace": mount_ns, "mount_namespace_differs_from_gateway": mount_ns != gateway_ns,
                          "cgroup": unified_cgroup(pid)})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return {"gateway_mount_namespace": gateway_ns, "processes": found,
            "status": "observed" if found else "pending_no_native_cli_descendants",
            "limits": "A point-in-time process observation; it does not establish a tool outcome or complete sandbox coverage."}


def remote_verify(request):
    require(sys.platform == "linux" and os.geteuid() == 0, "linux_root_required")
    install, _ = protected_read(MANIFEST, 128000)
    plan = json.loads(install)["plan"]
    require(plan["binding"]["deployment"] == request["deployment"] and
            plan["binding"]["service"] == request["service"], "deployment_mismatch")
    files = {}
    for path, expected in plan["files"].items():
        _, info = protected_read(path)
        require(info["sha256"] == expected["sha256"] and info["mode"] == expected["mode"], "managed_file_changed")
        files[path] = info
    sources = {}
    for name, expected in plan["binding"]["sources"].items():
        _, info = protected_read(plan["binding"]["source_root"] + "/" + name)
        require(info == expected, "source_changed")
        sources[name] = info["sha256"]
    crew = pwd.getpwnam("crew")
    gateway = service_state(request["service"])
    require(not request.get("expected_gateway_pid") or gateway["pid"] == request["expected_gateway_pid"], "gateway_pid_changed")
    child = own_child_check(gateway, crew)
    require(service_state(request["service"]) == gateway, "gateway_changed_during_check")
    native = native_descendants(gateway)
    return {"schema_version": 1, "kind": "managed_host_runtime_check", "captured_at": datetime.now(timezone.utc).isoformat(),
            "deployment": request["deployment"], "service": request["service"], "gateway": gateway,
            "managed_files": files, "source_sha256": sources, "own_disposable_child": child,
            "gateway_cgroup_pty_denial_verified": child["pty_expected_eperm"],
            "crew_policy_write_access_denied": not child["policy_write_access"],
            "native_cli_observation": native, "no_existing_process_moved": True, "no_service_restart": True,
            "policy_write_attempted": False, "native_tool_enforcement_verified": False}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--remote":
        try:
            report = remote_verify(json.loads(base64.b64decode(sys.argv[2], validate=True)))
        except Exception as exc:
            report = {"kind": "managed_host_runtime_check", "error": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}
        print(json.dumps(report, indent=2, sort_keys=True))
        return int("error" in report)
    from demo_config import load_config, ssh_options
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--service", default="kirocrew-demo.service")
    parser.add_argument("--expected-gateway-pid", type=int)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists() and not args.output.is_symlink(), "output_exists")
    config = load_config(args.config, require_target=True)
    request = {"service": args.service, "expected_gateway_pid": args.expected_gateway_pid,
               "deployment": {key: config["aws"][key] for key in ("region", "account_id", "stack_name", "instance_id")}}
    source = Path(__file__).read_bytes()
    command = shlex.join(["sudo", "-n", "/usr/bin/python3", "-", "--remote",
                          base64.b64encode(json.dumps(request).encode()).decode()])
    result = subprocess.run(["ssh", *ssh_options(config), "-o", "ConnectTimeout=10", config["ssh"]["admin_alias"], command],
                            input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
    require(len(result.stdout) <= 128000, "remote_report_limit")
    report = json.loads(result.stdout)
    report["verifier_sha256"] = sha(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True); stream.write("\n")
    print(json.dumps({"output": str(args.output), "error": report.get("error"),
                      "gateway_cgroup_pty_denial_verified": report.get("gateway_cgroup_pty_denial_verified"),
                      "crew_policy_write_access_denied": report.get("crew_policy_write_access_denied"),
                      "native_cli_status": report.get("native_cli_observation", {}).get("status")}, indent=2))
    return int(result.returncode != 0 or "error" in report)


if __name__ == "__main__":
    raise SystemExit(main())
