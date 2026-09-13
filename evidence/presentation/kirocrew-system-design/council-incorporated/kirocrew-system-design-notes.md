# KiroCrew system-design presentation

Recorded September 13, 2026. This presentation uses dated receipts and screenshots. It does not poll the live system.

## 1. KiroCrew on ARM

### On slide



KiroCrew / System design & demo

Remote execution.

Local desktop.

The Mac connects to a KiroCrew environment on EC2. The Gateway and workspace stay on the server.

ARM deployment, direct MCP/AWS checks and telemetry collection verified.

Native Kiro CLI sign-in and session pending.

Recorded September 13, 2026

CloudFormation in us-east-1   /   Architecture and recorded demo evidence

### Speaker notes

The Mac runs the desktop client. A t4g.xlarge EC2 host runs the Gateway, Kiro CLI installation, workspace and separate MCP service. The local Gateway is off. Direct MCP and AWS checks passed on ARM. Native Kiro CLI authentication and a verified backend session remain pending. Native Gateway metric collection and the custom client/server app are active. Collection events show a controlled Mac client quit and restart while the server Gateway remained running. Sources: evidence/aws/arm-20260913/final-cloud-verification.json; evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json; evidence/aws/arm-20260913/client-runtime-receipt.json; evidence/aws/arm-20260913/observability-runtime-receipt.json.

## 2. What this demo must establish

### On slide



01 The desktop connects to EC2

The Mac's local Gateway stays off.

02 Access stays bounded

SSH ingress from the operator's IPv4 /32. Separate Crew and MCP identities.

03 Each refusal has a stopping point

Crew configuration, MCP grants and target AWS IAM have distinct roles.

04 Both machines are observable

Client health, server health and collection events appear in the admin portal.

Demo assumption

One operator on

one execution host

Concurrency, latency and availability targets still need native-session measurements.

Remaining acceptance gate Sign in to the EC2 Kiro CLI and verify the four native turns.

Scope: a single-operator demo. Native backend enforcement remains pending.

### Speaker notes

Design assumptions: this edition covers one operator on one ARM EC2 host. Service-level objectives, sustained-load capacity and multi-user isolation still need validation.

The demo requires a remote Gateway, inbound access restricted to the operator's IP, backend MCP/AWS enforcement and client/server telemetry. The dated receipts establish the deployment, direct service checks and operational telemetry. Native Kiro CLI authentication and execution remain pending. Sources: HANDOFF.md; ARM-CONTINUATION-RECEIPT.json; WALKTHROUGH.md.

## 3. One endpoint-control boundary

### On slide



EC2 contains the Gateway, selected backend and workspace. The laptop is the client.

Reference diagram · September 11 Includes controls beyond this demo.

Crew can edit demo configuration and App Kit code. Protected policy and path enforcement are unverified.

ARM checks: September 13. Expand the reference to inspect its labels.

Verified: remote connection, direct MCP grants and S3 IAM. Sandbox, egress control and SEL/HMAC execution unverified.

### Speaker notes

The enclosure maps controls around the execution host. In remote mode, the Gateway, selected backend and workspace run on the same host. The reference includes enterprise controls and Crew capabilities beyond this demo. The desktop is connected to the ARM host with the local Gateway off. The ARM probe verifies direct MCP grants and S3 IAM outcomes. Native backend enforcement and sandbox behavior remain pending. The reference cites the September 11 baseline. Sources: kirocrew-security-layers.html; evidence/nightly/baseline-verification.json; evidence/aws/arm-20260913/client-runtime-receipt.json; evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json.

## 4. ARM execution in us-east-1

### On slide



Verified direct path EC2 probe (mcp-demo) → MCP :8001 → S3

4 vCPU t4g.xlarge, ARM64

16 GiB Host memory

40 GiB Encrypted gp3 root

SSH /32 Only inbound rule

Recorded September 13: cloud 14:22 UTC, ingress 14:57 UTC. Diagram shows native MCP path pending.

