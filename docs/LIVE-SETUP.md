# Recreate the live demo

The project contains the CloudFormation template, runtime bundler, service sources, managed policy, MCP demonstration service, desktop setup and telemetry app. CloudFormation owns the EC2 host, instance role, security group and S3 bucket. Project setup owns the software and configuration installed on that host. Each new deployment requires its own Kiro CLI sign-in and native acceptance observations. The checked-in recordings remain evidence of the recorded deployment.

The endpoint is macOS. The supported server is Ubuntu 24.04 ARM64 with Python 3.12, using the existing `crew` and `mcp-demo` accounts and the documented `/opt/kirocrew-demo` layout. The Gateway binds only `127.0.0.1:5476`; the desktop uses a configurable local SSH-forwarded port. No VPN, bastion, VPC, subnet or NAT gateway is added by setup.

## Prepare dependencies and the existing network

Use the project skill at [`.agents/skills/kirocrew-demo/SKILL.md`](../.agents/skills/kirocrew-demo/SKILL.md) for dependency installation and readiness checks. Run the KiroCrew desktop once so it creates its own configuration. Authentication stays in its owning product: keep AWS credentials in the AWS CLI chain, SSH keys in your SSH setup, and sign the EC2 Kiro CLI in through its own fresh flow. Do not copy a laptop token store or browser session to EC2.

After dependency setup, activate the environment before running the Python commands below:

```sh
source .venv/bin/activate
```

If you selected a different `--venv`, activate that environment instead. This supplies the Python 3.12 interpreter and installed libraries used by live setup.

Follow [DEPLOYMENT.md](DEPLOYMENT.md) to choose an **existing VPC and subnet**, an ARM-compatible AMI and the instance size. The ingress rule permits only TCP 22 from one client IPv4 `/32`. A private subnet must already have a route from the Mac and the outbound access needed for installation. Selecting a subnet does not create those routes.

Copy `config/demo.example.json` to the ignored `config/demo.local.json`. Set the account, region, stack, SSH aliases, trusted host-key alias and local paths. The example account is a placeholder. Verify the instance host key through your trusted process; no helper automatically trusts `ssh-keyscan` output. Set up the shared SSH `Host` block described in [RUNTIME.md](RUNTIME.md), including the Gateway (`crew`) and administration (`ubuntu`) aliases. The native desktop invokes `/usr/bin/ssh` through the default `~/.ssh/config`; a separate custom SSH file must also resolve to the same guarded alias through that default configuration, or desktop setup refuses it.

```sh
export KIRO_DEMO_CONFIG="$PWD/config/demo.local.json"
python3 scripts/demo-cloud.py status --config "$KIRO_DEMO_CONFIG"
```

Every applied setup stage repeats the account, stack ownership, instance, existing network and single `/32` checks, then checks that the administration alias points to that stack's current instance address. If the instance address changed, use the existing `demo-cloud.py start` plan/apply workflow to reconcile it first. Setup never changes network rules itself.

## Apply one stage at a time

`setup-live-demo.py` emits a plan by default. Plans make no network calls; runtime and service plans validate the selected bundle locally. Add `--apply` only to the stage you intend to execute. There is no all-stages operation that hides restarts, authentication or native UI acceptance.

| Stage | Result | Existing-state behavior |
|---|---|---|
| `runtime` | Verifies and stages the ARM bundle, then installs its root-owned runtime | Requires an absent runtime venv; never overwrites a running installation |
| `services` | Installs original Kiro CLI, the demo Gateway and MCP service, and the dedicated agent | Fresh host only; refuses existing config, token, CLI or MCP venv |
| `fixtures` | Creates the two tiny S3 canaries and updates the local expected allowed-object digest | Accepts identical bytes; refuses different existing objects and uses conditional creation |
| `server-integrations` | Installs the root owner helper, collectors and app source; enables native local telemetry and the server timer | Existing integration files must match; telemetry changes need `--restart-gateway` |
| `managed-policy` | Delegates preflight, policy installation and verification to the managed-policy helper | Activation requires `--restart-gateway`; receipts go to a new private directory |
| `desktop` | Preserves other settings, disables the local Gateway and adds the exact remote owner-helper entry | Requires KiroCrew to be quit; refuses conflicting entries or tunnel jobs |
| `client-telemetry` | Installs the config-bound macOS timer after a successful real upload | Reuses the existing exact-job and upload guards |
| `app` | Installs, trusts and enables only the reviewed `demo-observability` app through the owning Gateway | Refuses a different existing app; leaves global app trust unchanged |
| `mcp-user-ui` | Registers the demonstration MCP in Crew's user-facing MCP connections and verifies it | Can retire only the exact duplicate local denial after the managed policy is active |
| `host-controls` | Creates the dedicated host-control agent, public canaries and fixed diagnostic helpers | Delegates the existing additive fixture preflight/apply; refuses unsafe collisions |

