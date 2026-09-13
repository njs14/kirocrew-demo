# Native Mac client demo

The demonstration follows a macOS KiroCrew user from a request to the server’s decision. The Mac displays the conversation and approval controls. The EC2 host runs the Gateway, selected Kiro CLI backend, workspace and purpose-built enforcement MCP. The local Mac Gateway stays off.

## Current recorded results

The [10-slide native presentation](../output/kirocrew-native-controls.html) contains five clips: an allowed S3 read, Crew tool denial, MCP grant denial, IAM `AccessDenied` and a private-memory assignment refusal. The four MCP turns completed on September 13, 2026 through the original Kiro CLI backend after its fresh standalone sign-in. The Mac's local Gateway was off.

The [final reconciliation](../evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json) joins the four native turns to the bounded server interval. Its [independent review](../evidence/native-client-demo/20260913-ui2-reconciled-final/review.json) reproduced those joins. The [ARM readback](../evidence/native-client-demo/20260913-ui2/authority-arm-readback.json) verifies the separately protected MCP service and process identity; the [AWS readback](../evidence/native-client-demo/20260913-ui2/authority-aws-readback.json) checks the deployed role policy and existing fixtures. The [MCP clip review](../evidence/native-client-demo/media-review-mcp-controls.json) and [memory clip review](../evidence/native-client-demo/media-review-memory-assignment.json) cover the encoded media and inspected frames.

Keep the original collection failure visible. The collector's recent SEL API window lost its baseline anchor, so its receipt remains `collection_complete: false`. A later read-only recovery obtained the relevant retained rows. The generic reconciler preserves `full_native_acceptance: false` because it does not decide footage acceptance or every attribution check. Neither the readback nor reconciliation proves that process sampling overlapped a pending approval. The original Gateway verification supplies the SEL integrity observation; no independent per-row signature verification is claimed.

The published collector receipts cover the [MCP run](../evidence/native-client-demo/20260913-ui2/receipt-publication.json), [memory refusal](../evidence/native-client-demo/host-20260913-ui1/receipt-publication.json) and [unused host take](../evidence/native-client-demo/host-20260913-ui2/receipt-publication.json). Each has a companion `baseline-publication.json`. Full originals contain unrelated authentication details, so they remain byte-identical, ignored by Git and privately retained. Their SHA-256 values remain valid private-source references. The publication exports preserve the collection verdicts and link scoped native events; use the [recovered SEL interval](../evidence/native-client-demo/20260913-ui2-reconciled-final/sel-interval.json) for the four-turn joins. This publication step adds no new collection or enforcement verdict.

Six additional host takes are prepared and await a native recording. The Mac locked before the corrected host session's first prompt. The [host-control shot list](HOST-CONTROL-SCENARIOS.md) covers allowed workspace access, anonymous authentication, sensitive paths, protected writes, a custom command rule and IPv4 metadata connection isolation. Their outcomes remain unobserved.

## Prepare another MCP take

Use the existing configured SSH connection and a dedicated `enforcement-demo` session in `/srv/kirocrew-demo/workspace`. Verify the remote standalone CLI’s current authentication and start a new session after selecting Kiro CLI. The admin page’s GitHub sign-in card can report KAS identity independently of the standalone CLI. The [fresh authentication receipt](../evidence/native-client-demo/20260913/authenticated.json) records the September 13 sign-in. The completed-turn receipts above establish the subsequent native results. Recheck authentication before another take.

Confirm Interactive approval, healthy Gateway and MCP services, and the provisioned allowed-object digest. Capture the server process/start identity before and after the run. The passive observer should save bounded native events, relevant SEL records and the complete MCP journal interval. Keep authentication tokens, process environments and raw identity output out of receipts.

Record the native application window. The operator enters each prompt and uses the visible native approval control. A separate API runner can verify implementation behavior, but its submitted turns do not fulfill this client recording brief. A successful sign-in or short capture preflight establishes readiness for a new run; its outcomes still need their own evidence.

## Four native turns

Choose a new run ID, then replace `<RUN>` in these prompts. Use each trace once, wait for the turn to finish and retain its actual tool-call ID.

