"""Read-only collector view behind the KiroCrew App Kit authenticated proxy.

The Gateway owns this subprocess and supplies KIROCREW_PROXY_SECRET. There is
no alternate authentication path and no HTTP ingestion endpoint.
"""
from __future__ import annotations

import json
import math
import os
import stat
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from kiro_crew.apps.proxy_auth import verify_proxy_request

DATA_DIR = Path("/var/lib/kirocrew-demo-observability")
APP_PORT = 9102
MAX_FILE_BYTES = 128 * 1024
MAX_EVENTS = 200
STALE_AFTER_SECONDS = 180
COLLECTOR = "kirocrew-demo-custom"
ERRORS = frozenset({"process_probe_failed", "host_probe_failed", "service_probe_failed", "port_probe_failed"})
EVENT_CODES = ERRORS | {"first_sample", "checks_changed", "sample_recovered"}
METRICS = {
    "client": {"process_count": 4096, "cpu_percent": 100000, "rss_mib": 1048576},
    "server": {
        "cpu_percent": 100, "memory_used_mib": 1048576, "memory_total_mib": 1048576,
        "memory_available_mib": 1048576, "disk_used_gib": 1048576, "disk_total_gib": 1048576,
        "gateway_cpu_percent": 100000, "gateway_rss_mib": 1048576,
        "mcp_cpu_percent": 100000, "mcp_rss_mib": 1048576,
    },
}
CHECKS = {
    "client": ("client_running", "remote_gateway_reachable", "local_gateway_off"),
    "server": ("gateway_service_active", "mcp_service_active", "gateway_loopback_reachable", "mcp_loopback_reachable"),
}
SOURCE_LABELS = {
    "client": "macOS process and loopback probes, uploaded over SSH",
    "server": "EC2 host, systemd main-process and loopback probes",
}
EVENT_LABELS = {
    "first_sample": "First sample collected",
    "checks_changed": "Health checks changed",
    "sample_recovered": "Collection recovered",
    "process_probe_failed": "Process probe unavailable",
    "host_probe_failed": "Host probe unavailable",
    "service_probe_failed": "Service probe unavailable",
    "port_probe_failed": "Loopback probe unavailable",
}


def timestamp(value: Any) -> tuple[str, float] | None:
    if not isinstance(value, str) or not 20 <= len(value) <= 40:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
            return None
        return parsed.isoformat().replace("+00:00", "Z"), parsed.timestamp()
    except (ValueError, OverflowError):
        return None


def bounded_read(path: Path) -> bytes:
    # Filenames are fixed by this module; clients cannot supply filesystem paths.
    # No symlink following or devices/FIFOs, including in test fixtures.
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise ValueError("invalid data file")
        data = handle.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("oversized data file")
    return data


def clean_sample(raw: Any, source: str, now: float) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source": source, "collector": COLLECTOR, "collection_source": SOURCE_LABELS[source],
        "collected_at": None, "age_seconds": None, "freshness": "unavailable",
        "status": "unknown", "metrics": {key: None for key in METRICS[source]},
        "checks": {key: None for key in CHECKS[source]}, "errors": [],
    }
    if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int or raw["schema_version"] != 1:
        return result
    if raw.get("source") != source or raw.get("collector") != COLLECTOR:
        return result
    stamp = timestamp(raw.get("collected_at"))
    if stamp is None:
        return result
    age = now - stamp[1]
    result.update(collected_at=stamp[0], age_seconds=round(max(0, age), 1))
    result["freshness"] = "clock_skew" if age < -60 else "stale" if age > STALE_AFTER_SECONDS else "current"
    metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else {}
    for key, maximum in METRICS[source].items():
        value = metrics.get(key)
        if type(value) in (int, float) and 0 <= value <= maximum and math.isfinite(value):
            if key != "process_count" or type(value) is int:
                result["metrics"][key] = value
    checks = raw.get("checks") if isinstance(raw.get("checks"), dict) else {}
    result["checks"] = {key: value if type(value := checks.get(key)) is bool else None for key in CHECKS[source]}
    raw_errors = raw.get("errors")
    if isinstance(raw_errors, list):
        result["errors"] = sorted({item for item in raw_errors[:16] if isinstance(item, str) and item in ERRORS})
    # Recompute completeness rather than trusting a producer's optimistic label.
    values = [*result["metrics"].values(), *result["checks"].values()]
    result["status"] = "unknown" if all(value is None for value in values) else "partial" if any(value is None for value in values) or result["errors"] else "ok"
    return result


