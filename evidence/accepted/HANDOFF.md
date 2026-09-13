# KiroCrew demo — Codex continuation

## Goal

Continue this existing project. Prepare a short slide-to-live-demo walkthrough for a security and governance audience. Present KiroCrew as a governance layer around managed coding-agent execution, supporting Kiro CLI, Codex and Claude Code as backend choices. Noah is a Principal AWS Engineer; assume senior AWS/IAM fluency. Write plainly and use the installed No AI Slop skill when available.

The original demo sequence is:
1. Briefly explain what KiroCrew is.
2. Show its security controls.
3. Distinguish server-side and client/endpoint controls.
4. Explain MCP tools and services as further enforcement points.
5. Research MCP/tool governance, including LiteLLM OAuth and enterprise IAM integration.
6. Show a remote Crew service as a central control point, using AWS infrastructure.
7. Move from those slides into concrete live evidence.

This handoff transfers project files and decisions. It does not transfer the original conversation, credentials, connected apps, tool permissions or running processes. No AWS deployment has been performed.

## Current deliverable

Open `kirocrew-aws-remote.html`. It is self-contained and contains three views:
- Security layers: one detailed endpoint-control enclosure, with an enterprise host-protection band, Gateway/backend/tool runtime, Policy ∩ Profile, L0–L5, and cross-cutting controls.
- AWS deployment: the existing EC2 + SSM proposal, with embedded AWS service icons.
- Controls & demo proof: 15 control groups, limitations, pinned source links, and demonstration suggestions.

The latest accepted design request was: make endpoint control one box, add visual detail without clutter, then have a subagent review it. This is complete. Preserve that layout; do not split the endpoint back into many floating control boxes.

The visual and reference are developed. A completed PowerPoint deck and a rehearsed executable demo have NOT been delivered. The reference includes a proposed slide-to-demo sequence, not proof of a working live demo.

## Evidence baseline and unresolved freshness

Verified retained nightly: `0.7.0.dev20260911060948`.
Pinned commit: `fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482`.
The user requested latest-nightly documentation, but the current release feed could not be refreshed in the prior environment. Do not describe this retained build as the latest release without new verification.

`crew-security-evidence/` contains selected extracted implementation modules used in the prior review. It is not a complete source checkout or the original wheel. Source links are in the control catalog and notes. Reacquire the full build from an authorized official source if execution or full-version verification is needed.

The previous environment rejected access to the nightly feed and some pinned documentation URLs. Do not bypass a tool's access denial through another transport. If access remains unavailable, retain the pinned baseline and state that limitation.

## Security distinctions to preserve

- The endpoint box denotes the EXECUTION HOST. Locally this is the developer endpoint. Remotely it contains Crew Gateway, selected backend and workspace together. A remote service does not govern independently launched laptop agents.
- Enterprise EDR/MDM, OS hardening, disk encryption and network controls are external controls; Crew is not EDR. Availability depends on the host/runtime.
- L0: platform/backend-dependent OS sandbox around agent descendants.
- L1: resolved-path and protected-configuration checks.
- L2: command deny and exfiltration checks. L1/L2 prevention requires a pre-execution Crew hook or permission callback. Native backend auto-approval can skip that boundary; observed post-execution events are not preventive enforcement.
- L3: validation of registered tool schemas, not universal tool validation.
- L4: credential/URL-pattern redaction at covered sinks, not complete DLP.
- L5: SEL events with HMAC-chain verification, not complete capture or immutable audit retention.
- Effective policy is Policy ∩ Profile. Built-in command rules are configurable; managed policy pins and companion additions establish the managed floor. Advisory history scanning is different from blocking a command.
- Skills, steering and memory supply context, not authorization. Project-skill trust, app permissions, backend admission, credentials and resource limits are separate controls.
- Transport access, Crew identity, MCP service grants, and target IAM/OAuth are distinct decisions. Only routed MCP calls encounter the proposed external MCP gateway.
- LiteLLM integration and central policy distribution remain proposed integrations. Do not depict them as tested native Crew capabilities.

## AWS design decisions

The retained deployment uses a private EC2 execution host, SSM access, EBS state, a proposed privileged S3-to-protected-file policy sync, external collection, optional MCP/Fargate services, egress controls, and independent target IAM.

Crew runs unprivileged. The policy-sync adapter must own and protect the policy file and its ancestor directories against the Crew user. Do not imply native S3 policy fetching. Keep broad control-plane credentials away from agent processes; a Unix user boundary alone does not isolate an EC2 instance profile.