### Speaker notes

CloudFormation manages the active t4g.xlarge: four vCPUs, 16 GiB RAM and 40 GiB encrypted gp3 storage. The security group admits TCP 22 only from the client IPv4 /32. SSH forwards laptop port 5599 to EC2 loopback port 5476. The Gateway, Kiro CLI installation and workspace share the Crew execution boundary. The MCP service uses a separate UID and listens on loopback port 8001. IMDSv2 is required with a hop limit of one. The original x86 instance is stopped and remains available for rollback. Its 24 GiB disk remains billable. Cloud verification passed at 2026-09-13T14:22:25Z. The direct probe is a separate path from mcp-demo to the MCP service and S3. The native Gateway/Kiro CLI path to MCP is pending sign-in and is drawn dashed. The resource check does not establish native backend authentication or telemetry health. Sources: infrastructure/ec2-demo.json; evidence/aws/arm-20260913/final-cloud-verification.json; evidence/aws/arm-20260913/host-checks.txt.

## 5. Host identity determines authority

### On slide



Identity / Responsibility / Policy and evidence /

crew / Gateway, backend and workspace / Observed: IPv4 metadata TCP denied errno 113. No HTTP request or credential read. /

mcp-demo / Fixed MCP tools and S3 reads / Role policy: two S3 prefixes, explicit deny SSM core attached; SSM execution untested. /

Administrator Operator SSH account, sudo / Installs code and manages services / Trusted host administration Core Gateway and MCP runtime files are root-owned. /

Crew can edit configuration and custom App Kit code. Immutable policy and tamper resistance remain unverified.

IPv4 metadata connection check at 14:56 UTC. Separate from native sandbox proof.

### Speaker notes

Root owns the core Gateway and MCP runtime files and service definitions. The custom App Kit backend runs with Crew authority; its installed app files are Crew-writable. The crew user runs the Gateway, backend and workspace. An owner-based firewall rule blocks metadata requests from the crew UID, and the Gateway requires that guard service. A TCP-only check as crew at 14:56:15 UTC could not connect to the IPv4 metadata address on port 80, returning errno 113. It sent no HTTP request and read no metadata credentials. This check does not cover IPv6 or native agent sandbox execution. The mcp-demo UID can obtain the instance role through IMDSv2. That role permits reads under two demonstration S3 prefixes, explicitly denies GetObject under denied/, and includes the SSM core managed policy. The MCP service exposes four fixed tools. Root remains a trusted administrator. The operator’s IAM user keys remain local. Crew owns and can edit its configuration. The desktop uses the existing administrator account to invoke the verified owner-token helper; the helper enters the Gateway mount namespace and then drops to crew for the stock token mint. Crew has no new sudo permission. Sources: infrastructure/bootstrap.sh; infrastructure/kirocrew-demo.service; infrastructure/kirocrew-mcp-demo.service; infrastructure/mcp-enforcement/server.py; infrastructure/ec2-demo.json; evidence/aws/arm-20260913/observability-runtime-receipt.json; evidence/aws/arm-20260913/client-runtime-receipt.json; evidence/aws/arm-20260913/crew-imds-connect-receipt.json.

## 6. Four calls, three denial boundaries

### On slide



Tool / Result / Stopping point /

read_allowed / Allowed object digest / S3 completes the read /

crew_denied / Configured. Native proof pending. / Crew before MCP dispatch /

mcp_denied / tool_grant_denied / MCP before AWS dispatch /

iam_denied / S3 AccessDenied, HTTP 403 / AWS IAM /

The direct probe covers three tools. Only a native turn can establish the configured Crew denial.

Contract: fixed S3 actions and objects. Caller supplies a trace ID. No general-purpose AWS tool.

### Speaker notes

