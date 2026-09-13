# KiroCrew EC2 deployment and evidence

The active deployment is now ARM. Fresh read-only AWS checks at 14:22 UTC on September 13, 2026 confirm `UPDATE_COMPLETE`, a running `t4g.xlarge` and the original x86 host stopped. The Mac remains the client with its local Gateway off. The single endpoint-control enclosure still represents the remote execution host. [Current ARM cloud verification](evidence/aws/arm-20260913/final-cloud-verification.json)

| Current resource | Verified state |
| --- | --- |
| Stack / region | `kirocrew-demo-20260913` / `us-east-1`, `UPDATE_COMPLETE` |
| Active ARM host | `i-0fde6de3f0ea5a9d0`, running `t4g.xlarge`, 4 vCPU / 16 GiB RAM |
| ARM storage / OS | 40 GiB encrypted gp3, Ubuntu 24.04 ARM64, standard CPU credits |
| ARM public IPv4 at verification | `100.61.173.192`; can change after stop/start |
| Rollback host | `i-020eb373045b56586`, stopped `t3a.small`, 24 GiB encrypted gp3, no public IPv4 |
| Shared security group | `sg-08ac4789794115e39`; only TCP 22 from `24.60.107.229/32` inbound |

The Mac desktop and authenticated owner dashboard are connected to ARM through port 5599. Local Gateway is off and port 5476 has no local listener. The tunnel retains the unprivileged `kirocrew-demo` SSH alias and pinned ARM identity. Desktop owner refresh uses `kirocrew-demo-admin` with `/usr/local/bin/kirocrew-owner-token`. That reviewed helper enters the verified Gateway mount namespace, then drops to Crew for the stock token operation. It adds no Crew sudo permission and patches no Nightly code. Normal desktop relaunch and owner reconnection passed. [Client runtime](evidence/aws/arm-20260913/client-runtime-receipt.json), [owner helper review](evidence/aws/arm-20260913/owner-bootstrap-review.json)

The ARM direct MCP probe passed at 14:07 UTC: unauthenticated HTTP 401, the four-tool catalog, allowed S3 fixture digest, MCP grant denial before AWS dispatch and S3 IAM `AccessDenied` HTTP 403 with an AWS request ID. A separate TCP-only probe from the Crew UID to IPv4 IMDS was denied immediately, without an HTTP request or credential read. These results do not establish native backend sandbox execution. The configured Crew denial remains a writable demo rule. [ARM direct probe](evidence/aws/arm-20260913/mcp-live-receipt.json), [Crew metadata connection test](evidence/aws/arm-20260913/crew-imds-connect-receipt.json)

The exact documented MCP command passed again at 15:01:37 UTC, after telemetry deployment, with fresh trace and AWS request IDs. Its receipt still excludes native Crew backend verification. [Latest command rehearsal](evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json)

The Mac client is `0.7.0-nightly.20260913t061222`. All 24 selected modules match the package RECORD; three changed from the frozen September 12 baseline: governance, sandbox and security posture. No behavioral-equivalence claim follows from that byte comparison. ARM retains `0.7.0-nightly.20260912t060850` with hash-locked ARM64 dependencies and native libraries. All 24 selected server modules match that frozen baseline and are root-owned. It remains a custom Linux repack without a verified official Linux nightly artifact or source commit. [September 13 client baseline](evidence/nightly/client-20260913-verification.json), [ARM provenance](evidence/aws/arm-20260913/runtime-preparation.json), [ARM source verification](evidence/aws/arm-20260913/source-verification.json)

