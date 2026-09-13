**CHANGES REQUIRED**

candidate-v3. Packet `manifest.json` names this candidate; this review did not recompute the stated manifest SHA-256, render `deck.pptx`, or query live AWS/backend state. Judgment is from `notes.md`, `evidence-summary.md`, and the nine slide PNGs read as pixels.

## Image coverage

All nine PNGs were read as images: `slide-1.png` through `slide-9.png`. None failed as pixels. `deck.pptx` was not opened; on-slide wording was checked against `notes.md` and the PNGs.

## Findings

**1. High — Slide 3.** Several topology captions are truncated or corrupted in the PNG: `Policy n Profile`, `Files t session state`, and a clipped denied-object edge (`GetOb'ect denied`). Title and footer are readable; interior node/edge type is not reliable at presentation size. Speaker notes tell the presenter to open a live architecture artifact for readable detail, which concedes the slide itself is not the readable source. **Revise:** Re-export so every node, UID, port, and edge label is fully readable on the slide; do not depend on an off-slide original.

**2. High — Slide 3.** The CloudFormation topology draws `Policy n Profile · L0-L5` (`Approval · schemas · redaction · SEL`) inside the red `EC2 execution endpoint` as if that stack were part of the deployed system. Evidence supports a service-user-owned Crew config with a `crew_denied` rule, not a verified policy floor; sandbox, redaction, and SEL-on-EC2 are unverified; the earlier synthetic SEL run is explicitly not an EC2/native receipt. An AWS/IAM audience will read this node as deployed control, not a control-map overlay. **Revise:** Keep Gateway, Kiro CLI, and workspace in the execution enclosure; mark L0–L5/SEL as control-map reference or omit them from the deployment diagram.

**3. Medium — Slides 5 and 8, plus Slide 5 notes.** Slide 5’s footer correctly says Crew denial needs a native pre-execution gate, but the notes call the table “the live sequence.” Slide 8 then scripts “Run the four fixed tools, approving individual calls” for 03:50–05:50. Evidence: `direct_mcp_service_probe` at `2026-09-13T04:17:07Z`, overall passed, **Native Crew backend verified: false**; Builder ID looped; GitHub login in progress; `crew_denied` is configuration only. A presenter click-deny is not Crew prevention. **Revise:** Script the live path as the three-call direct probe (Slide 6). Keep native sign-in, model session, and automatic `crew_denied` as pending. Change step 3 so allowed calls may be approved individually and `crew_denied` is automatic-or-pending, never “approve all four.”

**4. Medium — Slide 8 step 2.** “Open the remote workspace and Kiro CLI session” binds a receipt-backed UI state (window `Kiro Crew [:5599]`, Gateway connected, `enforcement-demo`, `/srv/kirocrew-demo/workspace`) to an unverified backend session. **Revise:** Split “workspace already open over the tunnel” from “Kiro CLI auth/session still pending.”

**5. Low — Slide 4.** “Firewall blocks instance metadata” is easy to read as instance-wide IMDS lock. Slide 3 is accurate (`IMDSv2 · blocked for crew UID`); evidence is an owner-based reject of the `crew` UID so `mcp-demo` can still take the instance role. **Revise:** Say the guard blocks the `crew` UID only.

**6. Low — Slide 1.** Subtitle “remote coding-agent execution” has no on-slide pending flag. Notes correctly say Kiro CLI auth and a verified native session are still required; the client/tunnel/workspace facts are real. **Revise:** One title-line caveat that native backend auth is pending.

Not counted as defects: Slide 2’s single Endpoint control box (laptop = client; remote mode puts Gateway, backend, and workspace on EC2); Slide 6 omitting `crew_denied` and labeling a direct probe; MCP grant vs IAM 403 kept separate; no OAuth, signed policy, tamper-resistance, or egress-enforcement claims; pricing/cleanup matching the cited Pricing API and VPC IPv4 figures as rounded.

## Agreement priorities

1. Treat Slide 3 label damage as blocking. The architecture slide must be readable in the PNG; a side artifact is not a substitute.
2. Keep native Kiro CLI auth, automatic `crew_denied`, L0–L5/SEL/sandbox, and full-session performance in the pending/configured bucket. The only receipt-backed live demo is the direct MCP probe (`read_allowed` / `mcp_denied` / `iam_denied`).
3. Preserve one execution enclosure: laptop client; EC2 holds Gateway, backend, workspace, and endpoint controls; MCP on-host but outside the Crew box, holding AWS authority via IMDSv2. Do not “clarify” with OAuth, central policy, or egress language the evidence lacks.

## Material unknowns

Current EC2/MCP/IAM state after `2026-09-13T04:17:07Z` was not observed. Whether GitHub sign-in later produced a native success receipt is unknown; this packet has none. Canonical strings behind the truncated Slide 3 captions were not recovered. PPTX XML and file hashes were not inspected. Whether HMAC/SEL or sandbox is even installed on this host (beyond the deny-rule config) is not established here.
