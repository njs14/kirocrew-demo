#!/usr/bin/env python3
"""Build the standalone presentation from preserved demo evidence. No network calls."""
from pathlib import Path
import base64
import hashlib
import html
import json
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/kirocrew-system-design.html"
COPY = ROOT / "output/kirocrew-system-design-notes.md"
EVIDENCE = ROOT / "evidence/presentation/kirocrew-system-design"
source_copy = (ROOT / "output/kirocrew-arm-observability-demo-copy.md").read_text()
old_notes = {}
for number, block in re.findall(r"## Slide (\d+)\n(.*?)(?=\n## |\Z)", source_copy, re.S):
    old_notes[int(number)] = re.sub(r"^\d\d:\d\d–\d\d:\d\d\.\s*", "", block.split("### Speaker notes\n", 1)[1].strip())
assets = {}


def asset(path):
    if path not in assets:
        raw = (ROOT / path).read_bytes()
        mime = "image/jpeg" if path.endswith(".jpg") else "image/png"
        assets[path] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                        "data": f"data:{mime};base64," + base64.b64encode(raw).decode()}
    return assets[path]["data"]


def picture(path, caption, cls="screenshot"):
    uri = asset(path)
    esc = html.escape(caption, quote=True)
    return f'<div class="{cls}"><button type="button" class="media-button" data-image="{uri}" data-caption="{esc}" aria-label="Expand image: {esc}"><img src="{uri}" alt="{esc}" decoding="sync"></button></div>'


def notes(text):
    # Keep receipt source paths and exact commands as readable text, without remote requests.
    return "".join(f"<p>{html.escape(p)}</p>" for p in text.split("\n\n"))


slides = []


def add(title, section, body, note, footer, theme="", subtitle="", custom_header=False):
    number = len(slides) + 1
    heading = "" if custom_header else f'<header class="slide-header"><p class="eyebrow">{html.escape(section)}</p><h2>{title}</h2>' + (f'<p class="subline">{subtitle}</p>' if subtitle else '') + '</header>'
    markup = f'''<section class="slide {theme}" id="slide-{number}" data-title="{html.escape(re.sub('<[^>]+>', '', title), quote=True)}" data-section="{html.escape(section)}" aria-label="Slide {number}: {html.escape(re.sub('<[^>]+>', '', title), quote=True)}"{' hidden' if number > 1 else ''}>
{heading}<div class="slide-body">{body}</div>
<footer class="slide-footer"><span>{footer}</span><span class="number">{number:02d}</span></footer>
<div class="speaker-notes" hidden>{notes(note)}</div></section>'''
    slides.append({"number": number, "title": re.sub('<[^>]+>', '', title), "section": section, "html": markup, "note": note, "body": body, "footer": footer, "subtitle": subtitle})


add("KiroCrew on ARM", "System design", '''
<div class="hero stack"><p class="cover-kicker">KiroCrew / System design &amp; demo</p>
<h1>Remote execution.<br><span class="purple">Local desktop.</span></h1>
<p class="hero-intro">The Mac connects to a KiroCrew environment on EC2. The Gateway and workspace stay on the server.</p>
<div class="hero-bottom"><p><strong>ARM deployment, direct MCP/AWS checks and telemetry collection verified.</strong><br>Native Kiro CLI sign-in and session pending.</p><span class="date">Recorded September 13, 2026</span></div></div>''', old_notes[1],
"CloudFormation in us-east-1 &nbsp; / &nbsp; Architecture and recorded demo evidence", "dark", custom_header=True)

