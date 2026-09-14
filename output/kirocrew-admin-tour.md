# KiroCrew admin console tour

September 14, 2026 · macOS client / ARM EC2 server · owner console

Tour the owner console connected to the ARM EC2 Gateway: policy, user controls, runtime metrics and client/server health. The Mac runs the client with its local Gateway off. Each image retains its capture date.

Managed file policy is active on the EC2 Gateway. A fresh macOS take records its automatic MCP-tool refusal. A separate managed allowed read is verified in the receipts but was not filmed. Three September 14 native recordings now cover the sensitive-path read, protected-path write and fixed IMDS TCP check.

Eleven stops and 29 original images: 26 dated images retained from the previous edition, plus three clearly labeled native client result images. Configuration, Gateway metrics, collection health and security decisions have separate evidence.

## 01. Locate the execution host

Open **Settings → Overview; Developer → System → Performance**.

Route: `/settings/overview; /developer?tab=system&plane=performance`

The client is macOS Nightly September 13. The existing ARM EC2 host runs the September 12 server Nightly with Kiro CLI 2.21.4. The Mac quit and relaunched with its local Gateway off and the remote connection on port 5599. That continuity check preceded policy activation; the later native receipts verify execution after activation.

The retained Overview and Performance images predate managed policy. They identify the remote build, ARM Linux and the EC2 workspace; their uptime and activity counters belong to those capture times. Keep the Gateway, backend and workspace in the single endpoint-control box.

Presenter cue: Point to the remote Linux workspace. Keep the Gateway, backend and workspace inside the single endpoint-control box.

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier Overview capture: remote server Nightly, uptime of 6h 51m 40s, one session and zero messages.

![Overview shows All systems running, one session and the remote September 12 server build.](admin-console-native-20260913/07-gateway-overview.png)

*September 13, 2026 · earlier baseline · before managed policy.* Before managed policy. Earlier Performance capture: aarch64, four logical processors and the EC2 workspace.

![System Performance identifies ARM Linux and the remote workspace.](admin-console/02-arm-performance.jpg)

## 02. Read the configured controls

Open **Settings → Security → Live Security Posture**.

Route: `/settings/security/posture`

The active file policy sets the Linux sandbox floor to cc. Its readback and the Governance Policy view establish the configured floor. A separate runtime check saw six Kiro CLI descendants with seccomp mode 2, NoNewPrivs enabled and a different mount namespace; it did not attribute those processes to the exact recorded tool calls.

The earlier posture image below shows Standard sandbox, Interactive approval and coverage counts of 143 credential paths, 23 protected paths and 112 built-in command rules. Those are pre-policy capture values. Coverage counts describe registries; they do not establish that a particular read, write or command was blocked.

Presenter cue: Expand a control to explain its coverage. Keep the scope of the claim tied to the evidence.

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier posture capture: configuration and coverage counts on the EC2 Gateway.

![Live Security Posture shows Standard sandbox, Interactive approval and control coverage counts.](admin-console-native-20260913/01-live-security-posture.png)

## 03. Inspect the command rules

Open **Settings → Security → Denied Commands**.

Route: `/settings/security/rules → search s3`

In the current Denied Commands view, search s3. The built-in S3 upload deny is on, and its disabled switch has a lock and an organization-policy explanation. The file policy also contains a managed marker command. This screenshot establishes the locked configuration; no managed S3 upload attempt was recorded.

Command patterns and MCP tool policy are separate controls. The root-owned file now denies the canonical tool @aws-enforcement/crew_denied. The duplicate owner-editable auto_deny_tools hook was removed before the managed native take. This command-rule screen does not manage that MCP deny.

The four older images retain the catalog, teardown coverage and temporary KIROCREW_DEMO_COMMAND_CONTROL_20260913 rule before and after cleanup. That earlier marker was removed; its cleanup and native refusal receipts retain their original scope.

Presenter cue: Show the locked S3 upload rule, then identify the separate managed MCP deny. Date the old temporary-rule take before comparing it.

