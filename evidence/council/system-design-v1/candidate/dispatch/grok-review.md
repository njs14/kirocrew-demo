**CHANGES REQUIRED**

Candidate `system-design-v1` (manifest field only; hashes not recomputed). This is a packet review of notes, evidence-summary, and JPEG pixels. I did not render `presentation.html`, operate the deck, or check live AWS, IAM, Gateway, or CLI state.

The pending-auth story is mostly disciplined: native CLI/session is pending, the direct probe is separate and flagged `native_crew_backend_verified=false`, MCP grants and IAM are distinct, and the live-demo close does not treat sign-in as done. The remaining issues are misread risks and a few observed-vs-configured slips, not a missing packet.

## Image coverage

All 14 JPEGs were read as pixels: `slide-01.jpg` … `slide-14.jpg`. None failed. Nested admin UI on 9–11 is dense; those JPEGs were still read. I did not open Print, Original PPTX, Script, or Open admin portal.

## Findings

1. **Medium — slide 9.** The telemetry capture’s largest chips are **TURN LATENCY (P90) 0ms**, **FAULT RATE 0%**, **THROUGHPUT 0**, with a **Last 14d** control. Notes correctly say a displayed zero turn latency is not a measured model session, and the left rail says model-session metrics are pending. Those chips still read as a measured native session. **Revise:** strike or annotate the three chips on the image; keep the 14d-vs-7-day and single-boot-percentile footers.

2. **Medium — slide 4.** The only drawn MCP edge is the dashed **MCP pending** Gateway→MCP path. The verified path is caption-only: `mcp-demo → MCP → S3` at 15:01:37 UTC. An AWS reader can think S3 results on slide 7 rode the pending native path. **Revise:** draw a solid in-host **direct probe** arrow; leave Gateway→MCP dashed.

3. **Low — slide 3.** The required endpoint-control box is present, remote mode is stated, and the footer unswears sandbox, egress, and SEL/HMAC. The graphic still shows EDR/MDM, network egress, OS sandbox, HMAC-chain, protected configuration, and Codex/Claude Code more loudly than the disclaimer. **Revise:** keep the box; badge it **reference, not this demo**. Do not add OAuth, signed policy, tamper resistance, or egress as facts.

4. **Low — slide 5.** Column title is **Authority and observed boundary**, but mcp-demo lists **SSM core permissions** next to the crew **errno 113** TCP check (14:56:15 UTC). Evidence records the IMDS deny and S3 allow/deny via the instance role; it does not show SSM exercised. **Revise:** split **Observed** (TCP 113, no HTTP/token) from **Role policy** (two prefixes, explicit deny, SSM core attached).

5. **Low — slide 5.** Evidence: crew can edit **configuration and installed custom App Kit code**. The slide only says configuration. That understates the write surface beside root-owned Gateway/MCP files. **Revise:** one line that App Kit files are crew-writable; immutable policy remains unverified.

6. **Low — slide 10.** On-slide **authenticated Gateway proxy** matches the evidence phrase, but after slides 1–2 and 8 it can be heard as Kiro CLI auth. Evidence: owner-token/admin portal path; CLI still unauthenticated at **15:19 UTC**; KAS GitHub card is another store. **Revise:** **admin portal / owner token**, not CLI.

7. **Low — slides 10–11.** Key claims (4% / 772.4 MiB, 6.2% / 14.6 GiB, 0 processes, Gateway/MCP Yes) are readable; collection-log rows are not, and only slide 9 says expand. **Revise:** expand cue, or crop the 0-process client and the PID/start-time claim (receipt: PID **4991**, start **14:26:10 UTC**).

8. **Low — slides 4 and 12.** Cost introduces a **stopped x86** rollback disk ($1.92/month) that the architecture slide never names. Evidence: original **t3a.small** stopped; **24 GiB** gp3 retained. **Revise:** one clause on slide 4 or 12: stopped t3a.small disk retained for rollback.

## Agreement priorities

1. **No native approval receipt.** CLI 15:19 UTC unauthenticated; probe 15:01:37 UTC has `native_crew_backend_verified=false`; `crew_denied` is configured only; KAS GitHub card is not CLI auth; slide 10 proxy auth is not a backend session.

2. **Keep one execution host.** EC2 holds Gateway, selected backend, workspace, MCP, and the endpoint-control enclosure; the Mac is client with local Gateway off. Annotate unverified layers; do not delete the box or promote EDR, egress, sandbox, or HMAC.

3. **Do not collapse probes or telemetry classes.** Direct MCP/IAM (55-byte SHA prefix `34ebbefeb5f66527…`, `FC4GTZS0B83EQ5W1`, `tool_grant_denied`, S3 403 `BA5BT7K9765938BT`) is not a desktop e2e run. Native Gateway metrics ≠ App Kit samples ≠ collection events ≠ SEL. Mac nightly **20260913t061222** ≠ server **20260912t060850** unofficial ARM repack.

## Material unknowns

Native CLI sign-in and four-turn approval, including automatic pre-MCP `crew_denied`. IPv6 IMDS and native sandbox. Behavioral equivalence of the two nightlies and CLI 2.21.4 vs the Gateway repack. Native-session capacity, latency, throttle under standard T4g credits, failover/RTO. Model-turn metrics and session survival across client quit. Tamper resistance. Whether the 64 MiB metrics target is exceeded. Live AWS/SG/IAM/CLI state (receipts are 13 Sep 2026; this packet does not poll). Interactive HTML (portal button, PPTX, print). IMDSv2 hop-limit appears in speaker notes only, not in evidence-summary.
