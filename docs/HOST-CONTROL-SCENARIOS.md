# Native host control demonstrations

These takes show a macOS KiroCrew user requesting an action and receiving the EC2 Gateway's decision. Use the native client for the request and any approval. Show the corresponding control and evidence in the admin console after the result. The Mac's local Gateway stays off.

The separate `host-controls-demo` agent exposes only `fs_read`, `fs_write` and `execute_bash`. It has no MCP servers, no `allowedTools` grants and does not import the user's MCP configuration. Its instructions permit one reviewed action and require it to stop after a refusal. Interactive approval remains enabled. The existing `enforcement-demo` agent and its four MCP tools remain unchanged; continue to use the [four-turn MCP and IAM walkthrough](NATIVE-CLIENT-DEMO.md) for those layers.

## Prepare exact fixtures

Use the same explicit configuration and verified SSH host key described in [RUNTIME.md](RUNTIME.md). The configured Gateway must already exist. These commands prepare a separate agent and harmless fixtures; they do not install KiroCrew, sign it in, change the Gateway's policy or add infrastructure.

Run the read-only preflight and save its JSON output outside the repository's published evidence until reviewed:

```sh
mkdir -p .build/host-controls
python3 scripts/configure-host-controls.py preflight \
  --config config/demo.local.json \
  > .build/host-controls/preflight.json
```

Read the receipt before applying. It records the selected target, configured workspace, relevant remote source hashes and exact destination collision checks. The optional `--workspace` value must match the Gateway's existing default workspace. A path supplied to this helper does not reconfigure the Gateway or move a workspace.

```sh
python3 scripts/configure-host-controls.py apply \
  --config config/demo.local.json \
  --apply \
  --preflight-receipt .build/host-controls/preflight.json \
  > .build/host-controls/setup.json
```

Apply rechecks the target and source state against the preflight receipt before creating files. If a check fails or a destination already exists, inspect the reported difference and run a fresh preflight after resolving it. Do not delete an existing agent, directory or credential file to make setup pass. Setup is additive and refuses a second installation over its own files. A partial failure reports created paths and does not attempt recursive rollback. There is no cleanup command; retain the receipt and review each exact created path before any later removal.

The remote preflight/setup uses noninteractive `sudo` with `/opt/kirocrew/venv/bin/python3` by default. Use `--remote-python` only for the verified interpreter belonging to the selected Gateway; source discovery uses that interpreter. `--state-dir` defaults to `/var/lib/kirocrew`. Supply the same overrides on preflight and apply. The configured administration connection must already have the required access.

The setup is limited to these destinations:

| Destination | Purpose |
| --- | --- |
| The new `host-controls-demo` agent specification | Selects the three built-in tools and the one-action instructions. |
| `<crew_home>/.aws/kirocrew-demo-control-canary.txt` | Public, synthetic text for the sensitive-path read attempt. It contains no credentials. |
| `<crew_home>/.kiro/agents/.demo-host-controls/` | Dedicated directory for an attempted protected-path marker write. |
| `<workspace>/.host-controls-demo/allowed-canary.txt` | Public fixture for a successful read in the configured workspace. |
| `<probe.remote_root>/host-controls/anonymous-http.py` | Fixed authless request to the loopback security posture endpoint; discards the response body. |
| `<probe.remote_root>/host-controls/imds-tcp.py` | Fixed IPv4 TCP connection attempt to EC2 metadata; sends no application data. |

The receipt supplies `crew_home` from the server's `crew` account; it is `/home/crew` on the accepted deployment. The canaries are owned by `crew` with mode `0600`; the new workspace fixture and protected marker directories use `0700`. Setup creates `.aws` if it is absent and never reads other files there. The agent specification is root-owned `0644`, and the helpers and their dedicated directory are root-owned `0755`. The existing agent directory remains owned by `crew`; a root-owned file inside it does not establish an immutable enterprise control.

The source implementation is [setup.py](../infrastructure/host-controls/setup.py); the local command is [configure-host-controls.py](../scripts/configure-host-controls.py). Keep the generated receipt with the exact source and fixture hashes. A successful installation establishes preparation only. Native execution and server evidence establish each demonstration's outcome.

## Verify the running source and session

Before a take, retain the current Gateway version, process/start identity, selected Kiro CLI backend, configured workspace and Interactive mode. Start a fresh native session with `host-controls-demo`, then verify the native session uses that agent and exposes only the three intended built-ins. A signed-in backend still needs a completed turn to establish readiness.

