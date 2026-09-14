# Evidence scope for the eight-clip host edition

Draft awaiting the frozen 14-slide HTML, notes and root-captured browser screenshots. No inference has started. This summary contains only evidence related to the eight native clips and their explicit limits. Broad collector snapshots, private SEL pages, credentials and local build/runtime source trees are excluded from the model packet.

## What the eight clips establish

The macOS KiroCrew client connects to the remote ARM EC2 Gateway and original Kiro CLI backend; the Mac Gateway is off. Fresh Kiro CLI SocialGitHub authentication succeeded before the four MCP turns. One endpoint-control box belongs on EC2. Current connection has owner privileges, Crew configuration remains owner editable, and no immutable enterprise governance floor or restricted human-role RBAC is established. CloudFormation uses existing VPC/subnet parameters; no additional network infrastructure or GitHub Actions are part of this extension.

| Clip | Observation and supporting evidence | Important boundary |
|---|---|---|
| Allowed S3 read | Native once-only approval, then MCP allow, AWS dispatch and result joined by trace and invocation ID. Native/service AWS request ID DT9A0C6ZKDWEQETN, 55 bytes and the allowed fixture digest agree. | Receipt attribution, not pixels alone, supports AWS dispatch. |
| Crew tool denial | Native trace-bearing blocked row, one isolated-turn hook_deny, no permission card/resolution, no matching service journal event in the collected interval. | SEL correlation is session/turn based, without a direct SEL-to-trace join. |
| MCP grant denial | Native/SEL approval precedes the separate service's tool_grant_denied; the same invocation has no AWS dispatch. | MCP grant differs from Crew policy and target IAM. |
| S3 IAM denial | Native/SEL approval, MCP allow, AWS dispatch and S3 GetObject AccessDenied HTTP403 share native/service request ID 8DET0VKCQPXJXCMC. | Separate authority readback supports the fixed denied-prefix policy and existing fixture; no per-request STS identity was collected. |
| Private-memory assignment refusal | An existing conversation switched to a private-store alias is refused before a tool turn. | Conversation/private-memory binding, not restricted human RBAC, filesystem denial or host-tool interception. |
| Permitted workspace read | One actual fs_read returned the exact public canary in live native broadcasts; clip includes request, result and expanded tool Output. | No permission event occurred; this is not an approval-callback test. |
| Command denial summary | Exact persisted printf marker input joins a host-generated blocked row by tool-call ID, with one matching isolated-turn hook_deny. | Film begins after the refusal; it only inspects the completed assistant summary, not request submission or an expanded blocked row. |
| Anonymous Gateway authentication | Exact public helper was read and executed in two native calls, each separately approved once. Persisted exact execute input joins the live result by tool-call ID; a unique matching Token required SEL denial falls between approval and result. | The clip begins at execute approval, after the prompt and source-read call. Media alone shows HTTP403; first-enforcer attribution comes from the separate reviewed correlation. |

## Four original MCP cases: retain the incomplete collector record

The original passive collector remains collection_complete:false. A separate read-only reconciliation of original native events, a recovered bounded SEL interval and MCP audit events supports the four outcomes. An independent reviewer reproduced them. The MCP journal completeness and service restart continuity checks were true. None of that silently converts the original collector into a complete capture. SEL integrity relies on original Gateway verification, without exported HMAC keys or independent per-row signature verification. No sampled process is proven to overlap a pending approval.

Fresh after-capture authority readbacks show the MCP source and service unit remain root owned and match reviewed source, and the service runs as a separate UID with the same PID/InvocationID observed during capture. Existing ARM instance/profile receipts support role association. These observations do not exclude arbitrary administrator changes between checks, prove an immutable host or recompute the denied object's digest.

## Newly reviewed anonymous authentication

The helper command is fixed: `/usr/bin/python3 /opt/kirocrew-demo/host-controls/anonymous-http.py`. The native-read exact source matches preparation and guards both real/effective UID999. Native source-read tool-call ID toolu_bdrk_01VdSiWnn4TeweZHbmkb41kF and execute ID toolu_bdrk_0159BsH9v4wTh4Zrako473xV each have a distinct Allow once. The helper sends no authorization or cookies, discards the response body and returns HTTP403 in 3 ms. Its native_enforcement_verified:false field is retained: helper output alone does not certify the enforcing layer.

The independent auth review accepts bounded Gateway token authentication: the unique api_access row 090c2f546320493a names dashboard.token_auth, /api/security/posture, loopback caller and Token required between the execute approval at 00:07:16.725578Z and result at 00:07:16.806176Z on 2026-09-14. SEL has no direct tool-call trace ID; this is exact-input/native-result plus unique temporal/route/reason correlation. This is anonymous Gateway authentication, not human-role RBAC or centrally managed immutable policy.

The auth film covers take04 seconds398–420: execute approval to its assistant JSON result. The earlier prompt/source-read approval are outside the cut and actual tool Output stays collapsed. Do not describe it as a one-tool turn, full request-to-result footage or a filmed source inspection.

## Command control and media timing

The single harmless marker command is `printf '%s\n' 'KIROCREW_DEMO_COMMAND_CONTROL_20260913'`. The native persisted blocked row and exact tool input share tool-call ID toolu_bdrk_01BuWWZAH8puQxxWhHhiL3wZ. A matching scoped hook_deny identifies the configured Crew command rule. Generic 'User denied tool execution' text or the assistant's summary alone would not identify this enforcer. No manual approval is claimed.

