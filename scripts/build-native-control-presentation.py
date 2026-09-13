#!/usr/bin/env python3
"""Build a focused HTML presentation from reviewed recordings of real controls.

Repeat --manifest to append independently processed takes. The builder verifies
asset hashes, retains each scene's evidence scope and never creates demo footage.
It writes only the four kirocrew-native-controls artifacts in output/.
"""
import argparse
import base64
from datetime import datetime, timezone
import html
import importlib.util
import json
import math
from pathlib import Path
import re
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
}

EXTRA_CSS = r"""
.control-cover h1{font-size:5.7cqw;max-width:76cqw}.control-cover .hero-intro{max-width:69cqw;font-size:2.2cqw}.cover-count{font-size:1.35cqw;color:#c9b7f5;margin-top:1.8cqw}.cover-bottom{margin-top:auto;display:flex;align-items:end;justify-content:space-between;gap:4cqw}.cover-bottom p{font-size:1.35cqw;color:#c8c3d1}.cover-bottom .slide-link{background:#e5d8ff;color:#2f194d}.architecture-svg{width:100%;height:100%;max-height:32cqw}.architecture-caption{font-size:1.22cqw;color:#55525f;max-width:78cqw}.control-table td{font-size:1.45cqw;padding:1.05cqw 1cqw 1.05cqw 0}.control-table th{font-size:1cqw}.control-table td:first-child{font-weight:700;width:24%}.control-table td:nth-child(2){width:29%;color:#685083}.control-table a{text-decoration-color:#bba4da;text-underline-offset:4px}.control-table .scene-time{display:block;color:#72717c;font-size:1cqw;font-weight:400;margin-top:.2cqw}.native-scene .demo-description{max-width:84cqw}.native-scene .demo-layout{grid-template-columns:minmax(0,4.1fr) minmax(0,1.1fr);gap:1.5cqw}.native-scene .demo-screen{background:#f4f1f7;padding:.55cqw;grid-template-rows:minmax(0,1fr) auto auto}.native-scene .demo-screen video{background:#17151b;border:0}.native-scene .demo-controls{gap:.5cqw}.native-scene .demo-controls button{font-size:.95cqw;padding:.5cqw .6cqw}.native-scene .demo-controls label{font-size:.94cqw}.native-scene .demo-status{font-size:.9cqw!important}.native-scene .demo-cues button{font-size:1.03cqw;line-height:1.35;padding:.65cqw .4cqw}.native-scene .demo-cue-detail{font-size:1.03cqw}.native-scene .slide-footer{font-size:.92cqw}.scene-downloads{display:flex;gap:.85cqw;align-items:center}.scene-downloads a{font-size:.92cqw;color:#614482;text-underline-offset:3px}.authority-note{font-size:1.45cqw;line-height:1.5;max-width:82cqw}.admin-feature{display:grid;grid-template-columns:1fr 1.25fr;gap:3cqw;min-height:0;flex:1;align-items:center}.admin-feature h3{font-size:2.35cqw;line-height:1.17;margin-bottom:1.2cqw}.admin-feature p{font-size:1.48cqw;line-height:1.48}.admin-feature .screenshot{height:31cqw}.admin-feature .link-row{margin-top:2cqw}.artifact-list{display:flex;flex-direction:column;gap:0}.artifact-row{display:grid;grid-template-columns:2.2cqw 1fr;gap:1.3cqw;border-top:1px solid #c5b5dd;padding:1.4cqw 0}.artifact-row b{font-size:1.2cqw;color:#76509d}.artifact-row a{font-size:2cqw;font-weight:700;text-decoration-thickness:1px;text-underline-offset:5px}.artifact-row p{font-size:1.3cqw;margin-top:.5cqw;color:#62576e}.artifact-grid{display:grid;grid-template-columns:1.25fr .8fr;gap:5cqw;align-items:center}.artifact-grid .note{font-size:1.45cqw;line-height:1.6}.artifact-grid code{font-size:.86em}.scene-count{font-size:6.2cqw;line-height:1;letter-spacing:-.06em}.plain-links{font-size:1.1cqw;line-height:1.8}.plain-links a{display:block;color:#674690}.media-button::after{opacity:1}
@media(max-width:760px){.control-cover h1{font-size:46px;max-width:none}.control-cover .hero-intro{font-size:22px;max-width:none}.cover-count{font-size:15px;margin-top:20px}.cover-bottom{display:block}.cover-bottom p{font-size:15px;margin:20px 0}.architecture-svg{height:auto;max-height:none;min-width:660px}.architecture-scroll{overflow:auto}.architecture-caption{font-size:14px;max-width:none}.control-table td{font-size:14px;padding:15px 12px 15px 0}.control-table th{font-size:10px}.control-table .scene-time{font-size:12px}.control-table td:nth-child(2){width:31%}.native-scene .demo-layout{grid-template-columns:1fr;gap:22px}.native-scene .demo-screen{padding:7px;display:flex}.native-scene .demo-screen video{aspect-ratio:1920/1290}.native-scene .demo-description{max-width:none}.native-scene .demo-controls{gap:9px}.native-scene .demo-controls button,.native-scene .demo-controls label{font-size:14px}.native-scene .demo-status{font-size:13px!important}.native-scene .demo-cues button{font-size:14px;padding:12px}.native-scene .demo-cue-detail{font-size:15px}.native-scene .slide-footer{font-size:12px}.scene-downloads{gap:16px}.scene-downloads a{font-size:13px}.authority-note{font-size:16px;max-width:none}.admin-feature,.artifact-grid{grid-template-columns:1fr;gap:25px}.admin-feature h3{font-size:26px;margin-bottom:15px}.admin-feature p{font-size:16px}.admin-feature .screenshot{height:auto}.admin-feature .link-row{margin-top:20px}.artifact-row{grid-template-columns:24px 1fr;gap:12px;padding:20px 0}.artifact-row b{font-size:13px}.artifact-row a{font-size:23px}.artifact-row p{font-size:15px;margin-top:8px}.artifact-grid .note{font-size:16px}.scene-count{font-size:66px}.plain-links{font-size:14px}}
.scene-proof{font-size:1.02cqw!important;line-height:1.4;margin-top:.5cqw;color:#674587}.scene-proof code{font-size:.94em}.native-scene .slide-footer>span:first-child{max-width:84cqw}.admin-examples{display:grid;grid-template-columns:1fr 1.75fr;column-gap:2.5cqw;row-gap:1.1cqw;align-items:center}.admin-examples h3{font-size:1.9cqw;margin-bottom:.5cqw}.admin-examples p{font-size:1.2cqw;line-height:1.45}.admin-detail{width:100%;border:1px solid #d5d0dd;background:#101014;display:block}.admin-detail svg{display:block;width:100%;height:100%}.admin-posture{height:10.5cqw}.admin-governance{height:7.5cqw}.admin-sources{display:grid;grid-template-columns:repeat(4,1fr);gap:1.5cqw;border-top:1px solid #dad2e4;padding-top:1.1cqw;margin-top:.7cqw}.admin-sources dt{font-size:1.16cqw;font-weight:700;margin-bottom:.4cqw;color:#4f336d}.admin-sources dd{font-size:1.06cqw;line-height:1.45;margin:0;color:#5d5865}.admin-controls{display:flex;justify-content:space-between;align-items:center;gap:2cqw}.admin-controls p{font-size:1cqw;color:#696271}.receipt-heading{font-size:1.22cqw;color:#655374;margin:1.2cqw 0 .3cqw}.receipt-links a{font-size:1.2cqw;line-height:1.85}.artifact-grid .note{font-size:1.3cqw}.artifact-grid{grid-template-columns:1.15fr 1fr;gap:4cqw}
@media(max-width:760px){.scene-proof{font-size:13px!important;margin-top:8px}.native-scene .slide-footer>span:first-child{max-width:none}.admin-examples{grid-template-columns:1fr;gap:14px}.admin-examples h3{font-size:23px}.admin-examples p{font-size:15px}.admin-posture{height:auto;aspect-ratio:940/180}.admin-governance{height:auto;aspect-ratio:960/115}.admin-sources{grid-template-columns:1fr 1fr;gap:16px;margin-top:15px;padding-top:18px}.admin-sources dt{font-size:15px}.admin-sources dd{font-size:14px}.admin-controls{display:block}.admin-controls p{font-size:12px;margin-top:12px}.receipt-heading{font-size:15px;margin-top:20px}.receipt-links a{font-size:15px}.artifact-grid .note{font-size:15px}.artifact-grid{grid-template-columns:1fr;gap:25px}}
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


def architecture():
    # Exactly one endpoint-control enclosure. The labels inside it identify
    # software and host authority on EC2 without splitting that boundary.
    return '''<div class="architecture-scroll"><svg class="architecture-svg" viewBox="0 0 1180 415" role="img" aria-labelledby="architecture-title architecture-desc">
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


def build(manifests, receipt_paths=(), admin_build=DEFAULT_ADMIN, pending_host_takes=False):
    for destination in DESTINATIONS:
        if any(p.is_symlink() for p in (destination, *destination.parents)):
            raise ValueError("Output paths cannot contain symlinks")
        if destination.exists() and not destination.is_file():
            raise ValueError("Output destinations must be regular files")
    files, input_hashes, loaded = {}, {}, []

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

    receipts, reconciled_phases, superseded_authority = [], {}, []
    has_council_decisions = False
    authenticated_before_capture = False
    for receipt_path in receipt_paths:
        receipt_path = safe_file(receipt_path)
        if receipt_path in DESTINATIONS or receipt_path.suffix not in {".json", ".md", ".txt"}:
            raise ValueError("Evidence must be an explicit receipt input")
        receipts.append({"path": receipt_path.relative_to(ROOT).as_posix(), "url": register(receipt_path), "sha256": sha(receipt_path.read_bytes())})
        if receipt_path.suffix == ".json":
            content = json.loads(receipt_path.read_text())
            if isinstance(content, dict) and content.get("kind") == "native_client_evidence_reconciliation" and content.get("bounded_four_outcomes_reconciled") is True:
                reconciled_phases = checked_phase_observations(content)
            if (isinstance(content, dict) and content.get("authenticated") is True
                    and content.get("method") == "SocialGitHub"
                    and content.get("source") == "EC2 standalone Kiro CLI whoami"):
                checked = datetime.fromisoformat(text(content.get("checked_at"), "authentication timestamp", 80).replace("Z", "+00:00"))
                earliest = min(datetime.fromisoformat(scene["recordedAt"].replace("Z", "+00:00")) for scene in loaded)
                if checked.tzinfo is not None and 0 <= (earliest - checked).total_seconds() <= 86400:
                    authenticated_before_capture = True
            if isinstance(content, dict) and content.get("kind") == "bounded_native_evidence_attribution_review":
                previous = content.get("revision", {}).get("previous_review_sha256")
                if isinstance(previous, str) and re.fullmatch(r"[0-9a-f]{64}", previous):
                    superseded_authority.append({"previous": previous, "current": receipts[-1]["sha256"]})
            if isinstance(content, dict) and content.get("root_agreed_material_findings") is True and "review_candidate" in content:
                has_council_decisions = True
    host_plan = None
    if pending_host_takes:
        host_plan_path = ROOT / "docs/HOST-CONTROL-SCENARIOS.md"
        host_plan = register(host_plan_path)
        input_hashes[host_plan_path.relative_to(ROOT).as_posix()] = sha(host_plan_path.read_bytes())

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
    add("Server controls for a Mac client", f'<div class="slide-body hero"><p class="eyebrow">KiroCrew on EC2</p><h1>Server controls<br>for a Mac client</h1><p class="hero-intro">Real requests from Kiro Crew Nightly, with the Gateway and original Kiro CLI backend running on an ARM instance.</p><p class="cover-count">{len(loaded)} recorded control demonstrations</p></div><div class="cover-bottom"><p>Local Gateway off.<br>Remote workspace on EC2.</p>{guide_link}</div>',
        "This focused edition contains the supplied recordings of real application behavior. The Mac endpoint is the only client platform in scope. " + ("The supplied authentication receipt confirms that the original EC2 Kiro CLI backend was signed in through GitHub before capture. " if authenticated_before_capture else "This edition does not establish backend sign-in independently. ") + "The media manifest describes visible behavior. " + ("Explicit supporting receipts accompany this edition for separate server-attribution review. " if receipts else "Server attribution requires separate supporting receipts. ") + "Playback controls operate recordings and do not send requests to the live system.", classes="dark control-cover", footer="September 13, 2026 recordings")
    add("Execution and host controls stay on EC2", '<header class="slide-header"><p class="eyebrow">Deployment</p><h2>Execution and host controls stay on EC2</h2></header><div class="slide-body">' + architecture() + '<p class="architecture-caption">The Mac carries the chat and approval UI. EC2 holds the execution environment, policy checks and fixed MCP service.</p></div>',
        "The diagram preserves a single endpoint-control box. Gateway, Kiro CLI, workspace, host controls and the MCP service reside on the ARM EC2 host. The MCP service has a separate process identity and fixed demo grants. Its AWS calls use the instance role. The current connection has owner privileges, and no enterprise governance floor is active. Crew configuration remains writable by the crew account. The host diagram does not establish immutable multi-user policy, failover or EDR. Existing infrastructure supports caller-supplied VPC and subnet parameters without adding NAT gateways or load balancers.", footer="Owner connection. Crew configuration is owner editable. No enterprise governance floor.")
    # A readable matrix uses at most six demonstrations per page.
    for offset in range(0, len(loaded), 6):
        group = loaded[offset:offset + 6]
        matrix_count = math.ceil(len(loaded) / 6)
        first_clip = 3 + matrix_count
        rows = []
        for index, scene in enumerate(group, offset):
            p = scene["presentation"]
            rows.append(f'<tr><td><a href="#slide-{first_clip + index}">{e(p["control"])}</a><span class="scene-time">About {scene["duration"]:.0f} seconds</span></td><td>{e(p["enforcer"])}</td><td>{e(p["outcome"])}</td></tr>')
        pending_line = f'<p class="note">Six host takes prepared. Their native outcomes remain unrecorded. <a href="{host_plan}" target="_blank" rel="noopener">Shot list</a></p>' if pending_host_takes and offset + 6 >= len(loaded) else ""
        add("The control decides where the request stops", '<header class="slide-header"><p class="eyebrow">Recorded demonstrations</p><h2>The control decides<br>where the request stops</h2></header><div class="slide-body"><table class="control-table"><thead><tr><th scope="col">Demonstration</th><th scope="col">Decision point</th><th scope="col">Visible result</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>' + pending_line + '</div>',
            "The matrix summarizes only scenes present in the processed input manifests. It lists visible outcomes rather than assigning automatic acceptance. For native MCP turns, Crew auto-denial must precede MCP dispatch, MCP grant denial must precede AWS dispatch, and an AWS refusal needs the returned AWS request ID and matching service evidence. Host and identity cases retain their own scope. The private-memory refusal stops an unassigned conversation before a tool turn. It does not establish restricted human-role RBAC. An anonymous authentication rejection would establish an authentication boundary only." + (" The prepared host takes cover an allowed workspace read, anonymous server authentication, sensitive-path read, protected-path write, a server command rule and a metadata TCP connection. Those six native outcomes remain unobserved in this edition." if pending_host_takes else ""), section="Control map", footer="MCP control layers follow joined server receipts. The memory guard stopped before tools." if reconciled_phases else f"Select a demonstration to open its clip. Page {offset // 6 + 1} of {matrix_count}.")

    for scene in loaded:
        width, height = (int(scene["media"][0][key]) for key in ("width", "height"))
        title, description = scene["title"], scene["description"]
        proof_line = ""
        scope_line = f'About {scene["duration"]:.0f} seconds. {scene["presentation"]["enforcer"]}. Full evidence scope in notes.'
        if scene["id"] == "native-memory-assignment-refusal":
            title = "Private memory requires an assigned conversation"
            description = "An existing conversation switches to a private-store alias. The server refuses its first fixture request before tools run."
            scope_line = "Conversation binding only. fs_read never ran. RBAC and host tools remain untested."
        elif scene["id"] == "native-crew-denial":
            scope_line = "Crew configuration is owner editable. This run has no enterprise governance floor."
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
        sources = ''.join(f'<source src="{e(m["url"], quote=True)}" type="{e(m["type"], quote=True)}">' for m in scene["media"])
        cues = []
        for cue in scene["cues"]:
            evidence = f' data-cue-evidence="{e(cue["evidence"], quote=True)}"' if cue.get("evidence") else ""
            cues.append(f'<button type="button" data-cue-time="{cue["time"]}" data-cue-label="{e(cue["label"], quote=True)}" data-cue-detail="{e(cue["detail"], quote=True)}"{evidence}><time>{int(cue["time"]) // 60}:{int(cue["time"]) % 60:02d}</time><span>{e(cue["label"])}</span></button>')
        downloads = f'<a href="{scene["media"][0]["url"]}" target="_blank" rel="noopener">Open video full size</a><a href="{scene["media"][0]["url"]}" download>Download clip</a>'
        if scene.get("contactSheet"):
            downloads += f'<a href="{scene["contactSheet"]["url"]}" target="_blank" rel="noopener">Contact sheet</a>'
        proof_html = f'<p class="scene-proof">{e(proof_line)}</p>' if proof_line else ""
        body = f'<header class="slide-header"><p class="eyebrow">{e(scene["presentation"]["control"])}</p><h2>{e(title)}</h2><p class="demo-description">{e(description)}</p>{proof_html}</header><div class="demo-layout"><div class="demo-screen"><video controls muted playsinline width="{width}" height="{height}" style="aspect-ratio:{width}/{height}" preload="metadata" poster="{scene["poster"]["url"]}" aria-label="Recorded demonstration: {e(title, quote=True)}">{sources}Your browser does not support this video.</video><div class="demo-controls"><button class="demo-replay" type="button">Replay</button><button class="demo-next-cue" type="button">Next chapter</button><label><input class="demo-guided" type="checkbox"> Pause at chapters</label></div><p class="demo-status" role="status" aria-live="polite">Select a chapter to seek and pause.</p></div><aside class="demo-chapters" aria-label="Recording chapters"><h3>Chapters</h3><div class="demo-cues">{"".join(cues)}</div><div class="demo-cue-detail" aria-live="polite"></div></aside></div><div class="scene-downloads">{downloads}</div>'
        note = f'{scene["evidenceScope"]} Recorded {scene["recordedAt"]}. Source capture SHA-256: {scene["provenance"]["sourceSha256"]}. Cut: {json.dumps(scene["provenance"].get("cut"))}. ' + ' '.join(f'{cue["time"]:g}s: {cue["label"]}. {cue["detail"]}' for cue in scene["cues"])
        if proof_line:
            note += " " + proof_line + " Layer attribution follows the supplied bounded reconciliation. The original collector remains incomplete. Crew correlation uses the isolated turn because SEL has no direct trace-to-tool-call join for that denial."
        if scene["id"] == "native-iam-denial" and "iam" in reconciled_phases:
            note += " AWS role attribution uses the existing instance-profile/cutover receipts and after-capture source, service and policy checks. No per-request STS caller identity was collected. Fixture HEAD checks establish existence and metadata, without recomputing the denied object's content digest. Process observations do not establish that a sampled PID overlapped a pending approval. These limits remain in the linked authority review."
        if scene.get("poster", {}).get("time") is not None:
            note += f' The poster uses an actual result frame at {scene["poster"]["time"]:g} seconds in this clip. Video bytes and cut boundaries remain unchanged.'
        add(title, body, note, section="Recorded controls", classes="recorded-demo native-scene", footer=scope_line)

    if admin_url:
        def screenshot_detail(filename, box, css_class, caption):
            path = admin_images.get(filename)
            if path is None:
                raise ValueError("Admin tour needs the current posture and governance screenshots")
            data = path.read_bytes()
            mime = "image/jpeg" if data.startswith(b"\xff\xd8\xff") else "image/png"
            uri = "data:" + mime + ";base64," + base64.b64encode(data).decode()
            return f'<button class="media-button admin-detail {css_class}" data-image="{uri}" data-caption="{e(caption, quote=True)}"><svg viewBox="{box}" role="img" aria-label="{e(caption, quote=True)}"><image x="0" y="0" width="1555" height="1324" href="{uri}"/></svg></button>'
        posture = screenshot_detail("01-live-security-posture.png", "584 548 940 136", "admin-posture", "Configured sensitive paths, protected paths and command rules. Detail from the September 13 admin screenshot. Expand for the full original capture.")
        governance = screenshot_detail("06-governance-status.png", "584 352 940 103", "admin-governance", "No enterprise policy in effect. Detail from the September 13 governance screenshot. Expand for the full original capture.")
        admin_body = '<header class="slide-header"><p class="eyebrow">Separate screenshot walkthrough</p><h2>Admin settings and logs have different jobs</h2></header><div class="slide-body"><div class="admin-examples"><div><h3>Posture lists configured coverage</h3><p>Path and command counts describe available rules. Native recordings establish the outcomes.</p></div>' + posture + '<div><h3>No enterprise policy is active</h3><p>The owner can edit Crew configuration. This demo has no immutable governance floor.</p></div>' + governance + '</div><dl class="admin-sources"><div><dt>Gateway telemetry</dt><dd>Backend activity and performance metrics.</dd></div><div><dt>Collection events</dt><dd>Mac and EC2 health samples and errors.</dd></div><div><dt>SEL evidence</dt><dd>Security decisions in receipts. The portal lists coverage.</dd></div><div><dt>MCP audit</dt><dd>Service decisions and AWS dispatch in the service journal.</dd></div></dl><div class="admin-controls">' + guide_link + '<p>September 13 screenshot details. Expand either for its full capture.</p></div></div>'
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
    evidence_links = ''.join(f'<a href="{r["url"]}" target="_blank" rel="noopener">{e(selected_receipts[Path(r["path"]).name])}</a>' for r in receipts if Path(r["path"]).name in selected_receipts)
    evidence_note = "Supporting receipts" if evidence_links else "The recording manifest lists the supporting receipts."
    council_note = "The external Grok and Opus council reviewed the earlier ten-slide candidate and requested changes. This derivative incorporates the agreed changes, followed by No AI Slop editing. Its changed bytes need a fresh root browser review and local read-only review. The external verdicts do not constitute exact-model review of this derivative. " if has_council_decisions else "Review receipts apply to their exact candidates. Prior reviews do not automatically cover this derivative. "
    add("The recordings and evidence stay together", f'<header class="slide-header"><p class="eyebrow">Presentation assets</p><h2>The recordings and evidence stay together</h2></header><div class="slide-body artifact-grid"><div class="artifact-list"><div class="artifact-row"><b>01</b><div><a href="{NOTES.name}" download>Speaker notes</a><p>Scene scope, authority and interpretation.</p></div></div><div class="artifact-row"><b>02</b><div><a href="{PUBLIC.name}" download>Recording manifest</a><p>Clip paths, chapters and source capture hashes.</p></div></div><div class="artifact-row"><b>03</b><div><a href="{BUILD.name}" download>Build receipt</a><p>Exact files and hashes for this edition.</p></div></div></div><div><p class="receipt-heading">{e(evidence_note)}</p><div class="plain-links receipt-links">{evidence_links}</div><p class="note" style="margin-top:1.5cqw">Video slides include downloads and full-size playback. <strong>Print / PDF</strong> creates a static copy.</p></div></div>',
        "The build validates processed-media hashes, sizes, decoded-media flags, capture provenance and chapter bounds. Artifact integrity and enforcement acceptance have separate reviews. All supplied receipts appear in the recording manifest and these notes. " + council_note + "The preview server serves only the hash-bound allowlist and supports video byte ranges. Presentation controls do not execute demo commands.", section="Artifacts", classes="lilac", footer="Existing VPC/subnet support. No new VPC, NAT gateway or load balancer. GitHub Actions out of scope.")

    notes_text = "# KiroCrew native control presentation\n\n" + "\n\n".join(f'## {i}. {title}\n\n{note}' for i, (title, note) in enumerate(slide_notes, 1))
    notes_text += "\n\n## Build inputs\n\n" + "\n".join(f'- `{path}`: `{digest}`' for path, digest in input_hashes.items())
    if receipts:
        notes_text += "\n\n## Supporting receipts\n\n" + "\n".join(f'- `{r["path"]}`: `{r["sha256"]}`' for r in receipts)
    if superseded_authority:
        notes_text += "\n\n## Superseded citation\n\n" + "\n".join(f'The previous authority-review citation `{item["previous"]}` is superseded by `{item["current"]}`. The linked receipt and this build use the current hash.' for item in superseded_authority)
    notes_text += "\n\n## What changed\n\n" + ("After the Grok and Opus council, each clip now opens with its own real result poster. The video bytes, continuous cuts and original timing remain unchanged. " if has_council_decisions else "This edition puts each supplied native recording on its own slide. ") + "Owner authority and the absence of an enterprise policy floor are visible on the slides. The memory scene says the request stopped before tools. The admin slide magnifies actual posture and governance details and separates health collection, Gateway telemetry, SEL evidence and MCP audit records. The No AI Slop pass tightened the new captions and evidence labels while retaining the control names and observed outcomes.\n"

    css = safe_file(ROOT / "presentation/slides.css").read_text() + safe_file(ROOT / "presentation/demo-player.css").read_text() + EXTRA_CSS
    runtime = safe_file(ROOT / "presentation/slide-runtime.js").read_text()
    player = safe_file(ROOT / "presentation/demo-player.js").read_text()
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="color-scheme" content="dark light"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"><link rel="icon" href="data:,"><title>KiroCrew native control demonstrations</title><style>{css}</style></head><body>
<header class="shell-header"><span class="brand">KiroCrew</span><div class="header-right"><span class="edition">Native control demonstrations</span><a href="{PUBLIC.name}" download>Assets</a></div></header><main class="stage" id="deck" tabindex="-1" aria-label="KiroCrew native control presentation">{''.join(slides)}</main>
<nav class="toolbar" aria-label="Presentation controls"><div class="progress-track"><div id="progress"></div></div><div class="toolbar-group"><button id="previous" class="nav-button" aria-label="Previous slide">←</button><span id="slide-count" class="count"></span><button id="next" class="nav-button" aria-label="Next slide">→</button><span id="section-label"></span></div><div class="toolbar-group"><button id="overview-button">Slides</button><button id="notes-button">Notes</button><button id="fullscreen-button" class="optional">Full screen</button><button id="print-button" class="optional">Print / PDF</button><a href="{NOTES.name}" download class="optional">Script</a><button id="help-button" aria-label="Keyboard shortcuts">?</button></div></nav><p id="status" class="sr-only" role="status" aria-live="polite"></p>
<dialog id="overview-dialog" aria-labelledby="overview-title"><header><h2 id="overview-title">Slides</h2><button data-close>Close</button></header><div id="overview-list"></div></dialog><dialog id="notes-dialog" aria-labelledby="notes-title"><header><h2 id="notes-title">Speaker notes</h2><button data-close>Close</button></header><div id="notes-content"></div></dialog><dialog id="image-dialog" aria-labelledby="image-title"><header><h2 id="image-title">Original evidence image</h2><button data-close>Close</button></header><img id="expanded-image" alt=""><p id="image-caption"></p></dialog><dialog id="help-dialog" aria-labelledby="help-title"><header><h2 id="help-title">Keyboard shortcuts</h2><button data-close>Close</button></header><dl class="keys"><dt>← / →</dt><dd>Previous or next slide</dd><dt>Space</dt><dd>Next slide outside a video</dd><dt>O / N</dt><dd>Slide overview / notes</dd><dt>F</dt><dd>Full screen</dd><dt>Escape</dt><dd>Close a dialog</dd></dl></dialog><noscript>Enable JavaScript for slide navigation, or print the presentation.</noscript><script>{runtime}</script><script>{player}</script></body></html>'''
    if document.count('data-endpoint-control-box="true"') != 1:
        raise ValueError("The architecture must retain exactly one endpoint-control box")
    public = {"schemaVersion": 1, "title": "KiroCrew native control demonstrations", "synthetic": False,
              "scenes": loaded, "supportingReceipts": receipts, "adminTour": admin_url,
              "reviewScope": "Artifact integrity and visible recorded behavior. Enforcement acceptance and model council apply only through their separate exact-candidate receipts."}
    write_atomic(NOTES, notes_text)
    write_atomic(PUBLIC, json.dumps(public, indent=2) + "\n")
    write_atomic(OUTPUT, document)
    for path in (NOTES, PUBLIC, OUTPUT):
        register(path)
    inputs = [Path(__file__), ROOT / "scripts/build-recorded-demo-presentation.py", ROOT / "presentation/slides.css", ROOT / "presentation/slide-runtime.js", ROOT / "presentation/demo-player.css", ROOT / "presentation/demo-player.js"]
    receipt = {"schemaVersion": 1, "builtAt": datetime.now(timezone.utc).isoformat(), "edition": OUTPUT.relative_to(ROOT).as_posix(), "editionSha256": sha(document.encode()), "notes": NOTES.relative_to(ROOT).as_posix(), "notesSha256": sha(notes_text.encode()), "publicManifest": PUBLIC.relative_to(ROOT).as_posix(), "slideCount": len(slides), "sceneCount": len(loaded), "synthetic": False, "singleEndpointControlBoxCount": 1, "processedManifests": input_hashes, "supportingReceipts": receipts, "serveFiles": files, "buildInputs": {p.relative_to(ROOT).as_posix(): sha(safe_file(p).read_bytes()) for p in inputs}, "checks": {"assetHashes": True, "sceneIdsUnique": True, "chapterBounds": True, "noSyntheticScenes": True, "singleEndpointControlBox": True, "noLiveExecutionCode": True}, "reviewScope": public["reviewScope"], "browserReview": "Required separately for this edition hash", "editorialReview": "No AI Slop self-review applied to slide copy and notes"}
    write_atomic(BUILD, json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, action="append", required=True, help="Processed scene manifest. Repeat to append more takes.")
    parser.add_argument("--receipt", type=Path, action="append", default=[], help="Explicit reviewed, sanitized receipt to publish alongside the media.")
    parser.add_argument("--admin-build", type=Path, default=DEFAULT_ADMIN, help="Hash-bound receipt for the separate screenshot tour.")
    parser.add_argument("--without-admin-tour", action="store_true", help="Build scenes before the separate screenshot tour is ready.")
    parser.add_argument("--pending-host-takes", action="store_true", help="Show the six prepared host outcomes as unrecorded, with their shot list.")
    args = parser.parse_args()
    receipt = build(args.manifest, args.receipt, None if args.without_admin_tour else args.admin_build, args.pending_host_takes)
    print(json.dumps({"buildReceipt": str(BUILD), "edition": receipt["edition"], "sha256": receipt["editionSha256"], "slideCount": receipt["slideCount"], "sceneCount": receipt["sceneCount"]}, indent=2))


if __name__ == "__main__":
    main()
