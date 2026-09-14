# KiroCrew admin console tour

September 13, 2026 · macOS client / ARM EC2 server · owner console

Inspect the server’s controls, understand their authority and read the client and server measurements. These are original captures of the owner console connected to the ARM EC2 Gateway. The Mac runs the client with its local Gateway off.

Earlier MCP/IAM run: The native Mac run recorded an allowed S3 read, a Crew policy refusal, an MCP grant refusal and IAM AccessDenied. The final reconciliation and authority review support those four bounded outcomes.

Fresh security captures and earlier baseline screenshots are dated separately below. All image bytes are preserved. This tour is a guide to the console; native enforcement requires a separate recording and receipt.

## 01. Locate the execution host

Open **Settings → Overview; Developer → System → Performance**.

Route: `/settings/overview; /developer?tab=system&plane=performance`

The fresh Overview capture shows All systems running, the September 12 server Nightly, 6h 51m 40s uptime and one session. The earlier Performance capture identifies aarch64, four logical processors and the workspace on Linux. Both describe the EC2 execution host.

Read the host and build before interpreting the counters. Gateway health and a selected backend each need a completed native turn to establish that the backend can do the requested work.

Presenter cue: Point to the remote Linux workspace. Keep the Gateway, backend and workspace inside the single endpoint-control box.

*September 13, 2026 · evening capture.* Fresh Overview capture: remote server Nightly, uptime of 6h 51m 40s, one session and zero messages.

![Overview shows All systems running, one session and the remote September 12 server build.](admin-console-native-20260913/07-gateway-overview.png)

*September 13, 2026 · earlier baseline.* Earlier Performance capture: aarch64, four logical processors and the EC2 workspace.

![System Performance identifies ARM Linux and the remote workspace.](admin-console/02-arm-performance.jpg)

## 02. Read the configured controls

Open **Settings → Security → Live Security Posture**.

Route: `/settings/security/posture`

The page shows Standard process sandbox and Interactive tool approval. The visible coverage includes 143 credential paths, 23 protected configuration paths and 112 built-in denied-command rules.

These labels describe the configured controls and their registries. A completed request and its correlated evidence establish what ran or was blocked.

Presenter cue: Expand a control to explain its coverage. Keep the scope of the claim tied to the evidence.

*September 13, 2026 · evening capture.* Fresh posture capture: configuration and coverage counts on the EC2 Gateway.

![Live Security Posture shows Standard sandbox, Interactive approval and control coverage counts.](admin-console-native-20260913/01-live-security-posture.png)

## 03. Inspect the command rules

Open **Settings → Security → Denied Commands**.

Route: `/settings/security/rules`

The page groups 112 built-in rules into nine categories. The earlier expanded IaC teardown capture shows four enabled rules for destructive CDK, Kubernetes, Pulumi and Terraform commands. The custom-deny form accepts a pattern and an explanation for the agent.

The later owner-console capture shows KIROCREW_DEMO_COMMAND_CONTROL_20260913 enabled as a temporary custom deny. The next capture shows that marker removed after the take. Both show 112 built-in rules and Disable all built-in denies switched off. These images record configuration; the separate native command receipt supports the observed automatic hook refusal.

The cleanup readback confirms that the exact marker and its rule ID are absent, no built-in IDs are disabled, and the previously bound hook, path and token-auth sources are unchanged. Its earlier baseline did not hash all unrelated custom rules, so that receipt alone cannot prove every unrelated custom rule was preserved.

The custom command pattern is separate from auto_deny_tools for @aws-enforcement/crew_denied in the remote Gateway configuration. This screen does not manage that MCP tool deny. Crew can edit its configuration in this deployment.

Presenter cue: Compare the temporary marker before and after cleanup, then open the command decision and cleanup receipts. Keep the command rule separate from the MCP tool deny.

*September 13, 2026 · evening capture.* Fresh category view: nine groups, 112 rules and the custom-deny form.

![Denied Commands lists credential, shell, destructive-command and publication rule categories.](admin-console-native-20260913/03-denied-command-categories.png)

*September 13, 2026 · evening capture.* Fresh expanded IaC teardown category: four enabled rule descriptions.

