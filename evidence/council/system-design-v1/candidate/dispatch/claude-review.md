**1. Verdict: CHANGES REQUIRED** (text-level edits; no structural rework). The deck keeps native backend authentication/approval PENDING on every slide that touches it, separates MCP grant from target IAM, does not invent OAuth, signed policy, tamper resistance or egress control, and the timeline is internally consistent (14:22 CFN → 14:26:10 Gateway start → 14:43–14:49 quit/relaunch → 14:50 readback → 14:56/14:57 IMDS/ingress → 15:01:37 probe → 15:19 unauthenticated). Cost arithmetic checks: $0.1394×730 + $3.20 + $1.92 = $106.88. The single endpoint-control box is preserved.

**2. Image coverage:** All 14 JPEGs (slide-01 through slide-14) read as pixels at 1280×720. None unreadable. I did not open presentation.html, render the deck, or check live AWS/backend state.

**3. Findings**

**F1 — Medium — Slide 3.** The reference box asserts "Policy & Profile · protected configuration" and "L1 Protect paths · protected policy files", but slide 5 states "Crew can edit its configuration" and slide 6 notes place the `crew_denied` hook rule in that crew-writable config. The footer lists sandbox/egress/SEL-HMAC as unverified but omits protected configuration — the one item the evidence contradicts rather than merely leaves untested. Revision: footer → "…Sandbox, egress control, protected configuration/paths and SEL/HMAC execution unverified; Crew config is writable (slide 5)." Keep the box.

**F2 — Medium — Slide 14.** Step 04 "Complete CLI sign-in / Then run four native turns" is the only pending item with no on-slide pending marker; the latest receipt (15:19 UTC) is unauthenticated, so this step may fail live. Revision: add "(pending — 15:19 UTC check unauthenticated; if sign-in fails, stop here and say so)" and keep the notes' rule that an approval card on `crew_denied` fails the test.

**F3 — Medium — Slides 1–14 header.** "Original PPTX" appears on every slide and serves the earlier, superseded candidate (prior reviews covered it, not these bytes). Its content is unknown to me and may contradict current pending claims. Revision: remove from the presented header or relabel "superseded draft".

**F4 — Low — Slide 9.** The capture visibly shows "TURN LATENCY (P50) 0ms" and zero throughput; only the notes say a displayed zero is not a measured session. Revision: callout → "Native model-session metrics pending; the 0 ms turn latency is an empty series, not a measurement."

**F5 — Low — Slides 3, 9, 11 (legibility).** Embedded captures are ~370–400 px wide; layer labels, instrument names, health rows and log rows are unreadable at 1280×720. Captions carry the claims, which is acceptable only with an expand cue — present on 9, absent on 3 and 11. Revision: add "Expand to inspect" on 3 and 11, or show a single larger log pane on 11.

**F6 — Low — Slide 11.** Collection events can be read as an audit trail. evidence-summary: "operational telemetry, separate from security audit/SEL events"; the App Kit runs as crew and its files are crew-writable (slide 5 notes). Revision: footer add "Operational telemetry, crew-run; not a security audit record."

**F7 — Low — Slide 5.** The "Administrator" row does not say this is the operator's SSH account with sudo — used by the owner-token helper and the slide 14 probe command (`ssh kirocrew-demo-admin 'sudo -u mcp-demo …'`). For an IAM audience, the laptop is the client *and* holds the host's root of trust. Revision: "Administrator (operator SSH account, sudo)".

**F8 — Low — Slide 4.** The diagram draws no verified path into the MCP service — only the dashed pending Gateway→MCP arrow — while the caption says mcp-demo→MCP→S3 was verified. Revision: add a small solid arrow "direct probe (mcp-demo)" into MCP.

**F9 — Low — Slide 3.** Notes say the reference image cites the September 11 baseline; the footer's verifications are September 13 ARM. Nothing on-slide dates the reference, mixing baseline and host by omission. Revision: caption "Reference diagram (Sept 11 baseline); ARM verification Sept 13".

**F10 — Low — Slide 1.** "telemetry verified" overstates: what is receipted is collection enabled plus an API readback; slide 4 notes say the resource check "does not establish … telemetry health" and model-turn series are empty. Revision: "telemetry collection active".

**4. Agreement priorities for the other council member**

1. Slide 3 footer must name protected configuration/paths as unverified-and-contradicted (F1); the single box stays.
2. Slide 14 step 04 gets an on-slide pending marker and a stop rule (F2); steps 01–03 remain the demonstrable live path.
3. Freeze the qualifier language (`native_crew_backend_verified=false`, "pending", "unverified", "Separate direct probe", all UTC timestamps) so the no-ai-slop pass cannot soften it, and decide on the "Original PPTX" link (F3).

**5. Material unknowns**

- Content of the embedded PPTX and whether it contradicts the current deck.
- Underlying receipts (crew-imds-connect, native-cli-login-outcome, observability-runtime, final-direct-mcp-rehearsal, price.json) are not in the packet; all figures are taken from evidence-summary.md and notes.md.
- Whether the IMDS IPv6 endpoint is disabled, and whether UIDs other than `crew` (admin/ubuntu) are IMDS-blocked — only `crew` was tested.
- Ownership/permissions of `/var/lib/kirocrew/metrics` and App Kit state — governs any future tamper-resistance claim.
- IMDSv2-required and hop limit 1 are cited from `infrastructure/ec2-demo.json` (declared), not a runtime receipt.
- "before AWS dispatch" for `mcp_denied` derives from code reading (`server.py`), not an observed absence of an SDK call.
- Whether the stopped t3a.small retains the same instance profile and security group (it would inherit S3 access if started).
- Interactive elements ("Open admin portal", "Expand") were not exercised by this review.
