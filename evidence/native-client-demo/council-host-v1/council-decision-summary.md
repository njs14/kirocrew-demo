# Host edition council decisions

Both requested reviewers returned **CHANGES REQUIRED** for the frozen 14-slide, eight-clip candidate. They agree that the core MCP/IAM boundaries, one EC2 endpoint-control box, owner-editable configuration and the memory-before-tools limitation are now clear. Remaining changes concern visible scope and layout, not re-recording the existing clips.

## Shared recommendations

- **H1 — Name the three pending host cases on slide 4.** Sensitive-path read, protected-path write and IMDS execution. State that no completed IMDS/firewall result is accepted, bounded to the recorded interval. A count and shot-list link disappear as actionable context in a static/printed presentation.
- **H2 — Make the anonymous authentication boundary explicit.** The EC2 helper sends an anonymous loopback request while the Mac session remains authenticated. Label matrix attribution as correlated Gateway-token evidence; retain native_enforcement_verified:false in visible text. HTTP403 alone and the collapsed native output do not explain which identity or enforcer was tested.
- **H3 — Say the command marker rule was temporary and removed.** Add a short slide 11 note: temporary demo rule, removed after the take. Keep post-denial summary-inspection coverage explicit. Replay shows the earlier configuration, not a standing current rule.
- **H4 — Repair the posture crop and label configured controls.** Show three complete rows, keep Expand outside the crop, and state that sensitive/protected-path native denials are pending. Name shell Denied Commands separately from the Crew MCP auto_deny_tools hook. Truncation and a clipped extra row harm legibility, while catalog names can be mistaken for executed tests.
- **H6 — State the recording timezone.** Label the cover September 13, 2026 Eastern Time, or use UTC 13–14 September consistently. The command/auth captures cross midnight UTC but remain September 13 in America/New_York; the existing date is not intrinsically wrong.

## Additional supported recommendations

- **H5 — Balance the two matrix slides and split duplicate notes.** Use 4/4 or 5/3 rows if it improves spacing; make slide 3 andslide 4 presenter notes specific to their rows. Current 6/2 distribution crowds slide 3 and duplicates its notes verbatim.
- **H7 — Keep the role-attribution limit near the IAM scene.** Use a concise footer: role from instance-profile receipts; no per-request STS identity. This tempers model prose inside the actual recorded poster without changing footage.
- **H8 — Align the Crew-scene footer and missing setup references.** Keep duration/evidence-scope display consistent and make the original incomplete-collector versus complete MCP-journal distinction concise. Add receipt-backed SSH/us-east-1 context to notes if those diagram labels remain. This is a documentation/consistency issue; both reviewers accepted the bounded core MCP layering.

The date finding needs a timezone clarification, not an automatic date-range correction. The 14 September 00:00:31 UTC take was recorded on 13 September 20:00:31 Eastern. Preserve the underlying timestamps.

Do not alter existing MP4s or continuous cuts to address these findings. Correct presentation copy/layout and preserve the recorded helper field native_enforcement_verified:false. A direct SEL-to-tool correlation ID is unavailable for the anonymous auth case; the independent review supports exact-input/live-result plus unique temporal/route/caller/reason correlation.

## Exact review provenance

- HTML: `cc139d5d1d47dbc4ed79cb52ade4c972d14427071d5aff866d33ad9cc9070335`.
- Notes: `b4a9e1c3f2bc83687278ae2ce6fff9726df33a9d46a7ed90565fd19fe58baa9d`.
- Manifest: `0c3d937e477caf927c8af2e7f82ee501a7cedaba368a9478df2e06efe8c81d2d`.
- Actual review response IDs: `grok-4.6` and `claude-opus-5`; both streams contain all 14 exact packet PNG payloads.
- Both launches explicitly set `xhigh`; provider wire effort is not independently visible. Usage reports `grok-4.6-build` and Claude usage includes `claude-haiku-4-5-20251001` alongside `claude-opus-5`.
- Both clients exited successfully with one successful terminal result, no malformed JSON lines or sandbox warnings, and unchanged packet/source hashes.
- Original CUA JPEGs remain untouched. Packet PNGs preserve identical decoded RGB24 pixels, with source/capture hashes recorded. A 19-file byte-identical archive preserves the reviewed candidate.

Root has accepted H1–H8 and assigned implementation to `/root/native_control_deck`. The changes remain pending implementation; this synthesis does not accept edited bytes. After incorporation, apply No AI Slop and inspect the changed slides, notes and linked artifacts. External council verdicts apply to the original frozen bytes; final changed bytes need a separate incorporation/delta review. This council did not validate playback, seeking, every frame or live AWS/backend state, and did not directly inspect the full admin tour or diagram outside the slide screenshots.