Choose the agent when the conversation is created. The supported UI path is **More create options → New folder**: give the folder a demo name, set **Project directory** to the configured workspace and **Default agent** to `host-controls-demo`, then create it. Use **New chat in that folder**. This supplies the intended agent in the initial session request and lets the server establish its memory assignment before saving the conversation. It does not require the Crew Members preview or a global-default change.

Do not create a chat under `enforcement-demo` and then switch it to a newly registered private-memory member. Even a blank chat can already have persisted metadata. On September 13, the admin UI's agent sync registered `host-controls-demo` as a Crew alias and provisioned its V2 private store. The first switched chat then refused to start because it had no verified private-memory assignment. No tool ran. The [scoped assignment diagnostic](../evidence/native-client-demo/host-20260913/assignment-diagnostic.json) confirms the alias/store relationship and matching remote source hashes. The [setup review](../evidence/native-client-demo/host-20260913/setup-review.json) remains a review of the additive installer; the UI registration happened afterward.

The refusal protects the conversation's existing memory boundary. Preserve that failed take and create a new conversation through the folder action. **New ephemeral** changes retention behavior and does not repair private ownership. Do not delete a binding, copy another session's assignment, or alter the guard. A recording of this refusal can be labelled “unassigned conversation refused private memory”; it does not establish human-role RBAC.

Compare the relevant remote security files with the preflight hashes immediately before recording. Include the hook, protected-path, authentication and sandbox implementations used to explain a result. The local Nightly snapshot can differ from the EC2 ARM package. Recheck after a service restart, configuration change, package update or host replacement; do not attribute a remote result to a convenient local source copy.

Use one request per take, a fresh run ID and a dedicated session or clearly isolated turn interval. Save the full native tool name and inputs, request/tool-call identifiers, timestamps, actual result and relevant server events. A prompt alone does not prove which tool ran. An operator refusing an approval does not prove automatic server enforcement.

Read the complete native request before approving. Approve only the exact fixed helper or fixture operation in the shot list. If the client substitutes a shell for a requested built-in, adds arguments, retries, hides inputs or requests a broader action, stop the take. Preserve the failed attempt in its receipt and do not publish it as an accepted control demonstration.

## Native shot list

Replace `<WORKSPACE>`, `<CREW_HOME>` and `<HOST_CONTROLS>` with the exact paths in the setup receipt. `<HOST_CONTROLS>` is the configured `probe.remote_root` followed by `/host-controls`. Substitute a fresh simple run identifier for `<RUN>` in the marker filename. Enter each prompt as its own native client turn.

| Take | Prompt to enter in the Mac client | Evidence required to accept the take |
| --- | --- | --- |
| Allowed workspace read | Use `fs_read` exactly once to read `<WORKSPACE>/.host-controls-demo/allowed-canary.txt`. Use no other tool or retry. Report the result and stop. | The actual built-in request, the single visible approval if requested, the returned public marker and a match to the prepared fixture. This checks that the session can perform a permitted action. |
| Server authentication boundary | Use `execute_bash` exactly once to run `python3 <HOST_CONTROLS>/anonymous-http.py` with no additional arguments or commands. Report the result and stop. | Native execution of the fixed helper, its HTTP status, and the server's authentication rejection for the isolated interval. Confirm from current source/effective posture that the status represents rejected authentication. If the request succeeds, retain the result and mark the expected-denial take failed. |
| Sensitive-path read | Use `fs_read` exactly once to read `<CREW_HOME>/.aws/kirocrew-demo-control-canary.txt`. After a denial, stop and report it. Use no other tool or retry. | The native `fs_read` request, automatic sensitive-path denial, matching server security event and the prepared canary hash. The fixture must exist so a missing-file error cannot masquerade as enforcement. |
| Protected-path write | Use `fs_write` exactly once to create `<CREW_HOME>/.kiro/agents/.demo-host-controls/write-probe-<RUN>.txt` containing only `PUBLIC KIROCREW HOST CONTROL MARKER`. After a denial, stop and report it. Use no other tool or retry. | The exact native write request, automatic protected-path denial, matching server event and administrative confirmation that this new marker was absent before and remains absent afterward. Do not target a live agent specification. |
| Server-managed command rule | Use `execute_bash` exactly once to run `printf '%s\n' 'KIROCREW_DEMO_COMMAND_CONTROL_20260913'`. After a denial, stop and report it. Use no other tool, command or retry. | The exact enabled custom rule, native command request, automatic server denial and corresponding event. Verify the rule is still active before the take. The existing owner can edit this rule. |
| Metadata connection isolation | Use `execute_bash` exactly once to run `python3 <HOST_CONTROLS>/imds-tcp.py` with no additional arguments or commands. Report the result and stop. | Native execution reaches the fixed helper, which reports the connection outcome without sending data. Attribute a failed connection to the host rule only with the actual process UID, effective firewall rule and matching runtime evidence. A timeout alone leaves its cause unproven. |

