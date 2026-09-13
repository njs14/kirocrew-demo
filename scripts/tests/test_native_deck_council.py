import argparse
import base64
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("native_deck_council", ROOT / "scripts/run-native-deck-council.py")
council = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(council)
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6SAAAAABJRU5ErkJggg==")


class NativeCouncilTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.packets = self.root / "packets"
        self.packets.mkdir()
        self.addCleanup(patch.stopall)
        patch.object(council, "packet_root", return_value=self.packets).start()
        self.popen = patch.object(council.subprocess, "Popen", side_effect=AssertionError("offline test must not dispatch inference")).start()

    def make_sources(self, count=10, padded=True):
        deck = self.sources / "deck.html"
        deck.write_text("<!doctype html><html><head><title>Demo</title></head><body><main id='deck'>" + "".join(
            f"<section class='slide' id='slide-{i}'><h1>Control {i}</h1></section>" for i in range(1, count + 1)
        ) + "</main></body></html>")
        notes, evidence = self.sources / "notes.md", self.sources / "evidence.md"
        notes.write_text("Native control narrative and notes.")
        evidence.write_text("Exact native evidence; playback is a separate operator check.")
        slides = self.sources / "slides"
        slides.mkdir()
        rows = []
        for i in range(1, count + 1):
            name = f"slide-{i:02d}.png" if padded else f"slide-{i}.png"
            # PNG fixture bytes remain immutable. It tests receipt matching, not browser rendering.
            path = slides / name
            path.write_bytes(PNG)
            rows.append({"number": i, "file": name, "sha256": council.digest(path)})
        capture = self.sources / "capture.json"
        capture.write_text(json.dumps({"deck_sha256": council.digest(deck), "slide_count": count,
                                      "slides": rows, "capture_method": "offline fixture, no live rendering"}))
        return argparse.Namespace(candidate="test-candidate", deck=str(deck), notes=str(notes),
                                  evidence=str(evidence), slides=str(slides), capture_receipt=str(capture),
                                  slide_count=count, output=str(self.root / "review"))

    def prepare(self, args=None):
        args = args or self.make_sources()
        with redirect_stdout(io.StringIO()):
            council.prepare(args)
        prepared = json.loads((Path(args.output) / "prepared.json").read_text())
        # Temporary directory cleanup must be able to remove the frozen packet.
        packet = Path(prepared["packet"])
        self.addCleanup(packet.chmod, 0o700)
        return args, prepared, packet

    def test_prepare_freezes_exact_ten_pngs_and_never_dispatches(self):
        args, prepared, packet = self.prepare()
        manifest = council.verify_packet(packet, prepared["manifest_sha256"])
        self.assertEqual(manifest["slide_count"], 10)
        self.assertEqual(len(list(packet.iterdir())), 15)
        self.assertEqual(council.digest(packet / "presentation.html"), council.digest(Path(args.deck)))
        self.assertFalse(prepared["inference_started"])
        self.assertEqual((packet / "slide-10.png").read_bytes(), PNG)
        self.assertEqual(packet.stat().st_mode & 0o777, 0o500)
        self.assertEqual((packet / "slide-1.png").stat().st_mode & 0o777, 0o400)
        self.popen.assert_not_called()

    def test_unpadded_names_supported(self):
        self.prepare(self.make_sources(count=2, padded=False))

    def test_missing_extra_and_ambiguous_png_rejected(self):
        args = self.make_sources()
        first = Path(args.slides) / "slide-01.png"
        first.unlink()
        with self.assertRaisesRegex(ValueError, "exactly one"):
            council.prepare(args)
        first.write_bytes(PNG)
        extra = Path(args.slides) / "slide-11.png"
        extra.write_bytes(PNG)
        with self.assertRaisesRegex(ValueError, "extra numbered"):
            council.prepare(args)
        extra.unlink()
        (Path(args.slides) / "slide-1.png").write_bytes(PNG)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            council.prepare(args)

    def test_linked_png_and_linked_html_rejected(self):
        args = self.make_sources()
        first = Path(args.slides) / "slide-01.png"
        first.unlink()
        first.symlink_to(Path(args.slides) / "slide-02.png")
        with self.assertRaisesRegex(ValueError, "linked"):
            council.prepare(args)
        first.unlink()
        first.write_bytes(PNG)
        linked = self.sources / "link.html"
        linked.symlink_to(args.deck)
        args.deck = str(linked)
        with self.assertRaisesRegex(ValueError, "linked"):
            council.prepare(args)

    def test_html_count_duplicate_and_commented_slide_rejected(self):
        args = self.make_sources()
        path = Path(args.deck)
        text = path.read_text()
        with self.assertRaisesRegex(ValueError, "exactly 9"):
            council.validate_html_deck(path, 9)
        path.write_text(text.replace("id='slide-10'", "id='slide-9'"))
        with self.assertRaisesRegex(ValueError, "ordered slide"):
            council.validate_html_deck(path, 10)
        path.write_text(text.replace("<section class='slide' id='slide-10'>", "<!-- <section class='slide' id='slide-10'>").replace("<h1>Control 10</h1></section>", "<h1>Control 10</h1></section> -->"))
        with self.assertRaisesRegex(ValueError, "ordered slide"):
            council.validate_html_deck(path, 10)

    def test_stale_capture_deck_and_image_hashes_rejected(self):
        args = self.make_sources()
        path = Path(args.capture_receipt)
        binding = json.loads(path.read_text())
        binding["deck_sha256"] = "0" * 64
        path.write_text(json.dumps(binding))
        with self.assertRaisesRegex(ValueError, "this HTML"):
            council.prepare(args)
        binding["deck_sha256"] = council.digest(Path(args.deck))
        binding["slides"][-1]["sha256"] = "0" * 64
        path.write_text(json.dumps(binding))
        with self.assertRaisesRegex(ValueError, "slide-10.png"):
            council.prepare(args)

    def test_secret_in_text_or_decoded_html_asset_rejected(self):
        # Construct at runtime so the source does not resemble a secret itself.
        secret = "AKIA" + "X" * 16
        with self.assertRaisesRegex(ValueError, "credential"):
            council.scan_html_secrets("<p>" + secret + "</p>")
        encoded = base64.b64encode(json.dumps({"id": secret}).encode()).decode()
        with self.assertRaisesRegex(ValueError, "credential"):
            council.scan_html_secrets(f'<a href="data:application/json;base64,{encoded}">Data</a>')
        with self.assertRaisesRegex(ValueError, "unsupported embedded MIME"):
            council.scan_html_secrets('<img src="data:application/octet-stream;base64,YWJj">')

    def test_quoted_credential_fields_in_auxiliary_inputs_rejected(self):
        args = self.make_sources()
        for field in ("aws_secret_access_key", "aws_session_token"):
            Path(args.evidence).write_text(json.dumps({field: "example-redacted-fixture-only-123456"}))
            with self.assertRaisesRegex(ValueError, "possible credential"):
                council.prepare(args)

    def test_packet_changes_extra_files_and_wrong_manifest_rejected(self):
        args, prepared, packet = self.prepare()
        with self.assertRaisesRegex(ValueError, "manifest hash"):
            council.verify_packet(packet, "0" * 64)
        packet.chmod(0o700)
        extra = packet / "extra.txt"
        extra.write_text("unreviewed")
        with self.assertRaisesRegex(ValueError, "only frozen"):
            council.verify_packet(packet, prepared["manifest_sha256"])
        extra.unlink()
        image = packet / "slide-10.png"
        image.chmod(0o600)
        image.write_bytes(PNG + b"changed")
        with self.assertRaisesRegex(ValueError, "packet changed"):
            council.verify_packet(packet, prepared["manifest_sha256"])

    def test_source_change_blocks_model_dispatch(self):
        args, prepared, packet = self.prepare()
        Path(args.deck).write_text(Path(args.deck).read_text() + "<!-- changed -->")
        run = argparse.Namespace(prepared=str(Path(args.output) / "prepared.json"),
                                 confirm_manifest=prepared["manifest_sha256"], attempt="dispatch",
                                 reviewer="both", timeout=30)
        with self.assertRaisesRegex(ValueError, "source changed"):
            council.run(run)
        self.popen.assert_not_called()

    def test_fresh_output_and_packet_required(self):
        args, prepared, packet = self.prepare()
        with self.assertRaisesRegex(FileExistsError, "fresh output"):
            council.prepare(args)
        args.output = str(self.root / "another-output")
        with self.assertRaisesRegex(FileExistsError, "fresh packet"):
            council.prepare(args)

    def test_manifest_confirmation_required_before_dispatch(self):
        args, prepared, packet = self.prepare()
        run = argparse.Namespace(prepared=str(Path(args.output) / "prepared.json"),
                                 confirm_manifest="0" * 64, attempt="dispatch",
                                 reviewer="both", timeout=30)
        with self.assertRaisesRegex(ValueError, "confirmation"):
            council.run(run)
        self.popen.assert_not_called()

    def test_clean_environment_and_exact_strict_launch_policy_reused(self):
        with patch.dict(os.environ, {"AWS_SECRET_ACCESS_KEY": "unrelated", "ANTHROPIC_API_KEY": "unrelated", "XAI_API_KEY": "unrelated", "GITHUB_TOKEN": "unrelated"}):
            env = council.clean_env()
        for key in ("AWS_SECRET_ACCESS_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY", "GITHUB_TOKEN"):
            self.assertNotIn(key, env)
        self.assertEqual(env["GROK_MANAGED_MCPS_ENABLED"], "0")
        with patch.object(council._BASE, "reviewer_executable", side_effect=lambda name: "/cli/" + name):
            for reviewer in council.MODELS:
                command = council.command_for(reviewer, Path("/tmp/packet"), "prompt")
                self.assertEqual(command, council._BASE.command_for(reviewer, Path("/tmp/packet"), "prompt"))
                self.assertIn(council.MODELS[reviewer], command)
                self.assertIn("xhigh", command)
                self.assertIn("dontAsk", command)
        prompt = council.prompt_for("frozen", "0" * 64, 10)
        self.assertIn("slide-10.png", prompt)
        self.assertNotIn("slide-11.png", prompt)
        self.assertIn("current directory", prompt)

    def stream(self, packet, reviewer, *, missing=None, wrong_payload=None, model=None, terminal_error=False, extra_terminal=False, read_error=None):
        events = []
        for i in range(1, 11):
            if missing == i:
                continue
            name = f"slide-{i}.png"
            events.append({"type": "assistant", "message": {"model": model or council.MODELS[reviewer], "content": [
                {"type": "tool_use", "name": "Read" if reviewer == "claude" else "read_file", "id": f"read-{i}", "input": {"file_path": str(packet / name)}}]}})
            data = PNG + b"mismatch" if wrong_payload == i else PNG
            events.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"read-{i}",
                "is_error": read_error == i, "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(data).decode()}}]}]}})
        terminal = {"type": "result", "subtype": "error" if terminal_error else "success", "is_error": terminal_error,
                    "result": "CHANGES REQUIRED. Exact review text.", "modelUsage": {"usage-alias": {}}}
        events.append(terminal)
        if extra_terminal:
            events.append(terminal)
        path = self.root / f"{reviewer}.jsonl"
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
        return path

    def test_all_ten_exact_payloads_and_response_models_verified(self):
        _, _, packet = self.prepare()
        for reviewer in council.MODELS:
            result = council.analyze_stream(self.stream(packet, reviewer), reviewer, packet)
            self.assertTrue(result["all_exact_png_payloads_verified"])
            self.assertEqual(len(result["image_reads"]), 10)
            self.assertTrue(result["exact_response_model_verified"])
            self.assertEqual(result["usage_model_ids"], ["usage-alias"])
            self.assertTrue(result["terminal_success"])

    def test_missing_mismatched_and_failed_tenth_image_not_complete(self):
        _, _, packet = self.prepare()
        for reviewer in council.MODELS:
            for kwargs in ({"missing": 10}, {"wrong_payload": 10}, {"read_error": 10}):
                result = council.analyze_stream(self.stream(packet, reviewer, **kwargs), reviewer, packet)
                self.assertFalse(result["all_exact_png_payloads_verified"])

    def test_wrong_model_and_nonunique_or_error_terminal_not_complete(self):
        _, _, packet = self.prepare()
        for reviewer in council.MODELS:
            result = council.analyze_stream(self.stream(packet, reviewer, model="different-model"), reviewer, packet)
            self.assertFalse(result["exact_response_model_verified"])
            for kwargs in ({"terminal_error": True}, {"extra_terminal": True}):
                result = council.analyze_stream(self.stream(packet, reviewer, **kwargs), reviewer, packet)
                self.assertFalse(result["terminal_success"])

    def test_explicit_error_terminal_cannot_be_overridden_by_end_turn(self):
        _, _, packet = self.prepare()
        path = self.stream(packet, "grok")
        events = [json.loads(line) for line in path.read_text().splitlines()]
        events[-1].update(subtype="error_max_turns", stop_reason="end_turn")
        path.write_text("\n".join(json.dumps(event) for event in events))
        result = council.analyze_stream(path, "grok", packet)
        self.assertFalse(result["terminal_success"])

    def make_completed_fixture(self, args, prepared, packet, malformed=False):
        directory = Path(args.output) / "dispatch"
        directory.mkdir()
        prompt = council.prompt_for(prepared["candidate"], prepared["manifest_sha256"], 10)
        (directory / "prompt.txt").write_text(prompt)
        for reviewer in council.MODELS:
            raw = directory / f"{reviewer}-raw.jsonl"
            raw.write_text(self.stream(packet, reviewer).read_text() + ("malformed event\n" if malformed else ""))
            stderr = directory / f"{reviewer}-stderr.txt"
            stderr.write_text("")
            launch = directory / f"{reviewer}-launch.json"
            launch.write_text(json.dumps({"requested_model": council.MODELS[reviewer], "requested_effort": "xhigh",
                "cwd": str(packet), "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "runner_sha256": prepared["runner_sha256"], "launch_policy_sha256": prepared["launch_policy_sha256"],
                "effort_verification": "offline fixture"}))
            (directory / f"{reviewer}-receipt.json").write_text(json.dumps({
                "raw_stdout_sha256": council.digest(raw), "raw_stderr_sha256": council.digest(stderr),
                "launch_sha256": council.digest(launch), "exit_code": 0, "failure": None,
                "sandbox_warning_observed": False}))
        return argparse.Namespace(prepared=str(Path(args.output) / "prepared.json"), grok_attempt="dispatch",
                                  claude_attempt="dispatch", output=str(self.root / "assessment.json"))

    def test_assessment_detects_malformed_evidence_without_inference(self):
        args, prepared, packet = self.prepare()
        assess = self.make_completed_fixture(args, prepared, packet, malformed=True)
        with redirect_stdout(io.StringIO()):
            council.assess(assess)
        receipt = json.loads(Path(assess.output).read_text())
        self.assertFalse(receipt["council_review_evidence_complete"])
        for review in receipt["reviewers"].values():
            self.assertEqual(review["non_json_lines"], 1)
        self.popen.assert_not_called()

    def test_assessment_detects_prompt_change_without_inference(self):
        args, prepared, packet = self.prepare()
        assess = self.make_completed_fixture(args, prepared, packet)
        (Path(args.output) / "dispatch/prompt.txt").write_text("Changed review task")
        with self.assertRaisesRegex(ValueError, "review prompt"):
            council.assess(assess)
        self.popen.assert_not_called()

    def test_assessment_joins_exact_original_receipts_without_inference(self):
        args, prepared, packet = self.prepare()
        assess = self.make_completed_fixture(args, prepared, packet)
        with redirect_stdout(io.StringIO()):
            council.assess(assess)
        receipt = json.loads(Path(assess.output).read_text())
        self.assertTrue(receipt["council_review_evidence_complete"])
        self.assertFalse(receipt["inference_started_by_assessment"])
        self.popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
