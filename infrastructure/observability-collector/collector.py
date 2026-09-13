#!/usr/bin/env python3
"""Bounded demo observability. No product analytics, credentials, or raw logs.

The Mac probe reads ps PID/parent/CPU/RSS/executable columns only. The server
probe reads numeric /proc counters and fixed systemd properties. Only the
versioned allowlist below can cross SSH or reach the read-only dashboard.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import grp
import json
import math
import os
from pathlib import Path
import platform
import re
import socket
import stat
import subprocess
import sys
import tempfile
import time

SCHEMA_VERSION = 1
COLLECTOR = "kirocrew-demo-custom"
DATA_DIR = Path("/var/lib/kirocrew-demo-observability")
SAMPLE_LIMIT = 240
EVENT_LIMIT = 200
MAX_PAYLOAD = 8192
MAC_APP_ROOT = "/Applications/KiroCrew Nightly.app/Contents/"
MAC_MAIN = MAC_APP_ROOT + "MacOS/KiroCrew Nightly"
METRICS = {
    "client": ("process_count", "cpu_percent", "rss_mib"),
    "server": ("cpu_percent", "memory_used_mib", "memory_total_mib", "memory_available_mib",
               "disk_used_gib", "disk_total_gib", "gateway_cpu_percent", "gateway_rss_mib",
               "mcp_cpu_percent", "mcp_rss_mib"),
}
CHECKS = {
    "client": ("client_running", "remote_gateway_reachable", "local_gateway_off"),
    "server": ("gateway_service_active", "mcp_service_active", "gateway_loopback_reachable",
               "mcp_loopback_reachable"),
}
ERROR_CODES = {"process_probe_failed", "host_probe_failed", "service_probe_failed", "port_probe_failed"}


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def command(argv, timeout=4):
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            timeout=timeout, env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
    if result.returncode or len(result.stdout) > 2 * 1024 * 1024:
        raise RuntimeError("probe_failed")
    return result.stdout


def envelope(source):
    return {"schema_version": SCHEMA_VERSION, "source": source, "collector": COLLECTOR,
            "collected_at": utc_now(), "status": "unknown",
            "metrics": {key: None for key in METRICS[source]},
            "checks": {key: None for key in CHECKS[source]}, "errors": []}


def finish(sample):
    sample["errors"] = sorted(set(sample["errors"]))
    values = list(sample["metrics"].values()) + list(sample["checks"].values())
    sample["status"] = "unknown" if all(x is None for x in values) else "partial" if any(x is None for x in values) else "ok"
    return validate_sample(sample, sample["source"])


def probe_port(port):
    """TCP reachability only: no HTTP request, token, or application interaction."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except (ConnectionRefusedError, TimeoutError, socket.timeout):
        return False
    except OSError:
        return None


def parse_mac_processes(output, app_root=MAC_APP_ROOT, executable=None):
    """Do not accept args/command columns; callers supply the executable-only comm column."""
    app_root = str(Path(app_root)) + "/"
    executable = executable or app_root + "MacOS/" + Path(app_root).parent.stem
    selected = []
    for line in output.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) != 5:
            continue
        pid, parent, cpu, rss, process_executable = parts
        if process_executable == executable or process_executable.startswith(app_root + "Frameworks/"):
            try:
                row = (int(pid), int(parent), float(cpu), int(rss))
            except ValueError:
                raise RuntimeError("probe_failed")
            if row[0] < 1 or row[1] < 0 or not math.isfinite(row[2]) or row[2] < 0 or row[3] < 0:
                raise RuntimeError("probe_failed")
            selected.append(row)
    # Neither process IDs, ancestry nor executable paths are persisted.
    return {"process_count": len(selected), "cpu_percent": round(sum(row[2] for row in selected), 2),
            "rss_mib": round(sum(row[3] for row in selected) / 1024, 2)}


