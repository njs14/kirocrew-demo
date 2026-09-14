# KiroCrew native client demos and admin tour

The current [14-slide presentation](output/kirocrew-native-controls.html) contains eight native Mac recordings. Five original clips cover Crew/MCP/IAM decisions and private-memory assignment. Three additions show an allowed workspace read, a command-denial response summary and the anonymous helper's execute approval through the HTTP 403 summary. Recording count is separate from the number of fully verified control outcomes. The separate [admin screenshot tour](output/kirocrew-admin-tour.html) explains the controls, four completed turns and client/server collection data.

The endpoint client scope is macOS. EC2 runs the Gateway, original Kiro CLI backend, workspace and separate MCP service. Keep the single endpoint-control box around the remote execution host. The Mac's local Gateway stays off.

## Recorded control demonstrations

The four MCP turns used one dedicated `enforcement-demo` session. Each requested exactly one tool with its own trace ID. Prompts and once-only approvals came from the native Mac application; the evidence collector observed the session without submitting or approving its requests.

| Clip | Observed result | Evidence |
| --- | --- | --- |
| 1. Read the allowed fixture | `read_allowed` returns 55 bytes, the provisioned digest and an AWS request ID after native approval. | Native request/result and approval IDs, matching MCP invocation and S3 success. |
| 2. Hit the Crew-configured deny | `crew_denied` is blocked automatically, without an approval card or MCP arrival. | Host-generated blocked row, one isolated-turn `hook_deny`, complete service journal and stable MCP service. SEL correlation uses the session and turn interval; it has no direct trace join. |
| 3. Hit the MCP grant boundary | `mcp_denied` returns `tool_grant_denied` after native approval. | Matching trace and invocation in the MCP audit, with no AWS dispatch. |
| 4. Hit the IAM boundary | `iam_denied` returns S3 `AccessDenied`, HTTP 403 and an AWS request ID. | Native result, matching MCP/AWS audit, deployed policy and existing-object readbacks. |
| 5. Refuse an unassigned conversation | The server reports no verified assignment to private memory before a tool starts. | Native request/refusal footage, captured `memory_unavailable` event and source-based assignment diagnosis. The attempted file read never ran. |

The [final four-turn reconciliation](evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json) and its [independent review](evidence/native-client-demo/20260913-ui2-reconciled-final/review.json) establish the bounded event joins. [Fresh ARM authority](evidence/native-client-demo/20260913-ui2/authority-arm-readback.json) and [AWS authority](evidence/native-client-demo/20260913-ui2/authority-aws-readback.json) readbacks cover the protected service, running identity, deployed role policy and fixtures. [MCP media review](evidence/native-client-demo/media-review-mcp-controls.json) and [memory-refusal media review](evidence/native-client-demo/media-review-memory-assignment.json) record the continuous cuts, hashes, decode checks and independent sampled-frame inspection.

The original collector receipt remains `collection_complete: false`: its recent SEL API window lost the baseline anchor. A later read-only recovery obtained the bounded interval without rewriting that receipt. The generic reconciler still reports `full_native_acceptance: false`; footage review and authority checks have separate receipts. Process samples do not prove overlap with a pending approval. SEL integrity uses the original Gateway verification, without an independent per-row signature check or exported HMAC key.

Use the published collector exports for the [MCP run](evidence/native-client-demo/20260913-ui2/receipt-publication.json), [memory-refusal take](evidence/native-client-demo/host-20260913-ui1/receipt-publication.json) and [unused host take](evidence/native-client-demo/host-20260913-ui2/receipt-publication.json). Each run also has a `baseline-publication.json`. The exports retain source hashes and collection verdicts while omitting broad SEL pages and complete conversation snapshots. Full originals remain byte-identical, ignored by Git and privately retained; historical source hashes refer to those originals. Scoped `events.jsonl` and the [recovered SEL interval](evidence/native-client-demo/20260913-ui2-reconciled-final/sel-interval.json) supply the bounded event evidence.

The Crew deny is remote configuration that Crew can edit in this demo. The separately protected MCP service and AWS role enforce their own boundaries. The Mac uses an owner connection, and no enterprise governance policy is active. The private-memory clip establishes conversation assignment; restricted human-role authorization and immutable enterprise policy remain untested.

## Host takes after the Mac was unlocked

The first resumed native workspace read succeeded. A separate harmless marker command reached the server and was automatically denied by its configured rule. Its footage shows the assistant's response summary only. The request was submitted before the observer and recording started, and the expanded tool output and policy reason are not visible. Two other attempts stopped in model responses before any tool ran. A later anonymous helper run completed after separate read/execute approvals and returned HTTP 403. Sensitive-path read, protected-path write and metadata TCP isolation remain unfinished. The IMDS execution approval expired unanswered after ten minutes, with no helper execution or firewall result observed. A fresh slot failed screenshot readiness and received no prompt.

