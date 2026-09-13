# Exact PPTX slide text and speaker notes

## Slide 1

### Slide text

KiroCrew on EC2

A desktop client with

remote coding-agent execution

CloudFormation deployment in us-east-1

Crew controls, an MCP service and AWS IAM

### Speaker notes

00:00–00:20. This demo extends the accepted control map into a deployed EC2 environment. The native desktop client connects through local port 5599 to the EC2 Gateway, and the local Gateway listener is off. The EC2 host holds the workspace. The installed Kiro CLI backend still needs successful authentication and a verified native session at this stage. Direct MCP calls on EC2 already demonstrate an allowed S3 read, an MCP grant denial and an AWS IAM denial. Sources: evidence/aws/stack-state.json; evidence/aws/mcp-live-receipt.json; evidence/aws/client-runtime-verification.json. Runtime status must be updated from fresh receipts before presenting the native walkthrough as completed.

## Slide 2

### Slide text

One execution host

The execution host

Local mode

Developer endpoint

Remote mode

Gateway, backend and workspace

on the EC2 instance

Control map. The following slides show

the deployed subset and its evidence.

### Speaker notes

00:20–00:55. The accepted enclosure is the control map. In remote mode, the Gateway, selected backend and workspace occupy the same execution host. Enterprise host protection remains a separate responsibility from Crew. The EC2 demo implements the subset shown on later slides. Do not infer EDR enrollment, universal sandbox coverage, central policy distribution or external log retention from this reference image. The diagram retains the September 11 pinned-source baseline. Source image: evidence/browser/endpoint-slide.png, unchanged accepted endpoint SVG screenshot. Sources: HANDOFF.md; kirocrew-security-layers.html; evidence/nightly/baseline-verification.json.

## Slide 3

### Slide text

CloudFormation deployment in us-east-1

One t3a.small. SSH from the client IP /32. Gateway and MCP listen on loopback.

### Speaker notes

00:55–01:35. Open the live EC2 architecture artifact for readable node details. CloudFormation created one t3a.small in the existing public subnet, with a public IPv4 address to avoid NAT gateway or load balancer costs. Its security group has one inbound rule: TCP 22 from the current client IPv4 /32. Gateway port 5476 and MCP port 8001 bind to EC2 loopback. The laptop forwards local port 5599 over SSH to remote port 5476. The template includes the instance role, private S3 bucket, encrypted 24 GiB gp3 root volume and IMDSv2 requirement. CloudFormation CREATE_COMPLETE alone does not prove bootstrap, so the host bootstrap marker and service checks are separate evidence. The earlier private EC2 + SSM architecture remains a separate reference. Provisioning used the primary AWS MCP endpoint in us-east-1. That AWS control-plane connector is separate from the demonstration MCP service on EC2. The slide image crops only the canonical diagram exterior and generic color legend, preserving all topology nodes, labels and boundaries. Sources: evidence/aws/archify/presentation-crop.json; evidence/aws/primary-mcp-tools.json; infrastructure/ec2-demo.json; evidence/aws/stack-state.json; evidence/aws/security-group.json; evidence/aws/route-preflight.json; evidence/aws/ssh-verification.json; evidence/aws/ec2-console-bootstrap.json.

## Slide 4

### Slide text

Host identities and AWS credentials

Identity

Execution and authority

crew

Gateway, Kiro CLI and workspace

Firewall blocks instance metadata

mcp-demo

Fixed MCP tools and S3 reads

Instance role through IMDSv2

root / administrator

Installs code and manages services

Trusted host administration

The MCP process holds AWS authority. Crew calls its fixed tools.

### Speaker notes

01:35–02:10. Crew and the MCP service run as separate unprivileged Unix users. Root owns the executable and service files. An owner-based firewall rule rejects metadata requests from the crew UID, and the Gateway requires that guard service. The MCP process obtains the instance role through IMDSv2 and accepts only the four fixed demonstration calls. Its role allows reads under two demonstration prefixes, with an explicit GetObject deny on the denied prefix. The role also includes the SSM core policy. This is a host UID boundary for a small demo. It is not an assertion of isolation against root or arbitrary privilege escalation. No IAM user keys were copied to EC2. Crew configuration is service-user-owned, so it must not be described as an immutable centrally managed policy floor. Sources: infrastructure/bootstrap.sh; infrastructure/kirocrew-demo.service; infrastructure/kirocrew-mcp-demo.service; infrastructure/mcp-enforcement/server.py; infrastructure/ec2-demo.json.

## Slide 5

### Slide text

Four calls, three denial boundaries

Tool

Expected result

Stopping point

read_allowed

Digest of allowed object

S3 completes the read

crew_denied

Configured tool denial

Crew, before MCP dispatch

mcp_denied

tool_grant_denied

MCP, before AWS dispatch

iam_denied

S3 AccessDenied (403)

AWS IAM

Crew denial requires the native backend to reach its pre-execution gate.

### Speaker notes

02:10–02:45. This is the live sequence and its expected stopping points. Use a fresh trace_id for every call. The read_allowed tool returns only the object length and digest. crew_denied is allowed by the MCP service so a Crew hook can demonstrate blocking it before dispatch. Its configured deny is @aws-enforcement/crew_denied. mcp_denied remains in the discovery catalog but the service rejects it at call time before loading AWS credentials or calling the SDK. iam_denied passes the MCP grant and attempts GetObject on an existing object under denied/, where IAM applies an explicit deny. Approve individual calls only after checking the actual request. A user rejection must not be counted as an automatic Crew deny. Sources: infrastructure/configure-demo.py; infrastructure/mcp-enforcement/server.py; evidence/aws/iam-demo-policy.json; evidence/aws/fixture-hashes.json. Native Crew evidence remains pending at this stage.

