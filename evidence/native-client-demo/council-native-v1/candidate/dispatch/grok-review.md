**CHANGES REQUIRED**

Candidate `native-controls-v1` is bound: packet `manifest.json` matches `capture-receipt.json` (`presentation.html` SHA-256 `ac06b813…`, 10 PNG hashes). Architecture on slide 2 keeps one EC2 endpoint-control box (Gateway, Kiro CLI, workspace, MCP service) with the Mac as client and local Gateway off. Slide 3 discloses six unrecorded host takes. Frozen **notes** mostly respect layering, owner≠RBAC, and no governance floor. The **visible slides** do not: first-frame posters invert Crew / MCP / IAM, identity is easy to read as host FS, and IAM-material limits sit only in speaker notes.

**(2) Image coverage.** All ten files were read as pixels: `slide-1.png` … `slide-10.png`. None unread. Receipt names `slide-01.png`–`slide-10.png`; hashes match the packet files. Captures are 1280×720 slide chrome plus video posters/controls (slides 4–8) or stills (1–3, 9–10). **These PNGs do not prove playback, seeking, or any recorded frame after the poster.** `presentation.html` was not opened.

**(3) Findings**

1. **High — slides 5–7.** Posters are the previous turn, contradicting titles. Slide 5 (Crew block, no approval) shows `ok: true`, `tool: read_allowed`, `layer: aws`, 55 bytes. Slide 6 (MCP `tool_grant_denied`) shows a Crew hook block of `crew_denied` before MCP dispatch. Slide 7 (IAM `AccessDenied` / HTTP403 / AWS request ID) shows `layer: mcp`, `tool_grant_denied`, `mcp_denied`. A static IAM walkthrough therefore displays the wrong control layer. **Revise:** poster/chapter-0 still = the named result frame for that cut.

2. **High — slides 4 and 7 (IAM proof not on-slide).** Across all ten PNGs, no frame shows `AccessDenied` / HTTP403 / `8DET0VKCQPXJXCMC`, or allowed `DT9A0C6ZKDWEQETN` / 55 bytes / digest `34ebbef…`. Those joins exist only in `evidence-summary.md`. Slide 4’s poster is the idle greeting. MCP JSON alone is not AWS dispatch. **Revise:** put the joined native + service + AWS result stills on slides 4 and 7.

3. **High — slide 8.** Caption and composer (`host-controls` agent, `fs_read` of `allowed-canary.txt`) read as a host/filesystem demo. Receipts: conversation-to-private-memory assignment, stop before a tool turn, not RBAC, not FS denial, not host-tool enforcement. **Revise:** one on-slide line with that scope.

4. **Medium — notes / slide 10.** Frozen notes still cite `authority-attribution-review.json` as `3c0d5750…`. Summary’s current receipt is `3bd876c0…` and calls the old hash a known defect. **Revise:** current hash; mark `3c0d5750…` superseded.

5. **Medium — slides 2, 3, 9, 10.** Limitations an AWS/IAM audience must not miss are only in notes: owner connection ≠ restricted-user RBAC; Crew config writable; no enterprise policy floor / immutability; existing VPC/subnet only; no extra networking; no GitHub Actions; configured posture/catalog ≠ native proof; collection log ≠ SEL/security audit. Footers push “full evidence scope” to notes. **Revise:** one visible caveat line on those slides.

6. **Medium — slide 9.** Copy promises posture, denied-command rules, approval mode, and governance. The PNG is an unreadable Gateway telemetry thumbnail (native turn telemetry), not that tour, and does not separate collection health, Gateway telemetry, and security audit. **Revise:** dated stills for posture/governance plus those three labels.

7. **Medium — slide 10 / notes.** `media-review-mcp-controls.json` (`e7ffdfac…`) is in the summary but not in notes’ supporting receipts or slide 10 links, while the memory media review is listed. The four MCP cuts are the IAM core. **Revise:** add that receipt.

**(4) Agreement priorities**

1. Do not accept t=0 posters: require result-frame stills for Crew hook, MCP grant, and IAM, with AWS shown only where native call, service trace, and AWS result are joined.
2. Keep layers strict on-slide: identity-binding ≠ agent tool exposure ≠ Crew hook ≠ MCP grant ≠ target IAM ≠ host permission ≠ enterprise governance.
3. Put owner/RBAC, no policy floor, VPC/GHA scope, and catalog-vs-native-proof on the slides, not only in notes.

**(5) Material unknowns.** Frames after each poster; whether the HTML admin tour is substantive (not in these PNGs; HTML unread). Per-request STS caller identity, sampled PID vs pending approval, independent SEL HMAC, and denied-object digest recompute were not in this packet. Original collector `collection_complete: false`; MCP non-dispatch rests on summarized journal completeness, not re-verified here. No live AWS/IAM or playback validation.