The root-owned staging directory is named by the complete input inventory SHA-256. Upload accepts only the inventoried, individually hashed regular files. Symlinks, traversal, extra archive entries and changed staged files are refused. A failed stage can leave completed prerequisite work; inspect the reported host state before retrying. No automatic destructive rollback removes a partially installed runtime.

### Runtime and services

Prepare a manifest-driven ARM bundle using [ARM-RUNTIME-BUNDLE.md](ARM-RUNTIME-BUNDLE.md). Select the installed KiroCrew package explicitly; the bundler does not include user configuration, credentials or sessions. Its wheel lock, ARM libraries and official Kiro CLI archive are verified. The historical fixed-hash `install-arm-runtime.sh` remains a record of the accepted deployment; new setup uses `install-runtime-bundle.py`. Save the reviewed manifest SHA from preparation or the setup plan, and pass that same value when applying. A changed bundle is refused before deployment reads or mutations.

```sh
python3 scripts/setup-live-demo.py --stage runtime --config "$KIRO_DEMO_CONFIG" --bundle "$PWD/.build/arm-bundle"
# Replace REVIEWED_MANIFEST_SHA256 with the exact digest from the reviewed preparation or plan.
python3 scripts/setup-live-demo.py --stage runtime --config "$KIRO_DEMO_CONFIG" --bundle "$PWD/.build/arm-bundle" \
  --manifest-sha256 REVIEWED_MANIFEST_SHA256 --apply
python3 scripts/setup-live-demo.py --stage services --config "$KIRO_DEMO_CONFIG" --bundle "$PWD/.build/arm-bundle" \
  --manifest-sha256 REVIEWED_MANIFEST_SHA256 --apply
```

The service installer intentionally accepts the reviewed Kiro CLI 2.21.4 ARM archive. A different runtime or CLI must pass its own source and protocol review; changing a checksum is not a compatibility test. The bootstrap's IMDS firewall and AppArmor prerequisites must already be ready, as described in the deployment guide.

### S3 fixtures

The default fixtures contain only public explanatory canary text. Both `allowed/sentinel.txt` and `denied/sentinel.txt` must exist before interpreting IAM's 403. The setup identity reads both objects to verify existence and content; the instance role is deliberately denied the second object.

```sh
python3 scripts/setup-live-demo.py --stage fixtures --config "$KIRO_DEMO_CONFIG"
python3 scripts/setup-live-demo.py --stage fixtures --config "$KIRO_DEMO_CONFIG" --apply
```

For an existing deployment, supply `--allowed-file PATH --denied-file PATH` with the exact existing, non-sensitive bytes. Inputs must be 1–4096 bytes. Different objects are never silently overwritten. After both readbacks match, setup backs up the selected local configuration and sets only `probe.expected_allowed_sha256`. The receipt records bucket, keys, sizes and digests; no object text or AWS credentials are printed.

### Server integrations and managed policy

The server integration stage writes the existing bounded local telemetry settings with an empty OTLP endpoint and the beacon disabled. Its custom collector has its own data directory and timer; it does not turn client samples into native model metrics. It stages the app but does not install or trust it until the `app` stage.

```sh
python3 scripts/setup-live-demo.py --stage server-integrations --config "$KIRO_DEMO_CONFIG" --restart-gateway --apply
python3 scripts/setup-live-demo.py --stage managed-policy --config "$KIRO_DEMO_CONFIG"
python3 scripts/setup-live-demo.py --stage managed-policy --config "$KIRO_DEMO_CONFIG" \
  --receipt-dir "$PWD/.build/live-setup/policy-first-install" --restart-gateway --apply
```

The policy stage calls `manage-enterprise-policy.py preflight`, saves that exact receipt, applies from it, activates when requested and verifies the result. The policy file and service distribution setting are root-controlled. The ordinary Crew owner cannot edit this floor through Crew configuration. This is host administration, not an assertion that root itself is governed by Crew. The Linux sandbox applies to execution on EC2; macOS Seatbelt does not sandbox a remote Linux process.

Installing policy without `--restart-gateway` leaves activation pending. It must not be presented as active policy until the helper verifies the running process after activation. The dedicated MCP denial remains governed even when a user's local MCP toggle is enabled.

### Desktop cutover and authentication