## Slide 6

### Slide text

Observed MCP and AWS results

Direct probe on EC2

Call

Receipt output

read_allowed

55 bytes

SHA256 34ebbefeb5f66527…

mcp_denied

tool_grant_denied

No AWS dispatch for that trace

iam_denied

S3 AccessDenied, HTTP 403

AWS request ID recorded

The native Crew session remains a separate verification step.

### Speaker notes

02:45–03:20. These are actual direct calls against the deployed MCP service on EC2, not native Crew backend observations. The receipt is direct_mcp_service_probe, passed true, timestamp 2026-09-13T04:17:07Z. The unauthenticated request returned 401 and the catalog contained all four tools. read_allowed returned 55 bytes and the full SHA256 recorded in the fixture receipt. mcp_denied returned tool_grant_denied without an AWS dispatch audit record for that trace. iam_denied returned S3 AccessDenied with HTTP 403 and AWS request ID NJ428FX3JS4EV6VK. The object existence check ran first, avoiding confusion with a missing object. The service tests also cover failure attribution so an STS error cannot be reported as S3 IAM proof. Sources: evidence/aws/mcp-live-receipt.json; evidence/aws/mcp-live-audit.jsonl; evidence/aws/seed-fixtures-result.json; infrastructure/mcp-enforcement/TEST-RECEIPT.json.

## Slide 7

### Slide text

Installed nightly and client baseline

Crew package

0.7.0-nightly.20260912t060850

Custom Linux repack of the installed package

Kiro CLI backend

2.21.4 official Linux artifact

Hash-locked Linux dependencies for Crew

Desktop runtime verified with the local Gateway off.

### Speaker notes

03:20–03:50. The installed Mac app and copied package identify 0.7.0-nightly.20260912t060850. The Linux deployment is a custom repack of that frozen package with Linux dependencies and native libraries. It is not an official Linux nightly distribution, and no source commit is assigned to it. The repack archive SHA256 is 5133df99766a436a0fe346c6c57b4475fa00389a62fe7e464ec8440942e33d39. Linux dependency artifacts are hash locked. Kiro CLI 2.21.4 comes from the official stable Linux archive and matches its manifest. The Electron configuration records runLocalGateway=false, the SSH host alias and local port 5599. Native desktop inspection confirms Gateway connected, enforcement-demo selected and /srv/kirocrew-demo/workspace open. The local port 5476 has no listener, and SSH owns port 5599. The UI reports critically low memory with about 1.2 GB free on the 2 GiB instance. Native backend authentication and full-session performance remain pending. Sources: evidence/nightly/installed-nightly-verification.json; evidence/aws/linux-repack.json; infrastructure/crew-requirements-linux.lock; evidence/aws/kiro-cli-artifact.json; evidence/aws/client-runtime-verification.json.

## Slide 8

### Slide text

Desktop-to-EC2 walkthrough

1   Confirm the desktop uses the EC2 Gateway

2   Open the remote workspace and Kiro CLI session

3   Run the four fixed tools, approving individual calls

4   Compare Crew, MCP and AWS records by trace ID

Native Kiro CLI sign-in and backend session verification pending.

### Speaker notes

03:50–05:50. Before the audience walkthrough, confirm the EC2 instance, services, SSH tunnel and desktop connection with the current runbook. Show that the laptop has no local Gateway listener and that the desktop is connected through port 5599. Show the remote workspace at /srv/kirocrew-demo/workspace and a Kiro CLI process running as crew on EC2. Request each of the four fixed tools once, with a new trace ID and no retries after a denial. For allowed calls, inspect the permission card and approve once. For crew_denied, the configured hook must deny automatically before any MCP dispatch. Correlate the Crew transcript/SEL, MCP audit and AWS request ID. The direct probe is available if native authentication remains blocked, but it cannot substitute for that session. Native Kiro CLI sign-in and backend session verification pending. Sources: scripts/native-backend-demo.py when available; WALKTHROUGH.md; evidence/aws/mcp-live-receipt.json.

## Slide 9

### Slide text

Demo cost and return to baseline

$0.024 per running hour

Compute + IPv4. Storage adds $1.92 per month.

About $19 per month if always on, before other usage.

After the demo

Stop the instance. EBS remains.

Refresh its address after restart.

Stack deletion retains the S3 demo data.

2 GiB host. The UI warns about low memory. Full-session performance is pending.

### Speaker notes

05:50–06:20. AWS Pricing API returned $0.0188 per On Demand Linux t3a.small hour in us-east-1. AWS lists public IPv4 at $0.005 per hour, giving $0.0238 per running hour, rounded to $0.024 on the slide. AWS Pricing API returns $0.08 per GB-month for gp3 in us-east-1, or $1.92 per month for 24 GiB. At 730 running hours the compute, IPv4 and EBS base is $19.294, rounded to about $19 per month. These figures exclude S3, transfer, model usage and taxes. The instance uses standard credits and has no NAT gateway or load balancer. Stop the instance after the demo to stop compute billing and release the ephemeral public IPv4. EBS remains and continues to incur charges. A stop/start changes the public IPv4, so refresh the SSH target. Use CloudFormation to update the permitted client /32 if its address changes. Stack deletion removes the instance and root EBS but retains the private S3 bucket and bucket policy. Inspect and clean up retained data when retiring the demo. The 2 GiB instance triggers the UI low-memory warning, and full backend performance remains unverified. Preserve and use the saved desktop configuration backup to return to local mode. Sources: evidence/aws/t3a-small-pricing.json; evidence/aws/gp3-pricing.json; https://aws.amazon.com/vpc/pricing/ ; infrastructure/ec2-demo.json; evidence/aws/client-runtime-verification.json.