add("What this demo must establish", "01 / Requirements", '''
<div class="split wide-left"><div class="rule-list">
<div class="rule-row"><b>01</b><div><h3>The desktop connects to EC2</h3><p>The Mac's local Gateway stays off.</p></div></div>
<div class="rule-row"><b>02</b><div><h3>Access stays bounded</h3><p>SSH ingress from the operator's IPv4 /32. Separate Crew and MCP identities.</p></div></div>
<div class="rule-row"><b>03</b><div><h3>Each refusal has a stopping point</h3><p>Crew configuration, MCP grants and target AWS IAM have distinct roles.</p></div></div>
<div class="rule-row"><b>04</b><div><h3>Both machines are observable</h3><p>Client health, server health and collection events appear in the admin portal.</p></div></div>
</div><div class="stack"><p class="eyebrow">Demo assumption</p><h3>One operator on<br>one execution host</h3><p class="note">Concurrency, latency and availability targets still need native-session measurements.</p><div class="callout"><strong>Remaining acceptance gate</strong>Sign in to the EC2 Kiro CLI and verify the four native turns.</div></div></div>''',
"This demo assumes one operator on one ARM EC2 host. Service-level objectives, sustained-load capacity and multi-user isolation still need validation.\n\nThe demo requires a remote Gateway, inbound access restricted to the operator's IP, backend MCP/AWS enforcement and client/server telemetry. The dated receipts establish the deployment, direct service checks and operational telemetry. Native Kiro CLI authentication and execution remain pending. Sources: HANDOFF.md; ARM-CONTINUATION-RECEIPT.json; WALKTHROUGH.md.",
"Scope: a single-operator demo. Native backend enforcement remains pending.")

add("One endpoint-control boundary", "02 / Architecture", f'''
<div class="split wide-right"><div class="stack"><p class="lead">EC2 contains the Gateway, selected backend and workspace. The laptop is the client.</p><div class="callout"><strong>Reference diagram · September 11</strong>Includes controls beyond this demo.</div><p class="note">Crew can edit demo configuration and App Kit code. Protected policy and path enforcement are unverified.</p><p class="caption">ARM checks: September 13. Expand the reference to inspect its labels.</p></div><div class="image-and-caption">{picture('evidence/browser/endpoint-slide.png', 'Accepted September 11 endpoint-control reference. One enclosure preserved. Broader capabilities require their own verification.', 'endpoint')}</div></div>''', old_notes[2],
"Verified: remote connection, direct MCP grants and S3 IAM. Sandbox, egress control and SEL/HMAC execution unverified.")

add("ARM execution in us-east-1", "02 / Architecture", f'''
{picture('evidence/aws/archify-arm/kirocrew-arm-slide-council-1152x480.png', 'Mac client through SSH to the ARM Gateway. Native MCP path is dashed and pending. Separate direct mcp-demo service probe reached MCP and S3.', 'diagram')}
<div class="probe-flow" aria-label="Verified direct path: EC2 probe as mcp-demo to loopback MCP service to S3"><span class="probe-label">Verified direct path</span><strong>EC2 probe <small>(mcp-demo)</small></strong><b aria-hidden="true">→</b><strong>MCP :8001</strong><b aria-hidden="true">→</b><strong>S3</strong></div>
<div class="metrics-strip"><div><strong>4 vCPU</strong><span>t4g.xlarge, ARM64</span></div><div><strong>16 GiB</strong><span>Host memory</span></div><div><strong>40 GiB</strong><span>Encrypted gp3 root</span></div><div><strong>SSH /32</strong><span>Only inbound rule</span></div></div>''', old_notes[3],
"Recorded September 13: cloud 14:22 UTC, ingress 14:57 UTC. Diagram shows native MCP path pending.")

add("Host identity determines authority", "03 / Authorization", '''
<div class="table-wrap"><table><thead><tr><th>Identity</th><th>Responsibility</th><th>Policy and evidence</th></tr></thead><tbody>
<tr><td><code>crew</code></td><td>Gateway, backend and workspace</td><td>Observed: IPv4 metadata TCP denied<small>errno 113. No HTTP request or credential read.</small></td></tr>
<tr><td><code>mcp-demo</code></td><td>Fixed MCP tools and S3 reads</td><td>Role policy: two S3 prefixes, explicit deny<small>SSM core attached; SSM execution untested.</small></td></tr>
<tr><td>Administrator<small>Operator SSH account, sudo</small></td><td>Installs code and manages services</td><td>Trusted host administration<small>Core Gateway and MCP runtime files are root-owned.</small></td></tr>
</tbody></table></div><div class="callout"><strong>Crew can edit configuration and custom App Kit code.</strong>Immutable policy and tamper resistance remain unverified.</div>''', old_notes[4],
"IPv4 metadata connection check at 14:56 UTC. Separate from native sandbox proof.")

