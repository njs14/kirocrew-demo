# KiroCrew native control presentation

## 1. Server controls for a Mac client

This focused edition contains the supplied recordings of real application behavior. The Mac endpoint is the only client platform in scope. The supplied authentication receipt confirms that the original EC2 Kiro CLI backend was signed in through GitHub before capture. The media manifest describes visible behavior. Explicit supporting receipts accompany this edition for separate server-attribution review. Playback controls operate recordings and do not send requests to the live system.

## 2. Execution and host controls stay on EC2

The diagram preserves a single endpoint-control box. Gateway, Kiro CLI, workspace, host controls and the MCP service reside on the ARM EC2 host. The MCP service has a separate process identity and fixed demo grants. Its AWS calls use the instance role. The current connection has owner privileges, and no enterprise governance floor is active. Crew configuration remains writable by the crew account. The host diagram does not establish immutable multi-user policy, failover or EDR. Existing infrastructure supports caller-supplied VPC and subnet parameters without adding NAT gateways or load balancers.

## 3. The control decides where the request stops

The matrix summarizes only scenes present in the processed input manifests. It lists visible outcomes rather than assigning automatic acceptance. For native MCP turns, Crew auto-denial must precede MCP dispatch, MCP grant denial must precede AWS dispatch, and an AWS refusal needs the returned AWS request ID and matching service evidence. Host and identity cases retain their own scope. The private-memory refusal stops an unassigned conversation before a tool turn. It does not establish restricted human-role RBAC. An anonymous authentication rejection would establish an authentication boundary only. The prepared host takes cover an allowed workspace read, anonymous server authentication, sensitive-path read, protected-path write, a server command rule and a metadata TCP connection. Those six native outcomes remain unobserved in this edition.

## 4. A permitted S3 read

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 44.0, "end": 70.0}. 3s: Submit the allowed read. The Mac client sends read_allowed with its unique trace ID. 9s: Inspect the permission request. The UI asks to run the exact MCP tool once. 18s: Read the result. The client displays ok:true, layer:aws and the S3 result identifiers. 55 bytes. SHA-256 prefix 34ebbefeb5f6. Native and service request ID DT9A0C6ZKDWEQETN. Layer attribution follows the supplied bounded reconciliation. The original collector remains incomplete. Crew correlation uses the isolated turn because SEL has no direct trace-to-tool-call join for that denial. The poster uses an actual result frame at 22 seconds in this clip. Video bytes and cut boundaries remain unchanged.

## 5. Crew blocks a tool call

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 96.0, "end": 124.0}. 6s: Submit the denied tool. The Mac client requests crew_denied with its unique trace ID. 12s: See the policy block. The native client shows Tool call blocked for crew_denied. 20s: Read the refusal. The final response reports the Crew policy denial and stops. The blocked native turn matches an isolated SEL hook denial. The MCP journal has no matching arrival. Layer attribution follows the supplied bounded reconciliation. The original collector remains incomplete. Crew correlation uses the isolated turn because SEL has no direct trace-to-tool-call join for that denial. The poster uses an actual result frame at 17 seconds in this clip. Video bytes and cut boundaries remain unchanged.

## 6. The MCP service refuses the grant

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 160.0, "end": 189.0}. 6s: Submit the MCP request. The Mac client requests mcp_denied with its unique trace ID. 11s: Inspect the permission request. The client presents Allow once for the exact tool call. 23s: Read the MCP refusal. The client displays ok:false, layer:mcp and tool_grant_denied. Native and service results agree on tool_grant_denied. The matched invocation has no AWS dispatch. Layer attribution follows the supplied bounded reconciliation. The original collector remains incomplete. Crew correlation uses the isolated turn because SEL has no direct trace-to-tool-call join for that denial. The poster uses an actual result frame at 23 seconds in this clip. Video bytes and cut boundaries remain unchanged.

## 7. AWS refuses the S3 read

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 188.0, "end": 222.0}. 2s: Submit the AWS request. The Mac client requests iam_denied with its unique trace ID. 12s: Inspect the permission request. The client presents Allow once for the exact tool call. 28s: Read the AWS refusal. The client displays AccessDenied, HTTP403, layer:aws and an AWS request ID. Native and service results match: AccessDenied, HTTP 403, AWS request ID 8DET0VKCQPXJXCMC. Layer attribution follows the supplied bounded reconciliation. The original collector remains incomplete. Crew correlation uses the isolated turn because SEL has no direct trace-to-tool-call join for that denial. AWS role attribution uses the existing instance-profile/cutover receipts and after-capture source, service and policy checks. No per-request STS caller identity was collected. Fixture HEAD checks establish existence and metadata, without recomputing the denied object's content digest. Process observations do not establish that a sampled PID overlapped a pending approval. These limits remain in the linked authority review. The poster uses an actual result frame at 28 seconds in this clip. Video bytes and cut boundaries remain unchanged.

## 8. Private memory requires an assigned conversation

