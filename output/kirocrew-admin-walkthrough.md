# KiroCrew admin console walkthrough

Observed September 13, 2026 · Owner dashboard · ARM EC2 demo

The Mac is the client. The Gateway, Kiro CLI and demo workspace run on the ARM EC2 host. This tour follows the owner dashboard through host health, security settings, backend status and telemetry. The screenshots preserve the deployed September 13 demo, including the values and timestamps visible at capture.

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

![KiroCrew Settings Overview shows All systems running, the September 12 server Nightly and zero sessions and messages.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/01-overview.jpg)

### 02. Verify which machine is doing the work

Open **Developer → System → Performance**.

The CPU panel identifies aarch64 and four logical processors. The footer shows Linux, host ip-172-31-8-10 and working directory /srv/kirocrew-demo/workspace.

CPU, memory, disk and network values describe the remote ARM server. The CloudFormation receipt supplies the instance type, 16 GiB allocation and 40 GiB volume.

Presenter cue: Open Memory if the audience wants capacity detail. Keep the architecture’s endpoint-control enclosure around the Gateway, backend and workspace on EC2.

![System Performance identifies aarch64, four logical processors, Linux and the EC2 workspace path.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/02-arm-performance.jpg)

### 03. Read service counts in their process scope

Open **Developer → System → Services**.

The captured Gateway process is PID 4991, with 197 MB RSS. Embeddings are stopped. The panel reports zero MCP processes in its inventory.

The demo MCP runs as a separate systemd service and Unix user. This Gateway process inventory does not count that service. Use the custom observability page’s MCP checks and the direct MCP receipt to inspect it.

Presenter cue: Explain the zero before showing the separate MCP service later. The stopped embeddings service is intentional in this demo.

![System Services shows the remote Gateway process, 197 MB RSS, stopped embeddings and zero MCP processes in its process inventory.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/03-gateway-services.jpg)

### 04. Inspect the configured security controls

Open **Settings → Security → Live Security Posture**.

The page lists a Standard process sandbox and Interactive tool approval. The visible registry counts are 143 sensitive credential paths, 23 protected configuration paths and 112 built-in denied-command rules.

This view reports configured controls. Counts and status labels do not prove that a native backend delivered a pre-execution hook, that a sandbox ran or that a particular action was blocked.

Presenter cue: Expand a control when explaining its coverage. Tie each enforcement result to its execution receipt.

![Live Security Posture shows Standard process sandbox, Interactive approval, 143 sensitive paths, 23 protected paths and 112 built-in denied-command rules.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/04-security-posture.jpg)

### 05. Keep the demo in Interactive mode

Open **Settings → Security → YOLO (auto-approve)**.

The sidebar says Interactive. The six-hour selection sets how long auto-approve would last the next time it is turned on.

Auto-approve remains off, so a future authenticated Kiro CLI run can demonstrate the native approval step.

Presenter cue: Read the current mode in the sidebar and the sentence below the duration choices. Do not activate auto-approve during the tour.

![YOLO settings show Interactive in the sidebar and a six-hour duration selected for the next activation of auto-approve.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/05-interactive-approval.jpg)

### 06. Check whether an enterprise policy is present

Open **Settings → Security → Governance Policy**.

The effective security ceiling panel says “No enterprise policy in effect.” This host is in standalone mode.

The built-in safeguards and demo deny rule remain configured. The demo configuration is writable by crew; an immutable managed policy floor has not been deployed.

Presenter cue: Use this screen to distinguish the deployed demo from the architecture’s proposed central policy distribution.

![Governance Policy states No enterprise policy in effect and describes the standalone host mode.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/06-governance.jpg)

### 07. Confirm Kiro CLI, then verify its own sign-in

Open **Developer → Agent Backend**.

Kiro CLI is selected, matching the original walkthrough and the user’s explicit choice. The page also shows a “Signed in with GitHub” card.