add("Four calls, three denial boundaries", "03 / Authorization", '''
<div class="table-wrap"><table><thead><tr><th>Tool</th><th>Result</th><th>Stopping point</th></tr></thead><tbody>
<tr><td><code>read_allowed</code></td><td>Allowed object digest</td><td>S3 completes the read</td></tr>
<tr class="pending-row"><td><code>crew_denied</code></td><td>Configured. Native proof pending.</td><td>Crew before MCP dispatch</td></tr>
<tr><td><code>mcp_denied</code></td><td><code>tool_grant_denied</code></td><td>MCP before AWS dispatch</td></tr>
<tr><td><code>iam_denied</code></td><td>S3 AccessDenied, HTTP 403</td><td>AWS IAM</td></tr>
</tbody></table></div><p class="evidence-line">The direct probe covers three tools. Only a native turn can establish the configured Crew denial.</p>''', old_notes[5],
"Contract: fixed S3 actions and objects. Caller supplies a trace ID. No general-purpose AWS tool.")

add("Direct MCP and AWS results", "04 / Recorded evidence", '''
<div class="split"><div><p class="eyebrow">Allowed object</p><p class="large-stat">55</p><p class="stat-unit">bytes read from S3</p><p class="stat-description mono">SHA256 34ebbefeb5f66527…</p><p class="caption mono">AWS request FC4GTZS0B83EQ5W1</p></div><div class="stack"><div><h3>MCP refused the tool</h3><p class="note"><code>mcp_denied</code> returned <code>tool_grant_denied</code> before AWS dispatch.</p></div><div><h3>AWS refused the object</h3><p class="note"><code>iam_denied</code> returned AccessDenied, HTTP 403.</p><p class="caption mono">AWS request BA5BT7K9765938BT</p></div><div class="callout"><strong>Direct service probe passed.</strong><code>native_crew_backend_verified=false</code></div></div></div>
<p class="evidence-line">Unauthenticated request: 401. Discovery: four tools.</p>''', old_notes[6],
"Separate direct probe recorded September 13, 2026 at 15:01:37 UTC.")

add("Client and server nightly baselines", "04 / Recorded evidence", '''
<div class="split"><div class="stack"><div><p class="baseline-title">Mac client</p><p class="baseline-date">September 13</p><p class="baseline-code mono">0.7.0-nightly.20260913t061222</p></div><p>48 selected RECORD checks passed across arm64 and x64 bundles.</p></div><div class="stack"><div><p class="baseline-title">EC2 server</p><p class="baseline-date">September 12</p><p class="baseline-code mono">0.7.0-nightly.20260912t060850</p></div><p>Unofficial Linux ARM64 repack. 24 selected control modules match the frozen build.</p></div></div>
<div class="callout"><strong>Kiro CLI 2.21.4 is selected. Sign-in remains pending.</strong>The latest recorded CLI check at 15:19 UTC was unauthenticated. The KAS GitHub card uses a separate identity store.</div>''', old_notes[7] + "\n\nLatest authentication receipt: evidence/aws/arm-20260913/native-cli-login-outcome.json, September 13 at 15:19 UTC. The normal CLI login ended without an authenticated account. This presentation contains recorded state and does not poll the running system.",
"Different builds. Behavioral equivalence and a native model session remain unverified.")

add("Native telemetry measures the Gateway", "05 / Observability", f'''
<div class="split wide-right"><div class="stack"><h3>Request, boot and process metrics</h3><div class="metrics-strip"><div><strong>10 s</strong><span>Local export interval</span></div><div><strong>7 days</strong><span>Retention</span></div></div><p class="note">64 MiB retention target. No OTLP endpoint. Anonymous usage reporting off.</p><div class="callout"><strong>Native model-session metrics pending.</strong>The displayed 0 ms turn latency comes from an empty series.</div></div><div class="image-and-caption">{picture('output/admin-console/09-native-telemetry.jpg', 'Native Gateway telemetry capture on September 13. Display window is 14 days; retention is seven days. Native model-turn metrics have no completed session.')}<p class="caption">Developer / Telemetry / Latency. Expand to inspect the original capture.</p></div></div>''', old_notes[8],
"Recorded September 13. The UI shows a 14-day window. One boot observation cannot establish a latency distribution.")

