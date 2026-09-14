#!/usr/bin/env python3
"""Build a focused HTML presentation from reviewed recordings of real controls.

Repeat --manifest to append independently processed takes. The builder verifies
asset hashes, retains each scene's evidence scope and never creates demo footage.
By default it writes the four kirocrew-native-controls artifacts in output/.
--output-dir creates a separate portable export without replacing those files.
"""
import argparse
import base64
from datetime import datetime, timezone
import html
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/kirocrew-native-controls.html"
NOTES = ROOT / "output/kirocrew-native-controls-notes.md"
PUBLIC = ROOT / "output/kirocrew-native-controls-manifest.json"
BUILD = ROOT / "output/kirocrew-native-controls-build.json"
DEFAULT_ADMIN = ROOT / "evidence/admin-console/native-20260913/tour-build.json"
DESTINATIONS = {OUTPUT, NOTES, PUBLIC, BUILD}

# Reuse the reviewed local-path, hash, number and atomic-write helpers. Importing
# this module has no build, subprocess, network or browser side effects.
_spec = importlib.util.spec_from_file_location("recorded_build", ROOT / "scripts/build-recorded-demo-presentation.py")
_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_helpers)
safe_file = _helpers.safe_file
local_asset = _helpers.local_asset
sha = _helpers.sha
write_atomic = _helpers.write_atomic
e = html.escape

KNOWN_CONTROLS = {
    "native-allowed-read": ("Permitted read", "MCP service and AWS", "Returns the fixture digest"),
    "native-crew-denial": ("Tool permission", "Crew on EC2", "Blocks crew_denied"),
    "native-mcp-denial": ("MCP grant", "Fixed-grant MCP service", "Returns tool_grant_denied"),
    "native-iam-denial": ("AWS permission", "IAM", "Returns S3 AccessDenied"),
    "native-memory-assignment-refusal": ("Private memory binding", "EC2 conversation guard", "Refuses an unassigned conversation"),
    "native-host-workspace-read": ("Permitted workspace read", "Remote built-in tool", "Public canary returned"),
    "native-host-anonymous-http403": ("Anonymous Gateway request", "See the supporting evidence", "Assistant reports HTTP 403"),
}

RECORDING_COVERAGE = {"request_to_result", "approval_to_result", "result_inspection", "unknown"}
OUTCOME_CLASSES = {"native_allowed", "server_hook_denied", "server_authentication_denied", "model_refusal", "not_established", "unknown"}
LEGACY_HOST_PENDING = (
    "Allowed workspace read", "Anonymous server authentication", "Sensitive-path read",
    "Protected-path write", "Server command rule", "Metadata TCP connection",
)

EXTRA_CSS = r"""
.control-cover h1{font-size:5.7cqw;max-width:76cqw}.control-cover .hero-intro{max-width:69cqw;font-size:2.2cqw}.cover-count{font-size:1.35cqw;color:#c9b7f5;margin-top:1.8cqw}.cover-bottom{margin-top:auto;display:flex;align-items:end;justify-content:space-between;gap:4cqw}.cover-bottom p{font-size:1.35cqw;color:#c8c3d1}.cover-bottom .slide-link{background:#e5d8ff;color:#2f194d}.architecture-svg{width:100%;height:100%;max-height:32cqw}.architecture-caption{font-size:1.22cqw;color:#55525f;max-width:78cqw}.control-table td{font-size:1.45cqw;padding:1.05cqw 1cqw 1.05cqw 0}.control-table th{font-size:1cqw}.control-table td:first-child{font-weight:700;width:24%}.control-table td:nth-child(2){width:29%;color:#685083}.control-table a{text-decoration-color:#bba4da;text-underline-offset:4px}.control-table .scene-time{display:block;color:#72717c;font-size:1cqw;font-weight:400;margin-top:.2cqw}.native-scene .demo-description{max-width:84cqw}.native-scene .demo-layout{grid-template-columns:minmax(0,4.1fr) minmax(0,1.1fr);gap:1.5cqw}.native-scene .demo-screen{background:#f4f1f7;padding:.55cqw;grid-template-rows:minmax(0,1fr) auto auto}.native-scene .demo-screen video{background:#17151b;border:0}.native-scene .demo-controls{gap:.5cqw}.native-scene .demo-controls button{font-size:.95cqw;padding:.5cqw .6cqw}.native-scene .demo-controls label{font-size:.94cqw}.native-scene .demo-status{font-size:.9cqw!important}.native-scene .demo-cues button{font-size:1.03cqw;line-height:1.35;padding:.65cqw .4cqw}.native-scene .demo-cue-detail{font-size:1.03cqw}.native-scene .slide-footer{font-size:.92cqw}.scene-downloads{display:flex;gap:.85cqw;align-items:center}.scene-downloads a{font-size:.92cqw;color:#614482;text-underline-offset:3px}.authority-note{font-size:1.45cqw;line-height:1.5;max-width:82cqw}.admin-feature{display:grid;grid-template-columns:1fr 1.25fr;gap:3cqw;min-height:0;flex:1;align-items:center}.admin-feature h3{font-size:2.35cqw;line-height:1.17;margin-bottom:1.2cqw}.admin-feature p{font-size:1.48cqw;line-height:1.48}.admin-feature .screenshot{height:31cqw}.admin-feature .link-row{margin-top:2cqw}.artifact-list{display:flex;flex-direction:column;gap:0}.artifact-row{display:grid;grid-template-columns:2.2cqw 1fr;gap:1.3cqw;border-top:1px solid #c5b5dd;padding:1.4cqw 0}.artifact-row b{font-size:1.2cqw;color:#76509d}.artifact-row a{font-size:2cqw;font-weight:700;text-decoration-thickness:1px;text-underline-offset:5px}.artifact-row p{font-size:1.3cqw;margin-top:.5cqw;color:#62576e}.artifact-grid{display:grid;grid-template-columns:1.25fr .8fr;gap:5cqw;align-items:center}.artifact-grid .note{font-size:1.45cqw;line-height:1.6}.artifact-grid code{font-size:.86em}.scene-count{font-size:6.2cqw;line-height:1;letter-spacing:-.06em}.plain-links{font-size:1.1cqw;line-height:1.8}.plain-links a{display:block;color:#674690}.media-button::after{opacity:1}
@media(max-width:760px){.control-cover h1{font-size:46px;max-width:none}.control-cover .hero-intro{font-size:22px;max-width:none}.cover-count{font-size:15px;margin-top:20px}.cover-bottom{display:block}.cover-bottom p{font-size:15px;margin:20px 0}.architecture-svg{height:auto;max-height:none;min-width:660px}.architecture-scroll{overflow:auto}.architecture-caption{font-size:14px;max-width:none}.control-table td{font-size:14px;padding:15px 12px 15px 0}.control-table th{font-size:10px}.control-table .scene-time{font-size:12px}.control-table td:nth-child(2){width:31%}.native-scene .demo-layout{grid-template-columns:1fr;gap:22px}.native-scene .demo-screen{padding:7px;display:flex}.native-scene .demo-screen video{aspect-ratio:1920/1290}.native-scene .demo-description{max-width:none}.native-scene .demo-controls{gap:9px}.native-scene .demo-controls button,.native-scene .demo-controls label{font-size:14px}.native-scene .demo-status{font-size:13px!important}.native-scene .demo-cues button{font-size:14px;padding:12px}.native-scene .demo-cue-detail{font-size:15px}.native-scene .slide-footer{font-size:12px}.scene-downloads{gap:16px}.scene-downloads a{font-size:13px}.authority-note{font-size:16px;max-width:none}.admin-feature,.artifact-grid{grid-template-columns:1fr;gap:25px}.admin-feature h3{font-size:26px;margin-bottom:15px}.admin-feature p{font-size:16px}.admin-feature .screenshot{height:auto}.admin-feature .link-row{margin-top:20px}.artifact-row{grid-template-columns:24px 1fr;gap:12px;padding:20px 0}.artifact-row b{font-size:13px}.artifact-row a{font-size:23px}.artifact-row p{font-size:15px;margin-top:8px}.artifact-grid .note{font-size:16px}.scene-count{font-size:66px}.plain-links{font-size:14px}}
.scene-proof{font-size:1.02cqw!important;line-height:1.4;margin-top:.5cqw;color:#674587}.scene-proof code{font-size:.94em}.native-scene .slide-footer>span:first-child{max-width:84cqw}.admin-examples{display:grid;grid-template-columns:1fr 1.75fr;column-gap:2.5cqw;row-gap:1.1cqw;align-items:center}.admin-examples h3{font-size:1.9cqw;margin-bottom:.5cqw}.admin-examples p{font-size:1.2cqw;line-height:1.45}.admin-detail{width:100%;border:1px solid #d5d0dd;background:#101014;display:block}.admin-detail svg{display:block;width:100%;height:100%}.admin-posture{height:10.5cqw}.admin-governance{height:7.5cqw}.admin-sources{display:grid;grid-template-columns:repeat(4,1fr);gap:1.5cqw;border-top:1px solid #dad2e4;padding-top:1.1cqw;margin-top:.7cqw}.admin-sources dt{font-size:1.16cqw;font-weight:700;margin-bottom:.4cqw;color:#4f336d}.admin-sources dd{font-size:1.06cqw;line-height:1.45;margin:0;color:#5d5865}.admin-controls{display:flex;justify-content:space-between;align-items:center;gap:2cqw}.admin-controls p{font-size:1cqw;color:#696271}.receipt-heading{font-size:1.22cqw;color:#655374;margin:1.2cqw 0 .3cqw}.receipt-links a{font-size:1.2cqw;line-height:1.85}.artifact-grid .note{font-size:1.3cqw}.artifact-grid{grid-template-columns:1.15fr 1fr;gap:4cqw}
@media(max-width:760px){.scene-proof{font-size:13px!important;margin-top:8px}.native-scene .slide-footer>span:first-child{max-width:none}.admin-examples{grid-template-columns:1fr;gap:14px}.admin-examples h3{font-size:23px}.admin-examples p{font-size:15px}.admin-posture{height:auto;aspect-ratio:940/180}.admin-governance{height:auto;aspect-ratio:960/115}.admin-sources{grid-template-columns:1fr 1fr;gap:16px;margin-top:15px;padding-top:18px}.admin-sources dt{font-size:15px}.admin-sources dd{font-size:14px}.admin-controls{display:block}.admin-controls p{font-size:12px;margin-top:12px}.receipt-heading{font-size:15px;margin-top:20px}.receipt-links a{font-size:15px}.artifact-grid .note{font-size:15px}.artifact-grid{grid-template-columns:1fr;gap:25px}}
.control-table th{font-size:1.14cqw}.pending-controls{font-size:1.15cqw;line-height:1.45;border-left:3px solid #9475b8;padding-left:1cqw;margin-top:.3cqw}.pending-controls strong{color:#51386d}.admin-detail-wrap{min-width:0;display:flex;flex-direction:column;align-items:stretch}.admin-detail{overflow:hidden}.admin-posture{height:8.5cqw}.admin-governance{height:5.9cqw}.admin-expand{align-self:flex-end;font-size:1cqw;border:1px solid #bba9d0;background:#f3edf9;color:#573873;padding:.35cqw .75cqw;margin-top:.35cqw;border-radius:3px;cursor:pointer}.admin-examples .control-split{margin-top:.65cqw;font-size:1.08cqw}.control-split code{font-size:1em}
@media(max-width:760px){.control-table th{font-size:12px}.pending-controls{font-size:14px;padding-left:12px;margin-top:4px}.admin-posture{height:auto;aspect-ratio:929/132}.admin-governance{height:auto;aspect-ratio:940/103}.admin-expand{font-size:13px;padding:7px 11px;margin-top:7px}.admin-examples .control-split{font-size:14px;margin-top:8px}}
"""

MANAGED_CSS = r"""
.managed-user .slide-body{display:grid;grid-template-columns:1.65fr 1fr;gap:3cqw;align-items:start}.managed-user h3{font-size:1.9cqw;margin-bottom:.65cqw}.managed-user p{font-size:1.35cqw;line-height:1.45;margin-bottom:1cqw}.managed-user .mcp-enabled{height:11.5cqw}.managed-user .mcp-staged{height:4cqw;margin-top:1cqw}.managed-user .session-inventory{height:26cqw}.managed-user .admin-expand{margin-bottom:1.1cqw}.managed-admin .admin-governance{height:10cqw}.managed-admin .admin-posture{height:6.1cqw}.managed-admin .admin-examples{row-gap:.8cqw;grid-template-columns:1fr 1.8fr}.managed-admin .admin-examples p{font-size:1.17cqw}.managed-admin .admin-sources{margin-top:1.3cqw}.reproduce-command{padding:1.2cqw 0;border-top:1px solid #c5b5dd;border-bottom:1px solid #c5b5dd;overflow-wrap:anywhere;font-size:1.35cqw;line-height:1.6}.reproduce-command code{font-size:1.24cqw}.replication-copy{font-size:1.3cqw;line-height:1.5;margin:1.2cqw 0}.artifact-inline{display:flex;flex-wrap:wrap;gap:1.2cqw;margin-top:1.4cqw;font-size:1.3cqw}.managed-artifacts .receipt-links a{font-size:1.17cqw}.managed-artifacts .artifact-grid{grid-template-columns:1.3fr 1fr;gap:4cqw}
@media(max-width:760px){.managed-user .slide-body{display:block}.managed-user h3{font-size:23px}.managed-user p{font-size:16px}.managed-user .mcp-enabled,.managed-user .mcp-staged,.managed-user .session-inventory,.managed-admin .admin-governance,.managed-admin .admin-posture{height:auto}.managed-user .session-inventory{aspect-ratio:305/342;max-height:440px}.managed-user .admin-expand{margin-bottom:18px}.managed-admin .admin-examples{grid-template-columns:1fr}.managed-admin .admin-examples p{font-size:15px}.reproduce-command{padding:14px 0;font-size:16px}.reproduce-command code{font-size:14px}.replication-copy,.artifact-inline{font-size:16px}.managed-artifacts .receipt-links a{font-size:15px}}
"""