*September 13, 2026 · late evening EDT · managed policy active.* Search s3: the built-in upload deny is on and its switch is disabled. The lock and tooltip identify organization policy. This is a configured command rule, not a recorded S3 upload attempt.

![The S3 upload command rule is on with a disabled switch and an organization-policy explanation.](../evidence/enterprise-managed/20260913/screenshots/managed-command-locked.jpg)

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier category view: nine groups, 112 rules and the custom-deny form.

![Denied Commands lists credential, shell, destructive-command and publication rule categories.](admin-console-native-20260913/03-denied-command-categories.png)

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier expanded IaC teardown category: four enabled rule descriptions.

![The expanded IaC teardown category shows CDK destroy, Kubernetes namespace deletion, Pulumi destroy and Terraform destroy rules.](admin-console-native-20260913/04-teardown-rule-coverage-viewport.png)

*September 13, 2026 · later evening capture (EDT) · before managed policy.* Before managed policy. Later owner-console capture: the temporary marker pattern is enabled. The built-in catalog remains at 112 rules and its global-disable switch is off.

![Denied Commands shows 112 built-in rules and the enabled custom pattern KIROCREW_DEMO_COMMAND_CONTROL_20260913.](admin-console-host-20260913/01-command-rule-active.jpg)

*September 13, 2026 · later evening capture (EDT) · before managed policy.* Before managed policy. After cleanup through Delete pattern, the custom marker is absent. The same view retains 112 built-in rules with the global-disable switch off.

![Denied Commands shows an empty custom-deny list after the temporary marker was removed; 112 built-in rules remain listed.](admin-console-host-20260913/02-command-rule-removed.jpg)

## 04. Read the user's approval choices

Open **Native session → approval-mode menu; earlier Settings → Security → YOLO**.

Route: `Open the session's approval-mode menu; earlier settings route /settings/security/approval`

The current session menu has Normal selected. Reads and Trust remain available, while YOLO is absent. The managed file policy denies yolo; it does not force every session into Normal. No mode was changed during this inspection.

The earlier settings image shows Interactive and a six-hour duration for the next auto-approve activation. That saved duration predates the managed policy and does not grant permission to use YOLO now.

Presenter cue: Read what the user can choose now, then distinguish the old next-activation duration from the active policy.

*September 13, 2026 · late evening EDT · managed policy active.* The user's approval menu has Normal selected, Reads and Trust available, and no YOLO item. No approval mode was changed.

![The session approval menu lists Normal, Reads and Trust; Normal is selected and YOLO is absent.](../evidence/enterprise-managed/20260913/screenshots/user-approval-modes.jpg)

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier approval settings: Interactive remains active; six hours is the next auto-approve duration.

![The YOLO duration screen shows Interactive in its sidebar and a six-hour next-activation selection.](admin-console-native-20260913/05-approval-duration.png)

## 05. Check who owns the policy

Open **Settings → Security → Governance Policy**.

Route: `/settings/security/governance`

The current viewer shows Policy v1, Source: file, startup-only fetch and a cc sandbox floor. The policy is loaded from /etc/kirocrew-demo/security-policy.json through a protected systemd environment, with fail-closed behavior configured. Changes require a Gateway restart to be fetched.

The root-owned policy file is not writable by the Crew service account. It sets a floor against that account and the owner console; host root retains authority. This deployment does not establish signed fleet policy, enterprise SSO or separate human roles. The portal displays the policy; it does not author the file.

The protected MCP service still enforces its own grants, and AWS evaluates the instance role. Those authorities remain outside this portal. The earlier standalone screenshot below is preserved to show the state before policy activation.

Presenter cue: Read the policy source, refresh timing and floor. Name the service account it constrains, then the separate MCP-service and AWS authorities.

*September 13, 2026 · late evening EDT · managed policy active.* Active Policy v1 comes from a file, is fetched at startup and sets the cc sandbox floor. The panel lists one MCP deny and one denied approval mode.

