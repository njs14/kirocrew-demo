#!/usr/bin/env python3
"""Build the portable admin tour from unmodified, observed console screenshots."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
EVIDENCE = ROOT / "evidence/admin-console"
TITLE = "KiroCrew admin console walkthrough"
INTRO = (
    "The Mac is the client. The Gateway, Kiro CLI and demo workspace run on the ARM EC2 host. "
    "This tour follows the owner dashboard through host health, security settings, backend status and telemetry. "
    "The screenshots preserve the deployed September 13 demo, including the values and timestamps visible at capture."
)
STATUS = (
    "ARM EC2 and the remote dashboard are running. The direct MCP and AWS checks passed. "
    "Kiro CLI is selected for new sessions, but its native sign-in is still pending. "
    "A completed native tool call, approval and enforcement trace remain separate acceptance checks."
)
ENVIRONMENT = [
    ("Client", "macOS · September 13 Nightly · local Gateway off"),
    ("Connection", "Local port 5599 → pinned SSH tunnel → EC2 Gateway on loopback 5476"),
    ("Server", "t4g.xlarge · ARM64 · 4 vCPU · 16 GiB RAM · 40 GiB encrypted gp3"),
    ("Server build", "Custom Linux ARM repack of 0.7.0-nightly.20260912t060850"),
    ("Backend", "Kiro CLI 2.21.4 · selected · independent sign-in pending"),
    ("Inbound access", "TCP 22 from 24.60.107.229/32 only · us-east-1"),
]
SECTIONS = [
    {
        "id": "overview", "group": "Orient", "title": "Start with the connected Gateway",
        "path": "Settings → Overview", "route": "/settings/overview", "file": "01-overview.jpg",
        "alt": "KiroCrew Settings Overview shows All systems running, the September 12 server Nightly and zero sessions and messages.",
        "observed": "Overview reports “All systems running” and server version 0.7.0-nightly.20260912t060850. At capture, uptime was 5m 35s and the session and message counters were zero.",
        "meaning": "This is the remote Gateway’s health and activity summary. A green Gateway status does not establish that the selected coding backend can start a session.",
        "cue": "Point out the server build, then explain that the Mac can run a newer desktop build while displaying the EC2 dashboard.",
    },
    {
        "id": "performance", "group": "Orient", "title": "Verify which machine is doing the work",
        "path": "Developer → System → Performance", "route": "/developer?tab=system&plane=performance", "file": "02-arm-performance.jpg",
        "alt": "System Performance identifies aarch64, four logical processors, Linux and the EC2 workspace path.",
        "observed": "The CPU panel identifies aarch64 and four logical processors. The footer shows Linux, host ip-172-31-8-10 and working directory /srv/kirocrew-demo/workspace.",
        "meaning": "CPU, memory, disk and network values describe the remote ARM server. The CloudFormation receipt supplies the instance type, 16 GiB allocation and 40 GiB volume.",
        "cue": "Open Memory if the audience wants capacity detail. Keep the architecture’s endpoint-control enclosure around the Gateway, backend and workspace on EC2.",
    },
    {
        "id": "services", "group": "Orient", "title": "Read service counts in their process scope",
        "path": "Developer → System → Services", "route": "/developer?tab=system&plane=services", "file": "03-gateway-services.jpg",
        "alt": "System Services shows the remote Gateway process, 197 MB RSS, stopped embeddings and zero MCP processes in its process inventory.",
        "observed": "The captured Gateway process is PID 4991, with 197 MB RSS. Embeddings are stopped. The panel reports zero MCP processes in its inventory.",
        "meaning": "The demo MCP runs as a separate systemd service and Unix user. This Gateway process inventory does not count that service. Use the custom observability page’s MCP checks and the direct MCP receipt to inspect it.",
        "cue": "Explain the zero before showing the separate MCP service later. The stopped embeddings service is intentional in this demo.",
    },
    {
        "id": "posture", "group": "Security", "title": "Inspect the configured security controls",
        "path": "Settings → Security → Live Security Posture", "route": "/settings/security/posture", "file": "04-security-posture.jpg",
        "alt": "Live Security Posture shows Standard process sandbox, Interactive approval, 143 sensitive paths, 23 protected paths and 112 built-in denied-command rules.",
        "observed": "The page lists a Standard process sandbox and Interactive tool approval. The visible registry counts are 143 sensitive credential paths, 23 protected configuration paths and 112 built-in denied-command rules.",
        "meaning": "This view reports configured controls. Counts and status labels do not prove that a native backend delivered a pre-execution hook, that a sandbox ran or that a particular action was blocked.",
        "cue": "Expand a control when explaining its coverage. Tie each enforcement result to its execution receipt.",
    },
    {
        "id": "approval", "group": "Security", "title": "Keep the demo in Interactive mode",
        "path": "Settings → Security → YOLO (auto-approve)", "route": "/settings/security/approval", "file": "05-interactive-approval.jpg",
        "alt": "YOLO settings show Interactive in the sidebar and a six-hour duration selected for the next activation of auto-approve.",
        "observed": "The sidebar says Interactive. The six-hour selection sets how long auto-approve would last the next time it is turned on.",
        "meaning": "Auto-approve remains off, so a future authenticated Kiro CLI run can demonstrate the native approval step.",
        "cue": "Read the current mode in the sidebar and the sentence below the duration choices. Do not activate auto-approve during the tour.",
    },
    {
        "id": "governance", "group": "Security", "title": "Check whether an enterprise policy is present",
        "path": "Settings → Security → Governance Policy", "route": "/settings/security/governance", "file": "06-governance.jpg",
        "alt": "Governance Policy states No enterprise policy in effect and describes the standalone host mode.",
        "observed": "The effective security ceiling panel says “No enterprise policy in effect.” This host is in standalone mode.",
        "meaning": "The built-in safeguards and demo deny rule remain configured. The demo configuration is writable by crew; an immutable managed policy floor has not been deployed.",
        "cue": "Use this screen to distinguish the deployed demo from the architecture’s proposed central policy distribution.",
    },
    {
        "id": "backend", "group": "Backend", "title": "Confirm Kiro CLI, then verify its own sign-in",
        "path": "Developer → Agent Backend", "route": "/developer?tab=agent-backend", "file": "07-agent-backend.jpg",
        "alt": "Agent Backend has Kiro CLI selected while a separate Kiro sign-in card says Signed in with GitHub.",
        "observed": "Kiro CLI is selected, matching the original walkthrough and the user’s explicit choice. The page also shows a “Signed in with GitHub” card.",
        "meaning": "That card reads the KAS sign-in state. The standalone Kiro CLI has a separate login state and still reports signed out. Selecting the CLI changes the backend for new sessions; an existing session retains its original backend.",
        "cue": "Check the CLI’s own login state before starting a new native session. Screen 10 shows the observed authentication failure.",
    },
    {
        "id": "privacy", "group": "Telemetry", "title": "Inspect Gateway metric recording and export settings",
        "path": "Settings → Privacy → Telemetry controls", "route": "/settings/privacy", "file": "08-telemetry-controls.jpg",
        "alt": "Privacy has Record metrics enabled and the anonymous usage heartbeat disabled by the Gateway environment.",
        "observed": "Record metrics is on. The anonymous usage heartbeat is off because KIROCREW_TELEMETRY_DISABLED is set in the Gateway environment.",
        "meaning": "Native server metrics flush every 10 seconds with seven days of retention and a 64 MiB retention target. No OTLP destination is configured. The separate client collector sends bounded process and connection measurements to this EC2 host through the pinned SSH connection.",
        "cue": "Show the recording switch, then name the destination and retention. The remote Settings page controls this Gateway; it does not configure a local Mac Gateway.",
    },
    {
        "id": "native-telemetry", "group": "Telemetry", "title": "Read native Gateway instrumentation",
        "path": "Developer → Telemetry", "route": "/developer?tab=telemetry", "file": "09-native-telemetry.jpg",
        "alt": "Native Telemetry shows Gateway request and boot duration samples, process counters and zero completed turn samples.",
        "observed": "The Instruments table contains real Gateway request duration and boot duration measurements, plus process counters. At capture it showed 1,983 request samples and one boot sample. Completed turn throughput was zero.",
        "meaning": "Native instrumentation is recording Gateway activity. The “Last 14d” query window does not override the configured seven-day retention. Zero turn latency and zero faults are empty-turn statistics here, so they do not establish a successful backend session.",
        "cue": "Point at the request sample count. Next, inspect the native failure log before opening the combined client and server page.",
    },
    {
        "id": "backend-logs", "group": "Backend", "title": "Use the native log to explain the remaining failure",
        "path": "Developer → Logs · search AcpRuntime dead", "route": "/developer?tab=logs", "file": "10-native-auth-log.jpg",
        "alt": "Native Logs filtered to AcpRuntime dead show Kiro CLI exit code one and the message You are not logged in.",
        "observed": "The filtered Gateway log records repeated CLI exits with code 1, including two attempts at 14:34 UTC on September 13. The reason is explicit: “You are not logged in, please log in with kiro-cli login.”",
        "meaning": "This is an observed backend authentication failure. It explains why a connected Gateway, a selected CLI and the GitHub sign-in card have not produced a completed native run.",
        "cue": "Keep the filter on this known diagnostic. Resume the original Kiro CLI sign-in flow, then rerun the native walkthrough and capture new evidence before claiming native enforcement.",
    },
    {
        "id": "combined", "group": "Telemetry", "title": "Show client and server telemetry together",
        "path": "Apps → Demo Observability", "route": "/apps/demo-observability", "file": "11-client-server-telemetry.jpg",
        "alt": "The custom Demo Observability page shows current Mac client and EC2 server metrics, connection and service checks, and collection events.",
        "observed": "Both cards are marked Current. The captured Mac sample shows 4% process CPU and 772.4 MiB process memory; EC2 shows 6.2% host CPU and 14.6 GiB available RAM. “Local Gateway off” and all four server service and loopback checks read Yes.",
        "meaning": "The client collector measures KiroCrew desktop processes, the local SSH tunnel listener and the absence of a local Gateway listener. The server collector measures host resources, the Gateway and the separate MCP service. CPU sampling methods differ between the two sources.",
        "cue": "Read “Local Gateway off,” then the server Gateway and MCP checks. A reachable tunnel listener proves a local TCP listener; the connected owner dashboard supplies separate application-level evidence.",
    },
    {
        "id": "client-pause", "group": "Telemetry", "title": "Observe the server while the desktop is closed",
        "path": "Apps → Demo Observability · controlled desktop pause", "route": "/apps/demo-observability", "file": "13-client-stopped.jpg",
        "alt": "During a controlled desktop pause, the client card shows zero process CPU and memory and desktop running No, while the tunnel and all server checks remain Yes.",
        "observed": "During a controlled quit of the Mac desktop app, its process CPU and memory dropped to zero and “KiroCrew desktop running” changed to No. The SSH tunnel listener and all four server checks stayed Yes. The browser dashboard remained available.",
        "meaning": "The EC2 Gateway and MCP continued while the desktop was closed. The client sample still says Current because it is fresh; read the individual checks for health. The Mac app was relaunched after this capture and reconnected to the remote Gateway.",
        "cue": "Use this captured pause to explain client and server independence. If repeating it live, keep the browser dashboard and SSH tunnel open, quit only the desktop app, then relaunch it and check recovery.",
    },
    {
        "id": "collection-logs", "group": "Telemetry", "title": "Inspect the collection logs and their limits",
        "path": "Apps → Demo Observability → Collection logs", "route": "/apps/demo-observability", "file": "12-collection-logs.jpg",
        "alt": "Demo Observability collection logs show source labels, collection events and timestamps with All, Client and Server filters.",
        "observed": "Four events are visible: the two first samples, the client’s health change at 10:44:42 EDT (14:44:42 UTC), and its recovery at 10:49:34 EDT (14:49:34 UTC). The health change is a warning; recovery is info. All, Client and Server buttons filter the same event stream.",
        "meaning": "Both collectors sample every 60 seconds. The page refreshes every 15 seconds and marks a sample stale after three minutes. It retains 240 samples per source and 200 collection events. Events use fixed labels and exclude arbitrary logs, prompts and credentials.",
        "cue": "Filter Client, then Server. Routine unchanged samples do not add log rows. These collection events support operational diagnosis; native security-event and tool-enforcement receipts remain separate.",
    },
]

FLOW = [
    ("Locate the endpoint", "Show Overview and System Performance. Point out the remote ARM host and workspace, with the local Gateway off."),
    ("Explain the controls", "Open Live Security Posture, Interactive approval and Governance Policy. State which controls are configured and that no enterprise policy is loaded."),
    ("Check the chosen backend", "Show Kiro CLI selected and the filtered authentication failure. Keep the native run pending until the CLI itself is authenticated."),
    ("Show two telemetry sources", "Open native Telemetry for Gateway measurements, then Demo Observability for the Mac and EC2 collectors."),
    ("Read the evidence", "Show the captured desktop pause and recovery. Filter collection logs by source and check sample freshness. Use the passing direct MCP/AWS receipt for those enforcement results."),
    ("Continue after sign-in", "Start a new Kiro CLI session, run the approved native walkthrough and record the tool call, approval, denial and correlated events before updating the claims."),
]

FINDINGS = [
    ("Backend sign-in can be misread", "The Kiro sign-in card reports GitHub authentication while standalone Kiro CLI exits as signed out. The card reads KAS state. Label those identities separately in a future product fix; for this demo, show the CLI’s own result and retain the native-authentication gate.", "07-agent-backend.jpg; 10-native-auth-log.jpg; .build/kirocrew-source/website/src/pages/settings/KiroSignInCard.tsx:158; .build/installed-nightly/kiro_crew/auth/service.py:245"),
    ("Gateway health is broader than backend readiness", "Overview says all systems are running while the CLI cannot start. Use Overview to establish dashboard and Gateway health; use a completed native session to establish backend readiness.", "01-overview.jpg; 10-native-auth-log.jpg"),
    ("The MCP count has a narrower process scope", "System Services reports zero MCP processes, but the demo MCP runs under a separate Unix user and systemd unit. The custom collector displays that unit’s health. The passing direct MCP/AWS receipt establishes the tested tool behavior.", "03-gateway-services.jpg; 11-client-server-telemetry.jpg; evidence/aws/arm-20260913/mcp-live-receipt.json"),
    ("Security status reports configuration", "The posture page lists Standard sandbox, Interactive approval and control counts. No enterprise policy is in effect. Keep those labels separate from claims about executed sandboxing, pre-execution callbacks and immutable policy governance.", "04-security-posture.jpg; 05-interactive-approval.jpg; 06-governance.jpg"),
    ("The auto-approve duration needs its context", "Six hours is selected as the duration for the next activation, while the current mode is Interactive. Explain both labels together so the duration is not read as an active bypass.", "05-interactive-approval.jpg"),
    ("Native telemetry needs sample-count context", "Gateway duration measurements are present, but completed-turn samples are zero. A zero fault rate over zero turns is not a passed backend test. The displayed 14-day query window does not extend the configured seven-day retention. The 64 MiB storage setting is a retention target; pruning protects active writers, so stored data can temporarily exceed it.", "08-telemetry-controls.jpg; 09-native-telemetry.jpg; infrastructure/RUNBOOK.md:97; .build/installed-nightly/kiro_crew/metrics/local_exporter.py:398"),
    ("Client and server collection is visible in a custom app", "The native Telemetry panel continues to show Gateway instrumentation. The installed Demo Observability App Kit page adds the two collectors and collection-event filters inside the owner dashboard. It is a demo extension with local bounded storage.", "11-client-server-telemetry.jpg; 12-collection-logs.jpg"),
    ("Freshness and measurement definitions affect interpretation", "Samples older than three minutes become stale. Mac CPU sums process scheduler averages and can exceed 100%; server host CPU uses a one-second normalized sample. The local tunnel probe checks listener reachability. None of these health probes establishes an authorized model response.", "infrastructure/observability-collector/README.md; infrastructure/observability/APP-INSTALL.md"),
    ("Current means a fresh sample", "The controlled desktop pause produced a fresh sample with desktop running No and zero desktop process CPU and memory. Its Current badge remained visible while the server checks stayed Yes. Read the individual check results alongside the freshness badge. The recorded recovery followed the Mac app’s relaunch.", "13-client-stopped.jpg; 12-collection-logs.jpg"),
]

def escape(value: str) -> str:
    return html.escape(value, quote=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def screenshot_info(section: dict, draft: bool) -> dict | None:
    path = OUT / "admin-console" / section["file"]
    if not path.exists():
        if draft:
            return None
        raise SystemExit(f"Missing observed screenshot: {path}")
    data = path.read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = struct.unpack(">II", data[16:24])
        mime = "image/png"
    elif data[:2] == b"\xff\xd8":
        # CUA's saved byte stream can be JPEG even when the capture filename
        # ends in .png. Detect it; never transcode an evidence image.
        position = 2
        width = height = None
        while position < len(data):
            if data[position] != 0xFF:
                raise SystemExit(f"Malformed original JPEG: {path}")
            while data[position] == 0xFF:
                position += 1
            marker = data[position]
            position += 1
            if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                continue
            length = int.from_bytes(data[position:position + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                height, width = struct.unpack(">HH", data[position + 3:position + 7])
                break
            position += length
        if not width or not height:
            raise SystemExit(f"Missing original JPEG dimensions: {path}")
        mime = "image/jpeg"
    else:
        raise SystemExit(f"Expected original PNG or JPEG: {path}")
    return {"path": str(path), "sha256": sha(path), "width": width, "height": height, "mime_type": mime,
            "uri": "data:" + mime + ";base64," + base64.b64encode(data).decode()}


def markdown(draft: bool) -> str:
    lines = [f"# {TITLE}", "", "Observed September 13, 2026 · Owner dashboard · ARM EC2 demo", "", INTRO, "", STATUS, "",
             "## Deployment at capture", "", "| Component | Observed configuration |", "| --- | --- |"]
    lines += [f"| {key} | {value} |" for key, value in ENVIRONMENT]
    lines += ["", "The original x86 host is stopped and retained for rollback. The current owner dashboard is reached through the existing SSH tunnel at `http://localhost:5599`; it has no public Gateway or MCP ingress.", "",
              "## Walkthrough", ""]
    for index, section in enumerate(SECTIONS, 1):
        lines += [f"### {index:02}. {section['title']}", "", f"Open **{section['path']}**.", "", section["observed"], "", section["meaning"], "", f"Presenter cue: {section['cue']}", ""]
        info = screenshot_info(section, draft)
        lines += [f"![{section['alt']}]({info['path']})" if info else "Screenshot capture pending; this draft is not a completed browser-validation receipt.", ""]
    lines += ["## Live demo order", ""]
    lines += [f"{i}. **{label}.** {detail}" for i, (label, detail) in enumerate(FLOW, 1)]
    lines += ["", "## Operational notes", "",
              f"Native server metrics use a 10-second export interval, seven-day retention and a 64 MiB retention target. Pruning protects active writers, so storage can temporarily exceed the target; see the [telemetry runbook]({ROOT / 'infrastructure/RUNBOOK.md:97'}). Anonymous product reporting is off and no OTLP endpoint is configured. The custom client and server collectors run every minute; the owner app reads their samples without a write endpoint. Collector history is local to this EC2 host, with about four hours per source at continuous collection and up to 200 status events.", "",
              "The screenshots are original browser captures. They were not redrawn, retouched or populated with demonstration fixtures. Captured counts, process IDs and sample ages will change as the system runs.", "",
              "## Evidence and next action", "",
              f"Read the [findings]({OUT / 'kirocrew-admin-findings.md'}), [ARM cloud verification]({ROOT / 'evidence/aws/arm-20260913/final-cloud-verification.json'}), [direct MCP/AWS receipt]({ROOT / 'evidence/aws/arm-20260913/mcp-live-receipt.json'}), [telemetry API readback]({ROOT / 'evidence/aws/arm-20260913/observability-api-readback.json'}) and [telemetry runtime verification]({ROOT / 'evidence/aws/arm-20260913/observability-runtime-receipt.json'}). The [custom app contract]({ROOT / 'infrastructure/observability/APP-INSTALL.md'}) and [collector contract]({ROOT / 'infrastructure/observability-collector/README.md'}) define the displayed measurements and retention.", "",
              f"Follow the [fresh EC2 sign-in procedure]({ROOT / 'scripts/EC2-LOGIN.md'}), then use the [native evidence runner]({ROOT / 'scripts/native-backend-demo.README.md'}) to start a new Kiro CLI session and rerun the enforcement walkthrough. Keep these screenshots as the pre-authentication baseline; save a successful native run and its correlated events as new evidence.", "",
              "## What changed", "",
              "The editing pass clarified which host the metric settings control, corrected the screen order and linked the sign-in and native-run procedures. It shortened repeated cautions, corrected the 64 MiB setting to a retention target and preserved the measured values and pending CLI sign-in.", ""]
    return "\n".join(lines)


def findings_markdown() -> str:
    lines = ["# KiroCrew admin console findings", "", "Observed September 13, 2026 · ARM EC2 demo", "",
             "The owner dashboard shows the remote host and its control settings. The GitHub sign-in card can look ready while the selected standalone Kiro CLI is signed out. The screenshots preserve that observed failure.", ""]
    for i, (title, body, sources) in enumerate(FINDINGS, 1):
        links = []
        for source in sources.split("; "):
            path = OUT / "admin-console" / source if re.match(r"\d\d-.*\.jpg$", source) else ROOT / source
            links.append(f"[{source}]({path})")
        lines += [f"## {i}. {title}", "", body, "", "Evidence: " + ", ".join(links) + ".", ""]
    lines += ["## Demo changes", "",
              "The demo now uses the ARM host as its single execution endpoint and keeps the Mac Gateway off. The admin walkthrough adds native Gateway telemetry, a custom page for both client and server health, and source-filtered collection logs. The presentation must name the custom page as an App Kit extension and keep the CLI authentication failure visible until a new successful native run supersedes it.", "",
              "## What remains to be demonstrated", "",
              "The direct MCP probe verified authentication, catalog, an allowed S3 read, grant denial before AWS dispatch and an IAM-denied read. Complete the separate native Kiro CLI login, approval, hook, sandbox and security-event correlation checks before presenting those as end-to-end Crew enforcement.", "",
              "## What changed", "",
              "The editing pass shortened the opening, added direct evidence links, clarified the storage retention target and kept configuration, health measurements and executed enforcement distinct.", ""]
    return "\n".join(lines)


STYLE = """
:root{color-scheme:light;--bg:#f5f4f1;--paper:#fff;--ink:#202630;--muted:#5e6470;--line:#dce0e4;--accent:#6553a0;--soft:#eeebf6;--warn:#8b521c;--warn-bg:#fff5e7}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:32px}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--accent);text-underline-offset:3px}button{font:inherit}button,a{touch-action:manipulation}:focus-visible{outline:3px solid #8d73d1;outline-offset:4px}.shell{max-width:1440px;margin:auto;padding:48px 44px 80px}.eyebrow{margin:0 0 18px;color:var(--accent);font-size:12px;font-weight:700;letter-spacing:.13em;text-transform:uppercase}.hero{max-width:1050px;margin-bottom:36px}.hero h1{font-size:clamp(35px,5vw,61px);line-height:1.08;letter-spacing:-.045em;margin:0 0 24px;font-weight:660;max-width:850px}.lede{font-size:20px;line-height:1.6;max-width:960px;margin:0}.snapshot{display:flex;gap:16px;align-items:flex-start;background:var(--warn-bg);border:1px solid #ecd7b9;border-radius:10px;padding:18px 22px;margin:28px 0 0;font-size:14px;line-height:1.65}.snapshot b{color:var(--warn);white-space:nowrap;font-weight:650}.layout{display:grid;grid-template-columns:215px minmax(0,1fr);gap:36px}.toc{position:sticky;top:25px;max-height:calc(100vh - 50px);overflow:auto;align-self:start;padding:12px 12px 16px 0;font-size:13px}.toc-title{font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);font-weight:700;margin:0 0 12px}.toc a{display:block;color:var(--muted);text-decoration:none;padding:8px 12px;border-left:2px solid var(--line);line-height:1.4}.toc a:hover,.toc a[aria-current=true]{border-color:var(--accent);color:var(--accent);background:var(--soft)}.toc .chapter{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin:20px 0 7px 14px}.main{min-width:0}.environment{border:1px solid var(--line);border-radius:12px;background:var(--paper);padding:24px 26px;margin-bottom:34px}.environment h2{font-size:20px;margin:0 0 14px}.environment table{border-collapse:collapse;width:100%;font-size:13px}.environment td{padding:9px 0;vertical-align:top;border-top:1px solid #eceef0}.environment td:first-child{width:160px;padding-right:20px;color:var(--muted)}.environment p{font-size:12px;color:var(--muted);margin:16px 0 0}.step{margin:0 0 36px;scroll-margin-top:28px;background:var(--paper);border:1px solid var(--line);border-radius:13px;overflow:hidden}.step-copy{padding:28px 30px 24px}.step-head{display:flex;gap:15px;align-items:flex-start}.number{display:flex;align-items:center;justify-content:center;flex:none;height:34px;width:34px;border-radius:8px;background:var(--soft);color:var(--accent);font-weight:650;font-size:14px;margin-top:2px}.step h2{font-size:25px;line-height:1.3;font-weight:650;letter-spacing:-.02em;margin:0 0 7px}.route{font-size:12px;color:var(--muted);margin:0}.step-copy>p{font-size:15px;margin:20px 0 0}.cue{border-left:3px solid #bbb0d3;padding:1px 0 1px 14px;color:var(--muted);font-size:13px!important}.cue strong{font-weight:650;color:var(--ink)}figure{margin:0;border-top:1px solid var(--line);background:#080909}.image-button{display:block;width:100%;padding:0;border:0;background:transparent;cursor:zoom-in}.image-button img{display:block;width:100%;height:auto}figcaption{display:flex;justify-content:space-between;gap:15px;background:#f8f8fa;color:var(--muted);font-size:11px;padding:11px 18px;line-height:1.5}.pending{padding:70px 24px;text-align:center;color:#ddd;font-size:14px}.flow{padding:30px;background:var(--soft);border-radius:12px;margin:12px 0 30px}.flow h2,.notes h2{margin:0 0 17px;font-size:24px;letter-spacing:-.02em}.flow ol{margin:0;padding-left:24px}.flow li{padding:0 0 13px 7px;font-size:14px}.flow li:last-child{padding-bottom:0}.notes{padding:6px 6px 0;font-size:14px}.notes p{margin:0 0 17px}.notes .small{font-size:12px;color:var(--muted)}.footer{border-top:1px solid var(--line);padding-top:20px;margin-top:25px;color:var(--muted);font-size:11px}dialog{padding:0;border:1px solid #4a4d55;border-radius:8px;background:#080909;max-width:96vw;max-height:94vh;width:1400px;color:#fff;overflow:auto}dialog::backdrop{background:rgba(14,16,22,.85)}dialog img{display:block;width:100%;height:auto}.dialogbar{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:13px 18px;font-size:13px;position:sticky;top:0;background:#171920}dialog button{background:#30333d;border:1px solid #555b6a;color:#fff;padding:5px 13px;border-radius:5px;cursor:pointer}.download{display:inline-block;margin-top:12px;font-size:12px}.mobile-nav{display:none}@media(max-width:960px){.shell{padding:30px 22px 55px}.layout{grid-template-columns:1fr}.toc{display:none}.mobile-nav{display:block;margin:0 0 22px;padding:13px 18px;border:1px solid var(--line);border-radius:8px;background:var(--paper);font-size:13px}.mobile-nav summary{cursor:pointer;font-weight:650}.mobile-nav a{display:block;padding:6px 0;text-decoration:none}.snapshot{display:block}.snapshot b{display:block;margin-bottom:5px}.hero{margin-bottom:25px}.lede{font-size:18px}.step-copy{padding:24px}.environment{padding:21px}.step h2{font-size:23px}}@media(max-width:540px){.shell{padding:25px 13px 40px}.step-copy{padding:20px 17px}.step h2{font-size:21px}.step-head{gap:11px}.number{width:29px;height:29px;font-size:12px}.environment td:first-child{width:95px;padding-right:10px}.environment table{font-size:12px}figcaption{display:block}.flow{padding:23px}.hero h1{font-size:37px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}@media print{body{background:#fff;font-size:11px}.shell{padding:0}.hero h1{font-size:34px}.lede{font-size:14px}.layout{display:block}.toc,.mobile-nav,.download{display:none}.step{break-inside:avoid;page-break-inside:avoid;margin-bottom:20px}.step-copy{padding:18px}.step h2{font-size:20px}.step-copy>p{font-size:12px}.snapshot{font-size:11px}.flow,.environment{break-inside:avoid}a{color:inherit;text-decoration:none}figcaption span:last-child{display:none}}
"""

def document(draft: bool) -> str:
    navigation = "".join(f'<a href="#{s["id"]}">{i:02} · {escape(s["title"])}</a>' for i, s in enumerate(SECTIONS, 1))
    cards = []
    for index, s in enumerate(SECTIONS, 1):
        info = screenshot_info(s, draft)
        shot = (f'<button class="image-button" type="button" aria-label="Expand screenshot {index}: {escape(s["title"])}"><img loading="lazy" width="{info["width"]}" height="{info["height"]}" src="{info["uri"]}" alt="{escape(s["alt"])}"></button>' if info else '<div class="pending">Screenshot capture pending · Draft</div>')
        cards.append(f'''<section class="step" id="{s['id']}"><div class="step-copy"><div class="step-head"><span class="number">{index:02}</span><div><h2>{escape(s['title'])}</h2><p class="route">{escape(s['path'])}</p></div></div><p>{escape(s['observed'])}</p><p>{escape(s['meaning'])}</p><p class="cue"><strong>Presenter cue.</strong> {escape(s['cue'])}</p></div><figure>{shot}<figcaption><span>Original console capture · September 13, 2026 · {escape(s['file'])}</span><span>Click the screenshot to expand</span></figcaption></figure></section>''')
    environment = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>" for k, v in ENVIRONMENT)
    flow = "".join(f"<li><strong>{escape(label)}.</strong> {escape(detail)}</li>" for label, detail in FLOW)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="An evidence-bound screenshot walkthrough of the KiroCrew owner dashboard on ARM EC2, with client and server telemetry."><title>{TITLE}</title><style>{STYLE}</style></head><body>
<div class="shell"><header class="hero"><p class="eyebrow">KiroCrew · Operator walkthrough · September 13, 2026</p><h1>Know which host, control and measurement you are looking at.</h1><p class="lede">{escape(INTRO)}</p><div class="snapshot"><b>{'Draft' if draft else 'At capture'}</b><span>{escape(STATUS)}</span></div></header>
<details class="mobile-nav"><summary>Jump to a screen</summary>{navigation}<a href="#live-order">Live demo order</a></details>
<div class="layout"><nav class="toc" aria-label="Walkthrough"><p class="toc-title">Thirteen screens</p>{navigation}<p class="chapter">On stage</p><a href="#live-order">Live demo order</a><a href="#evidence">Evidence and next action</a></nav><main class="main"><section class="environment" id="deployment"><h2>Deployment at capture</h2><table><tbody>{environment}</tbody></table><p>The original x86 host is stopped and retained for rollback. The owner dashboard is available through the existing SSH tunnel at localhost:5599. Gateway and MCP ports have no public ingress.</p></section>
{''.join(cards)}
<section class="flow" id="live-order"><h2>Live demo order</h2><ol>{flow}</ol></section>
<section class="notes" id="evidence"><h2>Evidence and next action</h2><p>Native server metrics use a 10-second export interval, seven-day retention and a 64 MiB retention target. Pruning protects active writers, so storage can temporarily exceed the target; see the <a href="../infrastructure/RUNBOOK.md">telemetry runbook</a>. Anonymous product reporting is off and no OTLP endpoint is configured. The custom collectors sample every minute and keep up to 240 samples per source plus 200 collection events on EC2.</p><p>All screenshots are original browser captures. They were not redrawn, retouched or populated with demonstration fixtures. Process IDs, counts and sample ages will change as the system runs.</p><p>Follow the <a href="../scripts/EC2-LOGIN.md">fresh EC2 sign-in procedure</a>, then use the <a href="../scripts/native-backend-demo.README.md">native evidence runner</a> to start a new Kiro CLI session and rerun the enforcement walkthrough. Preserve these screenshots as the pre-authentication baseline and save a successful run with new correlated events.</p><p class="small">Read the adjacent <a href="kirocrew-admin-findings.md">findings</a> and <a href="kirocrew-admin-walkthrough.md">Markdown guide</a>. Cloud state and direct MCP/AWS behavior have separate receipts under evidence/aws/arm-20260913. The screenshot manifest and editorial receipt are under evidence/admin-console.</p><p class="small"><strong>What changed.</strong> The editing pass clarified which host the metric settings control, corrected the screen order and linked the sign-in and native-run procedures. It shortened repeated cautions, corrected the 64 MiB setting to a retention target and preserved the measured values and pending CLI sign-in.</p></section>
<footer class="footer">Portable HTML · 13 unmodified screenshots embedded · No external assets or network requests · Press Escape to close an expanded screenshot</footer></main></div></div>
<dialog aria-label="Expanded console screenshot"><div class="dialogbar"><span id="dialog-title"></span><button type="button" id="close-dialog">Close · Esc</button></div><img id="dialog-image" alt=""></dialog>
<script>
const dialog=document.querySelector('dialog'), zoom=document.getElementById('dialog-image'), title=document.getElementById('dialog-title');
document.querySelectorAll('.image-button').forEach(button=>button.addEventListener('click',()=>{{const source=button.querySelector('img');zoom.src=source.src;zoom.alt=source.alt;title.textContent=button.closest('.step').querySelector('h2').textContent;dialog.showModal();}}));
document.getElementById('close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{{if(event.target===dialog){{const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}}}});
const nav=[...document.querySelectorAll('.toc a')];
const observer=new IntersectionObserver(entries=>{{const visible=entries.filter(x=>x.isIntersecting);if(visible.length){{nav.forEach(a=>a.removeAttribute('aria-current'));const active=nav.find(a=>a.hash==='#'+visible[0].target.id);if(active)active.setAttribute('aria-current','true');}}}},{{rootMargin:'-10% 0px -60% 0px'}});document.querySelectorAll('.step,.flow,.notes').forEach(node=>observer.observe(node));
</script></body></html>'''


def build(draft: bool) -> None:
    OUT.mkdir(exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    guide = markdown(draft)
    paths = [OUT / "kirocrew-admin-walkthrough.html", OUT / "kirocrew-admin-walkthrough.md", OUT / "kirocrew-admin-findings.md"]
    rendered = document(draft)
    for path, content in zip(paths, [rendered, guide, findings_markdown()]):
        path.write_text(content, encoding="utf-8")
    if draft and not (EVIDENCE / "editorial-draft.md").exists():
        (EVIDENCE / "editorial-draft.md").write_text(guide + "\n\n" + findings_markdown(), encoding="utf-8")
    shots = []
    for section in SECTIONS:
        info = screenshot_info(section, draft)
        if info:
            info.pop("uri")
            info.update({"screen": section["id"], "navigation": section["path"], "capture": "Parent observed and saved original CUA browser screenshot; this builder reads unchanged bytes."})
            shots.append(info)
    embedded_hashes = [hashlib.sha256(base64.b64decode(encoded, validate=True)).hexdigest()
                       for encoded in re.findall(r'src="data:image/(?:jpeg|png);base64,([^"]+)"', rendered)]
    identifiers = set(re.findall(r'\bid="([^"]+)"', rendered))
    anchor_targets = set(re.findall(r'href="#([^"]+)"', rendered))
    browser_receipt = EVIDENCE / "browser-receipt.json"
    browser_blocked = browser_receipt.is_file() and json.loads(browser_receipt.read_text()).get("portable_html", {}).get("browser_status") == "blocked_by_browser_URL_security_policy"
    build_status = "draft" if draft else "static_passed_browser_blocked" if browser_blocked else "generated_pending_browser_review"
    receipt = {"schema": 1, "kind": "admin_walkthrough_artifact_manifest", "built_at_utc": datetime.now(timezone.utc).isoformat(),
               "status": build_status, "builder_sha256": sha(Path(__file__)),
               "browser_receipt": str(browser_receipt) if browser_receipt.is_file() else None,
               "browser_scope": "The direct local-file attempt on the prior guide build was blocked by browser URL security policy. This rebuilt guide has not been opened; no alternate route was attempted." if browser_blocked else "Browser validation requires a separate observed receipt.",
               "artifacts": [{"path": str(path), "sha256": sha(path), "bytes": path.stat().st_size} for path in paths],
               "screenshots": shots, "screenshot_count": len(shots), "expected_screenshot_count": 13,
               "static_checks": {"thirteen_sections": len(SECTIONS) == 13, "unique_section_ids": len({s["id"] for s in SECTIONS}) == 13,
                                 "all_screenshots_present": len(shots) == 13, "all_screenshots_embedded_unchanged": embedded_hashes == [s["sha256"] for s in shots],
                                 "all_navigation_targets_exist": anchor_targets <= identifiers,
                                 "no_external_asset_urls": not re.search(r'(?:src|href)=[\"\x27]https?://', rendered),
                                 "no_missing_markdown_images": all(Path(s["path"]).is_file() for s in shots)},
               "scope": ["Screenshots are historical observed UI snapshots, not a live portal.", "Native Kiro CLI authentication and enforcement remain pending.", "Custom App Kit telemetry is separate from native Gateway telemetry and the security event log.", "Browser layout, screenshot expansion and keyboard behavior remain unverified after the recorded URL-policy block."]}
    (EVIDENCE / "walkthrough-manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"draft": draft, "screenshots": len(shots), "outputs": [str(p) for p in paths]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", action="store_true", help="Allow screenshots whose capture is still pending.")
    build(parser.parse_args().draft)
