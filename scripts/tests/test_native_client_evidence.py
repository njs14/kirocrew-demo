"""Offline collector checks: no AWS, SSH, Gateway, browser or model calls."""
import argparse
import ast
import asyncio
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("passive_collector", SCRIPTS / "capture-native-client-evidence.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)
RECONCILE_SPEC = importlib.util.spec_from_file_location("reconciler", SCRIPTS / "reconcile-native-client-evidence.py")
reconcile = importlib.util.module_from_spec(RECONCILE_SPEC)
RECONCILE_SPEC.loader.exec_module(reconcile)
PREFIX = "native-offline-test"


def reconciliation_fixture():
    events, audit, sel = [], [], []
    for index, (phase, tool) in enumerate(module.native.PHASES):
        trace, call, request = PREFIX + "-" + phase, "call-" + phase, "request-" + phase
        stamp = "2026-09-13T21:2" + str(index) + ":"
        inputs = json.dumps({"trace_id": trace, "__tool_use_purpose": "Requested fixed read"})
        def event(kind, second, data):
            events.append({"type": kind, "time": stamp + second + "+00:00", "data": {"slot": "slot", **data}})
        event("chat_message", "00", {"role": "user", "content": "Call " + trace})
        event("tool_call", "01", {"tool_call_id": call, "input_preview": inputs})
        operation = "Running: @aws-enforcement/" + tool
        if phase == "crew":
            event("chat_message", "02", {"role": "tool", "tool_call_id": call, "meta": {"input": inputs}, "content": "🚫 Blocked by security policy: @aws-enforcement/crew_denied"})
            sel.append({"event_type": "tool_invocation", "outcome": "denied", "error": "hook_deny", "operation": operation, "request_id": request, "timestamp": stamp + "02+00:00"})
            continue
        event("chat_message", "02", {"role": "permission", "meta": {"approval_id": request, "tool_call_id": call, "tool_input": inputs}})
        event("approval_resolved", "03", {"approved": True, "id": request})
        sel.append({"event_type": "tool_invocation", "outcome": "approved", "operation": operation, "request_id": request})
        base = {"trace_id": trace, "tool": tool, "principal": "kirocrew-demo-client", "invocation_id": "inv-" + phase, "journal_invocation_id": "service-id"}
        audit.append({**base, "event": "tool_decision", "outcome": "denied" if phase == "mcp" else "allowed"})
        payload = {"trace_id": trace, "tool": tool, "principal": base["principal"], "invocation_id": base["invocation_id"], "ok": phase == "allow", "layer": "mcp" if phase == "mcp" else "aws"}
        if phase == "mcp":
            payload["error_code"] = "tool_grant_denied"
        else:
            payload["aws_request_id"] = "aws-" + phase
            if phase == "allow":payload.update(object_sha256="a" * 64, object_bytes=55)
            else:payload.update(error_code="AccessDenied", http_status=403)
            audit.append({**base, "event": "aws_dispatch", "outcome": "attempted"})
            audit.append({**base, **payload, "event": "aws_result", "outcome": "allowed" if phase == "allow" else "denied"})
        event("tool_result", "04", {"tool_call_id": call, "output": json.dumps(payload)})
    receipt = {"run_id": PREFIX, "slot": "slot", "stream_finished": "2026-09-13T21:24:00+00:00", "service_stable": True,
               "mcp_service_before": {"InvocationID": "service-id"}, "sel_integrity_after": {"integrity": "ok"},
               "mcp_audit": {"collection_succeeded": True, "events": audit}}
    return receipt, events, {"scan_complete": True, "events": sel}


class PassiveCollectorTests(unittest.TestCase):
    def test_no_application_write_transport(self):
        tree = ast.parse(Path(module.__file__).read_text())
        forbidden = {"post", "put", "patch", "delete", "request", "send_json", "send_str", "send_bytes"}
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(calls & forbidden)

    def test_only_read_routes_are_admitted(self):
        observer = module.Observer.__new__(module.Observer)
        observer.route = "/api/chat/slots/example"
        # No http attribute: a rejected route must fail before network access.
        for route in ("/api/chat", "/api/chat/slots/example/approve", "/api/chat/slots/example/stop", "/api/config"):
            with self.subTest(route=route), self.assertRaises(module.native.DemoFailure):
                asyncio.run(observer.get(route))

    def test_finish_is_local_and_bound_to_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "baseline.json").write_text(json.dumps({"kind": "passive_native_client_baseline", "run_id": PREFIX}))
            self.assertTrue(module.request_finish(path)["finish_requested"])
            self.assertEqual(json.loads((path / "finish-request.json").read_text())["run_id"], PREFIX)
            with self.assertRaises(FileExistsError):
                module.request_finish(path)

    def test_finish_rejects_nonprivate_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            path.chmod(0o755)
            try:
                with self.assertRaises(module.native.DemoFailure):
                    module.request_finish(path)
            finally:
                path.chmod(0o700)

    def test_finish_uses_small_control_when_baseline_is_large(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "baseline.json").write_text(json.dumps({"transcript": "x" * 2_100_000}))
            (path / "control.json").write_text(json.dumps({"kind": "passive_native_client_control", "run_id": PREFIX}))
            self.assertTrue(module.request_finish(path)["finish_requested"])

    def test_streaming_read_stops_at_bound(self):
        class Content:
            seen = 0
            async def iter_chunked(self, size):
                for _ in range(5):
                    self.seen += 1
                    yield b"xxxx"
        response = argparse.Namespace(content=Content())
        with self.assertRaises(module.native.DemoFailure):
            asyncio.run(module.bounded_read(response, limit=7))
        self.assertEqual(response.content.seen, 2)

    def test_finish_rejects_symlink_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            link = path / "link"
            link.symlink_to(path, target_is_directory=True)
            with self.assertRaises(module.native.DemoFailure):
                module.request_finish(link)

    def test_finish_rejects_finished_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "baseline.json").write_text(json.dumps({"kind": "passive_native_client_baseline", "run_id": PREFIX}))
            (path / "receipt.json").write_text("{}")
            with self.assertRaises(module.native.DemoFailure):
                module.request_finish(path)

    def test_model_prose_is_not_tool_evidence(self):
        rows = module.observations([{"type": "chat_message", "data": {"role": "assistant", "content": PREFIX + "-crew was denied"}}], {}, [], PREFIX)
        self.assertEqual(rows[1]["native_tool_call_ids"], [])
        self.assertEqual(rows[1]["native_blocked_tool_call_ids"], [])

    def test_service_result_requires_actual_native_tool_output(self):
        trace = PREFIX + "-mcp"
        payload = {"trace_id": trace, "tool": "mcp_denied", "principal": "kirocrew-demo-client", "invocation_id": "service-id", "error_code": "tool_grant_denied"}
        event = {"type": "tool_call", "data": {"tool_call_id": "call-id", "input_preview": {"trace_id": trace}}}
        result = {"type": "tool_result", "data": {"tool_call_id": "call-id", "output": json.dumps(payload)}}
        audit = {"events": [payload]}
        rows = module.observations([event, result], audit, [], PREFIX)
        self.assertEqual(rows[2]["joined_native_service_results"], [payload])
        result["data"]["tool_call_id"] = "unrelated-call"
        self.assertEqual(module.observations([event, result], audit, [], PREFIX)[2]["joined_native_service_results"], [])

    def test_extra_tool_arguments_do_not_match(self):
        event = {"type": "tool_call", "data": {"tool_call_id": "call-id", "input_preview": {"trace_id": PREFIX + "-allow", "key": "other"}}}
        self.assertEqual(module.observations([event], {}, [], PREFIX)[0]["native_tool_call_ids"], [])

    def test_hook_block_requires_exact_trace_and_host_row(self):
        row = {"type": "chat_message", "data": {"role": "tool", "tool_call_id": "call-id", "content": "🚫 Blocked by security policy: @aws-enforcement/crew_denied", "meta": {"input": {"trace_id": PREFIX + "-crew"}}}}
        result = module.observations([row], {}, [], PREFIX)[1]
        self.assertEqual(result["native_blocked_tool_call_ids"], ["call-id"])
        self.assertNotIn("passed", result)
        self.assertNotIn("no_dispatch", result)

    def test_ingest_filters_other_slots_and_redacts(self):
        with tempfile.TemporaryDirectory() as directory:
            observer = module.Observer.__new__(module.Observer)
            observer.args = argparse.Namespace(slot="my-slot")
            observer.directory = Path(directory)
            observer.cleaner = module.native.Sanitizer()
            observer.cleaner.secrets.add("test-private-value")
            observer.events, observer.event_bytes = [], 0
            observer.permission_snapshots = set()
            asyncio.run(observer.ingest({"type": "chat_message", "data": {"slot": "another-slot", "content": "hidden"}}))
            self.assertFalse(observer.events)
            asyncio.run(observer.ingest({"type": "chat_message", "data": {"slot": "my-slot", "role": "assistant", "content": "test-private-value"}}))
            self.assertNotIn("test-private-value", (Path(directory) / "events.jsonl").read_text())
            self.assertIn("REDACTED", observer.events[0]["data"]["content"])

    def test_source_never_claims_acceptance_pass(self):
        self.assertNotIn('"passed": True', Path(module.__file__).read_text())
        self.assertIn('"acceptance": "not_evaluated"', Path(module.__file__).read_text())

    def test_finish_drain_consumes_queued_tool_result_before_quiet(self):
        # Fake only the enum import; no aiohttp dependency or transport starts.
        fake_aiohttp = argparse.Namespace(WSMsgType=argparse.Namespace(TEXT="text"))
        class Socket:
            count = 0
            async def receive(self, timeout):
                self.count += 1
                if self.count == 1:
                    return argparse.Namespace(type="text", data=json.dumps({"type": "tool_result", "data": {"slot": "mine", "output": "final"}}))
                raise asyncio.TimeoutError
        observer = module.Observer.__new__(module.Observer)
        received = []
        async def ingest(frame):
            received.append(frame)
        observer.ingest = ingest
        with patch.dict(sys.modules, {"aiohttp": fake_aiohttp}):
            asyncio.run(observer.drain(Socket(), quiet_seconds=0.001))
        self.assertEqual(received[0]["type"], "tool_result")

    def test_finish_drain_deadline_is_failure(self):
        fake_aiohttp = argparse.Namespace(WSMsgType=argparse.Namespace(TEXT="text"))
        observer = module.Observer.__new__(module.Observer)
        with patch.dict(sys.modules, {"aiohttp": fake_aiohttp}), self.assertRaises(module.native.DemoFailure):
            asyncio.run(observer.drain(None, quiet_seconds=1, max_seconds=0))

    def test_full_sel_baseline_retains_exact_anchor(self):
        baseline = [{"event_id": str(i), "outcome": "old"} for i in range(1000, 0, -1)]
        final = [{"event_id": "new2"}, {"event_id": "new1"}] + baseline[:998]
        interval, proof = module.sel_interval(module.sel_checkpoint(baseline), final)
        self.assertEqual([row["event_id"] for row in interval], ["new2", "new1"])
        self.assertTrue(proof["complete"])

    def test_sel_missing_anchor_never_establishes_complete_interval(self):
        checkpoint = module.sel_checkpoint([{"event_id": "anchor"}])
        for final in ([], [{"event_id": str(i)} for i in range(1000)]):
            with self.subTest(size=len(final)), self.assertRaisesRegex(module.native.DemoFailure, "not_retained"):
                module.sel_interval(checkpoint, final)

    def test_sel_changed_anchor_is_failure(self):
        checkpoint = module.sel_checkpoint([{"event_id": "anchor", "outcome": "denied"}])
        with self.assertRaisesRegex(module.native.DemoFailure, "anchor_changed"):
            module.sel_interval(checkpoint, [{"event_id": "anchor", "outcome": "allowed"}])

    def test_empty_baseline_full_final_page_is_ambiguous(self):
        checkpoint = module.sel_checkpoint([])
        self.assertTrue(module.sel_interval(checkpoint, [{"event_id": "one"}])[1]["complete"])
        with self.assertRaisesRegex(module.native.DemoFailure, "may_be_truncated"):
            module.sel_interval(checkpoint, [{"event_id": str(i)} for i in range(1000)])

    def test_duplicate_anchor_records_are_rejected(self):
        with self.assertRaisesRegex(module.native.DemoFailure, "duplicate_sel"):
            module.sel_checkpoint([{"event_id": "same"}, {"event_id": "same"}])

    def test_documented_purpose_metadata_is_display_correlated(self):
        trace = PREFIX + "-allow"
        self.assertTrue(module.displayed_trace_input({"trace_id": trace, "__tool_use_purpose": "Requested read"}, trace))
        self.assertFalse(module.displayed_trace_input({"trace_id": trace, "bucket": "other"}, trace))
        self.assertFalse(module.displayed_trace_input({"trace_id": trace, "__made_up_purpose": "anything"}, trace))
        self.assertFalse(module.displayed_trace_input({"trace_id": trace, "__tool_use_purpose": {"key": "other"}}, trace))

    def test_observed_approval_id_shape_matches_legacy_request_id(self):
        value = {"meta": {"approval_id": "approval-1", "tool_call_id": "tool-1"},
                 "cls": json.dumps({"request_id": "approval-1", "tool_call_id": "tool-1"})}
        self.assertEqual(module.permission_metadata(value)["request_id"], "approval-1")
        value["meta"]["approval_id"] = "different"
        with self.assertRaisesRegex(module.native.DemoFailure, "conflicting_permission"):
            module.permission_metadata(value)

    def test_observed_native_shape_joins_permission_and_service(self):
        trace = PREFIX + "-mcp"
        args = json.dumps({"trace_id": trace, "__tool_use_purpose": "User requested read"})
        events = [{"type": "tool_call", "data": {"tool_call_id": "call-1", "input_preview": args}},
                  {"type": "chat_message", "data": {"role": "permission", "meta": {"approval_id": "req-1", "tool_call_id": "call-1", "tool_input": args}}},
                  {"type": "tool_result", "data": {"tool_call_id": "call-1", "output": json.dumps({"trace_id": trace, "tool": "mcp_denied", "invocation_id": "inv-1", "principal": "kirocrew-demo-client"})}}]
        row = module.observations(events, {"events": [{"trace_id": trace, "invocation_id": "inv-1"}]}, [{"request_id": "req-1", "outcome": "approved"}], PREFIX)[2]
        self.assertEqual(row["permission_request_ids"], ["req-1"])
        self.assertEqual(row["native_tool_call_ids"], ["call-1"])
        self.assertEqual(len(row["joined_native_service_results"]), 1)

    def test_four_outcomes_reconcile_without_upgrading_full_acceptance(self):
        result = reconcile.analyze(*reconciliation_fixture())
        self.assertTrue(result["bounded_four_outcomes_reconciled"])
        self.assertEqual(len(result["phase_observations"]), 4)

    def test_mismatched_aws_request_id_rejects_reconciliation(self):
        receipt, events, scan = reconciliation_fixture()
        receipt["mcp_audit"]["events"][-1]["aws_request_id"] = "different"
        self.assertFalse(reconcile.analyze(receipt, events, scan)["bounded_four_outcomes_reconciled"])

    def test_wrong_service_identity_rejects_reconciliation(self):
        receipt, events, scan = reconciliation_fixture()
        receipt["mcp_audit"]["events"][0]["journal_invocation_id"] = "other-process"
        self.assertFalse(reconcile.analyze(receipt, events, scan)["bounded_four_outcomes_reconciled"])

    def test_extra_native_tool_call_rejects_reconciliation(self):
        receipt, events, scan = reconciliation_fixture()
        extra = copy.deepcopy(events[1]);extra["data"]["tool_call_id"] = "unrelated";extra["data"]["input_preview"] = "{}"
        events.insert(2, extra)
        self.assertFalse(reconcile.analyze(receipt, events, scan)["bounded_four_outcomes_reconciled"])

    def test_incomplete_sel_scan_never_reconciles_four_outcomes(self):
        receipt, events, scan = reconciliation_fixture();scan["scan_complete"] = False
        self.assertFalse(reconcile.analyze(receipt, events, scan)["bounded_four_outcomes_reconciled"])

    def test_remote_scan_has_no_write_or_runtime_import(self):
        tree = ast.parse(reconcile.REMOTE_SCAN)
        forbidden = {"write", "chmod", "chown", "unlink", "remove", "rename", "mkdir", "makedirs", "system"}
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(calls & forbidden)
        self.assertNotIn("import kiro_crew", reconcile.REMOTE_SCAN)


if __name__ == "__main__":
    unittest.main()
