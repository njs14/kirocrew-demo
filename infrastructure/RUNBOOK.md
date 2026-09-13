# KiroCrew EC2 demo operations

The Mac is the client. The Crew Gateway, installed Kiro CLI backend, workspace and demo MCP service run together on ARM EC2. The desktop has `runLocalGateway: false`; a local SSH tunnel forwards `127.0.0.1:5599` to the remote Gateway at `127.0.0.1:5476`. Native metrics and the custom client/server observability page are live. Kiro CLI authentication and a completed native session remain pending. The single endpoint-control enclosure still represents the remote execution host.

Use [demo-cloud.py](/Users/noahsutter/git-projects/kirocrew-demo/scripts/demo-cloud.py) to inspect, stop, start or refresh access to this existing deployment. It defaults to a dry run. Only `--apply` performs the selected operation. Python's standard library provides strict AWS JSON/IP validation and atomic configuration edits; the helper uses the installed AWS CLI and its existing credential chain.

## Deployment binding and evidence

The ARM cutover was freshly checked on September 13, 2026 at 14:22 UTC. CloudFormation is `UPDATE_COMPLETE`; ARM is running and the original x86 host is stopped. [Current cloud verification](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/final-cloud-verification.json) records exact instance and volume bindings. A [14:57 UTC network readback](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/final-network-readback.json) confirms the sole SSH rule still matches the client's current public IPv4 and no Gateway, MCP or app ingress was added. Run `status` again before operating; the public address below can change after stop/start.

| Item | Deployed value |
| --- | --- |
| Region / stack | `us-east-1` / `kirocrew-demo-20260913` |
| Active EC2 | `i-0fde6de3f0ea5a9d0`, `t4g.xlarge`, ARM64, 4 vCPU / 16 GiB |
| Active root volume | `vol-02a27fe0b4d1af5af`, 40 GiB encrypted gp3 |
| Public IPv4 at verification | `100.61.173.192` |
| Stopped rollback EC2 | `i-020eb373045b56586`, `t3a.small`, x86_64, 2 vCPU / 2 GiB; no public IPv4 |
| Retained rollback root volume | `vol-07fce30fb97a89ab9`, 24 GiB encrypted gp3 |
| Security group | `sg-08ac4789794115e39` |
| Verified inbound rule | TCP 22 from `24.60.107.229/32` only |
| Stack ingress parameter | `AllowedCidr` |
| Demo bucket | `kirocrew-demo-20260913-demobucket-pdjzgyu25xhb` |
| Crew SSH alias | `kirocrew-demo`, user `crew` |
| Administrator alias | `kirocrew-demo-admin`, user `ubuntu` |
| Active SSH host-key alias | `kirocrew-demo-arm-20260913` |
| Pinned host-key file | `~/.ssh/kirocrew-demo-known_hosts` |
| Tunnel LaunchAgent | `com.kirocrew.demo-tunnel` |
| Remote service units | `kirocrew-demo`, `kirocrew-mcp-demo`, `kirocrew-imds-guard` |
| Gateway / MCP listener | `127.0.0.1:5476` / `127.0.0.1:8001/mcp` |
| Observability app | Demo Observability `1.0.1`, Gateway-managed App Kit backend on `127.0.0.1:9102` |
| Collector schedules | `com.kirocrew.demo-observability` on Mac; `kirocrew-demo-observability.timer` on EC2; both every 60 seconds |
| Gateway home / state / workspace | `/home/crew` / `/var/lib/kirocrew` / `/srv/kirocrew-demo/workspace` |

