**Verdict: CHANGES REQUIRED** (revisions are small; no factual over-claims found that would mislead an IAM audience on the core control layers, but several limitations that the notes carry are not visible on the slides, plus two layout defects).

**Image coverage.** All 14 PNGs (slide-1 … slide-14) were read as pixels; none skipped. Each is 1280×720, and every PNG SHA-256 in `capture-receipt.json` matches `manifest.json`; the receipt's `deck_sha256` matches the manifest's `presentation.html` hash. I did not compute hashes myself (read-only), so this is cross-document consistency, not verification. `presentation.html` was not read. Coverage limit: every clip slide shows a poster frame at 0:00 with player chrome; the receipt states `video_playback_pending_at_capture: true`. The PNGs prove nothing about playback, seeking, chapter behaviour or any frame beyond the poster. Poster UI text is ~5 px; only the larger tokens (e.g. `DT9A0C6ZKDWEQETN` on slide 5, `8DET0VKCQPXJXCMC` and `http_status: 403` on slide 8, the canary string on slide 10, `native_enforcement_verified: false` on slide 12) were legible enough to confirm the captions.

**What holds.** Slide 2 keeps the single endpoint-control box (Gateway, Kiro CLI, Workspace, MCP service on EC2), Mac client with local Gateway off, and footers on slides 2/6/13 say owner connection, owner-editable Crew config, no governance floor. Slide 9 correctly limits the memory refusal to conversation binding, "fs_read never ran", not RBAC. Slides 3/4 and 11/12 label result-inspection and approval-to-result cuts. Slide 13 separates configured coverage, Gateway telemetry, collection health, SEL and MCP audit, and says counts describe available rules, not outcomes. Slide 14 preserves existing VPC/subnet, no NAT/LB, no GitHub Actions.

**Findings**

1. **Medium — Slide 4.** "3 additional control demonstrations still need completed native evidence. Shot list" never names them; notes list sensitive-path read, protected-path write, IMDS execution. Slide 13 then shows "143 credential paths", "23 config paths" as configured. An IAM viewer will assume those path controls were demonstrated. Fix: list the three names on slide 4 (ample blank space) and tag the posture crop on slide 13 "native denial pending".

2. **Medium — Slide 12 (and slide 4 row).** Poster shows the helper doing an anonymous GET to `127.0.0.1:8476/api/security/posture`; evidence-summary says loopback caller. Slide text says only "Token required denial from the EC2 Gateway", so "Gateway authentication" reads as the Mac session being denied. Fix: subtitle "A helper on EC2 sends one anonymous loopback request; the Mac session stays authenticated", and state `native_enforcement_verified:false` in text, not just the poster.

3. **Medium — Slide 11.** Notes/evidence-summary: the marker command rule was temporary and removed after the take; replay does not mean it is active. Nothing on the slide says this. Fix: footer "Temporary marker rule, removed after the take; not current configuration."

4. **Low-Medium — Slide 8.** Notes: role attribution uses instance-profile receipts, no per-request STS caller identity collected. Slide is silent; the poster's model text says "The IAM role explicitly denied", which the caption doesn't temper. Fix: footer "Role attribution from instance-profile receipts; no per-request STS identity."

5. **Low-Medium — Slide 13 legibility.** The "Expand" button occludes the "112 buil…" badge and a fourth posture row is clipped to a sliver. Fix: crop to three full rows and place Expand outside the crop.

6. **Low — Slide 3 layout.** Six rows push the DEMONSTRATION/DECISION POINT header to ~10 px under the title descenders; slide 4 has two rows and a large blank. Fix: rebalance 4/4 (or 5/3).

7. **Low — Slide 2.** "SSH tunnel" and "us-east-1" appear only on the diagram; neither is in notes.md or evidence-summary.md. Fix: add a supporting line to notes, or drop the labels.

8. **Low — notes.md / slide 6.** Notes sections 3 and 4 are verbatim duplicates, so slide 4's presenter notes don't match its content. Slide 6 is the only clip slide whose footer omits duration and "Full evidence scope in notes"; it also doesn't carry the "original collector remains incomplete" caveat that sits behind "MCP journal has no matching arrival" (supported by the completeness/restart-continuity checks per evidence-summary, but the caveat belongs on-slide). Fix: split the notes; align footer. Also slide 1 says "September 13, 2026 recordings" while slides 11–12 are 2026-09-14T00:00:31Z; add "UTC 13–14 Sept" or a timezone.

Trivial, no action: slide 5 player shows 0:25 vs "About 26 seconds" (cut 44–70), slide 10 shows 0:38 vs 39 — player truncation.

**Agreement priorities for the other council member**

1. Confirm all 14 PNGs read as pixels and that the review claims nothing about playback, seeking or non-poster frames.
2. Agree on layer wording for slides 6/7/8/12: Crew hook (no service arrival), MCP grant (service refusal, no AWS dispatch), IAM (native+service+AWS request ID join, no STS identity), Gateway token (anonymous loopback probe, not Mac-session auth). Findings 2 and 4 are the ones most likely to be read differently.
3. Agree that the three pending host cases must be named on-slide beside slide 13's configured counts, and that slide 11 must say the rule was temporary.

**Material unknowns**

- Video playback, seek, chapter "Pause at chapters", download links and poster-vs-first-frame behaviour: unverifiable from stills; receipt says playback pending.
- The separate admin tour (`kirocrew-admin-tour.html`), shot list, contact sheets, diagram and all receipt links on slide 14 are outside the packet; whether the admin tour is "substantive" cannot be judged — inside the deck it is one slide with two crops.
- Whether the slide 13 "Expand" occlusion is a hover artifact of the capture or static layout.
- Original passive collector remains `collection_complete:false`; SEL integrity rests on Gateway verification without independent signature checks; no sampled process is proven to overlap a pending approval; denied object digest not recomputed.
- Whether the HTML Notes panel duplicates the 3/4 notes defect.
- Legibility of full-size video and whether "Open video full size" makes poster JSON readable.
