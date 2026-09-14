#!/usr/bin/env python3
"""Build a standalone admin tour from inspected, unchanged console captures."""
from __future__ import annotations

import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
EVIDENCE = ROOT / "evidence/admin-console/native-20260913"
FRESH = "admin-console-native-20260913/"
EARLIER = "admin-console/"
TITLE = "KiroCrew admin console tour"
INTRO = "Tour the owner console connected to the ARM EC2 Gateway: policy, user controls, runtime metrics and client/server health. The Mac runs the client with its local Gateway off. Each image retains its capture date."
STATUS = "The native Mac run recorded an allowed S3 read, a Crew policy refusal, an MCP grant refusal and IAM AccessDenied. The final reconciliation and authority review support those four bounded outcomes."


def shot(file, caption, alt, fresh=True):
    return {"file": (FRESH if fresh else EARLIER) + file, "caption": caption, "alt": alt,
            "capture_label": "September 13, 2026 · evening capture" if fresh else "September 13, 2026 · earlier baseline",
            "capture_group": "fresh_security_tour" if fresh else "accepted_earlier_baseline"}


STOPS = [
    {"id": "host", "title": "Locate the execution host", "path": "Settings → Overview; Developer → System → Performance",
     "route": "/settings/overview; /developer?tab=system&plane=performance",
     "body": ["The fresh Overview capture shows All systems running, the September 12 server Nightly, 6h 51m 40s uptime and one session. The earlier Performance capture identifies aarch64, four logical processors and the workspace on Linux. Both describe the EC2 execution host.",
              "Read the host and build before interpreting the counters. Gateway health and a selected backend each need a completed native turn to establish that the backend can do the requested work."],
     "cue": "Point to the remote Linux workspace. Keep the Gateway, backend and workspace inside the single endpoint-control box.",
     "shots": [shot("07-gateway-overview.png", "Fresh Overview capture: remote server Nightly, uptime of 6h 51m 40s, one session and zero messages.", "Overview shows All systems running, one session and the remote September 12 server build."),
               shot("02-arm-performance.jpg", "Earlier Performance capture: aarch64, four logical processors and the EC2 workspace.", "System Performance identifies ARM Linux and the remote workspace.", False)]},
    {"id": "posture", "title": "Read the configured controls", "path": "Settings → Security → Live Security Posture",
     "route": "/settings/security/posture",
     "body": ["The page shows Standard process sandbox and Interactive tool approval. The visible coverage includes 143 credential paths, 23 protected configuration paths and 112 built-in denied-command rules.",
              "These labels describe the configured controls and their registries. A completed request and its correlated evidence establish what ran or was blocked."],
     "cue": "Expand a control to explain its coverage. Keep the scope of the claim tied to the evidence.",
     "shots": [shot("01-live-security-posture.png", "Fresh posture capture: configuration and coverage counts on the EC2 Gateway.", "Live Security Posture shows Standard sandbox, Interactive approval and control coverage counts.")]},
    {"id": "rules", "title": "Inspect the command rules", "path": "Settings → Security → Denied Commands",
     "route": "/settings/security/rules",
     "body": ["The page groups 112 rules into nine categories. The expanded IaC teardown group describes four enabled rules for destructive CDK, Kubernetes, Pulumi and Terraform commands. The custom-deny form accepts a pattern and an explanation for the agent.",
              "These are command-pattern controls. The demo’s auto_deny_tools entry for @aws-enforcement/crew_denied lives in the remote Gateway configuration separately; this screen does not manage that MCP tool deny. Crew can edit its configuration in this deployment."],
     "cue": "Read a rule’s description and enabled state. Inspect coverage without changing the control during the tour.",
     "shots": [shot("03-denied-command-categories.png", "Fresh category view: nine groups, 112 rules and the custom-deny form.", "Denied Commands lists credential, shell, destructive-command and publication rule categories."),
               shot("04-teardown-rule-coverage-viewport.png", "Fresh expanded IaC teardown category: four enabled rule descriptions.", "The expanded IaC teardown category shows CDK destroy, Kubernetes namespace deletion, Pulumi destroy and Terraform destroy rules.")]},
    {"id": "approval", "title": "Read the active approval mode", "path": "Settings → Security → YOLO (auto-approve)",
     "route": "/settings/security/approval",
     "body": ["The sidebar says Interactive. Six hours is selected as the duration for the next activation of auto-approve; the sentence below the choices makes that timing explicit.",
              "The native demo requires reviewing each approvable request and choosing the once-only approval. Leave Interactive mode in place."],
     "cue": "Read the sidebar’s current mode first, then the selected duration and its next-activation note.",
     "shots": [shot("05-approval-duration.png", "Fresh approval settings: Interactive remains active; six hours is the next auto-approve duration.", "The YOLO duration screen shows Interactive in its sidebar and a six-hour next-activation selection.")]},
    {"id": "governance", "title": "Check who owns the policy", "path": "Settings → Security → Governance Policy",
     "route": "/settings/security/governance",
     "body": ["The effective security ceiling panel reports “No enterprise policy in effect.” It describes this host as standalone. This viewer is read-only; it does not author an enterprise policy.",
              "The demonstration uses an owner connection and editable Crew configuration. The root-managed MCP service enforces its own grants, and AWS evaluates the instance role. Those MCP and IAM policies live outside this portal. No immutable enterprise floor or separate low-privilege member workflow is established here."],
     "cue": "Name the three authorities: Gateway configuration, protected MCP service and AWS IAM. Show their evidence separately.",
     "shots": [shot("06-governance-status.png", "Fresh governance capture: no enterprise policy is loaded on the host.", "Governance Policy states No enterprise policy in effect and describes standalone mode.")]},
    {"id": "audit", "title": "Understand what SEL coverage lists", "path": "Settings → Security → Live Security Posture → SEL audit logging",
     "route": "/settings/security/posture",
     "body": ["The expanded SEL row lists covered session-key surfaces, with 19 reported in the posture summary. Entries include Background, CLI, Cron and Dashboard.",
              "This is a coverage list. It does not display the live security-event stream for a request. A native denial needs its blocked result, relevant SEL record and complete MCP journal interval. Where the SEL event lacks a trace field, keep the isolated-session correlation explicit."],
     "cue": "Use this screen to explain which surfaces emit audit records. Use the run’s sanitized receipt to inspect a particular decision.",
     "shots": [shot("02-sel-coverage-viewport.png", "Fresh expanded SEL coverage list; no per-request denial log is displayed here.", "The expanded SEL audit logging row lists session-key surfaces including Background, CLI, Cron and Dashboard.")]},
    {"id": "backend", "title": "Separate backend choice from sign-in", "path": "Developer → Agent Backend",
     "route": "/developer?tab=agent-backend",
     "body": ["This earlier screenshot shows Kiro CLI selected and a “Signed in with GitHub” card. That card reads KAS identity; the standalone CLI has its own sign-in state. At the earlier capture, the CLI was signed out.",
              "The EC2 standalone CLI receipt records authenticated=true via SocialGitHub at 21:09 UTC. The subsequent four native turns have reviewed client/server joins. Selecting Kiro CLI applies to new sessions; recheck its authentication before another take."],
     "cue": "Read the CLI’s own sign-in receipt, then the recorded native results. The two identity surfaces have separate evidence.",
     "shots": [shot("07-agent-backend.jpg", "Earlier backend page, retained to explain the two identity surfaces. The new CLI sign-in is documented separately.", "Kiro CLI is selected beside a GitHub sign-in card representing KAS identity.", False)]},
    {"id": "metrics", "title": "Read Gateway instrumentation", "path": "Settings → Privacy; Developer → Telemetry",
     "route": "/settings/privacy; /developer?tab=telemetry",
     "body": ["The earlier Privacy capture has Record metrics enabled and the anonymous usage heartbeat disabled by the Gateway environment. The fresh Telemetry capture expands the dashboard session “MCP Tool Call Read Allowed” into four completed turns, at 5:24:51, 5:25:41, 5:26:51 and 5:27:21 PM on September 13.",
              "The four durations are 12.3, 8.9, 14.2 and 17.7 seconds. The session total displays 0.5 credits after rounding. Throughput is eight because it includes four background turns. The fault summary reads 0 faults of 4; that is a runtime fault measurement, not a count of policy denials.",
              "The footer labels the metrics source local-only, no egress. That describes metric storage/export, not a network restriction on the agent or AWS requests. These rows establish recorded activity. The separately reviewed reconciliation and authority evidence establish the four specific allowed or denied outcomes."],
     "cue": "Read the named session’s four rows, then explain the background row and open the matched enforcement evidence.",
     "shots": [shot("08-telemetry-controls.jpg", "Earlier Privacy capture: metric recording on, anonymous heartbeat disabled by environment.", "Privacy shows Gateway metrics enabled and anonymous telemetry disabled.", False),
               shot("10-native-turn-telemetry.png", "Fresh native Telemetry: four completed dashboard turns, four background turns and the expanded demo session’s durations and credits.", "Native Telemetry expands the MCP Tool Call Read Allowed session into four completed turns, with durations 12.3, 8.9, 14.2 and 17.7 seconds.")]},
    {"id": "collection", "title": "Read client and server health together", "path": "Apps → Demo Observability",
     "route": "/apps/demo-observability",
     "body": ["The two cards identify their source and sample time. Read Local Gateway off on the Mac card, then the EC2 Gateway and separate MCP service checks. The client’s tunnel check establishes a local TCP listener. “Current” means the sample is fresh.",
              "Collection logs record first samples, health changes and collection errors. The Client and Server buttons filter that event stream. This custom App Kit page does not ingest native tool decisions, SEL records or MCP denial logs. Mac process CPU and EC2 host CPU also use different sampling methods."],
     "cue": "Read timestamps and individual checks, then filter the collection events. Pair enforcement claims with their separate native/server receipts.",
     "shots": [shot("11-client-server-telemetry.jpg", "Earlier custom telemetry capture: both samples Current, local Gateway off and server checks Yes.", "Demo Observability shows macOS client and EC2 server samples with freshness and service checks.", False),
               shot("12-collection-logs.jpg", "Earlier collection events include the observed client health change and recovery.", "Collection logs show source labels, timestamps, event levels and All, Client and Server filters.", False)]},
]