![The expanded IaC teardown category shows CDK destroy, Kubernetes namespace deletion, Pulumi destroy and Terraform destroy rules.](admin-console-native-20260913/04-teardown-rule-coverage-viewport.png)

*September 13, 2026 · later evening capture (EDT).* Later owner-console capture: the temporary marker pattern is enabled. The built-in catalog remains at 112 rules and its global-disable switch is off.

![Denied Commands shows 112 built-in rules and the enabled custom pattern KIROCREW_DEMO_COMMAND_CONTROL_20260913.](admin-console-host-20260913/01-command-rule-active.jpg)

*September 13, 2026 · later evening capture (EDT).* After cleanup through Delete pattern, the custom marker is absent. The same view retains 112 built-in rules with the global-disable switch off.

![Denied Commands shows an empty custom-deny list after the temporary marker was removed; 112 built-in rules remain listed.](admin-console-host-20260913/02-command-rule-removed.jpg)

## 04. Read the active approval mode

Open **Settings → Security → YOLO (auto-approve)**.

Route: `/settings/security/approval`

The sidebar says Interactive. Six hours is selected as the duration for the next activation of auto-approve; the sentence below the choices makes that timing explicit.

The native demo requires reviewing each approvable request and choosing the once-only approval. Leave Interactive mode in place.

Presenter cue: Read the sidebar’s current mode first, then the selected duration and its next-activation note.

*September 13, 2026 · evening capture.* Fresh approval settings: Interactive remains active; six hours is the next auto-approve duration.

![The YOLO duration screen shows Interactive in its sidebar and a six-hour next-activation selection.](admin-console-native-20260913/05-approval-duration.png)

## 05. Check who owns the policy

Open **Settings → Security → Governance Policy**.

Route: `/settings/security/governance`

The effective security ceiling panel reports “No enterprise policy in effect.” It describes this host as standalone. This viewer is read-only; it does not author an enterprise policy.

The demonstration uses an owner connection and editable Crew configuration. The root-managed MCP service enforces its own grants, and AWS evaluates the instance role. Those MCP and IAM policies live outside this portal. No immutable enterprise floor or separate low-privilege member workflow is established here.

Presenter cue: Name the three authorities: Gateway configuration, protected MCP service and AWS IAM. Show their evidence separately.

*September 13, 2026 · evening capture.* Fresh governance capture: no enterprise policy is loaded on the host.

![Governance Policy states No enterprise policy in effect and describes standalone mode.](admin-console-native-20260913/06-governance-status.png)

## 06. Understand what SEL coverage lists

Open **Settings → Security → Live Security Posture → SEL audit logging**.

Route: `/settings/security/posture`

The expanded SEL row lists covered session-key surfaces, with 19 reported in the posture summary. Entries include Background, CLI, Cron and Dashboard.

This is a coverage list. It does not display the live security-event stream for a request. A native denial needs its blocked result, relevant SEL record and complete MCP journal interval. Where the SEL event lacks a trace field, keep the isolated-session correlation explicit.

Presenter cue: Use this screen to explain which surfaces emit audit records. Use the run’s sanitized receipt to inspect a particular decision.

*September 13, 2026 · evening capture.* Fresh expanded SEL coverage list; no per-request denial log is displayed here.

![The expanded SEL audit logging row lists session-key surfaces including Background, CLI, Cron and Dashboard.](admin-console-native-20260913/02-sel-coverage-viewport.png)

## 07. Separate backend choice from sign-in

Open **Developer → Agent Backend**.

Route: `/developer?tab=agent-backend`

This earlier screenshot shows Kiro CLI selected and a “Signed in with GitHub” card. That card reads KAS identity; the standalone CLI has its own sign-in state. At the earlier capture, the CLI was signed out.

The EC2 standalone CLI receipt records authenticated=true via SocialGitHub at 21:09 UTC. The subsequent four native turns have reviewed client/server joins. Selecting Kiro CLI applies to new sessions; recheck its authentication before another take.

Presenter cue: Read the CLI’s own sign-in receipt, then the recorded native results. The two identity surfaces have separate evidence.

