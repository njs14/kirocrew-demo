# KiroCrew EC2 demo walkthrough

Use the nine-slide `output/kirocrew-ec2-demo.pptx` with `kirocrew-demo-live.html`. The brief takes about four minutes, followed by the live checks. Keep the accepted single endpoint-control box as the control map. The EC2 diagram shows the deployed subset.

The laptop desktop and remote Gateway connection are verified. The direct MCP/S3 probe also passed. Native Kiro CLI sign-in and the four model-driven tool turns are still pending. Present the native sequence as pending until a new native receipt passes. The original synthetic walkthrough remains in `evidence/accepted-before-ec2/WALKTHROUGH.md`.

## Before presenting

Run from `/Users/noahsutter/git-projects/kirocrew-demo`:

```sh
python3 scripts/demo-cloud.py status
ssh kirocrew-demo-admin 'systemctl is-active kirocrew-imds-guard kirocrew-demo kirocrew-mcp-demo'
lsof -nP -iTCP:5476 -sTCP:LISTEN
lsof -nP -iTCP:5599 -sTCP:LISTEN
```

Expect the exact demo instance and one inbound TCP 22 client `/32`, three active services, no local 5476 listener, and an SSH listener on local 5599. Open KiroCrew Nightly. Its window should show `[:5599]`, Gateway connected, agent `enforcement-demo` and project `/srv/kirocrew-demo/workspace`. Connection establishes which Gateway the client uses; it does not authenticate the coding backend.

If the instance is stopped or either public IP changed, use `python3 scripts/demo-cloud.py start --dry-run`, inspect the plan, then `start --apply`. The helper updates ingress through CloudFormation and preserves pinned SSH host-key checks. Operations details are in `infrastructure/RUNBOOK.md`.

Complete fresh backend sign-in before the audience arrives:

```sh
python3 scripts/ec2-login.py
```

Open the newly printed link, choose GitHub and keep the terminal running until it reports EC2 authentication. The helper checks its own callback tunnel before showing the link. Each attempt has a new URL. The earlier Builder ID device flow looped, and a subsequent GitHub callback attempt expired before completion. Existing local login stores are not copied. See `scripts/EC2-LOGIN.md`.

## Brief slides

| Slide | Presenter point | Time |
| --- | --- | --- |
| 1. KiroCrew on EC2 | The Mac is the client. The remote execution environment resides on EC2. | 20 sec |
| 2. One execution host | Locate Gateway, backend and workspace inside the single endpoint-control box. The reference map includes controls beyond this demo. | 30 sec |
| 3. CloudFormation deployment | Show the SSH `/32`, loopback listeners, separate MCP service and S3 paths. Open the interactive diagram for readable detail. | 40 sec |
| 4. Host identities | Crew cannot reach IMDS. The MCP service uses the instance role for fixed S3 operations. Root administers the host. | 30 sec |
| 5. Four calls | Identify Crew, MCP and IAM as separate decision points. A Crew denial must occur before MCP dispatch. | 30 sec |
| 6. Observed results | Show the actual direct-probe digest, MCP refusal and S3 403. Their receipt explicitly excludes native Crew proof. | 25 sec |
| 7. Installed baseline | Name the verified September 12 package, custom Linux repack and separate official Kiro CLI artifact. | 20 sec |
| 8. Live walkthrough | Switch to the native client and terminal. Keep the authentication/native-proof status visible. | 20 sec |
| 9. Cost and stopping | About $0.024 per running hour plus $1.92/month storage. Stop between demos; storage persists. | 25 sec |

## Live direct MCP and AWS check

This command uses the deployed probe as the MCP service user. Its bearer credential stays on EC2. It reads the benign allowed sentinel and attempts the two fixed denied operations:

```sh
ssh -T kirocrew-demo-admin 'sudo -u mcp-demo env DEMO_MCP_TOKEN_FILE=/etc/kirocrew-demo/mcp-token /opt/kirocrew-demo/mcp-venv/bin/python /opt/kirocrew-demo/mcp-enforcement/probe.py --expected-allowed-sha256 34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160'
```

Expected output has `kind: direct_mcp_service_probe`, `passed: true` and `native_crew_backend_verified: false`. Show the allowed object's 55 bytes and digest, `tool_grant_denied`, and S3 `AccessDenied` HTTP 403 with a fresh AWS request ID. The denied object exists and the deployed role has an explicit deny for that prefix. An STS error or missing object does not meet this test's acceptance criteria.

This route is available while backend authentication remains pending. It exercises real MCP and S3, without a model session or Crew callback. Use the Live evidence tab to keep that scope visible.

## Native backend sequence after authentication

The launcher uses the installed Nightly Python, whose aiohttp dependency is present. It inherits only the home and ordinary command path needed for the existing SSH configuration.

```sh
./native-demo.sh plan
./native-demo.sh run \
  --output evidence/native-backend/presenter-001 \
  --expected-allowed-sha256 34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160
```

Choose a new output directory for every run. The runner refuses to overwrite evidence. It creates one dedicated session and sends each of the four fixed prompts separately. All arguments are fixed except the unique trace ID.

For `read_allowed`, inspect the real pending card in the client and the runner's `pending.json`. Check the intended tool, exact trace input and native tool-call ID. Use a second terminal to approve only that card:

```sh
./native-demo.sh approve \
  --run-dir evidence/native-backend/presenter-001 \
  --request-id EXACT_PENDING_REQUEST_ID \
  --card-sha256 EXACT_PENDING_CARD_SHA256
```

The exact IDs appear in the pending output. Do not choose persistent trust or approve based only on a model-controlled title. The demo MCP service exposes four bounded tools; approve only the requested fixed operation. The runner rejects hidden or additional arguments.

| Turn | Expected native observation | Independent service evidence |
| --- | --- | --- |
| `read_allowed` | One reviewed approval, then the matching tool result | Matching trace and invocation ID; 55-byte object digest and AWS request ID |
| `crew_denied` | Crew automatically blocks before an approval card | Native `hook_deny` plus no arrival in a complete healthy MCP audit interval |
| `mcp_denied` | One reviewed approval lets the call reach MCP | MCP returns `tool_grant_denied`; no AWS dispatch for that trace |
| `iam_denied` | One reviewed approval lets the call reach S3 | Matching trace/invocation; S3 `AccessDenied` 403 and AWS request ID |

If the Crew-denied turn produces an approval card, the runner rejects it and fails the run. That manual rejection never counts as proof of Crew's configured deny. A missing audit interval also fails the evidence check.

The runner checks the SEL integrity chain, backend executable/CWD on EC2, actual callback IDs and MCP/AWS correlations. This nightly's Crew-denial SEL record lacks a direct trace ID, so that join uses the dedicated session and isolated turn interval. Do not describe it as a direct SEL-to-trace identifier match. An authenticated model response alone does not establish every L0–L5 control or an effective sandbox escape boundary.

Detailed runner instructions are in `scripts/native-backend-demo.README.md`. Native acceptance is complete only when the run's `receipt.json` reports success. Update deck/viewer status and final artifact receipts from that result.

## Close the demo

Finish active work, then use:

```sh
python3 scripts/demo-cloud.py stop --dry-run
python3 scripts/demo-cloud.py stop --apply
```

This stops EC2 and the local forwarding service. It preserves EBS state and does not turn the local Gateway on. Use the separate local-client rollback procedure if returning to local mode. The S3 bucket and policy survive stack deletion. Full cleanup instructions identify the exact resources in `infrastructure/RUNBOOK.md`.
