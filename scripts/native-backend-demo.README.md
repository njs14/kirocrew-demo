# Native EC2 backend evidence runner

`./native-demo.sh plan` is offline. `run` starts an actual Kiro CLI session through the EC2 Gateway and makes the four fixed MCP/S3 requests. Do not run it until the operator has completed a fresh Kiro CLI login on EC2. It does not copy the Mac's login state, provision infrastructure, change IAM or start services.

The runner is intended for the operator's Mac, using the existing local SSH tunnel to `localhost:5599`. The repository's `native-demo.sh` launcher uses Python 3.12 from the installed KiroCrew Nightly app, where aiohttp 3.14.3 was verified. The system Python and bundled document runtime do not have aiohttp. The launcher clears inherited environment variables and supplies only the user's HOME, a system PATH and UTF-8 locale; it does not inherit AWS credentials or Python module overrides. `KIRO_DEMO_PYTHON` can select another Python 3.10+ runtime with aiohttp if the app path changes. Plan and approval commands require only the standard library.

The fixed session uses agent `enforcement-demo`, project `/srv/kirocrew-demo/workspace`, and four separate turns: `read_allowed`, `crew_denied`, `mcp_denied`, `iam_denied`. Each call has only its unique `trace_id`. The primary AWS MCP configured for the operator and this purpose-built enforcement MCP are distinct services.

Prerequisites:

- `kirocrew-demo-admin` SSH alias logs in as the existing `ubuntu` administrator. `/usr/local/bin/kirocrew-owner-token token --ttl 30m` must work. The root-owned management wrapper uses the administrator's existing sudo access to enter the verified Gateway mount namespace, then drops to `crew` before minting through the stock wrapper. No sudoers grant is added. Noninteractive sudo must also permit read-only `systemctl show`, `journalctl` and Python `/proc` inspection.
- `kirocrew-mcp-demo.service` is healthy and its current journal contains at least one record. Journald must retain the complete interval without dropping records.
- The fixture's expected SHA256 comes from the provisioning receipt. The existing denied fixture and deployed IAM policy receipts remain required for policy attribution.
- This is the dedicated demo Gateway. The runner refuses to start while another slot is running. Its explicit `mode:normal` request also deactivates any global YOLO override, as the nightly's native UI does.

On the ARM deployment, ordinary token minting through the `crew` SSH session remains refused by the Gateway's namespace guard. The runner therefore uses only `--admin-host` for management access; the obsolete `--ssh-host` option was removed. Keep the existing independent SSH tunnel and service hardening in place. Owner bootstrap authenticates this dashboard API client; it does not authenticate the coding backend. The user-requested plain Kiro CLI still requires its own fresh remote login. A Crew KAS GitHub sign-in card is not proof of plain Kiro CLI authentication.

Inspect the exact plan without making a connection:

```sh
./native-demo.sh plan
```

After remote authentication is complete, start a new private evidence directory. Replace the digest placeholder with the verified allowed fixture hash:

```sh
./native-demo.sh run \
  --output evidence/native-backend/NEW-RUN \
  --expected-allowed-sha256 VERIFIED_64_CHARACTER_SHA256
```

The runner waits on the native callback and prints the path to `pending.json`, the exact request ID, and the card digest. Inspect the complete pending file and native client card. It includes the expected tool/trace, actual sanitized input, native tool-call ID and related native event. The current nightly does not expose canonical server/tool identity on parameterized HTTP approval cards; a matching display title alone is not authority. Confirm that the call is the intended fixed MCP operation and that its argument is exactly the current trace. Hidden, missing or extra input bytes cannot be approved by this runner.

In a second terminal, submit the reviewed card's exact values:

```sh
./native-demo.sh approve \
  --run-dir evidence/native-backend/NEW-RUN \
  --request-id EXACT_PENDING_REQUEST_ID \
  --card-sha256 EXACT_PENDING_CARD_SHA256
```

Use `reject` instead of `approve` to refuse the pending call. Each command records one local operator decision; the running process validates it against its in-memory card and sends the native once-only response. It never grants persistent trust. Do not edit `pending.json` or write a decision file manually. Expired/mismatched approvals fail. The default turn deadline is 300 seconds, while the Gateway may enforce a shorter native approval deadline. If a card expires, let the run fail and use a new evidence directory.

The Crew-denied turn must be rejected by Crew before an interactive card appears. If a card appears, the runner rejects it for containment, stops its dedicated session and marks the proof failed. That manual refusal never counts as native Crew enforcement.

`receipt.json` is the final verdict. Per-turn files contain sanitized callback/transcript/SEL observations; the final receipt additionally joins them to the complete service journal and checks the SEL chain. Passing requires:

- One exact trace-bearing native tool-call ID per phase; approved phases bind the reviewed permission and tool result to that same ID.
- An interactive approval SEL event for each operator-approved request ID.
- Real backend output containing the same trace and service-generated invocation ID as the MCP audit, with correct tool/principal and expected outcome.
- Successful allowed-object digest; MCP refusal before AWS dispatch; S3 `AccessDenied` with HTTP 403 and request ID for IAM denial.
- A host-generated Crew blocked row with the exact trace, one native `hook_deny` SEL event and no matching service arrival, surrounded by successful positive controls and a stable healthy MCP service.
- A valid SEL chain and an EC2 `kiro-cli*` executable observed with the actual project CWD while a native approval was pending.

The Crew denial SEL does not contain a trace or tool-call ID. That phase is explicitly an isolated-session/turn correlation, not a direct SEL-to-trace join. Process snapshots show PID, parent PID, executable and CWD, without command arguments or environment. They establish remote backend placement but do not claim a Gateway API-supplied session-to-PID mapping.

Tokens and cookies stay in memory. Receipts redact auth data, URLs and email addresses in dictionary keys and values, including JSON nested inside permission metadata. Raw CLI output, headers, identity responses, process environments and full token URLs are never saved. Evidence directories are private and never overwritten. A failure saves obtainable partial evidence, attempts to stop only the dedicated slot, and returns a nonzero exit code. A failure to collect service logs is recorded as missing evidence rather than an absence-of-dispatch claim.

Implementation was checked offline before the first execution. An offline parser check is not evidence of native, MCP or AWS behavior.
