# KiroCrew demo — managed EC2 controls and native recordings

> Current state: Read the [managed demo guide](docs/MANAGED-DEMO.md) and its linked status before running this demo. The root-owned policy and fresh native managed-denial test supersede the earlier configuration described below. Historical results and unfinished host cases retain their recorded scope.

The current Mac client uses the EC2 Gateway with its local Gateway off. The original Kiro CLI is authenticated, and fresh managed-policy turns verified a permitted MCP read and an automatic MCP denial. The delivered presentation has 16 slides and nine recordings; the separate admin tour has 10 stops and 26 screenshots. The [project skill](.agents/skills/kirocrew-demo/SKILL.md) covers dependencies, setup, presentation and recording. Use [current-status.json](evidence/native-client-demo/current-status.json) for the final artifact and validation bindings.

## Earlier deployment notes — historical

The sign-in failures and unfinished results below describe their original observation times. They do not override the current status above.

Updated September 13, 2026. The user authorized actual EC2 backend/MCP/AWS enforcement through CloudFormation, inbound access only from their IP, primary AWS MCP in us-east-1, and the subsequent ARM upgrade. The presentation work includes an updated deck and Archify, exact Grok 4.6 xhigh / Opus 5 xhigh council review, then no-ai-slop editing. The historical no-cloud authorization statements below are superseded. The preceding accepted handoff is preserved at `evidence/accepted-before-ec2/HANDOFF.md`.

Fresh read-only AWS verification at 14:22 UTC found stack `kirocrew-demo-20260913` UPDATE_COMPLETE in us-east-1. Active instance `i-0fde6de3f0ea5a9d0` is running: t4g.xlarge, ARM64, 4 vCPU / 16 GiB RAM, Ubuntu 24.04, standard CPU credits and 40 GiB encrypted gp3. Its observed public IP is `100.61.173.192` and may change after stop/start. Original x86 instance `i-020eb373045b56586` is stopped with no public IPv4; its 24 GiB encrypted gp3 root remains for rollback. Both attach only `sg-08ac4789794115e39`, whose sole ingress is TCP 22 from `24.60.107.229/32`. Evidence: `evidence/aws/arm-20260913/final-cloud-verification.json`.

The 14:57 UTC `evidence/aws/arm-20260913/final-network-readback.json` confirms that `24.60.107.229` is still the client's current public IPv4 and that the security group has only its SSH `/32` rule. Gateway, MCP and the observability app gained no public ingress.

The Mac desktop is connected to ARM with `runLocalGateway=false` and no local 5476 listener. The owner dashboard and remote workspace `/srv/kirocrew-demo/workspace` were observed through port 5599, including a successful normal desktop quit/relaunch and owner-token refresh. `remoteHosts["5599"]` now uses `kirocrew-demo-admin` and `/usr/local/bin/kirocrew-owner-token`; the independent tunnel still uses the unprivileged `kirocrew-demo` alias. Both use the pinned ARM host identity. The reviewed helper enters the verified Gateway mount namespace, then drops to crew for the stock token operation. It adds no Crew sudo rights and patches no Nightly code. Current evidence: `evidence/aws/arm-20260913/client-runtime-receipt.json`; source review: `owner-bootstrap-review.json` in that directory. No local IAM keys or existing coding-backend sessions were transferred.

The ARM direct MCP/AWS probe passed at 14:07 UTC: authentication 401, fixed four-tool catalog, allowed S3 read/digest, MCP tool-grant denial before AWS dispatch, and S3 IAM AccessDenied HTTP 403 with AWS request ID. See `evidence/aws/arm-20260913/mcp-live-receipt.json`. The same demo bucket and fixture evidence are retained. The separate MCP UID uses the instance role. At 14:56 UTC, a TCP-only connection from Crew to IPv4 IMDS was denied immediately with errno 113; no HTTP request, metadata token or credential was read. `crew-imds-connect-receipt.json` records that host boundary. It does not establish IPv6 behavior or native sandbox execution.

