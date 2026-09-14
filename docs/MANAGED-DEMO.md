# Managed KiroCrew demo

The EC2 Gateway now loads a root-owned governance policy. The Crew owner can edit ordinary configuration, but the Crew service account cannot write that policy or its systemd configuration. A fresh request from the native Mac client was denied by the policy before it reached the MCP service. The earlier editable `crew_denied` hook was removed before this test.

This is the current guide. The [status file](../evidence/native-client-demo/current-status.json) records presentation integration progress. Earlier guides and the eight earlier clips retain their original dates and evidence scope.

## What is enforced

The Gateway reads `/etc/kirocrew-demo/security-policy.json` at startup with `fail_closed` behavior. It requires the `cc` sandbox level, denies YOLO mode, denies `@aws-enforcement/crew_denied`, pins the built-in S3 upload command rule, and adds the specified path and command restrictions. The policy file, its ancestors and the service drop-in are protected by root ownership. See the [policy plan](../evidence/enterprise-managed/20260913/policy-plan.json), [running-service verification](../evidence/enterprise-managed/20260913/policy-verify.json) and [MCP verification](../evidence/enterprise-managed/20260913/mcp-verify.json).

The dashboard terminal is disabled. A separate device policy provides a kernel backstop: a disposable process running as Crew inside the Gateway's actual service cgroup received `EPERM` when it tried to create a PTY. Existing Kiro CLI processes had `NoNewPrivs=1`, seccomp filters and separate mount namespaces. These are the bounded observations in the [host runtime check](../evidence/enterprise-managed/20260913/host-runtime-check.json); they do not establish every sandbox behavior during a particular tool call.

Host root remains the administrator. This deployment uses a local, unsigned policy file fetched at startup, an owner connection and the Linux `cc` sandbox. It has no enterprise SSO, managed Kiro CLI MCP registry or verified macOS Seatbelt enforcement. The configured YOLO denial does not make every other approval mode interactive.

## Walk through the controls

1. Open the native Mac client and confirm the remote Gateway connection. The [quit and relaunch observation](../evidence/enterprise-managed/20260913/client-relaunch.json) verified that the Mac's local Gateway remained off while its SSH tunnel stayed available. The subsequent native tests used the original Kiro CLI backend on EC2.
2. Open **Settings → Security → Governance**. Show the active file policy, its rule counts and the `cc` floor. Open the command rules, search for `s3`, and show the pinned upload rule with its disabled switch and organization-policy explanation.
3. Open **Connections → MCP Servers**. The `aws-enforcement` server is online with four tools and enabled for Crew only. The provider-global settings stay off. Stage a tool restriction to show **Apply** and **Discard**, then discard the preview. These toggles control tool availability; the UI does not display a separate policy-lock badge for each tool. Follow [MCP-GOVERNANCE.md](MCP-GOVERNANCE.md) for the user-facing manager and session inventory.
4. In a dedicated `enforcement-demo` conversation, request `@aws-enforcement/read_allowed` once with a fresh trace. Read the native approval card and approve that exact request once. In the completed `ui3` test, S3 returned the expected 55-byte fixture and matching digest. That successful read has [native and service evidence](../evidence/enterprise-managed/20260913/native-managed-verification.json), but no retained video.
5. Request `@aws-enforcement/crew_denied` once with another fresh trace. Stop after the denial. Expand the native blocked notice to show **Blocked by governance policy** and the exact tool pattern. The separate [ui4 take](../evidence/enterprise-managed/20260913/native-managed-ui4-verification.json) recorded this automatic denial without a permission prompt. Its completed service interval contained no MCP audit arrivals. The [40-second clip review](../evidence/enterprise-managed/20260913/media-review.json) covers the request, block and expanded reason; it does not include the earlier allowed read.
6. Use the admin tour to connect each result to its control and then inspect client/server telemetry. Telemetry identifies activity and collection state; use native tool records, policy events and the MCP audit to attribute security decisions.

For a new take, use a new trace, one exact tool request and no retry or alternative route. Preserve the native tool-call ID and the complete server observation interval. The policy event has no direct native tool-call or trace ID, so its correlation uses the isolated session, exact tool, reason, timestamp and adjacent event linkage.

## Recreate it from this project

Invoke the project skill with `$kirocrew-demo`, or read [its setup, presentation and recording routes](../.agents/skills/kirocrew-demo/SKILL.md). The [dependency manager](DEPENDENCIES.md) plans and installs the selected workflow's dependencies. Playback needs Python 3.9 or newer and the checked-in artifacts. Authoring and live setup use an isolated Python 3.12 environment. Reviewer products are optional for playback.

The [live setup guide](LIVE-SETUP.md) covers ten explicit stages: runtime, services, fixtures, server integrations, managed policy, desktop, client telemetry, app, MCP user UI and host controls. Use the [ARM runtime bundler](ARM-RUNTIME-BUNDLE.md) to prepare the selected installed Nightly without copying user credentials or sessions. Each product uses its own sign-in, and a new deployment requires its own native acceptance tests.

Use [CloudFormation deployment](DEPLOYMENT.md) with an existing VPC and subnet. Put network values in a separate CloudFormation parameter file using the [public](../config/cloudformation-public.example.json) or [private](../config/cloudformation-private.example.json) example, and machine-specific connection values in the ignored `config/demo.local.json`. Keep SSH ingress to the client's single IPv4 `/32`. A private subnet needs an existing route from the Mac and the required outbound access; setup adds no VPC, subnet, VPN, bastion or NAT gateway. The selected server is ARM `t4g.xlarge` in `us-east-1`.

Sensitive-path read, protected-path write and native IPv4 metadata TCP isolation still need completed native takes. The PTY check does not close those cases. The earlier command clip shows only the response-summary inspection, and the private-memory clip shows a conversation-assignment refusal rather than restricted human-role RBAC. See the [historical host scenarios](HOST-CONTROL-SCENARIOS.md) before repeating them. Keep GitHub Actions out of this project.