Quit the configured KiroCrew desktop before applying the desktop stage. The helper checks the actual app identity and refuses an active process, a conflicting remote entry or an unrelated LaunchAgent. It backs up the config, writes it with mode `0600`, sets `runLocalGateway=false`, and preserves other remote hosts and settings.

```sh
python3 scripts/setup-live-demo.py --stage desktop --config "$KIRO_DEMO_CONFIG"
python3 scripts/setup-live-demo.py --stage desktop --config "$KIRO_DEMO_CONFIG" --apply
```

With `tunnel.mode=launchagent`, setup installs or reuses only the exact guarded tunnel job. With `manual`, it prints the strict SSH command to run in another terminal. Reopen KiroCrew and select the configured remote port. If other hosts already exist, the initial window may select a different saved host; setup does not rewrite unrelated dashboard preferences. The empty legacy `remoteHost` field is preserved; the current native app uses `remoteHosts`.

The owner helper mints the normal short-lived owner connection through the administration user's existing sudo access. It does not grant sudo to `crew`, print a token into a receipt or copy the Mac's Kiro CLI identity. Sign in separately:

```sh
python3 scripts/ec2-login.py --config "$KIRO_DEMO_CONFIG"
```

Complete the real sign-in in the user's browser, then select the original Kiro CLI backend and start a fresh dedicated demonstration session. The helper supports the reviewed Kiro CLI 2.21.4 protocol. A successful stack or service installation is not authentication acceptance.

### Telemetry app and MCP in the user's UI

```sh
python3 scripts/setup-live-demo.py --stage client-telemetry --config "$KIRO_DEMO_CONFIG" --apply
python3 scripts/setup-live-demo.py --stage app --config "$KIRO_DEMO_CONFIG" --apply
python3 scripts/setup-live-demo.py --stage mcp-user-ui --config "$KIRO_DEMO_CONFIG" \
  --receipt-dir "$PWD/.build/live-setup/mcp-first-install" --apply
```

The app bridge verifies the reviewed local app files and the installed App Kit API contract. It uses the pinned SSH connection and a private local socket for same-product authentication; raw tokens, cookies and API responses are never logged. Only this app receives a trust grant. A different installed copy or unsupported runtime contract requires review rather than an automatic overwrite or global trust change.

Once the managed policy is active, the optional `mcp-user-ui --retire-mutable-deny --restart-gateway` setup removes only the duplicate mutable `@aws-enforcement/crew_denied` hook entry. That makes a new denial attributable to the managed policy instead of the older local hook. Historical recordings retain their original attribution.

Open **Connections → MCP Servers** and the read-only governance page in KiroCrew. Inspect the active server and tools, then perform a fresh native request for the managed-denied tool. The frozen UI does not draw a per-tool governance lock: local enablement shows availability, while the host policy decides execution. Show the actual refusal without implying that a local toggle overrides policy. Capture the real UI and correlate its denial with the server event and absence of MCP-service execution.

Open **Apps → Demo Observability** and verify current client and server samples plus both sources in Collection logs. `backend_healthy=true` proves app health; `fresh_client_and_server=true` proves fresh collector samples. Neither replaces screenshot or native interaction acceptance. The Native Telemetry panel remains separate and may have empty model metrics until real instrumented turns occur.

Prepare the host-control scenes through their existing additive installer:

```sh
python3 scripts/setup-live-demo.py --stage host-controls --config "$KIRO_DEMO_CONFIG" \
  --receipt-dir "$PWD/.build/live-setup/host-fixtures-first-install" --apply
```

Use [HOST-CONTROL-SCENARIOS.md](HOST-CONTROL-SCENARIOS.md) for the exact native requests and acceptance criteria. The setup receipt binds the selected host's actual UID, workspace and helper bytes. Historical `read-native-host-fixture-history.py` reconstructs the recorded September 13 fixture and is not a generic fresh-host evidence reader; use the new setup binding when collecting new evidence. Installed fixtures are preparation, not proof that a native read, write, command or metadata request was blocked.

## Stop and recover narrowly

Use `demo-telemetry.py stop --config ... --apply` for the exact client timer. Use the existing cloud helper's `local-client-rollback` plan/apply path after quitting KiroCrew to restore local Gateway mode and remove only the matching remote host. This does not delete the EC2 stack or its data. The managed-policy helper owns its own receipt-bound rollback; inspect that plan before applying it. Runtime/service replacement and stack deletion are separate operations and are not part of this setup command.

For a second host, keep a separate ignored config and fresh receipt directories. Do not reuse the first host's authentication, source-IP assumption, pinned key, runtime-success receipt or native-control result.
