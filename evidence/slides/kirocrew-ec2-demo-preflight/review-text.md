# Exact PPTX slide text and speaker notes

## Slide 1

### Slide text

KiroCrew on EC2

Desktop client and

EC2 execution environment

CloudFormation in us-east-1

Direct MCP and AWS checks passed.

Native Kiro CLI sign-in and session pending.

### Speaker notes

00:00–00:20. The Mac is the desktop client. The EC2 host runs the Gateway and holds the workspace. The local Gateway listener is off. Direct MCP and AWS checks passed, including an allowed S3 read, an MCP grant denial and an S3 IAM denial. Native Kiro CLI authentication and a verified backend session remain pending. Sources: evidence/aws/stack-state.json; evidence/aws/client-runtime-verification.json; evidence/aws/mcp-live-receipt.json; evidence/aws/walkthrough-direct-probe.json.

## Slide 2

### Slide text

One execution host

Local mode

Developer endpoint

Remote mode

Gateway, backend and workspace

on the EC2 instance

Reference map.

Verified here: remote client,

MCP grants and S3 IAM checks.

### Speaker notes

00:20–00:55. The enclosure maps controls around the execution host. In remote mode, the Gateway, selected backend and workspace run on the same host. The reference includes enterprise controls and Crew capabilities beyond this demo. The checks verify the remote desktop connection, direct MCP grants and S3 IAM outcomes. Native backend enforcement and sandbox behavior remain pending. The reference cites the September 11 baseline. Sources: kirocrew-security-layers.html; evidence/nightly/baseline-verification.json; evidence/aws/client-runtime-verification.json; evidence/aws/mcp-live-receipt.json.

## Slide 3

### Slide text

CloudFormation deployment in us-east-1

One t3a.small. SSH from the client IP /32. Gateway and MCP listen on loopback.

### Speaker notes

00:55–01:35. CloudFormation created one t3a.small in an existing public subnet in us-east-1. The security group admits TCP 22 only from the current client IPv4 /32. SSH forwards laptop port 5599 to EC2 loopback port 5476. The Gateway, Kiro CLI installation and workspace share the Crew execution boundary. The MCP service runs on the same EC2 instance under a separate UID and listens on loopback port 8001. It uses the instance role for the fixed S3 requests. The role permits the allowed prefix and explicitly denies GetObject under the denied prefix. Native Kiro CLI sign-in remains pending. The host has encrypted 24 GiB gp3 storage and requires IMDSv2. Separate host checks confirmed bootstrap and active services after CloudFormation created the stack. Primary AWS MCP in us-east-1 handled provisioning. The demo MCP service on EC2 is separate from that provisioning connector. The detailed browser view contains ports and the remaining host configuration. Sources: infrastructure/ec2-demo.json; evidence/aws/stack-state.json; evidence/aws/security-group.json; evidence/aws/ssh-verification.json; evidence/aws/ec2-console-bootstrap.json; evidence/aws/primary-mcp-tools.json.

## Slide 4

### Slide text

Host identities and AWS credentials

Identity

Execution and authority

crew

Gateway, Kiro CLI and workspace

Firewall blocks metadata for the crew UID

mcp-demo

Fixed MCP tools and S3 reads

Instance role through IMDSv2

Two S3 prefixes + SSM core permissions

root / administrator

Installs code and manages services

Trusted host administration

The MCP service uses the instance role for fixed S3 calls.

### Speaker notes

01:35–02:10. Root owns the executable and service files. The crew user runs the Gateway, backend and workspace. An owner-based firewall rule blocks metadata requests from the crew UID, and the Gateway requires that guard service. The mcp-demo UID can obtain the instance role through IMDSv2. That role permits reads under two demonstration S3 prefixes, explicitly denies GetObject under denied/, and includes the SSM core managed policy. The MCP service exposes four fixed tools. Root remains a trusted administrator. The operator’s IAM user keys remain local. Crew owns and can edit its configuration. Sources: infrastructure/bootstrap.sh; infrastructure/kirocrew-demo.service; infrastructure/kirocrew-mcp-demo.service; infrastructure/mcp-enforcement/server.py; infrastructure/ec2-demo.json.

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

The direct probe covers three tools. Native Crew denial remains pending.

### Speaker notes

02:10–02:45. The direct probe verified read_allowed, mcp_denied and iam_denied. Native Crew denial is pending. read_allowed returns the object length and digest. The MCP service grants crew_denied so the Crew hook can block it before dispatch. Its configured rule names @aws-enforcement/crew_denied. mcp_denied appears in discovery, but the service rejects the call before loading AWS credentials or invoking the SDK. iam_denied passes the MCP grant and attempts GetObject on an existing object under denied/, where IAM applies the explicit deny. After native sign-in, inspect each request and approve the three routed calls once. crew_denied must stop automatically before an approval card or MCP dispatch. An operator rejection cannot count as that proof. Sources: infrastructure/configure-demo.py; infrastructure/mcp-enforcement/server.py; evidence/aws/iam-demo-policy.json; evidence/aws/fixture-hashes.json; evidence/aws/walkthrough-direct-probe.json.

## Slide 6

### Slide text

Observed MCP and AWS results

Direct probe on EC2

direct_mcp_service_probe, 2026-09-13 04:17:07 UTC

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

Request ID NJ428FX3JS4EV6VK

Unauthenticated request: 401. Discovery returned four tools.

Native Crew session pending.

### Speaker notes