def clean_events(data: bytes) -> list[dict[str, Any]]:
    result = []
    for line in data.splitlines()[-MAX_EVENTS:]:
        try:
            raw = json.loads(line)
        except (ValueError, UnicodeError, RecursionError):
            continue
        if not isinstance(raw, dict) or type(raw.get("schema_version")) is not int or raw["schema_version"] != 1:
            continue
        source, code, kind, level = (raw.get(key) for key in ("source", "code", "kind", "level"))
        if not all(isinstance(value, str) for value in (source, code, kind, level)):
            continue
        stamp = timestamp(raw.get("at"))
        if source not in METRICS or code not in EVENT_CODES or stamp is None:
            continue
        if kind not in {"collected", "status_changed", "collector_error"} or level not in {"info", "warning", "error"}:
            continue
        result.append({"source": source, "at": stamp[0], "kind": kind, "level": level, "code": code, "message": EVENT_LABELS[code]})
    return sorted(result, key=lambda event: event["at"], reverse=True)[:MAX_EVENTS]


def snapshot(data_dir: Path = DATA_DIR, now: float | None = None) -> dict[str, Any]:
    clock = time.time() if now is None else now
    sources = {}
    for source in METRICS:
        try:
            raw = json.loads(bounded_read(data_dir / f"{source}.json"))
        except (OSError, ValueError, UnicodeError, RecursionError):
            raw = None
        sources[source] = clean_sample(raw, source, clock)
    try:
        events = clean_events(bounded_read(data_dir / "events.jsonl"))
        events_available = True
    except (OSError, ValueError, UnicodeError):
        events, events_available = [], False
    return {
        "schema_version": 1, "generated_at": datetime.fromtimestamp(clock, timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "custom_demo_collectors", "stale_after_seconds": STALE_AFTER_SECONDS,
        "sources": sources, "events": events, "events_available": events_available,
        "events_limit": MAX_EVENTS,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DemoObservability"
    sys_version = ""

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *_args: Any) -> None:
        # Never log request targets, headers or payloads.
        pass

    def send_json(self, code: int, value: Any) -> None:
        payload = json.dumps(value, separators=(",", ":"), allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def authorized(self) -> bool:
        # Every data request uses the frozen Nightly SDK's HMAC verification.
        # Its timestamp allows a 60-second skew window; signatures are not single-use.
        if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Length", "0") != "0":
            self.send_json(400, {"error": "request body not supported"})
            return False
        if not verify_proxy_request(self.headers.get("X-KiroCrew-Proxy", ""), method=self.command, target=self.path, body=b""):
            self.send_json(401, {"error": "unauthorized"})
            return False
        return True

    def do_GET(self) -> None:
        if self.path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        if not self.authorized():
            return
        if self.path == "/api/snapshot":
            self.send_json(200, snapshot(self.server.data_dir))
        else:
            self.send_json(404, {"error": "not found"})

    def reject_mutation(self) -> None:
        if self.authorized():
            self.send_json(405, {"error": "read only"})

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = reject_mutation


class Server(ThreadingHTTPServer):
    daemon_threads = True
    data_dir = DATA_DIR


def main() -> None:
    if not os.environ.get("KIROCREW_PROXY_SECRET"):
        raise SystemExit("Gateway proxy authentication is required")
    port = int(os.environ.get("PORT", str(APP_PORT)))
    if port != APP_PORT:
        raise SystemExit("Unexpected app port")
    Server(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