SOURCES = [
    ("Fresh EC2 CLI authentication", "evidence/native-client-demo/20260913/authenticated.json"),
    ("Native Mac recording guide", "docs/NATIVE-CLIENT-DEMO.md"),
    ("MCP and IAM enforcement contract", "infrastructure/mcp-enforcement/README.md"),
    ("Custom telemetry data contract", "infrastructure/observability/APP-INSTALL.md"),
    ("Earlier screenshot capture receipt", "evidence/admin-console/browser-receipt.json"),
    ("Earlier admin findings", "output/kirocrew-admin-findings.md"),
    ("Final four-outcome reconciliation", "evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json"),
    ("Independent reconciliation review", "evidence/native-client-demo/20260913-ui2-reconciled-final/review.json"),
    ("MCP and IAM authority attribution review", "evidence/native-client-demo/20260913-ui2/authority-attribution-review.json"),
    ("Publication export of the incomplete collector receipt", "evidence/native-client-demo/20260913-ui2/receipt-publication.json"),
    ("Native MCP clip review", "evidence/native-client-demo/media-review-mcp-controls.json"),
]

NATIVE_LIMITS = "The original collector receipt remains collection_complete=false because its recent SEL window lost the baseline anchor. Its exact bytes are retained locally; the linked publication export identifies the original by hash. A separate read-only recovery joined the retained rows. The generic reconciler keeps full_native_acceptance=false: it does not decide footage acceptance or every attribution check. Process sampling was not shown to overlap an approval, and SEL integrity relies on the original Gateway verification rather than independent per-row signatures."

STYLE = """
:root{color-scheme:light;--bg:#f5f4f1;--paper:#fff;--ink:#202630;--muted:#5e6470;--line:#dce0e4;--accent:#6553a0;--soft:#eeebf6}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--accent);text-underline-offset:3px}button,select{font:inherit}button,a,select{touch-action:manipulation}:focus-visible{outline:3px solid #8d73d1;outline-offset:4px}button{cursor:pointer}button:disabled{cursor:default;opacity:.4}.shell{max-width:1400px;margin:auto;padding:44px 32px 60px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.11em;color:var(--accent);font-weight:700;margin:0 0 12px}h1{font-size:clamp(32px,4.5vw,56px);line-height:1.1;letter-spacing:-.04em;max-width:950px;margin:0 0 20px}.intro{font-size:19px;max-width:1030px}.status{padding:15px 19px;background:#fff5e7;border:1px solid #ead8ba;border-radius:9px;font-size:14px}.scope{font-size:13px;color:var(--muted)}.toolbar{display:none;position:sticky;top:0;z-index:4;align-items:center;gap:12px;padding:12px 0;background:var(--bg);border-bottom:1px solid var(--line);margin:25px 0}.enhanced .toolbar{display:flex}.toolbar select{flex:1;min-width:0;border:1px solid var(--line);border-radius:7px;padding:10px;background:white;color:var(--ink)}.toolbar button,.figuretools button,.figuretools a,.dialogbar button,.dialogbar a{border:1px solid var(--line);padding:9px 14px;border-radius:7px;background:white;color:var(--accent);text-decoration:none;font-size:13px}.counter{font-size:12px;color:var(--muted);white-space:nowrap}.layout{display:grid;grid-template-columns:210px minmax(0,1fr);gap:28px}.toc{align-self:start;position:sticky;top:90px;font-size:13px}.toc a{display:block;padding:10px 12px;border-left:2px solid var(--line);text-decoration:none;color:var(--muted);line-height:1.4}.toc a[aria-current=step]{color:var(--accent);background:var(--soft);border-color:var(--accent)}.step{background:white;border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-bottom:26px;scroll-margin-top:90px}.copy{padding:25px 30px}.number{font-size:12px;color:var(--accent);font-weight:700;letter-spacing:.06em}.step h2{font-size:29px;line-height:1.2;letter-spacing:-.02em;margin:7px 0 12px}.route{font-size:12px;color:var(--muted);overflow-wrap:anywhere}.copy p{margin:15px 0}.cue{border-left:3px solid #bbb0d3;padding-left:14px;color:var(--muted);font-size:14px}.figuretools{display:flex;gap:10px;padding:11px 18px;align-items:center;border-top:1px solid var(--line);background:#f8f8fa}.stamp{font-size:11px;color:var(--muted);margin-right:auto}figure{margin:0;border-top:1px solid var(--line);background:#080909}.image-button{display:block;padding:0;border:0;width:100%;background:#080909;cursor:zoom-in}.image-button img{display:block;width:100%;height:auto;max-height:760px;object-fit:contain}figcaption{background:#f8f8fa;color:var(--muted);padding:12px 18px;font-size:12px}.stopnav{display:flex;justify-content:space-between;gap:20px;padding:18px 28px;font-size:13px}.evidence{border-top:1px solid var(--line);padding-top:25px;margin-top:25px;font-size:14px}.evidence h2{font-size:23px;margin:0 0 10px}.evidence ul{padding-left:20px}.evidence li{margin:7px 0}.footer{font-size:12px;color:var(--muted);border-top:1px solid var(--line);padding-top:20px;margin-top:30px}dialog{padding:0;border:1px solid #545863;border-radius:10px;background:#080909;color:white;width:96vw;max-width:1700px;height:94vh;max-height:94vh}dialog::backdrop{background:#141621df}.dialogbar{display:flex;gap:12px;align-items:center;justify-content:space-between;padding:12px 18px;background:#171920}.dialogbar span{margin-right:auto;font-size:13px}.dialogbar button,.dialogbar a{background:#292c36;color:#fff;border-color:#525867}.zoomscroll{overflow:auto;height:calc(100% - 65px)}.zoomscroll img{display:block;width:100%;height:100%;object-fit:contain}.zoomscroll.actual img{width:auto;height:auto;max-width:none;object-fit:initial}.nojs{font-size:13px}@media(max-width:900px){.shell{padding:25px 18px}.layout{grid-template-columns:1fr}.toc{position:static;display:flex;gap:8px;overflow:auto}.toc a{min-width:140px;border-left:0;border-bottom:2px solid var(--line)}.copy{padding:23px}.toolbar{gap:7px}.toolbar button{padding:9px}.counter{display:none}.figuretools{flex-wrap:wrap}.stamp{flex-basis:100%}.dialogbar{flex-wrap:wrap}.dialogbar span{flex-basis:100%}.zoomscroll{height:calc(100% - 110px)}}@media(max-width:550px){.shell{padding:22px 12px}.intro{font-size:17px}.toolbar{flex-wrap:wrap}.toolbar select{order:-1;flex-basis:100%}.toolbar button{flex:1}.step h2{font-size:24px}.copy{padding:20px}.stepnav{padding:15px}.figuretools a,.figuretools button{padding:8px 10px}}@media print{.toolbar,.toc,.figuretools,.stopnav,.nojs{display:none!important}.layout{display:block}.step[hidden]{display:block!important}.step{break-inside:avoid}.shell{padding:0}body{font-size:12px;background:white}h1{font-size:32px}figure img{max-height:none}.evidence{break-before:page}}
"""

