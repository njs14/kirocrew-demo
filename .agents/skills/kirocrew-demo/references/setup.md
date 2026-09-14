# Set up a new project checkout

Use the project scripts; the linked guides hold their maintained schemas and detailed options. Start with [docs/DEPENDENCIES.md](../../../../docs/DEPENDENCIES.md), then load only the guides for the requested stage.

## Local tools

From the project root, run `python3 scripts/demo-dependencies.py plan --feature all --with-browser` for complete authoring/live setup, or select `playback`, `authoring`, `cloud`, or `native`. Apply the selected scope when authorized, then run `scripts/doctor.py` with the same feature. The `council` feature is optional and is excluded from `all`. A fresh Mac without Python first needs the bootstrap described in DEPENDENCIES.md.

The manager installs project Python packages into `.venv` by default. Use that interpreter for subsequent setup commands. It does not install KiroCrew itself or authenticate products. Record the installed app version and prepare an explicit runtime package; never assume a new Nightly matches a dated receipt.

## Cloud and server

Read [docs/DEPLOYMENT.md](../../../../docs/DEPLOYMENT.md), [docs/ARM-RUNTIME-BUNDLE.md](../../../../docs/ARM-RUNTIME-BUNDLE.md), and [docs/LIVE-SETUP.md](../../../../docs/LIVE-SETUP.md).

- Copy `config/demo.example.json` to ignored `config/demo.local.json`, set the actual AWS account/stack and SSH bindings, and select an existing VPC and subnet in the CloudFormation parameters. A private subnet needs the user's existing route and outbound installation access. Keep inbound SSH restricted to the single actual client IPv4 `/32` and retain the cheap, supported ARM instance choice.
- Prepare a portable runtime with `scripts/prepare-arm-runtime.py plan` and `prepare`, using the explicit installed `kiro_crew` package and a fresh `.build/arm-bundle` output. Consult its `--help` for metadata, existing wheelhouse and official CLI archive inputs. Unsupported versions stop for a compatibility update rather than receiving a false baseline label.
- Deploy through the config-bound CloudFormation helper, verify account/network/host-key selection, then use `scripts/setup-live-demo.py --config PATH --stage STAGE` to inspect the selected stage. Its ten stages are `runtime`, `services`, `fixtures`, `server-integrations`, `managed-policy`, `desktop`, `client-telemetry`, `app`, `mcp-user-ui`, and `host-controls`; `--apply` performs only the selected stage. Runtime and services take the prepared `--bundle`; apply also requires `--manifest-sha256` with the digest reviewed during preparation or planning, not a freshly calculated substitute. Follow LIVE-SETUP.md for current ordering, fresh receipt directories and explicit Gateway-restart options.
- Apply the root-managed policy through `scripts/manage-enterprise-policy.py`, using its preflight/plan/apply/verify contract. Inspect `--help` and its infrastructure policy guide before mutation. Verify the effective policy source and root-owned ancestors before claiming a floor that the Crew owner cannot replace.
- Read [docs/MCP-GOVERNANCE.md](../../../../docs/MCP-GOVERNANCE.md) and use `scripts/manage-demo-mcp.py plan --config PATH` to inspect the user-facing MCP registration. Retire the exact older mutable deny only with its explicit `--retire-mutable-deny` flow after the managed replacement is verified; applying that plan also requires `--restart-gateway` and interrupts sessions. Preserve unrelated MCP configuration.
- Use the `host-controls` stage with a new `--receipt-dir` for the additive diagnostic fixtures. Bind fresh recordings to that receipt's actual UID, workspace and helper hashes; the September 13 history reader is a historical reconstruction, not a generic new-host reader.

Review new native host takes through [docs/NATIVE-HOST-REVIEW.md](../../../../docs/NATIVE-HOST-REVIEW.md). It provides before/after snapshots and a local reviewer for the sensitive read, protected write and fixed IPv4 metadata TCP helper. Preserve the exact target, native tool-call ID, source hash and observation interval. The helper can require a native source-read approval followed by a separate execution approval; allow each exact requested operation once when it matches the reviewed fixture. A model explanation does not identify the enforcing layer.

A completed stack is a host and AWS resources, not a running authenticated demo. The runtime, service install, existing S3 fixture objects, remote CLI login, Mac remote-host selection, local Gateway off state, telemetry and AppKit installation each need their own observed result. Never reuse historical expected fixture digests for new data without a provisioning receipt.

After activation, use [scripts/verify-managed-host.py](../../../../scripts/verify-managed-host.py) with `--config PATH --output NEW_RECEIPT`. It checks protected policy/source files, tries PTY creation only in its own disposable child inside the Gateway's service cgroup, and observes native CLI descendants. It neither restarts the Gateway nor moves an existing process. Its result is a host check; a passing PTY denial or namespace observation does not prove that a particular native tool was sandboxed. Compare its scope with [the recorded host check](../../../../evidence/enterprise-managed/20260913/host-runtime-check.json) and collect a new receipt for the selected deployment.

## Native sign-in and acceptance

Run `scripts/ec2-login.py --config PATH` through an interactive terminal for the supported original Kiro CLI protocol. Let the user complete that product's browser sign-in when required; never copy session databases or tokens from another product. If browser approval loops, stop retrying the same expired flow and report the exact stage, while continuing independent setup work.

Use the actual Mac app to verify the selected EC2 host and original Kiro CLI backend, local Gateway off state, connected MCP tools, managed policy display and a harmless allowed request. Recheck after a Nightly update or Gateway restart. After the last restart, create a persistent dedicated native session and send only `Reply READY without calling any tools.` Wait for its idle state before binding the observer to that exact session and running the control take. A successful local doctor is not remote authentication or enforcement proof; the existing deployment's receipts do not establish acceptance of a newly provisioned host.

If accessibility text or screenshots stop matching the visible app, pause collection and inspect the actual native view. A normal full app quit/relaunch can restore fresh state without a Gateway restart; verify the saved remote connection and conversation after relaunch. **View → Reload** produced a black view in the recorded recovery attempt and is not the recommended repair.