The exact walkthrough MCP command passed again at 15:01:37 UTC after telemetry deployment. `evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json` records fresh trace/AWS request IDs, `passed: true` and `native_crew_backend_verified: false`; the 14:07 receipt remains the initial ARM baseline.

**Unfinished:** standalone Kiro CLI authentication, a completed native backend turn, native approval/hook/SEL correlation and actual sandbox execution. Kiro CLI is explicitly selected for new sessions. Its own authentication check is false, and the native ACP log records exit code 1 with the message that the CLI is not logged in. The dashboard's GitHub card reads the separate KAS identity store. The latest normal CLI login ended with exit code 1 without an authenticated account; the 15:19 UTC readback confirms the CLI is still signed out and both callback listeners are gone. See `evidence/aws/arm-20260913/native-cli-login-outcome.json`. When ready to complete sign-in, run `python3 scripts/ec2-login.py` for a fresh URL and keep the terminal open until it confirms the EC2 CLI result. Earlier x86 login receipts remain historical. Never copy credential/session databases or put owner-token or OAuth URLs in project receipts.

Native Gateway telemetry is enabled with a 10-second flush interval, seven-day retention and a 64 MiB retention target. OTLP is empty; anonymous product reporting is off in configuration and by the environment opt-out. The custom Mac and EC2 collectors run every 60 seconds, retain 240 samples per source and 200 fixed collection events, and exclude arbitrary logs, prompts and credentials. Demo Observability App Kit `1.0.1` reads both sources through the authenticated owner proxy and binds to `127.0.0.1:9102`. Data is `root:crew`, directory `0750`, files `0640`; Crew can read it and cannot write it. API readback and actual browser captures passed. See `evidence/aws/arm-20260913/observability-runtime-receipt.json` and `observability-api-readback.json`.

The controlled desktop quit produced a stopped-client sample and warning at 14:44:42 UTC; the recovery sample after relaunch is timestamped 14:49:34 UTC. These are sample times, not exact UI-action times. Gateway PID 4991 and its 14:26:10 UTC start identity stayed unchanged, and server checks stayed healthy. A fresh sample can report an unhealthy desktop, so read the checks alongside the Current badge. This collection-event stream is separate from Crew's security audit events.

The Crew deny configuration remains writable by crew. It demonstrates a configured demo rule without establishing immutable centrally managed policy. The custom MCP service has fixed bearer grants and is separate from LiteLLM/OAuth. The passing direct MCP probe does not prove native Crew prevention. SSM transport, central policy distribution, EDR and durable external SEL retention remain enterprise proposals.

The installed Mac client is `0.7.0-nightly.20260913t061222`; its baseline receipt is `evidence/nightly/client-20260913-verification.json`. All 24 selected packaged modules match their RECORD entries, and three differ from September 12. ARM remains a custom Linux repack of frozen `0.7.0-nightly.20260912t060850`, with hash-locked ARM64 dependencies and native libraries, plus official Kiro CLI 2.21.4. `evidence/aws/arm-20260913/runtime-preparation.json` records provenance; `source-verification.json` confirms all 24 selected server modules match that frozen baseline and are root-owned. No official Linux nightly artifact or source SHA is claimed. Preserve the single endpoint-control box and all historical accepted visuals and receipts.

Current deliverables are the 12-slide `output/kirocrew-arm-observability-demo.pptx` and companion copy, `output/kirocrew-admin-walkthrough.html` / `.md`, `output/kirocrew-admin-findings.md`, and 13 original CUA JPEGs under `output/admin-console/`. `WALKTHROUGH.md` runs from the brief slides to the live portal, direct MCP/S3 probe and pending native sequence. New diagrams are `kirocrew-arm-live.html`, `kirocrew-arm-observability.html` and `kirocrew-arm-slide.html`. Current resource/cost notes are in `kirocrew-ec2-notes.md`, operations in `infrastructure/RUNBOOK.md`, and the ARM template in `infrastructure/ec2-demo.json`. `native-demo.sh` uses the installed Nightly Python and reviewed administrator owner helper. Initial x86 presentation files and their receipts remain historical.