The direct probe verified read_allowed, mcp_denied and iam_denied. Native Crew denial is pending. read_allowed returns the object length and digest. The MCP service grants crew_denied so the Crew hook can block it before dispatch. Its configured rule names @aws-enforcement/crew_denied. mcp_denied appears in discovery, but the service rejects the call before loading AWS credentials or invoking the SDK. iam_denied passes the MCP grant and attempts GetObject on an existing object under denied/, where IAM applies the explicit deny. After native sign-in, inspect each request and approve the three routed calls once. crew_denied must stop automatically before an approval card or MCP dispatch. An operator rejection cannot count as that proof. Sources: infrastructure/configure-demo.py; infrastructure/mcp-enforcement/server.py; evidence/aws/iam-demo-policy.json; evidence/aws/fixture-hashes.json; evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json.

## 7. Direct MCP and AWS results

### On slide



Allowed object

55

bytes read from S3

SHA256 34ebbefeb5f66527…

AWS request FC4GTZS0B83EQ5W1

MCP refused the tool

mcp_denied returned tool_grant_denied before AWS dispatch.

AWS refused the object

iam_denied returned AccessDenied, HTTP 403.

AWS request BA5BT7K9765938BT

Direct service probe passed. native_crew_backend_verified=false

Unauthenticated request: 401. Discovery: four tools.

Separate direct probe recorded September 13, 2026 at 15:01:37 UTC.

### Speaker notes

The direct_mcp_service_probe passed on the ARM host at 2026-09-13T15:01:37Z and records native_crew_backend_verified=false. An unauthenticated request returned 401, and discovery returned four tools. read_allowed returned 55 bytes and the expected SHA256, with AWS request ID FC4GTZS0B83EQ5W1. mcp_denied returned tool_grant_denied at the MCP boundary. iam_denied returned S3 AccessDenied, HTTP 403, and request ID BA5BT7K9765938BT. This separate probe ran after telemetry activation. It exercises MCP and AWS directly; it does not establish a native Crew session, the configured Crew hook denial or a single end-to-end run through the desktop. Sources: evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json; infrastructure/mcp-enforcement/server.py.

## 8. Client and server nightly baselines

### On slide



Mac client

September 13

0.7.0-nightly.20260913t061222

48 selected RECORD checks passed across arm64 and x64 bundles.

EC2 server

September 12

0.7.0-nightly.20260912t060850

Unofficial Linux ARM64 repack. 24 selected control modules match the frozen build.

Kiro CLI 2.21.4 is selected. Sign-in remains pending. The latest recorded CLI check at 15:19 UTC was unauthenticated. The KAS GitHub card uses a separate identity store.

Different builds. Behavioral equivalence and a native model session remain unverified.

### Speaker notes

The installed Mac client is 0.7.0-nightly.20260913t061222. Its 24 selected paths passed RECORD hash and size checks in the arm64 and x64 bundles, 48 checks in total. Three selected paths differ from the September 12 baseline; that comparison does not establish behavioral equivalence. The EC2 server remains the custom Linux ARM64 repack of 0.7.0-nightly.20260912t060850, with 48 locked dependencies. Its 24 selected control modules match the frozen installed nightly source and are root-owned without group or world write access. The server was not upgraded when the Mac app changed. Kiro CLI 2.21.4 is installed separately from the official ARM artifact. It is the selected agent backend, but whoami reports unauthenticated and ACP startup exits with 'not logged in'. Full native-session performance remains unverified. Local-model downloads remain off. Sources: evidence/nightly/client-20260913-verification.json; evidence/aws/arm-20260913/runtime-preparation.json; evidence/aws/arm-20260913/source-verification.json; evidence/aws/arm-20260913/install-services.log; infrastructure/kirocrew-demo.service; output/admin-console/07-agent-backend.jpg; output/admin-console/10-native-auth-log.jpg; evidence/aws/arm-20260913/client-runtime-receipt.json; evidence/aws/arm-20260913/observability-runtime-receipt.json.

Latest authentication receipt: evidence/aws/arm-20260913/native-cli-login-outcome.json, September 13 at 15:19 UTC. The normal CLI login ended without an authenticated account. This presentation contains recorded state and does not poll the running system.

