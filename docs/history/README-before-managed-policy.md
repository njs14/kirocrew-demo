# KiroCrew demo

Native recordings show a macOS KiroCrew user reaching controls on an EC2 server: an allowed S3 read, a Crew tool denial, an MCP grant denial, an IAM denial, a private-memory assignment refusal, a workspace read, a command-denial response summary and an anonymous request ending in HTTP 403. A separate screenshot tour explains the admin console and client/server telemetry. Gateway, Kiro CLI backend, workspace and host controls remain together in one endpoint-control box.

The repository is private. GitHub Actions are outside this project's workflow; validation runs locally. The endpoint client scope is macOS.

## Play the native control demonstrations

Python 3.12+ is sufficient for the included preview. AWS credentials, KiroCrew, Node and FFmpeg are not needed to watch it.

```sh
git clone https://github.com/njs14/kirocrew-demo.git
cd kirocrew-demo
python3 scripts/doctor.py --feature preview
python3 scripts/serve-recorded-demos.py --build output/kirocrew-native-controls-build.json --port 5612
```

Open [the native control presentation](http://127.0.0.1:5612/). The 14-slide edition contains eight native Mac clips with replay, cue seeking and linked evidence. Open [the admin screenshot tour](http://127.0.0.1:5612/kirocrew-admin-tour.html) from the same preview. It has nine stops and 19 original screenshots, including the four completed MCP turns in Gateway telemetry.

| Demonstration | Observed outcome and scope |
|---|---|
| Allowed S3 read | The native request is approved once; the MCP service returns the provisioned fixture's digest and AWS request ID. |
| Crew tool control | The Gateway automatically blocks `crew_denied` before MCP arrival. The configured rule is Crew-writable in this demo. |
| MCP grant control | After native approval, the separate MCP service returns `tool_grant_denied` before AWS dispatch. |
| AWS IAM control | After native approval and MCP dispatch, S3 returns `AccessDenied`, HTTP 403 and a matching AWS request ID. |
| Conversation identity binding | The server refuses a conversation without a verified private-memory assignment before a tool starts. Human-role authorization remains untested. |
| Allowed workspace read | One native file read returns the prepared public marker; no approval callback is tested. |
| Server command rule | The clip shows the assistant response summary. Exact native-history and SEL receipts support automatic command denial; request and expanded-result footage are missing. |
| Anonymous Gateway request | The excerpt shows execute approval through the assistant's HTTP 403 summary. The earlier helper-read approval and collapsed tool output have separate evidence; the reviewed correlation identifies Gateway token authentication. |

These recordings preserve observations from September 13, 2026 (EDT); playback does not send live requests. The [four-turn reconciliation](evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json), [independent review](evidence/native-client-demo/20260913-ui2-reconciled-final/review.json), fresh ARM authority readbacks and media reviews support the stated outcomes. The original collector remains `collection_complete: false`; its limited SEL window was recovered separately. The reconciler retains `full_native_acceptance: false` because it does not decide footage acceptance or every attribution check. There is no evidence that process sampling overlapped a pending approval.

Published collector evidence uses bounded exports for the [four MCP turns](evidence/native-client-demo/20260913-ui2/receipt-publication.json), [memory refusal](evidence/native-client-demo/host-20260913-ui1/receipt-publication.json) and [unused host capture](evidence/native-client-demo/host-20260913-ui2/receipt-publication.json). Full baseline and receipt snapshots remain byte-identical and privately retained because they include unrelated authentication details. Source hashes still refer to those originals; scoped native events and the recovered SEL interval remain available for review. The exports preserve the original collection verdicts.

The Mac was unlocked and host testing resumed. A native workspace-canary read succeeded. A separate native marker command was automatically blocked by the server's configured command rule; persisted native history and an isolated `hook_deny` support that result, but footage shows the assistant's response summary only; request submission, expanded tool output and policy reason are not visible. Sensitive-path and anonymous-helper attempts produced model-only refusals before tool execution, so they establish no server denial. A later anonymous request completed after separate approvals to read and execute the fixed helper, then returned HTTP 403. Its clip begins at execute approval; the earlier source-read approval is outside the excerpt. [Reviewed correlation](evidence/native-client-demo/host-20260913-review/auth-review.json) identifies the Gateway's missing-token denial. Sensitive-path read, protected-path write and metadata TCP isolation remain unfinished. The IMDS execution approval expired unanswered after ten minutes; no helper execution or firewall result was observed. A fresh slot failed screenshot readiness, so no prompt was submitted. See the [resumed host appendix](docs/NATIVE-CLIENT-DEMO.md#resumed-host-observations), [recording plan](DEMO-RECORDING-PLAN.md), [host-control shot list](docs/HOST-CONTROL-SCENARIOS.md) and [current status](evidence/native-client-demo/current-status.json).

The temporary command marker was removed after the take. The [cleanup readback](evidence/native-client-demo/host-20260913-ui3/command-rule-cleanup.json) confirms the marker and its ID are absent, with no built-in IDs disabled. Read the [current admin findings](output/kirocrew-native-admin-findings.md) alongside the tour.

The [earlier 20-slide recorded edition](output/kirocrew-recorded-demos.html), [PowerPoint](output/kirocrew-arm-observability-demo.pptx), accepted diagrams and historical receipts remain available. Their older sign-in failures, direct service probes and synthetic runs keep their original scope.

## Choose the module you need

| Module | Entry point | Inputs and prerequisites |
|---|---|---|
| Watch the native deck and admin tour | `scripts/serve-recorded-demos.py` | Included media; explicit `--build output/kirocrew-native-controls-build.json` and `--port` |
| Plan CloudFormation | `scripts/deploy-demo.py` | Explicit stack, region/profile and CloudFormation parameter file; existing AWS CLI credentials |
| Operate a deployment | `scripts/demo-cloud.py` | Explicit local config; account/stack guards and discovered outputs |
| Collect client telemetry | `scripts/demo-telemetry.py` | Explicit local config, verified SSH host key and macOS scheduling |
| Native Kiro CLI sign-in/demo | `scripts/ec2-login.py`, `scripts/capture-native-client-evidence.py` | Configured SSH route, installed server runtime and separate native sign-in; prompts and approvals in the Mac client |
| Prepare additional host takes | `scripts/configure-host-controls.py` | Explicit config; reviewed preflight and apply; see the host-control shot list |
| Record/process new clips | `scripts/demo-clips.py` | Actual footage, cue manifest and local FFmpeg; see [recording setup](docs/RECORDING.md) |

`python3 scripts/doctor.py --feature all` checks local prerequisites and included artifact hashes. It makes no AWS, SSH or application connection.

## Use your existing VPC and subnet

[infrastructure/portable-demo.json](infrastructure/portable-demo.json) is the template for new deployments. Supply an existing VPC, one subnet, an Ubuntu 24.04 ARM64 AMI, a key pair and the administrator IPv4 `/32`. One subnet is sufficient for this single-instance demo. Choose public-IP assignment explicitly and set the outbound HTTP/HTTPS parameters to match the network you already operate.

The template creates one ARM EC2 host and the demo's security group, scoped instance role and S3 bucket. It creates no VPC, subnet, Internet Gateway, NAT gateway, route, VPC endpoint or load balancer. Application ports stay on loopback; inbound SSH is limited to the configured `/32`.

The planning helper checks subnet/VPC membership, DNS configuration, effective routes, AMI architecture and instance compatibility before preparing a change set. Existing private routing can use an already configured NAT, VPN, transit gateway or appliance path. You remain responsible for the complete network path, including NACLs, upstream policy and access to package repositories and AWS services. Read the [deployment guide](docs/DEPLOYMENT.md) for the parameter examples, preflight limits and explicit change-set execution procedure.

[infrastructure/ec2-demo.json](infrastructure/ec2-demo.json) preserves the historical two-host deployment. Do not apply the new single-instance template to that existing stack: removing its rollback host would be a separate infrastructure change. This portability update does not redeploy the accepted environment.

## Configure another machine

Copy the example and edit only deployment identifiers, paths and ports:

```sh
cp config/demo.example.json config/demo.local.json
```

Set `aws.account_id`, `aws.stack_name`, the SSH aliases and the verified host-key alias. Local paths can use `~` or resolve relative to the config file. Keep AWS credentials in your existing AWS CLI profile or credential provider. The config schema does not accept credentials.

```sh
python3 scripts/demo-cloud.py status --config config/demo.local.json
python3 scripts/demo-telemetry.py collect-once --config config/demo.local.json
```

Cloud mutations require explicit configuration and `--apply`. SSH checks remain strict. The tools do not create trusted host keys from an unverified scan. macOS client scheduling and local Gateway controls are separate from Linux/EC2 service installation. See [runtime setup](docs/RUNTIME.md) for the connection, telemetry and installer parameters.

The accepted EC2 runtime was a custom ARM repack of the installed September 12 Nightly. Runtime archives, installed applications, credentials and session databases are not distributed here. To execute the synthetic rehearsal on another machine, prepare a snapshot from a KiroCrew package you already have, then select its generated baseline manifest. A different package produces new evidence; it does not inherit the accepted recording's verdict. The [recording setup](docs/RECORDING.md) documents this path and the optional browser dependencies.

## Validation and source boundaries

Run the focused local tests documented with each module. No workflow files or hosted CI are included. Network fixtures validate the planning logic; they do not establish connectivity in an arbitrary VPC. A successful CloudFormation change set also does not establish successful OS bootstrap, native authentication or backend enforcement.

The native edition contains eight recordings. Each media review states its inspected frames and capture scope. Any browser or council verdict applies only to the exact artifacts named in its review receipt. The accepted HTML, PPTX, recordings and historical receipts retain their original evidence scope. The first recorded edition passed 71 browser checks, 29 chapter seeks and media/evidence delivery checks. Its prior model council verdicts apply to the frozen candidates named in those receipts. The [portability acceptance receipt](evidence/portability/acceptance.json) links the fresh-checkout checks and current code reviews. Endpoint validation is macOS-only. Server and infrastructure checks retain their individual runtime and fixture scopes.

The Git tree excludes local configuration, `.build`, virtual environments, raw captures, browser state, test signing keys and disposable workspaces. It includes processed media so a fresh clone can play the deck. Some historical receipts link to intentionally excluded local runtime artifacts. The [earlier README](docs/history/README-before-portability.md), [deployment handoff](HANDOFF.md) and [historical runbook](infrastructure/RUNBOOK.md) preserve the original observations and machine-specific commands; use the new setup guides for another deployment.
