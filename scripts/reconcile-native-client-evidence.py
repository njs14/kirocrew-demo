#!/usr/bin/env python3
"""Reconcile preserved native observations; optionally read a bounded SEL interval.

No native turn, approval, policy edit, log rewrite or replay is performed.
Outputs are written to a new directory, leaving the original receipt intact.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from datetime import datetime

from demo_config import load_config, ssh_options

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("passive_observer", HERE / "capture-native-client-evidence.py")
observer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(observer)
native = observer.native

# Fixed read-only filesystem scan. It never imports the runtime (whose SEL
# constructor may maintain key files), opens the HMAC key, or writes remotely.
REMOTE_SCAN = r'''
import collections,datetime,hashlib,json,os,re,stat,sys
since,until,caller=sys.argv[1:]
start=datetime.datetime.fromisoformat(since); end=datetime.datetime.fromisoformat(until)
fields={"event_id","timestamp","event_type","caller_identity","request_id","outcome","error","source","agent","operation","resources","tool_kind","entry_hash","prev_hash"}
name_re=re.compile(r"security_events-\d{6,}-\d{8}T\d{6}Z\.jsonl\Z")
out={"kind":"read_only_sel_interval","since":since,"until":until,"caller_identity":caller,"scan_complete":False,"files":[],"events":[],"window_event_count":0,"other_window_outcomes":{},"limitations":["Retained log bytes were scanned without opening or exporting the HMAC key.","This is a timestamp-bounded retained-log scan, not a restoration of the original recent-page anchor."]}
fds=[]; budget=96*1024*1024; total=0; timestamps=[]; counters=collections.Counter()
try:
 if start.tzinfo is None or end.tzinfo is None or not 0 < (end-start).total_seconds() <= 600: raise ValueError("invalid window")
 base=os.open("/var/lib/kirocrew",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(base)
 specs=[]; names=[]; seg=None
 try:
  seg=os.open("security_events.d",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=base);fds.append(seg)
 except FileNotFoundError: pass
 if seg is not None:
  names=sorted(n for n in os.listdir(seg) if name_re.fullmatch(n))
  if len(names)>7:raise ValueError("too many segments")
  specs.extend((seg,n,"security_events.d/"+n,False) for n in names)
 specs.append((base,"security_events.jsonl","security_events.jsonl",True))
 for parent,name,label,live in specs:
  fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=parent);fds.append(fd)
  info=os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_size>40*1024*1024:raise ValueError("invalid log file")
  total+=info.st_size
  if total>budget:raise ValueError("scan bound exceeded")
  digest=hashlib.sha256(); remaining=info.st_size; line_number=0; first=None; last=None
  with os.fdopen(os.dup(fd),"rb") as stream:
   while remaining:
    line=stream.readline(min(65537,remaining));remaining-=len(line);digest.update(line);line_number+=1
    if not line or not line.endswith(b"\n") or len(line)>65536:raise ValueError("partial or oversized log row")
    event=json.loads(line)
    stamp=datetime.datetime.fromisoformat(event["timestamp"])
    if stamp.tzinfo is None:raise ValueError("invalid timestamp")
    first=stamp if first is None or stamp<first else first;last=stamp if last is None or stamp>last else last
    if start<=stamp<end:
     out["window_event_count"]+=1
     if event.get("caller_identity")==caller:
      if len(out["events"])>=200:raise ValueError("matched event bound exceeded")
      out["events"].append({**{k:event[k] for k in fields if k in event},"source_file":label,"source_line":line_number})
     else:counters[(str(event.get("event_type","unknown")),str(event.get("outcome","unknown")))]+=1
  after=os.stat(name,dir_fd=parent,follow_symlinks=False)
  if (after.st_dev,after.st_ino)!=(info.st_dev,info.st_ino) or after.st_size<info.st_size or (not live and after.st_size!=info.st_size):raise ValueError("log changed during scan")
  out["files"].append({"path":label,"device":info.st_dev,"inode":info.st_ino,"snapshot_bytes":info.st_size,"snapshot_sha256":digest.hexdigest(),"rows":line_number,"earliest_timestamp":first.isoformat() if first else None,"latest_timestamp":last.isoformat() if last else None})
  if first is not None:timestamps.extend((first,last))
 if seg is not None and sorted(n for n in os.listdir(seg) if name_re.fullmatch(n))!=names:raise ValueError("segments changed during scan")
 out["other_window_outcomes"]={event+":"+outcome:count for (event,outcome),count in counters.items()}
 out["scanned_bytes"]=total
 out["retained_timestamps_bracket_window"]=bool(timestamps and min(timestamps)<=start and max(timestamps)>=end)
 out["scan_complete"]=out["retained_timestamps_bracket_window"]
except Exception as error:out["failure_type"]=type(error).__name__
finally:
 for fd in reversed(fds):os.close(fd)
print(json.dumps(out,sort_keys=True))
'''


def read_bounded(path, limit=32_000_000):
    native.require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit, "invalid_input_file")
    return path.read_bytes()


def analyze(receipt, events, sel_scan):
    rows = observer.observations(events, receipt.get("mcp_audit", {}), sel_scan.get("events", []), receipt["run_id"])
    resolved = {str(event["data"].get("id")) for event in events if event["type"] == "approval_resolved" and event["data"].get("approved") is True}
    # User turns bound the Crew-only SEL correlation; SEL has no trace field.
    starts = [(event["time"], event["data"].get("content", "")) for event in events if event["type"] == "chat_message" and event["data"].get("role") == "user"]
    for row in rows:
        calls, permissions = row["native_tool_call_ids"], row["permission_request_ids"]
        decisions = [event for event in row["service_events"] if event.get("event") == "tool_decision"]
        dispatch = [event for event in row["service_events"] if event.get("event") == "aws_dispatch"]
        results = [event for event in row["service_events"] if event.get("event") == "aws_result"]
        approvals = [event for event in row["sel_for_permission_ids"] if event.get("event_type") == "tool_invocation" and event.get("outcome") == "approved"]
        row["native_approval_resolved_ids"] = [value for value in permissions if value in resolved]
        start = next((stamp for stamp, content in starts if row["trace_id"] in content), None)
        finish = next((stamp for stamp, content in starts if start and stamp > start), receipt["stream_finished"])
        phase_calls = {event["data"].get("tool_call_id") for event in events if event["type"] == "tool_call" and start and start <= event["time"] < finish}
        exact_native_turn = len(calls) == 1 and phase_calls == set(calls)
        service_identity = all(event.get("tool") == row["tool"] and event.get("principal") == "kirocrew-demo-client" and
                               event.get("journal_invocation_id") == receipt.get("mcp_service_before", {}).get("InvocationID")
                               for event in row["service_events"])
        one_service_invocation = len({event.get("invocation_id") for event in row["service_events"]}) == 1 and all(event.get("invocation_id") for event in row["service_events"])
        canonical_operation = "Running: @aws-enforcement/" + row["tool"]
        if row["phase"] == "crew":
            denied = [event for event in sel_scan.get("events", []) if start and start <= event.get("timestamp", "") < finish and event.get("event_type") == "tool_invocation" and event.get("outcome") == "denied" and event.get("error") == "hook_deny" and event.get("operation") == canonical_operation and event.get("request_id")]
            row["isolated_turn_sel_denials"] = denied
            row["correlation"] = "Exact trace-bearing blocked native tool row; one isolated-turn hook_deny; no direct SEL-to-trace link"
            observed = exact_native_turn and row["native_blocked_tool_call_ids"] == calls and not permissions and len(denied) == 1 and not row["service_events"]
        else:
            observed = exact_native_turn and service_identity and one_service_invocation and len(permissions) == 1 and permissions[0] in resolved and len(approvals) == 1 and approvals[0].get("operation") == canonical_operation and len(decisions) == 1 and len(row["joined_native_service_results"]) == 1
            payload = row["joined_native_service_results"][0] if len(row["joined_native_service_results"]) == 1 else {}
            aws_result = results[0] if len(results) == 1 else {}
            same_result = bool(aws_result) and all(payload.get(key) == aws_result.get(key) for key in ("aws_request_id", "object_sha256", "object_bytes", "error_code", "http_status"))
            if row["phase"] == "allow":
                observed = observed and payload.get("ok") is True and payload.get("layer") == "aws" and bool(payload.get("aws_request_id")) and len(dispatch) == len(results) == 1 and decisions[0].get("outcome") == "allowed" and aws_result.get("outcome") == "allowed" and same_result
            elif row["phase"] == "mcp":
                observed = observed and payload.get("ok") is False and payload.get("error_code") == "tool_grant_denied" and payload.get("layer") == "mcp" and decisions[0].get("outcome") == "denied" and not dispatch and not results
            else:
                observed = observed and payload.get("ok") is False and payload.get("layer") == "aws" and payload.get("error_code") == "AccessDenied" and payload.get("http_status") == 403 and bool(payload.get("aws_request_id")) and len(dispatch) == len(results) == 1 and decisions[0].get("outcome") == "allowed" and aws_result.get("outcome") == "denied" and same_result
            row["correlation"] = "Native tool-call and approval IDs to SEL; native result trace and invocation ID to service audit"
        row["outcome_observed"] = bool(observed)
    support = bool(sel_scan.get("scan_complete") and receipt.get("service_stable") and receipt.get("mcp_audit", {}).get("collection_succeeded") and receipt.get("sel_integrity_after", {}).get("integrity") == "ok")
    return {"phase_observations": rows, "bounded_four_outcomes_reconciled": support and all(row["outcome_observed"] for row in rows),
            "supporting_collection_checks": {"retained_sel_interval_scanned": sel_scan.get("scan_complete") is True,
                                             "original_mcp_journal_complete": receipt.get("mcp_audit", {}).get("collection_succeeded") is True,
                                             "original_mcp_service_stable": receipt.get("service_stable") is True,
                                             "original_gateway_sel_integrity_ok": receipt.get("sel_integrity_after", {}).get("integrity") == "ok"}}


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config")
    parser.add_argument("--collect-sel", action="store_true", help="Read retained server logs through fixed pinned SSH")
    parser.add_argument("--sel-receipt", type=Path, help="Use an already collected interval instead")
    parser.add_argument("--sel-only", action="store_true", help="Write the generic scoped SEL interval without four-MCP outcome analysis")
    parser.add_argument("--since", required=True)
    parser.add_argument("--until", required=True)
    args = parser.parse_args()
    native.require(bool(args.collect_sel) != bool(args.sel_receipt), "choose_one_sel_source")
    start, end = datetime.fromisoformat(args.since), datetime.fromisoformat(args.until)
    native.require(start.tzinfo is not None and end.tzinfo is not None and 0 < (end-start).total_seconds() <= 600, "invalid_time_window")
    original = args.run_dir.resolve()
    receipt_bytes = read_bounded(original / "receipt.json")
    event_bytes = read_bounded(original / "events.jsonl")
    receipt = json.loads(receipt_bytes)
    events = [json.loads(line) for line in event_bytes.splitlines()]
    native.require(len(events) <= observer.MAX_EVENTS and all(event.get("data", {}).get("slot") == receipt["slot"] for event in events), "invalid_event_scope")
    native.require(not args.output.exists() and not args.output.is_symlink(), "output_directory_already_exists")
    args.output.mkdir(parents=True, mode=0o700)
    cleaner = native.Sanitizer()
    if args.collect_sel:
        config = load_config(args.config)
        native.SSH_OPTIONS = ssh_options(config)
        caller = "dashboard:" + receipt["slot"].removeprefix("dashboard:")
        raw = native.ssh(config["ssh"]["admin_alias"], ["sudo", "-n", "python3", "-c", REMOTE_SCAN, args.since, args.until, caller])
        scan = cleaner.clean(json.loads(raw))
    else:
        scan = json.loads(read_bounded(args.sel_receipt))
    native.require(scan.get("caller_identity") == "dashboard:" + receipt["slot"].removeprefix("dashboard:"), "sel_caller_mismatch")
    native.require(scan.get("since") == args.since and scan.get("until") == args.until, "sel_time_window_mismatch")
    native.require(all(event.get("caller_identity") == scan["caller_identity"] and
                       start <= datetime.fromisoformat(event["timestamp"]) < end for event in scan.get("events", [])),
                   "sel_event_outside_scope")
    native.write_new(args.output / "sel-interval.json", scan)
    if args.sel_only:
        print(json.dumps({"sel_interval_collected": scan.get("scan_complete") is True,
                          "event_count": len(scan.get("events", [])), "output": str(args.output),
                          "enforcement_attribution": "not_evaluated"}))
        return 0 if scan.get("scan_complete") is True else 1
    result = {"kind": "native_client_evidence_reconciliation", "created": native.now(), "original_receipt_preserved": True,
              "run_id": receipt["run_id"], "slot": receipt["slot"], "full_native_acceptance": False,
              "source_sha256": {"receipt.json": hashlib.sha256(receipt_bytes).hexdigest(), "events.jsonl": hashlib.sha256(event_bytes).hexdigest(),
                                "sel-interval.json": hashlib.sha256((args.output / "sel-interval.json").read_bytes()).hexdigest(),
                                "collector": hashlib.sha256((HERE / "capture-native-client-evidence.py").read_bytes()).hexdigest(),
                                "reconciler": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
              "original_collection_complete": receipt.get("collection_complete"), "original_sel_window": receipt.get("sel_window"),
              "limitations": ["Original collector receipt remains incomplete; this is a separate read-only reconciliation.",
                              "Known ACP purpose metadata is retained in original events and excluded only from functional trace matching.",
                              "No proof that EC2 process sampling overlapped pending approval; original collector missed approval_id metadata.",
                              "IAM policy attribution and allowed-fixture digest agreement require separately checked provisioning/deployment receipts.",
                              "The server hook is configurable Crew state, not an immutable enterprise policy floor.",
                              "Retained SEL rows were read without exporting the HMAC key; integrity uses the original Gateway verification, not independent per-row signature verification."]}
    result.update(analyze(receipt, events, scan))
    native.write_new(args.output / "reconciliation.json", cleaner.clean(result))
    print(json.dumps({"bounded_four_outcomes_reconciled": result["bounded_four_outcomes_reconciled"], "output": str(args.output),
                      "phases": [{"phase": row["phase"], "outcome_observed": row["outcome_observed"]} for row in result["phase_observations"]]}))
    return 0 if result["bounded_four_outcomes_reconciled"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({"failed": True, "failure": str(error) if isinstance(error, native.DemoFailure) else type(error).__name__}))
        raise SystemExit(1)
