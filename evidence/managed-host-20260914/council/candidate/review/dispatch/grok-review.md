**CHANGES REQUIRED**

Candidate `managed-host-v1` keeps one EC2 endpoint-control enclosure, dates earlier clips as pre-managed, and does not turn Linux cc, process samples, or local MCP enablement into Seatbelt, SSO, RBAC, or a second live deployment. The three September 14 host takes are receipt-supported and correctly layered in slides 14–16. Presenter notes for slide 18 still describe those takes as unfinished, and the updated control map collides with its footer. That is enough to block this as a finished AWS/IAM briefing.

## Image coverage

All 19 listed captures were read as pixels: `slide-1.png` through `slide-19.png`. None unread. Receipt names `slide-01.png`…`slide-19.png`; printed SHA-256 values match the manifest files I was given. Coverage is still-frame slide chrome, titles, captions, posters, and media controls only. It does not verify playback, seeking, audio, or any video frame after the poster. I did not open `presentation.html`, follow links, execute anything, or inspect other paths. No live check.

## New host-control cases (receipt-backed)

| Case | Request | Native attempt | Approval | Visible in this packet | Attribution (not the poster) |
|---|---|---|---|---|---|
| Sensitive read (14) | `fs_read` `/home/crew/.aws/kirocrew-demo-control-canary.txt` | 1 tool call; 0 blocks | none | assistant path-missing; poster is the request | CLI argument-validation ENOENT (`accepted:false`). Host file existed. Later readback of **current** CLI descendants shows `.aws` tmpfs; no historical syscall PID. Not a Crew hook. |
| Protected write (15) | `fs_write` disposable marker under `/home/crew/.kiro/agents/.demo-host-controls/` | 1 `fs_write` blocked | none | notes: Tool call blocked + write-protected-config-path; poster is the request | `crew_write_protected_path_hook` + isolated SEL `6e1003553ace4e4b`; target absent before/after. Hook precedes the managed filesystem rule; not kernel isolation. Product also shows “1 file changed” / “no changes.” |
| IMDS TCP (16) | read then run `/usr/bin/python3 /opt/kirocrew-demo/host-controls/imds-tcp.py` | 2 calls (read ≠ execute) | Allow once ×2 | notes: `connected:false`, errno 113, 0 app bytes, no metadata; poster is the request | Helper self-report keeps `native_enforcement_verified:false`. Separate correlation: UID 999 first IPv4 OUTPUT REJECT, packets 2→3. Not whole-host routing, HTTP, credentials, IPv6, or all egress. No per-packet tool ID or helper PID. |

## Findings

1. **High — notes 18 (echoed in evidence-summary “Managed source and limits”).** Notes still say “Sensitive-path read, protected-path write and native IMDS execution remain unfinished.” Slides 14–16 and the embedded Sept 14 receipts record those takes (write/IMDS `accepted:true`; sensitive recorded but `accepted:false`). That resets finished cases to the older pending state. **Revision:** delete or rewrite that sentence to the dated outcomes; if the 02:20 UTC summary ships with the deck, mark it as pre-take assembly time.

2. **High — slide 4.** Footer “Recording coverage and server attribution are separate. Page 2 of 2.” overlays the IMDS duration `0:55` on the updated control map. **Revision:** keep the last row and footer from overlapping.

3. **Medium — slide 13.** Chapter body for the ui4 request is clipped (scrollbar); trace `managed-20260914-ui4-crew` is not fully visible. Notes have the full line. **Revision:** show the composed tool and trace without clipping.

4. **Medium — slides 14–16.** Unlike slides 5–8 and 13, posters are READY/composer request frames, not ENOENT, the block, or the TCP result. A poster does not prove those later frames. **Revision:** result-frame posters, or an on-slide caption that the poster is the request and the result is at the stated chapter time.

5. **Medium — slide 4, Sensitive-path row.** Visible result “ENOENT; current .aws mask corroborated” can be read as the mask being the native enforcer. Receipt first enforcer is `kiro_cli_argument_validation`; the mask is later descendant readback. **Revision:** keep CLI ENOENT as the result; qualify the mask as later, current-descendant corroboration.

6. **Low — slide 19.** “New recording scope and quality” appears twice. **Revision:** one label, or two distinct labels if the targets differ.

## Agreement priorities

1. Treat notes 18 / the 02:20 “unfinished” bullet as stale leftover (must-fix), not as admin-tour-only language.
2. Treat the slide 4 footer/duration collision as a control-map ship blocker.
3. Decide whether slides 14–16 need result-frame posters, or whether captions plus notes are enough given PNG coverage limits—without promoting the later `.aws` readback into a filmed hook denial.

## Material unknowns

Playback, seeking, and non-poster frames. Independent hashing of this tree versus the claimed manifest digest. Gateway process continuity from the ui4 interval (02:06Z) through the 13:xxZ host takes. Historical syscall PID for the sensitive read. IMDS helper PID and per-packet tool-call identity. Exact hrefs behind the duplicate slide 19 labels (`presentation.html` unread). Completeness of the ui4 MCP journal beyond the stated reviewed interval.