For the initial x86 edition, Grok 4.6 xhigh through Grok Build and Opus 5 xhigh through Claude Code reviewed all nine candidate-v3 images plus text/notes. Both requested changes. Accepted decisions in `evidence/council/candidate-v3/DECISIONS.md` were incorporated before the requested no-ai-slop edit. The final nine-slide deck passed package, layout, font-policy and exact-file import checks, followed by author inspection of all nine renders. Council scope remains candidate-v3; no final-byte council approval or ARM-edition review is claimed. See `evidence/slides/kirocrew-ec2-demo/`.

The new ARM architecture, observability and slide diagrams passed all nine static checks each and received light-theme raster review. Browser validation was unavailable because CUA's local-file access policy blocked those diagram URLs and the portable admin guide. See `evidence/aws/archify-arm/council-delivery-receipt.json` and `evidence/admin-console/browser-receipt.json`. This gap is separate from the passing live owner-portal/browser observations. Earlier x86 browser/theme/export receipts retain their original scope; the accepted endpoint image and security reference remain intact.

Fresh Grok 4.6 and Opus 5 review completed for the frozen 12-slide ARM candidate-v2, SHA-256 `99d10eee8723b3998c40f52e902602661138e7388f0d6d3db8e2d5ef13f63dd9`. Both returned CHANGES REQUIRED. The dispatcher verified all 12 image payloads and exact packet bytes. Both used explicit xhigh launch settings; provider-internal effort is not independently visible. `evidence/council/arm-observability-v1/council-verified-receipt.json`, `council-synthesis.md` and `DECISIONS.md` record the review and accepted revisions. All accepted changes were incorporated, then the full deck and notes received the no-ai-slop edit. No final-byte council approval is claimed.

The final ARM PPTX is SHA-256 `37c82c82a00f16694f82fd11d2eda4c6188ce49de233b0c52448c47b820e0c13`. In `evidence/slides/kirocrew-arm-observability-demo/`, `council-incorporation.json` binds accepted decisions to those bytes; `no-ai-slop.md` records the subsequent edit; `finalization.json` records passing package, geometry, font, editable-table and exact-file import checks. `embedded-image-checks.json` preserves the original reference/screenshot bytes, and `visual-review.json` records author inspection of all 12 final renders. Native PowerPoint playback is not claimed. `WALKTHROUGH.md` matches all 12 final slide titles.

`ARM-CONTINUATION-RECEIPT.json` is the final manifest for the ARM source, runtime receipts, guide and deck. `EC2-CONTINUATION-RECEIPT.json` binds the preceding x86 continuation; the original `CONTINUATION-RECEIPT.json` also remains historical. The AWS Knowledge MCP plugin was uninstalled, and fresh configuration inspection still shows primary aws-mcp enabled for us-east-1. Current-process tool registrations remain stale until restart. Initial provisioning used `scripts/aws-mcp-client.py` for that reason.

ARM compute costs $0.1344/hour plus $0.005/hour public IPv4. Its 40 GiB gp3 root costs $3.20/month; the stopped x86 rollback host adds $1.92/month for 24 GiB gp3. At 730 running hours the combined base is about $106.88/month, before model use, S3, transfer, telemetry and tax. With both hosts stopped, their volumes remain about $5.12/month. The lifecycle helper targets ARM and defaults to dry-run. Do not stop an active demo or login. Full stack deletion removes both hosts and root volumes; only the S3 bucket and policy have explicit retention.

For operations, native Privacy controls, custom collector schedules and the App Kit backend have separate pause/resume controls in the runbook. The cloud helper does not stop the Mac collector. For a newly prepared host, apply `infrastructure/set-demo-telemetry.py` after initial demo configuration, then load the settings in the Gateway. It preserves other sections. Do not rerun initial configuration or replace existing configuration/token files on the live host.

