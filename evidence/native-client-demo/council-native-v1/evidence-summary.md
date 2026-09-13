# Native control evidence for this frozen deck

This packet covers the ten-slide native-controls HTML edition with five actual macOS KiroCrew client clips. The Mac uses the remote ARM EC2 Gateway and the original Kiro CLI backend, with its local Gateway off. The deck preserves one endpoint-control box on EC2. The user requested identity, MCP/tool and other host controls, plus a separate substantive admin console screenshot tour. macOS is the only client acceptance platform. CloudFormation supports existing VPC/subnet parameters; additional network infrastructure and GitHub Actions remain outside scope.

## Fresh authentication and four native MCP outcomes

The fresh 2026-09-13 Kiro CLI sign-in succeeded using SocialGitHub. Credentials/session state were not copied between products. Native Mac UI prompts and once-only approval cards were captured in an actual silent window recording at 21:23:50Z. Four continuous cuts retain timing: permitted read 44–70s, Crew denial 96–124s, MCP denial 160–189s, and IAM denial 188–222s. A separate media reviewer inspected source transitions and result frames, verified source/media hashes and fully decoded the outputs. It did not independently evaluate enforcement acceptance or browser playback.

The original passive collector receipt remains `collection_complete:false`: its SEL baseline anchor was no longer retained, and known ACP purpose metadata was not handled correctly by the original trace classifier. Nothing was rewritten as a passed capture. A separate read-only reconciliation recovered and joined the original 55 native events, 12 SEL rows and seven MCP service audit events. An independent reviewer reproduced all four bounded outcomes and returned no material findings. Original service-journal completeness and service stability checks were true. The recovered SEL rows use the Gateway's original integrity verification; independent per-row HMAC verification was not performed.

- Allowed: native approval IDs join SEL; trace and invocation ID join the service's MCP allow, AWS dispatch and S3 result. Request ID `DT9A0C6ZKDWEQETN`, 55 bytes, and fixture digest `34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160` agree.
- Crew: a trace-bearing native blocked tool row, one isolated-turn SEL `hook_deny`, no permission card/resolution and no matching MCP journal event in the collected interval. This is session/turn correlation; SEL does not expose a direct trace-to-tool-call-ID join for this hook.
- MCP: once-only native and SEL approval precede the separate service's `tool_grant_denied`. Native result and journal share the invocation ID; that invocation has no AWS dispatch.
- IAM: native and SEL approval precede MCP allow, AWS dispatch and S3 `GetObject AccessDenied` HTTP403. Native/service request ID is `8DET0VKCQPXJXCMC`. Separate authority readbacks establish that deployed policy still matches the original denied-prefix policy and the fixed fixture exists.

Fresh after-capture authority checks show the MCP source and unit are root owned, not group/world writable, and match reviewed source. The MCP service runs as its separate UID with the same PID and InvocationID observed during capture. Existing ARM instance-profile and stack receipts support the role association. No per-request STS caller identity or fresh IAM instance-profile membership was collected. After-capture checks cannot exclude arbitrary administrator changes between observations. HeadObject confirms fixture existence and metadata, not a freshly recomputed denied-object digest. Remote Kiro CLI lineage is observed, but there is no proof a specific sampled PID overlapped a pending approval.

## Fifth clip: conversation/private-memory assignment

The second actual native take at 21:40:04Z contains a 16–30s cut: after switching an existing conversation to a private-store alias, the client refuses the first fixture request because the conversation has no verified assignment to private V2 memory. The source-backed diagnostic maps this to the conversation assignment guard. It stopped before a tool turn; the attempted filesystem read never ran. This supports a session identity-binding refusal, not restricted human-role RBAC, a filesystem denial or host-tool enforcement. The original capture contains transient partial black repaint patches; the submitted request and refusal are readable in stable frames. The continuous cut retains those artifacts.

Six additional native host scenarios are prepared but unrecorded in this candidate: allowed workspace read, anonymous server authentication, sensitive-path read, protected-path write, server command rule and metadata TCP connection. Do not report those six outcomes as observed. Current connection has owner authority, Crew config is owner editable, and no immutable enterprise governance floor is active.

## Admin tour, presentation and review limits

A separate actual-screenshot admin guide covers configured posture, command rules, approval duration, governance, backend and telemetry. Posture counts and SEL coverage are configured catalogs, not executed test counts or a live SEL event viewer. The six-hour duration applies to the next auto-approve period; the native demonstrations remained interactive. The custom collection log contains client/server health events, not raw security denials. Native Gateway telemetry is a distinct view.

The ten packet PNGs are lossless encodings of the decoded pixels of root-captured browser screenshots at 1280x720, exactly bound to the frozen HTML by capture-binding.json. The original CUA captures used .png names but contained JPEG bytes; the strict preparation gate caught this before inference. Original capture bytes remain unchanged. FFmpeg converted their decoded RGB24 pixels to PNG without resizing, cropping, retouching or overlays; each source and PNG has the same decoded RGB24 hash. They can establish slide appearance, not video playback, seeking, every recorded frame or fresh AWS state. Root is reviewing playback separately; do not imply it was completed by these council members. The HTML includes embedded media/posters, and only the PNGs and notes are needed for review.

Known citation defect in this candidate: frozen notes still list the previous authority-attribution-review hash `3c0d57509955abb10cec950e922c4222d33bc0a3a8b1a718e525e96f2b63fadd`. The current revised authority receipt below binds the final reconciliation and explicitly records that prior hash. Evaluate that stale citation as a deck defect; the current summary does not silently correct the frozen notes. Earlier council decisions and pre-council No AI Slop edits do not automatically cover the post-council final derivative. Root will incorporate agreed decisions, then apply No AI Slop and verify changed artifacts.

## Exact source receipts read for this summary

These are source references for provenance, not authorization to open files outside the frozen packet. This summary is the packet's concise evidence source; underlying receipt content has been summarized above.

- `evidence/native-client-demo/20260913/authenticated.json` — SHA-256 `e34c9d5411b8a0f32cd65ee2ae29b45136cbdecb0e06cefbd4ea0b06d71742c1`.
- `evidence/native-client-demo/20260913-ui2/receipt.json` — SHA-256 `0b66f7888e1d4e7fc842650fa297c9d2785c856d48eb6e2cd8bf6f264c71448e`.
- `evidence/native-client-demo/20260913-ui2-reconciled-final/reconciliation.json` — SHA-256 `301c4baaf4fc7ff2dbab091c91df9bd89338f301247dd289450fbe2ad051ee0b`.
- `evidence/native-client-demo/20260913-ui2-reconciled-final/review.json` — SHA-256 `e18b6f2e304d800a2734e74d346a07894c34d745c43df69c2b370ff50b9989c9`.
- `evidence/native-client-demo/20260913-ui2/authority-attribution-review.json` — SHA-256 `3bd876c012bf0c0039e4cac74fb63b8736f3104dc947736356d66a7ccfb95642`.
- `evidence/native-client-demo/media-review-mcp-controls.json` — SHA-256 `e7ffdfac58d9c255c3aa538f41ef6c0568142b445c9779483393f684feee051d`.
- `evidence/native-client-demo/media-review-memory-assignment.json` — SHA-256 `68e609282f6cf097fc9ed3f88a1228f4703fee5311a5945cfa98a9dfc78cc167`.
- `evidence/native-client-demo/host-20260913/assignment-diagnostic.json` — SHA-256 `8090b4a69f0c4f76021d6cf1c869f352c188aaa61c31382f3b4e0b19f0ea8a6c`.