Actual macOS native client observation of the conversation-to-memory identity-binding guard. The request stops before a tool turn. This is not an RBAC test, a filesystem denial or proof of host-tool enforcement. Recorded 2026-09-13T21:40:04Z. Source capture SHA-256: 672c79f461f47c6f0389af0a908e9553fcbe9878b4c475f1e8216e353154d88e. Cut: {"start": 16.0, "end": 30.0}. 2s: Submit the fixture request. The composer contains one bounded fs_read request for the prepared public canary. 6s: Read the assignment refusal. The client reports no verified assignment to private memory and retains the conversation’s V1 context. 10s: Locate the control boundary. The refusal occurs before a tool turn. The source-backed diagnostic identifies a conversation-to-private-memory assignment guard; the filesystem request has not been tested. The poster uses an actual result frame at 8 seconds in this clip. Video bytes and cut boundaries remain unchanged.

## 9. Admin settings and logs have different jobs

The slide magnifies two rectangular details from the unchanged September 13 posture and governance screenshots. Each opens its complete original screenshot. The separate guide presents full screenshots with capture dates, route-specific explanations and full-size inspection. Live Security Posture reports configured coverage. Its SEL section lists coverage, with no live security-event viewer. Denied Commands controls shell rules, while auto_deny_tools controls the separate Crew MCP hook. The approval page's six-hour setting governs the next auto-approve period. The session remained interactive for these demonstrations. Governance reports no enterprise policy in effect. Native Gateway telemetry describes backend activity. The custom collection log reports client and server health events. SEL decisions and MCP audit records are separate evidence sources.

## 10. The recordings and evidence stay together

The build validates processed-media hashes, sizes, decoded-media flags, capture provenance and chapter bounds. Artifact integrity and enforcement acceptance have separate reviews. All supplied receipts appear in the recording manifest and these notes. The external Grok and Opus council reviewed the earlier ten-slide candidate and requested changes. This derivative incorporates the agreed changes, followed by No AI Slop editing. Its changed bytes need a fresh root browser review and local read-only review. The external verdicts do not constitute exact-model review of this derivative. The preview server serves only the hash-bound allowlist and supports video byte ranges. Presentation controls do not execute demo commands.

## Build inputs

- `output/native-client-clips-20260913/manifest.json`: `2683eef05ff8d2a347e8c2494ca15ffe8eb991effeb48fce12b98055cdf3e59e`
- `output/native-memory-clip-20260913/manifest.json`: `3565112184e648433a295349127b60181e80cd6517f67a46604edf66477b127d`
- `docs/HOST-CONTROL-SCENARIOS.md`: `9b5094ccd215128f9a69dc2cbcfdcdb96c34faa0433361cc255a4bbfc8669935`
- `evidence/admin-console/native-20260913/tour-build.json`: `a9f49d568662b158ad87215014cf32010815f01b022ab874725ca5f9cad99627`

## Supporting receipts

- `evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json`: `301c4baaf4fc7ff2dbab091c91df9bd89338f301247dd289450fbe2ad051ee0b`
- `evidence/native-client-demo/20260913-ui2-reconciled-final/review.json`: `e18b6f2e304d800a2734e74d346a07894c34d745c43df69c2b370ff50b9989c9`
- `evidence/native-client-demo/20260913-ui2/authority-attribution-review.json`: `3bd876c012bf0c0039e4cac74fb63b8736f3104dc947736356d66a7ccfb95642`
- `evidence/native-client-demo/media-review-mcp-controls.json`: `e7ffdfac58d9c255c3aa538f41ef6c0568142b445c9779483393f684feee051d`
- `evidence/native-client-demo/media-review-memory-assignment.json`: `68e609282f6cf097fc9ed3f88a1228f4703fee5311a5945cfa98a9dfc78cc167`
- `evidence/native-client-demo/20260913/authenticated.json`: `e34c9d5411b8a0f32cd65ee2ae29b45136cbdecb0e06cefbd4ea0b06d71742c1`
- `evidence/native-client-demo/20260913/runtime-preflight.json`: `d7c65d53e3bd2be421c6f5c80f9fe4f512eb18a5e76a52261f0cefc68ef60499`
- `evidence/native-client-demo/poster-review-v2.json`: `0489c07e6174363188760877260778e6b47cf72c462d3589224574872885649a`
- `evidence/native-client-demo/host-20260913/assignment-diagnostic.json`: `8090b4a69f0c4f76021d6cf1c869f352c188aaa61c31382f3b4e0b19f0ea8a6c`
- `evidence/native-client-demo/council-native-v1/council-decision-summary.json`: `16def13ae85f6ba9e911a633b17dd2bf584ac0f2bf210ba139ba849b8e6e86d1`

## Superseded citation

The previous authority-review citation `3c0d57509955abb10cec950e922c4222d33bc0a3a8b1a718e525e96f2b63fadd` is superseded by `3bd876c012bf0c0039e4cac74fb63b8736f3104dc947736356d66a7ccfb95642`. The linked receipt and this build use the current hash.

## What changed

After the Grok and Opus council, each clip now opens with its own real result poster. The video bytes, continuous cuts and original timing remain unchanged. Owner authority and the absence of an enterprise policy floor are visible on the slides. The memory scene says the request stopped before tools. The admin slide magnifies actual posture and governance details and separates health collection, Gateway telemetry, SEL evidence and MCP audit records. The No AI Slop pass tightened the new captions and evidence labels while retaining the control names and observed outcomes.