| Order | Prompt to enter in the Mac client | Presenter cue |
| --- | --- | --- |
| 1 | Call the `aws-enforcement` MCP tool `read_allowed` exactly once with only `trace_id="native-<RUN>-allow"`. Do not use another tool, a shell, or a retry. Report the tool result. | Read the tool and trace on the approval card. Approve once, then show the allowed fixture’s digest. |
| 2 | Call the `aws-enforcement` MCP tool `crew_denied` exactly once with only `trace_id="native-<RUN>-crew"`. After a denial, stop and report it. Do not use another tool, a shell, or a retry. | Show the automatic Crew refusal. It should appear before an interactive card or service arrival. |
| 3 | Call the `aws-enforcement` MCP tool `mcp_denied` exactly once with only `trace_id="native-<RUN>-mcp"`. After a denial, stop and report it. Do not use another tool, a shell, or a retry. | Approve this exact request once. Show the MCP grant refusal and the absence of AWS dispatch in the matched audit. |
| 4 | Call the `aws-enforcement` MCP tool `iam_denied` exactly once with only `trace_id="native-<RUN>-iam"`. After a denial, stop and report it. Do not use another tool, a shell, or a retry. | Approve this exact request once. Show S3’s denial and the matching AWS request ID. |

Read the complete native request before each approval. The inspected Nightly can omit canonical server/tool identity from parameterized HTTP approval cards; a matching title alone is insufficient. Verify the trace and complete inputs through the actual request and native evidence. If inputs are hidden, extra or ambiguous, stop that take. Keep approval limited to the single reviewed request.

If `crew_denied` produces an approval card, refuse it for containment and mark the take failed. A manual refusal is an operator decision. Acceptance requires the server’s configured hook to reject the request automatically.

## Match the server evidence

For each approved phase, join the native request and tool-call IDs to the native result, its trace and service-generated invocation ID, then to the MCP audit. The allowed result must match the provisioned digest. The grant refusal must precede AWS dispatch. The IAM result must include S3 `AccessDenied`, HTTP 403 and an AWS request ID; the existing denied fixture and deployed policy complete its attribution.

For the Crew denial, require the host-generated blocked row, a native `hook_deny`, full service-journal coverage with no matching arrival, and a stable healthy MCP service. The inspected SEL denial lacks a direct trace or tool-call ID. Report its correlation through the dedicated session and isolated turn interval; do not describe it as a direct trace join. Check the SEL chain separately.

The configured Crew hook lives on EC2, but Crew can edit its configuration in this deployment. The MCP service code, grants and instance-role boundary have separate protection. The demo uses an owner connection and currently has no enterprise governance policy. It does not establish an immutable policy floor, ordinary member permissions or sandbox execution.

See the [MCP enforcement contract](../infrastructure/mcp-enforcement/README.md) for the fixed tools and service audit, and the [native evidence runner contract](../scripts/native-backend-demo.README.md) for the existing correlation rules. The active recording uses the native client for requests and approvals.

## Conversation identity and host controls

The fifth clip records the first host-test attempt in `chat-3-1789335506`. The server returned `memory_unavailable` and explained that the conversation had no verified assignment to private memory. The requested file read never reached a tool. The [assignment diagnosis](../evidence/native-client-demo/host-20260913/assignment-diagnostic.json) ties the refusal to changing an existing conversation to an agent with a private store. This proves a conversation-assignment guard; it does not prove file enforcement or restricted human-role RBAC.

Create the host-test session with its intended agent assigned from the start. In the native client's create menu, choose **New folder**, select the existing demo workspace and set **Default agent** to `host-controls-demo`. Create a new chat inside that folder. The supported folder-default flow supplies the agent when the conversation is created, so the private-memory binding can be established at birth. Keep the global default and original `enforcement-demo` session intact.

The current blank session is `chat-4-1789335946`, inside **Host control demos**, with workspace `/srv/kirocrew-demo/workspace` and agent `host-controls-demo`. It has not received a prompt. The [unused capture and observer](../evidence/native-client-demo/host-20260913-ui2/capture-status.json) are finalized with zero captured events and zero session messages. After the Mac is unlocked, confirm the session and Interactive approval, then start a fresh passive observer and raw recording. Use the exact six prompts and fixture checks in [HOST-CONTROL-SCENARIOS.md](HOST-CONTROL-SCENARIOS.md). The [setup review](../evidence/native-client-demo/host-20260913/setup-review.json) covers the additive installer and fixed helpers; setup success does not establish native enforcement.

