**Verdict: CHANGES REQUIRED** — the deck is factually conservative and its layering is mostly correct; three medium on-slide gaps and several low presentation defects should be fixed before acceptance.

**Coverage.** Read as pixels: all 16 PNGs (`slide-1.png` … `slide-16.png`, 1280×720). None skipped. `presentation.html` not read (byte-binding only). Manifest and receipt SHA-256 values agree textually for all 16 PNGs and the HTML; I did not recompute hashes. Every video slide shows a poster and player at 0:00 with chapter buttons — no playback, seeking or non-poster frames are verified. The receipt says capture resumed at slide 11 after a timeout, so the sequence is two sessions.

**Findings**

1. **Medium — Slide 13 (and 4).** The managed deny and the earlier owner-editable Crew hook (slide 6) block the same tool, `crew_denied`, with the same visible "Tool call blocked" row. Notes §13 state the duplicate mutable hook was retired before this take; the slide omits it, so on-slide the "managed policy" attribution is indistinguishable from slide 6. Revision: footer "Duplicate owner-editable Crew hook retired before this take; deny attributed to root-managed Policy v1 via native history + policy-layer SEL (isolated-slot join, no direct trace ID)."

2. **Medium — Slide 15.** The Governance crop shows the UI heading "CENTRAL POLICY DISTRIBUTION" beside "Source: file". Notes disclaim any signed fleet policy or distribution service. Uncaptioned, an IAM audience will read this as a central service. Revision: caption "UI label only — source is a local root-owned file; no distribution service, SSO or immutability claimed," or crop the heading.

3. **Medium — Slide 15.** Loaded-policy identity is not bound to the filmed take on-slide. The crop shows "Policy v1", "Fetched at startup only", "Cached copy is 55s old", undated. The policy SHA-256 (ca6c7e…) and 02:20:00Z observation are notes-only; the denial was filmed 02:06:34Z. A 55-second-old cache under a startup-only fetch invites the question whether the Gateway restarted between take and capture. Revision: add capture time and hash prefix to the slide; state Gateway process continuity across 02:06–02:20Z if `host-runtime-check.json` supports it, otherwise say "identity verified 02:20Z; continuity per receipt."

4. **Low — Slide 2.** Single enclosure is preserved (good), but the operator/admin trust boundary exists only as a footer sentence. Revision: two small labels inside the enclosure — "Host root: owns `/etc/kirocrew-demo` policy + systemd env" and "Crew user: MCP availability, approvals, user settings" — without adding a second box.

5. **Low — Slide 15.** The pinned-command crop shows two toggled rows (`aws s3 cp` and a partly cut `aws s3 mv`); notes describe one pinned S3 upload rule and separately distinguish ordinary Shell Denied Commands. Which row is policy-pinned is ambiguous. Revision: crop to the single pinned row or caption the second row's control type.

6. **Low — Slides 5, 10 (and 3, 4).** Player durations read 0:25 and 0:38 while slide text says "About 26 seconds" / "About 39 seconds" (cut lengths). Revision: use the encoded durations or state "cut 26.0 s / encoded ~25.9 s". Also unify "About 28s" (slide 6) with the other slides' wording.

7. **Low — Slides 4, 14, 16 legibility.** Slide 4: title baseline nearly touches the "DEMONSTRATION" header row and the "Unfinished" callout crowds the footer (slide 3 spacing is correct). Slide 14: the staged-restriction crop is a thin strip with truncated text ("obals as opted-in."), too small to support "staged and discarded"; the session-options crop bleeds background chat text. Slide 16: ~150px of dead space under the title, and the notes' `--check` step is omitted from the shown command. Revision: restore slide-3 spacing; taller, tighter crops; add `--check`.

8. **Low — Packet.** `capture-receipt.json` names files `slide-01.png`…`slide-09.png` while the manifest and directory use `slide-1.png`…; binding holds by hash, but a name-based verifier fails. `capture_method` has typos ("at1280x720", "atslide11"). Revision: normalize names and text before final QA.

**Claims judged against evidence (no revision needed).** Slides 5–12 correctly carry "BEFORE MANAGED POLICY" and their recorded limits (collapsed output, approval-to-result cut, result-inspection-only, `native_enforcement_verified:false`). Slide 4's unfinished list (sensitive-path read, protected-path write, IMDS execution) is preserved, not promoted. "Blocked before MCP dispatch" (slides 4, 13) rests on notes' bounded, continuity-checked MCP journal; the slide-13 purple line is adequate. Slide 14 correctly states a local toggle narrows availability and the Gateway still evaluates policy; the discarded staging is labelled as discarded. Slide 3's "EC2 conversation guard" is scoped as binding-only, not RBAC or filesystem enforcement. VPC/subnet and no-new-network constraints are stated on slide 16. No slide claims SSO, central MCP registry, immutable policy, protected audit storage or failover; slide 15's bottom row separates telemetry, collection health, SEL decisions and MCP audit without asserting tamper-protection.

**Replication.** The only replication claimed is artifact rebuild from a clean checkout and a fresh ARM bundle (root-reported, not in packet). No scheduling, restore/recovery, retention or failover is claimed or demonstrated, and the slides don't say otherwise. Trust boundary: Mac app and remote CLI authenticate via their own flows; MCP uses the instance role; SSH source CIDR is caller-supplied. Demonstrated failure behavior: none for replication; `fail_closed` appears only in the evidence summary and no failed-load run is recorded.

**Agreement priorities for the other reviewer**
1. Slide 13 must state the hook retirement on-slide (finding 1) — without it the managed attribution is not distinguishable from slide 6.
2. Slide 15 must neutralize "CENTRAL POLICY DISTRIBUTION" and date/bind the Governance capture and policy hash to the 02:06:34Z take (findings 2–3).
3. Hold scope: eight earlier clips stay pre-policy; the allowed managed read stays unfilmed; screenshot coverage is posters/controls only; no live or playback validation.

**Material unknowns**
- Gateway process continuity across policy install, the 02:06:34Z take and the 02:20Z observation (the 55s cache).
- Capture times of the Governance, pinned-command and Connections screenshots relative to the take (Connections last probe 01:54Z).
- Contents of cited receipts (`policy-verify`, `host-runtime-check`, `native-managed-ui4-verification`, `mcp-verify`, `assignment-diagnostic`) — outside the packet; attribution rests on notes' descriptions.
- Whether the private-memory guard executes server-side as slide 9 states.
- Which slide-15 rows are policy-pinned versus ordinary shell denied commands.
- Actual video frames, durations and seek behavior; hash recomputation.