## 9. Native telemetry measures the Gateway

### On slide



Request, boot and process metrics

10 s Local export interval

7 days Retention

64 MiB retention target. No OTLP endpoint. Anonymous usage reporting off.

Native model-session metrics pending. Zero-valued turn metrics have no completed model session behind them.

Developer / Telemetry / Latency. Expand to inspect the original capture.

Recorded September 13. The UI shows a 14-day window. One boot observation cannot establish a latency distribution.

### Speaker notes

In the admin portal, open Developer → Telemetry and select Latency. The screenshot shows Gateway request and boot duration instruments, process CPU and garbage-collection counters. The API readback at 14:50:25 UTC confirms collection enabled, no environment pin, two local metric shards and no OTLP endpoint. Native local export is configured for ten-second intervals, seven-day retention and a 64 MiB target. Active writers can temporarily keep the directory above that target. Anonymous usage reporting is disabled. Model turn statistics remain empty because native Kiro CLI authentication has not succeeded; a displayed zero turn latency is not a measured zero-latency model session. The metrics directory is /var/lib/kirocrew/metrics. The “Last 14d” label identifies the display window. Retention remains seven days. The boot histogram has only one observation. Its displayed percentiles reflect the UI aggregation and are not a measured boot-time distribution. This pane reports native Gateway instrumentation. The custom Mac and EC2 samples appear in Demo Observability. Sources: evidence/aws/arm-20260913/observability-api-readback.json; infrastructure/set-demo-telemetry.py; output/admin-console/08-telemetry-controls.jpg; output/admin-console/09-native-telemetry.jpg; evidence/aws/arm-20260913/observability-runtime-receipt.json; .build/installed-nightly/kiro_crew/metrics/local_exporter.py.

## 10. Client and server in the admin portal

### On slide

Custom App Kit via the admin portal's owner-token proxy; separate from CLI sign-in. Expand the capture to inspect.

60 s Collection interval

15 s Page refresh

180 s Stale threshold

240 Samples per source

Captured September 13. Clocks: EDT (UTC−4). Client CPU measures a process family; server CPU measures the host.

### Speaker notes

Open Apps → Demo Observability. The App Kit page reads the custom collectors through the authenticated Gateway proxy; its snapshot returned HTTP 200. The screenshot shows the Mac sample at 14:43:14 UTC: four percent aggregate process CPU and 772.4 MiB RSS. Its EC2 sample at 14:43:35 UTC shows 6.2 percent host CPU and about 14.6 GiB available memory. The later API readback at 14:50:25 UTC shows both sources current. Its values differ as the processes continue running. These snapshots do not measure full-session performance. The client CPU sum uses process scheduler averages and can exceed 100 percent. Server host CPU uses a one-second host-wide sample. Treat client and server CPU as different measurements. Screenshot clocks are Eastern daylight time, UTC minus four hours. The Mac checks confirm the desktop is running, the local SSH tunnel listener accepts a connection and the local Gateway is off. A reachable local tunnel listener alone does not prove a remote Gateway response. EC2 checks separately confirm Gateway and MCP services active and both loopback ports reachable. Both collectors run every 60 seconds. The UI refreshes every 15 seconds, marks samples stale after 180 seconds, and displays missing values as unknown. Each source retains at most 240 samples, about four hours with uninterrupted collection. Collection events are capped at 200. The custom app is version 1.0.1; its loopback backend runs on port 9102 behind the Gateway proxy. Sources: evidence/aws/arm-20260913/observability-api-readback.json; evidence/aws/arm-20260913/observability-update.json; infrastructure/observability/app/app.json; infrastructure/observability/app/backend/server.py; infrastructure/observability-collector/collector.py; output/admin-console/11-client-server-telemetry.jpg; evidence/aws/arm-20260913/observability-runtime-receipt.json.

## 11. Closing the client did not stop the Gateway

### On slide



14:44:42 UTC / Stopped-client sample