The active host uses Ubuntu 24.04 ARM64 and a 40 GiB encrypted gp3 root volume. Both hosts use standard CPU credits. Standard mode avoids surplus CPU-credit charges but sustained work can exhaust credits and slow down. The original host remains CloudFormation-managed and stopped for rollback; routine helper operations target ARM only. There is no NAT gateway, load balancer or Elastic IP. HTTP 80 and HTTPS 443 egress remain permitted; HTTP supports Ubuntu package mirrors. AmazonProvidedDNS is handled by the VPC resolver and cannot be filtered by security groups. [AWS DNS behavior](https://docs.aws.amazon.com/en_en/vpc/latest/userguide/AmazonDNS-concepts.html)

ARM compute is **$0.1344 per running instance-hour**, plus **$0.005 per public IPv4 hour**. Its 40 GiB gp3 volume costs **$3.20/month**; the stopped x86 host's retained 24 GiB gp3 volume adds **$1.92/month**. At 730 running hours, ARM compute, IPv4 and storage total about **$104.96/month**, or **$106.88/month** including rollback storage, before S3, network transfer, model/backend use, telemetry and taxes. See [ARM compute pricing](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/price.json), [gp3 pricing](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/gp3-pricing.json) and [AWS IPv4 pricing](https://aws.amazon.com/vpc/pricing/). Stopping ARM releases its auto-assigned IPv4 and ends compute charges; the two EBS volumes together remain about **$5.12/month**, plus retained S3 usage. Stop between sessions. [AWS instance lifecycle and billing](https://docs.aws.amazon.com/us_en/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html)

## Read-only preflight

Run commands from the project directory:

```sh
cd /Users/noahsutter/git-projects/kirocrew-demo
python3 scripts/demo-cloud.py status
python3 scripts/demo-cloud.py start --dry-run
```

The helper verifies the AWS account, exact existing instance ID, project tags, security-group attachment and the single TCP 22 `/32` rule. It refuses to continue if the live ingress differs from the CloudFormation parameter. Use `--profile NAME` only for an already configured AWS CLI profile in this account. It never prints, exports or copies IAM keys.

`start` and `update-my-ip` discover the current public IPv4 through `https://checkip.amazonaws.com`. Discovery disables HTTP proxy environment settings; the result should match the egress path used by direct SSH. A VPN or split route can require `--client-ip YOUR_CURRENT_PUBLIC_IPV4`. That override accepts one public IPv4 address, then constructs `/32`; it cannot accept a broader CIDR.

For a completely offline rehearsal of the helper, use saved receipts and an explicit address:

```sh
python3 scripts/demo-cloud.py status --offline
python3 scripts/demo-cloud.py start --offline --dry-run --client-ip 24.60.107.229
python3 scripts/demo-cloud.py update-my-ip --offline --dry-run --client-ip 24.60.107.229
python3 scripts/demo-cloud.py stop --offline --dry-run
python3 scripts/demo-cloud.py cleanup-plan --offline
python3 scripts/demo-cloud.py local-client-rollback --offline --dry-run
```

Offline output is explicitly labeled as potentially stale and intentionally reads the initial x86 receipts; it does not verify ARM. `--offline --apply` is rejected. The original authoring checks covered all six offline actions, live x86 `status` and `start --dry-run`, plus mocked checks proving ingress completion precedes start and an ingress-update failure prevents start, SSH edits and tunnel restart. The fresh ARM cloud receipt above verifies current resource state. It does not establish an actual ARM stop/start, changed-IP recovery or rollback execution; those require their own operational verification when used.

## Start or recover after a public-IP change

```sh
python3 scripts/demo-cloud.py start --apply
```

The helper first refreshes and verifies `AllowedCidr` through CloudFormation using the existing template, existing capabilities and `UsePreviousValue` for every other parameter. A stopped host stays stopped until the ingress update succeeds, so it does not boot while the previous client IP remains authorized. The helper then starts the existing instance if needed, waits for EC2's `running` state, and obtains the current public IPv4 from EC2. It updates the one shared `HostName` for both SSH aliases, preserving all other SSH lines and the pinned host-key settings. Every changed local configuration file receives a timestamped, owner-readable backup before an atomic replacement. Finally, it starts or restarts the existing tunnel LaunchAgent.

EC2 normally assigns a new public IPv4 on stop/start. The EBS-backed host retains its SSH keys; the ARM `HostKeyAlias` allows strict checking across that address change. The separate ARM host identity and shared alias cutover are recorded in [ssh-cutover.json](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/ssh-cutover.json). The helper never uses `StrictHostKeyChecking=no`, deletes a known-hosts entry or trusts a newly scanned key. A host-key mismatch requires investigation through trusted AWS/SSM host evidence. [AWS stop/start behavior](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Stop_Start.html), [CloudFormation parameter updates](https://docs.aws.amazon.com/cli/latest/reference/cloudformation/update-stack.html)

The helper waits for EC2's state, not complete Gateway/backend readiness. The LaunchAgent retries the SSH connection while the host starts. Check the services and forwarding after it returns:

```sh
ssh kirocrew-demo-admin 'systemctl is-active kirocrew-imds-guard kirocrew-demo kirocrew-mcp-demo'
launchctl print gui/$(id -u)/com.kirocrew.demo-tunnel
curl --noproxy '*' --max-time 10 --silent --show-error --output /dev/null \
  --write-out 'Gateway HTTP status: %{http_code}\n' http://127.0.0.1:5599/
```

All three remote units should be `active`; the HTTP response establishes transport reachability only. Open KiroCrew Nightly and select the remote demo. Its local Gateway toggle should remain off. The configured `remoteHosts["5599"]` uses `kirocrew-demo-admin` and `/usr/local/bin/kirocrew-owner-token`. The separate SSH forwarding job still uses the unprivileged `kirocrew-demo` alias. The reviewed owner helper verifies the active Gateway process and its mount namespace, then drops from the existing administrator to `crew` for the stock owner-token operation. It adds no Crew sudo permission and changes no Nightly source. Keep generated owner URLs and tokens out of terminal captures and receipts. [Owner helper review](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/owner-bootstrap-review.json), [successful desktop reconnect](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/client-runtime-receipt.json)

If only the Mac's public IP changes while EC2 is running:

```sh
python3 scripts/demo-cloud.py update-my-ip --dry-run
python3 scripts/demo-cloud.py update-my-ip --apply
```

This replaces the existing `/32` through CloudFormation and waits for the completed update before refreshing the SSH target and tunnel. It does not add an extra ingress rule or directly mutate the security group outside CloudFormation. If the instance is stopped, it updates access without starting compute or the tunnel.

## Inspect or pause telemetry

Open the connected owner dashboard. **Settings → Privacy → Telemetry controls** records native Gateway metrics every 10 seconds, with seven-day retention and a 64 MiB retention target. Pruning protects active writers, so retained bytes can temporarily exceed that target. No OTLP endpoint is configured. Anonymous product reporting is off through both configuration and the environment opt-out. **Developer → Telemetry** shows native Gateway request, startup and process measurements. Its 14-day query window does not extend the configured retention, and empty turn charts do not establish a successful model session.

**Apps → Demo Observability** shows the separate custom collectors. The Mac sample covers Nightly desktop process CPU/RSS and local listener checks. The server sample covers host resources, Gateway/MCP main processes and loopback checks. Both run every 60 seconds. EC2 retains 240 samples per source and 200 fixed collection events, under a `root:crew` directory with mode `0750` and files with mode `0640`. Crew can read those files and cannot change them. No arbitrary logs, prompts, command arguments or credentials enter this collection schema. The app refreshes every 15 seconds and marks samples stale after 180 seconds. Read the health checks separately from the freshness badge.

The live receipt verifies both sources, app health HTTP 200, unsigned app data HTTP 401 and unauthenticated Gateway app access HTTP 403. The controlled Mac quit/relaunch produced a stopped-client sample at 14:44:42 UTC and recovery sample at 14:49:34 UTC. Those timestamps identify samples, not the exact UI actions. Gateway PID 4991 and its 14:26:10 UTC start identity stayed unchanged. This demonstrates client/server independence. [Runtime receipt](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/observability-runtime-receipt.json), [13-screen admin guide](/Users/noahsutter/git-projects/kirocrew-demo/output/kirocrew-admin-walkthrough.html)

To pause custom collection while leaving Gateway, MCP and the app running, use the same Mac Python interpreter used for setup:

```sh
/usr/bin/python3 scripts/demo-telemetry.py stop
/usr/bin/python3 scripts/demo-telemetry.py stop --apply
ssh kirocrew-demo-admin sudo systemctl disable --now kirocrew-demo-observability.timer
ssh kirocrew-demo-admin sudo systemctl stop kirocrew-demo-observability.service
```

The final command stops a sample already in progress. Stored samples remain. Resume the installed collectors with:

```sh
ssh kirocrew-demo-admin sudo systemctl enable --now kirocrew-demo-observability.timer
/usr/bin/python3 scripts/demo-telemetry.py setup
/usr/bin/python3 scripts/demo-telemetry.py setup --apply
```

The client helper uploads one valid sample before installing its schedule; omitting `--apply` produces a dry run. To pause native metrics, turn **Record metrics** off in the remote Privacy controls; turn it on to resume. To pause only the app backend, disable **Demo Observability** in the authenticated owner Apps management view, then enable that same installation to resume. These controls are independent. Keep the installed app and its generated secret; disabling it does not stop either collector. [Collector contract](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability-collector/README.md), [App Kit install and update contract](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability/APP-INSTALL.md)

For a newly prepared host, run initial demo configuration once. `configure-arm-services.sh` already calls `configure-demo.py`. After that step, run the reviewed [set-demo-telemetry.py](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/set-demo-telemetry.py) as root on EC2, then restart the Gateway once to load the settings. The installed copy is `/opt/kirocrew-demo/set-demo-telemetry.py`; it updates only the telemetry fields and preserves other configuration sections. Install the collectors before enabling the server timer or client uploads. Stage, install, trust only this app, and enable it through the owner App Kit operations in the linked contract. Verify backend health and an authenticated snapshot from both real collectors after activation.

Do not rerun initial configuration or deployment scripts over the live host, restore an old whole-config backup, or replace token files to reproduce telemetry. The telemetry setter enables metrics immediately and is not a pause command. Use the controls above for live pause/resume. These custom samples and events are local operational data; they do not provide durable external SEL retention or native tool-enforcement proof.

## Stop between demonstrations

Finish active backend work, save the session and close its remote view before stopping:

```sh
python3 scripts/demo-cloud.py stop --dry-run
python3 scripts/demo-cloud.py stop --apply
```

The helper unloads the local tunnel and requests an ordinary stop of active ARM instance `i-0fde6de3f0ea5a9d0` with OS shutdown. It does not force-stop, terminate or delete storage. Crew state, any subsequently completed backend authentication and workspace files remain on EBS. Use `start --apply` to resume ARM. The old x86 instance stays stopped; this helper does not reactivate it. Stopping a remote instance does not turn the local Gateway on. Pause the Mac collector separately if no uploads should run while EC2 is stopped; the cloud helper does not manage that job. An enabled server timer resumes when EC2 boots.

If an AWS operation fails after the tunnel was unloaded, inspect `status`; use `start --apply` to reconcile the running instance's address/access and restore the tunnel. If CloudFormation enters a rollback or failed state, inspect its events rather than editing the security group manually:

```sh
aws --region us-east-1 cloudformation describe-stack-events \
  --stack-name kirocrew-demo-20260913 --max-items 20
```

## Return the desktop to its local Gateway

Quit KiroCrew Nightly first so it cannot overwrite the configuration while exiting. Then run:

```sh
python3 scripts/demo-cloud.py local-client-rollback --dry-run
python3 scripts/demo-cloud.py local-client-rollback --apply
```

This unloads the tunnel, backs up `~/Library/Application Support/kirocrew-desktop-nightly/config.json`, sets `runLocalGateway` to `true`, and removes only `remoteHosts["5599"]` when its host/wrapper pair matches either the original Crew configuration or the current administrator owner helper. Crossed or unrelated pairs are refused. Other settings and remote hosts are preserved. Reopen the desktop and confirm the local Gateway starts. This operation does not stop EC2 or the custom Mac collector; pause those separately if the remote demo is no longer needed. [Rollback guard update](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/lifecycle-owner-update.json)

The initial complete client backup is recorded in [client-config-change.json](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/client-config-change.json). Use it for comparison rather than blindly restoring the entire file over later settings. The helper's timestamped backups support reversing its narrow edits. Existing SSH aliases and pinned keys remain available for administration and a future remote setup.

## Full cleanup

Cleanup destroys both the ARM and stopped x86 hosts and both root volumes, including any backend sign-in state, sessions and workspace data. The old host is retained for rollback within the live stack; it does not have a CloudFormation retention policy. Cleanup has no automatic helper action. Obtain explicit authorization for that deletion when the demo is retired, inspect the following plan, and export only the needed non-secret workspace/SEL evidence first:

```sh
python3 scripts/demo-cloud.py cleanup-plan
```

After approval and any required exports, perform local-client rollback above, then delete this exact stack. The complete StackId ARN binds the account and deployment identity, so another account's stack with the same name is not selected:

```sh
aws --region us-east-1 cloudformation delete-stack \
  --stack-name arn:aws:cloudformation:us-east-1:770132776059:stack/kirocrew-demo-20260913/72ef8b10-af28-11f1-b3b3-0affd5886c7b
aws --region us-east-1 cloudformation wait stack-delete-complete \
  --stack-name arn:aws:cloudformation:us-east-1:770132776059:stack/kirocrew-demo-20260913/72ef8b10-af28-11f1-b3b3-0affd5886c7b
```

CloudFormation removes both instances, their root EBS volumes, the shared security group, instance profile and instance role. The demo bucket and its TLS-only bucket policy have `DeletionPolicy: Retain` and remain. They continue to exist outside the deleted stack. [AWS retention behavior](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-attribute-deletionpolicy.html)

Inspect the retained bucket before deciding whether to delete it:

```sh
aws --region us-east-1 s3api get-bucket-tagging --bucket kirocrew-demo-20260913-demobucket-pdjzgyu25xhb
aws --region us-east-1 s3api get-bucket-versioning --bucket kirocrew-demo-20260913-demobucket-pdjzgyu25xhb
aws --region us-east-1 s3api list-objects-v2 --bucket kirocrew-demo-20260913-demobucket-pdjzgyu25xhb
aws --region us-east-1 s3api list-object-versions --bucket kirocrew-demo-20260913-demobucket-pdjzgyu25xhb
```

Only if the bucket is still tagged `Project=kirocrew-demo`, its contents are solely the two disposable sentinel fixtures, versioning has not been enabled, and nothing needs retaining, delete the two exact objects and then the bucket:

```sh
aws --region us-east-1 s3api delete-object --bucket kirocrew-demo-20260913-demobucket-pdjzgyu25xhb --key allowed/sentinel.txt
aws --region us-east-1 s3api delete-object --bucket kirocrew-demo-20260913-demobucket-pdjzgyu25xhb --key denied/sentinel.txt
aws --region us-east-1 s3api delete-bucket --bucket kirocrew-demo-20260913-demobucket-pdjzgyu25xhb
```

Unexpected keys, object versions, delete markers, multipart uploads, retention or a deletion failure require review. Do not replace this bounded procedure with a recursive `--force` deletion. The imported EC2 key pair was created outside the stack; delete `kirocrew-demo-20260913` through EC2 only after confirming no remaining instance uses it. Local SSH key material, pinned host keys, aliases and the unloaded LaunchAgent can be retained or removed deliberately after remote cleanup; do not remove unrelated SSH entries or the whole config file.

## Backend and enforcement evidence boundary

The Mac client is Nightly `0.7.0-nightly.20260913t061222`. Its 24 selected packaged modules match their bundled RECORD entries; three differ from the frozen September 12 source. The EC2 package remains `0.7.0-nightly.20260912t060850`, a custom Linux repack with hash-locked ARM64 dependencies and matching native libraries. All 24 selected deployed server modules match that frozen September 12 baseline and are root-owned. No official Linux nightly artifact or source commit is claimed. Kiro CLI `2.21.4` is a separate official ARM artifact. [Client baseline](/Users/noahsutter/git-projects/kirocrew-demo/evidence/nightly/client-20260913-verification.json), [ARM runtime provenance](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/runtime-preparation.json), [ARM source verification](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/source-verification.json), [CLI manifest](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/kiro-cli-manifest.json)

Kiro CLI is selected for new sessions, but its own authentication check returns false and the native ACP log records exit code 1 because it is not logged in. The dashboard's GitHub card reads the separate KAS identity store. The latest normal login ended with exit code 1 without an authenticated account; the independent readback confirms that the CLI remains signed out and neither callback listener remains. When ready, run `python3 scripts/ec2-login.py` for a fresh URL, complete GitHub sign-in in the browser and keep the terminal open until it confirms the EC2 CLI result. Earlier Builder ID and callback attempts are historical. AWS IAM credentials provision resources; they do not authenticate Kiro CLI. Do not copy local Kiro/Codex/Claude token stores or sessions to EC2. A completed native session and correlated tool evidence remain required. [Latest login outcome](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/native-cli-login-outcome.json), [sign-in instructions](/Users/noahsutter/git-projects/kirocrew-demo/scripts/EC2-LOGIN.md), [observed backend failure](/Users/noahsutter/git-projects/kirocrew-demo/output/kirocrew-admin-findings.md)

The deployed MCP service implements real Streamable HTTP, bearer authentication and fixed call-time tool grants, and makes real S3 requests under the EC2 role. The [14:07 ARM baseline](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/mcp-live-receipt.json) verifies HTTP 401 without authentication, discovery, successful allowed-object access, MCP denial without dispatch, and S3 HTTP 403 with an AWS request ID. The exact walkthrough command passed again after telemetry deployment at 15:01:37 UTC; its [latest rehearsal receipt](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/final-direct-mcp-rehearsal.json) records fresh trace and request IDs and still reports `native_crew_backend_verified: false`. Earlier fixture-existence and explicit IAM-denial evidence supplies context for the unchanged demo bucket.

The Crew UID's IPv4 TCP connection to `169.254.169.254:80` was denied immediately with errno 113, without sending HTTP or reading metadata credentials. This verifies that host connection boundary; IPv6 metadata and native sandbox execution remain outside the probe's scope. [ARM IMDS connection receipt](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/crew-imds-connect-receipt.json)

The [current walkthrough](/Users/noahsutter/git-projects/kirocrew-demo/WALKTHROUGH.md) links the ARM slides, live portal, real MCP probe and pending native sequence. The revised ARM execution diagram marks the native MCP path as dashed and pending, with verified direct-service evidence labeled separately. [Current diagram delivery](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/archify-arm/council-delivery-receipt.json) records static checks and raster review; local-file access policy blocked browser validation. The 13 admin screenshots are real portal captures and have separate runtime evidence. The ARM deck incorporates the accepted candidate review changes and subsequent no-ai-slop edit; [final author/artifact checks](/Users/noahsutter/git-projects/kirocrew-demo/evidence/slides/kirocrew-arm-observability-demo/finalization.json) passed. Council approval of final bytes and native PowerPoint playback are not claimed. Historical x86 council and browser receipts retain their original scope.

The service is purpose-built for this demo. Enterprise OAuth, group administration, LiteLLM, multi-tenant identity, centralized policy distribution and external audit retention remain proposed integrations. Follow [the MCP native-session procedure](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/mcp-enforcement/README.md) for the four separate native turns after backend login. A Crew denial is established by the actual permission callback/SEL and a complete healthy MCP audit interval showing no matching dispatch; the direct service probe alone cannot establish it.
