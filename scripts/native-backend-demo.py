#!/usr/bin/env python3
"""Run four real Kiro CLI turns through the dedicated EC2 Gateway.

The default `plan` command is offline. `run` starts a model session and performs
real fixed MCP/S3 reads. Every interactive approval requires a separate operator
decision bound to the exact sanitized pending card. No credentials are saved.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from urllib.parse import parse_qs, quote, urlsplit
import uuid

from demo_config import load_config, ssh_options

PROJECT = "/srv/kirocrew-demo/workspace"
AGENT = "enforcement-demo"
MCP_SERVER = "aws-enforcement"
SERVICE = "kirocrew-mcp-demo.service"
PHASES = (("allow", "read_allowed"), ("crew", "crew_denied"),
          ("mcp", "mcp_denied"), ("iam", "iam_denied"))
WS_TYPES = {"chat_message", "chat_message_update", "tool_call", "tool_result",
            "approval_resolved", "chat_done", "chat_status", "chat_segment"}
AUDIT_FIELDS = {"event", "time", "service", "trace_id", "invocation_id", "principal", "tool",
                "layer", "outcome", "aws_request_id", "http_status", "error_code",
                "object_bytes", "object_sha256"}
SAFE_ALIAS = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
SSH_OPTIONS = ["-o", "StrictHostKeyChecking=yes", "-o", "ForwardAgent=no"]


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=True).encode()).hexdigest()


class DemoFailure(Exception):
    """Only fixed, nonsensitive diagnostic codes are used in this exception."""


def require(ok, code):
    if not ok:
        raise DemoFailure(code)


class Sanitizer:
    def __init__(self):
        self.secrets = set()
        self.identifiers = {"canonical_parameterized_mcp_identity_exposed"}

    def text(self, value):
        for secret in sorted(self.secrets, key=len, reverse=True):
            if secret:
                value = value.replace(secret, "[REDACTED]")
        value = re.sub(r"https?://[^\s<>\"']+", "[URL REDACTED]", value)
        value = re.sub(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                       "[EMAIL REDACTED]", value)
        value = re.sub(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "[CREDENTIAL REDACTED]", value)
        value = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b",
                       "[TOKEN REDACTED]", value)
        value = re.sub(r"(?i)\bBearer\s+\S+", "Bearer [REDACTED]", value)
        value = re.sub(r"(?i)([\"']?(?:access_token|refresh_token|id_token|api[_-]?key|password|"
                       r"secret(?:_access_key)?|private_key|authorization|cookie)[\"']?\s*[=:]\s*[\"']?)[^\s,\"'}]+",
                       r"\1[REDACTED]", value)
        # Preserve SHA256 evidence; suppress opaque long token-shaped strings.
        value = re.sub(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_+/=-]{40,}(?![A-Za-z0-9_-])",
                       lambda m: m[0] if HEX64.fullmatch(m[0]) or m[0] in self.identifiers else "[OPAQUE REDACTED]", value)
        return value[:65536]

    def clean(self, value):
        if isinstance(value, str):
            # ACP often nests JSON inside cls/tool_input strings. Sanitize those
            # keys structurally, including escaped inner JSON, before serializing.
            try:
                nested = json.loads(value)
                if isinstance(nested, (dict, list)):
                    return json.dumps(self.clean(nested), sort_keys=True)
            except (ValueError, RecursionError):
                pass
            return self.text(value)
        if isinstance(value, list):
            return [self.clean(item) for item in value[:1000]]
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                original_key = str(key)
                safe_key = self.text(original_key)
                if re.search(r"(?i)(?:token|cookie|authorization|password|credential|email|api[_-]?key|secret|private[_-]?key)", str(key)):
                    result[safe_key] = "[REDACTED]"
                else:
                    result[safe_key] = self.clean(item)
            return result
        return value


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def read_json(path):
    require(path.is_file() and not path.is_symlink(), "invalid_evidence_file")
    require(path.stat().st_size <= 2_000_000, "oversized_evidence_file")
    return json.loads(path.read_text())


def fixed_prompts(run_id):
    return [{"phase": phase, "tool": tool, "trace_id": f"native-{run_id}-{phase}",
             "message": (f"Call exactly the MCP tool @{MCP_SERVER}/{tool} once with the only "
                         f"argument trace_id=\"native-{run_id}-{phase}\". Do not call any other "
                         "tool, use a shell, retry, or take an alternative route. After a denial, "
                         "stop and report that denial. Return the tool's structured result.")}
            for phase, tool in PHASES]


def ssh(alias, argv):
    require(bool(SAFE_ALIAS.fullmatch(alias)), "invalid_ssh_alias")
    result = subprocess.run(["ssh", *SSH_OPTIONS, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", alias,
                             shlex.join(argv)], capture_output=True, timeout=40)
    require(result.returncode == 0, "ssh_command_failed")
    require(len(result.stdout) < 8_000_000, "remote_output_too_large")
    return result.stdout.decode("utf-8", "replace")


def owner_token(alias):
    output = ssh(alias, ["/usr/local/bin/kirocrew-owner-token", "token", "--ttl", "30m"])
    # CLI diagnostics and the URL never leave this function or enter a receipt.
    found = []
    for url in re.findall(r"https?://[^\s<>\"']+", output):
        found.extend(parse_qs(urlsplit(url).query).get("token", []))
    if not found:
        found = re.findall(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", output)
    require(len(set(found)) == 1, "owner_token_not_unambiguous")
    return found[0]


def service_state(alias):
    output = ssh(alias, ["sudo", "-n", "systemctl", "show", SERVICE,
                        "--property=ActiveState,SubState,MainPID,NRestarts,InvocationID"])
    values = dict(line.split("=", 1) for line in output.splitlines() if "=" in line)
    require(values.get("ActiveState") == "active" and values.get("SubState") == "running",
            "mcp_service_not_healthy")
    require(values.get("MainPID", "0") != "0" and values.get("InvocationID"), "mcp_service_identity_missing")
    return values


def journal_start(alias):
    raw = ssh(alias, ["sudo", "-n", "journalctl", "-u", SERVICE, "-n", "1", "-o", "json", "--no-pager"])
    rows = [json.loads(line) for line in raw.splitlines() if line.startswith("{")]
    require(len(rows) == 1 and rows[0].get("__CURSOR"), "mcp_journal_start_cursor_missing")
    return rows[0]["__CURSOR"]


def journal_after(alias, cursor):
    raw = ssh(alias, ["sudo", "-n", "journalctl", "-u", SERVICE, "--after-cursor", cursor,
                      "--show-cursor", "-o", "json", "--no-pager"])
    rows, ignored, end = [], 0, None
    for line in raw.splitlines():
        if line.startswith("-- cursor: "):
            end = line.removeprefix("-- cursor: ")
            continue
        if not line.strip():
            continue
        envelope = json.loads(line)
        message = envelope.get("MESSAGE", "")
        require(not isinstance(message, str) or not re.search(r"(?i)(suppressed|dropped|missed)\s+\d+\s+messages", message),
                "mcp_journal_reports_message_loss")
        if not isinstance(message, str) or not message.startswith("{"):
            ignored += 1
            continue
        value = json.loads(message)
        rows.append({**{key: value[key] for key in AUDIT_FIELDS if key in value},
                     "journal_cursor": envelope.get("__CURSOR"),
                     "journal_timestamp_us": envelope.get("__REALTIME_TIMESTAMP"),
                     "journal_invocation_id": envelope.get("_SYSTEMD_INVOCATION_ID")})
    require(end is not None, "mcp_journal_end_cursor_missing")
    return {"start_cursor": cursor, "end_cursor": end, "events": rows,
            "ignored_non_audit_rows": ignored, "collection_succeeded": True}


PROCESS_SCRIPT = '''import json,os,pathlib,pwd
uids={pwd.getpwnam(n).pw_uid for n in ("crew","mcp-demo")}
out=[]
for p in pathlib.Path("/proc").iterdir():
 if not p.name.isdigit(): continue
 try:
  s=(p/"status").read_text(); uid=int(next(x for x in s.splitlines() if x.startswith("Uid:")).split()[1])
  if uid not in uids: continue
  ppid=int(next(x for x in s.splitlines() if x.startswith("PPid:")).split()[1])
  out.append({"pid":int(p.name),"ppid":ppid,"uid":uid,"comm":(p/"comm").read_text().strip(),"exe":os.readlink(p/"exe"),"cwd":os.readlink(p/"cwd")})
 except (OSError,StopIteration,ValueError): pass
print(json.dumps(out))'''


def process_snapshot(alias):
    return json.loads(ssh(alias, ["sudo", "-n", "python3", "-c", PROCESS_SCRIPT]))


def permission_meta(data):
    meta = data.get("meta")
    if not isinstance(meta, dict):
        try:
            meta = json.loads(data.get("cls") or "{}")
        except (TypeError, ValueError):
            meta = {}
    return meta if isinstance(meta, dict) else {}


def exact_trace_input(value, trace):
    """Only actual JSON arguments count; assistant prose containing a trace does not."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return False
    return isinstance(value, dict) and value == {"trace_id": trace}