![Governance Policy shows Policy v1, file source, startup-only refresh, cc sandbox floor and the configured policy lists.](../evidence/enterprise-managed/20260913/screenshots/managed-governance.jpg)

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier governance capture: no enterprise policy is loaded on the host.

![Governance Policy states No enterprise policy in effect and describes standalone mode.](admin-console-native-20260913/06-governance-status.png)

## 06. See what the user can enable

Open **Capabilities → MCP Servers; native session → Session options → MCP servers**.

Route: `/capabilities?tab=mcp opened Services first; click the visible MCP Servers tab. In the session, open Session options → MCP servers.`

The MCP manager shows the Crew-only aws-enforcement server enabled with four tools. Local controls can narrow the tools exposed to Crew. The second image records one staged restriction with Apply and Discard; it was discarded, so no restriction was applied.

In the actual web view of the native session, aws-enforcement has a green started ring. Its inventory reports 0/4 specifications loaded and lists read_allowed, crew_denied, mcp_denied and iam_denied as deferred tools. Neither this list nor the manager has a per-tool governance lock badge.

Enabled means available to the client. The canonical crew_denied invocation still met the root-managed deny. The filmed macOS host notice shows the automatic policy refusal; the ui4 receipt correlates it to policy-layer SEL evidence and a complete MCP journal interval with no matching service arrival. There was no approval card or operator refusal for this request.

A separate managed allowed read succeeded and has a client-to-service evidence join, but that read was not filmed. The earlier MCP grant and IAM denial recordings predate this policy change and keep their original evidence scope.

Presenter cue: Move from availability to deferred inventory to the actual native refusal. Use the receipt to identify the denying authority.

*September 13, 2026 · late evening EDT · managed policy active.* MCP Servers shows the Crew-only aws-enforcement server enabled with four tools. Enabled describes availability; the managed deny still applies when a tool is invoked.

![MCP Servers shows the enabled Crew-only aws-enforcement server with four tools.](../evidence/enterprise-managed/20260913/screenshots/mcp-manager-enabled.jpg)

*September 13, 2026 · late evening EDT · managed policy active.* One local restriction is pending, with Apply and Discard available. It was discarded after this capture; no local restriction was applied.

![The MCP manager shows one staged tool restriction and the Apply and Discard buttons.](../evidence/enterprise-managed/20260913/screenshots/mcp-manager-staged-restriction.jpg)

*September 13, 2026 · late evening EDT · managed policy active.* Session options lists aws-enforcement as started and shows 0/4 tool specifications loaded, with the four names deferred. The list has no per-tool governance lock badge.

![Session options shows aws-enforcement started, zero of four tool specifications loaded, and read_allowed, crew_denied, mcp_denied and iam_denied listed as deferred tools.](../evidence/enterprise-managed/20260913/screenshots/user-session-mcp-tools.jpg)

*September 13, 2026 · late evening EDT · managed policy active.* The filmed macOS take expands the host notice for the automatic governance-policy refusal. The ui4 receipt joins this result to the policy-layer SEL decision and a complete MCP journal interval with no matching service arrival.

![The actual macOS client shows the expanded host notice identifying the automatic governance-policy block of crew_denied.](../evidence/enterprise-managed/20260913/screenshots/native-managed-recorded-denial.jpg)

## 07. Understand what SEL coverage lists

Open **Settings → Security → Live Security Posture → SEL audit logging**.

Route: `/settings/security/posture`

The earlier expanded SEL row lists covered session-key surfaces, with 19 reported in the posture summary. Entries include Background, CLI, Cron and Dashboard. This capture predates managed policy.

This is a coverage list. It does not display the live security-event stream for a request. A native denial needs its blocked result, relevant SEL record and complete MCP journal interval. Where the SEL event lacks a trace field, keep the isolated-session correlation explicit.

Presenter cue: Use this screen to explain which surfaces emit audit records. Use the run’s sanitized receipt to inspect a particular decision.

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier expanded SEL coverage list; no per-request denial log is displayed here.