def text(value, label, maximum=2500):
    return _helpers.text(value, label, maximum)


def finite(value, label, minimum=0):
    value = _helpers.number(value, label)
    if value < minimum:
        raise ValueError(f"{label} is below its minimum")
    return value


def validate_hash(path, metadata, label):
    data = safe_file(path).read_bytes()
    if metadata.get("sha256") != sha(data):
        raise ValueError(f"{label} hash does not match")
    if "bytes" in metadata and metadata["bytes"] != len(data):
        raise ValueError(f"{label} size does not match")
    return data


def public_fields(value, fields):
    """Copy only the documented public fields, excluding incidental metadata."""
    return {key: value[key] for key in fields if key in value}


def checked_phase_observations(receipt):
    """Require the concrete evidence used by the slide's short proof labels."""
    phases = {}
    for item in receipt.get("phase_observations", []):
        if item.get("outcome_observed") is not True:
            continue
        phase = item.get("phase")
        if phase in phases:
            raise ValueError("Reconciliation has duplicate phases")
        events = item.get("service_events", [])
        joined = item.get("joined_native_service_results", [])
        if not isinstance(events, list) or not all(isinstance(event, dict) for event in events):
            raise ValueError("Reconciliation service events are invalid")
        if phase == "crew":
            denials = item.get("isolated_turn_sel_denials", [])
            blocked = item.get("native_blocked_tool_call_ids", [])
            if (not blocked or not all(isinstance(value, str) and value for value in blocked)
                    or len(denials) != 1 or denials[0].get("error") != "hook_deny"
                    or denials[0].get("outcome") != "denied" or events
                    or item.get("permission_request_ids") != []
                    or item.get("native_approval_resolved_ids") != []):
                raise ValueError("Crew proof lacks the isolated blocked turn and no-service-arrival evidence")
        elif phase == "mcp":
            if len(joined) != 1:
                raise ValueError("MCP proof needs one joined native and service result")
            result = joined[0]
            invocation = result.get("invocation_id")
            if (result.get("ok") is not False or result.get("layer") != "mcp"
                    or result.get("error_code") != "tool_grant_denied"
                    or not isinstance(invocation, str) or not invocation
                    or not any(event.get("event") == "tool_decision" and event.get("outcome") == "denied"
                               and event.get("invocation_id") == invocation for event in events)
                    or any(event.get("event") == "aws_dispatch" and event.get("invocation_id") == invocation for event in events)):
                raise ValueError("MCP proof lacks the matching denied grant and no-AWS-dispatch evidence")
        elif phase in {"allow", "iam"}:
            if len(joined) != 1:
                raise ValueError("AWS proof needs one joined native and service result")
            result = joined[0]
            invocation, request = result.get("invocation_id"), result.get("aws_request_id")
            if (not invocation or not request
                    or not any(event.get("event") == "aws_dispatch" and event.get("invocation_id") == invocation for event in events)
                    or not any(event.get("event") == "aws_result" and event.get("invocation_id") == invocation
                               and event.get("aws_request_id") == request for event in events)):
                raise ValueError("AWS proof lacks a matching dispatch, result and request ID")
        else:
            continue
        phases[phase] = item
    if set(phases) != {"allow", "crew", "mcp", "iam"}:
        raise ValueError("A four-outcome reconciliation must include all four validated phases")
    return phases


def controls_for(scene):
    supplied = scene.get("presentation")
    if supplied is not None:
        if not isinstance(supplied, dict):
            raise ValueError("Scene presentation metadata must be an object")
        return tuple(text(supplied.get(key), f"presentation {key}", 130)
                     for key in ("control", "enforcer", "outcome"))
    return KNOWN_CONTROLS.get(scene["id"], (scene["title"], "See the recorded result", "See the recorded result"))


def checked_managed(receipt, loaded, input_hashes, register, receipts):
    """Bind current policy claims to public, independently reviewed evidence."""
    if receipt.get("schema_version") != 1 or receipt.get("kind") != "managed_native_presentation":
        raise ValueError("Expected managed_native_presentation schema 1")
    policy, native = receipt.get("policy", {}), receipt.get("native", {})
    digest = policy.get("policy_sha256")
    if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or policy.get("sandbox_floor") != "cc" or policy.get("fail_closed") is not True
            or policy.get("source") != "file:///etc/kirocrew-demo/security-policy.json"
            or policy.get("denied_approval_modes") != ["yolo"]
            or policy.get("denied_mcp_tools") != ["@aws-enforcement/crew_denied"]
            or policy.get("owner_mutable_duplicate_hook_removed") is not True
            or native.get("managed_denial_verified") is not True
            or native.get("managed_denial_filmed") is not True
            or native.get("allowed_read_filmed") is not False):
        raise ValueError("Managed edition needs the verified, bounded file-policy configuration")
    observed = datetime.fromisoformat(text(receipt.get("observed_at"), "managed observation time", 80).replace("Z", "+00:00"))
    if observed.tzinfo is None:
        raise ValueError("Managed observation requires a timezone")
    manifest = receipt.get("clip_manifest", {})
    if input_hashes.get(manifest.get("path")) != manifest.get("sha256"):
        raise ValueError("Managed edition needs its exact processed clip manifest")
    matches = [scene for scene in loaded if scene["id"] == native.get("scene_id")]
    if len(matches) != 1:
        raise ValueError("Managed edition needs exactly one matching recorded scene")
    scene = matches[0]
    recorded = datetime.fromisoformat(scene["recordedAt"].replace("Z", "+00:00"))
    if not 0 <= (observed - recorded).total_seconds() <= 86400:
        raise ValueError("Managed observation must follow its capture within one day")
    evidence, bindings = {}, {}
    expected_kinds = {"enterprise_policy_verification", "demo_mcp_verification",
                      "native_managed_policy_verification", "native_managed_policy_denial_verification",
                      "independent_native_managed_artifact_review", "managed_host_runtime_check",
                      "native_client_relaunch", "actual_native_managed_mcp_clip_media_review"}
    for item in receipt.get("receipts", []):
        path = safe_file(ROOT / item["path"])
        if path.suffix != ".json" or not path.is_relative_to(ROOT / "evidence"):
            raise ValueError("Managed evidence must be explicit public JSON under evidence/")
        raw = validate_hash(path, item, "managed supporting receipt")
        body = json.loads(raw)
        kind = body.get("kind")
        if kind not in expected_kinds or kind in evidence:
            raise ValueError("Managed supporting receipts must have the eight expected distinct kinds")
        url = register(path, item)
        binding = {"path": item["path"], "url": url, "sha256": sha(raw)}
        existing = next((r for r in receipts if r["path"] == item["path"]), None)
        if existing and existing != binding:
            raise ValueError("Managed supporting receipt binding conflicts")
        if not existing:
            receipts.append(binding)
        evidence[kind], bindings[kind] = body, binding
    if set(evidence) != expected_kinds:
        raise ValueError("Managed presentation is missing an expected supporting receipt")
    verification = evidence.get("native_managed_policy_denial_verification", {})
    review = evidence.get("independent_native_managed_artifact_review", {})
    floor = verification.get("managed_floor", {})
    denial = verification.get("managed_denial", {})
    interval = verification.get("collection_boundary", {})
    governance = denial.get("sel_governance_decision", {})
    denied_request = denial.get("sel_denied_tool_request", {})
    verification_binding = bindings.get("native_managed_policy_denial_verification", {})
    reviewed = [item for item in review.get("artifacts", [])
                if item.get("artifact", {}).get("path") == verification_binding.get("path")
                and item.get("artifact", {}).get("sha256") == verification_binding.get("sha256")]
    if (verification.get("native_enforcement_verified") is not True
            or verification.get("verdict") != "PASS_FOR_RECORDED_NATIVE_MANAGED_MCP_DENY"
            or floor.get("policy_sha256") != digest
            or floor.get("exact_mutable_duplicate_removed_before_take") is not True
            or denial.get("tool") != "@aws-enforcement/crew_denied"
            or denial.get("trace_id") != native.get("filmed_trace")
            or not denial.get("tool_call_id")
            or denial.get("user_permission_prompt_in_collected_history") is not False
            or denial.get("matching_trace_service_arrivals") != 0
            or interval.get("collection_complete") is not True
            or interval.get("mcp_audit_collection_succeeded") is not True
            or interval.get("mcp_service_stable") is not True
            or interval.get("mcp_audit_event_count") != 0
            or interval.get("sel_window", {}).get("complete") is not True
            or governance.get("metadata", {}).get("layer") != "policy"
            or governance.get("outcome") != "denied"
            or governance.get("operation") != denial.get("tool")
            or denied_request.get("prev_hash") != governance.get("entry_hash")
            or denied_request.get("error") != "hook_deny"
            or denied_request.get("operation") != "Running: " + denial.get("tool", "")
            or denied_request.get("outcome") != "denied"
            or any(denied_request.get(key) != governance.get(key) for key in ("caller_identity", "agent", "source"))
            or review.get("verdict") != "PASS" or len(reviewed) != 1
            or reviewed[0].get("findings") != []):
        raise ValueError("Managed denial labels need matching native, policy, journal and independent-review evidence")
    protected = evidence.get("enterprise_policy_verification", {})
    mcp = evidence.get("demo_mcp_verification", {})
    live = mcp.get("binding", {}).get("proof", {}).get("live", {})
    media = evidence.get("actual_native_managed_mcp_clip_media_review", {})
    if (protected.get("root_protected_managed_files_verified") is not True
            or protected.get("unit_and_process_policy_environment_active") is not True
            or mcp.get("mutable_duplicate_present") is not False
            or mcp.get("binding", {}).get("proof", {}).get("policy_sha256") != digest
            or any(live.get(key) != value for key, value in {
                "has_policy": True, "mcp_governed": True, "mcp_source": "policy",
                "source_scheme": "file", "on_unavailable": "fail_closed"}.items())
            or media.get("verdict") != "PASS_FOR_ENCODING_AND_VISUAL_MEDIA_REVIEW"
            or media.get("scene_id") != scene["id"]
            or media.get("export", {}).get("sha256") != scene["media"][0]["sha256"]
            or media.get("source", {}).get("sha256") != scene["provenance"]["sourceSha256"]
            or media.get("cut", {}).get("contiguous") is not True
            or media.get("evidence_boundary", {}).get("denial_only_filmed") is not True):
        raise ValueError("Managed edition needs protected-source, duplicate-hook and exact-media verification")
    policy_plans = []
    for binding in receipts:
        if Path(binding["path"]).name == "policy-plan.json":
            body = json.loads(validate_hash(ROOT / binding["path"], binding, "policy content receipt"))
            if body.get("kind") == "enterprise_policy_plan":
                policy_plans.append(body)
    if len(policy_plans) != 1:
        raise ValueError("Managed policy claims need one explicit public policy-plan.json receipt")
    policy_file = policy_plans[0].get("files", {}).get("/etc/kirocrew-demo/security-policy.json", {})
    policy_text = text(policy_file.get("content"), "installed policy content", 20000)
    exact_policy = json.loads(policy_text)
    s3_upload_rule = r"aws(?:\s+--?[a-z-]+(?:[= ]\S+)?)*\s+s3(?:\s+--?[a-z-]+(?:[= ]\S+)?)*\s+cp .* s3://.*"
    if (sha(policy_text.encode()) != digest or policy_file.get("sha256") != digest
            or exact_policy.get("version") != 1
            or exact_policy.get("sandbox", {}).get("min_level") != "cc"
            or exact_policy.get("approval_modes") != {"mode": "deny", "deny": ["yolo"]}
            or exact_policy.get("mcp") != {"mode": "deny", "deny": ["@aws-enforcement/crew_denied"]}
            or exact_policy.get("commands", {}).get("mode") != "deny"
            or "*KIROCREW_MANAGED_COMMAND_CONTROL*" not in exact_policy.get("commands", {}).get("deny", [])
            or set(exact_policy.get("commands", {}).get("deny", [])) != {"*KIROCREW_MANAGED_COMMAND_CONTROL*", s3_upload_rule}
            or any(exact_policy.get("filesystem", {}).get(scope, {}).get("mode") != "deny"
                   or not exact_policy["filesystem"][scope].get("deny") for scope in ("read", "write"))):
        raise ValueError("Policy content must hash to the verified active policy and match the stated scopes")
    host = evidence["managed_host_runtime_check"]
    child = host.get("own_disposable_child", {})
    processes = host.get("native_cli_observation", {}).get("processes", [])
    relaunch = evidence["native_client_relaunch"]
    host_time = datetime.fromisoformat(host.get("captured_at", "").replace("Z", "+00:00"))
    relaunch_time = datetime.fromisoformat(relaunch.get("observed_at", "").replace("Z", "+00:00"))
    crew_uid = mcp.get("binding", {}).get("crew_uid")
    if (host.get("managed_files", {}).get("/etc/kirocrew-demo/security-policy.json", {}).get("sha256") != digest
            or host.get("gateway", {}).get("pid") != protected.get("main_pid")
            or host.get("crew_policy_write_access_denied") is not True
            or host.get("gateway_cgroup_pty_denial_verified") is not True
            or protected.get("dashboard_terminal_disabled") is not True
            or not isinstance(crew_uid, int) or child.get("uid") != crew_uid
            or child.get("cgroup") != host.get("gateway", {}).get("cgroup")
            or child.get("pty_errno") != 1 or child.get("pty_created") is not False
            or child.get("exited_and_reaped") is not True
            or len(processes) != 6
            or any(p.get("seccomp") != "2" or p.get("no_new_privs") != "1"
                   or p.get("mount_namespace_differs_from_gateway") is not True
                   or p.get("executable_basename") not in {"kiro-cli", "kiro-cli-chat"}
                   or p.get("cgroup") != host.get("gateway", {}).get("cgroup")
                   or str(p.get("uid")).split() != [str(crew_uid)] * 4 for p in processes)
            or relaunch.get("configured_runLocalGateway") is not False
            or relaunch.get("local_gateway_listener") is not False
            or relaunch.get("remote_tunnel_listener") is not True
            or relaunch.get("quit_observed_process_count") != 0
            or relaunch.get("running_native_process_count") != 1
            or relaunch.get("policy_at_observation") != "not yet installed"
            or any(t.tzinfo is None or not 0 <= (recorded - t).total_seconds() <= 86400
                   for t in (host_time, relaunch_time))):
        raise ValueError("Host and client claims need exact, dated runtime and pre-policy relaunch observations")
    images = {}
    for item in receipt.get("screenshots", []):
        role = item.get("role")
        if role not in {"governance", "mcp_enabled", "mcp_staged", "managed_command", "session_mcp", "approval_modes", "native_denial"} or role in images:
            raise ValueError("Unknown or duplicate managed screenshot role")
        path = safe_file(ROOT / item["path"])
        if not path.is_relative_to(ROOT / "evidence") or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("Managed screenshots must be explicit public evidence images")
        for key in ("width", "height"):
            if not isinstance(item.get(key), int) or not 1 <= item[key] <= 16384:
                raise ValueError("Managed screenshot dimensions must be bounded integers")
        images[role] = {**public_fields(item, ("path", "sha256", "bytes", "width", "height", "description")), "url": register(path, item)}
    if set(images) != {"governance", "mcp_enabled", "mcp_staged", "managed_command", "session_mcp", "approval_modes", "native_denial"}:
        raise ValueError("Managed edition needs all seven reviewed screenshot roles")
    scene["recordingCoverage"] = "request_to_result"
    scene["outcomeClass"] = "server_hook_denied"
    scene["presentation"] = {"control": "Managed MCP rule", "enforcer": "EC2 Gateway policy", "outcome": "Blocked before MCP dispatch"}
    scene["attributionReceipt"] = verification_binding
    scene["policySha256"] = digest
    return receipt, images


