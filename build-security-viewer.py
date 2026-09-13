import base64
import html
import json
from pathlib import Path

base=Path(__file__).parent
rev='fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482'
source_root=f'https://github.com/kirodotdev/KiroCrew/blob/{rev}/src/kiro_crew/'
def layer(code,title,owner,scope,body,limit,demo,files):
 return dict(code=code,title=title,owner=owner,scope=scope,body=body,limit=limit,demo=demo,sources=[{'label':f,'url':source_root+f} for f in files])
layers=[
 layer('E','Managed endpoint baseline','Enterprise','All processes on the execution host',
  'MDM and EDR where supported, managed OS configuration, disk encryption, device identity, restricted administration and network egress establish the host baseline.',
  'These are enterprise controls. Crew is not an endpoint detection and response product. Protect the machine where execution happens; a remote Crew service does not govern independently launched laptop agents.',
  'Name the execution host and show its management, identity and network posture.',[]),
 layer('L0','OS sandbox','Crew + OS','Agent subprocess tree and descendants',
  'The sandbox wrapper confines agent processes using platform-native facilities. Linux and macOS have different implementations; credential-path visibility and environment handling are part of the launch boundary. A policy floor can require a minimum sandbox level.',
  'Inspect the effective launch posture for the exact OS and backend. Configuration, native backend sandbox ownership, unavailable facilities and explicit unconfined allowances affect the result. VM isolation is a separate outer boundary.',
  'Show the effective sandbox mode and one harmless denied access from inside the agent process.', ['sandbox.py','platform/governance.py']),
 layer('L1','Filesystem and protected configuration','Crew','Tool requests that reach the path gate',
  'Resolved-path checks protect sensitive reads and writes. A wider write-protected set covers configuration. Keystone files include policy and trust records that the agent must not be able to rewrite to authorize itself.',
  'Path checks mediate known file/tool paths. Shell, imported executables and independent host processes need OS-level confinement as well. A privileged host operator remains outside the agent threat boundary.',
  'Attempt a read of a synthetic protected path, then an attempted change to a protected policy or trust record.', ['security/paths.py','hooks.py','platform/governance.py']),
 layer('L2','Commands and exfiltration shapes','Crew','PreToolUse decisions over actual tool arguments',
  'The command gate evaluates denied operations, shell command forms and exfiltration checks before trust or approval shortcuts at that gate. Enterprise command pins and companion additions constrain operator-configurable rules.',
  'Built-in denied rules are default-on but configurable; do not describe the entire shipped catalog as an immutable floor. Suspicious bash patterns in the history scan are advisory, a different control from execution blocking.',
  'Use a harmless command shaped to match a known enabled deny rule and show the rule and decision.', ['security/denied_rules.py','security/exfil.py','platform/security_authority.py','hooks.py']),
 layer('L3','Input and response validation','Crew','Registered MCP schemas and API boundaries',
  'Registered schemas enforce types, bounded lengths, enum choices and normalization. Responses can be sanitized and truncated to limit oversized or malformed inputs and outputs.',
  'Coverage is per tool. In this nightly, some dispatchers pass unregistered tools to their handler without central schema validation; the computer-use dispatcher rejects unregistered tools. Validation is not authorization.',
  'Submit malformed arguments to a known schema-backed tool and show rejection before its handler runs.', ['validation.py','security_posture.py']),
 layer('L4','Output redaction','Crew','Covered human-facing and external output sinks',
  'Credential-pattern scanners, exfiltration-URL checks and streaming redaction reduce sensitive output at registered sinks. The posture registry identifies concrete coverage instead of a fixed marketing count.',
  'Pattern recognition is not general-purpose DLP and cannot guarantee detection of arbitrary secrets, encodings or semantic leakage. Coverage varies by sink; transport and downstream data controls remain necessary.',
  'Use fake credentials and a synthetic exfiltration URL; show the redacted result without handling real secrets.', ['security/redaction.py','security/exfil.py','security_posture.py']),
 layer('L5','Security Event Log','Crew + enterprise collector','Recorded security decisions and activity',
  'SEL stores structured events with an HMAC integrity chain. Its signing material is separated from the log directory, and rotated segments remain individually verifiable.',
  'A valid chain does not prove complete event capture, immutable retention or resistance to a fully privileged host compromise. Collector integration and external retention are separate deployment work. SSM port forwarding does not record tool payloads.',
  'Correlate a denied action with its SEL event, run verification, and identify what reaches the external collector.', ['sel.py','security_posture.py']),
 layer('G','Policy and profile governance','Crew','Cross-cutting ceiling and narrower session scopes',
  'Effective permissions compose Policy ∩ Profile. Profiles bind to relevant surfaces, apps or tasks and may narrow the policy ceiling. Scopes cover tools, MCP, commands, paths, channels, approval posture, sandbox floors, backend selection and capabilities.',
  'A policy declaration is meaningful only where its enforcer is connected. Backend admission and live session retirement are different operations. The presence of a governance scope alone does not prove a remote integration is deployed.',
  'Show policy explain for the same operation under two profiles and identify the limiting rule.', ['platform/governance.py','platform/governance_profiles.py','agent_backend_governance.py']),
 layer('A','Access and surface controls','Crew + access provider','Browser, dashboard, messaging and remote transport',
  'Dashboard token authentication, origin/CSRF checks and Host validation protect the browser-facing boundary. Messaging surfaces apply their own owner, user and origin checks. SSH/SSM or MicroVM endpoint authentication protects a separate transport boundary.',
  'Authorization to open a tunnel or port does not automatically become per-user Crew authorization or permission to call downstream tools. A logical conversation session is not necessarily a separate OS process.',
  'Show the entry identity, Crew session identity and downstream workload identity as three separate facts.', ['security_posture.py','messaging/session_trust.py']),
 layer('P','Approvals and backend enforcement','Crew + selected backend','Permission callbacks and pre-tool hooks',
  'Crew brokers approval decisions for requests that reach its boundary. Its hard path, command and governance decisions precede approval/trust shortcuts there. Managed backend configuration also removes unsafe gate-skipping approval entries where applicable.',
  'Native backend auto-approval can execute without a Crew permission callback. An observational tool event received after execution is not a prevention point. Rehearse enforcement with the actual backend, version and launch settings.',
  'Demonstrate allow, ask and deny on the chosen backend, then explain which event occurs before execution.', ['hooks.py','platform/governance.py']),
 layer('C','Credentials and environment','Crew + OS + IAM','Process launch and service authority',
  'Launch handling scrubs sensitive inherited environment variables and sandbox policy limits access to credential locations. Internal credential access follows explicit privileged paths. External MCP services should use narrowly scoped workload identities.',
  'A per-session IAM role is still usable by code that can obtain its credentials. An unprivileged Unix user does not by itself isolate an EC2 instance profile. Do not put control-plane or broad target-system authority in the agent environment.',
  'Inspect environment names and role permissions without printing credential values.', ['sandbox.py','hooks.py','security/paths.py']),
 layer('R','Resource protection','Crew + OS + cloud runtime','Process, memory and descriptor usage',
  'Launch wrappers can apply Linux cgroup process/memory bounds and resource limits. Cloud compute sizing, runtime ceilings and task termination add separate outer limits.',
  'Availability and strength are platform dependent. Resource bounds reduce exhaustion; they do not authorize a tool operation or guarantee that a provider billing budget is enforced.',
  'Show configured limits and the effective host mechanism; use a small controlled resource exercise.', ['sandbox.py']),
 layer('T','Project skill trust and agent context','Crew + operator','Project-supplied skills, memory and steering',
  'Project skill loading has a consent record tied to the canonical project directory, stored in the protected trust area. Memory, steering, lessons and skills then supply context to the selected backend.',
  'Consenting to load a skill is not proof its instructions are safe. Skills, plans and memory are not ACLs; prompt injection remains a reason to enforce the lower execution layers.',
  'Open an untrusted sample project and show the project-skill trust decision.', ['skill_trust.py']),
 layer('X','Apps, hooks and unattended work','Crew','Gateway services and extension capabilities',
  'App manifests declare permissions checked at installation and runtime. Governance capabilities cover script hooks, spawning, memory writes, browsing, cron, messaging and other extensions. These constrain the Gateway services that keep work running.',
  'A workflow, scheduler or subagent does not automatically create a new host isolation boundary. Each dispatch path and extension must honor the applicable permissions and runtime controls.',
  'Show one disabled capability and an app permission declaration, then a blocked attempt through that path.', ['apps/permissions.py','hooks.py','platform/governance.py']),
 layer('M','MCP and target-service governance','External + Crew','Routed remote calls and target APIs',
  'Crew governs known MCP references where its checks apply. A separately deployed LiteLLM/MCP tier can add caller authentication, server/tool grants and service credentials; target AWS IAM or SaaS authorization then decides whether the resource action is allowed.',
  'The proposed external gateway governs only traffic routed through it. Direct shell/SDK/network access needs separate confinement. Caller OAuth identity and downstream AWS workload credentials are not interchangeable.',
  'Demonstrate gateway tool denial separately from downstream IAM denial.', ['platform/governance.py']),
]
catalog={'title':'KiroCrew endpoint and governance control map','baseline':'0.7.0.dev20260911060948','commit':rev,'baselineNote':'Diagram and source-link baseline: verified September 11 nightly. The local rehearsal uses the separately fingerprinted user-installed September 12 nightly; see continuation evidence.','layers':layers}
(base/'kirocrew-control-layers.json').write_text(json.dumps(catalog,indent=2)+'\n')

