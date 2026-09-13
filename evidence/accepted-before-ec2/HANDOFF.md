# KiroCrew demo — current handoff

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
