# KiroCrew ARM: brief slides to live demo

Use the 12-slide [ARM and observability deck](output/kirocrew-arm-observability-demo.pptx). Cover slides 1–10 in about five minutes, pause on slide 11 for the live portal and MCP probe, then close with slide 12. The [admin console guide](output/kirocrew-admin-walkthrough.html) provides 13 captured screens and presenter cues. Keep the accepted single endpoint-control box as the control map.

The [final slide copy and speaker notes](output/kirocrew-arm-observability-demo-copy.md) include the accepted council changes and the subsequent no-ai-slop edit. [Finalization](evidence/slides/kirocrew-arm-observability-demo/finalization.json) and [author visual review](evidence/slides/kirocrew-arm-observability-demo/visual-review.json) passed; the council review remains bound to its earlier candidate.

The September 13 Mac client is connected to the September 12 custom ARM Gateway. Local Gateway is off. Native Gateway metrics, the custom Mac/EC2 observability page and the direct MCP/S3 probe passed their live checks. Standalone Kiro CLI is selected but still signed out; its native ACP startup failed. Keep native approval, Crew denial, SEL correlation and sandbox execution pending until a new native receipt passes. The [initial x86 walkthrough](WALKTHROUGH-EC2.md) and [original synthetic walkthrough](evidence/accepted-before-ec2/WALKTHROUGH.md) retain their historical scope.

## Before presenting

Run from `/Users/noahsutter/git-projects/kirocrew-demo`:

```sh
python3 scripts/demo-cloud.py status
ssh kirocrew-demo-admin 'systemctl is-active kirocrew-imds-guard kirocrew-demo kirocrew-mcp-demo'
ssh kirocrew-demo-admin 'systemctl is-active kirocrew-demo-observability.timer'
lsof -nP -iTCP:5476 -sTCP:LISTEN
lsof -nP -iTCP:5599 -sTCP:LISTEN
```

Expect active ARM instance `i-0fde6de3f0ea5a9d0`, one inbound TCP 22 rule from `24.60.107.229/32`, three active services, the active collector timer, no local 5476 listener and an SSH listener on 5599. Open KiroCrew Nightly and the remote demo. Confirm Gateway connected, agent `enforcement-demo` and project `/srv/kirocrew-demo/workspace`. The connected owner dashboard is available through the same tunnel at `http://localhost:5599`. Use the existing owner session; keep generated sign-in URLs and tokens out of captures.

Desktop owner bootstrap uses `kirocrew-demo-admin` and the reviewed `/usr/local/bin/kirocrew-owner-token` helper. The independent tunnel still uses `kirocrew-demo`. This supports owner refresh after relaunch without Crew sudo access or a Nightly patch. [Client runtime receipt](evidence/aws/arm-20260913/client-runtime-receipt.json)

If the instance is stopped or either public IP changed, use `python3 scripts/demo-cloud.py start --dry-run`, inspect the plan, then `start --apply`. The helper updates ingress through CloudFormation and preserves pinned SSH host-key checks. Operations details are in `infrastructure/RUNBOOK.md`.

The observability and direct MCP demonstration can proceed while CLI authentication is pending. The latest normal login ended without an authenticated account, and both callback listeners were cleaned up. [Latest login outcome](evidence/aws/arm-20260913/native-cli-login-outcome.json). When ready to complete sign-in, start a fresh attempt:

```sh
python3 scripts/ec2-login.py
```

Open that attempt's newly printed link, choose GitHub and keep the terminal running until it reports the EC2 CLI result. The helper checks its callback tunnel before showing the link. The dashboard's GitHub card reads the separate KAS identity store; it is not the CLI result. Existing local login stores are not copied. See [CLI sign-in instructions](scripts/EC2-LOGIN.md).

## Brief slides

| Slide | Presenter point | Time |
| --- | --- | --- |
| 1. KiroCrew on ARM | The Mac is the client. Gateway, backend installation and workspace reside on EC2. | 20 sec |
| 2. One execution host | Locate the single endpoint-control enclosure. Its reference map includes controls beyond this demo. | 25 sec |
| 3. ARM execution in us-east-1 | Show 4 vCPU, 16 GiB RAM, 40 GiB gp3, SSH `/32`, loopback listeners and the separate MCP service. | 35 sec |
| 4. Host identities and AWS credentials | Root administers the host. Crew's IPv4 metadata connection was denied; MCP uses the role for fixed S3 calls. | 30 sec |
| 5. Four calls, three denial boundaries | Separate Crew, MCP and IAM decisions. Native Crew denial remains pending. | 30 sec |
| 6. ARM: MCP and AWS results | Show the 55-byte digest, MCP refusal and S3 403. These are direct service results. | 25 sec |
| 7. Client and server nightly baselines | Mac is September 13; server retains the frozen September 12 custom repack. Idle capacity is not a session benchmark. | 25 sec |
| 8. Native Gateway telemetry | Native request, boot and process metrics are present. Completed-turn evidence remains empty. | 30 sec |
| 9. Client and server in Demo Observability | Name the custom App Kit page and its two collectors. | 30 sec |
| 10. Close the client; the server keeps running | Show the recorded desktop quit and recovery. Gateway process identity and server checks stayed unchanged. | 25 sec |
| 11. Desktop-to-EC2 walkthrough | Switch to the live portal, show the collector events, then run the direct MCP probe below. | 3–5 min |
| 12. Running cost and rollback | $0.1394 per running hour plus $5.12/month for both disks. Stop ARM between demos. | 30 sec |