## Historical accepted handoff

Updated September 12 EDT / September 13 UTC, 2026. The browser validation, installed-nightly verification and brief slides-to-live-demo walkthrough are complete within the evidence scopes below. No AWS resources were deployed. The original handoff is retained at `evidence/accepted/HANDOFF.md`.

## Ready-to-use deliverables

- `output/kirocrew-demo.pptx`: seven slides with presenter notes and sources.
- `kirocrew-aws-remote.html`: self-contained Security layers, AWS deployment and Controls & demo proof views.
- `WALKTHROUGH.md`: approximately six-minute sequence, exact commands, expected outcomes and end-to-end follow-on checks.
- `demo.sh`: use `--interactive` for the synthetic write approval, or no argument for a complete scripted preflight.
- `kirocrew-continuation-notes.md`: current research, nightly differences and evidence boundaries. Generated full notes also append this section.
- `CONTINUATION-RECEIPT.json`: final artifact hashes and receipt references. Historical receipts retain their original scope.

The audience has senior AWS/IAM fluency. Present KiroCrew as governance around managed coding-agent execution with Kiro CLI, Codex and Claude Code backend choices. Installation, authentication and governance determine usable backends. Write plainly.

## Accepted visual preserved

The endpoint enclosure remains one box: enterprise host protection, Gateway/backend/workspace, Policy ∩ Profile, L0–L5 and cross-cutting controls. In local mode this is the developer machine; remotely, Gateway, backend and workspace run together. Independent laptop agents remain outside the remote service.

The original `kirocrew-security-layers.html`, accepted base, architecture JSON and `kirocrew-aws-deployment.html` remain byte-identical. Browser checks exposed vertical overflow in their reader layout. `prepare-browser-views.py` creates separate `*-browser.html` derivatives with adaptive sizing and concise normal-flow caveats. It also preserves custom endpoint styles in SVG/raster exports and verifies exact SVG equality to accepted inputs. The wrapper embeds those derivatives exactly.

The derivatives pass nine Archify static checks and containment at 1440×900, 1600×1000, 1920×1080 and 2048×1320. The wrapper passes both diagram themes, all three tabs, keyboard activation, all 15 reference details, endpoint search/focus, presentation-mode Escape, direct fragments and PNG/SVG downloads. The reference intentionally scrolls. Evidence is in `evidence/browser/` and derivative `*.visual-check.json` files. Original failures and prior skipped checks are retained. This continuation received author browser inspection, not a new independent security audit.

## Two version boundaries

Accepted diagram and source links: `0.7.0.dev20260911060948`, commit `fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482`, tree `dd8d21e77fe850d179b5a7971ad3f876f6eb011b`. Official pinned source was reacquired at `.build/kirocrew-source`; all 24 retained modules match it exactly.

The user installed the latest nightly during continuation. App Info.plist and package version identify `0.7.0-nightly.20260912t060850`. All 24 selected modules match the installed distribution RECORD. A 4,008-file package snapshot is recorded at `.build/installed-nightly/kiro_crew`. Twelve selected modules differ from September 11; the bounded comparison and raw diffs are retained. Installed metadata supplies no source SHA. Keep these baselines separate.

The web tool rejected both nightly CDN manifests as unsafe to open. No alternate transport was used. “Latest” is user-reported; actual installed identity is locally verified. The original wheel was not reacquired. Never assign the older SHA to this installed package or claim independent feed freshness.

See `evidence/nightly/baseline-verification.json`, `evidence/nightly/installed-nightly-verification.json`, `evidence/nightly/diffs/` and the continuation notes. The first receipt's September 7 app observation predates the user's upgrade; the installed-nightly receipt supersedes it.

## Executable evidence

