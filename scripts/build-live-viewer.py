#!/usr/bin/env python3
"""Integrate accepted and deployed diagrams without modifying either document."""

import base64
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_json(path):
    return json.loads((ROOT / path).read_text())


def fingerprint(path):
    data = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def esc(value):
    return html.escape(str(value))


client = read_json("evidence/aws/client-runtime-verification.json")
mcp = read_json("evidence/aws/mcp-live-receipt.json")
native_path = ROOT / "evidence/aws/native-backend-verification.json"
native = json.loads(native_path.read_text()) if native_path.exists() else {}
native_verified = native.get("native_crew_backend_verified") is True
checks = {item["name"]: item for item in mcp["checks"]}
client_verified = (
    client["runLocalGateway"] is False
    and client["listeners"]["5476"]["listener_present"] is False
    and client["listeners"]["5599"]["listener_present"] is True
    and client["native_ui_observation"]["status"] == "Gateway connected"
)
sources = {
    "security": "kirocrew-security-layers-browser.html",
    "ec2": "kirocrew-ec2-live.html",
}
encoded = {
    key: base64.b64encode((ROOT / value).read_bytes()).decode()
    for key, value in sources.items()
}
rows = [
    ("Desktop → EC2 Gateway", client_verified, "The desktop reports Gateway connected on :5599. The local Gateway setting is off, local :5476 has no listener, and the SSH tunnel listens on :5599.", "evidence/aws/client-runtime-verification.json", "Client receipt"),
    ("Allowed S3 read", checks["read_allowed"]["passed"], "The direct MCP probe read a preseeded 55-byte object through the EC2 role. Its digest matched the fixture.", "evidence/aws/mcp-live-receipt.json", "MCP receipt"),
    ("MCP grant denial", checks["mcp_denied"]["passed"], "The MCP service denied the discovered tool before AWS dispatch. The audit records the tool-grant decision.", "evidence/aws/mcp-live-audit.jsonl", "MCP audit"),
    ("AWS IAM denial", checks["iam_denied"]["passed"], "S3 returned AccessDenied (HTTP 403) for an existing object under the explicitly denied prefix. The receipt records an AWS request ID.", "evidence/aws/mcp-live-receipt.json", "MCP receipt"),
    ("Native backend + Crew prevention", native_verified, "Fresh GitHub sign-in on EC2 is pending. Native tool calls and Crew prevention are not yet verified." if not native_verified else native.get("summary", "See the native backend receipt for the exact backend, events and enforcement results."), "evidence/aws/native-backend-verification.json" if native_verified else "evidence/aws/backend-login-status.json", "Native backend receipt" if native_verified else "Current boundary"),
]
proof_rows = "".join(
    '<tr><th scope="row">' + esc(title) + '</th><td><span class="status ' + ("pass" if passed else "pending") + '">' + ("Verified" if passed else "Pending") + '</span></td><td>' + esc(body) + ' <a href="' + esc(path) + '">' + esc(label) + '</a></td></tr>'
    for title, passed, body, path, label in rows
)

PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KiroCrew · Live EC2 demo</title><style>
*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#192c43;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}header{min-height:76px;padding:13px 24px;background:#10243b;color:#fff;display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap}h1{font-size:18px;line-height:1.25;margin:0;font-weight:650}.strap{color:#bdcddd;font-size:12px;margin:5px 0 0}nav{display:flex;gap:7px;flex-wrap:wrap}button{font:inherit;font-size:13px;cursor:pointer;border:1px solid #66809a;border-radius:6px;background:transparent;color:#fff;padding:9px 14px}button[aria-selected=true]{background:#edf5ff;color:#10243b;border-color:#edf5ff}button:focus-visible,a:focus-visible,summary:focus-visible{outline:3px solid #e9a93d;outline-offset:3px}.panel[hidden]{display:none}iframe{display:block;width:100%;height:calc(100dvh - var(--header-h,76px));border:0;background:#fff}.context{display:none;height:36px;padding:9px 24px;margin:0;background:#e9eff6;color:#425a74;font-size:12px;line-height:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.context strong{color:#203e5e}.reference{max-width:1160px;margin:auto;padding:30px 26px 54px}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.1em;color:#5d738a;margin:0 0 8px;font-weight:650}.reference h2{font-size:29px;letter-spacing:-.025em;line-height:1.2;margin:0 0 13px;max-width:860px}.lede{font-size:16px;line-height:1.6;margin:0 0 23px;max-width:960px;color:#3a536d}.facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 26px}.fact{background:white;padding:16px 18px;border:1px solid #dce5ef;border-radius:8px}.fact h3{font-size:12px;text-transform:uppercase;letter-spacing:.065em;color:#5c728a;margin:0 0 7px}.fact p{font-size:15px;margin:0;line-height:1.45}.fact strong{display:block;font-size:18px;font-weight:650;margin-bottom:4px}.section-title{font-size:18px;margin:24px 0 12px}.table-wrap{border:1px solid #d6e1ed;border-radius:8px;overflow:hidden;background:#fff}table{width:100%;border-collapse:collapse;table-layout:fixed;text-align:left;font-size:14px;line-height:1.5}thead th{background:#e6edf6;padding:11px 15px;color:#36516e;font-size:12px;text-transform:uppercase;letter-spacing:.06em}thead th:nth-child(1){width:25%}thead th:nth-child(2){width:13%}tbody th{font-size:14px;font-weight:650;padding:16px 15px;vertical-align:top}td{padding:16px 15px;vertical-align:top;color:#38516c}tbody tr+tr{border-top:1px solid #e0e7ef}.status{display:inline-block;font-size:12px;line-height:1.2;border-radius:4px;padding:5px 7px;font-weight:650;white-space:nowrap}.pass{background:#e1f2eb;color:#176345}.pending{background:#fff0cf;color:#82540e}a{color:#245d94;text-decoration-thickness:1px;text-underline-offset:2px}code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.9em}.detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:21px 0}details{border:1px solid #dbe4ee;background:white;border-radius:8px;padding:16px 18px;line-height:1.6}summary{font-size:14px;font-weight:650;color:#234569;cursor:pointer}details p{font-size:14px;margin:12px 0 0;color:#425a73}.links{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}.links a{background:#fff;border:1px solid #c5d4e4;padding:10px 14px;border-radius:6px;font-weight:600;font-size:13px;text-decoration:none}.boundary{border-left:3px solid #c38e35;background:#fff6e6;padding:14px 18px;color:#644c25;font-size:14px;line-height:1.6;margin:20px 0}.receipt-date{font-size:12px;color:#65798e;line-height:1.65;margin:22px 0 0}@media(max-width:760px){header{padding:12px 16px;gap:12px}h1{font-size:16px}nav button{padding:8px 10px}.context{padding-left:16px}.reference{padding:24px 16px}.reference h2{font-size:25px}.facts,.detail-grid{grid-template-columns:1fr}.table-wrap{overflow-x:auto}table{min-width:640px}}
</style></head><body>
<header id="top"><div><h1>KiroCrew · Live EC2 demo</h1><p class="strap">Laptop client · remote Gateway and workspace · separate enforcement decisions</p></div><nav role="tablist" aria-label="Demo views"><button id="tab-ec2" role="tab" aria-selected="true" aria-controls="ec2" data-view="ec2">Deployed EC2</button><button id="tab-security" role="tab" aria-selected="false" aria-controls="security" data-view="security" tabindex="-1">Security layers</button><button id="tab-reference" role="tab" aria-selected="false" aria-controls="reference" data-view="reference" tabindex="-1">Live evidence</button></nav></header>
<main>
<section class="panel" id="ec2" role="tabpanel" aria-labelledby="tab-ec2"><p class="context"><strong>Deployed in us-east-1.</strong> CloudFormation owns the demo infrastructure. The evidence tab separates verified calls from the pending native backend path.</p><iframe id="ec2-frame" title="Archify deployed EC2 demo topology"></iframe></section>
<section class="panel" id="security" role="tabpanel" aria-labelledby="tab-security" hidden><p class="context"><strong>Accepted control map.</strong> The single endpoint-control enclosure and September 11 source baseline are preserved. This view describes controls beyond this demo’s verified scope.</p><iframe id="security-frame" title="Accepted Archify single endpoint-control security map"></iframe></section>
<section class="panel reference" id="reference" role="tabpanel" aria-labelledby="tab-reference" hidden>
<p class="eyebrow">September 13, 2026 · evidence boundaries</p><h2>The laptop is the client. EC2 runs the Gateway.</h2><p class="lede">The desktop connection and direct MCP/AWS calls have live receipts. Keep the backend path separate: connection to a Gateway does not prove that a coding backend authenticated or that Crew prevented a model-requested tool call.</p>
<div class="facts"><article class="fact"><h3>Client connection</h3><p><strong>Local Gateway off</strong>Desktop :5599 → SSH → EC2 :5476</p></article><article class="fact"><h3>Cloud host</h3><p><strong>t3a.small · us-east-1</strong>CloudFormation · encrypted 24 GiB gp3</p></article><article class="fact"><h3>Inbound boundary</h3><p><strong>SSH from one /32</strong>Gateway and MCP bind to loopback</p></article></div>
<h3 class="section-title">What the receipts establish</h3><div class="table-wrap"><table aria-label="Verified and pending demo outcomes"><thead><tr><th scope="col">Path</th><th scope="col">Status</th><th scope="col">Observed result and receipt</th></tr></thead><tbody>__PROOF_ROWS__</tbody></table></div>
<div class="boundary"><strong>Scope:</strong> The four-tool MCP service demonstrates caller authentication, a fixed tool grant and an EC2 role reaching S3. It is a purpose-built demo service. Central policy distribution, per-user OAuth, a general MCP proxy and external SEL collection are separate integration work.</div>
<div class="detail-grid"><details id="detail-identities"><summary>Keep the identities distinct</summary><p>SSH authenticates the laptop connection. Crew authenticates the desktop session. The MCP service recognizes a fixed demo caller. AWS evaluates the EC2 workload role. Success at one boundary does not grant permission at the next.</p><p>The <code>crew</code> user cannot reach instance metadata through the host guard; the separate MCP service uses the instance role. The demo tools expose fixed object reads, not arbitrary AWS APIs. The instance role also includes <code>AmazonSSMManagedInstanceCore</code>.</p><p>The <code>crew</code> user can write the demo configuration, including its configured deny rule. A native denial would demonstrate that configured gate; it would not establish an immutable managed policy. <a href="kirocrew-ec2-notes.md">Deployment and evidence details</a>.</p></details><details id="detail-baselines"><summary>Keep the version evidence distinct</summary><p>The accepted security diagram remains pinned to September 11 source. The EC2 install uses a Linux repack of the user-installed <code>0.7.0-nightly.20260912t060850</code> snapshot with Linux dependencies locked separately. It is not an official Linux nightly artifact, and no source commit is assigned to it.</p><p>Receipts: <a href="evidence/aws/linux-repack.json">Linux repack</a> · <a href="evidence/nightly/installed-nightly-verification.json">installed nightly</a> · <a href="evidence/aws/kiro-cli-artifact.json">Kiro CLI artifact</a>.</p></details></div>
<h3 class="section-title">Present the evidence in order</h3><p class="lede">Start with the brief deck. Use the deployed view to locate the Gateway, backend, workspace and separate MCP service. Open the security map to explain the single endpoint boundary. Return here to show what ran and what still needs a native backend receipt.</p><div class="links"><a href="output/kirocrew-ec2-demo.pptx">Open the updated deck</a><a href="WALKTHROUGH.md">Presenter walkthrough</a><a href="infrastructure/ec2-demo.json">CloudFormation template</a><a href="evidence/aws/archify/delivery-receipt.json">EC2 diagram receipt</a><a href="evidence/aws/walkthrough-direct-probe.json">Live command rehearsal</a></div>
<p class="receipt-date">Client observed: __CLIENT_DATE__ · direct MCP probe: __MCP_DATE__.<br>Both diagram documents are embedded byte-for-byte. The reference scrolls vertically; diagram views resize to the available frame. The browser receipt binds the generated viewer and both input documents.</p>
</section></main>
<script>
const sources=__SOURCES__;
const loaded=new Set();
function loadView(id){if(!sources[id]||loaded.has(id))return;const bytes=Uint8Array.from(atob(sources[id]),c=>c.charCodeAt(0));document.getElementById(id+'-frame').srcdoc=new TextDecoder().decode(bytes);loaded.add(id)}
function showView(id){if(!['ec2','security','reference'].includes(id))id='ec2';document.querySelector('.strap').textContent={ec2:'Deployed in us-east-1 · laptop client, remote Gateway and workspace',security:'Accepted control map · September 11 source baseline · scope in Live evidence',reference:'Connection, MCP grants and AWS IAM · each claim bound to a receipt'}[id];document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==id);document.querySelectorAll('[data-view]').forEach(b=>{b.setAttribute('aria-selected',String(b.dataset.view===id));b.tabIndex=b.dataset.view===id?0:-1});loadView(id);history.replaceState(null,'','#'+id)}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
document.querySelector('nav[role=tablist]').addEventListener('keydown',e=>{const tabs=[...document.querySelectorAll('[data-view]')];let i=tabs.indexOf(document.activeElement);if(i<0)return;if(e.key==='ArrowRight')i=(i+1)%tabs.length;else if(e.key==='ArrowLeft')i=(i+tabs.length-1)%tabs.length;else if(e.key==='Home')i=0;else if(e.key==='End')i=tabs.length-1;else return;e.preventDefault();showView(tabs[i].dataset.view);tabs[i].focus()});
new ResizeObserver(entries=>document.documentElement.style.setProperty('--header-h',entries[0].target.getBoundingClientRect().height+'px')).observe(document.getElementById('top'));
window.addEventListener('hashchange',()=>showView(location.hash.slice(1)||'ec2'));
showView(location.hash.slice(1)||'ec2');
</script></body></html>
'''
page = (PAGE.replace("__PROOF_ROWS__", proof_rows)
        .replace("__CLIENT_DATE__", esc(client["observed_at"]))
        .replace("__MCP_DATE__", esc(mcp["time"]))
        .replace("__SOURCES__", json.dumps(encoded, separators=(",", ":"))))
target = ROOT / "kirocrew-demo-live.html"
target.write_text(page)
inputs = list(sources.values()) + ["evidence/aws/client-runtime-verification.json", "evidence/aws/mcp-live-receipt.json", "evidence/aws/backend-login-status.json", "evidence/aws/walkthrough-direct-probe.json"]
if native_path.exists():
    inputs.append(str(native_path.relative_to(ROOT)))
receipt = {"schema": 1, "kind": "integrated_live_viewer_build", "artifact": fingerprint(target.name), "inputs": [fingerprint(p) for p in inputs], "embedded_diagrams": {key: fingerprint(path) for key, path in sources.items()}, "client_verified": client_verified, "direct_mcp_verified": mcp["passed"], "native_crew_backend_verified": native_verified, "scope": "Build and evidence attribution only. Browser validation is recorded separately."}
(ROOT / "evidence/aws/viewer-build.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"artifact": target.name, "bytes": target.stat().st_size, "native_crew_backend_verified": native_verified}))
