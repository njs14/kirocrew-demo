# KiroCrew admin console: current findings

The tour now contains nine stops and 19 original screenshots: the accepted 13 plus six captures from the later September 13 evening session. The Mac runs the client with its local Gateway off; the owner console connects to the ARM EC2 Gateway. The Gateway, Kiro CLI backend and workspace remain inside the single endpoint-control box.

The latest native evidence adds an allowed workspace read, an automatic command-rule refusal and an anonymous Gateway authentication refusal. The screenshots explain the settings and measurements. The linked native and server receipts establish the bounded outcomes.

## What the latest host takes establish

| Case | Observed result | Evidence and limit |
|---|---|---|
| Public workspace read | The native tool read the exact public canary and returned its expected content. | [Native observations](../evidence/native-client-demo/host-20260913-ui3/initial-observations.json), [independent review](../evidence/native-client-demo/host-20260913-review/initial-review.json). No permission event occurred, so this is not an approval-callback test. |
| Temporary custom command deny | Crew automatically blocked the harmless marker command. | [Command observations](../evidence/native-client-demo/host-20260913-ui3/command-observations.json), [independent review](../evidence/native-client-demo/host-20260913-review/initial-review.json). Exact native input joins the blocked tool row; SEL attribution uses the isolated command interval. No operator rejection supplied the denial. |
| Anonymous Gateway request | The prepared loopback helper returned HTTP 403. The corresponding security event reports `Token required`. | [Correlation](../evidence/native-client-demo/host-20260913-ui3/auth-correlation.json), [independent auth review](../evidence/native-client-demo/host-20260913-review/auth-review.json). Reading the helper source and executing it were separate native calls, each approved once. SEL attribution is by unique route, caller, reason and time interval; it has no direct tool trace ID. This establishes anonymous token authentication, not restricted-user RBAC. |

The sensitive-path request ended in a model refusal before a native tool attempt. Protected-path write and native IPv4 metadata isolation remain unproved. A prepared fixture or helper does not close those gaps. In particular, no native firewall result is claimed. See the [host scenario guide](../docs/HOST-CONTROL-SCENARIOS.md).

The earlier allowed S3 read and Crew, MCP-grant and IAM denials retain their separate [four-outcome reconciliation](../evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json), [independent review](../evidence/native-client-demo/20260913-ui2-reconciled-final/review.json) and [authority attribution](../evidence/native-client-demo/20260913-ui2/authority-attribution-review.json). The earlier conversation-assignment refusal is an identity guard; it does not establish file enforcement or a restricted human role.

## What the portal controls

Denied Commands shows 112 built-in rules in nine categories. The later captures show the temporary `KIROCREW_DEMO_COMMAND_CONTROL_20260913` pattern enabled, then absent after Delete pattern. The built-in count remains 112 in both images; the global-disable switch remains off. The [cleanup readback](../evidence/native-client-demo/host-20260913-ui3/command-rule-cleanup.json) confirms marker absence, no disabled built-in IDs and unchanged previously bound hook, path and token-auth sources. Its earlier baseline did not hash every unrelated custom rule, so that receipt alone cannot establish preservation of all other custom-rule bytes.

This owner-editable command pattern is separate from the Gateway's `auto_deny_tools` entry for `@aws-enforcement/crew_denied`. The Denied Commands page does not edit that MCP tool deny. The protected MCP service manages its own grants; AWS evaluates the instance role outside the portal.

Governance reports no enterprise policy in effect. Interactive approval is active. The six-hour selection is the duration for the next auto-approve activation. The expanded SEL posture row lists covered session surfaces; it is not a per-request security-event viewer. No immutable enterprise policy floor or separate low-privilege member workflow has been established.

## What the measurements mean

The later Native Telemetry captures show nine dashboard turns and 14 background turns, for throughput 23. The header reports p50 latency 3.5 seconds, p90 latency 17.4 seconds and zero runtime faults of nine. The command session has one turn at 8:00:21 PM, with 0.12 credits and 6.8 seconds. The anonymous-probe session has one turn at 8:07:21 PM, with 0.27 credits and 50.4 seconds. Those are September 13 local display times. The authentication turn includes the two approval steps; its 50.4-second duration is not the helper's 3 ms HTTP measurement.