esc=html.escape
cards=[]
for l in layers:
 sources=' · '.join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["label"])}</a>' for s in l['sources']) or 'Proposed enterprise host baseline; not a Crew feature.'
 cards.append(f'''<article class="control" data-code="{l['code']}"><div class="control-head"><span class="code">{l['code']}</span><div><h2>{esc(l['title'])}</h2><p class="owner">{esc(l['owner'])} · {esc(l['scope'])}</p></div></div><p>{esc(l['body'])}</p><details><summary>Enforcement limits and demo proof</summary><p>{esc(l['limit'])}</p><p><strong>Show live:</strong> {esc(l['demo'])}</p><p class="sources">{sources}</p></details></article>''')
security=base64.b64encode((base/'kirocrew-security-layers-browser.html').read_bytes()).decode()
aws=base64.b64encode((base/'kirocrew-aws-deployment-browser.html').read_bytes()).decode()
page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KiroCrew · Endpoint and AWS governance</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:#18283d;font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}header{padding:14px 24px;background:#10243b;color:#fff;display:flex;gap:20px;align-items:center;justify-content:space-between;flex-wrap:wrap}h1{font-size:18px;margin:0}.strap{font-size:12px;color:#bbccde;margin:5px 0 0}nav{display:flex;gap:7px;flex-wrap:wrap}button{font:inherit;font-size:13px;border:1px solid #5e7790;background:transparent;color:#fff;border-radius:6px;padding:9px 14px;cursor:pointer}button[aria-selected=true]{background:#ecf5ff;color:#10243b;border-color:#ecf5ff}button:focus-visible,summary:focus-visible,a:focus-visible{outline:3px solid #efb73e;outline-offset:3px}.panel[hidden]{display:none}iframe{display:block;border:0;width:100%;height:calc(100dvh - var(--header-h,95px));min-height:650px;background:white}.reference{max-width:1180px;margin:auto;padding:28px 24px 60px}.intro{max-width:900px;line-height:1.65;margin:0 0 22px}.intro h2{font-size:24px;margin:0 0 8px}.note{padding:15px 18px;border-left:4px solid #9d682c;background:#fff6e7;line-height:1.6;margin:18px 0}.controls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.control{background:white;border:1px solid #dce4ee;border-radius:10px;padding:21px;line-height:1.6}.control-head{display:flex;gap:12px;align-items:flex-start}.code{background:#e5efff;color:#244b82;min-width:40px;padding:5px 6px;border-radius:6px;font-weight:700;text-align:center}.control h2{font-size:17px;margin:0}.owner{font-size:12px;color:#50667f;margin:4px 0 0}.control p{font-size:14px}.control details{border-top:1px solid #e6ebf2;padding-top:12px}.control summary{font-size:13px;font-weight:600;cursor:pointer;color:#24517f}.sources{font-size:11px!important;overflow-wrap:anywhere}a{color:#245b91}.reference footer{font-size:12px;line-height:1.7;margin-top:24px;color:#526980}.reference h3{font-size:17px;margin-top:28px}.switches{margin:12px 0 20px}.switches button{color:#244b82;border-color:#a8bbd0;background:white}table{width:100%;border-collapse:collapse;font-size:14px;background:white}th,td{text-align:left;border-bottom:1px solid #dce4ee;padding:12px;vertical-align:top}th{background:#e8eff7} @media(max-width:760px){header{padding:12px 16px;gap:12px}h1{font-size:16px}.controls{grid-template-columns:1fr}.reference{padding:22px 16px}nav button{padding:8px 10px}.control{padding:17px}}
</style></head><body><header id="top"><div><h1>KiroCrew · Endpoint and AWS governance</h1><p class="strap">Security layers → deployment → live evidence</p></div><nav role="tablist" aria-label="Diagram views"><button id="tab-security" role="tab" aria-selected="true" aria-controls="security" data-view="security">Security layers</button><button id="tab-aws" role="tab" aria-selected="false" aria-controls="aws" data-view="aws">AWS deployment</button><button id="tab-reference" role="tab" aria-selected="false" aria-controls="reference" data-view="reference">Controls &amp; demo proof</button></nav></header>
<main><section class="panel" id="security" role="tabpanel" aria-labelledby="tab-security"><iframe id="security-frame" title="Archify endpoint protection and Crew security layers"></iframe></section><section class="panel" id="aws" role="tabpanel" aria-labelledby="tab-aws" hidden><iframe id="aws-frame" title="Archify proposed AWS deployment with service icons"></iframe></section><section class="panel reference" id="reference" role="tabpanel" aria-labelledby="tab-reference" hidden>
<div class="intro"><h2>What stops an agent action?</h2><p>The single endpoint box is the execution host. Its internal bands separate enterprise host protection, Crew runtime, local policy enforcement and the six security layers. Follow its external connections to central policy, MCP governance and target authorization. The six numbered layers are Crew’s documented security model. The surrounding controls cover identity, governance, extensions and host management. This is a control map, not a promise that every route runs every check.</p><p><strong>Execution location:</strong> In local mode the host is the developer endpoint. In remote mode it is the EC2 host or proposed per-session MicroVM. Independent laptop agents remain outside a remote Crew service.</p></div>
<div class="note"><strong>Two verified baselines:</strong> The accepted control map and source links use 0.7.0.dev20260911060948 · fa0d8cf3c241. The live rehearsal uses installed nightly <strong>0.7.0-nightly.20260912t060850</strong>, with packaged file hashes recorded. The nightly feed remains unavailable; “latest” is user-reported. Exact effective settings still require the actual backend and host diagnostics.</div>
<div class="switches"><button id="expand-controls">Expand all control details</button><button id="collapse-controls">Collapse details</button></div><div class="controls">__CARDS__</div>
<h3>Retained MicroVM alternative</h3><p class="note">Historical design discussion. These fast-changing service limits were not refreshed in this continuation. Reverify the linked AWS documentation before selecting this alternative.</p><p class="intro">A proposed session broker can launch a MicroVM containing Crew Gateway, the selected backend and workspace together. Keep central policy and privileged MCP services outside that session. This is additional integration work, not a verified native Crew deployment.</p><table><thead><tr><th>Property</th><th>Design implication</th></tr></thead><tbody><tr><td>Firecracker isolation per MicroVM</td><td>Use one MicroVM per isolated session. It does not create a separate trust boundary between Crew and agent processes inside the same VM.</td></tr><tr><td>Public, token-authenticated endpoint</td><td>WebSocket/SSE support can serve interactive flows. VPC egress does not make ingress private; this is a decision gate for the private-only design.</td></tr><tr><td>Eight-hour maximum lifetime</td><td>Includes suspended time. Save durable work externally and implement session recovery.</td></tr><tr><td>Snapshot and resume hooks</td><td>Initialize identity and credentials after launch; refresh credentials, connections and policy before resumed work. Configure idle behavior for background tasks.</td></tr></tbody></table>
<p class="sources"><a href="https://docs.aws.amazon.com/lambda/latest/dg/lambda-microvms-guide.html" target="_blank" rel="noopener">MicroVM overview</a> · <a href="https://docs.aws.amazon.com/lambda/latest/dg/microvms-launching.html" target="_blank" rel="noopener">Lifecycle and ingress</a> · <a href="https://docs.aws.amazon.com/lambda/latest/dg/microvms-networking.html" target="_blank" rel="noopener">Network connectors</a></p>
<h3>Ready-to-present walkthrough</h3><p class="intro">Open the <a href="output/kirocrew-demo.pptx">seven-slide deck</a> and <a href="WALKTHROUGH.md">presenter runbook</a>. Locate the execution host, explain ownership and the proposed MCP/AWS boundaries, then run <code>./demo.sh --interactive</code>. The rehearsal exercises actual installed Crew functions with synthetic requests: allow, presenter approval, deny, protected path, command classification, Policy ∩ Profile, redaction and SEL integrity. The approval UI and handler are supplied by the harness. Backend callback delivery, MCP grants and IAM denial require separate end-to-end evidence.</p>
<footer>Source basis: pinned nightly wheel implementation, including security_posture.py, hooks.py, sandbox.py, governance.py, validation.py, sel.py and skill_trust.py; <a href="https://github.com/kirodotdev/KiroCrew/blob/main/docs/architecture/security-deep-dive.md" target="_blank" rel="noopener">current security architecture</a> supplied the six-layer naming. Browser derivatives preserve the accepted SVGs byte-for-byte. Both passed Archify’s nine static checks and four desktop viewport checks; the integrated viewer passed tab, keyboard, theme, focus and PNG/SVG export checks. The local harness passed against installed September 12 nightly modules. Cloud deployment remains proposed. AWS service icons remain embedded in the deployment view.</footer>
</section></main><script>
const sources={security:'__SECURITY__',aws:'__AWS__'};
const loaded=new Set();
function loadView(id){if(!sources[id]||loaded.has(id))return;const bytes=Uint8Array.from(atob(sources[id]),c=>c.charCodeAt(0));document.getElementById(id+'-frame').srcdoc=new TextDecoder().decode(bytes);loaded.add(id)}
function showView(id){if(!['security','aws','reference'].includes(id))id='security';document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==id);document.querySelectorAll('[data-view]').forEach(b=>{b.setAttribute('aria-selected',String(b.dataset.view===id));b.tabIndex=b.dataset.view===id?0:-1});loadView(id);history.replaceState(null,'','#'+id)}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
document.querySelector('nav[role=tablist]').addEventListener('keydown',e=>{const tabs=[...document.querySelectorAll('[data-view]')];let i=tabs.indexOf(document.activeElement);if(i<0)return;if(e.key==='ArrowRight')i=(i+1)%tabs.length;else if(e.key==='ArrowLeft')i=(i+tabs.length-1)%tabs.length;else if(e.key==='Home')i=0;else if(e.key==='End')i=tabs.length-1;else return;e.preventDefault();showView(tabs[i].dataset.view);tabs[i].focus()});
document.getElementById('expand-controls').addEventListener('click',()=>document.querySelectorAll('.control details').forEach(d=>d.open=true));
document.getElementById('collapse-controls').addEventListener('click',()=>document.querySelectorAll('.control details').forEach(d=>d.open=false));
new ResizeObserver(entries=>document.documentElement.style.setProperty('--header-h',entries[0].target.getBoundingClientRect().height+'px')).observe(document.getElementById('top'));
window.addEventListener('hashchange',()=>showView(location.hash.slice(1)||'security'));
showView(location.hash.slice(1)||'security');
</script></body></html>'''
page=page.replace('__CARDS__',''.join(cards)).replace('__SECURITY__',security).replace('__AWS__',aws)
(base/'kirocrew-aws-remote.html').write_text(page)

notes=['# KiroCrew endpoint protection and governance layers','',catalog['baselineNote']+' Build: `'+catalog['baseline']+'`; commit `'+rev+'`.','',
 'The updated visual has three tabs: **Security layers**, **AWS deployment**, and **Controls & demo proof**. The AWS view retains its service icons. The security view groups endpoint control into one host panel: an enterprise protection band, the managed runtime, the policy ceiling, six L0–L5 rows, and cross-cutting controls. Four outside actors keep entry identity, central policy, MCP governance and target authorization distinct.','',
 'The diagram shows control relationships, not a guaranteed chronological pipeline. A backend may execute a tool without sending a Crew permission request, and an event observed after execution cannot prevent that action. Managed configuration attempts to close gate-skipping paths where supported; prove the actual behavior on the demo host.','']
for l in layers:
 notes += ['## '+l['code']+' · '+l['title'],'','Owner: '+l['owner']+'. Scope: '+l['scope']+'.','',l['body'],'',l['limit'],'','Demo: '+l['demo'],'']
 if l['sources']:notes += ['Sources: '+', '.join('['+s['label']+']('+s['url']+')' for s in l['sources']), '']
notes += ['## AWS deployment and MicroVM alternative','',
 'The existing EC2 + SSM diagram is included in the second tab. It remains a proposal, including the S3-to-protected-file policy sync and optional LiteLLM/MCP tier.','',
 'For a MicroVM alternative, place Crew Gateway, backend and workspace together inside each session VM. Add a session broker outside it. Public authenticated ingress, the eight-hour lifetime including suspension, durable state and safe run/resume hooks must be addressed. VPC egress is not private ingress. This integration has not been tested.','',
 '[MicroVM lifecycle](https://docs.aws.amazon.com/lambda/latest/dg/microvms-launching.html) · [Networking](https://docs.aws.amazon.com/lambda/latest/dg/microvms-networking.html)','',
 '## Validation','',
 'The browser derivatives passed nine Archify static checks and browser containment at 1440×900, 1600×1000, 1920×1080 and 2048×1320. The integrated viewer passed both diagram themes, all three tabs, keyboard activation, focus/search, presentation mode and PNG/SVG export. The reference intentionally scrolls vertically. Original SVGs are unchanged; the reader layout was adapted in separate browser derivatives. Historical static/subagent review receipts retain their original scope. See evidence/browser/integrated-browser-receipt.json and kirocrew-continuation-notes.md. The wrapper remains a separate integration artifact.','',
 '## Historical AWS walkthrough (retained; current evidence is in the continuation section)','', (base/'kirocrew-aws-deployment-notes.md').read_text()]
manual_file=base/'kirocrew-continuation-notes.md'
manual=manual_file.read_text() if manual_file.exists() else ''
accepted_notes=base/'evidence/accepted/kirocrew-aws-remote-notes.md'
prior=accepted_notes.read_text() if accepted_notes.exists() else ''
endpoint_receipt='## Endpoint visual revision receipt'
retained='\n\n'+endpoint_receipt+prior.split(endpoint_receipt,1)[1] if endpoint_receipt in prior else ''
(base/'kirocrew-aws-remote-notes.md').write_text('\n'.join(notes)+'\n'+retained+'\n'+manual)
print('Built three-view diagram and '+str(len(layers))+' control reference entries.')
