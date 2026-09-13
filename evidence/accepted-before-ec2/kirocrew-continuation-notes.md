## Continuation evidence — September 12 EDT / September 13 UTC, 2026

The accepted single endpoint-control box is preserved. Browser validation and the local slide-to-demo rehearsal are complete. The AWS deployment and external MCP integration remain proposals.

### Browser evidence

The accepted standalone HTML overflowed vertically at all four required desktop sizes. Its SVG geometry was sound; its reader-layout eligibility excluded these taller diagrams. `prepare-browser-views.py` now creates separate `*-browser.html` derivatives, adjusts the surrounding reader layout, and replaces redundant conclusion cards with a visible caveat. It also includes the existing custom endpoint CSS in SVG/raster exports, fixing a black endpoint panel found during export-image inspection. It verifies that each embedded SVG is byte-for-byte equal to its accepted source. The source architecture, accepted base, detailed endpoint SVG and AWS topology remain unchanged.

The derivatives pass Archify's nine static checks and browser containment at 1440×900, 1600×1000, 1920×1080 and 2048×1320. The integrated viewer passes both themes for both diagrams, all three tabs, keyboard tab activation, all 15 expandable reference entries, endpoint search/focus, presentation-mode Escape, direct reference-fragment navigation and PNG/SVG downloads. The reference is an intentionally scrolling document. Browser checks wait for both the reader and navigation layouts to settle and explicitly verify the caveat remains visible. Laptop scale gives an overview; use focus/presentation mode for small endpoint labels.

Evidence: `evidence/browser/derivatives.json`, the two `*-browser.visual-check.json` receipts, and `evidence/browser/integrated-browser-receipt.json`. Browser screenshots and actual downloads are under `evidence/browser/`. Original failure receipts and prior skipped checks are retained separately. The earlier subagent review is historical; the continuation received author browser inspection, not a new independent security review.

### Two version boundaries

| Evidence | Version identity | What was verified |
| --- | --- | --- |
| Accepted diagram and pinned links | `0.7.0.dev20260911060948`; commit `fa0d8cf3c241b3b53b81fe4115ab70a30c1ca482` | Official GitHub checkout reacquired; all 24 retained Python modules exactly match the pinned source |
| Installed app and local rehearsal | `0.7.0-nightly.20260912t060850` | App Info.plist and package version agree; all 24 selected modules match their installed distribution RECORD hashes; a 4,008-file package snapshot is fingerprinted |

The user installed and described the September 12 nightly as latest. The nightly CDN manifests remained inaccessible through the web tool; no alternate transport was used for those denied URLs. Therefore the installed version is verified locally, while current-feed freshness is not independently confirmed. The installed package does not expose a source commit; its build path is not a commit identifier. We do not assign the September 11 SHA to it.

`evidence/nightly/baseline-verification.json` records the earlier pinned-source check, including the September 7 app observed before the user's upgrade. `evidence/nightly/installed-nightly-verification.json` supersedes that app observation. The frozen installed package is at `.build/installed-nightly/kiro_crew`; the official pinned checkout is at `.build/kirocrew-source`. No original nightly wheel was reacquired.

### Relevant installed-code changes

Twelve of the 24 retained security-related modules differ from September 11. The other twelve match. Saved diffs are in `evidence/nightly/diffs/`. This was a bounded comparison of control-relevant code, not a full audit or exhaustive runtime regression test.

- `hooks.py` distinguishes classifier-proven read-only work from approval grants, supports classifier-only checks on designated surfaces, and adds opt-in live hook configuration reload. This reinforces the need to prove the actual backend's pre-execution boundary.
- `platform/governance.py` preserves further narrowing tiers when composing scoped rule maps and carries nested rule labels. The Policy ∩ Profile explanation remains valid; the rehearsal demonstrates a profile-limited denial.
- `security/paths.py` and `sandbox.py` add protection for the browser gateway launcher and harden path/resolution and temporary-directory handling. The protected-file rehearsal exercises one representative path, not every sandbox platform.
- Redaction plumbing adds structured findings and a browser launch-error sink. SEL API outcomes are redacted and clipped; shell normalization, self-protection and known OAuth endpoint classification also change. These are covered-sink and classifier improvements, not complete DLP or universal capture.
- `validation.py` requires positive monitor cycle/runtime caps. Exact effective limits still belong in host diagnostics.

The detailed control catalog keeps its September 11 source attribution. The installed-code deltas above and the executable evidence are separate, so an older pinned source link is never presented as provenance for the newer package.

### Live evidence and boundaries

`./demo.sh --interactive` passed on the installed September 12 snapshot. It verifies the snapshot's recorded files before import, uses the installed app's Python runtime in a clean environment, and creates a fresh synthetic Crew home/workspace under `evidence/live/`. It never starts a backend/model, sends shell text to an executor, or makes a network call. Existing Crew settings, credentials and sessions are not used.

The harness calls real Crew hook, governance, redaction and SEL functions. It shows an allowed read, a presenter-approved write, configured denial, protected-policy path denial, command-pattern denial, the Policy ∩ Profile limiting layer, a fake-credential redaction, and valid SEL records. Changing one disposable record makes verification fail; restoring the bytes makes all seven records verify again. The expected HMAC mismatch during that deliberate test is not a failed rehearsal.

Crew's `action=allow` means normal handling in this API. The harness supplies the approval prompt and executes the synthetic marker write only after `APPROVE`. It also explicitly records the actual gate verdicts through Crew's SEL API. This does not prove backend callback delivery, the native approval UI, automatic event capture, signed-policy verification, L0 sandbox effectiveness, project-skill trust or every catalog control. Those remain separate acceptance checks.

The current run receipt is located by `evidence/live/latest.json`; the continuation receipt binds the completed interactive rehearsal directly. Each successful receipt records the package identity, runner/launcher hashes, Python runtime and step outcomes. The seven-slide deck includes presenter notes and transitions; `WALKTHROUGH.md` supplies commands and expected evidence.

### MCP and enterprise IAM research

The proposed LiteLLM tier separates caller identity, server/tool grants, downstream service credentials and target authorization. Use explicit grants: omitted or empty settings can inherit broader access; the documented strict key-access option is `require_key_mcp_access_defined: true`. Verify the exact semantics against the version selected for deployment. [LiteLLM MCP access control](https://docs.litellm.ai/docs/mcp_control)

Interactive user consent uses authorization-code OAuth with PKCE; service identities can use client credentials. Entra delegated access uses LiteLLM's `entra_obo` token-exchange profile and an assertion whose audience is the LiteLLM application. AWS SigV4 calls instead use the proxy's credential chain or an assumed role. These are proposed integration choices, not observed Crew-native capabilities. [OAuth](https://docs.litellm.ai/docs/mcp_oauth), [Entra OBO](https://docs.litellm.ai/docs/mcp_obo_auth), [AWS SigV4](https://docs.litellm.ai/docs/mcp_aws_sigv4)

For the retained EC2 design, SSM governs transport access. It does not substitute for Crew policy, MCP grants or target IAM. Session Manager does not log port-forwarded or SSH payloads; external application-event collection must be designed separately. The privileged policy adapter must protect both the file and its ancestor directories, and agent processes must be prevented from accessing broad instance-profile credentials. [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html), [Session auditing](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-auditing.html)

For an eventual end-to-end demonstration, record three distinct outcomes: Crew denies before handler execution; MCP grants deny before the target call; MCP permits a call that target IAM denies. Correlate request IDs across services. No gateway, OAuth tenant, AWS deployment or external audit collector was exercised in this continuation.
