#!/usr/bin/env python3
"""Publish scoped derivatives of private passive-collector snapshots.

Original files are never rewritten. The exported receipt retains the inputs
used by the existing offline four-outcome analyzer, while the broad SEL pages
and conversation snapshots remain private. This command performs no network,
authentication, runtime or policy operations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_BYTES = 32_000_000
SLOT = re.compile(r"[A-Za-z0-9][A-Za-z0-9:_.-]{0,159}\Z")
RUN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{6,65}\Z")
SECRET = re.compile(
    r"(?:expected|received)=[a-f0-9]{8}\b|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|"
    r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b|"
    r"-----BEGIN [^-\r\n]*PRIVATE KEY-----|"
    r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b|"
    r"(?:aws_secret_access_key|aws_session_token|access_token|refresh_token|password|api[_-]?key)"
    r"[\"']?\s*[:=]\s*[\"']?[^\s\"']{12,}|"
    r"https?://[^\s\"<>]+[?&](?:token|access_token|refresh_token|user_code)=[^\s\"<>]+",
    re.IGNORECASE,
)
SCALAR_FIELDS = (
    "acceptance", "captured_events", "collection_complete", "collector_sha256",
    "helper_sha256", "finish_requested_at", "finished", "started", "stream_finished",
    "stream_quiet_interval_seconds", "ready_at", "service_stable", "failure",
)
SERVICE_FIELDS = ("ActiveState", "SubState", "MainPID", "NRestarts", "InvocationID")
AUDIT_FIELDS = (
    "aws_request_id", "error_code", "event", "http_status", "invocation_id",
    "journal_cursor", "journal_invocation_id", "journal_timestamp_us", "layer",
    "object_bytes", "object_sha256", "outcome", "principal", "service", "time",
    "tool", "trace_id",
)
PROCESS_FIELDS = ("comm", "cwd", "exe", "pid", "ppid", "uid")
SEL_FIELDS = (
    "event_id", "timestamp", "event_type", "caller_identity", "request_id", "outcome",
    "error", "source", "agent", "operation", "resources", "tool_kind", "entry_hash", "prev_hash",
)
NOTES = [
    "The hash-bound original snapshot is privately retained and excluded from Git; its bytes were not changed.",
    "Broad SEL pages, their error details and complete conversation snapshots are omitted by an explicit field allowlist.",
    "SEL summary counts describe the private source, not additional exported event evidence.",
    "Use the scoped native events.jsonl and separately recovered SEL interval for offline outcome analysis.",
    "This export is a publication boundary, not a new collection, integrity verification or enforcement acceptance verdict.",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BYTES, "invalid source type or size")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(MAX_BYTES + 1)
        require(len(data) <= MAX_BYTES, "source size limit")
        return data
    finally:
        os.close(fd)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fields(value, names):
    require(isinstance(value, dict), "expected an object")
    selected = {key: value[key] for key in names if key in value}
    require(all(item is None or type(item) in (str, int, float, bool) for item in selected.values()),
            "allowlisted leaf must be scalar")
    return selected


def rows(value):
    require(isinstance(value, list) and len(value) <= 20000 and all(isinstance(x, dict) for x in value),
            "invalid bounded event list")
    return value


def check_publishable(value):
    """Defense in depth after projection; fail closed, never print a match."""
    text = json.dumps(value, sort_keys=True)
    require(not SECRET.search(text), "possible credential or authentication fingerprint in selected evidence")
    def walk(item):
        if isinstance(item, dict):
            for key, child in item.items():
                require(not re.search(r"(?i)(?:password|authorization|cookie|access_token|refresh_token|"
                                      r"secret_access_key|session_token|api[_-]?key|private[_-]?key)", key),
                        "sensitive field in selected evidence")
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)
    walk(value)


def project(source, source_bytes, source_name, event_bytes=None):
    require(isinstance(source, dict), "source must be an object")
    kinds = {"baseline.json": "passive_native_client_baseline", "receipt.json": "passive_native_client_evidence"}
    require(source_name in kinds, "unsupported source filename")
    require(source.get("kind") == kinds[source_name], "collector kind does not match source filename")
    slot, run = source.get("slot"), source.get("run_id")
    require(isinstance(slot, str) and SLOT.fullmatch(slot), "invalid source slot")
    require(isinstance(run, str) and RUN.fullmatch(run), "invalid source run")
    caller = "dashboard:" + slot.removeprefix("dashboard:")
    notes = list(NOTES)
    if event_bytes is None:
        notes[3] = ("This observer captured no events.jsonl broadcast stream. "
                    "Review separately exported history or capture-status.json when present; "
                    "an empty event stream does not exclude earlier native turns.")
    out = {
        "kind": "native_client_publication_export", "schema": 1,
        "source_kind": source["kind"], "run_id": run, "slot": slot,
        "private_source": {"path": source_name, "sha256": sha(source_bytes),
                           "bytes": len(source_bytes), "retention": "privately_retained_ignored"},
        "exporter_sha256": sha(Path(__file__).read_bytes()),
        "publication_notes": notes,
        **fields(source, SCALAR_FIELDS),
    }
    for key in ("mcp_service_before", "mcp_service_after"):
        if key in source:
            out[key] = fields(source[key], SERVICE_FIELDS)
    for key, allowed in (
        ("sel_checkpoint", ("anchor_event_id", "anchor_sha256", "baseline_count")),
        ("sel_window", ("complete", "reason", "method", "anchor_event_id", "anchor_index", "event_count")),
        ("sel_integrity_after", ("integrity", "tampered", "total", "valid")),
    ):
        if key in source:
            out[key] = fields(source[key], allowed)
    if "mcp_audit" in source:
        audit = source["mcp_audit"]
        selected = fields(audit, ("collection_succeeded", "start_cursor", "end_cursor", "ignored_non_audit_rows"))
        audit_rows = rows(audit.get("events", []))
        traces = {run + "-" + phase for phase in ("allow", "crew", "mcp", "iam")}
        matching = [row for row in audit_rows if row.get("trace_id") in traces]
        selected["events"] = [fields(row, AUDIT_FIELDS) for row in matching]
        selected["publication_scope"] = {"original_event_count": len(audit_rows),
                                         "run_event_count": len(matching),
                                         "omitted_other_trace_count": len(audit_rows) - len(matching)}
        out["mcp_audit"] = selected
    if "processes_before" in source:
        out["processes_before"] = [fields(row, PROCESS_FIELDS) for row in rows(source["processes_before"])]
    if "permission_triggered_process_snapshots" in source:
        out["permission_triggered_process_snapshots"] = []
        for row in rows(source["permission_triggered_process_snapshots"]):
            item = fields(row, ("request_id", "started", "finished", "approval_pending_during_sampling"))
            item["processes"] = [fields(process, PROCESS_FIELDS) for process in rows(row.get("processes", []))]
            out["permission_triggered_process_snapshots"].append(item)
    out["private_sel_counts"] = {}
    for key in ("sel_before", "sel_after", "new_sel_interval"):
        if key in source:
            events = rows(source[key])
            count = sum(row.get("caller_identity") == caller for row in events)
            out["private_sel_counts"][key] = {"total": len(events), "target_session": count,
                                               "other_callers": len(events) - count}
    if "new_session_sel" in source:
        scoped = rows(source["new_session_sel"])
        require(all(row.get("caller_identity") == caller for row in scoped), "scoped SEL caller mismatch")
        out["new_session_sel"] = [fields(row, SEL_FIELDS) for row in scoped]
    out["conversation_summary"] = {}
    for key in ("slot_before", "slot_after"):
        if key in source:
            snapshot = source[key]
            require(isinstance(snapshot, dict), "invalid conversation snapshot")
            message_rows = snapshot.get("messages", [])
            require(isinstance(message_rows, list), "invalid conversation messages")
            out["conversation_summary"][key] = {
                **fields(snapshot, ("running", "stopping", "total", "has_more")),
                "captured_message_count": len(message_rows), "message_content_exported": False,
            }
    if event_bytes is not None:
        events = [json.loads(line) for line in event_bytes.splitlines()]
        rows(events)
        require(all(row.get("data", {}).get("slot") == slot for row in events), "native event slot mismatch")
        check_publishable(events)
        out["native_events"] = {"path": "events.jsonl", "sha256": sha(event_bytes),
                                "bytes": len(event_bytes), "events": len(events), "scope": "exact source slot",
                                "relationship": ("later same-run companion; not baseline-time evidence" if source_name == "baseline.json"
                                                 else "scoped companion for this capture")}
    else:
        require(source.get("captured_events", 0) == 0, "missing captured native events")
        out["native_events"] = {"path": "events.jsonl", "present": False, "events": 0}
    check_publishable(out)
    return out


def export_run(directory, output_directory=None):
    directory = Path(directory).absolute()
    require(directory.is_dir() and not directory.is_symlink(), "run directory must be a real directory")
    output = Path(output_directory).absolute() if output_directory is not None else directory
    if output_directory is not None:
        require(not output.exists() and not output.is_symlink(), "fresh output directory required")
        require(not any(parent.is_symlink() for parent in output.parents), "linked output ancestor refused")
    events_path = directory / "events.jsonl"
    event_bytes = read_bytes(events_path) if events_path.exists() or events_path.is_symlink() else None
    prepared = []
    for name in ("baseline.json", "receipt.json"):
        source = directory / name
        source_bytes = read_bytes(source)
        destination = output / (source.stem + "-publication.json")
        require(not destination.exists() and not destination.is_symlink(), "fresh publication outputs required")
        value = project(json.loads(source_bytes), source_bytes, name, event_bytes)
        if output_directory is not None:
            value["private_source"].update(path=os.path.relpath(source, output), path_base="publication_directory")
            value["native_events"].update(path=os.path.relpath(events_path, output), path_base="publication_directory",
                                           retention=("private companion; reviewed scoped derivatives are indexed separately" if event_bytes is not None
                                                      else "no companion captured; reference records the expected location"))
            value["publication_notes"].append("Relative private-source paths resolve from this publication directory; original capture files were not copied into it.")
            check_publishable(value)
        prepared.append((source, source_bytes, destination, value))
    require(len({(value["run_id"], value["slot"]) for _, _, _, value in prepared}) == 1,
            "baseline and receipt run identity mismatch")
    # Check every input before creating either derivative. No original mutation.
    for source, original, _, _ in prepared:
        require(read_bytes(source) == original, "source changed during export")
    if output_directory is not None:
        output.mkdir(parents=True, mode=0o700)
    for source, original, destination, value in prepared:
        with destination.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
        require(read_bytes(source) == original, "source changed during export")
    return [{"file": str(destination), "sha256": sha(read_bytes(destination)),
             "private_source_sha256": sha(original)} for _, original, destination, _ in prepared]


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, help="Fresh directory for derivatives only; private source references remain hash-bound and relative.")
    args = parser.parse_args()
    try:
        print(json.dumps({"exports": export_run(args.run_dir, args.output_dir)}, indent=2))
    except (ValueError, OSError) as error:
        print(json.dumps({"error": str(error) if isinstance(error, ValueError) else type(error).__name__}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