STYLE += "\n.step{scroll-margin-top:calc(var(--tour-toolbar-height,90px) + 16px)}.step h2{scroll-margin-top:calc(var(--tour-toolbar-height,90px) + 60px)}\n"

SCRIPT = """
const steps=[...document.querySelectorAll('.step')], links=[...document.querySelectorAll('.toc a')], choice=document.getElementById('stop-choice');
const previous=document.getElementById('previous'),next=document.getElementById('next'),counter=document.getElementById('counter');
let index=0;
function activate(i,focus=false){index=Math.max(0,Math.min(steps.length-1,i));steps.forEach((s,n)=>s.hidden=n!==index);links.forEach((a,n)=>{if(n===index)a.setAttribute('aria-current','step');else a.removeAttribute('aria-current')});choice.value=String(index);previous.disabled=index===0;next.disabled=index===steps.length-1;counter.textContent=`${index+1} of ${steps.length}`;if(focus)steps[index].querySelector('h2').focus({preventScroll:true});}
function move(i){if(i<0||i>=steps.length)return;history.replaceState(null,'','#'+steps[i].id);activate(i);const toolbarHeight=document.querySelector('.toolbar').getBoundingClientRect().height;document.documentElement.style.setProperty('--tour-toolbar-height',`${toolbarHeight}px`);const top=steps[index].getBoundingClientRect().top+window.scrollY-toolbarHeight-16;window.scrollTo({top:Math.max(0,top),behavior:'auto'});steps[index].querySelector('h2').focus({preventScroll:true});}
function readHash(){const i=steps.findIndex(s=>'#'+s.id===location.hash);if(i>=0)activate(i);}
document.body.classList.add('enhanced');activate(0);readHash();
previous.addEventListener('click',()=>move(index-1));next.addEventListener('click',()=>move(index+1));choice.addEventListener('change',()=>move(Number(choice.value)));
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',e=>{const i=steps.findIndex(s=>'#'+s.id===a.hash);if(i>=0){e.preventDefault();move(i)}}));window.addEventListener('hashchange',readHash);
const dialog=document.getElementById('zoom-dialog'),zoom=document.getElementById('zoom-image'),title=document.getElementById('zoom-title'),scroll=document.querySelector('.zoomscroll'),size=document.getElementById('actual-size'),original=document.getElementById('zoom-original');
document.querySelectorAll('[data-zoom]').forEach(button=>button.addEventListener('click',()=>{const source=document.getElementById(button.dataset.zoom);zoom.src=source.src;zoom.alt=source.alt;title.textContent=source.alt;original.href=source.dataset.original;scroll.classList.remove('actual');size.setAttribute('aria-pressed','false');size.textContent='Actual pixels';dialog.showModal()}));
document.getElementById('close-zoom').addEventListener('click',()=>dialog.close());size.addEventListener('click',()=>{const actual=scroll.classList.toggle('actual');size.setAttribute('aria-pressed',String(actual));size.textContent=actual?'Fit image':'Actual pixels';if(actual)scroll.focus()});
document.addEventListener('keydown',e=>{if(dialog.open||e.altKey||e.ctrlKey||e.metaKey||/INPUT|TEXTAREA|SELECT|BUTTON/.test(e.target.tagName))return;if(e.key==='ArrowRight'){e.preventDefault();move(index+1)}if(e.key==='ArrowLeft'){e.preventDefault();move(index-1)}});
"""


def esc(value):
    return html.escape(str(value), quote=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_relative_file(value, base=ROOT):
    """Accept a regular, non-symlink file under the selected checkout folder."""
    if not isinstance(value, str) or "\\" in value:
        raise ValueError("Expected a checkout-relative file path")
    relative = Path(value)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError("Expected a checkout-relative file path")
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"Symlink input is not supported: {value}")
    if not current.is_file():
        raise ValueError(f"Missing regular input: {value}")
    current.resolve().relative_to(base.resolve())
    return current


def checked_public_source(value):
    """Limit added links to scoped demo evidence; each source still needs review."""
    if not isinstance(value, str):
        raise ValueError("Expected a scoped evidence path")
    parts = value.split("/")
    if (len(parts) < 3 or parts[:2] not in [["evidence", "native-client-demo"], ["evidence", "admin-console"], ["evidence", "enterprise-managed"], ["evidence", "managed-host-20260914"]]
            or any(part.startswith(".") or part == "raw" for part in parts)
            or any(token in parts[-1] for token in (".local.", "preflight"))):
        raise ValueError("Added sources must be reviewed JSON receipts in the scoped demo evidence folders")
    path = checked_relative_file(value)
    if path.suffix != ".json":
        raise ValueError("Added evidence links must name reviewed JSON receipts")
    if path.name in {"baseline.json", "receipt.json"}:
        raise ValueError("Use the publication export, not a private collector original")
    return path