add("Client and server in the admin portal", "05 / Observability", f'''
{picture('output/admin-console/11-client-server-telemetry.jpg', 'Demo Observability capture with client and server samples. These are recorded observations, not a live feed.')}
<div class="metrics-strip"><div><strong>60 s</strong><span>Collection interval</span></div><div><strong>15 s</strong><span>Page refresh</span></div><div><strong>180 s</strong><span>Stale threshold</span></div><div><strong>240</strong><span>Samples per source</span></div></div>''', old_notes[9],
"Captured September 13. Clocks: EDT (UTC−4). Client CPU measures a process family; server CPU measures the host.",
subtitle="Custom App Kit via the admin portal's owner-token proxy; separate from CLI sign-in. Expand the capture to inspect.")

add("Closing the client did not stop the Gateway", "05 / Observability", f'''
<div class="two-shots"><div>{picture('output/admin-console/13-client-stopped.jpg', 'Stopped client sample at 14:44:42 UTC. Desktop check No. Gateway and MCP service checks remained Yes.')}<p class="caption"><strong>14:44:42 UTC</strong> / Stopped-client sample</p></div><div>{picture('output/admin-console/12-collection-logs.jpg', 'Collection events show the stopped client warning and the recovery sample at 14:49:34 UTC. Screenshot clocks are EDT, four hours behind UTC.')}<p class="caption"><strong>14:49:34 UTC</strong> / Recovery sample in collection logs</p></div></div>
<div class="callout"><strong>Per receipt: Gateway PID 4991, started 14:26:10 UTC, unchanged.</strong>Gateway and MCP stayed active. Active model-session continuity remains unverified.</div><p class="evidence-line">Crew-run collection events are operational telemetry, not SEL audit records. Expand either capture to inspect.</p>''', old_notes[10],
"September 13 sample times, not click times. Screenshot clocks: EDT (UTC−4). Current means freshness; health is a separate check.")

add("Running cost and operational trade-offs", "06 / Decisions", '''
<div class="split"><div><p class="eyebrow">730 running hours</p><p class="large-stat">$107</p><p class="stat-unit">per month, always on</p><p class="stat-description">Compute, public IPv4 and both disks. Model use, S3, transfer and tax add charges.</p><p class="caption">Estimate from September 13 price evidence.</p></div><div class="rule-list"><div class="rule-row"><b>01</b><div><h3>One host</h3><p>Fewer components, one failure domain.</p></div></div><div class="rule-row"><b>02</b><div><h3>Standard CPU credits</h3><p>No surplus charges. Sustained work can throttle after credits run out.</p></div></div><div class="rule-row"><b>03</b><div><h3>Retained rollback host</h3><p>The stopped t3a.small retains a 24 GiB disk at $1.92/month. Stop ARM when idle.</p></div></div></div></div>''', old_notes[12] + "\n\nOne execution host reduces the number of services to operate. Its failure can interrupt execution, local state and telemetry together. This edition has no tested failover or recovery-time commitment. The chosen 4 vCPU / 16 GiB host does not establish sustained session capacity.",
"$0.1394 per running hour. ARM storage $3.20/month plus stopped x86 storage $1.92/month. EBS remains billable.")

add("Decisions to revisit as usage grows", "06 / Decisions", '''
<div class="table-wrap"><table class="table-compact"><thead><tr><th>Trigger</th><th>Current choice</th><th>Next decision</th></tr></thead><tbody>
<tr><td>Shared users</td><td>Fixed demo grants<br>Crew-writable configuration</td><td>Identity-bound MCP grants and protected policy distribution</td></tr>
<tr><td>Uptime commitments</td><td>One host, local state</td><td>Backups, recovery targets and tested reconnect or failover</td></tr>
<tr><td>Sustained workloads</td><td>Burstable ARM host<br>Different nightly builds</td><td>Native-session measurements, CPU-credit behavior and version compatibility</td></tr>
<tr><td>Audit retention</td><td>Local operational samples<br>200 fixed collection events</td><td>Protected external security-event storage, separate from telemetry</td></tr>
</tbody></table></div><p class="evidence-line">First priority: complete native authentication and verify the four-turn enforcement sequence.</p>''',
"These are proposed design decisions, not deployed capabilities. The present system serves one operator with a fixed MCP catalog, a bounded instance role, local operational telemetry and a single ARM execution host.\n\nFor multiple users, review how user identity reaches MCP grants and prevent an execution identity from changing the enforcing policy. For uptime commitments, specify recovery point and recovery time before choosing replication or failover. For sustained workloads, collect real authenticated session measurements before resizing or adding hosts. For audit retention, design protected external security-event collection independently of numeric operational telemetry.\n\nDo not infer central policy, SSM transport, EDR, multi-user isolation, external SEL storage or failover from the current demo. Sources: HANDOFF.md; infrastructure/RUNBOOK.md; output/kirocrew-admin-findings.md.",
"Proposed next decisions. No multi-user capacity, failover or external audit-retention claim.")

