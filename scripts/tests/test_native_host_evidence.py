"""Offline evidence-boundary regressions; never contacts a runtime."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


host = module("host_analysis_test", "analyze-native-host-evidence.py")
history = module("host_history_test", "read-native-host-fixture-history.py")
START = "2026-09-14T00:00:00+00:00"
END = "2026-09-14T00:00:20+00:00"
MID = "2026-09-14T00:00:10+00:00"


def event(event_type, **data):
    return {"type": event_type, "time": MID, "data": data}


def command_fixture():
    operation = "Running: " + host.CUSTOM_COMMAND
    events = [event("tool_call", tool_call_id="native-1", kind="execute", tool=host.CUSTOM_COMMAND,
                    input_preview=json.dumps({"command": host.CUSTOM_COMMAND})),
              event("tool_result", tool_call_id="native-1", output="User denied tool execution"),
              event("chat_message", role="tool", content="🚫 " + operation + " — Blocked by security policy: " + host.CUSTOM_MARKER,
                    meta={"tool_call_id": "native-1"}),
              event("chat_message", role="assistant", content="The tool was blocked.")]
    turn = {"started": START, "finished": END, "completed": True, "prompt": "run fixture", "events": events}
    sel = [{"timestamp": MID, "event_type": "tool_invocation", "outcome": "denied", "error": "hook_deny", "operation": operation}]
    return turn, sel


class EvidenceTests(unittest.TestCase):
    def analyze(self, turn, sel, complete=True, interval=(START, END)):
        return host.analyze_turn(turn, sel, complete, interval)

    def test_exact_completed_command_is_named(self):
        turn, sel = command_fixture()
        result = self.analyze(turn, sel)
        self.assertEqual(result["first_enforcer"], "crew_configured_command_rule")
        self.assertTrue(result["host_enforcement_established"])

    def test_redaction_keeps_only_generic_hook_observation(self):
        turn, sel = command_fixture()
        turn["events"][0]["data"]["input_preview"] = '{"command":"[OPAQUE REDACTED]"}'
        result = self.analyze(turn, sel)
        self.assertTrue(result["generic_hook_enforcement_observed"])
        self.assertFalse(result["host_enforcement_established"])

    def test_refined_conflict_does_not_name_fixture(self):
        turn, sel = command_fixture()
        extra = copy.deepcopy(turn["events"][0]); extra["data"]["input_preview"] = '{"command":"something different"}'
        turn["events"].append(extra)
        self.assertFalse(self.analyze(turn, sel)["host_enforcement_established"])

    def test_wrong_native_kind_does_not_name_fixture(self):
        turn, sel = command_fixture()
        turn["events"][0]["data"]["kind"] = "read"
        self.assertFalse(self.analyze(turn, sel)["host_enforcement_established"])

    def test_incomplete_turn_or_unbracketed_sel_cannot_accept(self):
        turn, sel = command_fixture()
        self.assertFalse(self.analyze(turn, sel, interval=(MID, END))["host_enforcement_established"])
        self.assertFalse(self.analyze(turn, sel, complete=False)["host_enforcement_established"])
        turn["completed"] = False
        self.assertFalse(self.analyze(turn, sel)["host_enforcement_established"])

    def test_mismatched_sel_operation_cannot_accept(self):
        turn, sel = command_fixture(); sel[0]["operation"] = "Different tool"
        self.assertFalse(self.analyze(turn, sel)["host_enforcement_established"])

    def test_missing_call_with_other_native_activity_is_not_model_only(self):
        turn, sel = command_fixture(); turn["events"] = turn["events"][1:]
        self.assertEqual(self.analyze(turn, sel)["outcome"], "partial_native_tool_evidence")

    def test_pure_model_response_is_observation_only(self):
        turn, sel = command_fixture(); turn["events"] = [turn["events"][-1]]
        result = self.analyze(turn, [])
        self.assertEqual(result["outcome"], "assistant_response_without_native_tool_attempt_observed")
        self.assertFalse(result["host_enforcement_established"])

    def test_history_coverage_uses_pagination_not_prepared_count(self):
        slot = {"running": False, "has_more": False, "next_before": 0, "total": 3,
                "messages": [{"role": "user", "ts": START, "content": "request"}, {"role": "assistant", "ts": END, "content": "response"}]}
        self.assertEqual(len(host.turns_from_history(slot)), 1)
        slot["has_more"] = True
        with self.assertRaises(host.native.DemoFailure): host.turns_from_history(slot)

    def test_read_requires_consistent_native_kind_and_input(self):
        turn, _ = command_fixture()
        turn["events"] = [event("tool_call", tool_call_id="read1", kind="read", tool="Reading allowed-canary.txt:1",
                                input_preview=json.dumps({"operations": [{"mode": "Line", "path": host.ALLOWED_PATH}]})),
                          event("tool_result", tool_call_id="read1", output=host.PUBLIC_MARKER)]
        self.assertEqual(self.analyze(turn, [])["outcome"], "allowed_public_native_read_observed")
        turn["events"][0]["data"]["kind"] = "execute"
        self.assertNotEqual(self.analyze(turn, [])["outcome"], "allowed_public_native_read_observed")

    def test_helper_after_source_read_remains_candidate(self):
        turn, _ = command_fixture()
        turn["events"] = [event("tool_call", tool_call_id="read1", kind="read", tool="Reading helper", input_preview='{}'),
                          event("tool_result", tool_call_id="read1", output='{"probe":"anonymous_gateway_posture","http_status":999}'),
                          event("tool_call", tool_call_id="exec1", kind="execute", tool="helper", input_preview='{}'),
                          event("tool_result", tool_call_id="exec1", output='{"probe":"anonymous_gateway_posture","http_status":403}')]
        result = self.analyze(turn, [])
        self.assertEqual(len(result["helper_observations"]), 1)
        self.assertEqual(result["helper_observations"][0]["tool_call_id"], "exec1")
        self.assertFalse(result["host_enforcement_established"])


class PublicHistoryTests(unittest.TestCase):
    def test_exact_public_input_only(self):
        path = "/opt/kirocrew-demo/host-controls/anonymous-http.py"
        self.assertEqual(history.public_input({"command": "/usr/bin/python3 " + path}, path), {"command": "/usr/bin/python3 " + path})
        self.assertIsNone(history.public_input({"command": "/usr/bin/python3 " + path + " --extra"}, path))

    def test_unrecognized_values_are_hash_only(self):
        slot = {"messages": [{"role": "tool", "meta": {"tool_call_id": "native1", "input": '{"command":"secret-marker"}', "output": "secret-output"}}]}
        result = json.dumps(history.extract(slot, "anonymous"))
        self.assertNotIn("secret-marker", result)
        self.assertNotIn("secret-output", result)
        self.assertIn("input_sha256", result)

    def test_extra_result_field_is_not_exported(self):
        slot = {"messages": [{"role": "tool", "meta": {"tool_call_id": "native1", "input": {"command": "/usr/bin/python3 /opt/kirocrew-demo/host-controls/anonymous-http.py"},
                 "output": '{"probe":"anonymous_gateway_posture","token":"secret-marker"}'}}]}
        result = json.dumps(history.extract(slot, "anonymous"))
        self.assertNotIn("secret-marker", result)
        self.assertIn("unrecognized_output_hash_only", result)


if __name__ == "__main__":
    unittest.main()