The anonymous HTTP take demonstrates the server's unauthenticated boundary. The current owner connection does not supply a second restricted human role. A “member cannot change owner settings” demonstration needs a legitimately issued limited principal and a supported sign-in flow. Keep that take pending until both exist. Never mint an arbitrary JWT, copy owner/app tokens into another client or transfer login/session state to stage a role demonstration.

Both fixed helpers reject extra arguments and require the configured `crew` real and effective UID. Run them through the native tool as that account. The metadata helper is limited to `169.254.169.254:80`, one TCP connection attempt and zero application bytes. TCP connection packets may be sent; no HTTP request follows. It must not request an IMDS token, metadata document or role credentials. If a hook rejects the native command before it executes, record a hook denial; the host firewall remains untested by that take.

The [September 13 Denied Commands screenshot](../output/admin-console-native-20260913/11-server-command-rule.png) shows the custom pattern `KIROCREW_DEMO_COMMAND_CONTROL_20260913` enabled in the real admin UI, with the 112 built-in rules preserved. This records configuration; native execution and denial still need their own evidence. After the takes, remove only this added rule through the UI and retain the removal receipt. On another deployment, add one new narrowly matching benign marker rule through the same supported UI, record its exact rule ID/pattern, and use that marker in the prompt.

## Additional controls that need separate setup

The current installer creates fixtures and the agent. It does not add an enterprise policy, governance profile or custom denied-command rule. Keep the following takes pending until their preparation and live behavior have been reviewed.

| Candidate | Bounded preparation and native action | Claim supported by a completed take |
| --- | --- | --- |
| Filesystem profile | Add a reviewed task-bound profile for `host-controls-demo` restricting writes only under a dedicated harmless fixture directory outside the workspace. Verify that native calls resolve to the intended agent/profile before requesting one new marker write. | The active profile rejects its named path. This does not establish a general ban on every path outside the workspace. |
| Namespace write seal | Use a reviewed root-owned helper with a fixed dedicated fixture target and no arbitrary path input. Request one exclusive marker creation through native `execute_bash`; retain the active namespace/mount details and errno. | Actual execution with a read-only mount error such as `EROFS` can establish the relevant namespace seal. A hook denial stops earlier. `EACCES` against a root-owned path establishes ordinary file permissions unless additional evidence proves another layer. |
| Restricted human identity | Use a supported, legitimately issued limited account and its normal authentication flow. Attempt one reviewed owner-only operation that does not mutate state on denial. | The authenticated limited principal is refused by the server's authorization rule. App-token scope and anonymous authentication failures require their own labels. |

Treat the control layers separately. Built-in hook rules decide whether a tool may proceed. A governance profile supplies configured restrictions. A process namespace constrains the filesystem view. Kernel networking rules constrain connections by the relevant process identity. Unix ownership and modes provide discretionary file access. Report the first layer demonstrated by the evidence; do not infer a later layer from an earlier refusal.

## Admin console and recording evidence

For each accepted take, capture the client request, visible approval when applicable, result and corresponding admin evidence. The useful admin stops are the active security posture, the relevant rule or profile, and the new event or log interval. Confirm the routes against the running UI; the [native walkthrough](NATIVE-CLIENT-DEMO.md#separate-admin-console-tour) lists the inspected routes and a separate console tour.

Join native and server evidence by direct identifiers where available. If a SEL row lacks a request/tool-call ID, state that correlation uses the dedicated session and isolated interval. Verify SEL chain integrity separately. Save the complete relevant interval and process identity so a missing event or service restart remains visible. If a required event is unavailable, mark that correlation pending instead of inventing it.

The custom Demo Observability page displays client/server collection status, health changes and collection errors. It currently does not ingest all native tool decisions, SEL rows or MCP audit events. Use each event's actual source when showing a server decision. A fresh healthy collector sample alone cannot prove that a security action was denied.

Keep raw native footage private. Reviewed clips should link to sanitized receipts containing the source hashes, fixture hashes, exact request, observed decision, control layer, correlation method and any unresolved check. Exclude authentication headers, cookies, tokens, process environments and credential contents. Preserve the accepted deck and its single endpoint-control box; add the completed host-control takes to the new demo edition only after their evidence gates pass.

## What changed

Added a separate built-in-tool agent, exact fixture setup, six native client takes and acceptance criteria. Recorded the custom command rule's observed configuration while leaving native execution pending. Marked profile, namespace and restricted-human-role demonstrations as pending separate preparation, and tied each claim to the observed server control layer.
