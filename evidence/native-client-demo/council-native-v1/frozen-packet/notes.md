# KiroCrew native control presentation

## 1. A Mac client. Server controls.

This focused edition contains the supplied recordings of real application behavior. The Mac endpoint is the only client platform in scope. The original Kiro CLI backend completed a fresh GitHub sign-in before these native MCP turns. The media manifest describes visible behavior. Explicit supporting receipts accompany this edition for separate server-attribution review. Playback controls operate recordings and do not send requests to the live system.

## 2. Execution and host controls stay on EC2

The diagram preserves a single endpoint-control box. Gateway, Kiro CLI, workspace, host controls and the MCP service reside on the ARM EC2 host. The MCP service has a separate process identity and fixed demo grants. Its AWS calls use the instance role. The current connection has owner privileges, and no enterprise governance floor is active. Crew configuration remains writable by the crew account. The host diagram does not establish immutable multi-user policy, failover or EDR. Existing infrastructure supports caller-supplied VPC and subnet parameters without adding NAT gateways or load balancers.

## 3. The control decides where the request stops

The matrix summarizes only scenes present in the processed input manifests. It lists visible outcomes rather than assigning automatic acceptance. For native MCP turns, Crew auto-denial must precede MCP dispatch, MCP grant denial must precede AWS dispatch, and an AWS refusal needs the returned AWS request ID and matching service evidence. Host and identity cases retain their own scope. The private-memory refusal stops an unassigned conversation before a tool turn. It does not establish restricted human-role RBAC. An anonymous authentication rejection would establish an authentication boundary only. The prepared host takes cover an allowed workspace read, anonymous server authentication, sensitive-path read, protected-path write, a server command rule and a metadata TCP connection. Those six native outcomes remain unobserved in this edition.

## 4. A permitted S3 read

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 44.0, "end": 70.0}. 3s: Submit the allowed read. The Mac client sends read_allowed with its unique trace ID. 9s: Inspect the permission request. The UI asks to run the exact MCP tool once. 18s: Read the result. The client displays ok:true, layer:aws and the S3 result identifiers.

## 5. Crew blocks a tool call

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 96.0, "end": 124.0}. 6s: Submit the denied tool. The Mac client requests crew_denied with its unique trace ID. 12s: See the policy block. The native client shows Tool call blocked for crew_denied. 20s: Read the refusal. The final response reports the Crew policy denial and stops.

## 6. The MCP service refuses the grant

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 160.0, "end": 189.0}. 6s: Submit the MCP request. The Mac client requests mcp_denied with its unique trace ID. 11s: Inspect the permission request. The client presents Allow once for the exact tool call. 23s: Read the MCP refusal. The client displays ok:false, layer:mcp and tool_grant_denied.

## 7. AWS refuses the S3 read

Actual macOS Kiro Crew Nightly client turn through the EC2 Gateway and original Kiro CLI backend. Visible UI result; server receipt correlation is reviewed separately. This media review does not assert enforcement acceptance. Recorded 2026-09-13T21:23:50Z. Source capture SHA-256: f5ba02c11531c34f5097dc223ba37adb29c3cdb3ba05a669e32131e4c24cbcf7. Cut: {"start": 188.0, "end": 222.0}. 2s: Submit the AWS request. The Mac client requests iam_denied with its unique trace ID. 12s: Inspect the permission request. The client presents Allow once for the exact tool call. 28s: Read the AWS refusal. The client displays AccessDenied, HTTP403, layer:aws and an AWS request ID.

## 8. Unassigned conversation refused private memory

Actual macOS native client observation of the conversation-to-memory identity-binding guard. The request stops before a tool turn. This is not an RBAC test, a filesystem denial or proof of host-tool enforcement. Recorded 2026-09-13T21:40:04Z. Source capture SHA-256: 672c79f461f47c6f0389af0a908e9553fcbe9878b4c475f1e8216e353154d88e. Cut: {"start": 16.0, "end": 30.0}. 2s: Submit the fixture request. The composer contains one bounded fs_read request for the prepared public canary. 6s: Read the assignment refusal. The client reports no verified assignment to private memory and retains the conversation’s V1 context. 10s: Locate the control boundary. The refusal occurs before a tool turn. The source-backed diagnostic identifies a conversation-to-private-memory assignment guard; the filesystem request has not been tested.

## 9. The admin console explains the controls

The separate guide presents actual screenshots with capture dates, route-specific explanations and full-size inspection. Live Security Posture reports configured coverage. Its SEL section is a coverage list, not a live security-event viewer. Denied Commands controls shell rules, while auto_deny_tools controls the separate Crew MCP hook. The approval page's six-hour setting governs the next auto-approve period. The session remained interactive for these demonstrations. Governance reports no enterprise policy in effect. Native Gateway telemetry describes backend activity. The custom collection log reports client and server health events, not raw prompts or security denials.

## 10. The recordings and evidence stay together

The build validates processed-media hashes, sizes, decoded-media flags, capture provenance and chapter bounds. This is an artifact-integrity check, not an enforcement acceptance verdict. Review receipts apply to their exact candidates. Earlier model-council decisions do not automatically cover this derivative. The preview server serves only the hash-bound allowlist and supports video byte ranges. It does not execute demo commands. No GitHub Actions are required by this presentation.

## Build inputs

- `output/native-client-clips-20260913/manifest.json`: `75e26eb15e30ab2432da38e3a728936f539a789333a9e5f9ccb497f22943a127`
- `output/native-memory-clip-20260913/manifest.json`: `30defeffec49130c2fd9c307fb6fe19bd817902eb1044c02b9e1559751ccc8db`
- `docs/HOST-CONTROL-SCENARIOS.md`: `9b5094ccd215128f9a69dc2cbcfdcdb96c34faa0433361cc255a4bbfc8669935`
- `evidence/admin-console/native-20260913/tour-build.json`: `dcd0ce436cf786e90b0ea2ae5e7ae57999ba5f7f864979d8dd67e72281a3f12a`

## Supporting receipts

- `evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json`: `301c4baaf4fc7ff2dbab091c91df9bd89338f301247dd289450fbe2ad051ee0b`
- `evidence/native-client-demo/20260913-ui2-reconciled-final/review.json`: `e18b6f2e304d800a2734e74d346a07894c34d745c43df69c2b370ff50b9989c9`
- `evidence/native-client-demo/20260913-ui2/authority-attribution-review.json`: `3c0d57509955abb10cec950e922c4222d33bc0a3a8b1a718e525e96f2b63fadd`
- `evidence/native-client-demo/media-review-memory-assignment.json`: `68e609282f6cf097fc9ed3f88a1228f4703fee5311a5945cfa98a9dfc78cc167`
- `evidence/native-client-demo/host-20260913/assignment-diagnostic.json`: `8090b4a69f0c4f76021d6cf1c869f352c188aaa61c31382f3b4e0b19f0ea8a6c`

## What changed

This edition starts with the Mac-to-EC2 execution boundary and puts each recorded control on its own slide. The admin screenshot tour remains separate. Short result labels replace repeated qualification paragraphs on the slides. The notes retain attribution limits, owner authority and the absence of an enterprise governance floor. The No AI Slop pass removed vague claims and repeated setup while preserving tool names and observed results.
