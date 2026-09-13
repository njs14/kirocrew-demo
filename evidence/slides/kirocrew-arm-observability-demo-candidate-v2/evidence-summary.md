# ARM and observability demo evidence summary

Candidate: 12 slides. The accepted endpoint-control reference image is preserved byte for byte. It is a reference map; this demo does not claim every pictured enterprise or Crew control was executed.

## Verified deployment

CloudFormation UPDATE_COMPLETE in us-east-1. Active host t4g.xlarge, ARM64, four vCPUs, 16 GiB RAM and encrypted 40 GiB gp3. Security group inbound is TCP 22 from one client IPv4 /32 only. IMDSv2 required; hop limit 1. Gateway 5476, MCP 8001 and custom App Kit 9102 listen on loopback. Previous t3a.small x86 instance is stopped for rollback; its 24 GiB disk remains billable.

## Direct enforcement probe

ARM direct_mcp_service_probe passed at 2026-09-13T14:07:16Z, explicitly native_crew_backend_verified=false. Unauthenticated MCP 401; catalog four tools. read_allowed: 55 bytes, expected digest 34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160, request 5NMYCQ5YF956H52H. mcp_denied tool_grant_denied before AWS dispatch. iam_denied S3 AccessDenied 403, request 5NMQFXT3FYT6A0A9. crew_denied is configured to stop automatically before approval/MCP dispatch, but native proof is pending.

## Host authority

Gateway/backend/workspace run as crew. A UID-specific firewall blocks crew metadata access. MCP service runs as mcp-demo, obtains the instance role through IMDSv2 and exposes fixed tools. Role allows two demonstration S3 prefixes, explicitly denies GetObject under denied/, and includes SSM core managed policy. Root owns core Gateway/MCP runtime files and services; custom App Kit files are Crew-writable and its backend has Crew authority. Root/admin remains trusted. Desktop owner-token helper uses existing administrator access, enters the verified Gateway mount namespace and drops to crew for stock minting; it adds no crew sudo permission. Local IAM user credentials are not copied to EC2.

## Versions and current client

Mac client 0.7.0-nightly.20260913t061222: 24 selected paths across 2 bundled architecture lanes pass 48 RECORD hash/size checks. Three paths differ from frozen September 12; no behavioral equivalence claimed. Server remains frozen 0.7.0-nightly.20260912t060850 custom Linux ARM64 repack, 48 locked dependencies, 24 selected modules matching original frozen bytes. This is not an official Linux nightly release. Kiro CLI 2.21.4 official ARM artifact installed and selected. Current Mac native UI is connected to EC2 workspace with runLocalGateway=false, no 5476 listener and 5599 SSH listener. Owner-token refresh succeeded during normal restart.

## Native telemetry

Readback at 14:50:25 UTC: native collection enabled, not env-pinned, no OTLP, two metric shards under /var/lib/kirocrew/metrics, usage beacon disabled. Live configuration: export 10 seconds, retention 7 days, max_total_mb 64. Exporter uses MiB; 64 MiB is a pruning target and active writers can temporarily keep total above it. Native UI shows Gateway request/boot instruments and process counters. Empty model-turn statistics do not prove zero-latency sessions.

## Custom App Kit telemetry

Demo Observability 1.0.1 uses loopback 9102 behind authenticated Gateway proxy. Signed snapshot 200, backend health 200, unsigned direct data 401, unauthenticated Gateway app 403. Both collectors run 60 seconds; UI refresh 15 seconds / stale 180 seconds; at most 240 samples per source and 200 fixed collection events. Custom app labels collection sources, freshness and missing/unknown values. Mac measures process-family CPU/RSS/count and local TCP checks; a 5599 connection only proves local tunnel-listener reachability. Server measures host CPU/memory/disk, main-process CPU/RSS, systemd activity and loopback ports. CPU samples differ in meaning across Mac/server. No native RUM, distributed trace or centralized raw-log claim.

Screenshot 11 shows earlier 14:43:14 UTC Mac 4% CPU / 772.4 MiB and 14:43:35 EC2 6.2% CPU / 14.6 GiB available. The later API readback is 14:50:25 UTC, with different current values. They are distinct snapshots.

Controlled Mac quit generated warning 14:44:42 UTC; relaunch generated info 14:49:34 UTC. Gateway PID 4991 / start 14:26:10 UTC unchanged before/after. This proves independent process lifetimes, not active model-session survival. Displayed screenshot log times are Eastern local time (UTC-4).

## Native acceptance still pending

Plain Kiro CLI whoami reports unauthenticated / exit 1. ACP startup reports not logged in. No completed native model turn, native approval outcome, Crew hook denial, native SEL correlation or sandbox behavior is claimed. After login, inspect and approve three routed calls once. crew_denied must stop automatically before approval or MCP dispatch; operator rejection cannot satisfy it.

## Cost

AWS Pricing API: Linux t4g.xlarge $0.1344/hour. AWS VPC IPv4 $0.005/hour. Combined $0.1394/running hour, rounded $0.139. gp3 $0.08/GB-month: 40 GiB active $3.20/month + 24 GiB rollback $1.92/month = $5.12. 730 running hours yields $106.882 base/month, about $107. S3, transfer, model usage and taxes additional. Standard credits; no NAT/load balancer. Stopping stops compute/IP billing; EBS remains billable.

## Artifact validation scope

12-slide package, geometry, Arial font policy, editable native tables on 4/5/6 and exact artifact-tool reimport passed. Screenshot JPG bytes are embedded unchanged; native PowerPoint a:srcRect cropping preserves readable content. No PowerPoint application playback claimed. Candidate images have been inspected; prior council reviewed the separate earlier x86 deck only. This candidate is submitted for a fresh model council before final editorial pass.