That card reads the KAS sign-in state. The standalone Kiro CLI has a separate login state and still reports signed out. Selecting the CLI changes the backend for new sessions; an existing session retains its original backend.

Presenter cue: Check the CLI’s own login state before starting a new native session. Screen 10 shows the observed authentication failure.

![Agent Backend has Kiro CLI selected while a separate Kiro sign-in card says Signed in with GitHub.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/07-agent-backend.jpg)

### 08. Inspect Gateway metric recording and export settings

Open **Settings → Privacy → Telemetry controls**.

Record metrics is on. The anonymous usage heartbeat is off because KIROCREW_TELEMETRY_DISABLED is set in the Gateway environment.

Native server metrics flush every 10 seconds with seven days of retention and a 64 MiB retention target. No OTLP destination is configured. The separate client collector sends bounded process and connection measurements to this EC2 host through the pinned SSH connection.

Presenter cue: Show the recording switch, then name the destination and retention. The remote Settings page controls this Gateway; it does not configure a local Mac Gateway.

![Privacy has Record metrics enabled and the anonymous usage heartbeat disabled by the Gateway environment.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/08-telemetry-controls.jpg)

### 09. Read native Gateway instrumentation

Open **Developer → Telemetry**.

The Instruments table contains real Gateway request duration and boot duration measurements, plus process counters. At capture it showed 1,983 request samples and one boot sample. Completed turn throughput was zero.

Native instrumentation is recording Gateway activity. The “Last 14d” query window does not override the configured seven-day retention. Zero turn latency and zero faults are empty-turn statistics here, so they do not establish a successful backend session.

Presenter cue: Point at the request sample count. Next, inspect the native failure log before opening the combined client and server page.

![Native Telemetry shows Gateway request and boot duration samples, process counters and zero completed turn samples.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/09-native-telemetry.jpg)

### 10. Use the native log to explain the remaining failure

Open **Developer → Logs · search AcpRuntime dead**.

The filtered Gateway log records repeated CLI exits with code 1, including two attempts at 14:34 UTC on September 13. The reason is explicit: “You are not logged in, please log in with kiro-cli login.”

This is an observed backend authentication failure. It explains why a connected Gateway, a selected CLI and the GitHub sign-in card have not produced a completed native run.

Presenter cue: Keep the filter on this known diagnostic. Resume the original Kiro CLI sign-in flow, then rerun the native walkthrough and capture new evidence before claiming native enforcement.

![Native Logs filtered to AcpRuntime dead show Kiro CLI exit code one and the message You are not logged in.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/10-native-auth-log.jpg)

### 11. Show client and server telemetry together

Open **Apps → Demo Observability**.

Both cards are marked Current. The captured Mac sample shows 4% process CPU and 772.4 MiB process memory; EC2 shows 6.2% host CPU and 14.6 GiB available RAM. “Local Gateway off” and all four server service and loopback checks read Yes.

The client collector measures KiroCrew desktop processes, the local SSH tunnel listener and the absence of a local Gateway listener. The server collector measures host resources, the Gateway and the separate MCP service. CPU sampling methods differ between the two sources.

Presenter cue: Read “Local Gateway off,” then the server Gateway and MCP checks. A reachable tunnel listener proves a local TCP listener; the connected owner dashboard supplies separate application-level evidence.

![The custom Demo Observability page shows current Mac client and EC2 server metrics, connection and service checks, and collection events.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/11-client-server-telemetry.jpg)

### 12. Observe the server while the desktop is closed

Open **Apps → Demo Observability · controlled desktop pause**.

During a controlled quit of the Mac desktop app, its process CPU and memory dropped to zero and “KiroCrew desktop running” changed to No. The SSH tunnel listener and all four server checks stayed Yes. The browser dashboard remained available.

The EC2 Gateway and MCP continued while the desktop was closed. The client sample still says Current because it is fresh; read the individual checks for health. The Mac app was relaunched after this capture and reconnected to the remote Gateway.