def result_objects(value):
    """Extract bounded JSON result objects from the backend's text envelope."""
    if not isinstance(value, str):
        return []
    found = []
    for match in list(re.finditer(r"\{", value))[:64]:
        try:
            item, _ = json.JSONDecoder().raw_decode(value[match.start():])
            if isinstance(item, dict):
                found.append(item)
        except ValueError:
            pass
    return found


def approve(args):
    require(not args.run_dir.is_symlink() and args.run_dir.stat().st_uid == os.getuid() and
            args.run_dir.stat().st_mode & 0o077 == 0, "evidence_directory_not_private")
    pending = read_json(args.run_dir / "pending.json")
    require(pending.get("request_id") == args.request_id, "pending_request_id_mismatch")
    require(pending.get("card_sha256") == args.card_sha256, "pending_card_digest_mismatch")
    require(digest({key: value for key, value in pending.items() if key != "card_sha256"}) == args.card_sha256,
            "pending_card_bytes_changed")
    require(pending.get("phase") != "crew", "crew_denial_must_never_be_manually_approved")
    if args.command == "approve":
        require(not pending.get("approval_input_redacted"), "cannot_approve_hidden_input_bytes")
        require(pending.get("arguments_match_fixed_trace") is True, "approval_arguments_do_not_match_fixed_trace")
    decision = {"request_id": args.request_id, "card_sha256": args.card_sha256,
                "action": "approved" if args.command == "approve" else "rejected",
                "operator_reviewed_exact_inputs": True, "time": now()}
    write_new(args.run_dir / "decision.json", decision)
    print(json.dumps({"decision_recorded": True, "action": decision["action"],
                      "request_id": args.request_id}))


