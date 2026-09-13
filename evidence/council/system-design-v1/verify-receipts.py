#!/usr/bin/env python3
"""Verify completed review evidence without model calls or source changes."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json


BASE = Path(__file__).resolve().parent
DISPATCH = BASE / "candidate" / "dispatch"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    prepared = json.loads((BASE / "candidate" / "prepared.json").read_text())
    binding = json.loads((BASE / "dispatch-binding.json").read_text())
    runner_path = BASE / "run-council.py"
    require(sha(runner_path) == binding["runner"]["sha256"], "runner changed since dispatch")
    spec = importlib.util.spec_from_file_location("council_verifier", runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    packet = Path(prepared["packet"])
    manifest = runner.verify_packet(packet, prepared["manifest_sha256"])
    files = []
    for entry in manifest["files"]:
        source = Path(prepared["sources"][entry["name"]])
        files.append({**entry, "source_matches": sha(source) == entry["sha256"]})
    require(all(e["source_matches"] for e in files), "source changed during review")
    council = json.loads((DISPATCH / "council-receipt.json").read_text())
    require(council["manifest_sha256"] == prepared["manifest_sha256"], "council binding mismatch")
    require(council["council_review_evidence_complete"], "council incomplete")
    reviewers = {}
    required_reads = {"manifest.json", "notes.md", "evidence-summary.md"} | set(runner.SLIDE_NAMES)
    for who, model in runner.MODELS.items():
        receipt = json.loads((DISPATCH / f"{who}-receipt.json").read_text())
        launch = json.loads((DISPATCH / f"{who}-launch.json").read_text())
        for key, suffix in (("raw_stdout_sha256", "raw.jsonl"), ("raw_stderr_sha256", "stderr.txt"), ("launch_sha256", "launch.json")):
            require(receipt[key] == sha(DISPATCH / f"{who}-{suffix}"), f"{who} {key} mismatch")
        require(sha(DISPATCH / f"{who}-launch.json") == binding["launch_hashes"][who], "launch changed")
        effort_flag = "--reasoning-effort" if who == "grok" else "--effort"
        require(launch["requested_model"] == model and launch["requested_effort"] == "xhigh", "wrong requested identity")
        require(launch["argv"][launch["argv"].index(effort_flag) + 1] == "xhigh", "wrong effort flag")
        require(launch["cwd"] == str(packet), "wrong packet cwd")
        parsed = runner.analyze_stream(DISPATCH / f"{who}-raw.jsonl", who, packet)
        require(parsed["exact_response_model_verified"] and parsed["all_fourteen_exact_jpeg_payloads_verified"], "model or image mismatch")
        require(parsed["terminal_success"] and parsed["terminal_result_count"] == 1 and parsed["review_text_present"] and not parsed["stream_errors"], "failed terminal review")
        require(receipt["exit_code"] == 0 and not receipt["failure"] and receipt["review_evidence_complete"], "incomplete dispatch")
        require((DISPATCH / f"{who}-review.md").read_text() == parsed["review_text"] + "\n", "review extraction mismatch")
        calls = []
        for line in (DISPATCH / f"{who}-raw.jsonl").read_text().splitlines():
            frame = json.loads(line)
            message = frame.get("message", {})
            if not isinstance(message, dict):
                continue
            for block in message.get("content", []):
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                require(block.get("name") == ("read_file" if who == "grok" else "Read"), "unexpected tool")
                arg = block.get("input", {})
                target = arg.get("file_path") or arg.get("target_file") or arg.get("path")
                require(isinstance(target, str), "missing read path")
                target = Path(target) if Path(target).is_absolute() else packet / target
                require(target.parent == packet and target.name in required_reads | {"presentation.html"}, "read outside packet")
                calls.append({"tool": block["name"], "file": target.name})
        require(required_reads <= {c["file"] for c in calls}, "missing requested source/image read")
        evidence_files = [f"{who}-{suffix}" for suffix in ("receipt.json", "launch.json", "raw.jsonl", "stderr.txt", "review.md")]
        reviewers[who] = {"requested_model": model, "requested_effort": "xhigh", "effort_verification": launch["effort_verification"], "response_model_ids": parsed["response_model_ids"], "usage_model_ids": parsed["usage_model_ids"], "all_fourteen_exact_jpeg_payloads_verified": True, "image_reads": parsed["image_reads"], "observed_tool_calls": calls, "terminal_success": True, "exit_code": 0, "duration_seconds": receipt["duration_seconds"], "artifact_hashes": {name: sha(DISPATCH / name) for name in evidence_files}, "review_evidence_complete": True}
    output = BASE / "council-verified-receipt.json"
    require(not output.exists(), "fresh verification output required")
    result = {"schema": 1, "verified_utc": datetime.now(timezone.utc).isoformat(), "candidate": prepared["candidate"], "candidate_source": prepared["sources"]["presentation.html"], "candidate_html_sha256": next(e["sha256"] for e in files if e["name"] == "presentation.html"), "manifest_sha256": prepared["manifest_sha256"], "packet": str(packet), "packet_and_sources_unchanged": True, "file_checks": files, "reviewers": reviewers, "runner_sha256": sha(runner_path), "raw_council_receipt_sha256": sha(DISPATCH / "council-receipt.json"), "inference_started_by_verification": False, "decisions_incorporated_by_this_task": False, "no_ai_slop_pass_by_this_task": False, "limitations": ["Provider-internal effort is not independently visible; xhigh launch flags are verified.", "Usage accounting may contain aliases or helper models; exact observed review response models are separately recorded.", "Reviewers read frozen screenshots, notes and a sanitized evidence summary. They did not verify interactive browser behavior or live AWS/runtime state.", "New presentation bytes after incorporation are outside this frozen-candidate review."]}
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"receipt": str(output), "candidate_html_sha256": result["candidate_html_sha256"], "review_evidence_complete": True}))


if __name__ == "__main__":
    main()