![The expanded SEL audit logging row lists session-key surfaces including Background, CLI, Cron and Dashboard.](admin-console-native-20260913/02-sel-coverage-viewport.png)

## 08. Separate backend choice from sign-in

Open **Developer → Agent Backend**.

Route: `/developer?tab=agent-backend`

This earlier screenshot shows Kiro CLI selected and a “Signed in with GitHub” card. That card reads KAS identity; the standalone CLI has its own sign-in state. At the earlier capture, the CLI was signed out.

The EC2 standalone CLI receipt records authenticated=true via SocialGitHub at 21:09 UTC. The original four-turn run and the later managed native receipts each establish their own results. The selected backend remains Kiro CLI 2.21.4. The card shown here is not evidence of enterprise SSO or the CLI's current sign-in by itself.

Presenter cue: Read the CLI’s own sign-in receipt, then the recorded native results. The two identity surfaces have separate evidence.

*September 13, 2026 · earlier baseline · before managed policy.* Before managed policy. Earlier backend page, retained to explain the two identity surfaces. The new CLI sign-in is documented separately.

![Kiro CLI is selected beside a GitHub sign-in card representing KAS identity.](admin-console/07-agent-backend.jpg)

## 09. Read Gateway instrumentation

Open **Settings → Privacy; Developer → Telemetry**.

Route: `/settings/privacy; /developer?tab=telemetry`

These metric captures all precede managed policy. They explain the dashboard's measurements; they do not report a new managed-policy run.

The earlier Privacy capture has Record metrics enabled and the anonymous usage heartbeat disabled by the Gateway environment. The retained MCP/IAM capture expands four completed turns with durations 12.3, 8.9, 14.2 and 17.7 seconds; its session total displays 0.5 credits after rounding.

The later captures show nine dashboard turns and 14 background turns, for throughput 23. Their header reports p50 latency 3.5 seconds, p90 latency 17.4 seconds and 0 runtime faults of 9. These aggregates include different sessions and outcomes; they are not a count of passed security tests.

Blocked bash command demonstration expands to one turn at 8:00:21 PM, with 0.12 credits and 6.8 seconds. Anonymous loopback security posture probe expands to one turn at 8:07:21 PM, with 0.27 credits and 50.4 seconds. Both times are September 13. The authentication turn includes two separate once-only approvals, so its duration includes the approval workflow.

The footer labels the metrics source local-only, no egress. That describes metric storage/export, not a network restriction on the agent or AWS requests. These rows establish recorded activity. The native results and separately reviewed server evidence identify each allowed or denied outcome.

Presenter cue: Read the named turn, timestamp and duration, then open its decision receipt. Explain why runtime faults, background throughput and policy refusals are different measurements.

*September 13, 2026 · earlier baseline · before managed policy.* Before managed policy. Earlier Privacy capture: metric recording on, anonymous heartbeat disabled by environment.

![Privacy shows Gateway metrics enabled and anonymous telemetry disabled.](admin-console/08-telemetry-controls.jpg)

*September 13, 2026 · evening capture · before managed policy.* Before managed policy. Earlier native Telemetry: four completed dashboard turns, four background turns and the expanded demo session’s durations and credits.

![Native Telemetry expands the MCP Tool Call Read Allowed session into four completed turns, with durations 12.3, 8.9, 14.2 and 17.7 seconds.](admin-console-native-20260913/10-native-turn-telemetry.png)

*September 13, 2026 · later evening capture (EDT) · before managed policy.* Before managed policy. Later Native Telemetry: Blocked bash command demonstration contains one turn at 8:00:21 PM, with 0.12 credits and 6.8 seconds. Aggregate throughput 23 includes 14 background turns.

![Native Telemetry expands the command-demonstration session into its one recorded turn and shows the aggregate runtime measurements.](admin-console-host-20260913/03-command-turn-metrics.jpg)

