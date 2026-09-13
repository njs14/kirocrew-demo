#!/usr/bin/env python3
"""Observe an existing native client session without sending chat or decisions.

Start before the first UI turn and wait for ready:true. Finish writes a local
stop request; it never stops the native session. All Gateway HTTP operations
are GETs. The additional owner WebSocket receives broadcasts and sends no
application messages. Normal dashboard connection bookkeeping still occurs.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from urllib.parse import quote

from demo_config import load_config, ssh_options

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("native_evidence_helpers", HERE / "native-backend-demo.py")
native = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(native)
SLOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9:_.-]{0,159}\Z")
PREFIX = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{6,65}\Z")
MAX_EVENTS = 20000
MAX_BYTES = 24_000_000
LIMITATIONS = [
    "Collection is not an automatic native-enforcement acceptance verdict.",
    "UI footage must independently show who submitted the prompt and approved once.",
    "A second owner WebSocket does not own approval callbacks, but normal dashboard connection bookkeeping and cache refreshes occur.",
    "WebSocket broadcasts have no sequence number; a connected stream alone cannot prove upstream callback completeness.",
    "Permission-triggered process snapshots do not establish that approval remained pending during SSH sampling.",
    "Crew hook-denial SEL lacks a direct trace/tool-call-ID link; use the isolated native turn and complete service interval.",
    "IAM attribution additionally requires deployed-policy and existing-object receipts.",
    "Configured Crew hooks are not proof of an immutable managed policy floor.",
]


def protected_directory(path):
    path = Path(path).expanduser().absolute()
    info = path.lstat()
    native.require(stat.S_ISDIR(info.st_mode) and not path.is_symlink() and
                   info.st_uid == os.getuid() and not info.st_mode & 0o077,
                   "evidence_directory_not_private")
    return path


def request_finish(path):
    directory = protected_directory(path)
    # A large transcript may make baseline.json exceed the small control-file
    # parser bound. Keep stop coordination independent of captured evidence.
    control = directory / "control.json"
    baseline = native.read_json(control if control.exists() else directory / "baseline.json")
    native.require(baseline.get("kind") in {"passive_native_client_control", "passive_native_client_baseline"}, "invalid_baseline")
    native.require(not (directory / "receipt.json").exists(), "collection_already_finished")
    native.write_new(directory / "finish-request.json", {"requested_at": native.now(), "run_id": baseline["run_id"]})
    return {"finish_requested": True, "run_dir": str(directory)}


async def bounded_read(response, limit=4_000_000):
    chunks, size = [], 0
    async for chunk in response.content.iter_chunked(65536):
        size += len(chunk)
        native.require(size <= limit, "gateway_read_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def sel_checkpoint(events):
    """recent() is newest first: retain the newest record as a bounded anchor."""
    ids = [event.get("event_id") for event in events]
    native.require(all(isinstance(value, str) and value for value in ids) and len(set(ids)) == len(ids),
                   "invalid_or_duplicate_sel_event_ids")
    return {"baseline_count": len(events), "anchor_event_id": ids[0] if ids else None,
            "anchor_sha256": native.digest(events[0]) if events else None}


def sel_interval(checkpoint, events):
    """A full recent page is usable only while the exact baseline anchor remains."""
    sel_checkpoint(events)  # Validate record IDs before locating the anchor.
    anchor = checkpoint["anchor_event_id"]
    if anchor is None:
        native.require(len(events) < 1000, "sel_empty_baseline_interval_may_be_truncated")
        return events, {"complete": True, "method": "empty_baseline_and_nonfull_recent_page", "event_count": len(events)}
    matches = [index for index, event in enumerate(events) if event["event_id"] == anchor]
    native.require(len(matches) == 1, "sel_baseline_anchor_not_retained")
    index = matches[0]
    native.require(native.digest(events[index]) == checkpoint["anchor_sha256"], "sel_baseline_anchor_changed")
    return events[:index], {"complete": True, "method": "exact_newest_baseline_anchor_retained",
                            "anchor_event_id": anchor, "anchor_index": index, "event_count": index}


def displayed_trace_input(value, trace):
    """Match the functional argument while retaining known ACP purpose metadata.

    Kiro CLI displays its reserved purpose argument in rawInput. Only the two
    documented spellings are accepted here, never arbitrary extra arguments.
    This is display correlation, not proof of bytes delivered to the MCP SDK.
    """
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return False
    if not isinstance(value, dict) or value.get("trace_id") != trace:
        return False
    extra = set(value) - {"trace_id"}
    return not extra or (len(extra) == 1 and extra <= {"__tool_use_purpose", "__toolUsePurpose"} and
                         isinstance(value[next(iter(extra))], str) and 0 < len(value[next(iter(extra))]) <= 4096)


def permission_metadata(data):
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    try:
        legacy = json.loads(data.get("cls") or "{}")
    except (TypeError, ValueError):
        legacy = {}
    legacy = legacy if isinstance(legacy, dict) else {}
    for key in ("tool_call_id", "tool_input"):
        native.require(key not in meta or key not in legacy or meta[key] == legacy[key], "conflicting_permission_metadata")
    identities = {str(source[key]) for source in (meta, legacy) for key in ("request_id", "approval_id") if source.get(key)}
    native.require(len(identities) <= 1, "conflicting_permission_request_ids")
    result = {**legacy, **meta}
    if identities:
        result["request_id"] = next(iter(identities))
    return result


def observations(events, audit, sel, prefix):
    """Expose bounded joins, never infer consent or acceptance from model prose."""
    rows = []
    audit_rows = audit.get("events", []) if isinstance(audit, dict) else []
    for phase, tool in native.PHASES:
        trace = prefix + "-" + phase
        call_ids, permission_ids, blocked_ids, outputs = set(), set(), set(), []
        for event in events:
            data = event.get("data", {})
            meta = permission_metadata(data)
            call_id = data.get("tool_call_id") or meta.get("tool_call_id")
            inputs = [data.get("input_preview"), meta.get("input"), meta.get("tool_input")]
            exact = any(displayed_trace_input(value, trace) for value in inputs)
            if exact and call_id and event.get("type") in {"tool_call", "chat_message", "chat_message_update"}:
                call_ids.add(call_id)
            if exact and data.get("role") == "permission" and meta.get("request_id"):
                permission_ids.add(str(meta["request_id"]))
            if exact and call_id and data.get("role") == "tool" and data.get("content", "").startswith("🚫") and \
                    "Blocked by security policy: @aws-enforcement/crew_denied" in data.get("content", ""):
                blocked_ids.add(call_id)
        for event in events:
            data = event.get("data", {})
            if event.get("type") == "tool_result" and data.get("tool_call_id") in call_ids:
                outputs.extend(item for item in native.result_objects(data.get("output", ""))
                               if item.get("trace_id") == trace and item.get("tool") == tool)
        service = [item for item in audit_rows if item.get("trace_id") == trace]
        invocation_ids = {item.get("invocation_id") for item in service if item.get("invocation_id")}
        joined = [item for item in outputs if item.get("invocation_id") in invocation_ids and
                  item.get("principal") == "kirocrew-demo-client"]
        rows.append({"phase": phase, "tool": tool, "trace_id": trace,
                     "native_tool_call_ids": sorted(call_ids), "permission_request_ids": sorted(permission_ids),
                     "native_blocked_tool_call_ids": sorted(blocked_ids),
                     "sel_for_permission_ids": [item for item in sel if str(item.get("request_id")) in permission_ids],
                     "service_events": service, "joined_native_service_results": joined})
    return rows


class Observer:
    def __init__(self, args):
        native.require(bool(SLOT.fullmatch(args.slot)), "invalid_slot")
        native.require(bool(PREFIX.fullmatch(args.trace_prefix)), "invalid_trace_prefix")
        self.config = load_config(args.config)
        native.SSH_OPTIONS = ssh_options(self.config)
        self.alias = self.config["ssh"]["admin_alias"]
        native.require(bool(native.SAFE_ALIAS.fullmatch(self.alias)), "invalid_ssh_alias")
        self.args = args
        self.directory = args.output.expanduser().absolute()
        native.require(not self.directory.exists() and not self.directory.is_symlink(), "output_directory_already_exists")
        self.directory.mkdir(parents=True, mode=0o700)
        protected_directory(self.directory)
        self.cleaner = native.Sanitizer()
        self.cleaner.identifiers.add(args.slot)
        self.cleaner.identifiers.update(args.trace_prefix + "-" + phase for phase, _ in native.PHASES)
        self.base = "http://localhost:" + str(self.config["ssh"]["local_port"])
        self.route = "/api/chat/slots/" + quote(args.slot, safe="")
        self.events, self.event_bytes, self.permission_snapshots = [], 0, set()
        self.cursor = None
        self.receipt = {"kind": "passive_native_client_evidence", "schema": 1,
                        "run_id": args.trace_prefix, "slot": args.slot, "started": native.now(),
                        "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        "helper_sha256": hashlib.sha256((HERE / "native-backend-demo.py").read_bytes()).hexdigest(),
                        "acceptance": "not_evaluated", "collection_complete": False,
                        "limitations": LIMITATIONS, "permission_triggered_process_snapshots": []}

    async def get(self, route):
        # Deliberately no generic method argument and no mutation-capable routes.
        native.require(route in {"/api/auth/me", "/api/chat/slots", "/api/sel/events?limit=1000", "/api/sel/verify", self.route},
                       "unapproved_read_route")
        async with self.http.get(self.base + route, allow_redirects=False) as response:
            native.require(response.status == 200, "gateway_read_failed")
            raw = await bounded_read(response)
            return json.loads(raw)

    async def sel(self):
        value = await self.get("/api/sel/events?limit=1000")
        native.require(isinstance(value.get("events"), list) and len(value["events"]) <= 1000 and
                       value.get("count") == len(value["events"]) and
                       all(isinstance(event, dict) for event in value["events"]), "invalid_sel_recent_page")
        sel_checkpoint(value["events"])
        return value["events"]

    async def ingest(self, frame):
        data, kind = frame.get("data"), frame.get("type")
        if not isinstance(data, dict) or data.get("slot") != self.args.slot or kind not in native.WS_TYPES:
            return
        meta = permission_metadata(data)
        request_id = str(meta.get("request_id", ""))
        if request_id and len(request_id) <= 150:
            self.cleaner.identifiers.add(request_id)
        safe = self.cleaner.clean({"time": native.now(), "type": kind, "data": data})
        encoded = json.dumps(safe, sort_keys=True) + "\n"
        self.event_bytes += len(encoded.encode())
        native.require(len(self.events) < MAX_EVENTS and self.event_bytes <= MAX_BYTES, "event_capture_limit_reached")
        self.events.append(safe)
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(encoded)
        if kind == "chat_message" and data.get("role") == "permission" and request_id and \
                not meta.get("resolved") and request_id not in self.permission_snapshots:
            native.require(len(self.permission_snapshots) < 16, "permission_snapshot_limit_reached")
            self.permission_snapshots.add(request_id)
            started = native.now()
            snapshot = await asyncio.to_thread(native.process_snapshot, self.alias)
            self.receipt["permission_triggered_process_snapshots"].append({
                "request_id": request_id, "started": started, "finished": native.now(),
                "approval_pending_during_sampling": "not_verified", "processes": snapshot})

    async def drain(self, ws, quiet_seconds=1.0, max_seconds=10.0):
        import aiohttp
        deadline = time.monotonic() + max_seconds
        while True:
            remaining = deadline - time.monotonic()
            native.require(remaining >= quiet_seconds, "websocket_drain_did_not_quiesce")
            try:
                frame = await ws.receive(timeout=quiet_seconds)
            except asyncio.TimeoutError:
                return
            native.require(frame.type == aiohttp.WSMsgType.TEXT, "websocket_closed_or_invalid")
            await self.ingest(json.loads(frame.data))

    async def final_snapshots(self):
        operations = {"slot_after": lambda: self.get(self.route),
                      "mcp_service_after": lambda: asyncio.to_thread(native.service_state, self.alias),
                      "sel_integrity_after": lambda: self.get("/api/sel/verify"),
                      "sel_after": self.sel}
        if self.cursor:
            operations["mcp_audit"] = lambda: asyncio.to_thread(native.journal_after, self.alias, self.cursor)
        for key, call in operations.items():
            try:
                value = await call()
                if key == "mcp_audit":
                    # The shared sanitizer caps lists at 1000; truncation must
                    # never be represented as complete journal collection.
                    native.require(len(value.get("events", [])) <= 1000, "audit_exceeds_sanitizer_bound")
                if key == "sel_after":
                    try:
                        interval, proof = sel_interval(self.receipt["sel_checkpoint"], value)
                        self.receipt["new_sel_interval"] = self.cleaner.clean(interval)
                        self.receipt["sel_window"] = proof
                    except native.DemoFailure as error:
                        self.receipt["sel_window"] = {"complete": False, "reason": str(error)}
                self.receipt[key] = self.cleaner.clean(value)
            except Exception as error:
                self.receipt[key] = {"collection_succeeded": False, "error_type": type(error).__name__}

    async def run(self):
        import aiohttp
        token = await asyncio.to_thread(native.owner_token, self.alias)
        self.cleaner.secrets.add(token)
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(), trust_env=False,
                                         timeout=aiohttp.ClientTimeout(total=35),
                                         headers={"Origin": self.base}) as self.http:
            async with self.http.get(self.base + "/", params={"token": token}, allow_redirects=False) as response:
                native.require(response.status in (200, 302, 303), "owner_cookie_exchange_failed")
                await bounded_read(response)
            self.cleaner.secrets.update(item.value for item in self.http.cookie_jar)
            await self.get("/api/auth/me")  # Identity response is intentionally discarded.
            before = await self.get(self.route)
            native.require(before.get("running") is False, "session_must_be_idle_before_capture")
            self.receipt["slot_before"] = self.cleaner.clean(before)
            self.receipt["mcp_service_before"] = await asyncio.to_thread(native.service_state, self.alias)
            self.cursor = await asyncio.to_thread(native.journal_start, self.alias)
            baseline_sel = await self.sel()
            self.receipt["sel_checkpoint"] = sel_checkpoint(baseline_sel)
            self.receipt["sel_before"] = self.cleaner.clean(baseline_sel)
            self.receipt["processes_before"] = await asyncio.to_thread(native.process_snapshot, self.alias)
            try:
                async with self.http.ws_connect(self.base + "/api/ws", heartbeat=20, max_msg_size=2_000_000) as ws:
                    # Receive-only: no subscribe, focus, approval or chat WS frames.
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        frame = await ws.receive_json(timeout=30)
                        if frame.get("type") == "slots":
                            break
                    else:
                        raise native.DemoFailure("websocket_subscription_not_ready")
                    native.require((await self.get(self.route)).get("running") is False,
                                   "session_started_before_capture_ready")
                    native.write_new(self.directory / "control.json", {
                        "kind": "passive_native_client_control", "run_id": self.args.trace_prefix})
                    native.write_new(self.directory / "baseline.json", self.cleaner.clean({
                        **self.receipt, "kind": "passive_native_client_baseline", "ready_at": native.now(),
                        "mcp_journal_cursor": self.cursor}))
                    print(json.dumps({"ready": True, "slot": self.args.slot,
                                      "trace_prefix": self.args.trace_prefix, "run_dir": str(self.directory)}), flush=True)
                    deadline = time.monotonic() + self.args.max_seconds
                    while True:
                        if (self.directory / "finish-request.json").exists():
                            request = native.read_json(self.directory / "finish-request.json")
                            native.require(request.get("run_id") == self.args.trace_prefix, "finish_run_mismatch")
                            self.receipt["finish_requested_at"] = request.get("requested_at")
                            break
                        native.require(time.monotonic() < deadline, "capture_time_limit_reached")
                        try:
                            frame = await ws.receive(timeout=0.5)
                        except asyncio.TimeoutError:
                            continue
                        native.require(frame.type == aiohttp.WSMsgType.TEXT, "websocket_closed_or_invalid")
                        await self.ingest(json.loads(frame.data))
                    native.require((await self.get(self.route)).get("running") is False,
                                   "session_running_at_finish")
                    await self.drain(ws)
                    native.require((await self.get(self.route)).get("running") is False,
                                   "session_started_during_finish")
                    await self.final_snapshots()
                    # Reads and SSH sampling can take time; consume any final
                    # callbacks delivered while those snapshots were collected.
                    await self.drain(ws)
                    native.require((await self.get(self.route)).get("running") is False,
                                   "session_started_during_finish")
                    self.receipt["stream_finished"] = native.now()
                    self.receipt["stream_quiet_interval_seconds"] = 1.0
            except BaseException:
                await self.final_snapshots()
                raise
        before, after = self.receipt["mcp_service_before"], self.receipt.get("mcp_service_after", {})
        self.receipt["service_stable"] = all(before.get(key) == after.get(key) for key in ("MainPID", "NRestarts", "InvocationID"))
        audit = self.receipt.get("mcp_audit", {})
        final_sel = self.receipt.get("sel_after")
        caller = "dashboard:" + self.args.slot.removeprefix("dashboard:")
        scoped = [item for item in self.receipt.get("new_sel_interval", []) if item.get("caller_identity") == caller]
        self.receipt["new_session_sel"] = scoped
        self.receipt["phase_observations"] = observations(self.events, audit, scoped, self.args.trace_prefix)
        self.receipt["collection_complete"] = bool(audit.get("collection_succeeded") and isinstance(final_sel, list) and
                                                    self.receipt.get("sel_window", {}).get("complete") is True and
                                                    self.receipt.get("slot_after", {}).get("running") is False and
                                                    self.receipt.get("sel_integrity_after", {}).get("integrity") == "ok" and
                                                    self.receipt["service_stable"])


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="Observe an existing idle slot; leave this process running")
    start.add_argument("--config")
    start.add_argument("--output", type=Path, required=True)
    start.add_argument("--slot", required=True)
    start.add_argument("--trace-prefix", required=True)
    start.add_argument("--max-seconds", type=int, default=1800)
    finish = commands.add_parser("finish", help="Request collection finalization; do not stop the native session")
    finish.add_argument("--run-dir", type=Path, required=True)
    return result


def main():
    os.umask(0o077)
    args = parser().parse_args()
    observer = None
    try:
        if args.command == "finish":
            print(json.dumps(request_finish(args.run_dir)))
            return 0
        native.require(30 <= args.max_seconds <= 3600, "invalid_capture_duration")
        observer = Observer(args)
        asyncio.run(observer.run())
        return 0 if observer.receipt["collection_complete"] else 1
    except BaseException as error:
        code = str(error) if isinstance(error, native.DemoFailure) else type(error).__name__
        if observer:
            observer.receipt.update(collection_complete=False, failure=code)
        else:
            print(json.dumps({"collection_complete": False, "failure": code}))
        return 1
    finally:
        if observer:
            observer.receipt.update(finished=native.now(), captured_events=len(observer.events))
            native.write_new(observer.directory / "receipt.json", observer.cleaner.clean(observer.receipt))
            print(json.dumps({"collection_complete": observer.receipt["collection_complete"],
                              "acceptance": "not_evaluated", "receipt": str(observer.directory / "receipt.json")}), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
