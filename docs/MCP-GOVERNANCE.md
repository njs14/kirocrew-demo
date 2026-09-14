# MCP governance in the user's KiroCrew UI

The server's managed policy denies `@aws-enforcement/crew_denied`. The same MCP server remains available to the user, including its permitted `read_allowed` tool. A local visibility toggle does not remove the server policy.

This demonstration uses Crew's policy ceiling and the existing Kiro CLI backend. It does not claim enterprise identity-provider enrollment or Kiro CLI's separate enterprise MCP registry.

## Set up the UI entry

First install and activate the root-managed policy with [the policy lifecycle](../infrastructure/enterprise-policy/OPERATIONS.md). The Gateway must expose an active file-distributed policy with fail-closed behavior before this helper proceeds. The owner helper and original `enforcement-demo` agent must already be installed by the runtime setup.

From the project root, select the deployment explicitly:

```sh
mkdir -p .build/mcp-management
python3 scripts/manage-demo-mcp.py plan --config config/demo.local.json \
  --retire-mutable-deny > .build/mcp-management/plan.json
python3 scripts/manage-demo-mcp.py apply --config config/demo.local.json \
  --retire-mutable-deny --restart-gateway --apply \
  --plan-receipt .build/mcp-management/plan.json
python3 scripts/manage-demo-mcp.py verify --config config/demo.local.json
```

Review a successful plan before applying it. It binds the selected AWS account/stack, pinned SSH target, Gateway process, source hashes, exact configuration hashes and managed-policy bytes. A changed configuration, process or source invalidates it. Take a new plan after investigating a stale-plan refusal.

The helper copies the existing fixture's transport through the supported `POST /api/mcp/custom` route with Crew scope enabled. Its MCP authorization header and a short-lived owner session stay in memory on EC2. Neither crosses to the Mac or enters the returned report. It verifies the Crew store, the generated `kirocrew.json` entry and the readable custom-server API, including the absence of a governed `autoApprove`/`allowedTools` exemption. Existing Kiro and Claude global configurations and the source agent must remain unchanged. A same-name collision is refused; the helper does not replace or re-enable a different entry.

Omit `--retire-mutable-deny` when registering the UI entry alone. Registration alone does not restart the Gateway. With retirement requested, the helper removes only the exact `hooks.auto_deny_tools` entry `@aws-enforcement/crew_denied` after rechecking the live policy. It preserves all other entries and fields, uses the product's config lock as the `crew` user, and writes a root-only backup of that one hook field under `/etc/kirocrew-demo/mcp-management/`. `--restart-gateway` acknowledges the required restart, which interrupts active sessions. The managed policy remains installed throughout the transition.

The optional path flags `--state-dir`, `--remote-python`, `--owner-helper` and `--service` support the corresponding runtime layout. Ports and SSH configuration come from the chosen project config. The default runtime is the project's dedicated EC2 service; this helper is not a general MCP importer.

## Present the user workflow

1. Open **Settings → Security → Governance** (`/settings/security/governance`). Show the active host policy and governed MCP scope. This page shows the policy source and counts; it does not expose the rule text or let the user edit the ceiling.
2. Open **Connections → MCP Servers** (`/capabilities?tab=mcp`). Find `aws-enforcement`, its Crew scope and its available tools. Expand the list. The installed build has local tool toggles, with staged Apply/Discard controls. It has no per-tool badge for a managed denial.
3. Start a fresh native KiroCrew conversation with the original Kiro CLI backend. The conversation's session options show the MCP servers and tools available to that session. Existing conversations may retain the tool list from startup; use a fresh one after setup.
4. Ask for one `read_allowed` fixture call with a unique trace ID and show the permitted result. Then ask for one `crew_denied` fixture call with a different trace ID. Stop after the denial; do not substitute another tool or route.
5. Show that the denied tool can remain visible in Connections. Visibility is the user's tool selection; execution remains subject to the managed server rule. Do not suggest an unimplemented lock badge exists, or that clicking a toggle itself proves enforcement.

Record the actual native denial and its policy reason. Correlate the native tool call with the Gateway SEL decision and the absence of MCP service dispatch for that trace. A setup report, a rule count, an assistant's refusal before a tool call, or the old mutable hook's denial is insufficient for that acceptance claim.

The older footage showing the mutable `auto_deny_tools` hook remains historical evidence of that earlier configuration. It should not be relabeled as a managed-policy demonstration.

## Failure and recovery

The helper reports a bounded error code rather than raw API or SSH output. On a failed apply, inspect its `mutation_may_have_started` flag, run `verify`, and inspect the exact target files before retrying. A server entry may have been registered successfully before a later verification or restart failed. A new plan recognizes an exact existing registration without replacing it.

If hook retirement needs to be undone, have the host administrator inspect the named root-only backup and restore only that exact field under the configuration lock, preserving subsequent unrelated changes, then restart the named Gateway. Do not copy a full historical config over the live one. Policy removal is a separate lifecycle operation with its own exact-installation receipt.

No setup command submits a native prompt or approval, signs in to a product, copies credentials between products, or claims a fresh enforcement recording has passed.