def architecture(managed=False):
    # Exactly one endpoint-control enclosure. The labels inside it identify
    # software and host authority on EC2 without splitting that boundary.
    diagram = '''<div class="architecture-scroll"><svg class="architecture-svg" viewBox="0 0 1180 415" role="img" aria-labelledby="architecture-title architecture-desc">
<title id="architecture-title">The Mac client uses one endpoint-control boundary on EC2</title><desc id="architecture-desc">The Mac local Gateway is off. An SSH tunnel carries its connection to the EC2 Gateway. The EC2 enclosure contains the Gateway, original Kiro CLI backend, remote workspace, host controls and the separate MCP service. The MCP service calls S3 using the instance role, and AWS IAM evaluates permission.</desc>
<defs><marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#8062a7"/></marker></defs>
<rect x="12" y="130" width="215" height="180" rx="10" fill="#f3eff8" stroke="#bcb1cc"/>
<text x="34" y="170" font-size="25" font-weight="700" fill="#251d30">Mac client</text><text x="34" y="205" font-size="20" fill="#51445f">Kiro Crew Nightly</text><text x="34" y="239" font-size="18" fill="#51445f">Local Gateway off</text><text x="34" y="275" font-size="16" fill="#6e6080">Prompts and approval UI</text>
<path d="M227 219H336" stroke="#8062a7" stroke-width="3" marker-end="url(#flow-arrow)" fill="none"/><text x="280" y="195" text-anchor="middle" font-size="17" fill="#69517e">SSH tunnel</text>
<g data-endpoint-control-box="true"><rect x="348" y="25" width="540" height="365" rx="13" fill="#eee5fc" stroke="#78559d" stroke-width="2.5"/>
<text x="374" y="65" font-size="26" font-weight="700" fill="#332243">One endpoint-control boundary</text><text x="374" y="97" font-size="19" fill="#694982">EC2 ARM host · us-east-1</text><path d="M374 117H861" stroke="#c8b5e0"/>
<text x="375" y="155" font-size="22" font-weight="700" fill="#372449">Gateway</text><text x="561" y="155" font-size="18" fill="#594567">Authentication and Crew policy</text>
<text x="375" y="197" font-size="22" font-weight="700" fill="#372449">Kiro CLI</text><text x="561" y="197" font-size="18" fill="#594567">Original backend, interactive approval</text>
<text x="375" y="239" font-size="22" font-weight="700" fill="#372449">Workspace</text><text x="561" y="239" font-size="18" fill="#594567">Remote files and host controls</text>
<path d="M374 263H861" stroke="#c8b5e0"/><text x="375" y="305" font-size="22" font-weight="700" fill="#372449">MCP service</text><text x="561" y="305" font-size="18" fill="#594567">Separate process, fixed demo grants</text><text x="375" y="351" font-size="17" fill="#6b5480">Execution remains on EC2 when the Mac Gateway is off.</text></g>
<path d="M889 306H964" stroke="#8062a7" stroke-width="3" marker-end="url(#flow-arrow)" fill="none"/><text x="927" y="280" text-anchor="middle" font-size="16" fill="#69517e">Role</text>
<rect x="978" y="226" width="188" height="151" rx="10" fill="#fff4e6" stroke="#d8b389"/><text x="1000" y="268" font-size="25" font-weight="700" fill="#69401d">AWS</text><text x="1000" y="307" font-size="20" fill="#805b3a">IAM permission</text><text x="1000" y="344" font-size="20" fill="#805b3a">S3 fixtures</text>
</svg></div>'''
    return diagram.replace("Authentication and Crew policy", "Authentication and managed policy") if managed else diagram


def export_destination(value):
    """Require a fresh destination, including when an ancestor is a symlink."""
    destination = Path(value).absolute()
    if any(part.is_symlink() for part in (destination, *destination.parents)):
        raise ValueError("Export destination must not contain symlinks")
    if destination.exists():
        raise ValueError("Export destination already exists; choose a fresh directory")
    return destination


