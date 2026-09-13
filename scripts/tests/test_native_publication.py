"""Publication regressions: no broad SEL, transcript, or auth fingerprints."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "native_publication", Path(__file__).resolve().parents[1] / "export-native-publication.py")
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)


def fixture(kind="passive_native_client_evidence"):
    return {
        "kind": kind, "run_id": "native-publication-demo", "slot": "chat-demo",
        "captured_events": 0, "collection_complete": False,
        "started": "2026-09-13T21:00:00Z", "stream_finished": "2026-09-13T21:05:00Z",
        "sel_before": [{"caller_identity": "someone-else", "error": "expected=1234abcd received=8765abcd",
                        "private_key": "DO NOT EXPORT"}],
        "sel_after": [{"caller_identity": "dashboard:chat-demo", "error": "private context"}],
        "new_sel_interval": [{"caller_identity": "someone-else", "operation": "PRIVATE SENTINEL"}],
        "new_session_sel": [],
        "slot_before": {"running": False, "messages": [{"content": "PRIVATE TRANSCRIPT"}]},
        "slot_after": {"running": False, "messages": [], "total": 0},
        "sel_integrity_after": {"integrity": "ok", "total": 5, "valid": 5, "tampered": 0,
                                "detail": "expected=1234abcd received=8765abcd"},
        "mcp_service_before": {"ActiveState": "active", "SubState": "running", "MainPID": "123",
                               "InvocationID": "test-invocation", "NRestarts": "0", "environment": "PRIVATE ENV"},
        "service_stable": True,
        "mcp_audit": {"collection_succeeded": True, "events": [
            {"event": "tool_decision", "tool": "read_allowed", "trace_id": "native-publication-demo-allow",
             "invocation_id": "one", "outcome": "allowed", "unknown_payload": "PRIVATE TOOL DATA"},
            {"event": "tool_decision", "trace_id": "unrelated-allow", "tool": "PRIVATE OTHER TOOL"},
        ]},
        "unknown_future_field": {"credential": "PRIVATE FUTURE DATA"},
    }


class PublicationTests(unittest.TestCase):
    def project(self, value=None, event_bytes=None):
        value = fixture() if value is None else value
        raw = json.dumps(value).encode()
        return exporter.project(value, raw, "receipt.json", event_bytes), raw

    def test_broad_sel_and_transcripts_are_omitted(self):
        result, _ = self.project()
        text = json.dumps(result)
        self.assertNotIn("expected=", text)
        self.assertNotIn("received=", text)
        self.assertNotIn("PRIVATE", text)
        for key in ("sel_before", "sel_after", "new_sel_interval", "slot_before", "slot_after"):
            self.assertNotIn(key, result)
        self.assertEqual(result["private_sel_counts"]["sel_before"],
                         {"total": 1, "target_session": 0, "other_callers": 1})
        self.assertEqual(result["conversation_summary"]["slot_before"]["captured_message_count"], 1)

    def test_source_hash_binds_original_unmodified_bytes(self):
        value = fixture()
        previous = copy.deepcopy(value)
        result, raw = self.project(value)
        self.assertEqual(value, previous)
        self.assertEqual(result["private_source"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["private_source"]["retention"], "privately_retained_ignored")

    def test_analyzer_fields_retained_with_only_run_audit_events(self):
        result, _ = self.project()
        for key in ("run_id", "slot", "stream_finished", "mcp_audit", "mcp_service_before",
                    "service_stable", "sel_integrity_after"):
            self.assertIn(key, result)
        self.assertEqual(len(result["mcp_audit"]["events"]), 1)
        self.assertEqual(result["mcp_audit"]["publication_scope"]["omitted_other_trace_count"], 1)
        self.assertTrue(result["mcp_audit"]["collection_succeeded"])
        self.assertNotIn("unknown_payload", result["mcp_audit"]["events"][0])

    def test_scoped_sel_rejects_other_caller(self):
        value = fixture()
        value["new_session_sel"] = [{"caller_identity": "dashboard:another-chat"}]
        with self.assertRaisesRegex(ValueError, "caller mismatch"):
            self.project(value)

    def test_auth_fingerprint_in_selected_field_fails_closed(self):
        value = fixture()
        value["failure"] = "expected=1234abcd received=8765abcd"
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.project(value)

    def test_credential_assignment_in_selected_string_fails_closed(self):
        value = fixture()
        value["failure"] = "password=private-placeholder-for-regression"
        with self.assertRaisesRegex(ValueError, "credential"):
            self.project(value)

    def test_nested_future_value_in_scalar_allowlist_is_rejected(self):
        value = fixture()
        value["failure"] = {"unexpected": "private"}
        with self.assertRaisesRegex(ValueError, "scalar"):
            self.project(value)

    def test_native_events_are_bound_and_must_match_slot(self):
        good = json.dumps({"type": "chat_message", "data": {"slot": "chat-demo", "content": "public fixture"}}).encode()
        result, _ = self.project(event_bytes=good)
        self.assertEqual(result["native_events"]["sha256"], hashlib.sha256(good).hexdigest())
        self.assertEqual(result["native_events"]["events"], 1)
        bad = good.replace(b"chat-demo", b"chat-other")
        with self.assertRaisesRegex(ValueError, "slot mismatch"):
            self.project(event_bytes=bad)

    def test_sensitive_native_event_field_is_rejected(self):
        events = json.dumps({"data": {"slot": "chat-demo", "access_token": "private"}}).encode()
        with self.assertRaisesRegex(ValueError, "sensitive field"):
            self.project(event_bytes=events)

    def test_missing_nonzero_event_file_is_rejected(self):
        value = fixture()
        value["captured_events"] = 1
        with self.assertRaisesRegex(ValueError, "missing captured"):
            self.project(value)

    def test_zero_event_note_does_not_direct_reader_to_missing_file(self):
        result, _ = self.project()
        self.assertIn("no events.jsonl", result["publication_notes"][3])
        self.assertIn("capture-status.json when present", result["publication_notes"][3])
        self.assertNotIn("Use the scoped native events.jsonl", result["publication_notes"][3])

    def test_source_kind_must_match_filename(self):
        value = fixture("passive_native_client_baseline")
        with self.assertRaisesRegex(ValueError, "kind does not match"):
            self.project(value)

    def test_baseline_event_link_is_explicitly_later_companion(self):
        value = fixture("passive_native_client_baseline")
        events = json.dumps({"data": {"slot": "chat-demo", "content": "public"}}).encode()
        result = exporter.project(value, json.dumps(value).encode(), "baseline.json", events)
        self.assertEqual(result["native_events"]["relationship"],
                         "later same-run companion; not baseline-time evidence")

    def test_run_pair_identity_mismatch_writes_nothing(self):
        for field in ("run_id", "slot"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "baseline.json").write_text(json.dumps(fixture("passive_native_client_baseline")))
                value = fixture()
                value[field] += "-other"
                (root / "receipt.json").write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, "identity mismatch"):
                    exporter.export_run(root)
                self.assertEqual(list(root.glob("*-publication.json")), [])

    def test_export_is_fresh_and_preserves_both_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            originals = {}
            for name, kind in (("baseline.json", "passive_native_client_baseline"),
                               ("receipt.json", "passive_native_client_evidence")):
                originals[name] = json.dumps(fixture(kind)).encode()
                (root / name).write_bytes(originals[name])
            exports = exporter.export_run(root)
            self.assertEqual(len(exports), 2)
            for name, raw in originals.items():
                self.assertEqual((root / name).read_bytes(), raw)
                self.assertTrue((root / name.replace(".json", "-publication.json")).is_file())
            with self.assertRaisesRegex(ValueError, "fresh"):
                exporter.export_run(root)

    def test_source_and_destination_symlinks_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real.json").write_text(json.dumps(fixture()))
            (root / "baseline.json").symlink_to(root / "real.json")
            with self.assertRaises(OSError):
                exporter.export_run(root)
            (root / "baseline.json").unlink()
            (root / "baseline.json").write_text(json.dumps(fixture("passive_native_client_baseline")))
            (root / "receipt.json").write_text(json.dumps(fixture()))
            (root / "receipt-publication.json").symlink_to(root / "does-not-exist")
            with self.assertRaisesRegex(ValueError, "fresh"):
                exporter.export_run(root)
            self.assertFalse((root / "baseline-publication.json").exists())


if __name__ == "__main__":
    unittest.main()