Runtime faults are not policy-denial counts. Credits, durations and throughput establish recorded activity, not which control made a decision. The local-only/no-egress footer describes metrics storage and export, not the agent's network permissions.

Demo Observability combines custom health samples. At 20:16:02, the Mac sample shows 3.7% process CPU, 967.1 MiB process memory and Local Gateway off. At 20:16:26, the EC2 sample shows 0.7% host CPU and 12.6 GiB available memory. Both are Current. The expanded server view shows 235 MiB for the Gateway main process and 147.5 MiB for the MCP main process. These use different sampling methods and timestamps.

With Server selected, Collection logs shows one `First sample collected` event at 10:31:23. The page records first samples, health changes and collection errors. It does not ingest native tool decisions, SEL records or MCP denial logs. The Mac tunnel check establishes a local TCP listener; it does not independently prove a successful remote request.

## Screenshot inventory

All images below retain their original bytes. The [interactive tour](kirocrew-admin-tour.html) provides zoom and original-image links; its [build receipt](../evidence/admin-console/native-20260913/tour-build.json) binds each image and evidence source.

| Tour stop | Retained screenshots | Later host captures |
|---|---|---|
| Execution host | [Overview](admin-console-native-20260913/07-gateway-overview.png), [ARM performance](admin-console/02-arm-performance.jpg) | — |
| Configured controls | [Security posture](admin-console-native-20260913/01-live-security-posture.png) | — |
| Command rules | [Categories](admin-console-native-20260913/03-denied-command-categories.png), [IaC teardown](admin-console-native-20260913/04-teardown-rule-coverage-viewport.png) | [Marker active](admin-console-host-20260913/01-command-rule-active.jpg), [marker removed](admin-console-host-20260913/02-command-rule-removed.jpg) |
| Approval mode | [Interactive and next duration](admin-console-native-20260913/05-approval-duration.png) | — |
| Policy ownership | [Governance](admin-console-native-20260913/06-governance-status.png) | — |
| SEL coverage | [Covered surfaces](admin-console-native-20260913/02-sel-coverage-viewport.png) | — |
| Backend identity | [Earlier backend card](admin-console/07-agent-backend.jpg) | — |
| Gateway metrics | [Privacy settings](admin-console/08-telemetry-controls.jpg), [four MCP/IAM turns](admin-console-native-20260913/10-native-turn-telemetry.png) | [Command turn](admin-console-host-20260913/03-command-turn-metrics.jpg), [anonymous-auth turn](admin-console-host-20260913/04-anonymous-turn-metrics.jpg) |
| Client/server health | [Earlier samples](admin-console/11-client-server-telemetry.jpg), [earlier collection events](admin-console/12-collection-logs.jpg) | [Later samples](admin-console-host-20260913/05-client-server-health.jpg), [server measurements and filter](admin-console-host-20260913/06-server-collection-logs.jpg) |

## Evidence limits

The earlier MCP/IAM collector remains incomplete in its original receipt. Its private bytes were preserved; the [publication export](../evidence/native-client-demo/20260913-ui2/receipt-publication.json) identifies them by hash. A separate reconciliation recovered the four bounded outcomes. Its generic `full_native_acceptance:false` is retained, as are the limits on pending-approval process overlap and independent per-row SEL signature verification. The later host results have their own receipts and reviews.

The admin browser was used to inspect settings, metrics and cleanup. Native tool approvals occurred in the macOS client. This screenshot tour is separate from the native enforcement recordings. The [browser review](../evidence/admin-console/native-20260913/browser-host/review.json) records the exact HTML hash inspected; its verdict applies only to that edition. The accepted 13-image review retains its earlier scope and cannot approve the added host captures.

The earlier [admin findings](kirocrew-admin-findings.md) remain unchanged as a dated baseline. This edition adds the six later captures, the three bounded host outcomes, temporary-rule cleanup and current measurement interpretation. The final copy received a No AI Slop edit.