The denial completed at 00:00:21.709678Z, before take04 began at 00:00:31Z. The 48–66s cut is summary inspection only; its native steps remain collapsed. No action/interception footage is invented. The exact temporary marker rule was subsequently removed; fresh readback confirms its ID/pattern absent and no other user-added rule present. The before-state did not hash every unrelated custom rule, so the cleanup receipt alone cannot prove every unrelated custom rule was preserved. Built-in count112 is catalog/source evidence, not112 executed tests.

## Unfinished and excluded cases

A sensitive-path public canary request and the first anonymous-helper request produced model-only refusals without native tool attempts. They do not establish filesystem, host or Gateway enforcement and are excluded from accepted enforcement footage. A later narrow public-fixture prompt amendment did not change tools, MCP, empty allowedTools or server policy.

Sensitive-path read and protected-path write still lack completed native denial demonstrations. The IMDS helper source was read and approved; its execute request remains unresolved at permission request ee23b765-4f4e-4fbf-b47e-10b933c0f69a. No completed IMDS result or bracketed firewall-counter outcome exists. Root reports the Mac locked with that approval pending. A prepared OUTPUT UID/destination rule and a before-counter snapshot are not network-enforcement proof. These remain unfinished, not quietly skipped successes.

## Visual review limits

Three new continuous cuts were fully decoded and sampled by a media reviewer; an independent visual reviewer inspected their contact sheets and own-result posters. Original timing and source bytes are retained: no overlays, synthetic freeze, padding, speed change or compositing. Workspace cut is take03 seconds26–65, command summary is take04 seconds48–66, and auth is take04 seconds398–420. Media review and enforcement attribution are separate. Browser playback/seek and the final root acceptance belong to separate exact-artifact checks.

The forthcoming14 council screenshots will show the deck's still appearance and posters only, not every frame, video playback or live AWS/backend state. Their original browser JPEG bytes will be preserved and converted to PNG with an identical decoded-RGB24 hash for each image. The council receives these14 actual screenshot encodings, final notes and this concise public evidence summary; underlying private collector/source material is deliberately excluded. Admin configured coverage, native Gateway telemetry, custom collection health logs and security audit are distinct surfaces.

## Public evidence references and preparation hashes

References below are provenance for this summary, not authorization to read outside the frozen packet. Final preparation must refresh any changed inputs.

- `evidence/native-client-demo/20260913/authenticated.json` — `e34c9d5411b8a0f32cd65ee2ae29b45136cbdecb0e06cefbd4ea0b06d71742c1`.
- `evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json` — `301c4baaf4fc7ff2dbab091c91df9bd89338f301247dd289450fbe2ad051ee0b`.
- `evidence/native-client-demo/20260913-ui2-reconciled-final/review.json` — `e18b6f2e304d800a2734e74d346a07894c34d745c43df69c2b370ff50b9989c9`.
- `evidence/native-client-demo/20260913-ui2/authority-attribution-review.json` — `3bd876c012bf0c0039e4cac74fb63b8736f3104dc947736356d66a7ccfb95642`.
- `evidence/native-client-demo/media-review-mcp-controls.json` — `e7ffdfac58d9c255c3aa538f41ef6c0568142b445c9779483393f684feee051d`.
- `evidence/native-client-demo/media-review-memory-assignment.json` — `68e609282f6cf097fc9ed3f88a1228f4703fee5311a5945cfa98a9dfc78cc167`.
- `evidence/native-client-demo/host-20260913/assignment-diagnostic.json` — `8090b4a69f0c4f76021d6cf1c869f352c188aaa61c31382f3b4e0b19f0ea8a6c`.
- `evidence/native-client-demo/host-20260913-review/initial-review.json` — `ff855dbecb4bdb852200521040f4d5e523b1f50d7035fb3ec808395f4e3314e9`.
- `evidence/native-client-demo/host-20260913-review/auth-review.json` — `da505b7c943ad593d02e1c2021b8e54d84ce58478bb6b4ef53b668d891047204`.
- `evidence/native-client-demo/host-20260913-ui3/initial-observations-v2.json` — `9f757015d7bd9da89c7e694a315c0d73e7004e743f0404cd0cd487d88c742302`.
- `evidence/native-client-demo/host-20260913-ui3/command-observations-v2.json` — `63a86c6d6e8be4e14efe5dbe31962eab4d921c104cf40a1d6bbef770c3a54436`.
- `evidence/native-client-demo/host-20260913-ui3/command-rule-cleanup.json` — `3eae37afdfc7d513f702a336d1e6ce70f07f36209151630b0271f314bfc146e1`.
- `evidence/native-client-demo/host-20260913-ui3/auth-correlation.json` — `24c53664bcecc22aaa59e15a86f52c910bcb2dc6662d840b2a665c8f2e133543`.
- `evidence/native-client-demo/host-20260913-ui3/imds-history-pending.json` — `24d4206a25af8d082e671ca7603a43565d395e265727daf2e7ecbf7d891122af`.
- `evidence/native-client-demo/media-review-host-controls.json` — `367feb092840ca302df918152c1f28f5e71604c5674c6557bbd193c6361bfe02`.
