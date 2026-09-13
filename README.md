# KiroCrew demo

Recorded walkthroughs and modular tools for running a KiroCrew Gateway on EC2, connecting a local client, inspecting telemetry, and testing a separate MCP service's AWS access. The accepted presentation keeps Gateway, backend, workspace and endpoint controls in one endpoint-control box.

The repository is private. GitHub Actions are outside this project's workflow; validation runs locally.

## Play the recorded demos

Python 3.12+ on macOS or Linux is sufficient for the included preview. AWS credentials, KiroCrew, Node and FFmpeg are not needed to watch it.

```sh
git clone https://github.com/njs14/kirocrew-demo.git
cd kirocrew-demo
python3 scripts/doctor.py --feature preview
python3 scripts/serve-recorded-demos.py --port 5606
```

Open [the recorded scenes](http://127.0.0.1:5606/#slide-15). The 20-slide deck contains the accepted 14 slides followed by six recordings, totaling 2 minutes 43 seconds. Replay, chapters, guided pauses and linked receipts work in the local HTTP preview.

| Scene | Evidence scope |
|---|---|
| Endpoint diagram and ARM placement | Accepted architecture reference and dated deployment evidence |
| Admin-console navigation | Recorded owner-portal operation, backend selection and sign-in failure |
| Client/server telemetry | Stored Mac/EC2 samples and collection events |
| Native Gateway instruments | Gateway metrics with zero completed backend turns |
| Direct MCP/AWS probe | Real S3 read, MCP grant rejection and IAM denial |
| Synthetic control rehearsal | Isolated local controls and scripted approval |

The recordings preserve September 13, 2026 observations. They do not operate a live deployment during playback. Native Kiro CLI sign-in and completed-turn enforcement remain pending. The planned quit/relaunch recording also remains pending; older runtime receipts document a separate client-stop observation. See the [recording guide](DEMO-RECORDING-GUIDE.md), [recording receipt](DEMO-RECORDING-RECEIPT.json), [admin-console tour](output/kirocrew-admin-walkthrough.html) and [findings](output/kirocrew-admin-findings.md).

## Choose the module you need

| Module | Entry point | Inputs and prerequisites |
|---|---|---|
| Watch the deck | `scripts/serve-recorded-demos.py` | Included media; `--port` and optional `--build` |
| Plan CloudFormation | `scripts/deploy-demo.py` | Explicit stack, region/profile and CloudFormation parameter file; existing AWS CLI credentials |
| Operate a deployment | `scripts/demo-cloud.py` | Explicit local config; account/stack guards and discovered outputs |
| Collect client telemetry | `scripts/demo-telemetry.py` | Explicit local config and verified SSH host key; macOS scheduling or manual Linux collection |
| Native Kiro CLI sign-in/demo | `scripts/ec2-login.py`, `native-demo.sh` | Configured SSH route, installed server runtime and separate native sign-in |
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

The accepted HTML, PPTX, recordings and historical receipts retain their original evidence scope. The first recorded edition passed 71 browser checks, 29 chapter seeks and media/evidence delivery checks. Its prior model council verdicts apply to the frozen candidates named in those receipts. The [portability acceptance receipt](evidence/portability/acceptance.json) links the fresh-checkout checks and current code reviews. Validation ran on macOS; Linux paths are implemented but have not been exercised on a separate Linux machine.

The Git tree excludes local configuration, `.build`, virtual environments, raw captures, browser state, test signing keys and disposable workspaces. It includes processed media so a fresh clone can play the deck. Some historical receipts link to intentionally excluded local runtime artifacts. The [earlier README](docs/history/README-before-portability.md), [deployment handoff](HANDOFF.md) and [historical runbook](infrastructure/RUNBOOK.md) preserve the original observations and machine-specific commands; use the new setup guides for another deployment.
