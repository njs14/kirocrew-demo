# KiroCrew native client demos and admin tour

The current [10-slide presentation](output/kirocrew-native-controls.html) contains five real macOS KiroCrew clips. Four show a user reaching the EC2 Crew, MCP and AWS controls; the fifth shows the server refusing an unassigned conversation before private-memory access. The separate [admin screenshot tour](output/kirocrew-admin-tour.html) explains the controls, four completed turns and client/server collection data.

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

## Six prepared host takes

The fixtures, fixed helpers and separate `host-controls-demo` agent are installed and reviewed. These six native outcomes remain unrecorded because the Mac locked before the corrected session's first prompt.

| Take | Bounded client action | Required decision evidence |
| --- | --- | --- |
| Allowed workspace read | Read the prepared public workspace canary once with `fs_read`. | Actual request and returned marker match the fixture. |
| Anonymous server authentication | Run the fixed no-argument loopback HTTP helper once. | Rejected authentication status and matching server context. |
| Sensitive-path read | Read the public canary under Crew's `.aws` directory once. | Automatic path denial and matching server event; the canary exists. |
| Protected-path write | Request a new harmless marker under the dedicated agent fixture directory. | Automatic write denial and marker absent before and after. |
| Server command rule | Request the harmless command containing the exact custom deny marker. | Enabled rule, automatic denial and matching event. |
| Metadata connection isolation | Run the fixed IPv4 IMDS TCP helper once, sending zero application bytes. | Actual process UID, effective host rule and connection result. A timeout alone leaves attribution unresolved. |

The corrected blank session is `chat-4-1789335946` in **Host control demos**, with `host-controls-demo` assigned at creation and workspace `/srv/kirocrew-demo/workspace`. Recheck that state after the Mac is unlocked. The [unused capture](evidence/native-client-demo/host-20260913-ui2/capture-status.json) and observer are finalized with zero captured events and zero session messages. Start a fresh observer and raw recording before sending the first prompt. The earlier `chat-3-1789335506` refusal remains a separate identity-binding observation.

Use the exact prompts and acceptance checks in [the host-control shot list](docs/HOST-CONTROL-SCENARIOS.md). The custom rule `KIROCREW_DEMO_COMMAND_CONTROL_20260913` was added through the admin UI for these takes. Remove only that added rule after recording and retain the cleanup receipt. Keep the 112 built-in rules unchanged. Restricted human identity, filesystem profiles and namespace-write demonstrations need separate setup before they become recording candidates.

## Finish the presentation walkthrough

1. Resume the six host takes after the Mac is unlocked. Verify the session, services, fixture hashes and exact enabled custom rule. Approve only the bounded request shown in the native client; preserve any substituted tool, missing input or unexpected result as a failed take.
2. Correlate each result with the relevant server evidence. Record the first control that stopped it. A hook denial before helper execution leaves the later filesystem or network boundary untested.
3. Export reviewed continuous cuts with FFmpeg, source hashes, posters and timestamped cues. Preserve all raw failure takes privately and keep their receipts. Append completed scenes with `scripts/build-native-control-presentation.py --manifest`; use the existing processed manifests as inputs.
4. Walk through the separate admin tour. Explain configured coverage, policy authority, backend status, Gateway turn metrics and custom client/server collection events. The latter do not contain all SEL or MCP decisions.
5. Verify playback, cue seeking, keyboard controls and evidence delivery for the final edition. Complete the requested Grok 4.6 xhigh and Opus 5 xhigh council review on a frozen candidate, incorporate agreed findings, then apply No AI Slop and verify the edited output.
6. Update the status and delivery receipts, remove the temporary command rule, and publish the reviewed artifacts to the existing private repository. GitHub Actions remain out of scope.

Keep the accepted deck, PowerPoint, diagrams and earlier receipts unchanged. New infrastructure uses explicit CloudFormation parameters for an existing VPC and subnet; this recording work does not add network infrastructure or redeploy the accepted stack.

## Earlier recordings

The previous September 13 edition contains six validated clips of the architecture reference, admin navigation, custom telemetry, Gateway instrumentation, a direct MCP/AWS probe and a synthetic rehearsal. They remain supporting material with their original scope. Their earlier sign-in failure was superseded by the [successful native CLI authentication](evidence/native-client-demo/20260913/authenticated.json) and completed turns in this edition.

The [prior plan](docs/history/DEMO-RECORDING-PLAN-before-native-focus.md), [recording receipt](DEMO-RECORDING-RECEIPT.json) and [recording guide](DEMO-RECORDING-GUIDE.md) retain the historical result and failure takes.

## What changed

Recorded five native control clips and linked their evidence. Added six prepared host takes with explicit remaining checks, the corrected session setup and temporary-rule cleanup. Made the new presentation and separate admin screenshot tour the current entry points.