The Lambda discussion concerned a proposed per-session Lambda MicroVM alternative, not a verified replacement. The retained reference records public token-authenticated ingress, VPC egress versus private ingress, an eight-hour lifetime including suspension, durable checkpoints and safe initialization/resume. Reverify all rapidly changing AWS specifics before recommending or implementing it. Managed Instances and MicroVMs are different options. Neither alternative has been deployed here.

## Files and authoring workflow

- `kirocrew-aws-remote.html`: current integrated viewer.
- `kirocrew-aws-remote-preview.png`: accepted light security preview.
- `kirocrew-security-layers-dark-preview.png`: dark preview.
- `kirocrew-aws-remote-notes.md`: research/control notes and demo guidance.
- `kirocrew-control-layers.json`: 15-control reference catalog.
- `kirocrew-security-layers.architecture.json`: accepted Archify geometry/topology.
- `kirocrew-security-layers-base.html`: unchanged accepted Archify base.
- `detail-endpoint-panel.py`: adds the detailed endpoint SVG inside a single component to create `kirocrew-security-layers.html`.
- `build-security-viewer.py`: embeds security/AWS HTML and generates the control reference and notes.
- `export-security-preview.cjs`: renders light/dark previews with Sharp.
- `kirocrew-aws-deployment.html`: retained AWS diagram, with icons.
- `kirocrew-endpoint-review.json`: completed subagent review and resolution.
- `kirocrew-aws-remote-receipt.json`: previous artifact hashes and check scopes.
- `history/reviewed-source-snapshot.zip`: exact previous source bundle before portability changes.

The Archify package is included at `archify-source/archify/`; revision `c1443b31b496eebf4a68bf83151816c955ddb796`. Read its `SKILL.md` before editing diagrams. Its license is included. AWS icon provenance is in `kirocrew-aws-icons.json`.

Transfer-only changes: the two preview scripts now use `require('sharp')` instead of an absolute path in the prior runtime. `package.json` pins Sharp to the previously available version, 0.35.4. The displayed HTML and previews have not changed. Prior receipts describe the prior artifacts; `TRANSFER-MANIFEST.json` fingerprints this bundle.

Use Node.js and Python 3. Run `npm install` to install the pinned preview dependency if needed. Python authoring scripts use the standard library. The standalone HTML can be viewed without rebuilding.

Typical security diagram edit:
1. Read the Archify skill. Edit/validate the architecture source as required.
2. Deliver the accepted source to `kirocrew-security-layers-base.html` and retain the receipt.
3. Run `python3 detail-endpoint-panel.py`.
4. Check `kirocrew-security-layers.html` with Archify.
5. Run `npm run preview:security` and `npm run preview:security:dark`.
6. Run `python3 build-security-viewer.py`.
7. Inspect both themes and the actual integrated viewer; obtain a bounded subagent review after meaningful visual edits.

CAUTION: `add-aws-icons.cjs` and `export-aws-preview.cjs` are older scripts that target the integrated viewer/preview filenames. Adapt their paths to the dedicated AWS files before running them, or they will overwrite the current viewer/security preview. `build-security-viewer.py` also regenerates notes, so preserve any manually appended review/receipt sections. `package-kirocrew-visual.py` contains an intentional checksum assertion for the retained AWS view; revise that baseline only after an intentional AWS edit and review.

## Completed validation

The Archify base and displayed diagrams passed nine static artifact checks with zero composition errors or warnings. Viewer JavaScript syntax and exact embedding were checked. A subagent inspected both light and dark previews, source and reference; its minor legend inconsistency was fixed and re-reviewed. No blocking findings remained.

Chromium was unavailable. Actual browser interactions, responsive containment and focus/export behavior are still UNVERIFIED. Static previews are SVG rasterizations, not browser screenshots. Read the included receipts; do not turn static success into a browser or deployment claim.

## Recommended next work

First inspect this handoff, the current viewer, notes and receipts. Establish the local working environment without changing the accepted visual. Use the existing folder as the project; no new architecture is required.

Then close the browser-validation gap on macOS using an available supported browser. Verify the three tabs, both themes, controls, and desktop layouts required by Archify. Obtain fresh nightly evidence through permitted official access and update only documented differences. Finally finish a brief slide sequence and runnable live-demo checklist with harmless synthetic allow/ask/deny, path protection, redaction and SEL evidence. Distinguish Crew denial, MCP denial and IAM denial.

These are next-work recommendations from the existing goal, not proof those activities are already done. Do not deploy AWS resources, publish externally or use real secrets without authorization for that work.
