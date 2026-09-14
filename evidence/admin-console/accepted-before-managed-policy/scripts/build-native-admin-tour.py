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
INTRO = "Inspect the server’s controls, understand their authority and read the client and server measurements. These are original captures of the owner console connected to the ARM EC2 Gateway. The Mac runs the client with its local Gateway off."
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
    if (len(parts) < 3 or parts[:2] not in [["evidence", "native-client-demo"], ["evidence", "admin-console"]]
            or any(part.startswith(".") or part == "raw" for part in parts)
            or any(token in parts[-1] for token in (".local.", "preflight"))):
        raise ValueError("Added sources must be reviewed JSON receipts in the native-client-demo or admin-console evidence folders")
    path = checked_relative_file(value)
    if path.suffix != ".json":
        raise ValueError("Added evidence links must name reviewed JSON receipts")
    if "native-client-demo" in path.parts and path.name in {"baseline.json", "receipt.json"}:
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


def image_info(item):
    path = OUT / item["file"]
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing regular screenshot: {path}")
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


def build(proof_paths, capture_group=None, validate_only=False, browser_review_file=None):
    stops = copy.deepcopy(STOPS)
    sources = list(SOURCES)
    capture_metadata = None
    status = STATUS
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
    md = [f"# {TITLE}", "", "September 13, 2026 · macOS client / ARM EC2 server · owner console", "", INTRO, "", status, "",
          "Fresh security captures and earlier baseline screenshots are dated separately below. All image bytes are preserved. This tour is a guide to the console; native enforcement requires a separate recording and receipt.", ""]
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
<header><p class="eyebrow">KiroCrew · operator tour · September 13, 2026</p><h1>Inspect the server’s controls.<br>Read the evidence behind them.</h1><p class="intro">{esc(INTRO)}</p><p class="status">{esc(status)} <a href="../evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json">Read the four-outcome reconciliation</a>.</p><p class="scope">Fresh security captures and earlier baseline images are dated separately. All screenshots are embedded unchanged. Native client enforcement requires a separate recording and receipt.</p></header>
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
    if validate_only:
        print(json.dumps({"status": "validated_without_writes", "stops": len(stops), "screenshots": len(images),
                          "html_sha256": rendered_sha256, "browser_review_matches": browser_matches,
                          "capture_group": capture_metadata, "static_checks": checks}))
        return
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    for path, text in zip(outputs, (rendered, "\n".join(md))):
        path.write_text(text, encoding="utf-8")
    receipt = {"schema": 1, "kind": "native_admin_tour_build", "built_at_utc": datetime.now(timezone.utc).isoformat(),
               "status": "static_and_browser_passed" if browser_matches else "static_passed_browser_review_pending", "builder_sha256": sha(Path(__file__)),
               "stop_count": len(stops), "screenshot_count": len(images), "static_checks": checks,
               "screenshots": [{key: value for key, value in item.items() if key != "uri"} for item in images],
               "sources": [{"label": label, "path": path, "sha256": sha(ROOT / path)} for label, path in sources],
               "outputs": [{"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path), "bytes": path.stat().st_size} for path in outputs],
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
    (EVIDENCE / "tour-build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "stops": len(stops), "screenshots": len(images), "outputs": [str(path) for path in outputs]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-proof", type=Path, action="append", default=[], help="Optional existing sanitized native receipt to link; its presence never changes the tour verdict.")
    parser.add_argument("--capture-group", type=Path, help="Optional hash-bound JSON group of inspected screenshots to append to existing stops. See load_capture_group for its schema.")
    parser.add_argument("--validate-only", action="store_true", help="Validate inputs and report the proposed HTML hash without changing outputs or receipts.")
    parser.add_argument("--browser-review", type=Path, help="Existing scoped browser receipt to bind; approval applies only if its exact HTML hash matches.")
    args = parser.parse_args()
    build(args.native_proof, args.capture_group, args.validate_only, args.browser_review)