def build(manifests, receipt_paths=(), admin_build=DEFAULT_ADMIN, pending_host_takes=False,
          pending_controls=(), limitations=(), recording_coverage=(), diagram_build=None,
          output_dir=None):
    output_dir = export_destination(output_dir) if output_dir is not None else None
    for destination in DESTINATIONS:
        if any(p.is_symlink() for p in (destination, *destination.parents)):
            raise ValueError("Output paths cannot contain symlinks")
        if destination.exists() and not destination.is_file():
            raise ValueError("Output destinations must be regular files")
    files, input_hashes, loaded = {}, {}, []
    if pending_host_takes and pending_controls:
        raise ValueError("Use either the legacy six-host flag or explicit pending controls")
    pending = list(LEGACY_HOST_PENDING if pending_host_takes else pending_controls)
    if len(pending) > 24 or len(limitations) > 12:
        raise ValueError("Too many pending controls or evidence limitations")
    pending = [text(value, "pending control", 160) for value in pending]
    limitations = [text(value, "evidence limitation", 600) for value in limitations]
    coverage_overrides = {}
    for specification in recording_coverage:
        scene_id, separator, coverage = specification.partition("=")
        if (not separator or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", scene_id)
                or coverage not in RECORDING_COVERAGE or scene_id in coverage_overrides):
            raise ValueError("Recording coverage must be a unique SCENE=request_to_result|approval_to_result|result_inspection|unknown")
        coverage_overrides[scene_id] = coverage

    def register(path, expected=None):
        path = safe_file(path)
        if path in DESTINATIONS and expected is not None:
            raise ValueError("A build input cannot be a destination")
        relative = path.relative_to(ROOT)
        if "raw" in relative.parts or path.suffix.lower() not in {".html", ".mp4", ".webm", ".jpg", ".jpeg", ".png", ".webp", ".json", ".md", ".txt", ".pdf"}:
            raise ValueError("Only explicit processed artifacts may be served")
        data = validate_hash(path, expected, path.name) if expected else path.read_bytes()
        # Root-relative evidence routes also match the admin guide's ../ links.
        route = "/" + (path.relative_to(OUTPUT.parent).as_posix() if path.is_relative_to(OUTPUT.parent) else relative.as_posix())
        if not re.fullmatch(r"/[A-Za-z0-9_./~-]+", route):
            raise ValueError("Artifact URL contains unsupported characters")
        item = {"path": relative.as_posix(), "bytes": len(data), "sha256": sha(data)}
        if route in files and files[route] != item:
            raise ValueError("Artifact routes collide")
        files[route] = item
        return route[1:]

    scene_ids = set()
    for manifest_path in manifests:
        manifest_path = safe_file(manifest_path)
        if manifest_path in DESTINATIONS:
            raise ValueError("A presentation output cannot be a processed input")
        raw = manifest_path.read_bytes()
        if len(raw) > 4_000_000:
            raise ValueError("Manifest exceeds the input limit")
        manifest = json.loads(raw)
        if manifest.get("schemaVersion") != 1 or not isinstance(manifest.get("scenes"), list) or not manifest["scenes"]:
            raise ValueError("Expected a nonempty schemaVersion 1 scene manifest")
        if manifest.get("synthetic") or "synthetic" in str(manifest.get("title", "")).lower():
            raise ValueError("Synthetic scenes cannot enter the native control deck")
        input_hashes[manifest_path.relative_to(ROOT).as_posix()] = sha(raw)
        evidence_index = {item["url"]: item for item in manifest.get("evidence", [])}
        for scene in manifest["scenes"]:
            scene_id = text(scene.get("id"), "scene id", 80)
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", scene_id) or scene_id in scene_ids:
                raise ValueError("Scene IDs must be unique safe identifiers")
            if len(scene_ids) >= 24:
                raise ValueError("At most 24 recorded scenes are supported")
            scene_ids.add(scene_id)
            source = scene.get("source", {})
            if source.get("kind") not in {"desktop-recording", "native-client-recording", "screen-recording", "terminal-recording", "browser-recording"}:
                raise ValueError("Every scene must identify real application capture")
            duration = finite(scene.get("duration"), "duration", .01)
            recorded = text(scene.get("recordedAt"), "recordedAt", 80)
            if datetime.fromisoformat(recorded.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError("recordedAt requires a timezone")
            provenance = scene.get("provenance", {})
            if not re.fullmatch(r"[0-9a-f]{64}", provenance.get("sourceSha256", "")):
                raise ValueError("Source capture provenance is required")
            if provenance.get("retimed") is not False or provenance.get("padded") is not False:
                raise ValueError("Control recordings must retain their actual timing")
            source_duration = finite(provenance.get("sourceDuration"), "source duration", .01)
            cut = provenance.get("cut", {})
            cut_start = finite(cut.get("start"), "cut start")
            cut_end = finite(cut.get("end"), "cut end", .01)
            if cut_start >= cut_end or cut_end > source_duration:
                raise ValueError("The cut must stay within the source capture")
            public_source = {"kind": source["kind"], "description": text(source.get("description"), "capture description", 1500)}
            public_provenance = {"sourceSha256": provenance["sourceSha256"], "sourceDuration": source_duration,
                                 "cut": {"start": cut_start, "end": cut_end}, "recordedAt": recorded,
                                 "retimed": False, "padded": False}
            if "audioIncluded" in provenance:
                if not isinstance(provenance["audioIncluded"], bool):
                    raise ValueError("Audio provenance must be boolean")
                public_provenance["audioIncluded"] = provenance["audioIncluded"]
            result = {"id": scene_id, "title": text(scene.get("title"), "title", 180),
                      "description": text(scene.get("description"), "description", 1500),
                      "evidenceScope": text(scene.get("evidenceScope"), "evidence scope"),
                      "duration": duration, "recordedAt": recorded, "source": public_source,
                      "provenance": public_provenance, "media": [], "cues": []}
            result["recordingCoverage"] = coverage_overrides.get(scene_id, scene.get("recordingCoverage", "unknown"))
            result["outcomeClass"] = scene.get("outcomeClass", "unknown")
            if result["recordingCoverage"] not in RECORDING_COVERAGE or result["outcomeClass"] not in OUTCOME_CLASSES:
                raise ValueError("Unsupported recording coverage or outcome classification")
            for media in scene.get("media", []):
                if media.get("type") not in {"video/mp4", "video/webm"} or media.get("decodeValidated") is not True:
                    raise ValueError("Only fully decoded MP4 or WebM media are supported")
                path = local_asset(media.get("url"), manifest_path.parent, manifest_path.parent)
                if path.suffix.lower() not in {".mp4", ".webm"}:
                    raise ValueError("Video path has an unsupported extension")
                for dimension in ("width", "height"):
                    value = finite(media.get(dimension), dimension, 1)
                    if value > 16384 or int(value) != value:
                        raise ValueError("Video dimensions must be bounded integers")
                for label in ("codec", "pixelFormat"):
                    text(media.get(label), label, 40)
                finite(media.get("fps"), "media frame rate", .01)
                finite(media.get("duration"), "media duration", .01)
                if not isinstance(media.get("audio"), bool):
                    raise ValueError("Media audio metadata must be boolean")
                finite(media.get("bytes"), "media bytes", 1)
                result["media"].append({**public_fields(media, ("type", "bytes", "sha256", "duration", "width", "height", "codec", "pixelFormat", "fps", "audio", "decodeValidated")), "url": register(path, media)})
            if not result["media"]:
                raise ValueError("Every scene needs processed video")
            for key in ("poster", "contactSheet"):
                metadata = scene.get(key)
                if metadata is None and key == "contactSheet":
                    continue
                if not isinstance(metadata, dict):
                    raise ValueError("Every scene needs a processed poster")
                path = local_asset(metadata.get("url"), manifest_path.parent, manifest_path.parent)
                if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    raise ValueError("Scene images must use a supported image format")
                if metadata.get("type") not in {"image/jpeg", "image/png", "image/webp"}:
                    raise ValueError("Scene image media type is unsupported")
                finite(metadata.get("bytes"), "image bytes", 1)
                if "time" in metadata and finite(metadata["time"], "image timestamp") > duration:
                    raise ValueError("Image timestamp must stay inside its clip")
                result[key] = {**public_fields(metadata, ("type", "bytes", "sha256", "time")), "url": register(path, metadata)}
            previous = -1
            for cue in scene.get("cues", []):
                at = finite(cue.get("time"), "cue time")
                if at <= previous or at > duration:
                    raise ValueError("Cue times must increase within the clip")
                previous = at
                cue_out = {"time": at, "label": text(cue.get("label"), "cue label", 200), "detail": text(cue.get("detail"), "cue detail")}
                if cue.get("evidence"):
                    metadata = evidence_index.get(cue["evidence"])
                    if not metadata:
                        raise ValueError("Cue evidence needs processed hash metadata")
                    path = local_asset(cue["evidence"], manifest_path.parent, manifest_path.parent)
                    cue_out["evidence"] = register(path, metadata)
                result["cues"].append(cue_out)
            result["presentation"] = dict(zip(("control", "enforcer", "outcome"), controls_for(scene)))
            loaded.append(result)

    if coverage_overrides.keys() - scene_ids:
        raise ValueError("A recording-coverage override names a scene absent from the manifests")
    if pending_host_takes and any(scene["id"].startswith("native-host-") for scene in loaded):
        raise ValueError("Host scenes require explicit pending controls instead of the old six-host flag")

    receipts, reconciled_phases, superseded_authority = [], {}, []
    auth_correlation, auth_review, command_evidence = None, None, None
    managed, managed_images, managed_receipt = None, {}, None
    has_council_decisions = False
    has_host_council_decisions = False
    command_rule_removed = False
    imds_approval_expired = False
    authenticated_before_capture = False
    for receipt_path in receipt_paths:
        receipt_path = safe_file(receipt_path)
        if receipt_path in DESTINATIONS or receipt_path.suffix not in {".json", ".md", ".txt"}:
            raise ValueError("Evidence must be an explicit receipt input")
        receipts.append({"path": receipt_path.relative_to(ROOT).as_posix(), "url": register(receipt_path), "sha256": sha(receipt_path.read_bytes())})
        if receipt_path.suffix == ".json":
            content = json.loads(receipt_path.read_text())
            if isinstance(content, dict) and content.get("kind") == "managed_native_presentation":
                if managed is not None:
                    raise ValueError("Supply only one managed presentation receipt")
                managed, managed_receipt = content, receipts[-1]
            if isinstance(content, dict) and content.get("kind") == "native_client_evidence_reconciliation" and content.get("bounded_four_outcomes_reconciled") is True:
                reconciled_phases = checked_phase_observations(content)
            if (isinstance(content, dict) and content.get("authenticated") is True
                    and content.get("method") == "SocialGitHub"
                    and content.get("source") == "EC2 standalone Kiro CLI whoami"):
                checked = datetime.fromisoformat(text(content.get("checked_at"), "authentication timestamp", 80).replace("Z", "+00:00"))
                earliest = min(datetime.fromisoformat(scene["recordedAt"].replace("Z", "+00:00")) for scene in loaded)
                latest = max(datetime.fromisoformat(scene["recordedAt"].replace("Z", "+00:00")) for scene in loaded)
                if checked.tzinfo is not None and 0 <= (earliest - checked).total_seconds() <= 86400 and (latest - checked).total_seconds() <= 86400:
                    authenticated_before_capture = True
            if isinstance(content, dict) and content.get("kind") == "bounded_native_evidence_attribution_review":
                previous = content.get("revision", {}).get("previous_review_sha256")
                if isinstance(previous, str) and re.fullmatch(r"[0-9a-f]{64}", previous):
                    superseded_authority.append({"previous": previous, "current": receipts[-1]["sha256"]})
            if isinstance(content, dict) and content.get("root_agreed_material_findings") is True and "review_candidate" in content:
                has_council_decisions = True
            if (isinstance(content, dict) and content.get("root_adopted_decisions") is True
                    and content.get("candidate", {}).get("name") == "host-controls-v1"
                    and {item.get("id") for item in content.get("decisions", [])} == {f"H{i}" for i in range(1, 9)}):
                has_host_council_decisions = True
            if (isinstance(content, dict) and content.get("kind") == "read_only_command_rule_cleanup"
                    and content.get("exact_marker_absent") is True and content.get("exact_rule_id_absent") is True
                    and content.get("removed_rule_pattern") == "KIROCREW_DEMO_COMMAND_CONTROL_20260913"):
                command_rule_removed = True
            if (isinstance(content, dict) and content.get("kind") == "native_approval_timeout_correlation"
                    and content.get("outcome") == "native_execution_approval_expired_unanswered"
                    and content.get("native_helper_execution_observed") is False
                    and content.get("native_imds_firewall_enforcement_established") is False
                    and str(content.get("exact_pending_input", {}).get("command", "")).endswith("/imds-tcp.py")):
                imds_approval_expired = True
            if isinstance(content, dict) and content.get("kind") == "reviewable_native_host_auth_correlation":
                if auth_correlation is not None:
                    raise ValueError("Supply only one native host authentication correlation")
                auth_correlation = (content, receipts[-1])
            if isinstance(content, dict) and content.get("kind") == "independent_native_host_auth_review":
                if auth_review is not None:
                    raise ValueError("Supply only one native host authentication review")
                auth_review = content
            if (isinstance(content, dict) and content.get("kind") == "native_host_observations"
                    and content.get("observation_source") == "persisted_native_history_before_observer"
                    and content.get("sel_interval_complete") is True):
                for turn in content.get("turns", []):
                    blocked = turn.get("native_blocked_rows", [])
                    command = blocked[0].get("input", {}).get("command") if len(blocked) == 1 else None
                    if (turn.get("outcome") == "native_hook_denial_observed"
                            and turn.get("first_enforcer") == "crew_configured_command_rule"
                            and turn.get("completed") is True
                            and turn.get("exact_recorded_inputs_available") is True
                            and turn.get("host_enforcement_established") is True
                            and isinstance(command, str) and command
                            and sum(event.get("error") == "hook_deny" and event.get("outcome") == "denied"
                                    and event.get("operation") == "Running: " + command
                                    for event in turn.get("session_sel", [])) == 1):
                        if command_evidence is not None:
                            raise ValueError("Supply only one matching configured-command observation")
                        command_evidence = receipts[-1]
    if managed is not None:
        managed, managed_images = checked_managed(managed, loaded, input_hashes, register, receipts)
    command_scene = next((scene for scene in loaded if scene["id"] == "native-host-command-denial-summary"), None)
    if command_scene is not None:
        command_scene["outcomeClass"] = "server_hook_denied" if command_evidence else "unknown"
        command_scene["presentation"] = {"control": "Configured command rule", "enforcer": "Crew hook, separate receipt" if command_evidence else "Not attributed by this build", "outcome": "Assistant denial summary"}
        if command_evidence:
            command_scene["attributionReceipt"] = command_evidence
    authenticated_scene = next((scene for scene in loaded if scene["id"] == "native-host-anonymous-http403"), None)
    if authenticated_scene is not None:
        authenticated_scene["outcomeClass"] = "unknown"
        authenticated_scene["presentation"] = {"control": "Anonymous Gateway request", "enforcer": "Not attributed by this build", "outcome": "Assistant reports HTTP 403"}
    if authenticated_scene is not None and auth_review is not None:
        if auth_correlation is None:
            raise ValueError("The host authentication review needs its exact correlation receipt")
        correlation, correlation_file = auth_correlation
        reviewed = auth_review.get("reviewed_receipt", {})
        result = correlation.get("native_helper_result", {})
        auth_events = correlation.get("matching_auth_sel", [])
        if (reviewed.get("path") != correlation_file["path"]
                or reviewed.get("sha256") != correlation_file["sha256"]
                or auth_review.get("verdict") != "bounded_gateway_token_auth_denial_supported"
                or auth_review.get("material_findings") != []
                or correlation.get("first_enforcer") != "gateway_token_auth"
                or correlation.get("outcome") != "native_anonymous_gateway_auth_denial_observed"
                or result.get("http_status") != 403
                or result.get("authorization_sent") is not False
                or result.get("cookies_sent") is not False
                or result.get("response_body_read") is not False
                or len(auth_events) != 1
                or auth_events[0].get("error") != "Token required"
                or auth_events[0].get("operation") != "dashboard.token_auth"
                or auth_events[0].get("resources") != "/api/security/posture"
                or auth_events[0].get("caller_identity") != "127.0.0.1"
                or auth_events[0].get("outcome") != "denied"):
            raise ValueError("Host authentication labels require the matching bounded review and anonymous HTTP 403 result")
        authenticated_scene["outcomeClass"] = "server_authentication_denied"
        authenticated_scene["presentation"] = {"control": "Gateway authentication", "enforcer": "EC2 Gateway token check; correlated receipt", "outcome": "Assistant reports HTTP 403"}
        authenticated_scene["attributionReceipt"] = correlation_file
    host_plan = None
    if pending:
        host_plan_path = ROOT / "docs/HOST-CONTROL-SCENARIOS.md"
        host_plan = register(host_plan_path)
        input_hashes[host_plan_path.relative_to(ROOT).as_posix()] = sha(host_plan_path.read_bytes())

    diagram_url = None
    if diagram_build:
        diagram_build = safe_file(diagram_build)
        dependency = json.loads(diagram_build.read_bytes())
        artifact = dependency.get("artifact", {})
        if (dependency.get("required_asset_files") != [artifact.get("path")]
                or dependency.get("external_asset_dependencies") != []
                or not str(artifact.get("path", "")).endswith(".html")):
            raise ValueError("The optional architecture diagram must be one self-contained HTML artifact")
        diagram_path = safe_file(ROOT / artifact["path"])
        diagram_url = register(diagram_path, artifact)
        if not diagram_path.is_relative_to(OUTPUT.parent):
            diagram_url = "../" + diagram_path.relative_to(ROOT).as_posix()
        register(diagram_build)
        input_hashes[diagram_build.relative_to(ROOT).as_posix()] = sha(diagram_build.read_bytes())
        input_hashes[artifact["path"]] = artifact["sha256"]

    admin_url, admin_images = None, {}
    if admin_build:
        admin_build = safe_file(admin_build)
        admin = json.loads(admin_build.read_bytes())
        if admin.get("kind") != "native_admin_tour_build":
            raise ValueError("Expected the separate native admin tour receipt")
        input_hashes[admin_build.relative_to(ROOT).as_posix()] = sha(admin_build.read_bytes())
        admin_inputs = {}
        for item in admin.get("outputs", []) + admin.get("sources", []) + admin.get("screenshots", []):
            url = register(ROOT / item["path"], item)
            admin_inputs[(ROOT / item["path"]).resolve()] = files["/" + url]
            if item["path"] == "output/kirocrew-admin-tour.html":
                admin_url = url
            if item["path"] in {"output/admin-console-native-20260913/01-live-security-posture.png", "output/admin-console-native-20260913/06-governance-status.png"}:
                admin_images[Path(item["path"]).name] = ROOT / item["path"]
        build_url = register(admin_build)
        admin_inputs[admin_build] = files["/" + build_url]
        if not admin_url:
            raise ValueError("Admin build has no guide HTML")
        # The guide is authored for a local output/ folder. Its ../output links
        # normalize differently at the preview root. Alias only links to files
        # already declared and hash-checked by its receipt, never new paths.
        admin_html = ROOT / "output/kirocrew-admin-tour.html"
        for reference in re.findall(r'(?:src|href)="([^"]+)"', admin_html.read_text()):
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or reference.startswith("#"):
                continue
            target = (admin_html.parent / parsed.path).resolve()
            if target not in admin_inputs:
                raise ValueError("Admin guide links outside its explicit receipt")
            route = urlsplit(urljoin("http://localhost/" + admin_url, reference)).path
            if parsed.query or parsed.fragment or not re.fullmatch(r"/[A-Za-z0-9_./~-]+", route):
                raise ValueError("Unsupported admin guide artifact route")
            if route in files and files[route] != admin_inputs[target]:
                raise ValueError("Admin guide artifact routes collide")
            files[route] = admin_inputs[target]

    slides, slide_notes = [], []

    def add(title, body, note, section="Context", classes="", footer=""):
        position = len(slides) + 1
        slides.append(f'<section class="slide {classes}" id="slide-{position}" data-title="{e(title, quote=True)}" data-section="{e(section, quote=True)}" aria-label="Slide {position}: {e(title, quote=True)}"{" hidden" if position > 1 else ""}>{body}<footer class="slide-footer"><span>{e(footer)}</span><span class="number">{position:02d}</span></footer><aside class="speaker-notes" hidden><p>{e(note)}</p></aside></section>')
        slide_notes.append((title, note))

    guide_link = f'<a class="slide-link" href="{admin_url}" target="_blank" rel="noopener">Open the admin tour</a>' if admin_url else ""
    diagram_link = f' <a href="{diagram_url}" target="_blank" rel="noopener">Explore the architecture and export it.</a>' if diagram_url else ""
    cover_intro = "Real requests from Kiro Crew Nightly, with the Gateway and original Kiro CLI backend running on an ARM instance."
    cover_count = f"{len(loaded)} recorded scenes"
    if managed:
        cover_intro = "A root-managed Gateway on EC2 sets the execution limits. The Mac supplies prompts, approvals and MCP controls."
        cover_count = f"1 managed-policy recording · {len(loaded) - 1} earlier control recordings"
    add("Server controls for a Mac client", f'<div class="slide-body hero"><p class="eyebrow">KiroCrew on EC2</p><h1>Server controls<br>for a Mac client</h1><p class="hero-intro">{cover_intro}</p><p class="cover-count">{cover_count}</p></div><div class="cover-bottom"><p>Local Gateway off.<br>Remote workspace on EC2.</p>{guide_link}</div>',
        "This focused edition contains the supplied recordings of real application behavior. The Mac endpoint is the only client platform in scope. " + ("The supplied authentication receipt confirms that the original EC2 Kiro CLI backend was signed in through GitHub before capture. " if authenticated_before_capture else "This edition does not establish backend sign-in independently. ") + "The media manifest describes visible behavior. " + ("Explicit supporting receipts accompany this edition for separate server-attribution review. " if receipts else "Server attribution requires separate supporting receipts. ") + "Playback controls operate recordings and do not send requests to the live system. Slide dates use Eastern Daylight Time (UTC-4); source capture timestamps retain UTC.", classes="dark control-cover", footer="Recorded September 13, 2026 · Eastern Time (UTC−4)")
    architecture_note = "The diagram preserves a single endpoint-control box. The Mac connects through the configured SSH tunnel to the ARM EC2 host in us-east-1. Gateway, Kiro CLI, workspace, host controls and the MCP service reside together on that host. The MCP service has a separate process identity and fixed demo grants. Its AWS calls use the instance role. "
    architecture_note += ("The current Gateway loads an unsigned file policy from /etc/kirocrew-demo/security-policy.json through its protected systemd environment. Root owns the policy and protected ancestors; the Crew account cannot replace it. The policy requires Linux cc, denies YOLO, the exact crew_denied MCP tool, the harmless managed-command marker and the pinned S3 upload rule, plus named filesystem paths. Host root can replace this policy. Ordinary Crew configuration remains writable for MCP availability. The previous eight clips predate this change. Linux cc is not macOS Seatbelt or strict isolation; neither the loaded floor nor the denied tool proves exact-tool sandbox execution. " if managed else "The recorded Mac session had owner privileges, and no enterprise governance floor is active. Crew configuration remains writable by the crew account. The host diagram does not establish immutable multi-user policy, failover or EDR. ")
    architecture_note += "Existing infrastructure supports caller-supplied VPC and subnet parameters without adding NAT gateways or load balancers."
    architecture_footer = "Root-managed file policy. User settings can narrow access. Host root can replace the policy." if managed else "Owner connection. Crew configuration is owner editable. No enterprise governance floor."
    add("Execution and host controls stay on EC2", '<header class="slide-header"><p class="eyebrow">Deployment</p><h2>Execution and host controls stay on EC2</h2></header><div class="slide-body">' + architecture(bool(managed)) + '<p class="architecture-caption">The Mac carries the chat and approval UI. EC2 holds the execution environment, policy checks and fixed MCP service.' + diagram_link + '</p></div>',
        architecture_note, footer=architecture_footer)
    # Balance the pages while keeping each matrix at six rows or fewer.
    matrix_count = math.ceil(len(loaded) / 6)
    page_size, longer_pages = divmod(len(loaded), matrix_count)
    first_clip = 3 + matrix_count
    for page_index in range(matrix_count):
        offset = page_index * page_size + min(page_index, longer_pages)
        group = loaded[offset:offset + page_size + (page_index < longer_pages)]
        rows = []
        for index, scene in enumerate(group, offset):
            p = scene["presentation"]
            capture_label = "Before managed policy. " if managed and scene["id"] != managed["native"]["scene_id"] else "Managed policy. " if managed else ""
            coverage_label = {"request_to_result": "Request to result. ", "approval_to_result": "Approval to result. ", "result_inspection": "Result inspection. ", "unknown": ""}[scene["recordingCoverage"]]
            rows.append(f'<tr><td><a href="#slide-{first_clip + index}">{e(p["control"])}</a><span class="scene-time">{capture_label}{coverage_label}About {scene["duration"]:.0f} seconds</span></td><td>{e(p["enforcer"])}</td><td>{e(p["outcome"])}</td></tr>')
        last_page = page_index == matrix_count - 1
        pending_line = ""
        if pending and last_page:
            pending_line = '<p class="pending-controls"><strong>Unfinished in this edition:</strong> ' + e(", ".join(pending)) + '.'
            if "IMDS execution" in pending:
                if imds_approval_expired:
                    pending_line += ' The earlier IMDS execution approval expired unanswered.'
                pending_line += ' This edition contains no completed IMDS execution or firewall result.'
            pending_line += f' <a href="{host_plan}" target="_blank" rel="noopener">Shot list</a></p>'
        group_ids = {scene["id"] for scene in group}
        map_note = "This page covers " + ", ".join(scene["presentation"]["control"] for scene in group) + ". The scene count includes successful baselines, so it is not a count of verified denials. "
        if reconciled_phases and group_ids & {"native-allowed-read", "native-crew-denial", "native-mcp-denial", "native-iam-denial"}:
            map_note += "The MCP comparison follows the bounded four-outcome reconciliation: Crew denial precedes MCP dispatch; the MCP grant refusal precedes AWS dispatch; allowed and IAM results join native output to the service and AWS request IDs. The original passive collector remains incomplete. The reconciliation uses the complete MCP journal and service-continuity checks for these four turns. "
        if "native-memory-assignment-refusal" in group_ids:
            map_note += "The private-memory guard stops an unassigned conversation before a tool turn; restricted human-role RBAC is outside that observation. "
        if "native-host-workspace-read" in group_ids:
            map_note += "The permitted workspace read is a positive native fs_read baseline, with no approval card. "
        if "native-host-command-denial-summary" in group_ids:
            map_note += "The command recording inspects an assistant summary after denial, with tool history collapsed. "
            if command_evidence:
                map_note += "Separate persisted native history and scoped SEL establish the Crew hook decision. "
            if command_rule_removed:
                map_note += "The temporary marker rule was removed after its take. "
        if "native-host-anonymous-http403" in group_ids:
            map_note += "The authentication recording starts at execution approval and ends with the assistant's HTTP 403 summary. An EC2 helper sends one anonymous loopback request while the Mac session stays authenticated. Its native_enforcement_verified:false field is preserved. "
            if authenticated_scene.get("attributionReceipt"):
                map_note += "Combined native and Gateway receipts support bounded token-auth attribution. "
        if managed:
            map_note += "Earlier recordings retain the policy and evidence boundaries of their original takes. The new managed MCP denial follows retirement of the duplicate mutable hook and is the only filmed turn under the new policy. A fresh permitted read was verified in an earlier unfilmed managed take. "
        if pending and last_page:
            map_note += "Unfinished native evidence in this edition: " + ", ".join(pending) + ". "
            if "IMDS execution" in pending:
                map_note += "The IMDS helper's source read completed. "
                if imds_approval_expired:
                    map_note += "The execution approval expired unanswered after ten minutes, with no observed helper execution. The earlier observer-expiry snapshot remains preserved as a historical receipt. "
                map_note += "This edition contains no completed IMDS execution or firewall result. "
        if limitations and last_page:
            map_note += "Retained limitations: " + " ".join(limitations)
        add("The control decides where the request stops", '<header class="slide-header"><p class="eyebrow">Recorded demonstrations</p><h2>The control decides<br>where the request stops</h2></header><div class="slide-body"><table class="control-table"><thead><tr><th scope="col">Demonstration</th><th scope="col">Decision point</th><th scope="col">Visible result</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>' + pending_line + '</div>',
            map_note, section="Control map", footer=f"Recording coverage and server attribution are separate. Page {page_index + 1} of {matrix_count}.")

    for scene in loaded:
        width, height = (int(scene["media"][0][key]) for key in ("width", "height"))
        title, description = scene["title"], scene["description"]
        proof_line = ""
        scope_line = f'About {scene["duration"]:.0f} seconds. {scene["presentation"]["enforcer"]}. Full evidence scope in notes.'
        if managed and scene["id"] == managed["native"]["scene_id"]:
            title = "A managed policy blocks a locally enabled tool"
            description = "The Mac requests crew_denied. The Gateway blocks it automatically, then the user expands the native notice to read the policy rule."
            scope_line = "Fresh managed-policy take. The earlier allowed control was verified separately and was not filmed."
            proof_line = "Native history and policy-layer SEL identify the deny. The complete, stable MCP journal interval has no arrival."
        if scene["id"] == "native-memory-assignment-refusal":
            title = "Private memory requires an assigned conversation"
            description = "An existing conversation switches to a private-store alias. The server refuses its first fixture request before tools run."
            scope_line = "Conversation binding only. fs_read never ran in this attempt. Human-role RBAC is outside its scope."
        elif scene["id"] == "native-crew-denial":
            scope_line = (f'About {scene["duration"]:.0f}s. Earlier owner-editable Crew hook. ' if managed else f'About {scene["duration"]:.0f}s. Owner-editable Crew; no enterprise floor. ') + ("Four bounded outcomes reconciled; original collector incomplete." if "crew" in reconciled_phases else "Full evidence scope in notes.")
        elif scene["id"] == "native-iam-denial":
            scope_line = "Role attribution uses instance-profile receipts. No per-request STS identity was collected."
        elif scene["id"] == "native-host-workspace-read":
            description = "Read a public canary in the EC2 workspace. Native fs_read returns its contents; the clip ends on the expanded tool output."
        elif scene["id"] == "native-host-command-denial-summary":
            description = "The completed conversation shows the marker command and the assistant's denial summary. Tool history stays collapsed."
        elif scene["id"] == "native-host-anonymous-http403":
            title = "Approve the helper; read the 403 summary"
            description = "An EC2 helper sends one anonymous loopback request. The Mac session stays authenticated. The clip shows Allow once through the assistant's 403 summary; native Output stays collapsed."
        if scene["recordingCoverage"] == "result_inspection":
            scope_line = "Result inspection only. Request submission occurred before this recording."
        elif scene["recordingCoverage"] == "approval_to_result":
            scope_line = "Footage starts at native approval. Earlier conversation steps are outside the cut."
            if scene["id"] == "native-host-anonymous-http403":
                scope_line = "Footage starts at native approval. Prompt submission and helper-source review occurred earlier."
        if scene["id"] == "native-host-command-denial-summary":
            scope_line = "Recorded after denial; tool history collapsed. " + ("Crew hook: separate receipts. " if command_evidence else "Server outcome is unattributed. ") + ("Temporary marker rule removed after the take." if command_rule_removed else "Rule cleanup is not bound to this build.")
        if scene["outcomeClass"] == "model_refusal":
            scope_line = "Model response only. This scene does not establish tool execution or server enforcement."
        for phase, scene_id in (("allow", "native-allowed-read"), ("iam", "native-iam-denial")):
            if scene["id"] != scene_id:
                continue
            joined = reconciled_phases.get(phase, {}).get("joined_native_service_results", [])
            if len(joined) == 1:
                result = joined[0]
                request_id = text(result.get("aws_request_id"), "AWS request ID", 80)
                if phase == "allow":
                    if result.get("ok") is not True or result.get("layer") != "aws":
                        raise ValueError("The allowed proof must be a successful AWS result")
                    byte_count = int(finite(result.get("object_bytes"), "object byte count"))
                    digest = text(result.get("object_sha256"), "object digest", 64)
                    if not re.fullmatch(r"[0-9a-f]{64}", digest):
                        raise ValueError("The allowed object digest is invalid")
                    proof_line = f'{byte_count} bytes. SHA-256 prefix {digest[:12]}. Native and service request ID {request_id}.'
                else:
                    if result.get("error_code") != "AccessDenied" or result.get("http_status") != 403:
                        raise ValueError("The IAM proof must be the expected AWS refusal")
                    proof_line = f'Native and service results match: AccessDenied, HTTP 403, AWS request ID {request_id}.'
        if scene["id"] == "native-mcp-denial" and "mcp" in reconciled_phases:
            proof_line = "Native and service results agree on tool_grant_denied. The matched invocation has no AWS dispatch."
        if scene["id"] == "native-crew-denial" and "crew" in reconciled_phases:
            proof_line = "The blocked native turn matches an isolated SEL hook denial. The MCP journal has no matching arrival."
        if scene["id"] == "native-host-anonymous-http403" and scene.get("attributionReceipt"):
            proof_line = "Helper reports native_enforcement_verified:false. Combined native-history and Gateway receipts support token-auth attribution."
        sources = ''.join(f'<source src="{e(m["url"], quote=True)}" type="{e(m["type"], quote=True)}">' for m in scene["media"])
        cues = []
        for cue in scene["cues"]:
            evidence = f' data-cue-evidence="{e(cue["evidence"], quote=True)}"' if cue.get("evidence") else ""
            cues.append(f'<button type="button" data-cue-time="{cue["time"]}" data-cue-label="{e(cue["label"], quote=True)}" data-cue-detail="{e(cue["detail"], quote=True)}"{evidence}><time>{int(cue["time"]) // 60}:{int(cue["time"]) % 60:02d}</time><span>{e(cue["label"])}</span></button>')
        downloads = f'<a href="{scene["media"][0]["url"]}" target="_blank" rel="noopener">Open video full size</a><a href="{scene["media"][0]["url"]}" download>Download clip</a>'
        if scene.get("contactSheet"):
            downloads += f'<a href="{scene["contactSheet"]["url"]}" target="_blank" rel="noopener">Contact sheet</a>'
        proof_html = f'<p class="scene-proof">{e(proof_line)}</p>' if proof_line else ""
        scene_heading = scene["presentation"]["control"] + (" · Before managed policy" if managed and scene["id"] != managed["native"]["scene_id"] else " · Managed policy" if managed else "")
        body = f'<header class="slide-header"><p class="eyebrow">{e(scene_heading)}</p><h2>{e(title)}</h2><p class="demo-description">{e(description)}</p>{proof_html}</header><div class="demo-layout"><div class="demo-screen"><video controls muted playsinline width="{width}" height="{height}" style="aspect-ratio:{width}/{height}" preload="metadata" poster="{scene["poster"]["url"]}" aria-label="Recorded demonstration: {e(title, quote=True)}">{sources}Your browser does not support this video.</video><div class="demo-controls"><button class="demo-replay" type="button">Replay</button><button class="demo-next-cue" type="button">Next chapter</button><label><input class="demo-guided" type="checkbox"> Pause at chapters</label></div><p class="demo-status" role="status" aria-live="polite">Select a chapter to seek and pause.</p></div><aside class="demo-chapters" aria-label="Recording chapters"><h3>Chapters</h3><div class="demo-cues">{"".join(cues)}</div><div class="demo-cue-detail" aria-live="polite"></div></aside></div><div class="scene-downloads">{downloads}</div>'
        note = f'{scene["evidenceScope"]} Recorded {scene["recordedAt"]}. Source capture SHA-256: {scene["provenance"]["sourceSha256"]}. Cut: {json.dumps(scene["provenance"].get("cut"))}. ' + ' '.join(f'{cue["time"]:g}s: {cue["label"]}. {cue["detail"]}' for cue in scene["cues"])
        if scene["recordingCoverage"] == "result_inspection":
            note += " This footage inspects the result after completion. The request submission is outside the clip, so it is not a continuous request-to-result recording."
        elif scene["recordingCoverage"] == "approval_to_result":
            note += " This continuous cut starts at native execution approval and ends with the reported result. Earlier conversation steps are outside the cut."
            if scene["id"] == "native-host-anonymous-http403":
                note += " The visible result is the assistant's HTTP 403 summary; actual native tool output stays collapsed. Prompt submission and the earlier helper-source read and approval are outside the cut."
        elif scene["recordingCoverage"] == "request_to_result":
            note += " The supplied recording metadata identifies a continuous request-to-result take."
        if scene["id"] == "native-host-command-denial-summary":
            note += " The recording shows the submitted prompt and assistant summary after the denial. The tool history stays collapsed; the actual blocked tool output and policy reason are not visible. " + ("Server-hook attribution comes from the supplied native history and scoped SEL receipt." if command_evidence else "This build has no matching supplied server-attribution receipt.")
        if proof_line:
            note += " " + proof_line
            if scene["id"] == "native-host-anonymous-http403" and scene.get("attributionReceipt"):
                note += " Attribution follows the supplied correlation receipt and its independent review. The helper's native_enforcement_verified:false field is retained. Source read and execution were two separate calls, each approved once. SEL correlation uses the unique route, caller, reason and approval-to-result interval, without a direct SEL-to-tool trace ID. This demonstrates anonymous Gateway token authentication; restricted human-role RBAC and immutable managed policy remain outside its scope."
            elif managed and scene["id"] == managed["native"]["scene_id"]:
                note += " The exact native tool ID joins the trace to the blocked row. SEL correlation uses the isolated slot, tool, policy reason and time, plus adjacent hash-chain linkage; SEL has no direct native trace or tool ID. The duplicate mutable Crew denial was retired before this take. No permission prompt appeared. This take contains only ui4 denial; visible ui3 conversation history and the separately verified allowed read are outside its filmed sequence. The original dark host notice stays unchanged. The policy-layer denial does not establish exact-tool sandbox execution, human-role RBAC or a managed MCP registry."
            else:
                note += " Layer attribution follows the supplied bounded four-outcome reconciliation. It uses the complete MCP journal and service-continuity checks for these four turns. The original passive collector remains incomplete. Crew correlation uses the isolated turn because SEL has no direct trace-to-tool-call join for that denial."
        if scene["id"] == "native-iam-denial" and "iam" in reconciled_phases:
            note += " AWS role attribution uses the existing instance-profile/cutover receipts and after-capture source, service and policy checks. No per-request STS caller identity was collected. Fixture HEAD checks establish existence and metadata, without recomputing the denied object's content digest. Process observations do not establish that a sampled PID overlapped a pending approval. These limits remain in the linked authority review."
        if scene.get("poster", {}).get("time") is not None:
            note += f' The poster uses an actual result frame at {scene["poster"]["time"]:g} seconds in this clip. Video bytes and cut boundaries remain unchanged.'
        if managed and scene["id"] != managed["native"]["scene_id"]:
            note = "Recorded before the root-managed policy was installed. This earlier take retains its original configuration, outcome and limits; it does not verify the current managed floor. " + note
        add(title, body, note, section="Recorded controls", classes="recorded-demo native-scene", footer=scope_line)

    def managed_detail(role, box, css_class, caption):
        item = managed_images[role]
        x, y, width, height = box
        if x < 0 or y < 0 or x + width > item["width"] or y + height > item["height"]:
            raise ValueError("Managed screenshot detail must stay inside the original image")
        data = validate_hash(ROOT / item["path"], item, "managed screenshot")
        mime = "image/jpeg" if data.startswith(b"\xff\xd8\xff") else "image/png"
        uri = "data:" + mime + ";base64," + base64.b64encode(data).decode()
        return f'<div class="admin-detail-wrap"><div class="admin-detail {css_class}"><svg viewBox="{x} {y} {width} {height}" role="img" aria-label="{e(caption, quote=True)}"><image x="0" y="0" width="{item["width"]}" height="{item["height"]}" href="{uri}"/></svg></div><button class="admin-expand" data-image="{uri}" data-caption="{e(caption, quote=True)}">Expand full screenshot</button></div>'

    if managed:
        enabled = managed_detail("mcp_enabled", (318, 325, 720, 146), "mcp-enabled", "Connections: aws-enforcement is enabled for Crew, with four tools listed. Provider-global settings are off.")
        staged = managed_detail("mcp_staged", (918, 231, 591, 56), "mcp-staged", "Apply and Discard for one staged local tool restriction. The change was discarded after capture.")
        session = managed_detail("session_mcp", (350, 84, 305, 342), "session-inventory", "Session MCP inventory: aws-enforcement started, with 0 of 4 specs loaded and deferred tools listed. This is the actual captured inventory, not four loaded specs.")
        add("MCP availability and execution permission", '<header class="slide-header"><p class="eyebrow">The user’s MCP controls</p><h2>MCP availability and execution permission</h2></header><div class="slide-body"><div><h3>Connections → MCP Servers</h3><p>The Crew-scoped server is enabled. Its four tools remain visible, including <code>crew_denied</code>.</p>' + enabled + '<p>A user can stage a narrower tool selection. This example was discarded.</p>' + staged + '</div><div><h3>Session options</h3><p>The server started. The inventory shows <strong>0/4 specs loaded</strong>, with tools deferred until needed.</p>' + session + '</div></div>',
            "The actual Connections manager and session-options menu expose different state. Connections manages the Crew-only server registration and local tool availability; provider-global settings remain off. The staged restriction on crew_denied had Apply and Discard controls and was discarded, so no local narrowing was applied. The session menu lists the configured tools and its own startup/loading report: aws-enforcement started, 0 of 4 specs loaded, Tool Search Deferred. It does not say all four specs were loaded. A locally enabled or listed tool remains subject to the root-managed execution policy. The current manager has no per-tool governance lock badge and does not establish an enterprise MCP registry. The user approval menu separately shows Normal selected, Reads and Trust available, and YOLO absent; no mode was changed for the screenshot. The new filmed denial verifies the policy check, while the earlier allowed managed read has separate unfilmed native evidence.",
            section="User MCP", classes="managed-user", footer="Local availability can narrow access. The Gateway still evaluates each attempted tool against policy.")
        governance = managed_detail("governance", (590, 347, 933, 112), "admin-governance", "Current Governance Policy: Source file, fetched at startup only, Policy v1. Root-protected policy digest is bound in the managed receipts.")
        command = managed_detail("managed_command", (610, 495, 905, 66), "admin-posture", "Current S3 upload deny: the switch is on and disabled, with the organization-policy explanation. This capture establishes the UI state, not execution of an S3 upload.")
        add("Managed policy and admin evidence", '<header class="slide-header"><p class="eyebrow">Separate admin screenshot tour</p><h2>Managed policy and admin evidence</h2></header><div class="slide-body"><div class="admin-examples"><div><h3>Policy v1 loads at startup</h3><p>Root-owned file. Linux <code>cc</code> minimum. YOLO denied; Reads and Trust remain available.</p></div>' + governance + '<div><h3>An administrator-pinned command</h3><p>The S3 upload deny is on. Its switch is disabled by policy; ordinary MCP availability stays editable.</p></div>' + command + '</div><dl class="admin-sources"><div><dt>Gateway telemetry</dt><dd>Backend activity and performance metrics.</dd></div><div><dt>Collection events</dt><dd>Mac and EC2 health samples and errors.</dd></div><div><dt>SEL evidence</dt><dd>Security decisions in receipts. The portal lists coverage.</dd></div><div><dt>MCP audit</dt><dd>Service decisions and AWS dispatch in the journal.</dd></div></dl><div class="admin-controls">' + guide_link + '<p>Current policy views; earlier telemetry retains its capture date.</p></div></div>',
            "The Governance view reports the file source, startup-only fetch and Policy v1. Its full screenshot also displays the cc floor and governed scopes. The protected policy and systemd environment were verified separately. The S3 upload rule’s on/disabled switch and policy explanation are actual UI evidence, distinct from a native command-execution test. The policy also denies the harmless managed-command marker. Shell Denied Commands, the managed MCP rule and the earlier mutable auto_deny_tools hook are different controls; the duplicate mutable MCP denial was retired before the new take. The owner cannot replace the protected policy file, while host root retains that authority. The dashboard terminal setting is off; a disposable Crew-UID child in the actual Gateway cgroup received EPERM when opening a PTY. Six Kiro CLI descendants showed seccomp mode2, NoNewPrivs1 and different mount namespaces in a point-in-time check. Those observations do not establish exact-tool sandbox behavior. Sensitive-path read, protected-path write and native IMDS execution remain unfinished. Linux cc is neither Seatbelt nor strict isolation. The screenshot tour retains prior telemetry and health captures with their dates; configured control counts, backend metrics, collection health, SEL decisions and service audit have separate scopes.",
            section="Admin tour", classes="managed-admin", footer="The file policy is protected from Crew edits. Host root remains the administrator.")

    if admin_url and not managed:
        def screenshot_detail(filename, box, css_class, caption):
            path = admin_images.get(filename)
            if path is None:
                raise ValueError("Admin tour needs the current posture and governance screenshots")
            data = path.read_bytes()
            mime = "image/jpeg" if data.startswith(b"\xff\xd8\xff") else "image/png"
            uri = "data:" + mime + ";base64," + base64.b64encode(data).decode()
            return f'<div class="admin-detail-wrap"><div class="admin-detail {css_class}"><svg viewBox="{box}" role="img" aria-label="{e(caption, quote=True)}"><image x="0" y="0" width="1555" height="1324" href="{uri}"/></svg></div><button class="admin-expand" data-image="{uri}" data-caption="{e(caption, quote=True)}">Expand full screenshot</button></div>'
        posture = screenshot_detail("01-live-security-posture.png", "590 549 929 132", "admin-posture", "Configured coverage catalog: three complete rows for sensitive paths, protected paths and shell command rules. Sensitive-path and protected-path denial tests are unfinished in this edition. Detail from the September 13 Eastern Time admin screenshot.")
        governance = screenshot_detail("06-governance-status.png", "584 352 940 103", "admin-governance", "No enterprise policy in effect. Detail from the September 13 governance screenshot. Expand for the full original capture.")
        admin_body = '<header class="slide-header"><p class="eyebrow">Separate screenshot walkthrough</p><h2>Admin settings and logs have different jobs</h2></header><div class="slide-body"><div class="admin-examples"><div><h3>Configured coverage catalog</h3><p>Sensitive-path and protected-path denial tests are unfinished in this edition.</p><p class="control-split">Shell rules: <strong>Denied Commands</strong>.<br>Crew MCP hook: <code>auto_deny_tools</code>.</p></div>' + posture + '<div><h3>No enterprise policy is active</h3><p>The owner can edit Crew configuration. This demo has no immutable governance floor.</p></div>' + governance + '</div><dl class="admin-sources"><div><dt>Gateway telemetry</dt><dd>Backend activity and performance metrics.</dd></div><div><dt>Collection events</dt><dd>Mac and EC2 health samples and errors.</dd></div><div><dt>SEL evidence</dt><dd>Security decisions in receipts. The portal lists coverage.</dd></div><div><dt>MCP audit</dt><dd>Service decisions and AWS dispatch in the service journal.</dd></div></dl><div class="admin-controls">' + guide_link + '<p>September 13, Eastern Time. Original screenshots expand separately.</p></div></div>'
        add("Admin settings and logs have different jobs", admin_body,
            "The slide magnifies two rectangular details from the unchanged September 13 posture and governance screenshots. Each opens its complete original screenshot. The separate guide presents full screenshots with capture dates, route-specific explanations and full-size inspection. Live Security Posture reports configured coverage. Its SEL section lists coverage, with no live security-event viewer. Denied Commands controls shell rules, while auto_deny_tools controls the separate Crew MCP hook. The approval page's six-hour setting governs the next auto-approve period. The session remained interactive for these demonstrations. Governance reports no enterprise policy in effect. Native Gateway telemetry describes backend activity. The custom collection log reports client and server health events. SEL decisions and MCP audit records are separate evidence sources.", section="Admin tour", footer="Configured coverage, operational telemetry and security evidence have separate scopes.")

    selected_receipts = {
        "reconciliation.json": "Native and server result joins",
        "authority-attribution-review.json": "AWS and MCP authority review",
        "media-review-mcp-controls.json": "Native MCP footage review",
        "poster-review-v2.json": "Result poster review",
        "authenticated.json": "Fresh Kiro CLI sign-in",
        "assignment-diagnostic.json": "Private-memory guard diagnostic",
        "council-decision-summary.json": "Agreed Grok and Opus revisions",
    }
    if any(scene["id"].startswith("native-host-") for scene in loaded):
        selected_receipts = {
            "reconciliation.json": "Native and MCP result joins",
            "authority-attribution-review.json": "AWS and MCP authority review",
            "command-observations-v2.json": "Command history and Crew denial",
            "auth-correlation.json": "Anonymous request and Gateway denial",
            "auth-review.json": "Independent authentication review",
            "media-review-host-controls.json": "Host footage and recording gaps",
            "council-decision-summary.json": "Earlier Grok and Opus revisions",
        }
    visible_receipts = [r for r in receipts if Path(r["path"]).name in selected_receipts
                        and not (has_host_council_decisions and Path(r["path"]).name == "council-decision-summary.json"
                                 and "council-host-v1" not in Path(r["path"]).parts)]
    evidence_links = ''.join(f'<a href="{r["url"]}" target="_blank" rel="noopener">{e("Host-edition Grok and Opus decisions" if "council-host-v1" in Path(r["path"]).parts else selected_receipts[Path(r["path"]).name])}</a>' for r in visible_receipts)
    evidence_note = "Supporting receipts" if evidence_links else "The recording manifest lists the supporting receipts."
    council_note = "The external Grok and Opus council reviewed the earlier ten-slide candidate and requested changes. This derivative incorporates the agreed changes, followed by No AI Slop editing. Its changed bytes need a fresh root browser review and local read-only review. The external verdicts do not constitute exact-model review of this derivative. " if has_council_decisions else "Review receipts apply to their exact candidates. Prior reviews do not automatically cover this derivative. "
    if has_host_council_decisions:
        council_note = "Grok 4.6 and Opus 5 reviewed all fourteen slide screenshots and supporting notes for the preceding host-edition candidate. Both requested changes. This derivative incorporates the adopted H1-H8 decisions, followed by No AI Slop editing. The council did not play the videos or inspect live systems; its original verdicts remain unchanged. The revised bytes require a separate browser delta and local static review. Exact external-model acceptance of this derivative is not claimed. "
    if not managed:
        add("The recordings and evidence stay together", f'<header class="slide-header"><p class="eyebrow">Presentation assets</p><h2>The recordings and evidence stay together</h2></header><div class="slide-body artifact-grid"><div class="artifact-list"><div class="artifact-row"><b>01</b><div><a href="{NOTES.name}" download>Speaker notes</a><p>Scene scope, authority and interpretation.</p></div></div><div class="artifact-row"><b>02</b><div><a href="{PUBLIC.name}" download>Recording manifest</a><p>Clip paths, chapters and source capture hashes.</p></div></div><div class="artifact-row"><b>03</b><div><a href="{BUILD.name}" download>Build receipt</a><p>Exact files and hashes for this edition.</p></div></div></div><div><p class="receipt-heading">{e(evidence_note)}</p><div class="plain-links receipt-links">{evidence_links}</div><p class="note" style="margin-top:1.5cqw">Video slides include downloads and full-size playback. <strong>Print / PDF</strong> creates a static copy.</p></div></div>',
            "The build validates processed-media hashes, sizes, decoded-media flags, capture provenance and chapter bounds. Artifact integrity and enforcement acceptance have separate reviews. All supplied receipts appear in the recording manifest and these notes. " + council_note + "The preview server serves only the hash-bound allowlist and supports video byte ranges. Presentation controls do not execute demo commands.", section="Artifacts", classes="lilac", footer="Existing VPC/subnet support. No new VPC, NAT gateway or load balancer. GitHub Actions out of scope.")
    else:
        setup_links = {}
        for label, relative in (("Project skill", ".agents/skills/kirocrew-demo/SKILL.md"), ("Managed walkthrough", "docs/MANAGED-DEMO.md"), ("Live setup", "docs/LIVE-SETUP.md")):
            path = safe_file(ROOT / relative)
            setup_links[label] = register(path)
            input_hashes[relative] = sha(path.read_bytes())
        managed_labels = {"managed-presentation.json": "Current policy and capture scope", "native-managed-ui4-verification.json": "Recorded managed denial", "native-managed-artifact-review.json": "Independent native evidence review", "native-managed-verification.json": "Unfilmed managed allowed control", "host-runtime-check.json": "Host protection checks", "media-review.json": "New recording scope and quality"}
        managed_evidence_links = ''.join(f'<a href="{r["url"]}" target="_blank" rel="noopener">{e(managed_labels[Path(r["path"]).name])}</a>' for r in receipts if Path(r["path"]).name in managed_labels)
        add("Reproduce the presentation or set up a host", f'<header class="slide-header"><p class="eyebrow">Project skill and portable assets</p><h2>Reproduce the presentation or set up a host</h2></header><div class="slide-body artifact-grid"><div><p class="replication-copy">Use the <a href="{setup_links["Project skill"]}" target="_blank" rel="noopener">kirocrew-demo project skill</a> to present, rebuild, set up or record this demo.</p><p class="reproduce-command"><code>python3 scripts/build-demo-presentation.py --output-dir .build/presentation-export</code></p><p class="replication-copy">Rebuild the recorded edition from a checkout with Python 3.9+. The returned preview command runs its included local server.</p><div class="artifact-inline"><a href="{NOTES.name}" download>Notes</a><a href="{PUBLIC.name}" download>Recording manifest</a><a href="{BUILD.name}" download>Build receipt</a></div><div class="artifact-inline"><a href="{setup_links["Managed walkthrough"]}" target="_blank" rel="noopener">Managed walkthrough</a><a href="{setup_links["Live setup"]}" target="_blank" rel="noopener">Live setup stages</a></div></div><div><p class="receipt-heading">Managed-policy evidence</p><div class="plain-links receipt-links">{managed_evidence_links}</div><p class="replication-copy">Live setup uses your account, runtime package, existing VPC/subnet and SSH source CIDR. A second complete live deployment has not been run.</p></div></div>',
            "From a clean checkout, run python3 scripts/build-demo-presentation.py --check, then python3 scripts/build-demo-presentation.py --output-dir .build/presentation-export using a fresh destination. The recorded artifact rebuild needs Python 3.9+ and committed media, without AWS, Kiro login or historical private raw footage. Run the returned preview command; the allowlist and byte-range server travel with the export. The project skill routes full setup through dependency planning, explicit account/network configuration, a prepared ARM runtime bundle, CloudFormation, services, fixtures, server integrations, managed policy, MCP user UI, desktop connection, observability app and client telemetry. Read each stage’s plan before applying it. The Mac app and original remote CLI authenticate through their own supported flows. CloudFormation uses supplied VPC/subnet and exact SSH source CIDR without creating additional network infrastructure. A fresh ARM bundle and clean-checkout artifact reproduction were tested; a second complete live deployment was not run. Existing clips and reviews keep their original dates and scope. The new managed candidate needs its own council and browser receipts; prior acceptance does not transfer to these edited bytes. Presentation controls never execute live demo commands.",
            section="Reproduce", classes="lilac managed-artifacts", footer="Recorded playback and artifact rebuild are reproducible locally. Live deployment needs its own account and acceptance checks.")


    notes_text = "# KiroCrew native control presentation\n\n" + "\n\n".join(f'## {i}. {title}\n\n{note}' for i, (title, note) in enumerate(slide_notes, 1))
    notes_text += "\n\n## Build inputs\n\n" + "\n".join(f'- `{path}`: `{digest}`' for path, digest in input_hashes.items())
    if receipts:
        notes_text += "\n\n## Supporting receipts\n\n" + "\n".join(f'- `{r["path"]}`: `{r["sha256"]}`' for r in receipts)
    if superseded_authority:
        notes_text += "\n\n## Superseded citation\n\n" + "\n".join(f'The previous authority-review citation `{item["previous"]}` is superseded by `{item["current"]}`. The linked receipt and this build use the current hash.' for item in superseded_authority)
    if limitations:
        notes_text += "\n\n## Retained limitations\n\n" + "\n\n".join(limitations)
    if any(scene["id"].startswith("native-host-") for scene in loaded):
        host_notes = []
        if "native-host-workspace-read" in scene_ids:
            host_notes.append("The permitted workspace read has a continuous request-to-result recording.")
        if command_scene:
            host_notes.append("The command clip inspects an assistant summary after completion." + (" Its separate native history and SEL receipt establish the configured Crew denial." if command_evidence else " Server attribution requires a separate receipt."))
        if authenticated_scene:
            host_notes.append("The anonymous-request clip starts at execution approval and ends with the assistant's HTTP 403 summary. The earlier helper-source read had its own approval.")
        notes_text += "\n\n## Host edition\n\n" + " ".join(host_notes) + " The slides label the remaining tests separately.\n"
    if has_host_council_decisions and not managed:
        notes_text += "\n\n## Host council changes\n\nThe control maps are balanced across their pages, with notes specific to each set of rows. Pending sensitive-path read, protected-path write and IMDS execution are named on the slide. The authentication scene identifies the anonymous EC2 loopback helper while the Mac session remains authenticated, retains the helper's false verification flag, and attributes the Gateway decision to combined receipts. The command scene states that its temporary rule was removed. The admin crop contains three complete configured-coverage rows, with expansion buttons outside each crop, and distinguishes shell Denied Commands from the Crew MCP hook. The cover uses Eastern Time; the IAM footer states the STS limitation; the Crew footer separates the incomplete original collector from complete bounded reconciliation.\n"
    if not managed:
        notes_text += "\n\n## What changed\n\n" + ("The previously reviewed result posters, video bytes, continuous cuts and original timing remain unchanged. " if has_host_council_decisions else "After the Grok and Opus council, each clip now opens with its own real result poster. The video bytes, continuous cuts and original timing remain unchanged. " if has_council_decisions else "This edition puts each supplied native recording on its own slide. ") + "Owner authority and the absence of an enterprise policy floor are visible on the slides. The memory scene says the request stopped before tools. The admin slide magnifies actual posture and governance details and separates health collection, Gateway telemetry, SEL evidence and MCP audit records. The No AI Slop pass tightened the new captions and evidence labels while retaining the control names and observed outcomes.\n"
    else:
        notes_text += "\n\n## Managed edition\n\nAdded one continuous request-to-result recording of the managed MCP denial and the actual Connections, session inventory, Governance and pinned-command views. The previous eight clips retain their pre-managed-policy labels, bytes, cuts and evidence limits. A separate unfilmed managed allowed-read receipt establishes the positive control. Root owns the active file policy and service environment; the ordinary Crew configuration remains writable for local MCP management. The registered project skill and portable build command cover reproduction without reusing private runtime state.\n"
        notes_text += "\n\n## Managed source and limits\n\nObserved " + managed["observed_at"] + ". Policy SHA-256: " + managed["policy"]["policy_sha256"] + ". Client Nightly " + managed["client"]["mac_version"] + "; server Nightly " + managed["client"]["server_version"] + "; " + managed["client"]["backend"] + ". The Mac quit/relaunch and local Gateway off observation preceded policy installation. The later managed take used the remote Gateway.\n\n" + "\n\n".join(managed["limits"]) + "\n"


    css = safe_file(ROOT / "presentation/slides.css").read_text() + safe_file(ROOT / "presentation/demo-player.css").read_text() + EXTRA_CSS + (MANAGED_CSS if managed else "")
    runtime = safe_file(ROOT / "presentation/slide-runtime.js").read_text()
    player = safe_file(ROOT / "presentation/demo-player.js").read_text()
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="color-scheme" content="dark light"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"><link rel="icon" href="data:,"><title>KiroCrew native control demonstrations</title><style>{css}</style></head><body>
<header class="shell-header"><span class="brand">KiroCrew</span><div class="header-right"><span class="edition">Native control demonstrations</span><a href="{PUBLIC.name}" download>Assets</a></div></header><main class="stage" id="deck" tabindex="-1" aria-label="KiroCrew native control presentation">{''.join(slides)}</main>
<nav class="toolbar" aria-label="Presentation controls"><div class="progress-track"><div id="progress"></div></div><div class="toolbar-group"><button id="previous" class="nav-button" aria-label="Previous slide">←</button><span id="slide-count" class="count"></span><button id="next" class="nav-button" aria-label="Next slide">→</button><span id="section-label"></span></div><div class="toolbar-group"><button id="overview-button">Slides</button><button id="notes-button">Notes</button><button id="fullscreen-button" class="optional">Full screen</button><button id="print-button" class="optional">Print / PDF</button><a href="{NOTES.name}" download class="optional">Script</a><button id="help-button" aria-label="Keyboard shortcuts">?</button></div></nav><p id="status" class="sr-only" role="status" aria-live="polite"></p>
<dialog id="overview-dialog" aria-labelledby="overview-title"><header><h2 id="overview-title">Slides</h2><button data-close>Close</button></header><div id="overview-list"></div></dialog><dialog id="notes-dialog" aria-labelledby="notes-title"><header><h2 id="notes-title">Speaker notes</h2><button data-close>Close</button></header><div id="notes-content"></div></dialog><dialog id="image-dialog" aria-labelledby="image-title"><header><h2 id="image-title">Original evidence image</h2><button data-close>Close</button></header><img id="expanded-image" alt=""><p id="image-caption"></p></dialog><dialog id="help-dialog" aria-labelledby="help-title"><header><h2 id="help-title">Keyboard shortcuts</h2><button data-close>Close</button></header><dl class="keys"><dt>← / →</dt><dd>Previous or next slide</dd><dt>Space</dt><dd>Next slide outside a video</dd><dt>O / N</dt><dd>Slide overview / notes</dd><dt>F</dt><dd>Full screen</dd><dt>Escape</dt><dd>Close a dialog</dd></dl></dialog><noscript>Enable JavaScript for slide navigation, or print the presentation.</noscript><script>{runtime}</script><script>{player}</script></body></html>'''
    if document.count('data-endpoint-control-box="true"') != 1:
        raise ValueError("The architecture must retain exactly one endpoint-control box")
    public = {"schemaVersion": 1, "title": "KiroCrew native control demonstrations", "synthetic": False,
              "scenes": loaded, "supportingReceipts": receipts, "adminTour": admin_url, "architectureDiagram": diagram_url,
              "pendingControls": pending, "limitations": limitations,
              "reviewScope": "Artifact integrity and visible recorded behavior. Enforcement acceptance and model council apply only through their separate exact-candidate receipts."}
    if managed:
        public["managedEdition"] = {"receipt": managed_receipt, "observedAt": managed["observed_at"], "policySha256": managed["policy"]["policy_sha256"], "sceneId": managed["native"]["scene_id"], "earlierClipsPredatePolicy": True, "screenshots": managed_images}
    generated = {NOTES.name: notes_text, PUBLIC.name: json.dumps(public, indent=2) + "\n", OUTPUT.name: document}
    if output_dir is None:
        for path in (NOTES, PUBLIC, OUTPUT):
            write_atomic(path, generated[path.name])
            register(path)
    else:
        # Preserve the existing URL routes in all HTML and media metadata. The
        # allowlist maps those routes to copied files inside the export. No
        # private source directory or raw recording is recursively copied.
        if any("/" + name in files for name in generated):
            raise ValueError("A generated artifact route collides with a build input")
        files = {route: {**item, "path": "assets/" + item["path"]} for route, item in files.items()}
        for name, content in generated.items():
            data = content.encode("utf-8")
            files["/" + name] = {"path": name, "bytes": len(data), "sha256": sha(data)}
    inputs = [Path(__file__), ROOT / "scripts/build-recorded-demo-presentation.py", ROOT / "presentation/slides.css", ROOT / "presentation/slide-runtime.js", ROOT / "presentation/demo-player.css", ROOT / "presentation/demo-player.js"]
    receipt = {"schemaVersion": 1, "builtAt": datetime.now(timezone.utc).isoformat(), "edition": OUTPUT.name if output_dir else OUTPUT.relative_to(ROOT).as_posix(), "editionSha256": sha(document.encode()), "notes": NOTES.name if output_dir else NOTES.relative_to(ROOT).as_posix(), "notesSha256": sha(notes_text.encode()), "publicManifest": PUBLIC.name if output_dir else PUBLIC.relative_to(ROOT).as_posix(), "slideCount": len(slides), "sceneCount": len(loaded), "synthetic": False, "singleEndpointControlBoxCount": 1, "processedManifests": input_hashes, "supportingReceipts": receipts, "serveFiles": files, "buildInputs": {p.relative_to(ROOT).as_posix(): sha(safe_file(p).read_bytes()) for p in inputs}, "checks": {"assetHashes": True, "sceneIdsUnique": True, "chapterBounds": True, "noSyntheticScenes": True, "singleEndpointControlBox": True, "noLiveExecutionCode": True}, "reviewScope": public["reviewScope"], "browserReview": "Required separately for this edition hash", "editorialReview": "No AI Slop self-review applied to slide copy and notes"}
    if managed:
        receipt["editorialReview"] = "Managed candidate: post-council No AI Slop review is pending."
    receipt["editionParameters"] = {"pendingControls": pending, "limitations": limitations, "recordingCoverageOverrides": coverage_overrides,
                                    "diagramBuild": diagram_build.relative_to(ROOT).as_posix() if diagram_build else None}
    if output_dir is None:
        write_atomic(BUILD, json.dumps(receipt, indent=2) + "\n")
    else:
        server = safe_file(ROOT / "scripts/serve-recorded-demos.py").read_bytes()
        receipt["editorialReview"] = "A portable derivative requires its own editorial review; no prior verdict is inherited."
        receipt["portableExport"] = {
            "schemaVersion": 1,
            "sourcePaths": "Input paths describe the source project; serveFiles paths are relative to this export.",
            "previewScript": {"path": "scripts/serve-recorded-demos.py", "sha256": sha(server), "bytes": len(server)},
            "previewArguments": ["--build", BUILD.name, "--port", "5612"],
            "copiedAssetsOnly": True,
        }
        # Stage in a sibling directory and publish only a complete export. The
        # destination is never merged with or substituted for an existing tree.
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".native-export-", dir=output_dir.parent))
        try:
            copied = set()
            for item in files.values():
                relative = item["path"]
                if not relative.startswith("assets/") or relative in copied:
                    continue
                source = safe_file(ROOT / relative.removeprefix("assets/"))
                data = validate_hash(source, item, source.name)
                target = temporary / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                copied.add(relative)
            for name, content in generated.items():
                write_atomic(temporary / name, content)
            (temporary / "scripts").mkdir()
            (temporary / "scripts/serve-recorded-demos.py").write_bytes(server)
            write_atomic(temporary / BUILD.name, json.dumps(receipt, indent=2) + "\n")
            export_destination(output_dir)
            os.rename(temporary, output_dir)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", required=True, help="Processed scene manifest. Repeat to append more takes.")
    parser.add_argument("--receipt", type=Path, action="append", default=[], help="Explicit reviewed, sanitized receipt to publish alongside the media.")
    parser.add_argument("--admin-build", type=Path, default=DEFAULT_ADMIN, help="Hash-bound receipt for the separate screenshot tour.")
    parser.add_argument("--without-admin-tour", action="store_true", help="Build scenes before the separate screenshot tour is ready.")
    parser.add_argument("--diagram-build", type=Path, help="Explicit dependency receipt for an optional self-contained architecture HTML.")
    parser.add_argument("--pending-host-takes", action="store_true", help="Show the six prepared host outcomes as unrecorded, with their shot list.")
    parser.add_argument("--pending-control", action="append", default=[], help="Control still awaiting completed native evidence. Repeat for the current pending set.")
    parser.add_argument("--limitation", action="append", default=[], help="Explicit retained evidence limitation for notes and manifest. Repeat as needed.")
    parser.add_argument("--recording-coverage", action="append", default=[], metavar="SCENE=MODE", help="Explicit coverage override: request_to_result, approval_to_result, result_inspection, or unknown.")
    parser.add_argument("--output-dir", type=Path, help="Fresh portable export directory; keeps accepted output artifacts unchanged.")
    args = parser.parse_args()
    receipt = build(args.manifest, args.receipt, None if args.without_admin_tour else args.admin_build, args.pending_host_takes,
                    args.pending_control, args.limitation, args.recording_coverage, args.diagram_build, args.output_dir)
    print(json.dumps({"buildReceipt": str(args.output_dir / BUILD.name if args.output_dir else BUILD), "edition": receipt["edition"], "sha256": receipt["editionSha256"], "slideCount": receipt["slideCount"], "sceneCount": receipt["sceneCount"]}, indent=2))


if __name__ == "__main__":
    main()
