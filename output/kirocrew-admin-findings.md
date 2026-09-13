# KiroCrew admin console findings

Observed September 13, 2026 · ARM EC2 demo

The owner dashboard shows the remote host and its control settings. The GitHub sign-in card can look ready while the selected standalone Kiro CLI is signed out. The screenshots preserve that observed failure.

## 1. Backend sign-in can be misread

The Kiro sign-in card reports GitHub authentication while standalone Kiro CLI exits as signed out. The card reads KAS state. Label those identities separately in a future product fix; for this demo, show the CLI’s own result and retain the native-authentication gate.

Evidence: [07-agent-backend.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/07-agent-backend.jpg), [10-native-auth-log.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/10-native-auth-log.jpg), [.build/kirocrew-source/website/src/pages/settings/KiroSignInCard.tsx:158](/Users/noahsutter/git-projects/kirocrew-demo/.build/kirocrew-source/website/src/pages/settings/KiroSignInCard.tsx:158), [.build/installed-nightly/kiro_crew/auth/service.py:245](/Users/noahsutter/git-projects/kirocrew-demo/.build/installed-nightly/kiro_crew/auth/service.py:245).

## 2. Gateway health is broader than backend readiness

Overview says all systems are running while the CLI cannot start. Use Overview to establish dashboard and Gateway health; use a completed native session to establish backend readiness.

Evidence: [01-overview.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/01-overview.jpg), [10-native-auth-log.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/10-native-auth-log.jpg).

## 3. The MCP count has a narrower process scope

System Services reports zero MCP processes, but the demo MCP runs under a separate Unix user and systemd unit. The custom collector displays that unit’s health. The passing direct MCP/AWS receipt establishes the tested tool behavior.

Evidence: [03-gateway-services.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/03-gateway-services.jpg), [11-client-server-telemetry.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/11-client-server-telemetry.jpg), [evidence/aws/arm-20260913/mcp-live-receipt.json](/Users/noahsutter/git-projects/kirocrew-demo/evidence/aws/arm-20260913/mcp-live-receipt.json).

## 4. Security status reports configuration

The posture page lists Standard sandbox, Interactive approval and control counts. No enterprise policy is in effect. Keep those labels separate from claims about executed sandboxing, pre-execution callbacks and immutable policy governance.

Evidence: [04-security-posture.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/04-security-posture.jpg), [05-interactive-approval.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/05-interactive-approval.jpg), [06-governance.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/06-governance.jpg).

## 5. The auto-approve duration needs its context

Six hours is selected as the duration for the next activation, while the current mode is Interactive. Explain both labels together so the duration is not read as an active bypass.

Evidence: [05-interactive-approval.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/05-interactive-approval.jpg).

## 6. Native telemetry needs sample-count context

Gateway duration measurements are present, but completed-turn samples are zero. A zero fault rate over zero turns is not a passed backend test. The displayed 14-day query window does not extend the configured seven-day retention. The 64 MiB storage setting is a retention target; pruning protects active writers, so stored data can temporarily exceed it.

Evidence: [08-telemetry-controls.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/08-telemetry-controls.jpg), [09-native-telemetry.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/09-native-telemetry.jpg), [infrastructure/RUNBOOK.md:97](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/RUNBOOK.md:97), [.build/installed-nightly/kiro_crew/metrics/local_exporter.py:398](/Users/noahsutter/git-projects/kirocrew-demo/.build/installed-nightly/kiro_crew/metrics/local_exporter.py:398).

## 7. Client and server collection is visible in a custom app

The native Telemetry panel continues to show Gateway instrumentation. The installed Demo Observability App Kit page adds the two collectors and collection-event filters inside the owner dashboard. It is a demo extension with local bounded storage.

Evidence: [11-client-server-telemetry.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/11-client-server-telemetry.jpg), [12-collection-logs.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/12-collection-logs.jpg).

## 8. Freshness and measurement definitions affect interpretation

Samples older than three minutes become stale. Mac CPU sums process scheduler averages and can exceed 100%; server host CPU uses a one-second normalized sample. The local tunnel probe checks listener reachability. None of these health probes establishes an authorized model response.

Evidence: [infrastructure/observability-collector/README.md](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability-collector/README.md), [infrastructure/observability/APP-INSTALL.md](/Users/noahsutter/git-projects/kirocrew-demo/infrastructure/observability/APP-INSTALL.md).

## 9. Current means a fresh sample

The controlled desktop pause produced a fresh sample with desktop running No and zero desktop process CPU and memory. Its Current badge remained visible while the server checks stayed Yes. Read the individual check results alongside the freshness badge. The recorded recovery followed the Mac app’s relaunch.

Evidence: [13-client-stopped.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/13-client-stopped.jpg), [12-collection-logs.jpg](/Users/noahsutter/git-projects/kirocrew-demo/output/admin-console/12-collection-logs.jpg).

## Demo changes

The demo now uses the ARM host as its single execution endpoint and keeps the Mac Gateway off. The admin walkthrough adds native Gateway telemetry, a custom page for both client and server health, and source-filtered collection logs. The presentation must name the custom page as an App Kit extension and keep the CLI authentication failure visible until a new successful native run supersedes it.

## What remains to be demonstrated

The direct MCP probe verified authentication, catalog, an allowed S3 read, grant denial before AWS dispatch and an IAM-denied read. Complete the separate native Kiro CLI login, approval, hook, sandbox and security-event correlation checks before presenting those as end-to-end Crew enforcement.

## What changed

The editing pass shortened the opening, added direct evidence links, clarified the storage retention target and kept configuration, health measurements and executed enforcement distinct.