ARM compute costs **$0.1344/hour**, public IPv4 **$0.005/hour**, and its 40 GiB gp3 volume **$3.20/month**. The stopped x86 host adds **$1.92/month** for its retained 24 GiB root volume. At 730 running hours, the combined base is about **$106.88/month**, before model use, S3, transfer, telemetry and taxes. Stop ARM between demonstrations; both stopped volumes together remain about **$5.12/month**. The helper targets ARM only. Full stack deletion removes both instances and root volumes; the rollback host is retained operationally, without a CloudFormation retention policy. [ARM pricing](evidence/aws/arm-20260913/price.json), [gp3 pricing](evidence/aws/gp3-pricing.json), [AWS IPv4 pricing](https://aws.amazon.com/vpc/pricing/), [current runbook](infrastructure/RUNBOOK.md)

Native Gateway telemetry and custom client/server collection are live. Native metrics flush every 10 seconds with seven-day retention and a 64 MiB retention target. No OTLP endpoint is set, and anonymous product reporting is off through configuration and the environment opt-out. Native Telemetry shows request, boot and process measurements. Its zero completed-turn samples do not establish a successful backend session.

The custom collectors run every 60 seconds. The Mac sample covers Nightly desktop processes and local listener checks; the server sample covers EC2 resources, Gateway/MCP main processes and loopback checks. They retain 240 samples per source and 200 fixed collection events locally on EC2. Data is `root:crew`, with directory mode `0750` and files `0640`; Crew can read it and cannot change it. The schema excludes arbitrary logs, prompts and credentials. These are operational events with bounded local retention, separate from native SEL evidence.

Demo Observability App Kit `1.0.1` displays both sources through the owner-authenticated proxy. Its backend listens only on `127.0.0.1:9102`. Health returned 200, unsigned data returned 401, unauthenticated Gateway app access returned 403, and the signed owner snapshot and live page showed current Client and Server samples. The page refreshes every 15 seconds and marks samples stale after 180 seconds. The Mac CPU sum and server CPU utilization use different sampling methods. [Runtime receipt](evidence/aws/arm-20260913/observability-runtime-receipt.json), [API readback](evidence/aws/arm-20260913/observability-api-readback.json), [collector contract](infrastructure/observability-collector/README.md), [app contract](infrastructure/observability/APP-INSTALL.md)

During the controlled desktop quit, the stopped-client sample at 14:44:42 UTC recorded zero desktop processes and a warning. The tunnel and server stayed available. The recovery sample at 14:49:34 UTC followed relaunch, and owner reconnection succeeded. These are sample timestamps; screenshots display EDT (UTC−4) and receipts use UTC. The runtime receipt records Gateway PID 4991 and its unchanged 14:26:10 UTC start identity. Current describes sample freshness, so a fresh sample can correctly report desktop running No.

Kiro CLI is selected for new sessions, matching the user's explicit choice. Its own authentication check remains false, and the native ACP log records exit code 1 because it is not logged in. The visible GitHub card reads the separate KAS identity store. The latest normal CLI login also ended without an authenticated account. At 15:19 UTC, the CLI readback remained false and both callback listeners were absent. When ready, use the helper for a fresh URL and keep its terminal open until it confirms the EC2 CLI result, then run the four native turns in a new session. Native approvals, Crew denial, SEL correlation and sandbox execution remain pending. [Latest login outcome](evidence/aws/arm-20260913/native-cli-login-outcome.json), [observed findings](output/kirocrew-admin-findings.md), [CLI login](scripts/EC2-LOGIN.md), [native procedure](scripts/native-backend-demo.README.md)

The current presentation is the [12-slide ARM and observability deck](output/kirocrew-arm-observability-demo.pptx), [slides-to-live walkthrough](WALKTHROUGH.md) and [admin guide with 13 CUA captures](output/kirocrew-admin-walkthrough.html). Grok 4.6 and Opus 5 reviewed all 12 frozen candidate-v2 images plus text and returned CHANGES REQUIRED. The dispatcher verified the image and packet byte bindings; xhigh is verified as a launch setting only. [Council receipt](evidence/council/arm-observability-v1/council-verified-receipt.json), [accepted decisions](evidence/council/arm-observability-v1/DECISIONS.md)

The final deck incorporates every accepted council change, followed by the no-ai-slop edit of the full copy and notes. Package, layout, font, editable-table, original-image-byte and exact-file import checks passed, and the author inspected all 12 final renders. Its SHA-256 is `37c82c82a00f16694f82fd11d2eda4c6188ce49de233b0c52448c47b820e0c13`. [Incorporation receipt](evidence/slides/kirocrew-arm-observability-demo/council-incorporation.json), [copy edit](evidence/slides/kirocrew-arm-observability-demo/no-ai-slop.md), [finalization](evidence/slides/kirocrew-arm-observability-demo/finalization.json), [visual review](evidence/slides/kirocrew-arm-observability-demo/visual-review.json)

The council verdict applies to candidate-v2; no final-byte council approval or native PowerPoint playback is claimed. The nine-slide x86 council review below remains historical. New ARM architecture, observability and slide diagrams passed static checks and light-theme raster review. Browser file-access policy blocked local HTML validation for the diagrams and portable guide; live portal inspection passed separately. [ARM diagram receipt](evidence/aws/archify-arm/council-delivery-receipt.json), [portal/guide browser receipt](evidence/admin-console/browser-receipt.json)

Use the runbook's separate pause/resume controls for native metrics, the collectors and the app. The cloud helper stops ARM and the tunnel but does not unload the Mac collector. On a newly prepared host, apply `infrastructure/set-demo-telemetry.py` after initial configuration and load those settings in the Gateway. It preserves other configuration sections. Do not rerun initial configuration or replace live configuration/token files to reproduce observability.

## Historical initial x86 deployment

The following notes preserve the initial x86 deployment and presentation review. Their instance size, addresses, cost and runtime observations are historical; use the ARM state and current runbook above for operations.

The September 13 continuation deploys the backend environment shown by the design. The Mac's Nightly desktop connects to the EC2 Gateway through SSH. Gateway, the installed Kiro CLI backend and workspace reside on the same EC2 host. The local Gateway toggle is off and port 5476 has no listener. The desktop shows its remote workspace and Gateway connection on local port 5599. [Client runtime receipt](evidence/aws/client-runtime-verification.json)

### Infrastructure and identities

CloudFormation created one `t3a.small` in `us-east-1`, in an existing public subnet. The instance uses Ubuntu 24.04 amd64, standard CPU credits and 24 GiB encrypted gp3 storage. The security group accepts only TCP 22 from the client's public IPv4 `/32`. Gateway 5476 and MCP 8001 bind to loopback. SSH verifies the instance host key against its authenticated EC2 console output. The cheaper public-subnet/SSH demo differs from the retained private EC2/SSM enterprise proposal. [Template](infrastructure/ec2-demo.json), [network receipt](evidence/aws/security-group.json), [SSH verification](evidence/aws/ssh-verification.json)

Root owns installed runtime and service code. The `crew` UID owns its state and workspace. The separate `mcp-demo` UID runs the MCP service. Host firewall rules reject the Crew UID's access to both metadata addresses; a real denied connection increased the matching rule counter. MCP uses the instance role through IMDSv2. The instance role includes the SSM core managed policy and bounded S3 permissions. No IAM user credentials were copied to EC2. [Host review](evidence/aws/deployment-final-review.json), [IAM policy](evidence/aws/iam-demo-policy.json)

### What ran

| Check | Evidence |
| --- | --- |
| Primary AWS MCP | Enabled and initialized against the us-east-1 endpoint. It performed real provisioning calls. The AWS Knowledge plugin was uninstalled. |
| Nightly desktop client | Native UI connected to remote Gateway and project. Local Gateway off and SSH-only listener on 5599 observed. |
| MCP caller authentication | Unauthenticated request returned HTTP 401. |
| MCP catalog and grants | Four tools were discoverable. `mcp_denied` returned `tool_grant_denied` before AWS dispatch. |
| S3 allowed read | `read_allowed` returned the digest of the existing 55-byte fixture plus an AWS request ID. |
| S3 IAM denial | `iam_denied` reached S3 and returned `AccessDenied` HTTP 403. The denied object had already been confirmed to exist. |
| Documented live command | The exact walkthrough probe command passed again, with a new trace and request IDs. |
| Native Kiro CLI and Crew denial | Pending fresh user authentication and the model-driven four-turn run. |

[Initial direct probe](evidence/aws/mcp-live-receipt.json), [service audit](evidence/aws/mcp-live-audit.jsonl), [walkthrough rehearsal](evidence/aws/walkthrough-direct-probe.json), [primary MCP discovery](evidence/aws/primary-mcp-tools.json)

The purpose-built MCP service has one fixed bearer principal, fixed tool grants, fixed S3 paths and bounded trace arguments. It returns digests rather than object contents. It is separate from the operator's primary AWS MCP connector. LiteLLM, user/group OAuth, central policy distribution and external SEL retention remain future integrations. [MCP implementation](infrastructure/mcp-enforcement/server.py)

Crew's dedicated agent has no preapproved MCP tools and uses interactive approval. Its configured `crew_denied` rule is writable by the Crew service user. A successful native denial would demonstrate that configured gate, without establishing an immutable managed policy. The native runner requires actual callback/SEL/service evidence and cannot count an operator's manual rejection as Crew prevention. [Runner](scripts/native-backend-demo.py), [operator-script review](evidence/aws/operator-scripts-review.json)

### Authentication and version boundary

The user's working local Kiro account uses GitHub. The first remote Builder ID device flow returned to browser sign-in/approval. The corrected normal Kiro flow exposed a loopback callback; SSH forwarding made that remote callback reachable from the Mac. That attempt expired before the user completed sign-in. The fresh-login helper now omits the SSH hint variables that made CLI startup stall, and a new attempt verified its own IPv4/IPv6 callback listeners. User authentication remains pending. It does not transfer any existing token/session store. [Login instructions](scripts/EC2-LOGIN.md), [latest setup receipt](evidence/aws/ec2-login-setup.json), [earlier attempt status](evidence/aws/backend-login-status.json)

The installed Nightly identifies `0.7.0-nightly.20260912t060850`. Its selected files match the installed distribution RECORD. EC2 uses a custom Linux repack of the frozen snapshot with separate Linux native libraries and hash-locked dependencies. All 24 selected deployed control modules match the locally verified installed bytes and are root-owned. There is no verified official Linux nightly artifact or source SHA for that repack. Kiro CLI 2.21.4 is a separately verified official Linux artifact. [Installed package](evidence/nightly/installed-nightly-verification.json), [deployed modules](evidence/aws/deployed-nightly-verification.json), [repack](evidence/aws/linux-repack.json), [CLI artifact](evidence/aws/kiro-cli-artifact.json)

The accepted security map retains its September 11 pinned-source identity. The earlier synthetic harness verified seven SEL records and detected a modified record. That result does not establish automatic capture or sandbox enforcement in a real EC2 backend session. The current diagrams preserve one endpoint-control enclosure and label the deployed subset separately.

### Cost and lifecycle

Compute costs $0.0188/hour and public IPv4 costs $0.005/hour. The gp3 volume costs $1.92/month. At 730 running hours the base is about $19.29/month, before model use, S3 requests, transfer and taxes. Stop the instance between demos to stop compute and release its auto-assigned IPv4; EBS remains billed. CloudFormation retains the S3 bucket and policy on deletion. [Compute pricing](evidence/aws/t3a-small-pricing.json), [gp3 pricing](evidence/aws/gp3-pricing.json), [AWS IPv4 pricing](https://aws.amazon.com/vpc/pricing/)

The lifecycle helper updates the current-IP rule through CloudFormation before booting a stopped instance, preserves every other parameter and pinned SSH checks, then refreshes the SSH target and tunnel. Its actual changed-IP/start/stop execution remains untested; read-only checks and offline failure tests passed. The operations runbook contains exact commands and retained-data cleanup boundaries. [Runbook](infrastructure/RUNBOOK.md)

### Deck review

Grok 4.6 xhigh through Grok Build and Opus 5 xhigh through Claude Code reviewed all nine candidate slide images, text and notes. Both requested changes. Their shared priorities were readable architecture labels, visible evidence status and the distinction between automatic Crew denial and operator approval. The accepted changes were incorporated, then the full deck copy and presenter notes received the requested no-ai-slop edit. [Verified council receipt](evidence/council/candidate-v3/council-verified-receipt.json), [decisions](evidence/council/candidate-v3/DECISIONS.md), [copy-edit receipt](evidence/slides/kirocrew-ec2-demo/no-ai-slop.md)

Council scope is the frozen candidate. Final artifact validation and author visual inspection are recorded separately. Neither reviewer independently queried the running AWS account.
