# KiroCrew admin console walkthrough

Observed September 13, 2026 · Owner dashboard · ARM EC2 demo

The Mac is the client. The Gateway, Kiro CLI and demo workspace run on the ARM EC2 host. This tour follows the owner dashboard through host health, security settings, backend status and telemetry. The screenshots show the deployed September 13 demo; values and timestamps are observations from the capture, not live readings.

ARM EC2 and the remote dashboard are running. The direct MCP and AWS checks passed. Kiro CLI is selected for new sessions, but its native sign-in is still pending. A completed native tool call, approval and enforcement trace remain separate acceptance checks.

## Deployment at capture

| Component | Observed configuration |
| --- | --- |
| Client | macOS · September 13 Nightly · local Gateway off |
| Connection | Local port 5599 → pinned SSH tunnel → EC2 Gateway on loopback 5476 |
| Server | t4g.xlarge · ARM64 · 4 vCPU · 16 GiB RAM · 40 GiB encrypted gp3 |
| Server build | Custom Linux ARM repack of 0.7.0-nightly.20260912t060850 |
| Backend | Kiro CLI 2.21.4 · selected · independent sign-in pending |
| Inbound access | TCP 22 from 24.60.107.229/32 only · us-east-1 |

The original x86 host is stopped and retained for rollback. The current owner dashboard is reached through the existing SSH tunnel at `http://localhost:5599`; it has no public Gateway or MCP ingress.

## Walkthrough

### 01. Start with the connected Gateway

Open **Settings → Overview**.

Overview reports “All systems running” and server version 0.7.0-nightly.20260912t060850. At capture, uptime was 5m 35s and the session and message counters were zero.

This is the remote Gateway’s health and activity summary. A green Gateway status does not establish that the selected coding backend can start a session.

Presenter cue: Point out the server build, then explain that the Mac can run a newer desktop build while displaying the EC2 dashboard.

![KiroCrew Settings Overview shows All systems running, the September 12 server Nightly and zero sessions and messages.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/01-overview.png)

### 02. Verify which machine is doing the work

Open **Developer → System → Performance**.

The CPU panel identifies aarch64 and four logical processors. The footer shows Linux, host ip-172-31-8-10 and working directory /srv/kirocrew-demo/workspace.

These readings identify the remote ARM host behind the dashboard. CPU, memory, disk and network values describe this server. The CloudFormation receipt supplies the instance type, 16 GiB allocation and 40 GiB volume.

Presenter cue: Open Memory if the audience wants capacity detail. Keep the architecture’s endpoint-control enclosure around the Gateway, backend and workspace on EC2.

![System Performance identifies aarch64, four logical processors, Linux and the EC2 workspace path.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/02-arm-performance.png)

### 03. Read service counts in their process scope

Open **Developer → System → Services**.

The captured Gateway process is PID 4991, with 197 MB RSS. Embeddings are stopped. The panel reports zero MCP processes in its inventory.

The demo MCP runs as a separate systemd service and Unix user. This Gateway process inventory does not count that service. Use the custom observability page’s MCP checks and the direct MCP receipt to inspect it.

Presenter cue: Explain the zero before showing the separate MCP service later. The stopped embeddings service is intentional in this demo.

![System Services shows the remote Gateway process, 197 MB RSS, stopped embeddings and zero MCP processes in its process inventory.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/03-gateway-services.png)

### 04. Inspect the configured security controls

Open **Settings → Security → Live Security Posture**.

The page lists a Standard process sandbox and Interactive tool approval. The visible registry counts are 143 sensitive credential paths, 23 protected configuration paths and 112 built-in denied-command rules.

This view reports configured controls. Counts and status labels do not prove that a native backend delivered a pre-execution hook, that a sandbox ran or that a particular action was blocked.

Presenter cue: Expand a control when explaining its coverage. Tie each claimed enforcement result to the corresponding execution receipt rather than a green label.

![Live Security Posture shows Standard process sandbox, Interactive approval, 143 sensitive paths, 23 protected paths and 112 built-in denied-command rules.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/04-security-posture.png)

### 05. Keep the demo in Interactive mode

Open **Settings → Security → YOLO (auto-approve)**.

The sidebar says Interactive. The six-hour selection sets how long auto-approve would last the next time it is turned on.

A duration selection is not an active approval bypass. The walkthrough leaves auto-approve off so a future authenticated Kiro CLI run can demonstrate the native approval step.

Presenter cue: Read the current mode in the sidebar and the sentence below the duration choices. Do not activate auto-approve during the tour.

![YOLO settings show Interactive in the sidebar and a six-hour duration selected for the next activation of auto-approve.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/05-interactive-approval.png)

### 06. Check whether an enterprise policy is present

Open **Settings → Security → Governance Policy**.

The effective security ceiling panel says “No enterprise policy in effect.” This host is in standalone mode.

The demo’s configured deny rule and built-in safeguards coexist with an absent enterprise policy. The crew-writable demo configuration does not establish an immutable managed policy floor.

Presenter cue: Use this screen to distinguish the deployed demo from the architecture’s proposed central policy distribution.