add("Desktop-to-EC2 walkthrough", "07 / Live demo", '''
<div class="walkthrough-grid"><article><b>01 / CONNECTION</b><h3>Confirm the remote workspace</h3><p>Show the desktop connected through :5599. Confirm the Mac's local Gateway is off.</p></article><article><b>02 / OBSERVABILITY</b><h3>Inspect both machines</h3><p>Open native Gateway telemetry, then client/server samples and collection events.</p></article><article><b>03 / DIRECT PROBE</b><h3>Run the three-call MCP probe</h3><p>Inspect the object digest, MCP refusal and S3 403 with fresh request IDs.</p></article><article><b>04 / PENDING NATIVE ACCEPTANCE</b><h3>Sign in before native turns</h3><p>If sign-in fails, stop here and report it. After sign-in, run four turns; <code>crew_denied</code> must stop automatically before MCP dispatch.</p></article></div>
<div class="link-row"><a class="slide-link" href="http://localhost:5599/apps/demo-observability" target="_blank" rel="noopener noreferrer">Open admin portal</a><span class="note">Exact commands and evidence checks are in this slide's notes.</span></div>''', old_notes[11] + "\n\nCommands (run in the project terminal, not from the presentation):\npython3 scripts/ec2-login.py\n./native-demo.sh plan\n\nThe command below runs the direct three-tool probe. Complete native sign-in and approvals through their normal user flow. The presentation displays recorded evidence and does not execute these commands.",
"Stop the ARM host after the demo when idle. Retained disks remain billable.", "lilac")

# Carry the reviewed direct probe command into the final slide's speaker notes.
runbook = (ROOT / "WALKTHROUGH.md").read_text()
probe_blocks = re.findall(r"```(?:sh|bash)?\n(.*?)```", runbook, re.S)
probe = next((b.strip() for b in probe_blocks if "probe.py" in b and "ssh" in b), "See WALKTHROUGH.md for the reviewed direct probe command.")
slides[-1]["note"] += "\n\n" + probe
slides[-1]["html"] = slides[-1]["html"].replace('</div></section>', f'<pre>{html.escape(probe)}</pre></div></section>')