class Runner:
    def __init__(self, args):
        self.args, self.cleaner = args, Sanitizer()
        self.directory = args.output.resolve()
        require(not self.directory.exists(), "output_directory_already_exists")
        self.directory.mkdir(parents=True, mode=0o700)
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
        self.cleaner.identifiers.update(item["trace_id"] for item in fixed_prompts(self.run_id))
        self.base = f"http://localhost:{args.gateway_port}"
        self.slot, self.current = "", None
        self.receipt = {"schema": 1, "kind": "native_backend_demo", "run_id": self.run_id,
                        "started": now(), "passed": False, "project": PROJECT, "agent": AGENT,
                        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        "expected_allowed_sha256": args.expected_allowed_sha256,
                        "phases": [], "limitations": [
                            "The dashboard does not expose canonical MCP identity for parameterized approval cards.",
                            "Crew denial SEL correlates by isolated session and phase interval; it lacks a direct trace/tool-call-ID link.",
                            "SEL integrity verifies the stored chain, not the completeness of every upstream callback.",
                            "IAM policy attribution also requires the separate deployed-policy and existing-object receipts."]}
        self.http = None

    def emit(self, kind, **data):
        row = self.cleaner.clean({"time": now(), "kind": kind, **data})
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    async def request(self, method, route, body=None):
        async with self.http.request(method, self.base + route, json=body,
                                     allow_redirects=False) as response:
            require(response.status == 200, f"gateway_http_{response.status}")
            raw = await response.read()
            require(len(raw) <= 4_000_000, "gateway_response_too_large")
            return json.loads(raw)

    async def sel(self):
        data = await self.request("GET", "/api/sel/events?limit=1000")
        require(isinstance(data.get("events"), list), "invalid_sel_response")
        # Refuse a full page: earlier correlated rows could have been truncated.
        require(len(data["events"]) < 1000, "sel_page_may_be_truncated")
        return data["events"]

    async def stop(self):
        if self.slot:
            try:
                await self.request("POST", f"/api/chat/slots/{quote(self.slot, safe='')}/stop", {})
                self.emit("dedicated_slot_stopped")
            except Exception as error:
                self.emit("stop_failed", error_type=type(error).__name__)

    async def run(self):
        import aiohttp  # Only the explicit live command requires this dependency.
        token = await asyncio.to_thread(owner_token, self.args.admin_host)
        self.cleaner.secrets.add(token)
        jar = aiohttp.CookieJar()
        async with aiohttp.ClientSession(cookie_jar=jar, trust_env=False,
                                         timeout=aiohttp.ClientTimeout(total=35),
                                         headers={"Origin": self.base}) as self.http:
            async with self.http.get(self.base + "/", params={"token": token},
                                     allow_redirects=False) as response:
                require(response.status in (200, 302, 303), "owner_cookie_exchange_failed")
                await response.read()
            self.cleaner.secrets.update(cookie.value for cookie in jar)
            await self.request("GET", "/api/auth/me")  # Do not persist identity/email.
            self.receipt["mcp_service_before"] = await asyncio.to_thread(service_state, self.args.admin_host)
            cursor = await asyncio.to_thread(journal_start, self.args.admin_host)
            self.receipt["processes_before"] = await asyncio.to_thread(process_snapshot, self.args.admin_host)
            async with self.http.ws_connect(self.base + "/api/ws", heartbeat=20,
                                            max_msg_size=2_000_000) as ws:
                try:
                    # The HTTP upgrade precedes Gateway broadcast registration.
                    # Its initial slots frame is the subscription-ready barrier.
                    ready_by = time.monotonic() + 30
                    while time.monotonic() < ready_by:
                        frame = await ws.receive_json(timeout=30)
                        if frame.get("type") == "slots":
                            break
                    else:
                        raise DemoFailure("websocket_subscription_not_ready")
                    existing = await self.request("GET", "/api/chat/slots")
                    require(not any(item.get("running") for item in existing), "dedicated_demo_gateway_busy")
                    created = await self.request("POST", "/api/chat/slots", {
                        "name": "ec2-enforcement-" + self.run_id, "agent": AGENT,
                        "memory_mode": "persistent", "title": "EC2 enforcement demo " + self.run_id})
                    self.slot = created["key"]
                    self.cleaner.identifiers.add(self.slot)
                    self.receipt["slot"] = self.slot
                    await self.request("POST", f"/api/chat/slots/{quote(self.slot, safe='')}/project", {"project": PROJECT})
                    await self.request("POST", "/api/chat/mode", {"slot": self.slot, "mode": "normal"})
                    for phase in fixed_prompts(self.run_id):
                        await self.phase(ws, phase)
                    self.receipt["mcp_audit"] = await asyncio.to_thread(journal_after, self.args.admin_host, cursor)
                    self.receipt["mcp_service_after"] = await asyncio.to_thread(service_state, self.args.admin_host)
                    self.receipt["sel_integrity"] = await self.request("GET", "/api/sel/verify")
                    self.evaluate()
                except BaseException:
                    await self.stop()
                    # Preserve obtainable partial evidence without turning collection failure into absence proof.
                    for key, fn in (("mcp_audit", lambda: asyncio.to_thread(journal_after, self.args.admin_host, cursor)),
                                    ("mcp_service_after", lambda: asyncio.to_thread(service_state, self.args.admin_host))):
                        if key not in self.receipt:
                            try:
                                self.receipt[key] = await fn()
                            except Exception as error:
                                self.receipt[key] = {"collection_succeeded": False, "error_type": type(error).__name__}
                    raise

    async def phase(self, ws, phase):
        import aiohttp
        self.current = row = {**phase, "started": now(), "approvals": [], "events": []}
        self.receipt["phases"].append(row)
        baseline_ids = {item.get("event_id") for item in await self.sel()}
        sent = await self.request("POST", "/api/chat?ws=1", {"slot": self.slot, "message": phase["message"]})
        require(sent.get("ok") is True and not sent.get("queued") and not sent.get("steered"), "turn_not_admitted_directly")
        row["admission"] = sent
        deadline, pending, started = time.monotonic() + self.args.turn_timeout, None, False
        calls = {}
        while time.monotonic() < deadline:
            if pending:
                decision_path = self.directory / "decision.json"
                if decision_path.exists():
                    decision = read_json(decision_path)
                    require(read_json(self.directory / "pending.json") == pending, "pending_card_changed_after_display")
                    require(decision.get("request_id") == pending["request_id"] and
                            decision.get("card_sha256") == pending["card_sha256"] and
                            decision.get("action") in ("approved", "rejected") and
                            decision.get("operator_reviewed_exact_inputs") is True, "invalid_operator_decision")
                    require(decision["action"] != "approved" or not pending["approval_input_redacted"], "cannot_approve_hidden_input_bytes")
                    require(decision["action"] != "approved" or pending["arguments_match_fixed_trace"], "approval_arguments_do_not_match_fixed_trace")
                    await self.request("POST", f"/api/chat/slots/{quote(self.slot, safe='')}/approve",
                                       {"request_id": decision["request_id"], "action": decision["action"]})
                    row["approvals"].append({"card": pending, "decision": decision})
                    index = len(row["approvals"])
                    decision_path.rename(self.directory / f"{phase['phase']}-decision-{index}.json")
                    (self.directory / "pending.json").rename(self.directory / f"{phase['phase']}-card-{index}.json")
                    self.emit("approval_submitted", **decision)
                    pending = None
                    require(decision["action"] == "approved", "operator_rejected_demo_call")
            try:
                message = await ws.receive(timeout=0.5)
            except asyncio.TimeoutError:
                continue
            require(message.type == aiohttp.WSMsgType.TEXT, "websocket_closed_or_invalid")
            frame = json.loads(message.data)
            data, kind = frame.get("data"), frame.get("type")
            if not isinstance(data, dict) or data.get("slot") != self.slot or kind not in WS_TYPES:
                continue
            if kind == "chat_message" and data.get("role") == "user" and data.get("content") == phase["message"]:
                started = True
            # Tool activity also proves the current phase began if the user echo was coalesced.
            if phase["trace_id"] in json.dumps(data):
                started = True
            if not started:
                continue
            if kind == "chat_message" and data.get("role") == "permission":
                native_request_id = str(permission_meta(data).get("request_id", ""))
                if native_request_id and len(native_request_id) <= 150:
                    self.cleaner.identifiers.add(native_request_id)
            safe_frame = self.emit("websocket", phase=phase["phase"], type=kind, data=data)
            row["events"].append(safe_frame)
            if kind == "tool_call" and data.get("tool_call_id"):
                calls[data["tool_call_id"]] = self.cleaner.clean(data)
            if kind == "chat_message" and data.get("role") == "permission":
                meta = permission_meta(data)
                if meta.get("resolved"):
                    continue
                require(meta.get("request_id") is not None, "permission_request_id_missing")
                request_id = str(meta["request_id"])
                require(len(request_id) <= 150, "permission_request_id_invalid")
                if phase["phase"] == "crew":
                    await self.request("POST", f"/api/chat/slots/{quote(self.slot, safe='')}/approve",
                                       {"request_id": request_id, "action": "rejected"})
                    row["unexpected_approval_rejected"] = True
                    raise DemoFailure("crew_denied_became_approvable")
                require(pending is None and not row["approvals"], "unexpected_additional_permission")
                card = {"phase": phase["phase"], "slot": self.slot, "request_id": request_id,
                        "expected_tool": phase["tool"], "expected_trace_id": phase["trace_id"],
                        "native_card": self.cleaner.clean(data),
                        "related_tool_call": calls.get(meta.get("tool_call_id")),
                        "canonical_parameterized_mcp_identity_exposed": False,
                        "arguments_match_fixed_trace": exact_trace_input(meta.get("tool_input"), phase["trace_id"]),
                        "approval_input_redacted": "REDACT" in str(meta.get("tool_input", "")).upper() or
                            self.cleaner.text(str(meta.get("tool_input", ""))) != str(meta.get("tool_input", ""))}
                card["card_sha256"] = digest(card)
                pending = card
                write_new(self.directory / "pending.json", card)
                print(json.dumps({"pending_approval": str(self.directory / "pending.json"),
                                  "phase": phase["phase"], "request_id": request_id,
                                  "card_sha256": card["card_sha256"]}), flush=True)
                row["processes_during_approval"] = await asyncio.to_thread(process_snapshot, self.args.admin_host)
            if kind == "chat_done":
                detail = await self.request("GET", f"/api/chat/slots/{quote(self.slot, safe='')}")
                if detail.get("running"):
                    continue
                require(pending is None, "turn_finished_with_unresolved_approval")
                row["transcript"] = self.cleaner.clean(detail)
                break
        else:
            raise DemoFailure("turn_timed_out")
        row["finished"] = now()
        # The native SEL writer is asynchronous; bounded polling awaits its correlated decision.
        for attempt in range(12):
            rows = [item for item in await self.sel() if item.get("event_id") not in baseline_ids and
                    item.get("caller_identity") == "dashboard:" + self.slot.removeprefix("dashboard:")]
            if any(item.get("outcome") in ("approved", "denied") for item in rows):
                break
            await asyncio.sleep(0.25)
        row["sel"] = self.cleaner.clean(rows)
        slots = await self.request("GET", "/api/chat/slots")
        metadata = next((item for item in slots if item.get("key") == self.slot), {})
        row["slot_metadata"] = self.cleaner.clean({key: metadata.get(key) for key in (
            "key", "agent", "effective_agent", "model", "served_model", "workspace", "project",
            "running", "trust", "trust_reads", "trusted_patterns_count", "mcp_report")})
        require(metadata.get("project") == PROJECT and metadata.get("agent") == AGENT, "slot_execution_scope_changed")
        require(not metadata.get("trust") and not metadata.get("trust_reads"), "unexpected_persistent_trust")
        write_new(self.directory / f"{phase['phase']}-phase.json", self.cleaner.clean(row))
        print(json.dumps({"phase_finished": phase["phase"], "receipt": f"{phase['phase']}-phase.json"}), flush=True)

    def evaluate(self):
        before, after = self.receipt["mcp_service_before"], self.receipt["mcp_service_after"]
        stable = all(before.get(key) == after.get(key) for key in ("MainPID", "NRestarts", "InvocationID"))
        require(stable, "mcp_service_changed_during_evidence_interval")
        audit = self.receipt["mcp_audit"]
        require(audit.get("collection_succeeded"), "mcp_audit_incomplete")
        all_events = audit["events"]
        checks = []
        for row in self.receipt["phases"]:
            phase, trace, tool = row["phase"], row["trace_id"], row["tool"]
            events = [event for event in all_events if event.get("trace_id") == trace]
            invocations = {event.get("invocation_id") for event in events}
            common = all(event.get("tool") == tool and event.get("principal") == "kirocrew-demo-client" and
                         event.get("journal_invocation_id") == before["InvocationID"] for event in events)
            decisions = [event for event in events if event.get("event") == "tool_decision"]
            dispatch = [event for event in events if event.get("event") == "aws_dispatch"]
            results = [event for event in events if event.get("event") == "aws_result"]
            native = [event for event in row["sel"] if event.get("event_type") == "tool_invocation"]
            call_ids, trace_ids, blocked_ids = set(), set(), set()
            for event in row["events"]:
                data = event["data"]
                meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
                tcid = data.get("tool_call_id") or meta.get("tool_call_id")
                is_tool = event["type"] == "tool_call" or (event["type"] == "chat_message" and data.get("role") == "tool")
                if not tcid or not is_tool:
                    continue
                call_ids.add(tcid)
                if exact_trace_input(data.get("input_preview", meta.get("input")), trace):
                    trace_ids.add(tcid)
                    if (data.get("role") == "tool" and data.get("content", "").startswith("🚫") and
                            "Blocked by security policy: @aws-enforcement/crew_denied" in data.get("content", "")):
                        blocked_ids.add(tcid)
            # A later same-ID refinement may fill input absent on the initial tool_call.
            for event in row["events"]:
                data = event["data"]
                meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
                tcid = data.get("tool_call_id") or meta.get("tool_call_id")
                if event["type"] == "chat_message_update" and tcid in call_ids and exact_trace_input(meta.get("input"), trace):
                    trace_ids.add(tcid)
            one_exact_call = len(call_ids) == 1 and call_ids == trace_ids
            if phase == "crew":
                denied = [event for event in native if event.get("outcome") == "denied" and event.get("error") == "hook_deny" and event.get("request_id")]
                passed = not events and not row["approvals"] and len(denied) == 1 and one_exact_call and blocked_ids == trace_ids
                row["correlation"] = "dedicated session and isolated phase; trace-bearing tool row plus unique native hook_deny; no direct SEL trace link"
            else:
                approvals = row["approvals"]
                approved_ids = {item["decision"]["request_id"] for item in approvals}
                native_ids = {str(item.get("request_id")) for item in native if item.get("outcome") == "approved"}
                approved_call_ids = {permission_meta(item["card"]["native_card"]).get("tool_call_id") for item in approvals}
                approved_inputs_exact = all(exact_trace_input(permission_meta(item["card"]["native_card"]).get("tool_input"), trace) for item in approvals)
                passed = (common and len(invocations) == 1 and None not in invocations and len(decisions) == 1 and
                          len(approvals) == 1 and approved_ids <= native_ids and one_exact_call and
                          approved_call_ids == trace_ids and approved_inputs_exact)
                if phase == "mcp":
                    passed = passed and decisions[0].get("outcome") == "denied" and not dispatch and not results
                else:
                    passed = passed and decisions[0].get("outcome") == "allowed" and len(dispatch) == 1 and len(results) == 1
                    result = results[0] if len(results) == 1 else {}
                    passed = passed and bool(result.get("aws_request_id"))
                    if phase == "allow":
                        passed = passed and result.get("outcome") == "allowed" and result.get("object_sha256") == self.args.expected_allowed_sha256
                    else:
                        passed = passed and result.get("outcome") == "denied" and result.get("error_code") == "AccessDenied" and result.get("http_status") == 403
                # Bind the observed backend result to the independently collected service invocation.
                outputs = [event["data"].get("output", "") for event in row["events"] if event.get("type") == "tool_result" and event["data"].get("tool_call_id") in approved_call_ids]
                invocation = next(iter(invocations), "") or ""
                payloads = [payload for output in outputs for payload in result_objects(output) if
                            payload.get("trace_id") == trace and payload.get("invocation_id") == invocation and
                            payload.get("tool") == tool and payload.get("principal") == "kirocrew-demo-client"]
                expected_layer = "mcp" if phase == "mcp" else "aws"
                expected_error = {"allow": None, "mcp": "tool_grant_denied", "iam": "AccessDenied"}[phase]
                passed = passed and any(payload.get("layer") == expected_layer and payload.get("error_code") == expected_error and
                                        payload.get("ok") is (phase == "allow") for payload in payloads)
                row["correlation"] = "operator-approved native request ID to SEL; trace and invocation ID in native tool output to service audit"
            row["audit_events"] = events
            row["passed"] = bool(passed)
            checks.append({"phase": phase, "passed": bool(passed)})
        integrity = self.receipt["sel_integrity"]
        checks.append({"phase": "sel_integrity", "passed": integrity.get("integrity") == "ok" and
                       integrity.get("total", 0) > 0 and integrity.get("total") == integrity.get("valid") and integrity.get("tampered") == 0})
        processes = [item for row in self.receipt["phases"] for item in row.get("processes_during_approval", [])]
        checks.append({"phase": "remote_backend_cwd", "passed": any(item.get("cwd") == PROJECT and
                       Path(item.get("exe", "")).name.startswith("kiro-cli") for item in processes)})
        self.receipt["checks"] = checks
        self.receipt["passed"] = all(check["passed"] for check in checks)
        require(self.receipt["passed"], "native_evidence_expectations_not_met")


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command")
    commands.add_parser("plan", help="Print fixed scope and prompts without network/model calls")
    live = commands.add_parser("run", help="Start a real remote model session and fixed MCP/AWS reads")
    live.add_argument("--output", type=Path, required=True, help="New private evidence directory")
    live.add_argument("--expected-allowed-sha256", required=True)
    live.add_argument("--config", help="Explicit local deployment config; alternatively KIRO_DEMO_CONFIG")
    live.add_argument("--gateway-port", type=int, default=None)
    live.add_argument("--admin-host", default=None,
                      help="Existing administrator SSH alias for owner bootstrap and read-only evidence")
    live.add_argument("--turn-timeout", type=int, default=300)
    for name in ("approve", "reject"):
        decision = commands.add_parser(name, help="Resolve one operator-reviewed pending card")
        decision.add_argument("--run-dir", type=Path, required=True)
        decision.add_argument("--request-id", required=True)
        decision.add_argument("--card-sha256", required=True)
    return result