*September 13, 2026 · later evening capture (EDT) · before managed policy.* Before managed policy. Later Native Telemetry: Anonymous loopback security posture probe contains one turn at 8:07:21 PM, with 0.27 credits and 50.4 seconds. Its security outcome is established separately.

![Native Telemetry expands the anonymous-probe session into one recorded turn; the header shows 0 faults of 9 and throughput 23.](admin-console-host-20260913/04-anonymous-turn-metrics.jpg)

## 10. Read client and server health together

Open **Apps → Demo Observability**.

Route: `/apps/demo-observability`

All four collection captures below precede managed policy. Their values are dated samples, retained to explain the client/server health view.

The cards identify their source and sample time. The later Mac sample is 20:16:02, with 3.7% KiroCrew process CPU and 967.1 MiB process memory. The EC2 sample is 20:16:26, with 0.7% host CPU and 12.6 GiB memory available. Both are marked Current.

Read Local Gateway off on the Mac card, then the EC2 Gateway and separate MCP service checks. The client tunnel check establishes a local TCP listener. Current means the sample is fresh. Mac process CPU and EC2 host CPU use different sampling methods.

The expanded server measurements show 235 MiB for the Gateway main process and 147.5 MiB for the MCP main process. With the Server filter selected, the collection log contains one First sample collected event at 10:31:23. The later screenshot has a new Mac sample at 20:17:04; do not treat the two captures as one simultaneous sample.

Collection logs record first samples, health changes and collection errors. The Client and Server buttons filter that event stream. This custom App Kit page does not ingest native tool decisions, SEL records or MCP denial logs.

Presenter cue: Read both timestamps and individual checks. Expand server measurements and filter Server, then use separate security receipts for enforcement claims.

*September 13, 2026 · earlier baseline · before managed policy.* Before managed policy. Earlier custom telemetry capture: both samples Current, local Gateway off and server checks Yes.

![Demo Observability shows macOS client and EC2 server samples with freshness and service checks.](admin-console/11-client-server-telemetry.jpg)

*September 13, 2026 · earlier baseline · before managed policy.* Before managed policy. Earlier collection events include the observed client health change and recovery.

![Collection logs show source labels, timestamps, event levels and All, Client and Server filters.](admin-console/12-collection-logs.jpg)

*September 13, 2026 · later evening capture (EDT) · before managed policy.* Before managed policy. Later collection view: both samples are Current, the Mac local Gateway is off, and the EC2 Gateway/MCP checks read Yes. Mac and server sample times are 20:16:02 and 20:16:26.

![Demo Observability shows Current macOS and EC2 samples, local Gateway off, client 3.7% CPU and 967.1 MiB memory, and server 0.7% CPU with 12.6 GiB available.](admin-console-host-20260913/05-client-server-health.jpg)

*September 13, 2026 · later evening capture (EDT) · before managed policy.* Before managed policy. Server measurements expanded: Gateway 235 MiB and MCP 147.5 MiB main-process memory. The Server filter displays one First sample collected event; this is a collection-health log.

![Demo Observability shows expanded server process measurements and a Server-only collection log containing one First sample collected event at 10:31:23.](admin-console-host-20260913/06-server-collection-logs.jpg)

## 11. Inspect the native host results

Open **Recorded macOS client sessions; supporting receipts below**.

Route: `Native client results, not an admin-console route`

Three September 14 recordings complete the previously unfinished host checks. These images show the native Mac client. The existing admin screenshots and dashboard counters do not establish these outcomes.

Sensitive-path read: CLI argument validation returned ENOENT for the public canary. A later readback found the host file hidden from the current CLI descendants by a .aws tmpfs mask. The native classifier remains accepted:false; the readback does not identify the historical syscall PID.

Protected-path write: Crew's built-in hook blocked the marker, which remained absent. Its source files are root-owned. The hook runs before the managed filesystem rule, so this take tests that earlier hook. The host readback resolves the UI's conflicting 1 file changed heading and no changes row.

