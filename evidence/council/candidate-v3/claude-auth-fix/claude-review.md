## 1. Decision

**CHANGES REQUIRED.** The deck's factual claims track `evidence-summary.md` closely, and the pending/deployed split is handled correctly in the speaker notes and in the red captions on slides 5, 6, 8, 9. The defects are on-slide: slide 2 projects a control map full of undeployed capability with no on-slide caveat, slide 3's diagram is not readable at presentation size, and slides 1 and 7 lack the status framing their neighbors have. No fabricated OAuth, signed policy, tamper resistance, or egress enforcement appears in the slide text; no slide asserts native backend approval.

## 2. Image coverage

I read all nine PNGs as pixels: slide-1 through slide-9. None failed to load; there is no image I could not read.

Resolution limits within images I did read: on slide-3 the diagram node sub-labels render at roughly 8–9 px, and I could not reliably distinguish `0` from `8` — I read "Ubuntu 24.84" and "loopback :8081" where `notes.md` and `evidence-summary.md` say 24.04 and port 8001. On slide-2 the embedded screenshot's third-level captions ("Resolved paths · protected policy files", etc.) are at the edge of legibility. I did not parse `deck.pptx`; I treated `notes.md` as the authoritative slide text, and I did not verify the packet or file SHA-256 values (no hashing available under Read-only). I did not render the deck or observe any live AWS, EC2, or backend state; all cloud facts here are as-supplied by the packet.

## 3. Findings

**F1 — High — Slide 2.** The pinned endpoint image shows EDR/MDM, disk encryption, device identity, network egress, OS sandbox, exfiltration checks, credential scrub, resource limits, and "HMAC-chain verification." The "do not infer" disclaimer lives only in the notes; on-slide text says just "Control map. The following slides show the deployed subset and its evidence." Projected, this reads as claimed tamper resistance and egress enforcement. *Fix:* add one on-slide line under the image — "Reference map. Most pictured controls are not deployed or verified in this demo." Do not alter the pinned image.

**F2 — High — Slide 3.** Node text is too small to read from an audience seat, and the notes concede it: "Open the live EC2 architecture artifact for readable node details." An AWS-fluent audience reads ports and OS versions; I could not resolve them. *Fix:* enlarge the diagram (the crop retains empty grid columns at both edges), or split into two slides, and verify the port/OS digits against `infrastructure/ec2-demo.json` before freezing.

**F3 — Medium-High — Slide 7.** The green caption "Desktop runtime verified with the local Gateway off" sits under a "Kiro CLI backend / 2.21.4 official Linux artifact" block. Green is this deck's verified color; only the artifact hash and manifest match were verified, not any backend session. *Fix:* add a red line — "Native backend authentication pending; artifact integrity only."

**F4 — Medium — Slide 8, step 3.** "Run the four fixed tools, approving individual calls" conflicts with the evidence requirement that `crew_denied` must stop automatically before dispatch; a presenter rejection is explicitly not evidence. *Fix:* "Run the four fixed tools; approve allowed calls individually — crew_denied must deny automatically."

**F5 — Medium — Slide 1.** Slide text names "Crew controls, an MCP service and AWS IAM" as equal pillars with no status line, while the Crew boundary has zero receipts. The caveat is notes-only. *Fix:* add a subtitle line — "MCP and IAM boundaries receipt-verified; native Crew session pending."

**F6 — Medium — Slide 4.** "Firewall blocks instance metadata" reads host-wide; per evidence it is an owner-based rule scoped to the `crew` UID. Separately, the `mcp-demo` row omits that the instance role also carries the SSM core managed policy, understating role scope for an IAM audience. *Fix:* "Firewall blocks metadata for this UID" and "Instance role (two S3 prefixes + SSM core) through IMDSv2."

**F7 — Low-Medium — Slide 3.** The outer dashed box is labeled "us-east-1 · t3a.small · Ubuntu 24.0x," mixing region and host; the Demo MCP service and instance role sit outside the inner "EC2 execution endpoint" box. Correct, but a viewer may read the MCP service as off-host. *Fix:* label the outer box "EC2 host — t3a.small" and put the region on the canvas edge. The single endpoint-control enclosure is otherwise preserved and should stay as-is.

**F8 — Low — Slide 6.** No receipt identity on-slide; the 401 unauthenticated check and four-tool discovery are notes-only, and `read_allowed`'s request ID is omitted while `iam_denied`'s is cited. *Fix:* add a footer — "direct_mcp_service_probe · 2026-09-13T04:17:07Z · unauthenticated request 401."

## 4. Agreement priorities for the other council member

1. **On-slide provenance labels for every claim class.** Deployed-and-receipted, configured-but-untested, and pending must each be visible without the notes, specifically on slides 1, 2, and 7 (F1, F3, F5). This is the single highest-value change.
2. **Slide 3 must be legible unaided.** A slide whose notes tell the presenter to open a different artifact is not doing its job; port and OS digits must be verified against the template, not the raster (F2).
3. **Hold the `crew_denied` line.** No slide may imply Crew prevention occurred. Slides 5, 6, and 8 currently hold it — keep slide 8 step 3 from eroding it, and require a rehearsed on-slide fallback if sign-in is still blocked at demo time (F4).

## 5. Material unknowns

- Whether native Kiro CLI sign-in will succeed before the demo. The deck has no on-slide fallback; the notes' direct-probe fallback is explicitly not a substitute.
- Whether ":8081"/"24.84" are raster artifacts or real diagram typos. Unresolvable from the PNG; check `infrastructure/ec2-demo.json` and the source SVG.
- Current cloud state: I cannot confirm the stack, instance, services, tunnel, or the client `/32` ingress rule are live today. The client IP changes invalidate the SG rule.
- `deck.pptx` internals — fonts, embedded image scale, alt text, note-to-slide sync — unexamined.
- The cited evidence files (receipts, audit JSONL, policy JSON) are not in this packet; I judged the deck against `evidence-summary.md` as-supplied and could not corroborate it.
- Whether the pinned slide-2 image may carry a new on-slide caption without breaking its "unchanged accepted" status.
