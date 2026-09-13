# Native controls council decisions

Both requested reviewers returned **CHANGES REQUIRED** for the frozen ten-slide candidate. Their substantive recommendations agree. This document proposes the joint decisions for root to incorporate; it does not mark a changed deck accepted or the No AI Slop pass complete.

## Candidate and review evidence

- Frozen HTML: `ac06b8132961dfc35cccc5d1c470ca0ff5b395ec7f7044659803f4ea7b0be8a7`.
- Frozen notes: `612775125751c05138e39a13bd2d88814e6c58b6ef49f48d338cb69acf24f78c`.
- Packet manifest: `74280ad40e10efaf66fe465f0a0f4e472a20e5f60fc02f6eec2edd8a2f24fa4a`.
- Actual review response IDs: `grok-4.6` and `claude-opus-5`. Both read all ten exact packet PNG payloads and exited successfully, with one successful terminal result and no malformed stream lines or sandbox warnings.
- Both launches explicitly requested `xhigh`; provider wire effort is not independently visible. Usage accounting reports `grok-4.6-build` and, for Claude, both `claude-opus-5` and `claude-haiku-4-5-20251001`. This does not prove every internal call used only the requested review model.
- The original CUA captures were JPEG bytes with .png names. The strict preparation gate rejected them before inference. Original bytes are preserved; PNG encodings have identical decoded RGB24 hashes and a recorded conversion chain.
- Council members inspected slide screenshots and the source-bound summary, not raw live AWS state, every video frame, browser playback or the separate admin guide. The runner independently verifies hashes and observed image payloads; the models themselves did not compute hashes.

## Joint revisions

| Decision | Council agreement | Minimal change | Verification after change |
|---|---|---|---|
| D1 — Match the poster to the demonstrated outcome | Both: slides 5–7 currently show the previous turn; Grok also identifies idle/fixture posters on slides 4 and 8. | Use an actual stable result frame from each existing continuous clip as its poster. Allowed read shows the permitted result; Crew shows Tool call blocked; MCP shows tool_grant_denied; IAM shows AccessDenied/403; memory shows the assignment refusal. Do not alter or synthesize video evidence. | Inspect the five displayed posters and each full-size result frame. Confirm poster timestamps remain inside the corresponding existing cut and source hashes stay unchanged. |
| D2 — State server authority limits on the architecture slide | Both: owner authority and the absence of a governance floor are hidden in notes. | Add one readable line: current session has owner authority; Crew configuration is owner editable; no enterprise policy floor. Preserve the single EC2 endpoint-control box. | Inspect slide 2 at 1280×720 and verify the box count. |
| D3 — Name the private-memory refusal precisely | Both: the visible fixture/host label can be mistaken for filesystem or RBAC enforcement. | Say the existing conversation was switched to a private-store alias. Add: conversation assignment guard; request stopped before a tool turn; no restricted-user RBAC or filesystem denial established. | Inspect slide 8 and align it with the assignment diagnostic and original footage. |
| D4 — Repair evidence references | Both: authority review hash is stale and the four MCP clips lack their media review in the visible supporting set. | Update authority-attribution-review to the current exact hash. Add media-review-mcp-controls.json and authenticated.json to the notes/supporting links. Preserve the prior hash in historical council receipts only. | Recompute hashes and resolve each link through the final allowed-file server. |
| D5 — Show what the admin guide covers and separate evidence types | Both: the single small telemetry thumbnail is insufficient for the stated posture/rules/governance tour. | Use readable, dated posture and governance images on slide 9 or a clear paired preview; keep the full guide link. Label configured coverage, native Gateway telemetry, and collection health logs. State that health logs are not the security audit. | Root separately reviews the actual guide and its images; inspect final slide 9 for readable labels. |
| D6 — Keep evidence scope visible without filling slides with disclaimers | Both: material layer limits should not require presenter notes. | Add a short slide 3 attribution line: outcomes are correlated to joined server receipts. Retain six additional host takes as unrecorded. Keep networking/Actions scope compact on the final slide or notes where it is already explicit. | Inspect slide 3 and final slide; do not upgrade original collection_complete:false or claim immutable policy, complete enterprise acceptance or pending PID overlap proof. |

## Other findings and disposition

- Opus notes a one-second overlap between existing MCP and IAM source cuts. This is not evidence corruption: both are continuous, disclosed cuts of the same raw recording, and the overlap precedes the IAM submission. Result-frame posters fix the misleading static view. Prefer preserving the existing accepted media bytes unless root's playback review finds the shared lead-in confusing enough to justify new derivatives.
- Opus notes a 25-second player label versus a 26-second rounded duration. Use consistent nearest-second display for a 25.998058-second clip; do not change the underlying media or falsify precise duration metadata.
- The packet normalizes `slide-01.png` source names to `slide-1.png`, which is explicit in the runner's source map and exact hashes. The summary calls the source file `capture-binding.json`, while its normalized packet name is `capture-receipt.json`. The reviewers confirmed hash agreement; no integrity failure occurred. Preserve the frozen packet and document this naming transformation rather than silently rewriting review inputs.
- Grok asks for joined native/service/AWS result stills. The existing result-frame poster plus a concise source-bound evidence label can make that attribution visible. Do not fabricate a composite application screenshot or imply the model council itself verified live dispatch.

## Follow-through status

- Council reviews completed: yes.
- Exact packet unchanged after both reviews: yes.
- Joint decisions incorporated: pending root/deck worker.
- Final derivative browser and link checks: pending root.
- No AI Slop pass after incorporation: pending root/deck worker.
- Additional six host control recordings: outside this frozen candidate and remain unrecorded here.