14:49:34 UTC / Recovery sample in collection logs

Per receipt: Gateway PID 4991, started 14:26:10 UTC, unchanged. Gateway and MCP stayed active. Active model-session continuity remains unverified.

Crew-run collection events are operational telemetry, not SEL audit records. Expand either capture to inspect.

September 13 sample times, not click times. Screenshot clocks: EDT (UTC−4). Current means freshness; health is a separate check.

### Speaker notes

In the controlled check, quit the Mac desktop and keep the browser admin portal open through the existing SSH tunnel. The client collector sampled the stopped desktop and the collection log added a warning at 14:44:42 UTC. These timestamps identify samples, not the exact quit or relaunch clicks. The stopped-client screenshot shows zero client processes while Gateway and MCP service checks stay active. Relaunch the desktop. The client log recorded an informational recovery sample at 14:49:34 UTC. The server Gateway remained PID 4991, started at 14:26:10 UTC, across the client quit and relaunch. Closing the client did not stop the Gateway. Continuity of an active model session remains unverified while Kiro CLI authentication is pending. The displayed log timestamps are local Eastern time, four hours behind UTC. The page exposes fixed collection events, not raw application logs, prompts or chat contents. Use the Client and Server filters to inspect each source. Sources: output/admin-console/12-collection-logs.jpg; output/admin-console/13-client-stopped.jpg; infrastructure/observability-collector/collector.py; evidence/aws/arm-20260913/observability-runtime-receipt.json; evidence/aws/arm-20260913/client-runtime-receipt.json.

## 12. Running cost and operational trade-offs

### On slide



730 running hours

$107

per month, always on

Compute, public IPv4 and both disks. Model use, S3, transfer and tax add charges.

Estimate from September 13 price evidence.

01 One host

Fewer components, one failure domain.

02 Standard CPU credits

No surplus charges. Sustained work can throttle after credits run out.

03 Retained rollback host

Stopped t3a.small: 24 GiB disk retained, $1.92/month. Stop ARM when idle.

$0.1394 per running hour. ARM storage $3.20/month plus stopped x86 storage $1.92/month. EBS remains billable.

### Speaker notes

The AWS Pricing API lists On Demand Linux t4g.xlarge at $0.1344 per hour in us-east-1. Public IPv4 adds $0.005 per hour, for $0.1394 per running hour, rounded to $0.139. At $0.08 per GB-month, the active 40 GiB gp3 disk costs $3.20 per month. The stopped x86 rollback host retains a 24 GiB gp3 disk at $1.92 per month. Together the disks cost $5.12 per month while rollback is retained. At 730 running hours, compute, IPv4 and both disks total $106.882, or about $107 per month. S3, transfer, model usage and taxes add charges. The instances use standard CPU credits, with no surplus-credit charges. Sustained load can throttle to baseline after credits are depleted. There is no NAT gateway or load balancer. Stop the active ARM instance after the demo with scripts/demo-cloud.py; inspect its dry-run plan first. Stopping releases the ephemeral IPv4 address and stops compute billing; EBS remains billable. Refresh the SSH address after restart. Keep the stopped x86 rollback host until it is no longer needed. Sources: evidence/aws/arm-20260913/price.json; evidence/aws/gp3-pricing.json; https://aws.amazon.com/vpc/pricing/ ; evidence/aws/arm-20260913/final-cloud-verification.json; scripts/demo-cloud.py.

One execution host reduces the number of services to operate. Its failure can interrupt execution, local state and telemetry together. This edition has no tested failover or recovery-time commitment. The chosen 4 vCPU / 16 GiB host does not establish sustained session capacity.

## 13. Decisions to revisit as usage grows

### On slide



Trigger / Current choice / Next decision /

Shared users / Fixed demo grants

Crew-writable configuration / Identity-bound MCP grants and protected policy distribution /

Uptime commitments / One host, local state / Backups, recovery targets and tested reconnect or failover /