| Take | Current observation | Required decision evidence |
| --- | --- | --- |
| Allowed workspace read | One native `fs_read` returned the prepared public canary. | Exact tool request and marker result are captured. No permission event appeared; this is not an approval-callback test. |
| Anonymous server authentication | A later request approved the exact helper read and execution separately, then returned HTTP 403. | The clip starts at execute approval and ends at the assistant's 403 summary; source-read approval and expanded tool output are outside the excerpt. Matched token-auth evidence supports the outcome. |
| Sensitive-path read | First request received a model-only refusal; no file tool ran. | Actual native read of the exact prepared canary, automatic path denial and matching server event. |
| Protected-path write | Request a new harmless marker under the dedicated agent fixture directory. | Automatic write denial and marker absent before and after. |
| Server command rule | Persisted native history contains the exact blocked `printf` request and matching isolated-turn `hook_deny`. | Assistant response-summary inspection footage is recorded; expanded tool output and policy reason are not visible. A complete prompt-to-denial recording remains a separate gap. |
| Metadata connection isolation | Helper read was approved; the execute approval expired unanswered after ten minutes. No helper execution or probe result was observed. | Actual process UID, effective host rule and connection result. A connection timeout alone leaves attribution unresolved. |

The folder-created `chat-4-1789335946` completed the workspace read and two model-only refusals. The command denial occurred in `chat-5-1789343728`. Read the [resumed host appendix](docs/NATIVE-CLIENT-DEMO.md#resumed-host-observations) for the exact evidence and capture limits. The earlier [zero-event capture](evidence/native-client-demo/host-20260913-ui2/capture-status.json) and private-memory refusal retain their original scope. The [IMDS timeout correlation](evidence/native-client-demo/host-20260913-ui4/prior-imds-timeout-correlation.json) records the expired approval; the [unused fresh-slot observer](evidence/native-client-demo/host-20260913-ui4/unused-slot8-observer.json) records zero events and no submitted prompt. For the remaining cases, confirm that actual screenshots show the current folder-created chat and reviewed `host-controls-demo` instructions, then start a fresh observer and raw recording before sending its first prompt.

Use the exact prompts and acceptance checks in [the host-control shot list](docs/HOST-CONTROL-SCENARIOS.md). The custom rule `KIROCREW_DEMO_COMMAND_CONTROL_20260913` was added through the admin UI and removed after the take. The [cleanup readback](evidence/native-client-demo/host-20260913-ui3/command-rule-cleanup.json) confirms the exact marker and rule ID are absent, with no built-in IDs disabled. A repeat command take needs a newly added bounded marker rule and its own cleanup; keep built-in rules enabled. Restricted human identity, filesystem profiles and namespace-write demonstrations need separate setup before they become recording candidates.

## Finish the presentation walkthrough

1. Complete the three remaining host cases and decide whether to recapture the command denial from prompt submission. Verify the session, services and fixture hashes. The prior custom marker has been removed; only a repeat command take needs a new bounded rule. Approve only the bounded request shown in the native client; preserve any substituted tool, missing input or unexpected result as a failed take.
2. Correlate each result with the relevant server evidence. Record the first control that stopped it. A hook denial before helper execution leaves the later filesystem or network boundary untested.
3. Export reviewed continuous cuts with FFmpeg, source hashes, posters and timestamped cues. Preserve all raw failure takes privately and keep their receipts. Append completed scenes with `scripts/build-native-control-presentation.py --manifest`; use the existing processed manifests as inputs.
4. Walk through the separate admin tour. Explain configured coverage, policy authority, backend status, Gateway turn metrics and custom client/server collection events. The latter do not contain all SEL or MCP decisions.
5. Verify playback, cue seeking, keyboard controls and evidence delivery for the final edition. Complete the requested Grok 4.6 xhigh and Opus 5 xhigh council review on a frozen candidate, incorporate agreed findings, then apply No AI Slop and verify the edited output.
6. Update the status and delivery receipts, verify any new temporary-rule cleanup, and publish the reviewed artifacts to the existing private repository. GitHub Actions remain out of scope.

Keep the accepted deck, PowerPoint, diagrams and earlier receipts unchanged. New infrastructure uses explicit CloudFormation parameters for an existing VPC and subnet; this recording work does not add network infrastructure or redeploy the accepted stack.

## Earlier recordings

The previous September 13 edition contains six validated clips of the architecture reference, admin navigation, custom telemetry, Gateway instrumentation, a direct MCP/AWS probe and a synthetic rehearsal. They remain supporting material with their original scope. Their earlier sign-in failure was superseded by the [successful native CLI authentication](evidence/native-client-demo/20260913/authenticated.json) and completed turns in this edition.

The [prior plan](docs/history/DEMO-RECORDING-PLAN-before-native-focus.md), [recording receipt](DEMO-RECORDING-RECEIPT.json) and [recording guide](DEMO-RECORDING-GUIDE.md) retain the historical result and failure takes.

## What changed

Preserved the five-clip edition and added the resumed workspace success and bounded command-denial evidence. Distinguished two model-only refusals from server decisions, added the later anonymous-helper 403 with read/execute approvals, and retained three pending cases and the command request-capture gap. Replaced the earlier pending IMDS status with its unanswered approval timeout and recorded the unused fresh slot.
