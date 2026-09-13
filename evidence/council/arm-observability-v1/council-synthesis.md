# ARM and observability deck council

Both requested reviewers completed and returned **CHANGES REQUIRED** for the frozen 12-slide candidate. This is completed review evidence, not acceptance of the deck. Root owns the next revision and the subsequent no-ai-slop pass.

- Candidate: `output/kirocrew-arm-observability-demo-candidate-v2.pptx`
- PPTX SHA-256: `99d10eee8723b3998c40f52e902602661138e7388f0d6d3db8e2d5ef13f63dd9`
- Packet manifest SHA-256: `f99ba433ccb533fe0142ebad8810b58a6b159a127696913331d9f2f118a511f8`
- Requested/observed response models: Grok Build `grok-4.6`; Claude Code `claude-opus-5`.
- Both launched with explicit `xhigh`. The provider's internal effort setting is not independently visible.
- Both raw streams contain successful reads of all 12 slide PNGs, with decoded image payload SHA-256 values matching the manifest. Both also requested only the packet manifest, exact text/notes, and sanitized evidence summary. No other reviewer tool calls were observed.
- Both exited 0 with exactly one successful terminal result. Packet and source artifacts remained unchanged.

## Changes both reviewers explicitly recommend

| Priority | Slides | Agreed finding | Minimal revision |
|---|---|---|---|
| 1 | 9–10 | Screenshot clocks show Eastern time while visible claims use UTC. The offset is only in notes. | Add `Screenshot clocks: EDT (UTC−4)`. Root already queued slide 10's more precise labels: `Stopped sample: 14:44:42 UTC · Recovery sample: 14:49:34 UTC`. These are collection samples, not exact process-action timestamps. |
| 1 | 10 | The displayed collection log does not show the Gateway PID/start-time evidence behind the continuity claim. | Attribute the claim: `Collector receipt: Gateway PID 4991, started 14:26:10 UTC, unchanged`, or add the corresponding server/stopped-client receipt panel. Keep the claim limited to process continuity; native model-session survival remains pending. |
| 2 | 8 | The native UI's `Last 14d` display range can be mistaken for configured retention. | Label `14-day display window · 7-day retention · 64 MiB target`. Preserve the distinction between this pane's emitted observations and exporter configuration. |
| 2 | 12 | The visible rate omits the Standard CPU-credit mode supporting the estimate. | Name `t4g.xlarge · Standard CPU credits` and `stopped t3a.small · 24 GiB still billed`. Mention that sustained CPU load can throttle to baseline. Keep the current cost arithmetic; both found it consistent with the supplied summary. |

Both reviewers also agree that native sign-in, native approval, `crew_denied` before dispatch, model-turn metrics, and model-session survival remain pending; the direct MCP probe cannot stand in for a native Crew session. Preserve the single endpoint-control image and the laptop/client versus remote EC2 execution split.

## Additional findings for root adjudication

These are reviewer recommendations, not a second-round consensus vote or approved edits.

Root subsequently accepted the shared findings and material additional findings. Root reports a fresh blocked crew-UID IMDS request receipt and a new direct MCP probe around 15:01 UTC. The next deck will bind those fresh receipts and identify the direct probe as a separate check; it should not reuse the historical claim that the newly substituted probe preceded the current Gateway. Root records the final decisions in `DECISIONS.md`. These new facts were not part of the frozen council packet.

| Priority | Slides | Reviewer | Recommendation / evidence boundary |
|---|---|---|---|
| High | 3 | Opus | Visually distinguish the configured, unverified Gateway→MCP native path from the verified direct MCP→S3 probe. A dashed path with a pending label and a `Verified: direct MCP probe` footer avoids solid-green implying native success. This is consistent with both reviewers' agreement priority to preserve native-pending status. |
| Medium | 6 | Opus | State that the 14:07:16 UTC direct probe precedes the current Gateway process and telemetry window. They are separate checks; no single end-to-end native run is proved. |
| Medium | 2 | Opus; Grok supports preserving the reference boundary | Make the reference disclaimer/exclusions more prominent without changing the accepted endpoint-control image. Both noticed `Policy n Profile` inside the preserved image; flag it rather than silently changing the image bytes. |
| Medium | 4 | Opus | A blocked crew-UID metadata-request receipt was not included in the review packet. Root should consult the actual current receipt before changing a verified-control claim to configured-only. Add the relevant evidence or qualify the statement. The reviewers' packet visibility is not proof that no receipt exists. Make Crew's writable configuration/root-trusted boundary clear without inventing tamper resistance. |
| Low | 5 | Grok | Mark `crew_denied` as configured and not native-probed in its table row, in addition to the pending footer. |
| Low | 7 | Opus | Explicitly call the server ARM64 repack unofficial; Mac is one nightly ahead and behavioral equivalence is not claimed. |
| Low | 8 | Grok | The one-sample boot pane has approximate percentile values outside its displayed min/max. Do not interpret n=1 percentiles as a boot distribution; mention that limit in notes. Do not label a UI defect as proved without inspecting its implementation. |
| Low | 8 | Opus | Improve the dim log-scale explanatory text for projection if practical, preserving screenshot provenance. |
| Low | 9 | Opus | Label client CPU as a process-family measure and server CPU as whole-host. They are different scopes. |
| Low | 3 | Grok | Optionally add the custom Demo Observability loopback `:9102` path to the current deployment diagram. Keep it separate from native telemetry and the accepted endpoint-control reference. |

## Provenance and limits

Raw reviews are `candidate/dispatch/grok-review.md` and `candidate/dispatch/claude-review.md`. Raw provider streams, launcher configuration, individual receipts, and the combined receipt are preserved beside them. `council-verified-receipt.json` binds those artifacts to the candidate and records the observed tools and image coverage.

The response model IDs exactly match the request. Grok's usage record uses `grok-4.6-build`. Claude's usage includes `claude-haiku-4-5-20251001` alongside `claude-opus-5`; all observed review-response model IDs are `claude-opus-5`. The stream does not explain the helper usage, so this receipt does not claim exclusive overall use of Opus.

The reviewers read all slide pixels plus exact slide text/notes and a sanitized evidence summary. They did not render/open the PPTX, calculate the candidate hash themselves, inspect live AWS, or inspect underlying runtime receipts. The dispatch verifier establishes the byte binding; project/runtime verification remains separate. Their findings about omitted evidence must be adjudicated against the actual project receipts.

Native backend authentication remained pending in this frozen candidate. Root's subsequent changes and no-ai-slop revision will produce new bytes; this council receipt must not be relabeled as a review of those later bytes.