def load_capture_group(manifest_path, stops):
    """Append inspected captures to existing stops; evidence links never grant a verdict.

    The JSON input contains schemaVersion=1, groupId, captureLabel, and stops.
    Each stop names an existing id and shots with output-relative file, sha256,
    caption and alt. Optional body/cue replace that stop's reviewed prose. An
    optional sources array contains label/path/sha256 for publishable receipts.
    """
    relative = manifest_path.absolute().relative_to(ROOT).as_posix()
    manifest_path = checked_relative_file(relative)
    data = json.loads(manifest_path.read_text())
    if data.get("schemaVersion") != 1 or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", data.get("groupId", "")):
        raise ValueError("Capture group needs schemaVersion=1 and a lowercase groupId")
    label = data.get("captureLabel")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("Capture group needs a dated captureLabel")
    updates = data.get("stops")
    if not isinstance(updates, list) or not updates:
        raise ValueError("Capture group needs at least one stop with inspected screenshots")
    by_id = {stop["id"]: stop for stop in stops}
    seen = set()
    for update in updates:
        stop_id = update.get("id")
        if stop_id not in by_id or stop_id in seen:
            raise ValueError("Capture group stop ids must be existing and unique")
        seen.add(stop_id)
        shots = update.get("shots")
        if not isinstance(shots, list) or not shots:
            raise ValueError("Each capture group stop needs actual screenshots")
        for item in shots:
            path = checked_relative_file(item.get("file"), OUT)
            if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) or sha(path) != item["sha256"]:
                raise ValueError(f"Screenshot differs from its inspected capture hash: {path.name}")
            if any(not isinstance(item.get(key), str) or not item[key].strip() for key in ("caption", "alt")):
                raise ValueError("Each inspected screenshot needs a caption and alt text")
            by_id[stop_id]["shots"].append({"file": item["file"], "caption": item["caption"], "alt": item["alt"],
                                          "capture_label": label, "capture_group": data["groupId"]})
        if "body" in update:
            if not isinstance(update["body"], list) or not update["body"] or any(not isinstance(p, str) or not p.strip() for p in update["body"]):
                raise ValueError("Stop body must contain nonempty reviewed paragraphs")
            by_id[stop_id]["body"] = update["body"]
        if "cue" in update:
            if not isinstance(update["cue"], str) or not update["cue"].strip():
                raise ValueError("Stop cue must contain reviewed text")
            by_id[stop_id]["cue"] = update["cue"]
    sources = []
    for item in data.get("sources", []):
        path = checked_public_source(item.get("path"))
        if sha(path) != item.get("sha256"):
            raise ValueError(f"Capture evidence changed after review: {path.name}")
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            raise ValueError("Capture evidence needs a source label")
        sources.append((item["label"], item["path"]))
    return sources, {"path": relative, "sha256": sha(manifest_path), "group_id": data["groupId"],
                     "capture_label": label, "stop_ids": sorted(seen),
                     "scope": "Appended original screenshots and reviewed copy; this input does not change native outcome verdicts."}