`./demo.sh --interactive` passed using the frozen September 12 package and installed app Python. A clean process creates new synthetic Crew home/workspace state and verifies recorded snapshot hashes. Existing settings, credentials and sessions are not used. It does not start a model/backend, execute submitted shell text, or make network calls. The executable currently depends on this Mac's runtime; the viewer and deck are portable.

Observed: allow; pause with no write before approval; approved synthetic marker; configured deny; protected-policy path deny with unchanged bytes; command-pattern deny; Policy ∩ Profile limiting layer; fake-credential redaction; seven valid SEL events; one changed record detected; original log restored and verified. Receipts include package, runner/launcher and Python identity. `evidence/live/latest.json` locates the newest successful run; the continuation receipt fixes the accepted interactive run.

Crew's `action=allow` means normal handling. The harness supplies the approval UI and synthetic handler, and explicitly records verdicts through Crew's SEL API. Backend admission/callback delivery, native approvals, auto-approval bypass, signed-policy verification, L0 isolation, project-skill trust, automatic capture/external retention, MCP grants and target IAM remain separate end-to-end checks. Do not present function-level evidence as a backend session.

## Security and AWS distinctions

- Enterprise EDR/MDM, OS hardening, encryption and network controls are external. Crew is not EDR.
- L0 depends on OS/backend. L1/L2 prevention needs a pre-execution Crew hook/callback. Post-execution events cannot prevent an action.
- L3 covers registered schemas; L4 covers particular redaction sinks; L5 verifies recorded SEL events. None implies universal coverage.
- Policy ∩ Profile constrains permissions. Configurable command rules and managed floors differ. Skills, steering and memory provide context, not authorization.
- Transport access, Crew identity, MCP grants and target IAM/OAuth are separate. Only routed calls reach the proposed MCP gateway. LiteLLM and central policy distribution remain proposed integrations.
- Preserve private EC2 + SSM, EBS state, privileged S3-to-protected-file policy sync, optional MCP services, egress controls and external collection. Protect policy ancestors; an effective boundary must prevent agent access to broad instance-profile credentials.
- The MicroVM alternative is historical and was not refreshed here. Reverify current AWS properties before recommending it. Neither AWS design was deployed.

## Reproduction and continuation

Read included `archify-source/archify/SKILL.md` before diagram edits. Revision `c1443b31b496eebf4a68bf83151816c955ddb796` and AWS icon provenance are retained. For reader/viewer changes:

```sh
python3 prepare-browser-views.py
python3 build-security-viewer.py
node archify-source/archify/bin/archify.mjs check kirocrew-security-layers-browser.html
node archify-source/archify/bin/archify.mjs check kirocrew-aws-deployment-browser.html
node archify-source/archify/bin/archify.mjs visual-check kirocrew-security-layers-browser.html --json
node archify-source/archify/bin/archify.mjs visual-check kirocrew-aws-deployment-browser.html --json
node scripts/validate-browser.cjs
```

Use bundled Node/Playwright when needed; the local browser validator launches installed Chrome. Keep SVG-equality verification. Meaningful visual changes require fresh appropriate review. Prior `kirocrew-endpoint-review.json` and `kirocrew-aws-remote-receipt.json` retain their historical scope. New final bytes need new receipts.

Deck authoring: `.build/slides/build-deck.mjs` uses bundled artifact-tool. Finalization validates package structure, geometry, native tables and font policy, then imports the exact PPTX again. Final renders are in `output/slides/`; receipt: `evidence/slides/finalization.json`. Native PowerPoint playback is not claimed. Stage a new output path for revisions rather than overwrite a finalized deck.

`build-security-viewer.py` regenerates catalog/full notes, preserves the historical endpoint review from `evidence/accepted/`, and appends `kirocrew-continuation-notes.md`. Edit that continuation file for current notes. Old packaging and AWS-preview scripts target historical filenames/assumptions; adapt and review before running them.

This folder has no Git metadata. Original transfer files and bundles remain intact. AWS deployment, external publication, real-secret use and messages to others were not authorized. Obtain authorization before new external or paid execution.
