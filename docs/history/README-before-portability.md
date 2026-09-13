# KiroCrew ARM and observability demo

The Mac runs the desktop client with its local Gateway off. The active remote host is now an ARM `t4g.xlarge` in `us-east-1`: 4 vCPU, 16 GiB RAM and 40 GiB encrypted gp3 storage. It runs the Crew Gateway, remote workspace, installed Kiro CLI backend and a separate MCP service. The original x86 host is stopped and retained for rollback. Fresh cloud verification confirms the stack is `UPDATE_COMPLETE` and the only inbound rule is TCP 22 from `24.60.107.229/32`.

The remote desktop connection, native Gateway metrics and custom client/server telemetry are live. Demo Observability shows both sources inside the owner dashboard. A controlled desktop quit and relaunch produced client warning/recovery events while the EC2 Gateway continued running. The ARM direct MCP probe passed caller authentication, allowed S3 access, MCP grant denial and IAM denial.

Kiro CLI is selected for new sessions, but its separate sign-in is still incomplete. The native log records an ACP startup failure because the CLI is not logged in. The GitHub card reports KAS identity and does not establish CLI authentication. Native tool approvals, Crew denial, SEL correlation and sandbox execution remain pending.

- [ARM and observability deck](output/kirocrew-arm-observability-demo.pptx)
- [Brief slides to live demo](WALKTHROUGH.md)
- [Admin console tour with 13 captured screens](output/kirocrew-admin-walkthrough.html)
- [Admin findings and remaining gaps](output/kirocrew-admin-findings.md)
- [ARM architecture](kirocrew-arm-live.html) and [observability flow](kirocrew-arm-observability.html)
- [Current ARM cloud verification](evidence/aws/arm-20260913/final-cloud-verification.json)
- [ARM direct MCP probe](evidence/aws/arm-20260913/mcp-live-receipt.json)
- [Latest documented MCP command rehearsal](evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json)
- [Client runtime evidence](evidence/aws/arm-20260913/client-runtime-receipt.json)
- [Observability runtime evidence](evidence/aws/arm-20260913/observability-runtime-receipt.json)
- [Deployment and evidence notes](kirocrew-ec2-notes.md)
- [Cloud operations](infrastructure/RUNBOOK.md)
- [CloudFormation template](infrastructure/ec2-demo.json)
- [Current handoff](HANDOFF.md)

Run `python3 scripts/demo-cloud.py status`, open KiroCrew Nightly on the remote demo, then follow the walkthrough from Settings → Overview to Developer → Telemetry and Apps → Demo Observability. Native metrics flush every 10 seconds with seven-day retention and a 64 MiB retention target; OTLP export and anonymous product reporting are off. The custom collectors run every 60 seconds and retain 240 samples per source and 200 fixed collection events locally on EC2.

The latest CLI login ended without an authenticated account, and its callback listeners were cleaned up. When ready to complete sign-in, run `python3 scripts/ec2-login.py` for a fresh URL and keep the terminal open until it confirms the EC2 CLI result. After authentication, use `./native-demo.sh plan` and follow the four native calls. [Latest login outcome](evidence/aws/arm-20260913/native-cli-login-outcome.json)

The Mac runs Nightly `0.7.0-nightly.20260913t061222`; EC2 retains the verified September 12 custom ARM repack. [Client baseline](evidence/nightly/client-20260913-verification.json)

The ARM host costs $0.1344 per running hour plus $0.005 per public IPv4 hour; its 40 GiB gp3 volume costs $3.20/month. The stopped x86 host adds $1.92/month for its retained 24 GiB volume. At 730 running hours the combined base is about $106.88/month, before model use, S3, transfer, telemetry and taxes. Stop ARM between demos with the reviewed lifecycle helper; both volumes remain billed while stopped.

The endpoint-control reference remains one box. The original visual, synthetic deck and reviewed nine-slide x86 deck remain historical artifacts. The new ARM diagrams passed static validation and raster review; browser validation of those diagrams and the portable admin guide was blocked by the local-file access policy. Live owner-portal inspection passed separately.

Grok 4.6 and Opus 5 reviewed all 12 ARM candidate images and returned CHANGES REQUIRED. The final deck incorporates the [accepted revisions](evidence/slides/kirocrew-arm-observability-demo/council-incorporation.json), followed by the [no-ai-slop edit](evidence/slides/kirocrew-arm-observability-demo/no-ai-slop.md). [Final artifact checks](evidence/slides/kirocrew-arm-observability-demo/finalization.json) and [author visual review](evidence/slides/kirocrew-arm-observability-demo/visual-review.json) passed. The council verdict covers the frozen candidate; it is not approval of the final output.
