# KiroCrew admin console tour

September 13, 2026 · macOS client / ARM EC2 server · owner console

Inspect the server’s controls, understand their authority and read the client and server measurements. These are original captures of the owner console connected to the ARM EC2 Gateway. The Mac runs the client with its local Gateway off.

The native Mac run recorded an allowed S3 read, a Crew policy refusal, an MCP grant refusal and IAM AccessDenied. The final reconciliation and authority review support those four bounded outcomes.

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

The page groups 112 rules into nine categories. The expanded IaC teardown group describes four enabled rules for destructive CDK, Kubernetes, Pulumi and Terraform commands. The custom-deny form accepts a pattern and an explanation for the agent.

These are command-pattern controls. The demo’s auto_deny_tools entry for @aws-enforcement/crew_denied lives in the remote Gateway configuration separately; this screen does not manage that MCP tool deny. Crew can edit its configuration in this deployment.

Presenter cue: Read a rule’s description and enabled state. Inspect coverage without changing the control during the tour.

*September 13, 2026 · evening capture.* Fresh category view: nine groups, 112 rules and the custom-deny form.

![Denied Commands lists credential, shell, destructive-command and publication rule categories.](admin-console-native-20260913/03-denied-command-categories.png)

*September 13, 2026 · evening capture.* Fresh expanded IaC teardown category: four enabled rule descriptions.

![The expanded IaC teardown category shows CDK destroy, Kubernetes namespace deletion, Pulumi destroy and Terraform destroy rules.](admin-console-native-20260913/04-teardown-rule-coverage-viewport.png)

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

The earlier Privacy capture has Record metrics enabled and the anonymous usage heartbeat disabled by the Gateway environment. The fresh Telemetry capture expands the dashboard session “MCP Tool Call Read Allowed” into four completed turns, at 5:24:51, 5:25:41, 5:26:51 and 5:27:21 PM on September 13.

The four durations are 12.3, 8.9, 14.2 and 17.7 seconds. The session total displays 0.5 credits after rounding. Throughput is eight because it includes four background turns. The fault summary reads 0 faults of 4; that is a runtime fault measurement, not a count of policy denials.

The footer labels the metrics source local-only, no egress. That describes metric storage/export, not a network restriction on the agent or AWS requests. These rows establish recorded activity. The separately reviewed reconciliation and authority evidence establish the four specific allowed or denied outcomes.

Presenter cue: Read the named session’s four rows, then explain the background row and open the matched enforcement evidence.

*September 13, 2026 · earlier baseline.* Earlier Privacy capture: metric recording on, anonymous heartbeat disabled by environment.

![Privacy shows Gateway metrics enabled and anonymous telemetry disabled.](admin-console/08-telemetry-controls.jpg)

*September 13, 2026 · evening capture.* Fresh native Telemetry: four completed dashboard turns, four background turns and the expanded demo session’s durations and credits.

![Native Telemetry expands the MCP Tool Call Read Allowed session into four completed turns, with durations 12.3, 8.9, 14.2 and 17.7 seconds.](admin-console-native-20260913/10-native-turn-telemetry.png)

## 09. Read client and server health together

Open **Apps → Demo Observability**.

Route: `/apps/demo-observability`

The two cards identify their source and sample time. Read Local Gateway off on the Mac card, then the EC2 Gateway and separate MCP service checks. The client’s tunnel check establishes a local TCP listener. “Current” means the sample is fresh.

Collection logs record first samples, health changes and collection errors. The Client and Server buttons filter that event stream. This custom App Kit page does not ingest native tool decisions, SEL records or MCP denial logs. Mac process CPU and EC2 host CPU also use different sampling methods.

Presenter cue: Read timestamps and individual checks, then filter the collection events. Pair enforcement claims with their separate native/server receipts.

*September 13, 2026 · earlier baseline.* Earlier custom telemetry capture: both samples Current, local Gateway off and server checks Yes.

![Demo Observability shows macOS client and EC2 server samples with freshness and service checks.](admin-console/11-client-server-telemetry.jpg)

*September 13, 2026 · earlier baseline.* Earlier collection events include the observed client health change and recovery.

![Collection logs show source labels, timestamps, event levels and All, Client and Server filters.](admin-console/12-collection-logs.jpg)

## Evidence

The original collector receipt remains collection_complete=false because its recent SEL window lost the baseline anchor. Its exact bytes are retained locally; the linked publication export identifies the original by hash. A separate read-only recovery joined the retained rows. The generic reconciler keeps full_native_acceptance=false: it does not decide footage acceptance or every attribution check. Process sampling was not shown to overlap an approval, and SEL integrity relies on the original Gateway verification rather than independent per-row signatures.

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

## What changed

Added fresh security, command-rule, approval, governance, SEL-coverage and completed-turn telemetry captures. Updated the four native outcomes from the final reconciliation and authority review, while retaining the original collection failure and remaining limits. Earlier reference screenshots keep their capture dates.
