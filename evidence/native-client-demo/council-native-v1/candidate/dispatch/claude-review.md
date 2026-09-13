**Verdict: CHANGES REQUIRED.** Packet fully read; defects are fixable without re-recording.

**Image coverage.** All ten PNGs (slide-1 … slide-10) were read as pixels. Each is 1280×720 and its manifest hash matches the capture-receipt hash for the same slide number. I did not compute any hash myself; binding to `presentation.html` (ac06b8…) is taken from the receipt text. The PNGs show players, posters and chapter lists only; they do not establish playback, seeking, or any frame other than the poster. No PNG shows the AWS AccessDenied/HTTP403 frame, the "Tool call blocked" row, or the private-memory refusal text — those outcomes are accepted from notes/summary, not pixels.

**Findings**

1. **Medium — Slides 5, 6, 7: poster frames contradict the headings.** Each cut starts before the submit, so the first frame shows the *previous* scene's result: slide 5 ("Crew blocks a tool call") shows `ok:true, layer:aws, aws_request_id DT9A0C6ZKDWEQETN`; slide 6 ("MCP service refuses the grant") shows the Crew-hook denial text; slide 7 ("AWS refuses the S3 read") shows `error_code: tool_grant_denied, layer: mcp`. In Print/PDF or a paused deck an IAM audience reads the wrong layer under each title. Revision: set each poster to the result chapter (0:20 / 0:23 / 0:28) or caption "Poster shows the prior turn; play to the result chapter." Related: the MCP cut (160–189) and IAM cut (188–222) overlap by 1 s; trim slide 7 to start ≥189.

2. **Medium — notes.md line 54 / slide 10: stale receipt hash.** Notes cite `authority-attribution-review.json` as `3c0d5750…`; evidence-summary states the current receipt is `3bd876c0…` and that the old hash is superseded. Slide 10 links the same filename. Revision: update the notes hash and confirm the HTML link resolves to the current receipt before acceptance.

3. **Medium — Slide 2 (and deck-wide): owner authority and no governance floor appear only in notes.** Slide 2 says "fixed demo grants," which an IAM reader may take as immutable policy; nothing on any slide says the session has owner privileges, Crew config is owner-editable, and no enterprise policy floor is active. Revision: one footer line on slide 2: "Owner session; Crew config owner-editable; no enterprise policy floor; MCP grants are demo-scoped, not immutable."

4. **Low-Medium — Slide 8: wording diverges from evidence and scope limits are off-slide.** Subtitle says the conversation was "switched to the host-controls agent"; notes and summary say "private-store alias." The slide never states that the fs_read never ran and that this is not RBAC or a filesystem denial. Revision: align the subtitle to the receipt wording and add a footer: "Identity-binding guard; fs_read never executed; not RBAC, not a host-tool denial."

5. **Low-Medium — Slide 9: admin tour substance is not in the packet and the distinctions are off-slide.** The slide is one illegible thumbnail plus a link; the notes' key caveats (posture counts and SEL section are configured catalogs, not executed tests or a live event viewer; collection log is client/server health events, not security denials; Gateway telemetry is distinct) are absent. Revision: add two caption lines carrying those distinctions; the guide itself must be reviewed separately.

6. **Low — Slide 3: "Decision point" column asserts layer attribution without stating its basis.** IAM/MCP/Crew attribution rests on joined server receipts (summary), while slides 4–7 notes say "server receipt correlation is reviewed separately." Revision: footer "Layer per joined server receipts; see notes," keeping the existing "six host takes unrecorded" line, which is good.

7. **Low — Packet hygiene.** capture-receipt.json names files `slide-01.png…slide-10.png` while the packet and manifest use `slide-1.png…`; evidence-summary refers to `capture-binding.json`, which does not exist here (the file is `capture-receipt.json`). Hashes match, so binding holds. Revision: normalize names in the receipt and summary.

8. **Low — Slide 10 / notes: receipt list is incomplete; slide 4 duration mismatch.** The summary relies on `media-review-mcp-controls.json` (e7ffdf…) and `authenticated.json` (e34c9d…) for the four MCP clips and the fresh sign-in, but neither appears in notes' supporting receipts or slide 10. Slide 4's player shows 0:25 while footer and slide 3 say 26 seconds (cut 44–70). Revision: add both receipts; reconcile the duration label.

Legibility otherwise: headings, matrix, chapters and footers are readable at 1280×720; in-poster app text is inherently tiny and needs "Open video full size," which the slides provide. The single endpoint-control box on slide 2 is preserved correctly (Gateway, Kiro CLI, Workspace, MCP service inside; Mac client with local Gateway off; AWS reached via role). Existing VPC/subnet scope, no added networking and no GitHub Actions are stated in notes only, which is acceptable.

**Agreement priorities for the other council member**

1. The stale `3c0d5750…` hash (finding 2) is a blocking defect; acceptance requires the notes hash and slide 10 link to bind the current receipt.
2. Posters on slides 5–7 show the prior scene (finding 1); confirm you see the same frames and agree a result-frame poster or caption is required, and that no PNG evidences the AWS 403 or memory refusal.
3. Layer attribution (Crew non-dispatch, MCP `tool_grant_denied`, IAM `8DET0VKCQPXJXCMC` join) rests entirely on the evidence summary's description of receipts neither of us opened; treat it as "attributed per receipts," not council-verified, and require the owner-authority/no-floor line on-slide.

**Material unknowns**

- No hashes were computed; manifest/receipt integrity is self-asserted.
- Underlying receipts (reconciliation, review, authority readbacks, authenticated.json) are outside the packet; the IAM native→service→AWS join and the Crew "no MCP journal event" claim are known only via the summary. The passive collector remains `collection_complete:false`; only the MCP service journal is asserted complete and restart-continuous. Recovered SEL rows have no independent HMAC verification.
- Video content, chapter seeking and the "transient black repaint" artifact on clip 5 are unverified; root's playback review is pending.
- The admin tour guide's content and dates are not in the packet.
- Slide 2's "us-east-1" and "SSH tunnel" are uncorroborated by notes or summary.
- Whether `presentation.html` embedded links point at current-hash receipts is unknown; I did not open the HTML.