The custom command pattern `KIROCREW_DEMO_COMMAND_CONTROL_20260913` is enabled for the pending take. Remove only that added rule through the admin UI after recording and save the removal receipt. Never target a live agent file for the write demonstration. The metadata helper makes one IPv4 TCP connection attempt with zero application bytes; its failure requires process and effective-rule evidence before attribution to host isolation.

## Separate admin-console tour

Open the [nine-stop screenshot tour](../output/kirocrew-admin-tour.html) for the recorded walkthrough, or use the configured SSH tunnel to inspect the live owner console. The tour contains 13 original screenshots, with dates that distinguish fresh native-run captures from earlier runtime observations. Its [browser review](../evidence/admin-console/native-20260913/browser-review.json) covers navigation, image viewing and the exact inspected HTML. The routes below were inspected in the current UI; recheck them after a Nightly update.

| Stop | Route | What to explain |
| --- | --- | --- |
| Locate the server | `/settings/overview`, then `/developer?tab=system&plane=performance` | Read the server build, architecture and workspace. Gateway health establishes the running server; a completed native turn establishes backend readiness. |
| Inspect the configured controls | `/settings/security/posture`, then `/settings/security/rules` | Show Interactive approval, expand a control and inspect one denied-command rule. Built-in and custom shell-command rules are distinct from the demo’s configured `auto_deny_tools` MCP hook. |
| Read policy authority | `/settings/security/approval`, then `/settings/security/governance` | Explain the active mode and whether an enterprise policy is present. A selected auto-approve duration applies to its next activation. Keep Interactive mode enabled. |
| Diagnose the native request | `/developer?tab=agent-backend`, then `/developer?tab=logs` | Show Kiro CLI selected and inspect the new run’s relevant log evidence. Pair it with the client result and sanitized server receipt. Do not reuse the old sign-in failure as a current diagnosis. |
| Inspect Gateway telemetry | `/settings/privacy`, then `/developer?tab=telemetry` | Explain metric recording, destination, retention and the four completed MCP turns. Background activity is separate. Runtime fault counts are not policy-denial counts. |
| Inspect client and server collection | `/apps/demo-observability` | Read sample times, Local Gateway off, tunnel listener and server service checks. Filter Collection logs by Client and Server and explain the source’s latest event. |

Demo Observability is a custom App Kit page. Its collection logs contain first samples, health changes and collection errors. Native tool decisions, SEL records and MCP audit events need their own evidence; the current custom page does not ingest them. “Current” means a fresh sample, even when an individual health check reads No. Its tunnel probe establishes a local TCP listener.

System Services at `/developer?tab=system&plane=services` can report zero MCP processes because the demo MCP runs as a separate systemd service and Unix user. Use the custom collector for that service’s health. The current tour includes Denied Commands, expanded control coverage, approval duration, governance status and fresh four-turn telemetry. Coverage counts describe the installed catalog, not executed security tests. The earlier [13-screen walkthrough](../output/kirocrew-admin-walkthrough.md) and [findings](../output/kirocrew-admin-findings.md) retain their dated observations.

## Delivery and editing

Keep the raw native window footage private. Export reviewed cuts with FFmpeg and attach timestamps, trace IDs, receipt links and source hashes. Captions should name the observed decision and where it occurred. Preserve errors and waiting in the raw take; document any removed interval.

The current HTML edition includes the five reviewed native clips and links the separate admin tour. Append the six host takes only after each recording and evidence check passes. Retain the existing six supporting recordings, accepted deck, PowerPoint, single endpoint-control box and previous receipts. Any unobserved turn remains pending in the current status and delivery receipts.

## What changed

Updated the guide with five recorded native outcomes, final four-turn reconciliation and separate authority/media reviews. Added the private-memory diagnosis, corrected host-session setup and six unrecorded host takes. Linked the current admin tour and clarified its telemetry and control-catalog scope.