![Governance Policy states No enterprise policy in effect and describes the standalone host mode.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/06-governance.png)

### 07. Confirm Kiro CLI, then verify its own sign-in

Open **Developer → Agent Backend**.

Kiro CLI is selected, matching the original walkthrough and the user’s explicit choice. The page also shows a “Signed in with GitHub” card.

That card reads the KAS sign-in state. The standalone Kiro CLI has a separate login state and still reports signed out. Selecting the CLI changes the backend for new sessions; an existing session retains its original backend.

Presenter cue: Treat the CLI’s own login check and a successful new native session as the acceptance gate. The next screenshot shows why the card alone is insufficient.

![Agent Backend has Kiro CLI selected while a separate Kiro sign-in card says Signed in with GitHub.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/07-agent-backend.png)

### 08. Enable local metrics and inspect the export settings

Open **Settings → Privacy → Telemetry controls**.

Record metrics is on. The anonymous usage heartbeat is off because KIROCREW_TELEMETRY_DISABLED is set in the Gateway environment.

Native server metrics flush every 10 seconds with seven days of retention and a 64 MiB cap. No OTLP destination is configured. The separate client collector sends bounded process and connection measurements to this EC2 host through the pinned SSH connection.

Presenter cue: Show the recording switch, then name the destination and retention. The remote Settings page controls this Gateway; it does not configure a local Mac Gateway.

![Privacy has Record metrics enabled and the anonymous usage heartbeat disabled by the Gateway environment.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/08-telemetry-controls.png)

### 09. Read native Gateway instrumentation

Open **Developer → Telemetry**.

The Instruments table contains real Gateway request duration and boot duration measurements, plus process counters. At capture it showed 1,983 request samples and one boot sample. Completed turn throughput was zero.

Native instrumentation is recording Gateway activity. The “Last 14d” query window does not override the configured seven-day retention. Zero turn latency and zero faults are empty-turn statistics here, so they do not establish a successful backend session.

Presenter cue: Point at the request sample count to prove recording, then move to the combined client and server page for the custom collectors.

![Native Telemetry shows Gateway request and boot duration samples, process counters and zero completed turn samples.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/09-native-telemetry.png)

### 10. Use the native log to explain the remaining failure

Open **Developer → Logs · search AcpRuntime dead**.

The filtered Gateway log records repeated CLI exits with code 1, including two attempts at 14:34 UTC on September 13. The reason is explicit: “You are not logged in, please log in with kiro-cli login.”

This is an observed backend authentication failure. It explains why a connected Gateway, a selected CLI and the GitHub sign-in card have not produced a completed native run.

Presenter cue: Keep the filter on this known diagnostic. Resume the original Kiro CLI sign-in flow, then rerun the native walkthrough and capture new evidence before claiming native enforcement.

![Native Logs filtered to AcpRuntime dead show Kiro CLI exit code one and the message You are not logged in.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/10-native-auth-log.png)

### 11. Show client and server telemetry together

Open **Apps → Demo Observability**.

The custom App Kit page presents separate Mac client and EC2 server cards. Each card carries a sample timestamp, age and freshness label, followed by its measured checks.

The client collector measures KiroCrew desktop processes, the local SSH tunnel listener and the absence of a local Gateway listener. The server collector measures host resources, the Gateway and the separate MCP service. CPU sampling methods differ between the two sources.

Presenter cue: Read “Local Gateway off,” then the server Gateway and MCP checks. A reachable tunnel listener proves a local TCP listener; the connected owner dashboard supplies separate application-level evidence.

![The custom Demo Observability page shows current Mac client and EC2 server metrics, connection and service checks, and collection events.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/11-client-server-telemetry.png)

### 12. Inspect the collection logs and their limits

Open **Apps → Demo Observability → Collection logs**.

Collection logs list first samples, check changes, probe errors and recovery events. All, Client and Server buttons filter the same bounded event stream.

Both collectors sample every 60 seconds. The page refreshes every 15 seconds and marks a sample stale after three minutes. It retains 240 samples per source and 200 collection events. Events use fixed labels and exclude arbitrary logs, prompts and credentials.

Presenter cue: Filter Client, then Server. Routine unchanged samples do not add log rows. These collection events support operational diagnosis; native security-event and tool-enforcement receipts remain separate.

Screenshot capture pending; this draft is not a completed browser-validation receipt.

## Live demo order

1. **Locate the endpoint.** Show Overview and System Performance. Point out the remote ARM host and workspace, with the local Gateway off.
2. **Explain the controls.** Open Live Security Posture, Interactive approval and Governance Policy. State which controls are configured and that no enterprise policy is loaded.
3. **Check the chosen backend.** Show Kiro CLI selected and the filtered authentication failure. Keep the native run pending until the CLI itself is authenticated.
4. **Show two telemetry sources.** Open native Telemetry for Gateway measurements, then Demo Observability for the Mac and EC2 collectors.
5. **Read the evidence.** Filter collection logs by source and check sample freshness. Use the passing direct MCP/AWS receipt for those enforcement results.
6. **Continue after sign-in.** Start a new Kiro CLI session, run the approved native walkthrough and record the tool call, approval, denial and correlated events before updating the claims.