IMDS TCP: the user approved the helper source read once and execution once. One native execution made one fixed TCP attempt, returned errno 113, sent zero application bytes and requested no metadata. The Crew UID's firewall counter increased from 2 to 3 during the observed interval. This does not establish that the whole host lacks an IMDS route. The earlier unanswered IMDS approval timeout remains a separate historical take.

Open the three actual clips and sanitized receipts in the evidence list. Keep each result tied to its mechanism: filesystem visibility, a built-in write hook or an outbound network rule.

Presenter cue: Read the native result first, then the matching receipt. Do not count these frames as fresh admin-dashboard measurements.

*September 14, 2026 · native macOS result · not admin-console UI.* Actual recording frame at clip 24 seconds (raw 50 seconds). The native read returned ENOENT for the public canary. Separate current namespace evidence corroborates that the host file is hidden; this was not a read-hook denial.

![Actual native recording frame shows the public sensitive-path canary read returning ENOENT.](../output/native-host-managed-20260914/native-managed-sensitive-read/cue-03.jpg)

*September 14, 2026 · native macOS result · not admin-console UI.* Actual macOS client result: the prepared write was refused by the built-in protected-config write hook. The UI displays both 1 file changed and no changes. The separate host readback confirms the marker file is absent.

![The native macOS client reports a protected-config write refusal; its file panel displays both 1 file changed and no changes.](../evidence/managed-host-20260914/screenshots/protected-write-result.jpg)

*September 14, 2026 · native macOS result · not admin-console UI.* Actual macOS result: connected false, errno 113, zero application bytes sent and no metadata requested. The sanitized receipt joins the one native execution to the firewall counter changing from 2 to 3 in the observed interval.

![The native IMDS TCP result reports EHOSTUNREACH, zero application bytes and no metadata request.](../evidence/managed-host-20260914/screenshots/imds-tcp-result.jpg)

## Evidence

Host root retains authority. This deployment does not establish signed fleet policy, enterprise SSO or human-role RBAC. The Linux cc floor is not macOS Seatbelt or strict-tier isolation. The three host checks now have separate native recordings and sanitized evidence. The sensitive-read result is ENOENT with separate current namespace corroboration; it is not a read-hook denial. The earlier unanswered IMDS approval remains historical. The policy-layer SEL join uses the isolated session, tool, reason and interval; those SEL events have no direct tool-call or trace-ID field. Earlier MCP/IAM collection: The original collector receipt remains collection_complete=false because its recent SEL window lost the baseline anchor. Its exact bytes are retained locally; the linked publication export identifies the original by hash. A separate read-only recovery joined the retained rows. The generic reconciler keeps full_native_acceptance=false: it does not decide footage acceptance or every attribution check. Process sampling was not shown to overlap an approval, and SEL integrity relies on the original Gateway verification rather than independent per-row signatures.