The [ARM architecture](kirocrew-arm-live.html), [observability flow](kirocrew-arm-observability.html) and [slide diagram](kirocrew-arm-slide.html) passed static checks and raster review. Browser validation of these local HTML files and the portable admin guide was blocked by the browser file-access policy. Use the captured slide images and the live owner portal; do not claim responsive/export/HTML-interaction checks for these new files. [Diagram receipt](evidence/aws/archify-arm/council-delivery-receipt.json), [portal and guide browser receipt](evidence/admin-console/browser-receipt.json)

## Live owner portal

1. Open **Settings → Overview**, then **Developer → System → Performance**. Identify the remote ARM server and workspace. In Services, explain that the separate systemd MCP process is outside the Gateway's own MCP process count.
2. Open **Settings → Security**. Show Live Security Posture, Interactive approval and Governance Policy. These display configured controls; no enterprise policy is in effect. The six-hour auto-approve selection is a possible duration, not an active bypass.
3. Open **Developer → Agent Backend**, then **Developer → Logs**, filtered to `AcpRuntime dead`. Kiro CLI is selected, while its startup reports that it is not logged in. Explain the separate KAS GitHub card and retain the native gate.
4. Open **Settings → Privacy → Telemetry controls**, then **Developer → Telemetry**. Record metrics is on, product reporting is off, and no OTLP destination is configured. Native metrics flush every 10 seconds with seven-day retention and a 64 MiB retention target. Request/boot samples establish instrumentation; zero completed turns do not establish backend success.
5. Open **Apps → Demo Observability**. Confirm Client and Server sample times are current. Read Local Gateway off, desktop running, Gateway/MCP service state and loopback checks. The local SSH listener check establishes local TCP reachability; the connected dashboard provides separate application-level evidence. Mac CPU sums scheduler averages and can exceed 100%; server host CPU uses a one-second normalized sample.
6. Filter **Collection logs** by Client, then Server, then restore All. Show the stopped-client sample and warning at **14:44:42 UTC** and recovery sample at **14:49:34 UTC**. These are sample times, not exact quit/relaunch times. The runtime receipt records Gateway PID **4991** with the same **14:26:10 UTC** start identity throughout. A Current badge describes freshness even when desktop running is No.

The captured browser clocks show EDT (UTC−4); the receipts use UTC. The collection-event table contains the client transitions. Use the runtime receipt for the separate Gateway PID/start-time evidence.

Both collectors run every 60 seconds, retain 240 samples per source and share a 200-event limit. The page refreshes every 15 seconds and marks samples stale after three minutes. Collection logs contain fixed operational events, not raw application logs or native SEL records. The data remains on EC2 with root ownership and read-only Crew access. [Live observability receipt](evidence/aws/arm-20260913/observability-runtime-receipt.json)

The desktop-pause capture already demonstrates server independence. To repeat it, first finish active backend work, keep the owner browser and SSH tunnel open, quit only KiroCrew Nightly, and wait for the next client sample. Relaunch Nightly and verify owner reconnection and the recovery event. Leave the EC2 Gateway running throughout.

## Live direct MCP and AWS check

This command uses the deployed probe as the MCP service user. Its bearer credential stays on EC2. It reads the benign allowed sentinel and attempts the two fixed denied operations:

```sh
ssh -T kirocrew-demo-admin 'sudo -u mcp-demo env DEMO_MCP_TOKEN_FILE=/etc/kirocrew-demo/mcp-token /opt/kirocrew-demo/mcp-venv/bin/python /opt/kirocrew-demo/mcp-enforcement/probe.py --expected-allowed-sha256 34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160'
```

Expected output has `kind: direct_mcp_service_probe`, `passed: true` and `native_crew_backend_verified: false`. Show the allowed object's 55 bytes and digest, `tool_grant_denied`, and S3 `AccessDenied` HTTP 403 with a fresh AWS request ID. The denied object exists and the deployed role has an explicit deny for that prefix. An STS error or missing object does not meet this test's acceptance criteria.

This route is available while backend authentication remains pending. It exercises real MCP and S3 without a model session or Crew callback. Keep `native_crew_backend_verified: false` visible. The exact documented command passed again at **15:01:37 UTC**, after telemetry deployment. Its [latest rehearsal receipt](evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json) has fresh trace and AWS request IDs. The [14:07 ARM probe](evidence/aws/arm-20260913/mcp-live-receipt.json) remains the earlier baseline.

## Native backend sequence after authentication

Complete the standalone CLI's sign-in before this step and start a new Kiro CLI session. The launcher uses the installed Nightly Python, whose aiohttp dependency is present, with a clean environment retaining only the home and ordinary command path needed for SSH. It obtains owner access through the reviewed administrator helper and keeps token material in memory.

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

This stops ARM and the local forwarding service, preserves EBS state and leaves the local Gateway off. The original x86 host remains stopped. The Mac collector is independent; pause it with `/usr/bin/python3 scripts/demo-telemetry.py stop --apply` if no further uploads should run while EC2 is stopped. Resume it after cloud start with the helper's `setup --apply`. The runbook has separate controls for native metrics, both collectors and the App Kit backend, plus local-client rollback and exact retained-data cleanup. [Operations](infrastructure/RUNBOOK.md)