## Operational notes

Native server metrics use a 10-second export interval, seven-day retention and a 64 MiB cap. Anonymous product reporting is off and no OTLP endpoint is configured. The custom client and server collectors run every minute; the owner app reads their samples without a write endpoint. Collector history is local to this EC2 host, with about four hours per source at continuous collection and up to 200 status events.

The screenshots are original browser captures. They were not redrawn, retouched or populated with demonstration fixtures. Captured counts, process IDs and sample ages will change as the system runs.

## Evidence and next action

Read the [findings](/Users/noahsutter/git-projects/kirocrew-demo/output/kirocrew-admin-findings.md), [ARM cloud verification](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/final-cloud-verification.json) and [direct MCP/AWS receipt](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/mcp-live-receipt.json). The [custom app contract](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability/APP-INSTALL.md) and [collector contract](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability-collector/README.md) define the displayed measurements and retention.

Complete standalone Kiro CLI sign-in on EC2, start a new native session and rerun the original enforcement walkthrough. Keep the current screenshots as the pre-authentication baseline; save the successful native run and its correlated events as new evidence.

## What changed

The editing pass replaced broad health and security claims with the exact observed scope, shortened repeated cautions and kept the operator cues direct. Product labels, measured counts, retention settings and the pending CLI sign-in remain explicit.


# KiroCrew admin console findings

Observed September 13, 2026 · ARM EC2 demo

The owner dashboard makes the remote host and its controls inspectable. The main confusion is backend identity: the GitHub card can look ready while the selected standalone Kiro CLI is signed out. The screenshots preserve that state rather than implying a completed native run.

## 1. Backend sign-in can be misread

The Kiro sign-in card reports GitHub authentication while standalone Kiro CLI exits as signed out. The card reads KAS state. Label those identities separately in a future product fix; for this demo, show the CLI’s own result and retain the native-authentication gate.

Evidence: `07-agent-backend.png; 10-native-auth-log.png`.

## 2. Gateway health is broader than backend readiness

Overview says all systems are running while the CLI cannot start. Use Overview to establish dashboard and Gateway health; use a completed native session to establish backend readiness.

Evidence: `01-overview.png; 10-native-auth-log.png`.

## 3. The MCP count has a narrower process scope

System Services reports zero MCP processes, but the demo MCP runs under a separate Unix user and systemd unit. The custom collector displays that unit’s health. The passing direct MCP/AWS receipt establishes the tested tool behavior.

Evidence: `03-gateway-services.png; 11-combined-telemetry.png; evidence/aws/arm-20260913/mcp-live-receipt.json`.

## 4. Security status reports configuration

The posture page lists Standard sandbox, Interactive approval and control counts. No enterprise policy is in effect. Keep those labels separate from claims about executed sandboxing, pre-execution callbacks and immutable policy governance.

Evidence: `04-security-posture.png; 05-interactive-approval.png; 06-governance.png`.

## 5. The auto-approve duration needs its context

Six hours is selected as the duration for the next activation, while the current mode is Interactive. Explain both labels together so the duration is not read as an active bypass.

Evidence: `05-interactive-approval.png`.

## 6. Native telemetry needs sample-count context

Gateway duration measurements are present, but completed-turn samples are zero. A zero fault rate over zero turns is not a passed backend test. The displayed 14-day query window can include at most the configured seven-day retention.

Evidence: `08-telemetry-controls.png; 09-native-telemetry.png`.

## 7. Client and server collection is visible in a custom app

The native Telemetry panel continues to show Gateway instrumentation. The installed Demo Observability App Kit page adds the two collectors and collection-event filters inside the owner dashboard. It is a demo extension with local bounded storage.

Evidence: `11-combined-telemetry.png; 12-collection-logs.png`.

## 8. Freshness and measurement definitions affect interpretation

Samples older than three minutes become stale. Mac CPU sums process scheduler averages and can exceed 100%; server host CPU uses a one-second normalized sample. The local tunnel probe checks listener reachability. None of these health probes establishes an authorized model response.

Evidence: `infrastructure/observability-collector/README.md; infrastructure/observability/APP-INSTALL.md`.

## Demo changes

The demo now uses the ARM host as its single execution endpoint and keeps the Mac Gateway off. The admin walkthrough adds native Gateway telemetry, a custom page for both client and server health, and source-filtered collection logs. The presentation must name the custom page as an App Kit extension and keep the CLI authentication failure visible until a new successful native run supersedes it.

## What remains to be demonstrated

The direct MCP probe verified authentication, catalog, an allowed S3 read, grant denial before AWS dispatch and an IAM-denied read. Complete the separate native Kiro CLI login, approval, hook, sandbox and security-event correlation checks before presenting those as end-to-end Crew enforcement.

## What changed

The editing pass made each finding traceable to a screen or contract, removed repeated setup and preserved the distinctions between configuration, health measurements and executed enforcement.