Presenter cue: Use this captured pause to explain client and server independence. If repeating it live, keep the browser dashboard and SSH tunnel open, quit only the desktop app, then relaunch it and check recovery.

![During a controlled desktop pause, the client card shows zero process CPU and memory and desktop running No, while the tunnel and all server checks remain Yes.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/13-client-stopped.jpg)

### 13. Inspect the collection logs and their limits

Open **Apps → Demo Observability → Collection logs**.

Four events are visible: the two first samples, the client’s health change at 10:44:42 EDT (14:44:42 UTC), and its recovery at 10:49:34 EDT (14:49:34 UTC). The health change is a warning; recovery is info. All, Client and Server buttons filter the same event stream.

Both collectors sample every 60 seconds. The page refreshes every 15 seconds and marks a sample stale after three minutes. It retains 240 samples per source and 200 collection events. Events use fixed labels and exclude arbitrary logs, prompts and credentials.

Presenter cue: Filter Client, then Server. Routine unchanged samples do not add log rows. These collection events support operational diagnosis; native security-event and tool-enforcement receipts remain separate.

![Demo Observability collection logs show source labels, collection events and timestamps with All, Client and Server filters.](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/12-collection-logs.jpg)

## Live demo order

1. **Locate the endpoint.** Show Overview and System Performance. Point out the remote ARM host and workspace, with the local Gateway off.
2. **Explain the controls.** Open Live Security Posture, Interactive approval and Governance Policy. State which controls are configured and that no enterprise policy is loaded.
3. **Check the chosen backend.** Show Kiro CLI selected and the filtered authentication failure. Keep the native run pending until the CLI itself is authenticated.
4. **Show two telemetry sources.** Open native Telemetry for Gateway measurements, then Demo Observability for the Mac and EC2 collectors.
5. **Read the evidence.** Show the captured desktop pause and recovery. Filter collection logs by source and check sample freshness. Use the passing direct MCP/AWS receipt for those enforcement results.
6. **Continue after sign-in.** Start a new Kiro CLI session, run the approved native walkthrough and record the tool call, approval, denial and correlated events before updating the claims.

## Operational notes

Native server metrics use a 10-second export interval, seven-day retention and a 64 MiB retention target. Pruning protects active writers, so storage can temporarily exceed the target; see the [telemetry runbook](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/RUNBOOK.md:97). Anonymous product reporting is off and no OTLP endpoint is configured. The custom client and server collectors run every minute; the owner app reads their samples without a write endpoint. Collector history is local to this EC2 host, with about four hours per source at continuous collection and up to 200 status events.

The screenshots are original browser captures. They were not redrawn, retouched or populated with demonstration fixtures. Captured counts, process IDs and sample ages will change as the system runs.

## Evidence and next action

Read the [findings](/Users/noahsutter/git-projects/kirocrew-demo/output/kirocrew-admin-findings.md), [ARM cloud verification](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/final-cloud-verification.json), [direct MCP/AWS receipt](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/mcp-live-receipt.json), [telemetry API readback](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/observability-api-readback.json) and [telemetry runtime verification](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/observability-runtime-receipt.json). The [custom app contract](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability/APP-INSTALL.md) and [collector contract](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability-collector/README.md) define the displayed measurements and retention.

Follow the [fresh EC2 sign-in procedure](/Users/noahsutter/git-projects/kirocrew-demo/scripts/EC2-LOGIN.md), then use the [native evidence runner](/Users/noahsutter/git-projects/kirocrew-demo/scripts/native-backend-demo.README.md) to start a new Kiro CLI session and rerun the enforcement walkthrough. Keep these screenshots as the pre-authentication baseline; save a successful native run and its correlated events as new evidence.

## What changed

The editing pass clarified which host the metric settings control, corrected the screen order and linked the sign-in and native-run procedures. It shortened repeated cautions, corrected the 64 MiB setting to a retention target and preserved the measured values and pending CLI sign-in.