def collect_linux_processes(executable, interval=0.1):
    """Measure only an explicitly configured executable; never inspect args or env."""
    if not executable or not Path(executable).is_absolute():
        raise ValueError("client_executable_required")
    selected = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if os.readlink(entry / "exe") == executable:
                selected.append((int(entry.name), process_ticks(int(entry.name)), time.monotonic()))
        except (FileNotFoundError, ProcessLookupError):
            continue  # A short-lived process may disappear during enumeration.
        except PermissionError:
            if entry.stat().st_uid == os.getuid():
                raise RuntimeError("probe_failed") from None
    time.sleep(interval)
    total_cpu, total_rss = 0.0, 0.0
    for pid, before, started in selected:
        after = process_ticks(pid)
        if after[2] != before[2] or after[0] < before[0]:
            raise RuntimeError("probe_failed")
        total_cpu += (after[0] - before[0]) / os.sysconf("SC_CLK_TCK") / (time.monotonic() - started) * 100
        total_rss += after[1]
    return {"process_count": len(selected), "cpu_percent": round(total_cpu, 2), "rss_mib": round(total_rss, 2)}


def validated_port(port):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("invalid_port")
    return port


def collect_client(*, app_root=MAC_APP_ROOT, executable=None, remote_gateway_port=5599,
                   local_gateway_port=5476, check_local_gateway=None):
    validated_port(remote_gateway_port)
    validated_port(local_gateway_port)
    if check_local_gateway is not None and type(check_local_gateway) is not bool:
        raise ValueError("invalid_local_gateway_check")
    sample = envelope("client")
    system = platform.system()
    try:
        if system == "Darwin":
            if not app_root:
                raise ValueError("client_app_path_required")
            sample["metrics"] = parse_mac_processes(
                command(["/bin/ps", "-axo", "pid=,ppid=,%cpu=,rss=,comm="]), app_root, executable)
        elif system == "Linux":
            sample["metrics"] = collect_linux_processes(executable)
        else:
            raise RuntimeError("unsupported_client_platform")
        sample["checks"]["client_running"] = sample["metrics"]["process_count"] > 0
    except (OSError, KeyError, IndexError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        sample["errors"].append("process_probe_failed")
    # This is a local tunnel listener check, not proof of a remote response.
    sample["checks"]["remote_gateway_reachable"] = probe_port(remote_gateway_port)
    should_check_local = system == "Darwin" if check_local_gateway is None else check_local_gateway
    if should_check_local:
        local_port = probe_port(local_gateway_port)
        sample["checks"]["local_gateway_off"] = None if local_port is None else not local_port
    if sample["checks"]["remote_gateway_reachable"] is None or (should_check_local and sample["checks"]["local_gateway_off"] is None):
        sample["errors"].append("port_probe_failed")
    return finish(sample)


def cpu_ticks():
    values = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
    if len(values) != 8:
        raise RuntimeError("probe_failed")
    return sum(values), values[3] + values[4]


def process_ticks(pid):
    data = Path("/proc") / str(pid)
    # The comm field can contain spaces and ')'; stat numeric fields follow its last ')'.
    fields = (data / "stat").read_text().rsplit(")", 1)[1].split()
    ticks = int(fields[11]) + int(fields[12])  # fields 14 and 15 in proc_pid_stat(5)
    rss_mib = int((data / "statm").read_text().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1048576
    start_ticks = int(fields[19])
    return ticks, rss_mib, start_ticks


def service_state(service):
    raw = command(["/usr/bin/systemctl", "show", service, "--property=ActiveState", "--property=MainPID"])
    properties = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
    if properties.get("ActiveState") not in {"active", "inactive", "failed", "activating", "deactivating", "reloading", "maintenance", "refreshing"}:
        raise RuntimeError("probe_failed")
    return properties["ActiveState"] == "active", int(properties["MainPID"])


def collect_server(interval=1.0, *, gateway_service="kirocrew-demo.service", mcp_service="kirocrew-mcp-demo.service",
                   gateway_port=5476, mcp_port=8001, disk_path="/"):
    for service in (gateway_service, mcp_service):
        if not isinstance(service, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@:-]*\.service", service):
            raise ValueError("invalid_service")
    validated_port(gateway_port)
    validated_port(mcp_port)
    if not Path(disk_path).is_absolute():
        raise ValueError("absolute_disk_path_required")
    sample = envelope("server")
    if platform.system() != "Linux":
        sample["errors"].extend(["host_probe_failed", "service_probe_failed"])
        return finish(sample)
    host_before = None
    processes = {}
    try:
        host_before = cpu_ticks()
        mem = {line.split(":", 1)[0]: int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith(("MemTotal:", "MemAvailable:"))}
        total, available = mem["MemTotal"] / 1024, mem["MemAvailable"] / 1024
        fs = os.statvfs(disk_path)
        sample["metrics"].update(memory_total_mib=round(total, 2), memory_available_mib=round(available, 2),
                                  memory_used_mib=round(total - available, 2),
                                  disk_total_gib=round(fs.f_blocks * fs.f_frsize / 1073741824, 3),
                                  disk_used_gib=round((fs.f_blocks - fs.f_bfree) * fs.f_frsize / 1073741824, 3))
    except (OSError, KeyError, IndexError, ValueError, RuntimeError):
        sample["errors"].append("host_probe_failed")
    for short, unit in (("gateway", gateway_service), ("mcp", mcp_service)):
        try:
            active, pid = service_state(unit)
            sample["checks"][short + "_service_active"] = active
            if pid > 0:
                processes[short] = (pid, process_ticks(pid), time.monotonic())
            elif not active:
                sample["metrics"].update({short + "_cpu_percent": 0.0, short + "_rss_mib": 0.0})
            else:
                raise RuntimeError("probe_failed")
        except (OSError, KeyError, IndexError, ValueError, RuntimeError, subprocess.TimeoutExpired):
            sample["errors"].append("service_probe_failed")
    # Fixed one-second measurement; no continuous process or request capture.
    time.sleep(interval)
    if host_before:
        try:
            total, idle = cpu_ticks()
            delta = total - host_before[0]
            if delta <= 0:
                raise RuntimeError("probe_failed")
            sample["metrics"]["cpu_percent"] = round(max(0, min(100, 100 * (1 - (idle - host_before[1]) / delta))), 2)
        except (OSError, IndexError, ValueError, RuntimeError):
            sample["errors"].append("host_probe_failed")
    for short, (pid, before, started) in processes.items():
        try:
            after = process_ticks(pid)
            if after[2] != before[2] or after[0] < before[0]:
                raise RuntimeError("probe_failed")
            sample["metrics"][short + "_cpu_percent"] = round((after[0] - before[0]) / os.sysconf("SC_CLK_TCK") / (time.monotonic() - started) * 100, 2)
            sample["metrics"][short + "_rss_mib"] = round(after[1], 2)
        except (OSError, IndexError, ValueError, RuntimeError):
            sample["errors"].append("service_probe_failed")
    for short, port in (("gateway", gateway_port), ("mcp", mcp_port)):
        sample["checks"][short + "_loopback_reachable"] = probe_port(port)
        if sample["checks"][short + "_loopback_reachable"] is None:
            sample["errors"].append("port_probe_failed")
    sample["collected_at"] = utc_now()
    return finish(sample)


def validate_sample(sample, expected_source, now=None):
    """Reject added fields and free text before it can enter the root-owned store."""
    if not isinstance(sample, dict) or set(sample) != {"schema_version", "source", "collector", "collected_at", "status", "metrics", "checks", "errors"}:
        raise ValueError("invalid_sample_fields")
    if type(sample["schema_version"]) is not int or sample["schema_version"] != SCHEMA_VERSION or sample["source"] != expected_source or expected_source not in METRICS or sample["collector"] != COLLECTOR:
        raise ValueError("invalid_sample_identity")
    timestamp = sample["collected_at"]
    if not isinstance(timestamp, str) or len(timestamp) != 20 or not timestamp.endswith("Z"):
        raise ValueError("invalid_timestamp")
    try:
        recorded = dt.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        raise ValueError("invalid_timestamp") from None
    if abs(((now or dt.datetime.now(dt.timezone.utc)) - recorded).total_seconds()) > 300:
        raise ValueError("sample_clock_skew")
    if not isinstance(sample["metrics"], dict) or set(sample["metrics"]) != set(METRICS[expected_source]):
        raise ValueError("invalid_metric_fields")
    for key, value in sample["metrics"].items():
        if value is None:
            continue
        maximum = 100 if expected_source == "server" and key == "cpu_percent" else 1000000
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
            raise ValueError("invalid_metric_value")
        if key == "process_count" and type(value) is not int:
            raise ValueError("invalid_process_count")
    if not isinstance(sample["checks"], dict) or set(sample["checks"]) != set(CHECKS[expected_source]) or any(value is not None and type(value) is not bool for value in sample["checks"].values()):
        raise ValueError("invalid_checks")
    errors = sample["errors"]
    if not isinstance(errors, list) or len(errors) > len(ERROR_CODES) or any(not isinstance(code, str) or code not in ERROR_CODES for code in errors) or errors != sorted(set(errors)):
        raise ValueError("invalid_error_codes")
    values = list(sample["metrics"].values()) + list(sample["checks"].values())
    expected_status = "unknown" if all(x is None for x in values) else "partial" if any(x is None for x in values) else "ok"
    if sample["status"] != expected_status:
        raise ValueError("invalid_status")
    return sample


def secure_directory(directory, owner_uid, reader_gid):
    directory.mkdir(mode=0o750, parents=False, exist_ok=True)
    info = directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != owner_uid or info.st_mode & 0o022:
        raise RuntimeError("unsafe_data_directory")
    os.chmod(directory, 0o750)
    os.chown(directory, owner_uid, reader_gid)


def atomic_write(path, contents, owner_uid, reader_gid):
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != owner_uid or info.st_mode & 0o022:
            raise RuntimeError("unsafe_data_file")
    descriptor, temporary = tempfile.mkstemp(prefix=".sample-", dir=str(path.parent))
    try:
        os.fchmod(descriptor, 0o640)
        os.fchown(descriptor, owner_uid, reader_gid)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_bounded_jsonl(path, limit):
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > MAX_PAYLOAD * (SAMPLE_LIMIT + EVENT_LIMIT):
        raise RuntimeError("unsafe_history_file")
    return [json.loads(line) for line in path.read_text().splitlines()[-limit:] if line]


def transition_events(previous, sample):
    common = {"schema_version": 1, "source": sample["source"], "at": sample["collected_at"]}
    events = []
    if previous is None:
        events.append({**common, "kind": "collected", "level": "info", "code": "first_sample"})
    elif previous.get("checks") != sample["checks"]:
        level = "warning" if any(value is not True for value in sample["checks"].values()) else "info"
        events.append({**common, "kind": "status_changed", "level": level, "code": "checks_changed"})
    if previous and previous.get("errors") and not sample["errors"]:
        events.append({**common, "kind": "status_changed", "level": "info", "code": "sample_recovered"})
    old_errors = set(previous.get("errors", [])) if previous else set()
    for code in sample["errors"]:
        if code not in old_errors:
            events.append({**common, "kind": "collector_error", "level": "warning", "code": code})
    return events


def store_sample(sample, directory=DATA_DIR, owner_uid=0, reader_gid=None):
    validate_sample(sample, sample["source"])
    reader_gid = grp.getgrnam("crew").gr_gid if reader_gid is None else reader_gid
    secure_directory(directory, owner_uid, reader_gid)
    lockpath = directory / ".collector.lock"
    descriptor = os.open(lockpath, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != owner_uid or info.st_mode & 0o077:
            raise RuntimeError("unsafe_lock_file")
        deadline = time.monotonic() + 2
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("collector_busy")
                time.sleep(0.05)
        history_path = directory / (sample["source"] + "-history.jsonl")
        history = read_bounded_jsonl(history_path, SAMPLE_LIMIT)
        previous = history[-1] if history else None
        if previous and sample["collected_at"] <= previous.get("collected_at", ""):
            raise ValueError("sample_not_newer")
        events = read_bounded_jsonl(directory / "events.jsonl", EVENT_LIMIT)
        events = (events + transition_events(previous, sample))[-EVENT_LIMIT:]
        serialized = lambda entries: "".join(json.dumps(entry, separators=(",", ":"), allow_nan=False) + "\n" for entry in entries)
        atomic_write(history_path, serialized((history + [sample])[-SAMPLE_LIMIT:]), owner_uid, reader_gid)
        atomic_write(directory / "events.jsonl", serialized(events), owner_uid, reader_gid)
        atomic_write(directory / (sample["source"] + ".json"), json.dumps(sample, indent=2, allow_nan=False) + "\n", owner_uid, reader_gid)
    finally:
        os.close(descriptor)


def read_client_input(stream):
    raw = stream.read(MAX_PAYLOAD + 1)
    if len(raw) > MAX_PAYLOAD:
        raise ValueError("sample_too_large")
    return validate_sample(json.loads(raw), "client")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["client", "server", "receive-client"])
    parser.add_argument("--store", action="store_true", help="Write a server sample to the root-owned store.")
    parser.add_argument("--app-path", default=os.environ.get("KIRO_DEMO_CLIENT_APP_PATH", "/Applications/KiroCrew Nightly.app"))
    parser.add_argument("--client-executable", default=os.environ.get("KIRO_DEMO_CLIENT_EXECUTABLE"))
    parser.add_argument("--tunnel-port", type=int, default=int(os.environ.get("KIRO_DEMO_TUNNEL_PORT", "5599")))
    parser.add_argument("--client-gateway-port", type=int, default=int(os.environ.get("KIRO_DEMO_CLIENT_GATEWAY_PORT", "5476")))
    parser.add_argument("--check-local-gateway", action="store_true", default=None,
                        help="Opt in to the local Gateway port check on a non-Mac client.")
    parser.add_argument("--data-dir", type=Path, default=Path(os.environ.get("KIRO_DEMO_COLLECTOR_DATA_DIR", str(DATA_DIR))))
    parser.add_argument("--reader-group", default=os.environ.get("KIRO_DEMO_COLLECTOR_READER_GROUP", "crew"))
    parser.add_argument("--gateway-service", default=os.environ.get("KIRO_DEMO_GATEWAY_SERVICE", "kirocrew-demo.service"))
    parser.add_argument("--mcp-service", default=os.environ.get("KIRO_DEMO_MCP_SERVICE", "kirocrew-mcp-demo.service"))
    parser.add_argument("--gateway-port", type=int, default=int(os.environ.get("KIRO_DEMO_GATEWAY_PORT", "5476")))
    parser.add_argument("--mcp-port", type=int, default=int(os.environ.get("KIRO_DEMO_MCP_PORT", "8001")))
    parser.add_argument("--disk-path", default=os.environ.get("KIRO_DEMO_DISK_PATH", "/"))
    args = parser.parse_args()
    if not args.data_dir.is_absolute() or not Path(args.app_path).is_absolute():
        raise ValueError("absolute_path_required")
    if args.operation == "receive-client":
        if os.geteuid() != 0:
            raise RuntimeError("root_required")
        store_sample(read_client_input(sys.stdin.buffer), args.data_dir, reader_gid=grp.getgrnam(args.reader_group).gr_gid)
        print(json.dumps({"stored": True, "source": "client"}))
        return
    sample = (collect_client(app_root=str(Path(args.app_path) / "Contents"), executable=args.client_executable,
                             remote_gateway_port=args.tunnel_port, local_gateway_port=args.client_gateway_port,
                             check_local_gateway=args.check_local_gateway) if args.operation == "client" else
              collect_server(gateway_service=args.gateway_service, mcp_service=args.mcp_service,
                             gateway_port=args.gateway_port, mcp_port=args.mcp_port, disk_path=args.disk_path))
    if args.store:
        if os.geteuid() != 0 or args.operation != "server":
            raise RuntimeError("root_server_required")
        store_sample(sample, args.data_dir, reader_gid=grp.getgrnam(args.reader_group).gr_gid)
    print(json.dumps(sample, separators=(",", ":"), allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # No subprocess stderr, filesystem paths, input payload or OS exception text.
        print(json.dumps({"ok": False, "code": "collector_failed"}), file=sys.stderr)
        sys.exit(1)