def text_from_markup(markup):
    text = re.sub(r"</(?:p|div|h[1-6]|tr|article)>|<br\s*/?>", "\n\n", markup)
    text = re.sub(r"</(?:td|th)>", " / ", text)
    text = re.sub(r"</(?:strong|small|span|b)>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in html.unescape(text).splitlines())
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()

copy_parts = ["# KiroCrew system-design presentation", "Recorded September 13, 2026. This presentation uses dated receipts and screenshots. It does not poll the live system."]
for slide in slides:
    copy_parts += [f'## {slide["number"]}. {slide["title"]}', f'### On slide\n\n{text_from_markup(slide["subtitle"])}\n\n{text_from_markup(slide["body"])}\n\n{text_from_markup(slide["footer"])}', f'### Speaker notes\n\n{slide["note"]}']
copy_parts += ["## What changed", "Added a visible direct-probe flow, clearer reference and pending-native labels, an empty-metric explanation, and persistent image expansion controls. Clarified host authority, admin authentication, collection events and retained storage. The No AI Slop pass tightened the new labels and removed repetition in the walkthrough notes. Original evidence images, tool names, request IDs and recorded times remain intact."]
copy_text = re.sub(r"\n{3,}", "\n\n", "\n\n".join(copy_parts)) + "\n"
COPY.write_text(copy_text)

css = (ROOT / "presentation/slides.css").read_text()
js = (ROOT / "presentation/slide-runtime.js").read_text()
download_pptx = "data:application/vnd.openxmlformats-officedocument.presentationml.presentation;base64," + base64.b64encode((ROOT / "output/kirocrew-arm-observability-demo.pptx").read_bytes()).decode()
download_notes = "data:text/markdown;charset=utf-8;base64," + base64.b64encode(copy_text.encode()).decode()
document = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="color-scheme" content="dark light"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data: blob:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"><title>KiroCrew on ARM — System design presentation</title><style>{css}</style></head>
<body><header class="shell-header"><span class="brand">KiroCrew</span><div class="header-right"><span class="edition">System design / September 2026</span><a href="{download_pptx}" download="kirocrew-arm-observability-demo.pptx" title="Earlier accepted ARM deck, 12 slides">Earlier PPTX (12 slides)</a></div></header>
<main id="deck" class="stage" aria-label="KiroCrew system design slides">{''.join(slide['html'] for slide in slides)}</main>
<nav class="toolbar" aria-label="Presentation controls"><div class="progress-track" aria-hidden="true"><div id="progress"></div></div>
<div class="toolbar-group"><button id="previous" class="nav-button" aria-label="Previous slide">←</button><span class="count" id="slide-count">1 / {len(slides)}</span><button id="next" class="nav-button" aria-label="Next slide">→</button><span id="section-label"></span></div>
<div class="toolbar-group"><button id="overview-button">Slides</button><button id="notes-button">Notes</button><button id="fullscreen-button">Full screen</button><button id="print-button" class="optional">Print</button><a href="{download_notes}" download="kirocrew-system-design-notes.md" class="optional">Script</a><button id="help-button" aria-label="Keyboard shortcuts">?</button></div></nav>
<p id="status" class="sr-only" role="status" aria-live="polite"></p>
<dialog id="overview-dialog" aria-labelledby="overview-title"><header><h2 id="overview-title">Slides</h2><button data-close>Close</button></header><div id="overview-list"></div></dialog>
<dialog id="notes-dialog" aria-labelledby="notes-title"><header><h2 id="notes-title">Speaker notes</h2><button data-close>Close</button></header><div id="notes-content"></div></dialog>
<dialog id="image-dialog" aria-labelledby="image-title"><header><h2 id="image-title">Original evidence image</h2><button data-close>Close</button></header><img id="expanded-image" alt=""><p id="image-caption"></p></dialog>
<dialog id="help-dialog" aria-labelledby="help-title"><header><h2 id="help-title">Keyboard shortcuts</h2><button data-close>Close</button></header><dl class="keys"><dt>← / →</dt><dd>Previous or next slide</dd><dt>Space</dt><dd>Next slide</dd><dt>Home / End</dt><dd>First or last slide</dd><dt>O / N</dt><dd>Slide overview / speaker notes</dd><dt>F</dt><dd>Full screen</dd><dt>Escape</dt><dd>Close an expanded image or dialog</dd></dl></dialog>
<noscript>This presentation uses JavaScript for navigation. Enable JavaScript to browse the slides.</noscript><script>{js}</script></body></html>'''
OUT.write_text(document)
EVIDENCE.mkdir(parents=True, exist_ok=True)
manifest = {"schema": 1, "edition": "Standalone system-design presentation", "slide_count": len(slides),
            "recorded_evidence_date": "2026-09-13", "live_state_reverified": False,
            "native_kiro_cli_proof": "pending in source receipts", "prior_council_scope": "Prior ARM PPTX candidate-v2 remains historical", "current_council_scope": "Grok 4.6 and Opus 5 reviewed frozen system-design-v1, HTML bfc2516128526ab049a7c4c0b36994aae82d87c44790785ee9125da5d63a5712; subsequent edits receive author validation", "council_receipt": "evidence/council/system-design-v1/council-verified-receipt.json",
            "artifact": {"path": str(OUT.relative_to(ROOT)), "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(), "bytes": OUT.stat().st_size},
            "speaker_notes": {"path": str(COPY.relative_to(ROOT)), "sha256": hashlib.sha256(COPY.read_bytes()).hexdigest()},
            "preserved_pptx_sha256": hashlib.sha256((ROOT / "output/kirocrew-arm-observability-demo.pptx").read_bytes()).hexdigest(),
            "embedded_assets": {p: {k: v for k, v in data.items() if k != "data"} for p, data in assets.items()},
            "slides": [{"number": s["number"], "title": s["title"], "section": s["section"]} for s in slides]}
(EVIDENCE / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Built {len(slides)} slides: {OUT} ({OUT.stat().st_size:,} bytes)")