def load_managed_summary(manifest_path, stops):
    """Apply the reviewed managed-policy edition after the historical captures."""
    relative = manifest_path.absolute().relative_to(ROOT).as_posix()
    manifest_path = checked_public_source(relative)
    data = json.loads(manifest_path.read_text())
    if data.get("schema_version") != 1 or data.get("kind") != "managed_native_presentation":
        raise ValueError("Expected the reviewed managed native presentation summary")
    policy, native, client = (data.get(key, {}) for key in ("policy", "native", "client"))
    if (policy.get("version") != 1 or policy.get("sandbox_floor") != "cc"
            or policy.get("denied_approval_modes") != ["yolo"]
            or policy.get("denied_mcp_tools") != ["@aws-enforcement/crew_denied"]
            or policy.get("owner_mutable_duplicate_hook_removed") is not True
            or policy.get("refresh") != "startup only" or policy.get("fail_closed") is not True
            or native.get("allowed_read_verified") is not True or native.get("allowed_read_filmed") is not False
            or native.get("managed_denial_verified") is not True or native.get("managed_denial_filmed") is not True
            or client.get("local_gateway_off") is not True or client.get("quit_and_relaunch_verified") is not True):
        raise ValueError("Managed summary no longer supports this edition's bounded claims")
    descriptions = {
        "governance": ("Active Policy v1 comes from a file, is fetched at startup and sets the cc sandbox floor. The panel lists one MCP deny and one denied approval mode.", "Governance Policy shows Policy v1, file source, startup-only refresh, cc sandbox floor and the configured policy lists."),
        "managed_command": ("Search s3: the built-in upload deny is on and its switch is disabled. The lock and tooltip identify organization policy. This is a configured command rule, not a recorded S3 upload attempt.", "The S3 upload command rule is on with a disabled switch and an organization-policy explanation."),
        "approval_modes": ("The user's approval menu has Normal selected, Reads and Trust available, and no YOLO item. No approval mode was changed.", "The session approval menu lists Normal, Reads and Trust; Normal is selected and YOLO is absent."),
        "mcp_enabled": ("MCP Servers shows the Crew-only aws-enforcement server enabled with four tools. Enabled describes availability; the managed deny still applies when a tool is invoked.", "MCP Servers shows the enabled Crew-only aws-enforcement server with four tools."),
        "mcp_staged": ("One local restriction is pending, with Apply and Discard available. It was discarded after this capture; no local restriction was applied.", "The MCP manager shows one staged tool restriction and the Apply and Discard buttons."),
        "session_mcp": ("Session options lists aws-enforcement as started and shows 0/4 tool specifications loaded, with the four names deferred. The list has no per-tool governance lock badge.", "Session options shows aws-enforcement started, zero of four tool specifications loaded, and read_allowed, crew_denied, mcp_denied and iam_denied listed as deferred tools."),
        "native_denial": ("The filmed macOS take expands the host notice for the automatic governance-policy refusal. The ui4 receipt joins this result to the policy-layer SEL decision and a complete MCP journal interval with no matching service arrival.", "The actual macOS client shows the expanded host notice identifying the automatic governance-policy block of crew_denied."),
    }
    images = data.get("screenshots")
    if not isinstance(images, list) or len(images) != len(descriptions) or {item.get("role") for item in images} != set(descriptions):
        raise ValueError("The managed edition requires exactly the seven inspected screenshot roles")
    roles = {}
    for item in images:
        value = item.get("path")
        if not isinstance(value, str) or not value.startswith("evidence/enterprise-managed/") or "/screenshots/" not in value:
            raise ValueError("Managed screenshots must stay in their reviewed evidence screenshot folder")
        path = checked_relative_file(value)
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"} or sha(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
            raise ValueError("Managed screenshot differs from its reviewed bytes")
        caption, alt = descriptions[item["role"]]
        roles[item["role"]] = {"source": value, "file": "../" + value, "caption": caption, "alt": alt,
                                "capture_label": "September 13, 2026 · late evening EDT · managed policy active",
                                "capture_group": "managed-policy-20260913"}
    source_labels = {
        "policy-verify.json": "Active managed policy readback",
        "mcp-verify.json": "MCP configuration and policy readback",
        "native-managed-verification.json": "Managed native allowed read and automatic deny correlation (ui3; read not filmed)",
        "native-managed-ui4-verification.json": "Filmed automatic managed MCP denial correlation (ui4)",
        "native-managed-artifact-review.json": "Independent managed native artifact review",
        "host-runtime-check.json": "Root-owned policy and separate service sandbox observations",
        "client-relaunch.json": "Mac quit and relaunch with local Gateway off (before policy activation)",
        "media-review.json": "Managed native clip review",
    }
    receipts = data.get("receipts")
    if not isinstance(receipts, list) or len(receipts) != len(source_labels) or {Path(item.get("path", "")).name for item in receipts} != set(source_labels):
        raise ValueError("Managed summary needs its complete reviewed receipt set")
    sources = [("Managed policy, client state and screenshot summary", relative)]
    for item in receipts:
        path = checked_public_source(item.get("path"))
        if sha(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
            raise ValueError("Managed receipt differs from its reviewed bytes")
        sources.append((source_labels[path.name], item["path"]))
    by_id = {stop["id"]: stop for stop in stops}
    for stop in stops:
        for item in stop["shots"]:
            item["capture_label"] += " · before managed policy"
            item["caption"] = "Before managed policy. " + item["caption"].replace("Fresh ", "Earlier ").replace("fresh ", "earlier ")
    by_id["host"]["body"] = [
        "The client is macOS Nightly September 13. The existing ARM EC2 host runs the September 12 server Nightly with Kiro CLI 2.21.4. The Mac quit and relaunched with its local Gateway off and the remote connection on port 5599. That continuity check preceded policy activation; the later native receipts verify execution after activation.",
        "The retained Overview and Performance images predate managed policy. They identify the remote build, ARM Linux and the EC2 workspace; their uptime and activity counters belong to those capture times. Keep the Gateway, backend and workspace in the single endpoint-control box."]
    by_id["posture"]["body"] = [
        "The active file policy sets the Linux sandbox floor to cc. Its readback and the Governance Policy view establish the configured floor. A separate runtime check saw six Kiro CLI descendants with seccomp mode 2, NoNewPrivs enabled and a different mount namespace; it did not attribute those processes to the exact recorded tool calls.",
        "The earlier posture image below shows Standard sandbox, Interactive approval and coverage counts of 143 credential paths, 23 protected paths and 112 built-in command rules. Those are pre-policy capture values. Coverage counts describe registries; they do not establish that a particular read, write or command was blocked."]
    by_id["rules"]["body"] = [
        "In the current Denied Commands view, search s3. The built-in S3 upload deny is on, and its disabled switch has a lock and an organization-policy explanation. The file policy also contains a managed marker command. This screenshot establishes the locked configuration; no managed S3 upload attempt was recorded.",
        "Command patterns and MCP tool policy are separate controls. The root-owned file now denies the canonical tool @aws-enforcement/crew_denied. The duplicate owner-editable auto_deny_tools hook was removed before the managed native take. This command-rule screen does not manage that MCP deny.",
        "The four older images retain the catalog, teardown coverage and temporary KIROCREW_DEMO_COMMAND_CONTROL_20260913 rule before and after cleanup. That earlier marker was removed; its cleanup and native refusal receipts retain their original scope."]
    by_id["rules"]["cue"] = "Show the locked S3 upload rule, then identify the separate managed MCP deny. Date the old temporary-rule take before comparing it."
    by_id["rules"]["route"] = "/settings/security/rules → search s3"
    by_id["rules"]["shots"].insert(0, roles["managed_command"])
    by_id["approval"].update({"title": "Read the user's approval choices", "path": "Native session → approval-mode menu; earlier Settings → Security → YOLO",
        "route": "Open the session's approval-mode menu; earlier settings route /settings/security/approval",
        "body": ["The current session menu has Normal selected. Reads and Trust remain available, while YOLO is absent. The managed file policy denies yolo; it does not force every session into Normal. No mode was changed during this inspection.",
                 "The earlier settings image shows Interactive and a six-hour duration for the next auto-approve activation. That saved duration predates the managed policy and does not grant permission to use YOLO now."],
        "cue": "Read what the user can choose now, then distinguish the old next-activation duration from the active policy."})
    by_id["approval"]["shots"].insert(0, roles["approval_modes"])
    by_id["governance"]["body"] = [
        "The current viewer shows Policy v1, Source: file, startup-only fetch and a cc sandbox floor. The policy is loaded from /etc/kirocrew-demo/security-policy.json through a protected systemd environment, with fail-closed behavior configured. Changes require a Gateway restart to be fetched.",
        "The root-owned policy file is not writable by the Crew service account. It sets a floor against that account and the owner console; host root retains authority. This deployment does not establish signed fleet policy, enterprise SSO or separate human roles. The portal displays the policy; it does not author the file.",
        "The protected MCP service still enforces its own grants, and AWS evaluates the instance role. Those authorities remain outside this portal. The earlier standalone screenshot below is preserved to show the state before policy activation."]
    by_id["governance"]["cue"] = "Read the policy source, refresh timing and floor. Name the service account it constrains, then the separate MCP-service and AWS authorities."
    by_id["governance"]["shots"].insert(0, roles["governance"])
    mcp = {"id": "mcp", "title": "See what the user can enable", "path": "Capabilities → MCP Servers; native session → Session options → MCP servers",
        "route": "/capabilities?tab=mcp opened Services first; click the visible MCP Servers tab. In the session, open Session options → MCP servers.",
        "body": ["The MCP manager shows the Crew-only aws-enforcement server enabled with four tools. Local controls can narrow the tools exposed to Crew. The second image records one staged restriction with Apply and Discard; it was discarded, so no restriction was applied.",
                 "In the actual web view of the native session, aws-enforcement has a green started ring. Its inventory reports 0/4 specifications loaded and lists read_allowed, crew_denied, mcp_denied and iam_denied as deferred tools. Neither this list nor the manager has a per-tool governance lock badge.",
                 "Enabled means available to the client. The canonical crew_denied invocation still met the root-managed deny. The filmed macOS host notice shows the automatic policy refusal; the ui4 receipt correlates it to policy-layer SEL evidence and a complete MCP journal interval with no matching service arrival. There was no approval card or operator refusal for this request.",
                 "A separate managed allowed read succeeded and has a client-to-service evidence join, but that read was not filmed. The earlier MCP grant and IAM denial recordings predate this policy change and keep their original evidence scope."],
        "cue": "Move from availability to deferred inventory to the actual native refusal. Use the receipt to identify the denying authority.",
        "shots": [roles[key] for key in ("mcp_enabled", "mcp_staged", "session_mcp", "native_denial")]}
    stops.insert(stops.index(by_id["governance"]) + 1, mcp)
    by_id["audit"]["body"][0] = "The earlier expanded SEL row lists covered session-key surfaces, with 19 reported in the posture summary. Entries include Background, CLI, Cron and Dashboard. This capture predates managed policy."
    by_id["backend"]["body"][1] = "The EC2 standalone CLI receipt records authenticated=true via SocialGitHub at 21:09 UTC. The original four-turn run and the later managed native receipts each establish their own results. The selected backend remains Kiro CLI 2.21.4. The card shown here is not evidence of enterprise SSO or the CLI's current sign-in by itself."
    by_id["metrics"]["body"].insert(0, "These metric captures all precede managed policy. They explain the dashboard's measurements; they do not report a new managed-policy run.")
    by_id["collection"]["body"].insert(0, "All four collection captures below precede managed policy. Their values are dated samples, retained to explain the client/server health view.")
    return sources, {"path": relative, "sha256": sha(manifest_path), "observed_at": data["observed_at"],
                     "policy_sha256": policy["policy_sha256"], "screenshot_roles": list(roles),
                     "native_claim_scope": native, "scope": "Seven managed-policy captures plus 19 unchanged earlier images; earlier outcomes retain their original authority and collection limits."}


def image_info(item):
    path = checked_relative_file(item["source"]) if "source" in item else checked_relative_file(item["file"], OUT)
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        mime = "image/png"
    elif data[:2] == b"\xff\xd8":
        width = height = 0
        p = 2
        while p < len(data):
            if data[p] != 255:
                p += 1
                continue
            while p < len(data) and data[p] == 255:
                p += 1
            marker = data[p]
            p += 1
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            length = int.from_bytes(data[p:p + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height, width = struct.unpack(">HH", data[p + 3:p + 7])
                break
            if length < 2:
                raise ValueError(f"Invalid JPEG segment: {path}")
            p += length
        mime = "image/jpeg"
    else:
        raise ValueError(f"Unsupported screenshot format: {path}")
    if not width or not height:
        raise ValueError(f"Invalid screenshot dimensions: {path}")
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), "width": width, "height": height, "mime_type": mime,
            "capture_label": item["capture_label"], "capture_group": item["capture_group"],
            "uri": f"data:{mime};base64," + base64.b64encode(data).decode()}


def load_host_results(manifest_path, stops):
    """Add inspected native result frames and direct links to their bounded proof."""
    relative = manifest_path.absolute().relative_to(ROOT).as_posix()
    manifest_path = checked_public_source(relative)
    data = json.loads(manifest_path.read_text())
    if (data.get("schemaVersion") != 1 or data.get("kind") != "native_host_results_tour"
            or data.get("verifiedOutcomes") != ["sensitive_enoent", "protected_write_hook", "imds_tcp_rejected"]):
        raise ValueError("Expected the reviewed three-outcome native host tour input")
    descriptions = {
        "sensitive": ("Actual recording frame at clip 24 seconds (raw 50 seconds). The native read returned ENOENT for the public canary. Separate current namespace evidence corroborates that the host file is hidden; this was not a read-hook denial.", "Actual native recording frame shows the public sensitive-path canary read returning ENOENT."),
        "protected": ("Actual macOS client result: the prepared write was refused by the built-in protected-config write hook. The UI displays both 1 file changed and no changes. The separate host readback confirms the marker file is absent.", "The native macOS client reports a protected-config write refusal; its file panel displays both 1 file changed and no changes."),
        "imds": ("Actual macOS result: connected false, errno 113, zero application bytes sent and no metadata requested. The sanitized receipt joins the one native execution to the firewall counter changing from 2 to 3 in the observed interval.", "The native IMDS TCP result reports EHOSTUNREACH, zero application bytes and no metadata request."),
    }
    images = data.get("screenshots", [])
    if len(images) != 3 or {item.get("role") for item in images} != set(descriptions):
        raise ValueError("Host results need three inspected native result images")
    shots = []
    for item in images:
        value = item.get("path", "")
        if not value.startswith(("evidence/managed-host-20260914/screenshots/", "output/native-host-managed-20260914/")):
            raise ValueError("Host result image must be an inspected capture or decoded recording frame")
        path = checked_relative_file(value)
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"} or sha(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
            raise ValueError("Host result image differs from its inspected bytes")
        caption, alt = descriptions[item["role"]]
        shots.append({"source": value, "file": "../" + value, "caption": caption, "alt": alt,
                      "capture_label": "September 14, 2026 · native macOS result · not admin-console UI",
                      "capture_group": "completed-host-results-20260914"})
    sources = [("September 14 native host result images and evidence bindings", relative)]
    receipts = data.get("sources", [])
    if not receipts:
        raise ValueError("Native result frames require their sanitized supporting receipts")
    for item in receipts:
        value = item.get("path")
        media_documents = {"output/native-host-managed-20260914/manifest.json", "output/native-host-managed-20260914/keyframe-provenance.json"}
        path = (checked_relative_file(value) if value in media_documents or value == "evidence/managed-host-20260914/findings.md"
                else checked_public_source(value))
        if sha(path) != item.get("sha256") or path.stat().st_size != item.get("bytes"):
            raise ValueError("Host result receipt differs from its reviewed bytes")
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            raise ValueError("Host evidence needs a descriptive label")
        sources.append((item["label"], item["path"]))
    clips = data.get("clips", [])
    clip_names = {"native-managed-sensitive-read", "native-managed-protected-write", "native-managed-imds-tcp"}
    if len(clips) != 3 or {item.get("id") for item in clips} != clip_names:
        raise ValueError("Host results need the three actual reviewed clips")
    for item in clips:
        value = item.get("path", "")
        path = checked_relative_file(value)
        if (not value.startswith("output/native-host-managed-20260914/") or path.suffix != ".mp4"
                or sha(path) != item.get("sha256") or path.stat().st_size != item.get("bytes")):
            raise ValueError("Host clip differs from its reviewed recording output")
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            raise ValueError("Host clip needs a descriptive label")
        sources.append((item["label"], value))
    stops.append({"id": "host-results", "title": "Inspect the native host results",
        "path": "Recorded macOS client sessions; supporting receipts below", "route": "Native client results, not an admin-console route",
        "body": ["Three September 14 recordings complete the previously unfinished host checks. These images show the native Mac client. The existing admin screenshots and dashboard counters do not establish these outcomes.",
                 "Sensitive-path read: CLI argument validation returned ENOENT for the public canary. A later readback found the host file hidden from the current CLI descendants by a .aws tmpfs mask. The native classifier remains accepted:false; the readback does not identify the historical syscall PID.",
                 "Protected-path write: Crew's built-in hook blocked the marker, which remained absent. Its source files are root-owned. The hook runs before the managed filesystem rule, so this take tests that earlier hook. The host readback resolves the UI's conflicting 1 file changed heading and no changes row.",
                 "IMDS TCP: the user approved the helper source read once and execution once. One native execution made one fixed TCP attempt, returned errno 113, sent zero application bytes and requested no metadata. The Crew UID's firewall counter increased from 2 to 3 during the observed interval. This does not establish that the whole host lacks an IMDS route. The earlier unanswered IMDS approval timeout remains a separate historical take.",
                 "Open the three actual clips and sanitized receipts in the evidence list. Keep each result tied to its mechanism: filesystem visibility, a built-in write hook or an outbound network rule."],
        "cue": "Read the native result first, then the matching receipt. Do not count these frames as fresh admin-dashboard measurements.",
        "shots": shots})
    return sources, {"path": relative, "sha256": sha(manifest_path), "observed_date": "2026-09-14",
                     "verified_outcomes": data["verifiedOutcomes"], "scope": "Three native result images and recorded clips with separately reviewed proof; earlier admin captures are unchanged."}


def build(proof_paths, capture_group=None, validate_only=False, browser_review_file=None, managed_summary=None, host_results=None):
    stops = copy.deepcopy(STOPS)
    sources = list(SOURCES)
    capture_metadata = None
    managed_metadata = None
    host_metadata = None
    edition_date = "September 13, 2026"
    status = STATUS
    status_link = ("Read the four-outcome reconciliation", "evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json")
    scope = "Fresh security captures and earlier baseline images are dated separately. All screenshots are embedded unchanged. Native client enforcement requires a separate recording and receipt."
    native_limits = NATIVE_LIMITS
    evidence_intro = "The native recordings show the Mac requests and results. The final reconciliation and separate authority review support the allowed S3 read and the Crew, MCP and IAM denials. This screenshot tour explains the console’s observed views."
    md_changes = "Added fresh security, command-rule, approval, governance, SEL-coverage and completed-turn telemetry captures. Updated the four native outcomes from the final reconciliation and authority review, while retaining the original collection failure and remaining limits. Earlier reference screenshots keep their capture dates."
    footer_changes = "Added fresh security coverage, policy screens and completed-turn telemetry, explained the separate MCP/IAM authority, and retained earlier reference images with their capture dates."
    if capture_group:
        extra_sources, capture_metadata = load_capture_group(capture_group, stops)
        sources.extend(extra_sources)
        sources.append(("Current native admin findings", "output/kirocrew-native-admin-findings.md"))
        sources.append(("Host-control scenario guide", "docs/HOST-CONTROL-SCENARIOS.md"))
        status = "Earlier MCP/IAM run: " + STATUS
        native_limits = "Earlier MCP/IAM collection: " + NATIVE_LIMITS
        evidence_intro += " Later host observations, reviews and cleanup are linked separately below. Their results do not change the earlier collection verdict."
        md_changes = "Retained the 13 accepted images and appended six later host captures: the temporary command rule before and after cleanup, command and authentication turn metrics, current client/server samples and filtered server collection events. The added captions distinguish configuration, runtime measurements and security decisions."
        footer_changes = "Retained the earlier captures and added the temporary-rule cleanup, host-turn metrics and current client/server health views. Each native outcome remains tied to its own reviewed evidence."
    if managed_summary:
        if not capture_group:
            raise ValueError("The managed edition requires the preceding host capture group")
        extra_sources, managed_metadata = load_managed_summary(managed_summary, stops)
        # The tour is independently reproducible from the frozen evidence. Live
        # recording guides are owned and updated separately from this edition.
        sources = [("Before managed policy: " + label, path) for label, path in sources
                   if path not in {"docs/NATIVE-CLIENT-DEMO.md", "docs/HOST-CONTROL-SCENARIOS.md"}]
        sources = extra_sources + sources
        status = "Managed file policy is active on the EC2 Gateway. A fresh macOS take records its automatic MCP-tool refusal. A separate managed allowed read is verified in the receipts but was not filmed."
        status_link = ("Read the filmed managed-denial correlation", "evidence/enterprise-managed/20260913/native-managed-ui4-verification.json")
        scope = "Ten stops, seven managed-policy captures and 19 unchanged images from before the change. Each image is dated. Configuration, Gateway metrics, collection health and security decisions have separate evidence."
        evidence_intro = "The managed receipts establish the file policy, client state, allowed read and automatic MCP denial. The filmed take covers the managed denial. The earlier eight recordings and host observations retain their original evidence limits; they are not reclassified as managed-policy proof."
        native_limits = "Host root retains authority. This deployment does not establish signed fleet policy, enterprise SSO or human-role RBAC. The Linux cc floor is not macOS Seatbelt or strict-tier isolation. Sensitive-path read, protected-path write and native IMDS recordings remain unfinished. The policy-layer SEL join uses the isolated session, tool, reason and interval; those SEL events have no direct tool-call or trace-ID field. Earlier MCP/IAM collection: " + NATIVE_LIMITS
        md_changes = "Added the active file policy, locked S3 command rule, user approval menu, MCP availability and deferred inventory views, and the filmed native managed-denial result. Preserved all 19 earlier screenshots with pre-policy labels and added seven unchanged captures. The staged MCP restriction was discarded."
        footer_changes = md_changes
    if host_results:
        if not managed_summary:
            raise ValueError("The current host results extend the managed-policy tour")
        extra_sources, host_metadata = load_host_results(host_results, stops)
        sources = extra_sources + [(label, path) for label, path in sources if path != "output/kirocrew-admin-findings.md"]
        sources.append(("Current findings, followed by the preserved September 13 findings", "output/kirocrew-admin-findings.md"))
        edition_date = "September 14, 2026"
        status += " Three September 14 native recordings now cover the sensitive-path read, protected-path write and fixed IMDS TCP check."
        status_link = ("Read the completed host-result evidence bindings", host_metadata["path"])
        scope = "Eleven stops and 29 original images: 26 dated images retained from the previous edition, plus three clearly labeled native client result images. Configuration, Gateway metrics, collection health and security decisions have separate evidence."
        native_limits = native_limits.replace("Sensitive-path read, protected-path write and native IMDS recordings remain unfinished.", "The three host checks now have separate native recordings and sanitized evidence. The sensitive-read result is ENOENT with separate current namespace corroboration; it is not a read-hook denial. The earlier unanswered IMDS approval remains historical.")
        evidence_intro += " The September 14 host-result receipts and three actual clips are linked first. Their results do not turn the earlier admin counters into security-decision evidence."
        md_changes = "Retained all 26 prior images and added one native-results stop with three original result images and links to the three actual clips. Updated the sensitive-read, protected-write and IMDS status from their sanitized receipts; preserved the earlier unanswered IMDS take and its limits."
        footer_changes = md_changes
    for i, path in enumerate(proof_paths, 1):
        relative = path.absolute().relative_to(ROOT).as_posix()
        checked_public_source(relative)
        sources.append((f"Native run receipt {i} (read its recorded verdict)", relative))
    for _, path in sources:
        if not (ROOT / path).is_file():
            raise ValueError(f"Missing evidence source: {path}")
    auth = json.loads((ROOT / SOURCES[0][1]).read_text())
    if auth.get("authenticated") is not True or auth.get("method") != "SocialGitHub":
        raise ValueError("The source authentication receipt no longer supports this tour’s dated statement")
    native = json.loads((ROOT / "evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json").read_text())
    native_review = json.loads((ROOT / "evidence/native-client-demo/20260913-ui2-reconciled-final/review.json").read_text())
    authority = json.loads((ROOT / "evidence/native-client-demo/20260913-ui2/authority-attribution-review.json").read_text())
    if native.get("bounded_four_outcomes_reconciled") is not True or native_review.get("verdict") != "no_material_findings" or authority.get("verdict") != "bounded_attribution_supported":
        raise ValueError("Native evidence no longer supports the four bounded outcome statement")
    publication = json.loads((ROOT / "evidence/native-client-demo/20260913-ui2/receipt-publication.json").read_text())
    if (publication.get("kind") != "native_client_publication_export"
            or publication.get("run_id") != native["run_id"]
            or publication.get("private_source", {}).get("sha256") != native["source_sha256"]["receipt.json"]
            or publication.get("collection_complete") != native["original_collection_complete"]):
        raise ValueError("The publication export does not match the retained original native receipt")
    images, cards = [], []
    md = [f"# {TITLE}", "", edition_date + " · macOS client / ARM EC2 server · owner console", "", INTRO, "", status, "",
          scope, ""]
    for index, stop in enumerate(stops):
        paragraphs = "".join(f"<p>{esc(text)}</p>" for text in stop["body"])
        figures = []
        md += [f"## {index + 1:02}. {stop['title']}", "", f"Open **{stop['path']}**.", "", f"Route: `{stop['route']}`", ""]
        for paragraph in stop["body"]:
            md += [paragraph, ""]
        md += [f"Presenter cue: {stop['cue']}", ""]
        for item in stop["shots"]:
            info = image_info(item)
            info["stop"] = stop["id"]
            images.append(info)
            image_id = f"image-{len(images)}"
            figures.append(f'<div class="figuretools"><span class="stamp">{esc(item["capture_label"])}</span><button type="button" data-zoom="{image_id}">Zoom image</button><a href="{esc(item["file"])}" target="_blank" rel="noopener">Open original</a></div><figure><button class="image-button" type="button" data-zoom="{image_id}" aria-label="Enlarge: {esc(item["alt"])}"><img id="{image_id}" src="{info["uri"]}" data-original="{esc(item["file"])}" alt="{esc(item["alt"])}" width="{info["width"]}" height="{info["height"]}"></button><figcaption>{esc(item["caption"])}</figcaption></figure>')
            md += [f"*{item['capture_label']}.* {item['caption']}", "", f"![{item['alt']}]({item['file']})", ""]
        previous = f'<a href="#{stops[index-1]["id"]}">← Previous stop</a>' if index else "<span></span>"
        following = f'<a href="#{stops[index+1]["id"]}">Next stop →</a>' if index + 1 < len(stops) else '<a href="#evidence">Read the evidence →</a>'
        cards.append(f'<article class="step" id="{stop["id"]}"><div class="copy"><div class="number">STOP {index+1:02}</div><h2 tabindex="-1">{esc(stop["title"])}</h2><div class="route">{esc(stop["path"])}<br><code>{esc(stop["route"])}</code></div>{paragraphs}<p class="cue"><strong>Presenter cue.</strong> {esc(stop["cue"])}</p></div>{"".join(figures)}<nav class="stopnav" aria-label="Adjacent stops">{previous}{following}</nav></article>')
    source_links = "".join(f'<li><a href="../{esc(path)}">{esc(label)}</a></li>' for label, path in sources)
    md += ["## Evidence", "", native_limits, ""] + [f"- [{label}](../{path})" for label, path in sources]
    md += ["", "## What changed", "", md_changes, ""]
    navigation = "".join(f'<a href="#{stop["id"]}">{i+1:02} · {esc(stop["title"])}</a>' for i, stop in enumerate(stops))
    choices = "".join(f'<option value="{i}">{i+1:02} · {esc(stop["title"])}</option>' for i, stop in enumerate(stops))
    rendered = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="A screenshot tour of the KiroCrew owner console, security controls and client/server telemetry."><title>{TITLE}</title><style>{STYLE}</style></head><body><div class="shell">
<header><p class="eyebrow">KiroCrew · operator tour · {esc(edition_date)}</p><h1>Inspect the server’s controls.<br>Read the evidence behind them.</h1><p class="intro">{esc(INTRO)}</p><p class="status">{esc(status)} <a href="../{esc(status_link[1])}">{esc(status_link[0])}</a>.</p><p class="scope">{esc(scope)}</p></header>
<div class="toolbar" aria-label="Tour navigation"><button id="previous" type="button">← Previous</button><label for="stop-choice" class="sr-only" hidden>Choose a stop</label><select id="stop-choice" aria-label="Choose a stop">{choices}</select><span id="counter" class="counter" aria-live="polite"></span><button id="next" type="button">Next →</button></div>
<noscript><p class="nojs">Every stop is shown below. Use the stop links and Open original to inspect screenshots.</p></noscript>
<div class="layout"><nav class="toc" aria-label="Tour stops">{navigation}</nav><main>{"".join(cards)}
<section class="evidence" id="evidence"><h2>Read the supporting evidence</h2><p>{esc(evidence_intro)}</p><p>{esc(native_limits)}</p><ul>{source_links}</ul><p><a href="kirocrew-admin-tour.md">Markdown walkthrough</a> · <a href="../evidence/admin-console/native-20260913/tour-build.json">Build and image manifest</a></p></section>
<footer class="footer">Original screenshots · no generated product footage · use left/right arrows to move between stops · Escape closes image zoom.<p><strong>What changed.</strong> {esc(footer_changes)}</p></footer></main></div></div>
<dialog id="zoom-dialog" aria-label="Expanded console screenshot"><div class="dialogbar"><span id="zoom-title"></span><button id="actual-size" type="button" aria-pressed="false">Actual pixels</button><a id="zoom-original" href="#" target="_blank" rel="noopener">Open original</a><button id="close-zoom" type="button">Close · Esc</button></div><div class="zoomscroll" tabindex="0" role="region" aria-label="Screenshot pan area; use arrow keys at actual pixel size"><img id="zoom-image" alt=""></div></dialog>
<script>{SCRIPT}</script></body></html>'''
    outputs = [OUT / "kirocrew-admin-tour.html", OUT / "kirocrew-admin-tour.md"]
    embedded = [hashlib.sha256(base64.b64decode(value, validate=True)).hexdigest() for value in re.findall(r'src="data:image/(?:png|jpeg);base64,([^"]+)"', rendered)]
    ids = re.findall(r'\bid="([^"]+)"', rendered)
    anchors = re.findall(r'href="#([^"#]+)"', rendered)
    checks = {"unique_ids": len(ids) == len(set(ids)), "all_anchor_targets_exist": set(anchors) <= set(ids),
              "all_screenshot_bytes_preserved": embedded == [item["sha256"] for item in images],
              "all_stops_have_images": all(stop["shots"] for stop in stops),
              "no_external_assets": not re.search(r'(?:src|href)="https?://', rendered),
              "no_video_or_fake_enforcement_frames": "<video" not in rendered and "<canvas" not in rendered,
              "native_auth_source_confirmed": auth["authenticated"] is True}
    if not all(checks.values()):
        raise ValueError(f"Tour static validation failed: {checks}")
    browser_review_path = (checked_public_source(browser_review_file.absolute().relative_to(ROOT).as_posix())
                           if browser_review_file else EVIDENCE / "browser-review.json")
    browser_review = json.loads(browser_review_path.read_text())
    if not isinstance(browser_review, dict):
        raise ValueError("Browser review must be a JSON object")
    rendered_sha256 = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    browser_matches = browser_review.get("status") == "passed" and browser_review.get("sha256") == rendered_sha256
    output_texts = (rendered, "\n".join(md))
    receipt = {"schema": 1, "kind": "native_admin_tour_build", "built_at_utc": datetime.now(timezone.utc).isoformat(),
               "status": "static_and_browser_passed" if browser_matches else "static_passed_browser_review_pending", "builder_sha256": sha(Path(__file__)),
               "stop_count": len(stops), "screenshot_count": len(images), "static_checks": checks,
               "screenshots": [{key: value for key, value in item.items() if key != "uri"} for item in images],
               "sources": [{"label": label, "path": path, "sha256": sha(ROOT / path)} for label, path in sources],
               "outputs": [{"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                            "bytes": len(text.encode("utf-8"))} for path, text in zip(outputs, output_texts)],
               "native_proof_links": [path for label, path in sources if "20260913-ui2" in path or label.startswith("Native run receipt")],
               "native_claim_scope": {"bounded_four_outcomes_reconciled": native["bounded_four_outcomes_reconciled"],
                                      "full_native_acceptance": native["full_native_acceptance"],
                                      "original_collection_complete": native["original_collection_complete"],
                                      "authority_verdict": authority["verdict"]},
               "browser_review": {"current_candidate": "passed" if browser_matches else "copy_delta_review_pending",
                                  "reviewed_candidate_sha256": browser_review.get("sha256"),
                                  "review_path": browser_review_path.relative_to(ROOT).as_posix(),
                                  "review_sha256": sha(browser_review_path),
                                  "recorded_status": browser_review.get("status"),
                                  "scope": "Browser approval applies only when its recorded HTML hash matches this build. Prior navigation, zoom, keyboard and sticky layout approval remains bound to the earlier candidate."},
               "limits": ["Screenshots preserve capture-time values; they do not poll the live portal.",
                          "The four native outcomes have bounded supporting receipts; broader native acceptance is not inferred from the screenshot tour.",
                          "Browser layout, stop navigation and zoom require a separate observed browser receipt.",
                          "Earlier host, backend and telemetry images retain their earlier-baseline scope."],
               "editorial_review": "No AI Slop self-review applied to captions, explanations and status claims."}
    if capture_metadata:
        receipt["capture_groups"] = [capture_metadata]
    if managed_metadata:
        receipt["managed_edition"] = managed_metadata
        receipt["native_claim_scope"]["earlier_run_scope"] = "The four original outcomes predate managed policy."
        receipt["native_claim_scope"]["managed"] = managed_metadata["native_claim_scope"]
    if host_metadata:
        receipt["completed_host_results"] = host_metadata
        receipt["native_claim_scope"]["completed_host_results"] = host_metadata["verified_outcomes"]
    receipt_text = json.dumps(receipt, indent=2) + "\n"
    if validate_only:
        print(json.dumps({"status": "validated_without_writes", "stops": len(stops), "screenshots": len(images),
                          "html_sha256": rendered_sha256, "browser_review_matches": browser_matches,
                          "capture_group": capture_metadata, "static_checks": checks}))
        return
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for path, text in zip(outputs, output_texts):
        path.write_text(text, encoding="utf-8")
    (EVIDENCE / "tour-build.json").write_text(receipt_text)
    print(json.dumps({"status": receipt["status"], "stops": len(stops), "screenshots": len(images), "outputs": [str(path) for path in outputs]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-proof", type=Path, action="append", default=[], help="Optional existing sanitized native receipt to link; its presence never changes the tour verdict.")
    parser.add_argument("--capture-group", type=Path, help="Optional hash-bound JSON group of inspected screenshots to append to existing stops. See load_capture_group for its schema.")
    parser.add_argument("--validate-only", action="store_true", help="Validate inputs and report the proposed HTML hash without changing outputs or receipts.")
    parser.add_argument("--browser-review", type=Path, help="Existing scoped browser receipt to bind; approval applies only if its exact HTML hash matches.")
    parser.add_argument("--managed-summary", type=Path, help="Reviewed managed-policy summary with exact screenshot roles and receipt hashes; applied after the earlier capture group.")
    parser.add_argument("--host-results", type=Path, help="Reviewed completed-host result images, clips and sanitized receipt bindings; adds a native-results stop.")
    args = parser.parse_args()
    build(args.native_proof, args.capture_group, args.validate_only, args.browser_review, args.managed_summary, args.host_results)