- [September 14 native host result images and evidence bindings](../evidence/managed-host-20260914/tour-input.json)
- [index](../evidence/managed-host-20260914/index.json)
- [findings](../evidence/managed-host-20260914/findings.md)
- [public evidence review](../evidence/managed-host-20260914/public-evidence-review.json)
- [media review](../evidence/managed-host-20260914/media-review.json)
- [sensitive read](../evidence/managed-host-20260914/receipts/sensitive-read.json)
- [sensitive namespace](../evidence/managed-host-20260914/receipts/sensitive-namespace.json)
- [protected write](../evidence/managed-host-20260914/receipts/protected-write.json)
- [imds tcp](../evidence/managed-host-20260914/receipts/imds-tcp.json)
- [host state snapshots](../evidence/managed-host-20260914/receipts/host-state-snapshots.json)
- [manifest](../output/native-host-managed-20260914/manifest.json)
- [keyframe provenance](../output/native-host-managed-20260914/keyframe-provenance.json)
- [Read the protected .aws canary](../output/native-host-managed-20260914/native-managed-sensitive-read/native-managed-sensitive-read.mp4)
- [Try writing a protected configuration path](../output/native-host-managed-20260914/native-managed-protected-write/native-managed-protected-write.mp4)
- [Approve an IMDS TCP probe](../output/native-host-managed-20260914/native-managed-imds-tcp/native-managed-imds-tcp.mp4)
- [Managed policy, client state and screenshot summary](../evidence/enterprise-managed/20260913/managed-presentation.json)
- [Active managed policy readback](../evidence/enterprise-managed/20260913/policy-verify.json)
- [MCP configuration and policy readback](../evidence/enterprise-managed/20260913/mcp-verify.json)
- [Managed native allowed read and automatic deny correlation (ui3; read not filmed)](../evidence/enterprise-managed/20260913/native-managed-verification.json)
- [Filmed automatic managed MCP denial correlation (ui4)](../evidence/enterprise-managed/20260913/native-managed-ui4-verification.json)
- [Independent managed native artifact review](../evidence/enterprise-managed/20260913/native-managed-artifact-review.json)
- [Root-owned policy and separate service sandbox observations](../evidence/enterprise-managed/20260913/host-runtime-check.json)
- [Mac quit and relaunch with local Gateway off (before policy activation)](../evidence/enterprise-managed/20260913/client-relaunch.json)
- [Managed native clip review](../evidence/enterprise-managed/20260913/media-review.json)
- [Before managed policy: Fresh EC2 CLI authentication](../evidence/native-client-demo/20260913/authenticated.json)
- [Before managed policy: MCP and IAM enforcement contract](../infrastructure/mcp-enforcement/README.md)
- [Before managed policy: Custom telemetry data contract](../infrastructure/observability/APP-INSTALL.md)
- [Before managed policy: Earlier screenshot capture receipt](../evidence/admin-console/browser-receipt.json)
- [Before managed policy: Final four-outcome reconciliation](../evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json)
- [Before managed policy: Independent reconciliation review](../evidence/native-client-demo/20260913-ui2-reconciled-final/review.json)
- [Before managed policy: MCP and IAM authority attribution review](../evidence/native-client-demo/20260913-ui2/authority-attribution-review.json)
- [Before managed policy: Publication export of the incomplete collector receipt](../evidence/native-client-demo/20260913-ui2/receipt-publication.json)
- [Before managed policy: Native MCP clip review](../evidence/native-client-demo/media-review-mcp-controls.json)
- [Before managed policy: Later host workspace-read observations](../evidence/native-client-demo/host-20260913-ui3/initial-observations.json)
- [Before managed policy: Later native command-rule observations](../evidence/native-client-demo/host-20260913-ui3/command-observations.json)
- [Before managed policy: Independent initial host review](../evidence/native-client-demo/host-20260913-review/initial-review.json)
- [Before managed policy: Anonymous Gateway authentication correlation](../evidence/native-client-demo/host-20260913-ui3/auth-correlation.json)
- [Before managed policy: Independent anonymous Gateway authentication review](../evidence/native-client-demo/host-20260913-review/auth-review.json)
- [Before managed policy: Temporary command-rule cleanup readback](../evidence/native-client-demo/host-20260913-ui3/command-rule-cleanup.json)
- [Before managed policy: Current native admin findings](../output/kirocrew-native-admin-findings.md)
- [Current findings, followed by the preserved September 13 findings](../output/kirocrew-admin-findings.md)
- [Native run receipt 1 (read its recorded verdict)](../evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json)
- [Native run receipt 2 (read its recorded verdict)](../evidence/native-client-demo/20260913-ui2-reconciled-final/review.json)
- [Native run receipt 3 (read its recorded verdict)](../evidence/native-client-demo/20260913-ui2/authority-attribution-review.json)
- [Native run receipt 4 (read its recorded verdict)](../evidence/native-client-demo/20260913-ui2/receipt-publication.json)

## What changed

Retained all 26 prior images and added one native-results stop with three original result images and links to the three actual clips. Updated the sensitive-read, protected-write and IMDS status from their sanitized receipts; preserved the earlier unanswered IMDS take and its limits.
