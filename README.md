# KiroCrew managed-control demo

A macOS KiroCrew client sends requests to a Gateway on ARM EC2. The Gateway, original Kiro CLI, workspace and host controls share one endpoint-control box. The local Mac Gateway is off; quit and reopen reconnects to EC2.

The current deployment uses a root-owned governance policy. It requires the Linux `cc` sandbox tier, denies YOLO, blocks a selected MCP tool, pins an S3 upload command rule, and protects credential and management paths. The owner can narrow ordinary settings but cannot replace the policy through Crew. Host administrators retain root authority.

The repository is private. GitHub Actions are outside this project's workflow. Endpoint operation and recording are macOS-only.

## Watch the presentation

Playback needs Python 3.9 or newer. It uses included media and needs no AWS account, KiroCrew installation, Node or FFmpeg.

```sh
git clone https://github.com/njs14/kirocrew-demo.git
cd kirocrew-demo
python3 scripts/doctor.py --feature playback
python3 scripts/serve-recorded-demos.py --build output/kirocrew-native-controls-build.json --port 5612
```

Open the [presentation](http://127.0.0.1:5612/) or [admin screenshot tour](http://127.0.0.1:5612/kirocrew-admin-tour.html). Playback replays recorded actions; it does not send live requests.

| Control | Evidence |
|---|---|
| Managed policy | The live Governance page shows Policy v1, a file-distributed source and the effective restrictions. Root-owned file and service checks bind the policy digest. |
| Permitted MCP read | A fresh native request, approved once, returns the fixture digest and an AWS request ID under the managed floor. |
| Managed MCP denial | The native tool record names the governance policy as the blocker. The matching complete service interval contains no arrival for the denied trace. |
| User MCP management | Connections exposes Crew-scoped availability and staged Apply/Discard controls. Session options shows that session's tools. An enabled tool can still be denied at invocation. |
| Command management | The policy-pinned S3 upload rule is on with its switch disabled. The previous marker-command recording retains its earlier configuration and footage limits. |
| Host isolation | A disposable process in the actual Gateway cgroup receives `EPERM` when allocating a PTY. Its permission check reports that the policy is not writable; no write was attempted. Observed Kiro CLI descendants have seccomp, no-new-privileges and separate mount namespaces. |
| MCP grants and IAM | Earlier native recordings show service-level grant denial and S3 AccessDenied. They remain dated evidence from before the managed-policy change. |
| Identity and authentication | Earlier recordings show conversation/private-memory binding and an anonymous Gateway request returning HTTP 403. This deployment does not claim enterprise SSO or restricted human-seat provisioning. |

See [managed native verification](evidence/enterprise-managed/20260913/native-managed-verification.json), [host runtime checks](evidence/enterprise-managed/20260913/host-runtime-check.json), [client restart evidence](evidence/enterprise-managed/20260913/client-relaunch.json) and [current status](evidence/native-client-demo/current-status.json). Sensitive-path, protected-write and native IMDS execution takes from the earlier host shot list retain their individual acceptance status. The `cc` setting is a Linux sandbox tier; Seatbelt applies to macOS execution.

## Reproduce it from this project

The shipped [project skill](.agents/skills/kirocrew-demo/SKILL.md) covers setup, dependencies, presentation, native execution and recording. In a compatible agent, ask: **Use $kirocrew-demo to set up and run this project's presentation and live demo.**

```sh
python3 scripts/demo-dependencies.py plan --feature all --with-browser
python3 scripts/demo-dependencies.py apply --feature all --with-browser
python3 scripts/build-demo-presentation.py --output-dir "/path/to/new presentation export"
```

Dependency installation uses a project virtual environment, locked npm packages and selected Homebrew tools. Optional council clients remain separately installed and authenticated. Read the [dependency guide](docs/DEPENDENCIES.md) for feature-specific installation and checks.

For live deployment, follow [LIVE-SETUP.md](docs/LIVE-SETUP.md). Its ten stages cover the runtime, services, S3 fixtures, telemetry, managed policy, MCP manager, host fixtures, Mac cutover, admin app and client timer. The [ARM bundle builder](docs/ARM-RUNTIME-BUNDLE.md) prepares a hash-bound bundle from an explicitly selected supported KiroCrew installation, the locked ARM wheels and official Kiro CLI. It does not need the original private repack tarballs or copy user sessions and credentials.

CloudFormation owns the EC2 host, security group, scoped instance role and demo bucket. Use [DEPLOYMENT.md](docs/DEPLOYMENT.md) and `infrastructure/portable-demo.json` with your existing VPC, subnet, Ubuntu 24.04 ARM64 AMI, key pair and administrator IPv4 `/32`. The template creates no VPC, subnet, NAT gateway, VPN, route or load balancer. Application ports remain on loopback. Existing routing and outbound access must support SSH, package installation and AWS calls.

Keep network parameters in `config/cloudformation.local.json` and deployment/client settings in `config/demo.local.json`. Keep credentials in the normal AWS and SSH credential stores. The helpers require explicit account/stack selection, pinned SSH host identity and reviewed plans for changes. [RUNTIME.md](docs/RUNTIME.md) describes those configuration contracts.

A fresh machine still authenticates through its own Kiro CLI sign-in and macOS permission prompts. A new deployment needs its own native acceptance results. Local bundle, fixture and clean-checkout tests do not confer the recorded deployment's verdict.

## Present, record and maintain

Use [MCP-GOVERNANCE.md](docs/MCP-GOVERNANCE.md) for the user-facing control sequence and [RECORDING.md](docs/RECORDING.md) for actual capture and FFmpeg processing. Raw recordings, local configuration, runtime bundles, credentials and session databases stay out of Git. Included processed clips, screenshots and receipts make playback portable.

The project skill distinguishes playback, rebuilding, provisioning and native execution. Run the focused local checks for the modules you change; no hosted CI is implied. Preserve original observations when replacing a Nightly or changing policy.

The [previous README](docs/history/README-before-managed-policy.md), [original handoff](HANDOFF.md), earlier PowerPoint, diagrams and receipts remain historical references. Their sign-in failures, direct probes and synthetic results retain their original scope.