Sustained workloads / Burstable ARM host

Different nightly builds / Native-session measurements, CPU-credit behavior and version compatibility /

Audit retention / Local operational samples

200 fixed collection events / Protected external security-event storage, separate from telemetry /

First priority: complete native authentication and verify the four-turn enforcement sequence.

Proposed next decisions. No multi-user capacity, failover or external audit-retention claim.

### Speaker notes

These are proposed design decisions, not deployed capabilities. The present system serves one operator with a fixed MCP catalog, a bounded instance role, local operational telemetry and a single ARM execution host.

For multiple users, review how user identity reaches MCP grants and prevent an execution identity from changing the enforcing policy. For uptime commitments, specify recovery point and recovery time before choosing replication or failover. For sustained workloads, collect real authenticated session measurements before resizing or adding hosts. For audit retention, design protected external security-event collection independently of numeric operational telemetry.

Do not infer central policy, SSM transport, EDR, multi-user isolation, external SEL storage or failover from the current demo. Sources: HANDOFF.md; infrastructure/RUNBOOK.md; output/kirocrew-admin-findings.md.

## 14. Desktop-to-EC2 walkthrough

### On slide



01 / CONNECTION Confirm the remote workspace

Show the desktop connected through :5599. Confirm the Mac's local Gateway is off.

02 / OBSERVABILITY Inspect both machines

Open native Gateway telemetry, then client/server samples and collection events.

03 / DIRECT PROBE Run the three-call MCP probe

Inspect the object digest, MCP refusal and S3 403 with fresh request IDs.

04 / PENDING NATIVE ACCEPTANCE Sign in before native turns

If sign-in fails, stop here and report it. After sign-in, run four turns; crew_denied must stop before MCP dispatch.

Open admin portal Exact commands and evidence checks are in this slide's notes.

Stop the ARM host after the demo when idle. Retained disks remain billable.

### Speaker notes

Show the native desktop connected on port 5599 and the remote workspace at /srv/kirocrew-demo/workspace. Confirm that local port 5476 has no listener. Run the direct MCP command from WALKTHROUGH.md as mcp-demo on EC2. The bearer token stays on the instance. Show the 55-byte digest, tool_grant_denied and S3 AccessDenied 403 with a new AWS request ID. The receipt must report direct_mcp_service_probe, passed=true and native_crew_backend_verified=false. This direct path is available while Kiro CLI authentication remains pending. After successful authentication through scripts/ec2-login.py, use native-demo.sh to test four native turns in a dedicated session. Inspect the real request card and approve read_allowed, mcp_denied and iam_denied once each. crew_denied must stop automatically before any approval card or MCP arrival. An approval card on that turn fails the test, even if the runner rejects it. The runner correlates callback IDs and MCP/AWS traces. The Crew-denial SEL record lacks a direct trace ID, so the correlation uses the dedicated session and isolated turn interval. Sources: WALKTHROUGH.md; scripts/native-backend-demo.README.md; scripts/EC2-LOGIN.md; evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json; evidence/aws/arm-20260913/client-runtime-receipt.json.

Commands (run in the project terminal, not from the presentation):
python3 scripts/ec2-login.py
./native-demo.sh plan

For the currently verified direct path, use the fixed three-tool probe in WALKTHROUGH.md. The exact command is included below in this slide's notes. Authentication and approvals require their normal user flow. Opening this presentation executes no commands, stops no services and performs no live polling.

ssh -T kirocrew-demo-admin 'sudo -u mcp-demo env DEMO_MCP_TOKEN_FILE=/etc/kirocrew-demo/mcp-token /opt/kirocrew-demo/mcp-venv/bin/python /opt/kirocrew-demo/mcp-enforcement/probe.py --expected-allowed-sha256 34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160'

## What changed

Reorganized the accepted deck around requirements, architecture, authorization, observability and operational decisions. Added explicit assumptions and growth triggers. Kept the original evidence images, exact tool names, recorded times and native-authentication limits.