*September 13, 2026 · earlier baseline.* Earlier backend page, retained to explain the two identity surfaces. The new CLI sign-in is documented separately.

![Kiro CLI is selected beside a GitHub sign-in card representing KAS identity.](admin-console/07-agent-backend.jpg)

## 08. Read Gateway instrumentation

Open **Settings → Privacy; Developer → Telemetry**.

Route: `/settings/privacy; /developer?tab=telemetry`

The earlier Privacy capture has Record metrics enabled and the anonymous usage heartbeat disabled by the Gateway environment. The retained MCP/IAM capture expands four completed turns with durations 12.3, 8.9, 14.2 and 17.7 seconds; its session total displays 0.5 credits after rounding.

The later captures show nine dashboard turns and 14 background turns, for throughput 23. Their header reports p50 latency 3.5 seconds, p90 latency 17.4 seconds and 0 runtime faults of 9. These aggregates include different sessions and outcomes; they are not a count of passed security tests.

Blocked bash command demonstration expands to one turn at 8:00:21 PM, with 0.12 credits and 6.8 seconds. Anonymous loopback security posture probe expands to one turn at 8:07:21 PM, with 0.27 credits and 50.4 seconds. Both times are September 13. The authentication turn includes two separate once-only approvals, so its duration includes the approval workflow.

The footer labels the metrics source local-only, no egress. That describes metric storage/export, not a network restriction on the agent or AWS requests. These rows establish recorded activity. The native results and separately reviewed server evidence identify each allowed or denied outcome.

Presenter cue: Read the named turn, timestamp and duration, then open its decision receipt. Explain why runtime faults, background throughput and policy refusals are different measurements.

*September 13, 2026 · earlier baseline.* Earlier Privacy capture: metric recording on, anonymous heartbeat disabled by environment.

![Privacy shows Gateway metrics enabled and anonymous telemetry disabled.](admin-console/08-telemetry-controls.jpg)

*September 13, 2026 · evening capture.* Fresh native Telemetry: four completed dashboard turns, four background turns and the expanded demo session’s durations and credits.

![Native Telemetry expands the MCP Tool Call Read Allowed session into four completed turns, with durations 12.3, 8.9, 14.2 and 17.7 seconds.](admin-console-native-20260913/10-native-turn-telemetry.png)

*September 13, 2026 · later evening capture (EDT).* Later Native Telemetry: Blocked bash command demonstration contains one turn at 8:00:21 PM, with 0.12 credits and 6.8 seconds. Aggregate throughput 23 includes 14 background turns.

![Native Telemetry expands the command-demonstration session into its one recorded turn and shows the aggregate runtime measurements.](admin-console-host-20260913/03-command-turn-metrics.jpg)

*September 13, 2026 · later evening capture (EDT).* Later Native Telemetry: Anonymous loopback security posture probe contains one turn at 8:07:21 PM, with 0.27 credits and 50.4 seconds. Its security outcome is established separately.

![Native Telemetry expands the anonymous-probe session into one recorded turn; the header shows 0 faults of 9 and throughput 23.](admin-console-host-20260913/04-anonymous-turn-metrics.jpg)

## 09. Read client and server health together

Open **Apps → Demo Observability**.

Route: `/apps/demo-observability`

The cards identify their source and sample time. The later Mac sample is 20:16:02, with 3.7% KiroCrew process CPU and 967.1 MiB process memory. The EC2 sample is 20:16:26, with 0.7% host CPU and 12.6 GiB memory available. Both are marked Current.

Read Local Gateway off on the Mac card, then the EC2 Gateway and separate MCP service checks. The client tunnel check establishes a local TCP listener. Current means the sample is fresh. Mac process CPU and EC2 host CPU use different sampling methods.

The expanded server measurements show 235 MiB for the Gateway main process and 147.5 MiB for the MCP main process. With the Server filter selected, the collection log contains one First sample collected event at 10:31:23. The later screenshot has a new Mac sample at 20:17:04; do not treat the two captures as one simultaneous sample.

Collection logs record first samples, health changes and collection errors. The Client and Server buttons filter that event stream. This custom App Kit page does not ingest native tool decisions, SEL records or MCP denial logs.