02:45–03:20. The probe called the MCP service directly. The direct_mcp_service_probe receipt passed at 2026-09-13T04:17:07Z and explicitly records native_crew_backend_verified=false. The unauthenticated request returned 401, and discovery returned four tools. read_allowed returned 55 bytes and the expected SHA256, with AWS request ID NJ47PCKDNPWNT29P. mcp_denied returned tool_grant_denied without an AWS dispatch for its trace. iam_denied returned S3 AccessDenied, HTTP 403, and request ID NJ428FX3JS4EV6VK. An independent check confirmed that the denied object existed. An STS failure does not satisfy the S3-denial check. The exact command in WALKTHROUGH.md passed again at 2026-09-13T04:48:49Z, with fresh AWS request IDs C25PB34E90H62Y2N for the allowed read and 4FM4E0EGXJ783W7H for the IAM denial. The second run has a separate receipt. Sources: evidence/aws/mcp-live-receipt.json; evidence/aws/mcp-live-audit.jsonl; evidence/aws/walkthrough-direct-probe.json; evidence/aws/seed-fixtures-result.json; infrastructure/mcp-enforcement/TEST-RECEIPT.json.

## Slide 7

### Slide text

Installed nightly and client baseline

Crew package

0.7.0-nightly.20260912t060850

Custom Linux repack of the installed package

Hash-locked Linux dependencies

Kiro CLI artifact

2.21.4 official Linux artifact

Archive hash matches the official manifest

Desktop uses EC2. Local Gateway is off.

Native backend authentication and session pending.

### Speaker notes

03:20–03:50. The installed Mac app and package identify 0.7.0-nightly.20260912t060850. EC2 runs a custom Linux repack with Linux dependencies and native libraries. Installed metadata provides no source commit. The archive SHA256 is 5133df99766a436a0fe346c6c57b4475fa00389a62fe7e464ec8440942e33d39. The Linux dependency lock pins versions and accepted artifact hashes. On EC2, 24 selected modules for Crew controls match the installed nightly RECORD. Those files are root-owned and neither group- nor world-writable. Kiro CLI 2.21.4 comes from the official stable Linux artifact and matches its manifest. Backend authentication and a native session remain pending. The desktop shows Gateway connected, enforcement-demo and /srv/kirocrew-demo/workspace. Local port 5476 has no listener, and SSH owns port 5599. The UI warns about low memory with about 1.2 GB free on the 2 GiB instance. Performance during a full backend session remains unverified. Sources: evidence/nightly/installed-nightly-verification.json; evidence/aws/linux-repack.json; infrastructure/crew-requirements-linux.lock; evidence/aws/deployed-nightly-verification.json; evidence/aws/kiro-cli-artifact.json; evidence/aws/client-runtime-verification.json.

## Slide 8

### Slide text

Desktop-to-EC2 walkthrough

1   Confirm the remote client and workspace

2   Run the three-call MCP probe in WALKTHROUGH.md

3   Check the digest, MCP refusal and S3 403

Native sequence pending sign-in

Approve the three routed calls once.

crew_denied must stop automatically before MCP dispatch.

### Speaker notes

03:50–05:50. Show the native desktop connected on port 5599 and the remote workspace at /srv/kirocrew-demo/workspace. Confirm that local port 5476 has no listener. Run the direct MCP command from WALKTHROUGH.md as mcp-demo on EC2. The bearer token stays on the instance. Show the 55-byte digest, tool_grant_denied and S3 AccessDenied 403 with a new AWS request ID. The receipt must report direct_mcp_service_probe, passed=true and native_crew_backend_verified=false. This direct path is available while Kiro CLI authentication remains pending. After successful authentication through scripts/ec2-login.py, use native-demo.sh to test four native turns in a dedicated session. Inspect the real request card and approve read_allowed, mcp_denied and iam_denied once each. crew_denied must stop automatically before any approval card or MCP arrival. An approval card on that turn fails the test, even if the runner rejects it. The runner correlates callback IDs and MCP/AWS traces. The Crew-denial SEL record lacks a direct trace ID, so the correlation uses the dedicated session and isolated turn interval. Sources: WALKTHROUGH.md; scripts/native-backend-demo.README.md; scripts/EC2-LOGIN.md; evidence/aws/walkthrough-direct-probe.json.

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

The 2 GiB host has a low-memory warning. Full backend performance is unverified.

### Speaker notes

05:50–06:20. AWS Pricing API returned $0.0188 per On Demand Linux t3a.small hour in us-east-1. AWS lists public IPv4 at $0.005 per hour. Together they cost $0.0238 per running hour, rounded to $0.024. The gp3 rate is $0.08 per GB-month, so 24 GiB costs $1.92 per month. At 730 running hours, compute, IPv4 and EBS total $19.294, or about $19 per month. S3, transfer, model usage and taxes add charges. The instance uses standard credits and has no NAT gateway or load balancer. After finishing active work, use scripts/demo-cloud.py stop --dry-run, inspect the plan, then stop --apply. Stopping releases the ephemeral public IPv4 and stops compute billing. The EBS volume remains billable. Refresh the SSH target after restart. Use the helper to update CloudFormation if the allowed client /32 changes. Stack deletion removes the instance and root EBS but retains the S3 bucket and its policy. The UI warns about low memory on the 2 GiB host. Full backend performance remains unverified. The separate client rollback procedure restores local mode. Sources: evidence/aws/t3a-small-pricing.json; evidence/aws/gp3-pricing.json; https://aws.amazon.com/vpc/pricing/ ; infrastructure/ec2-demo.json; infrastructure/RUNBOOK.md.