def main():
    global SSH_OPTIONS
    os.umask(0o077)
    args = parser().parse_args()
    if args.command in (None, "plan"):
        print(json.dumps({"mode": "offline_plan", "project": PROJECT, "agent": AGENT,
                          "prompts": fixed_prompts("RUNID"), "automatic_approval": False}, indent=2))
        return 0
    runner = None
    try:
        if args.command in ("approve", "reject"):
            approve(args)
            return 0
        try:
            config = load_config(args.config)
            SSH_OPTIONS = ssh_options(config)
        except (OSError, ValueError) as error:
            raise DemoFailure("runtime_config_invalid: use --config with a verified SSH host-key configuration") from error
        args.gateway_port = args.gateway_port if args.gateway_port is not None else config["ssh"]["local_port"]
        args.admin_host = args.admin_host or config["ssh"]["admin_alias"]
        require(bool(SAFE_ALIAS.fullmatch(args.admin_host)), "invalid_ssh_alias")
        require(bool(HEX64.fullmatch(args.expected_allowed_sha256)), "invalid_expected_fixture_digest")
        require(1 <= args.gateway_port <= 65535 and 30 <= args.turn_timeout <= 600, "invalid_runtime_limits")
        runner = Runner(args)
        asyncio.run(runner.run())
    except BaseException as error:
        code = str(error) if isinstance(error, DemoFailure) else type(error).__name__
        if runner:
            runner.receipt.update(passed=False, failure=code)
        else:
            print(json.dumps({"passed": False, "failure": code}))
            return 1
    finally:
        if runner:
            runner.receipt["finished"] = now()
            for name in ("pending.json", "decision.json"):
                path = runner.directory / name
                if path.exists():
                    path.rename(runner.directory / ("unresolved-" + name))
            write_new(runner.directory / "receipt.json", runner.cleaner.clean(runner.receipt))
            print(json.dumps({"passed": runner.receipt["passed"], "receipt": str(runner.directory / "receipt.json")}))
    return 0 if runner.receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
