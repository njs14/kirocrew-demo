# System-design HTML council

Both requested reviewers completed and returned **CHANGES REQUIRED**. They found presentation clarity and provenance issues, without requesting structural redesign. Their raw reviews remain unchanged. Root owns decision incorporation and the subsequent no-ai-slop edit.

- HTML SHA-256: `bfc2516128526ab049a7c4c0b36994aae82d87c44790785ee9125da5d63a5712`.
- Notes SHA-256: `b7fc925872ed5be0c285537f7415781bb4dd96b4cc294c205d26b8e247602269`.
- Packet manifest SHA-256: `da036f95026defc582acbecd2109f0c905f1266c250afccc7442b73758802d02`.
- Models: Grok Build `grok-4.6` and Claude Code `claude-opus-5`. Both launched with explicit `xhigh`; response model IDs matched exactly.
- Both raw streams contain all fourteen JPEG payloads with hashes matching the frozen browser screenshots. They also read the manifest, exact text/notes and sanitized evidence summary. Both completed with one successful terminal result, exit code 0 and empty stderr.

## Shared actionable findings

| Priority | Slide | Finding | Recommended disposition |
|---|---|---|---|
| 1 | 9 | Empty native model-metric chips show zero latency/rate/throughput and can look like actual session measurements. | Add a visible caption stating that native model-session metrics are empty and pending. Keep the existing 14-day display-window, seven-day retention and one-boot-observation qualifications. Add text around the original screenshot; preserve its pixels. |
| 1 | 4 | The only drawn entry into MCP is the pending native path. The verified direct probe appears only in the caption. | Add a clearly labeled direct-probe entry into MCP while keeping the Gateway/native path dashed and pending. Preserve the single endpoint-control boundary. |
| 2 | 3 | The preserved reference's protected-configuration and enterprise-control labels can outweigh the disclaimer. | Make the reference date/scope prominent and mention that Crew configuration is writable and protected policy is not established here. Keep the accepted endpoint-control image unchanged. |
| 2 | 10–11 | Small embedded evidence rows need a visible way to inspect the original. | Add an `Expand to inspect` cue, including the reference slide where useful. Root owns verification of actual expansion behavior. |

Both reviewers agree that native CLI sign-in, native approval and automatic pre-MCP Crew denial remain pending. The dated direct probe, native Gateway metrics, custom samples, collection events and SEL are separate evidence classes. Keep these qualifications through the no-ai-slop pass.

## Additional recommendations for root adjudication

| Slide | Reviewer | Recommendation |
|---|---|---|
| 14 | Opus | Put a pending marker on native sign-in and state what to do if sign-in fails. Steps 1–3 remain the demonstrated path. An approval card on `crew_denied` still fails native acceptance. |
| Header | Opus | Clarify the `Original PPTX` link's provenance. See the correction below: it is the prior final ARM deck, not the frozen review candidate. |
| 5 | Grok | Separate observed checks from attached role-policy permissions; SSM core attachment is not proof that SSM was exercised. |
| 5 | Grok | State that installed custom App Kit files are Crew-writable alongside the existing writable-configuration disclosure. |
| 5 | Opus | Identify the trusted administrator as the operator's SSH account with sudo; this also explains the probe and owner-token helper. |
| 10 | Grok | Name owner/admin-portal authentication explicitly so it cannot be mistaken for standalone Kiro CLI authentication. |
| 11 | Opus | Label collection events as operational telemetry, separate from security audit/SEL records. |
| 12 (or 4) | Grok | Name the stopped `t3a.small` and its retained 24 GiB rollback disk explicitly. |
| 1 | Opus | Prefer `telemetry collection active` over the broad `telemetry verified`, while retaining the actual collection and API evidence. |

## Findings that need precise interpretation

- **PPTX provenance:** Opus calls the download a superseded candidate but also says it did not open it. Dispatcher inspection of the frozen HTML's embedded PPTX yields SHA-256 `37c82c82a00f16694f82fd11d2eda4c6188ce49de233b0c52448c47b820e0c13`, the final accepted 12-slide ARM deck after decisions and no-ai-slop. A label such as `Source PPTX (12-slide ARM edition)` is supported. Calling it the reviewed candidate or claiming its contents contradict this HTML is not supported.
- **Protected paths:** Crew's demo configuration is writable. That does not establish that every path-protection mechanism in the historical reference is ineffective. State the demonstrated writable surface and the unverified enforcement scope without extrapolating to all protected paths.
- **Telemetry:** Actual collection, emitted observations, API readback and browser observations are recorded. Empty native model-series values do not invalidate those operational measurements. Limit the headline wording without downgrading the underlying observations to configuration-only.
- **Screenshot edits:** Grok suggests striking or annotating metric chips. An adjacent caption can resolve the ambiguity while preserving the exact historical screenshot. No source-image modification is required.
- The reviewers did not inspect underlying runtime receipts or live state. Their material-unknown lists identify packet limits, not new evidence that a configured setting or recorded check is absent from the project.

## Receipt scope

`council-verified-receipt.json` records the packet, raw-stream and launcher hashes, exact image payloads, observed tool calls and response model IDs. The source HTML, notes and screenshots still matched the packet at post-review verification. Later revised presentation bytes are outside this council's scope.

Both used explicit xhigh launch configuration. Provider-internal effort is not independently visible. Grok usage accounting uses `grok-4.6-build`; Claude usage accounting includes `claude-haiku-4-5-20251001` alongside `claude-opus-5`. Every observed review response model was the exact requested model, but these receipts do not claim that all internal product activity used only those two models.

The reviewers did not render or operate the HTML. Final browser interaction and layout checks, decision incorporation and the new no-ai-slop pass remain root's work. No AWS, UI, authentication or runtime changes were performed by this council task.
