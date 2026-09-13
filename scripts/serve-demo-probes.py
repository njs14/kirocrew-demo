#!/usr/bin/env python3
"""Loopback-only operator screen for two fixed, bounded demo commands.

This is a recording aid, not KiroCrew's native interface. Starting this server
does not run either command. The operator must press a same-origin UI button.
Only schema-checked probe receipts / synthetic step rows are retained or served.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import selectors
import shlex
import signal
import subprocess
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from demo_config import load_config, ssh_options

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "recordings/20260913/probe-presenter"
EVIDENCE = ROOT / "evidence/demo-clips/20260913/probe-presenter"
HOST = "127.0.0.1:5607"
ORIGIN = "http://" + HOST
PROBE_URL = "http://127.0.0.1:8001/mcp"
EXPECTED_SHA = "34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160"
# Commands are bound once from an explicit local config before the HTTP server starts.
# Tests can inject bounded command fixtures; HTTP clients can choose only a fixed mode.
COMMANDS = {"direct": [], "synthetic": []}


def configure_runtime(config):
    global ASSETS, EVIDENCE, HOST, ORIGIN, EXPECTED_SHA, COMMANDS, PROBE_URL
    probe = config["probe"]
    ASSETS = Path(probe["assets_dir"])
    EVIDENCE = Path(probe["evidence_dir"])
    HOST = "127.0.0.1:" + str(probe["port"])
    ORIGIN = "http://" + HOST
    EXPECTED_SHA = probe["expected_allowed_sha256"]
    remote_root = probe["remote_root"]
    remote_args = ["sudo", "-u", "mcp-demo", "env", "DEMO_MCP_TOKEN_FILE=/etc/kirocrew-demo/mcp-token",
                   remote_root + "/mcp-venv/bin/python", remote_root + "/mcp-enforcement/probe.py",
                   "--expected-allowed-sha256", EXPECTED_SHA]
    COMMANDS = {
        "direct": ["/usr/bin/ssh", "-T", *ssh_options(config), "-o", "ClearAllForwardings=yes",
                   config["ssh"]["admin_alias"], shlex.join(remote_args)],
        "synthetic": ["/bin/bash", str(ROOT / "demo.sh")],
    }


TIMEOUT = 90
OUTPUT_LIMIT = 128 * 1024
CHECK_NAMES = ["authentication_required", "catalog", "read_allowed", "mcp_denied", "iam_denied"]
TOOLS = ["crew_denied", "iam_denied", "mcp_denied", "read_allowed"]
STEP_NAMES = ["allow", "ask-pending", "ask-resolved", "deny", "protected-path", "command-gate",
              "policy-profile", "redaction", "sel-integrity", "sel-tamper-detection"]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def safe_text(value, pattern=r"[A-Za-z0-9_.:/ +()\[\]@,=<>-]{0,200}"):
    if not isinstance(value, str) or re.fullmatch(pattern, value) is None:
        raise ValueError("invalid_receipt_text")
    return value


def boolean(value):
    if type(value) is not bool:
        raise ValueError("invalid_receipt_boolean")
    return value


def integer(value, maximum=100000):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("invalid_receipt_integer")
    return value


def parse_direct(raw):
    """Accept only the known remote receipt schema; never export arbitrary stdout."""
    original = json.loads(raw)
    if not isinstance(original, dict) or original.get("kind") != "direct_mcp_service_probe":
        raise ValueError("invalid_receipt_kind")
    if original.get("native_crew_backend_verified") is not False:
        raise ValueError("invalid_native_boundary")
    receipt = {"kind": "direct_mcp_service_probe", "native_crew_backend_verified": False,
               "native_backend_verified": False, "passed": False}
    if "error_type" in original:
        receipt["error_type"] = safe_text(original["error_type"], r"[A-Za-z][A-Za-z0-9_]{0,79}")
        return receipt
    receipt["time"] = safe_text(original["time"], r"[0-9T:.+Z-]{1,40}")
    receipt["trace_prefix"] = safe_text(original["trace_prefix"], r"probe-[a-f0-9]{32}")
    receipt["expected_allowed_sha256"] = safe_text(original["expected_allowed_sha256"], r"[a-f0-9]{64}")
    receipt["server_file_sha256"] = safe_text(original["server_file_sha256"], r"[a-f0-9]{64}")
    receipt["schema"] = 1
    receipt["url"] = PROBE_URL
    if original.get("schema") != 1 or original.get("url") != receipt["url"]:
        raise ValueError("invalid_receipt_schema")
    deps = original.get("dependencies", {})
    receipt["dependencies"] = {key: safe_text(deps[key], r"[0-9A-Za-z.+-]{1,40}")
                               for key in ("boto3", "httpx", "mcp")}
    checks = original.get("checks")
    if not isinstance(checks, list) or [c.get("name") for c in checks] != CHECK_NAMES:
        raise ValueError("invalid_receipt_checks")
    receipt["checks"] = []
    for check in checks:
        name = check["name"]
        row = {"name": name, "passed": boolean(check["passed"])}
        if name == "authentication_required":
            row["http_status"] = integer(check["http_status"], 599)
            row["passed"] = row["passed"] and row["http_status"] == 401
        elif name == "catalog":
            if check.get("tools") != TOOLS:
                raise ValueError("invalid_catalog")
            row["tools"] = TOOLS
        else:
            payload = check["result"]
            if not isinstance(payload, dict):
                raise ValueError("invalid_result")
            result = {"tool": name, "ok": boolean(payload["ok"]),
                      "layer": safe_text(payload["layer"], r"aws|mcp"),
                      "principal": safe_text(payload["principal"], r"kirocrew-demo-client"),
                      "trace_id": safe_text(payload["trace_id"], r"probe-[a-f0-9]{32}-(read_allowed|mcp_denied|iam_denied)"),
                      "invocation_id": safe_text(payload["invocation_id"], r"[a-f0-9-]{36}")}
            expected_layer = "mcp" if name == "mcp_denied" else "aws"
            valid = (payload.get("tool") == name and result["layer"] == expected_layer
                     and result["trace_id"] == receipt["trace_prefix"] + "-" + name
                     and result["ok"] is (name == "read_allowed"))
            if name in ("read_allowed", "iam_denied"):
                result["aws_request_id"] = safe_text(payload["aws_request_id"], r"[A-Za-z0-9+/=_-]{1,128}")
            if name == "read_allowed":
                result["object_sha256"] = safe_text(payload["object_sha256"], r"[a-f0-9]{64}")
                result["object_bytes"] = integer(payload["object_bytes"], 4096)
                valid = valid and result["object_sha256"] == EXPECTED_SHA and payload.get("error_code") is None
            else:
                code = "tool_grant_denied" if name == "mcp_denied" else "AccessDenied"
                result["error_code"] = safe_text(payload["error_code"], r"tool_grant_denied|AccessDenied")
                valid = valid and result["error_code"] == code
            if name == "iam_denied":
                result["http_status"] = integer(payload["http_status"], 599)
                valid = valid and result["http_status"] == 403
            row["result"] = result
            row["passed"] = row["passed"] and valid
        receipt["checks"].append(row)
    receipt["passed"] = (boolean(original["passed"]) and receipt["expected_allowed_sha256"] == EXPECTED_SHA
                         and all(c["passed"] for c in receipt["checks"]))
    return receipt


def synthetic_step(original):
    name = original.get("step")
    if name not in STEP_NAMES:
        raise ValueError("invalid_synthetic_step")
    row = {"step": name}
    for key in ("handler_executed", "approved", "bytes_unchanged", "shell_executed", "synthetic_input", "original_restored"):
        if key in original:
            row[key] = boolean(original[key])
    if "crew_action" in original:
        row["crew_action"] = safe_text(original["crew_action"], r"auto_approve|allow|deny")
    for key in ("total", "valid"):
        if key in original:
            row[key] = integer(original[key])
    if "approval_mode" in original:
        row["approval_mode"] = safe_text(original["approval_mode"], r"scripted rehearsal")
    if name == "ask-pending":
        row["approval_ui"] = "synthetic harness"
    if name == "policy-profile":
        row["decisions"] = {}
        for tool in ("ReadDemo", "WriteDemo", "DenyDemo"):
            decision = original["decisions"][tool]
            row["decisions"][tool] = {"permitted": boolean(decision["permitted"]),
                                       "limiting_layer": safe_text(decision["limiting_layer"])}
        row["signature_state"] = safe_text(original["signature_state"])
    if name == "redaction":
        # Only the known redacted output is accepted; no arbitrary input enters the UI.
        row["output"] = safe_text(original["output"], r"\[REDACTED: credential\]")
    if name == "sel-integrity":
        row["correlated_request"] = safe_text(original["correlated_request"], r"demo-deny")
        row["event_source"] = "harness records the actual gate verdict"
    return row


def parse_synthetic(raw):
    text = raw.decode("utf-8", errors="strict")
    steps = [synthetic_step(json.loads(line)) for line in text.splitlines() if line.startswith('{"step":')]
    if [row["step"] for row in steps] != STEP_NAMES:
        raise ValueError("incomplete_synthetic_steps")
    baseline_line = next(line for line in text.splitlines() if line.startswith("Baseline: "))
    baseline = json.loads(baseline_line.removeprefix("Baseline: "))
    return {"kind": "local_synthetic_control_rehearsal", "native_backend_verified": False,
            "backend_session_executed": False, "network_calls": 0, "mcp_gateway_executed": False,
            "approval_mode": "scripted rehearsal", "steps": steps,
            "baseline": {"installed_version": safe_text(baseline["installed_version"]),
                         "snapshot_digest": safe_text(baseline["snapshot_digest"], r"[a-f0-9]{64}")},
            "passed": any(line.startswith("PASS. Evidence: ") for line in text.splitlines())}


def bounded_command(mode, progress):
    """No shell, arguments, environment values or filenames are supplied by HTTP."""
    started = time.monotonic()
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    environment = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C.UTF-8"}
    if mode == "synthetic":
        # Two operator-supplied local paths only; HTTP cannot set environment.
        for key in ("KIRO_DEMO_PYTHON", "KIRO_DEMO_BASELINE"):
            if os.environ.get(key):
                environment[key] = os.environ[key]
    with subprocess.Popen(COMMANDS[mode], cwd=ROOT, shell=False, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                          start_new_session=True) as proc:
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
        selector.register(proc.stderr, selectors.EVENT_READ, "stderr")
        termination = None
        try:
            while selector.get_map():
                if time.monotonic() - started > TIMEOUT:
                    termination = "timeout"
                    break
                for key, _ in selector.select(timeout=0.2):
                    chunk = os.read(key.fileobj.fileno(), 4096)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    captured[key.data].extend(chunk)
                    if sum(len(data) for data in captured.values()) > OUTPUT_LIMIT:
                        termination = "output_limit"
                        break
                if termination:
                    break
                progress(sum(len(data) for data in captured.values()))
            if termination:
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
        finally:
            selector.close()
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
    return {"stdout": bytes(captured["stdout"]), "stderr": bytes(captured["stderr"]),
            "exit_code": proc.returncode, "termination": termination}


class OperatorState:
    def __init__(self, evidence=None, runner=bounded_command):
        self.lock = threading.Lock()
        self.nonce = secrets.token_urlsafe(32)
        self.evidence = Path(evidence) if evidence is not None else EVIDENCE
        self.runner = runner
        self.active = None
        self.records = {mode: self.empty(mode) for mode in COMMANDS}
        self.artifacts = {}

    @staticmethod
    def empty(mode):
        return {"mode": mode, "status": "idle", "native_backend_verified": False,
                "started_at": None, "finished_at": None, "output_bytes": 0, "receipt": None}

    def snapshot(self):
        with self.lock:
            return {"active": self.active, "server_time": utc_now(), "native_backend_verified": False,
                    "runs": copy.deepcopy(self.records)}

    def start(self, mode):
        with self.lock:
            if self.active is not None:
                return False
            self.active = mode
            self.records[mode] = {**self.empty(mode), "status": "running", "started_at": utc_now()}
        threading.Thread(target=self.run, args=(mode,), daemon=True).start()
        return True

    def run(self, mode):
        def progress(count):
            with self.lock:
                self.records[mode]["output_bytes"] = count
        result = None
        try:
            result = self.runner(mode, progress)
            if result["termination"]:
                raise ValueError(result["termination"])
            receipt = (parse_direct if mode == "direct" else parse_synthetic)(result["stdout"])
            passed = result["exit_code"] == 0 and receipt["passed"]
            finished = utc_now()
            with self.lock:
                started = self.records[mode]["started_at"]
            artifact = {"schema": 1, "kind": "demo_probe_presenter_command_result", "mode": mode,
                        "native_backend_verified": False, "started_at": started, "finished_at": finished,
                        "command_argv": COMMANDS[mode], "exit_code": result["exit_code"],
                        "stdout_bytes": len(result["stdout"]), "stderr_bytes": len(result["stderr"]),
                        "stdout_sha256": hashlib.sha256(result["stdout"]).hexdigest(),
                        "stderr_sha256": hashlib.sha256(result["stderr"]).hexdigest(),
                        "raw_output_retained": False, "sanitization": "strict field and value allowlist",
                        "passed": passed, "receipt": receipt}
            self.evidence.mkdir(parents=True, exist_ok=True)
            name = mode + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4) + ".json"
            data = (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode()
            path = self.evidence / name
            with path.open("xb") as stream:
                stream.write(data)
            with self.lock:
                self.artifacts[name] = data
                self.records[mode].update(status="passed" if passed else "failed", finished_at=finished,
                                          receipt=receipt, exit_code=result["exit_code"],
                                          artifact_url="/artifacts/" + name,
                                          artifact_sha256=hashlib.sha256(data).hexdigest())
        except Exception as exc:
            # Exception strings and stderr may contain credentials/paths. Do not expose them.
            error = str(exc) if isinstance(exc, ValueError) and str(exc) in {"timeout", "output_limit"} else type(exc).__name__
            finished = utc_now()
            with self.lock:
                started = self.records[mode]["started_at"]
            failed_artifact = {"schema": 1, "kind": "demo_probe_presenter_command_result", "mode": mode,
                               "native_backend_verified": False, "started_at": started, "finished_at": finished,
                               "command_argv": COMMANDS[mode], "passed": False, "error_type": error,
                               "raw_output_retained": False, "receipt": None}
            if result is not None:
                failed_artifact.update(exit_code=result["exit_code"],
                                       stdout_bytes=len(result["stdout"]), stderr_bytes=len(result["stderr"]),
                                       stdout_sha256=hashlib.sha256(result["stdout"]).hexdigest(),
                                       stderr_sha256=hashlib.sha256(result["stderr"]).hexdigest())
            data = (json.dumps(failed_artifact, indent=2, sort_keys=True) + "\n").encode()
            name = mode + "-failed-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4) + ".json"
            artifact_saved = False
            try:
                self.evidence.mkdir(parents=True, exist_ok=True)
                with (self.evidence / name).open("xb") as stream:
                    stream.write(data)
                artifact_saved = True
            except OSError:
                pass
            with self.lock:
                self.records[mode].update(status="failed", finished_at=finished, error_type=error)
                if artifact_saved:
                    self.artifacts[name] = data
                    self.records[mode].update(artifact_url="/artifacts/" + name,
                                              artifact_sha256=hashlib.sha256(data).hexdigest())
        finally:
            with self.lock:
                self.active = None


def handler_for(state):
    class Handler(BaseHTTPRequestHandler):
        server_version = "DemoProbePresenter/1"

        def log_message(self, *_args):
            pass

        def send_bytes(self, status, body, content_type="application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, status, data):
            self.send_bytes(status, json.dumps(data).encode())

        def allowed(self, post=False):
            if self.client_address[0] != "127.0.0.1" or self.headers.get_all("Host") != [HOST]:
                self.send_json(403, {"error": "loopback_host_required"})
                return False
            origins = self.headers.get_all("Origin") or []
            if (origins and origins != [ORIGIN]) or (post and origins != [ORIGIN]):
                self.send_json(403, {"error": "same_origin_required"})
                return False
            if post and (self.headers.get("Sec-Fetch-Site") not in (None, "same-origin")
                         or not hmac.compare_digest(self.headers.get("X-Demo-Nonce", ""), state.nonce)):
                self.send_json(403, {"error": "operator_nonce_required"})
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            if self.path == "/api/state":
                self.send_json(200, state.snapshot())
                return
            if self.path.startswith("/artifacts/"):
                name = self.path.removeprefix("/artifacts/")
                with state.lock:
                    data = state.artifacts.get(name)
                self.send_bytes(200, data) if data is not None else self.send_json(404, {"error": "not_found"})
                return
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/styles.css": ("styles.css", "text/css; charset=utf-8")}
            if self.path not in assets:
                self.send_json(404, {"error": "not_found"})
                return
            name, kind = assets[self.path]
            data = (ASSETS / name).read_bytes()
            if name == "index.html":
                data = data.replace(b"__DEMO_NONCE__", state.nonce.encode())
            self.send_bytes(200, data, kind)

        def do_POST(self):
            if not self.allowed(post=True):
                return
            if self.path != "/api/run":
                self.send_json(404, {"error": "not_found"})
                return
            if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Type") != "application/json":
                self.send_json(400, {"error": "bounded_json_required"})
                return
            lengths = self.headers.get_all("Content-Length") or []
            if len(lengths) != 1 or not re.fullmatch(r"[0-9]{1,3}", lengths[0]) or not 1 <= int(lengths[0]) <= 64:
                self.send_json(400, {"error": "bounded_json_required"})
                return
            self.connection.settimeout(3)
            try:
                request = json.loads(self.rfile.read(int(lengths[0])))
                if not isinstance(request, dict) or set(request) != {"mode"} or request["mode"] not in COMMANDS:
                    raise ValueError()
            except (ValueError, TypeError, TimeoutError):
                self.send_json(400, {"error": "fixed_mode_required"})
                return
            if not state.start(request["mode"]):
                self.send_json(409, {"error": "run_already_active"})
                return
            self.send_json(202, {"accepted": True, "mode": request["mode"]})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Explicit deployment JSON; or set KIRO_DEMO_CONFIG")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        configure_runtime(config)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    state = OperatorState()
    server = ThreadingHTTPServer(("127.0.0.1", config["probe"]["port"]), handler_for(state))
    server.daemon_threads = True
    print("Operator screen: " + ORIGIN + "/ (commands run only after a UI button press)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
