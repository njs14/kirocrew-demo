# Root-managed policy for the demo Gateway

This installer uses KiroCrew's consumed central-policy channel with a local,
root-protected file. The file and every ancestor must be root-owned and not
group/world writable. A dedicated systemd drop-in supplies
`KIROCREW_POLICY_URL=file:///etc/kirocrew-demo/security-policy.json`. The policy
is unsigned: integrity comes from those filesystem permissions and the protected
service definition, not a signature or an external fleet service.

The enforcement host is Linux ARM; Seatbelt is a macOS facility and is not the
server's sandbox. The policy requires KiroCrew's `cc` sandbox tier. It denies
YOLO, the exact `@aws-enforcement/crew_denied` MCP tool, a harmless command
marker, reads of the Crew account's `.aws` tree, and writes to the management,
systemd, package and agent trees. `read_allowed`, `mcp_denied` and `iam_denied`
remain permitted at this policy layer so the later MCP-grant and IAM boundaries
can still be demonstrated. Omitted scopes keep the product's other defaults.
The exact installed `credential-exfil-s3-cp` built-in pattern is also pinned,
which gives the Denied Commands UI a real managed rule. The installer extracts
that pattern from the inspected source AST and refuses a mismatch.

The installer sets only `dashboard.terminal.enabled=false` in ordinary Crew
configuration and keeps that file writable for MCP management. A separate
root-owned systemd `DevicePolicy=strict` allows only `/dev/null`, `/dev/zero`,
`/dev/full`, `/dev/random` and `/dev/urandom`, with read/write access. No PTY
device is allowed. The UI flag can be edited by the owner; the OS device policy
is its independent backstop. Verify PTY refusal inside the actual Gateway
cgroup and check a fresh native Kiro CLI turn before claiming either outcome.
The Linux `cc` tier leaves SSH available and exposes `.aws/config`; do not label
it as complete credential or SSH isolation.

The policy is a floor for this managed Gateway. A host administrator with root
can replace it or change the service; that is the management boundary. This
setup does not enroll the Mac in MDM, change its local OS sandbox, or create a
Kiro organization MCP registry. The existing owner-authenticated dashboard and
editable configuration remain separate from the root-owned enterprise ceiling.

## Install and activate

Use the explicit deployment config and verified SSH host key from
[RUNTIME.md](../../docs/RUNTIME.md). The remote Python must be the installed
KiroCrew environment. All receipts below are new local output paths; keep them
outside a public export until reviewed. The scripts print bounded JSON without
credential bytes. They do not write those local receipt files themselves.

```sh
python3 scripts/manage-enterprise-policy.py plan --config /path/to/demo.json > /path/to/policy-plan.json
python3 scripts/manage-enterprise-policy.py apply --apply --config /path/to/demo.json --receipt /path/to/policy-plan.json > /path/to/policy-install.json
```

`plan` and `preflight` are aliases for the same read-only operation. They inspect
the selected machine, configured service, package source hashes, approval state
and destinations, and run the installed policy parser against the rendered
document. Review the returned policy and impact before apply. Apply requires
that exact plan, refuses existing destinations and preserves unrelated config,
profiles and systemd drop-ins. It writes the policy, dedicated drop-in and a
root-only manifest; the root-only before receipt records that the destinations
were absent. A separate root-only full configuration backup remains on the host;
the terminal patch takes the product's config lock and preserves ownership and
permissions. It does **not** restart or hot-activate the policy.

Before activation, finish or stop in-flight native turns. Activation interrupts
the Gateway connection and restarts exactly the configured service:

```sh
python3 scripts/manage-enterprise-policy.py activate --apply --config /path/to/demo.json --receipt /path/to/policy-install.json > /path/to/policy-activation.json
python3 scripts/manage-enterprise-policy.py verify --config /path/to/demo.json --receipt /path/to/policy-install.json > /path/to/policy-verification.json
```

Verification confirms protected bytes, service configuration and the running
process's policy environment. It does not
claim native enforcement or a healthy authenticated backend. Reconnect the Mac,
confirm the live Governance page shows the policy, check Kiro CLI sign-in, and
use a new native session for the allowed read and the exact managed deny. Bind
the native request/result to fresh server evidence. Only after the floor is
loaded and verified may the operator remove the exact duplicate mutable
`auto_deny_tools` entry for `@aws-enforcement/crew_denied`; this helper deliberately
does not edit it. Retain that edit's before/after receipt separately.

The command marker is `KIROCREW_MANAGED_COMMAND_CONTROL`. It is harmless if a
mistake lets it execute; a model's predicted refusal is not a policy result.

## Narrower profile example

`reviewer-profile.example.json` shows an optional user/profile restriction that
additionally denies `@aws-enforcement/iam_denied`. It is not installed or bound
automatically, because that would suppress the IAM example. Inspect the actual
profile management UI and bind it only for a separate profile demonstration.
The enterprise policy remains authoritative if a user deletes or loosens such
a profile.

## Rollback and subsequent updates

```sh
python3 scripts/manage-enterprise-policy.py rollback --apply --config /path/to/demo.json --receipt /path/to/policy-install.json > /path/to/policy-rollback.json
```

Rollback validates the original install, source and machine bindings and refuses
any changed managed file. It removes only the two installed files and manifest,
restores only the original terminal flag if its current value is still false,
retains the root-only backups, reloads systemd and restarts the named
Gateway. It does not restore a mutable hook that was later removed manually;
restore that exact reviewed hook first if the demonstration needs its previous
configuration. Empty dedicated directories may remain. The retained backup is
evidence, not an active policy. Do not delete unrelated files to make rollback
pass.

The tool intentionally does not overwrite an existing managed policy in place.
For a new candidate, validate/review the new document, preserve the prior
receipt, then perform a bounded administrator-managed update or roll back the
prior installation and create a fresh plan. A service restart or native failure
is not permission to weaken the floor; report it and diagnose the affected
control before changing the policy.
