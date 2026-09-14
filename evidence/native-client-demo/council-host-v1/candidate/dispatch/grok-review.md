**CHANGES REQUIRED**

Candidate `host-controls-v1` is bound: `presentation.html` SHA-256 `cc139d5d1d47dbc4ed79cb52ade4c972d14427071d5aff866d33ad9cc9070335` matches `capture-receipt.json` `deck_sha256`. Packet PNGs were operator-captured stills of that HTML (1280×720); this review did not render HTML, follow links, play video, or inspect live systems.

### Image coverage
All 14 listed PNGs were read as pixels: `slide-1.png` … `slide-14.png`. None unread. Stills show chrome, captions, and video posters/controls only. They do **not** prove playback, seeking, or any frame not on the poster. `capture-receipt.json` has `video_playback_pending_at_capture: true`.

### Findings
1. **Medium — Slide 4.** Footer says “3 additional control demonstrations still need completed native evidence” and links “Shot list,” but does not name **sensitive-path read, protected-path write, IMDS execution**. Notes/`evidence-summary.md` treat those as unfinished (IMDS execute still pending when the observer expired; no firewall outcome). On a print/PDF path the names vanish. **Revise:** name the three pending cases on-slide; state IMDS has no completed native result.

2. **Medium — Slide 11.** Title/footer correctly call this post-denial inspection with collapsed tools. They do **not** say the temporary marker `printf` rule was **removed after the take**; cleanup only proves that exact rule is absent. Replay is historical, not a live standing control. **Revise:** one footer clause: rule removed after capture; recording is that earlier config.

3. **Medium — Slide 4 (row “Gateway authentication”).** Decision point is “EC2 Gateway token check.” Slide 12 and the evidence summary say the film is **Allow-once → assistant HTTP 403**, native Output collapsed, `native_enforcement_verified: false`, and Gateway `Token required` is **correlated** (route/caller/reason/interval), not a direct SEL-to-tool id. Command row already uses “Crew hook, separate receipt.” **Revise:** same pattern, e.g. “EC2 Gateway token (correlated receipt).”

4. **Medium — Slide 13.** Left text correctly treats 143/23/112 as **configured coverage**, not native proof. The crop still leads with “Sensitive path blocking” / “Write-protected paths” while those denials are pending, and **Denied commands** is truncated (`112 buil`). Notes distinguish **Denied Commands** (shell) from **`auto_deny_tools`** (Crew MCP hook for slide 6); the pixels never show that split. **Revise:** untruncate the count; label catalog vs filmed outcomes on the crop; show or name the Crew MCP hook apart from shell Denied Commands.

5. **Low — Slide 1.** “September 13, 2026 recordings” omits command/auth takes at `2026-09-14T00:00:31Z`. **Revise:** “13–14 Sep 2026” or “from 13 Sep 2026.”

No High factual error on the MCP quartet: slides 5 and 8 quote joined native/service AWS request IDs (`DT9A0C6ZKDWEQETN`, `8DET0VKCQPXJXCMC`); slide 7 states MCP `tool_grant_denied` and no AWS dispatch on that invocation; slide 6 is a native blocked row plus isolated SEL hook_deny. Evidence summary records MCP journal completeness and restart continuity **true** for those four cases, so absence is not upgraded from an incomplete journal. Original collector remains `collection_complete: false` (notes).

Architecture (slide 2) keeps **one** EC2 endpoint-control box (Gateway, Kiro CLI, workspace/host controls, MCP service). Mac is client, local Gateway off. Owner-editable Crew and **no enterprise floor** appear on slides 2, 6, 13. VPC/subnet-only, no extra network gear, GitHub Actions out of scope: slide 14. Identity (slide 9) vs Crew tool hook (6) vs MCP grant (7) vs IAM (8) vs host allow-baseline (10) vs command inspection (11) vs Gateway auth (12) is mostly clear once findings 3–4 are fixed. Admin “tour” on-deck is two crops plus **Open the admin tour**; substance is a separate HTML not in this packet.

### Agreement priorities
1. Slide 4: is “3 additional… Shot list” enough, or must pending names (including IMDS/no firewall) be on-slide for print?
2. Slide 4 vs 12: may the matrix say “EC2 Gateway token check,” or must it match “separate receipt” given collapsed output and correlation-only SEL?
3. Slide 11: is marker-rule removal notes-only, or required on the inspection slide so replay is not read as current policy?

### Material unknowns
Playback, seek, and non-poster frames; admin-tour HTML bytes (hash cited, artifact not in packet); whether “Shot list” names the three pending cases; per-request STS caller identity (not collected); IMDS after observer expiry; independent SEL HMAC verification; any host change after cleanup readback; live AWS/backend state.

Recommend: keep the single EC2 box and MCP/IAM request-id captions; apply findings 1–4 before ACCEPT. Do not treat this as live validation or video review.