Presenter cue: Read both timestamps and individual checks. Expand server measurements and filter Server, then use separate security receipts for enforcement claims.

*September 13, 2026 · earlier baseline.* Earlier custom telemetry capture: both samples Current, local Gateway off and server checks Yes.

![Demo Observability shows macOS client and EC2 server samples with freshness and service checks.](admin-console/11-client-server-telemetry.jpg)

*September 13, 2026 · earlier baseline.* Earlier collection events include the observed client health change and recovery.

![Collection logs show source labels, timestamps, event levels and All, Client and Server filters.](admin-console/12-collection-logs.jpg)

*September 13, 2026 · later evening capture (EDT).* Later collection view: both samples are Current, the Mac local Gateway is off, and the EC2 Gateway/MCP checks read Yes. Mac and server sample times are 20:16:02 and 20:16:26.

![Demo Observability shows Current macOS and EC2 samples, local Gateway off, client 3.7% CPU and 967.1 MiB memory, and server 0.7% CPU with 12.6 GiB available.](admin-console-host-20260913/05-client-server-health.jpg)

*September 13, 2026 · later evening capture (EDT).* Server measurements expanded: Gateway 235 MiB and MCP 147.5 MiB main-process memory. The Server filter displays one First sample collected event; this is a collection-health log.

![Demo Observability shows expanded server process measurements and a Server-only collection log containing one First sample collected event at 10:31:23.](admin-console-host-20260913/06-server-collection-logs.jpg)

## Evidence

Earlier MCP/IAM collection: The original collector receipt remains collection_complete=false because its recent SEL window lost the baseline anchor. Its exact bytes are retained locally; the linked publication export identifies the original by hash. A separate read-only recovery joined the retained rows. The generic reconciler keeps full_native_acceptance=false: it does not decide footage acceptance or every attribution check. Process sampling was not shown to overlap an approval, and SEL integrity relies on the original Gateway verification rather than independent per-row signatures.

- [Fresh EC2 CLI authentication](../evidence/native-client-demo/20260913/authenticated.json)
- [Native Mac recording guide](../docs/NATIVE-CLIENT-DEMO.md)
- [MCP and IAM enforcement contract](../infrastructure/mcp-enforcement/README.md)
- [Custom telemetry data contract](../infrastructure/observability/APP-INSTALL.md)
- [Earlier screenshot capture receipt](../evidence/admin-console/browser-receipt.json)
- [Earlier admin findings](../output/kirocrew-admin-findings.md)
- [Final four-outcome reconciliation](../evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json)
- [Independent reconciliation review](../evidence/native-client-demo/20260913-ui2-reconciled-final/review.json)
- [MCP and IAM authority attribution review](../evidence/native-client-demo/20260913-ui2/authority-attribution-review.json)
- [Publication export of the incomplete collector receipt](../evidence/native-client-demo/20260913-ui2/receipt-publication.json)
- [Native MCP clip review](../evidence/native-client-demo/media-review-mcp-controls.json)
- [Later host workspace-read observations](../evidence/native-client-demo/host-20260913-ui3/initial-observations.json)
- [Later native command-rule observations](../evidence/native-client-demo/host-20260913-ui3/command-observations.json)
- [Independent initial host review](../evidence/native-client-demo/host-20260913-review/initial-review.json)
- [Anonymous Gateway authentication correlation](../evidence/native-client-demo/host-20260913-ui3/auth-correlation.json)
- [Independent anonymous Gateway authentication review](../evidence/native-client-demo/host-20260913-review/auth-review.json)
- [Temporary command-rule cleanup readback](../evidence/native-client-demo/host-20260913-ui3/command-rule-cleanup.json)
- [Current native admin findings](../output/kirocrew-native-admin-findings.md)
- [Host-control scenario guide](../docs/HOST-CONTROL-SCENARIOS.md)

## What changed

Retained the 13 accepted images and appended six later host captures: the temporary command rule before and after cleanup, command and authentication turn metrics, current client/server samples and filtered server collection events. The added captions distinguish configuration, runtime measurements and security decisions.
