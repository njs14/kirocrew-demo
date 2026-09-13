## 1. Verdict

**CHANGES REQUIRED.** Every number I could cross-check (t4g.xlarge 4 vCPU/16 GiB, 40 GiB gp3, $0.1344 + $0.005 = $0.1394 → $0.139, 40 GiB×$0.08 = $3.20, 24 GiB×$0.08 = $1.92, 730 h → $106.882 ≈ $107, 24 paths × 2 lanes = 48 RECORD checks, request IDs, digest prefix) agrees with `evidence-summary.md` and `notes.md`. The pending/verified discipline in slide *text* is unusually good. The defects are in what the *visuals* imply and in evidence that is asserted on-slide but not shown: the architecture diagram styles a pending path as verified, screenshot times contradict on-slide times, and three separate time intervals read as one run. All are fixable without new lab work.

## 2. Image coverage

All 12 PNGs (slide-1 … slide-12) read as pixels and were legible at full size. **None failed to render.** I did not open or render `deck.pptx`, and I did not verify any live AWS, Gateway, or backend state; my reading of slide text comes from the PNGs plus `notes.md`.

## 3. Findings

| # | Sev | Slide | Evidence | Minimal revision |
|---|---|---|---|---|
| 1 | **High** | 3 | Diagram draws Laptop→Gateway+Kiro CLI→**MCP**→S3 as one chain, with the Gateway→MCP and MCP→S3 legs in identical solid green. Only the direct probe (`mcp-demo` on EC2 → MCP loopback 8001 → S3) is receipt-backed; Kiro CLI is unauthenticated, so the Gateway→MCP leg is configured-but-untested. Slide 3 is the only structural slide with no pending marker. | Dash the Gateway→MCP leg, label it "native path — pending sign-in", and add a footer: "Verified here: direct MCP probe (mcp-demo → MCP → S3)." |
| 2 | **High** | 10 | Headline reads "Client stopped: 14:44:42 UTC · Relaunched: 14:49:34 UTC"; the screenshot directly beneath reads `10:44:42` and `10:49:34`. The UTC−4 offset appears only in speaker notes. Same mismatch latent on slide 9 (notes narrate 14:43:14 UTC over a `10:43:14` card). | Add "screenshot times are local Eastern (UTC−4)" to slides 9 and 10. |
| 3 | **Medium** | 10 | The slide's load-bearing claim, "EC2 Gateway PID 4991 stayed running through the client restart," is not in the displayed artifact. The collection log shows only two generic `Health checks changed` client rows (warning/info); no PID, no start time, no server row in that window. The stopped-client screenshot cited in notes (`13-client-stopped.jpg`) is not on the slide. | Add the stopped-client panel or a PID/start-time readout, or re-word to "per collector receipt: Gateway PID 4991, started 14:26:10 UTC, unchanged." |
| 4 | **Medium** | 6 (and 1) | Three disjoint intervals on 2026-09-13 are presented as one demo: probe **14:07:16Z**; cloud verification **14:22:25Z**; Gateway PID 4991 start **14:26:10Z**; first collector samples **14:31:23Z** (server) / **14:34:59Z** (client); readback **14:50:25Z**. The enforcement probe therefore predates both the running Gateway process and the entire telemetry window. | One line on slide 6: "Separate run — this probe precedes the current Gateway process and the telemetry window; no single end-to-end session is claimed." |
| 5 | **Medium** | 2 | The preserved reference box advertises `network egress`, `exfiltration checks`, `OS sandbox`, `SEL events · HMAC-chain verification`. None is demonstrated. The "Reference map. Verified here: remote client, MCP grants and S3 IAM checks." disclaimer is small, low-contrast, and visually subordinate to the box. (Also: `Policy n Profile` looks like a fallback glyph for `∩`.) | Promote the disclaimer to the deck's red pending style and name the exclusions: "Not demonstrated: sandbox, egress control, SEL/HMAC chain." Glyph fix requires re-accepting the byte-preserved image — flag, don't silently edit. |
| 6 | **Medium** | 4 | "Firewall blocks metadata for the crew UID" is presented as an effective control; the packet cites only configuration sources (`bootstrap.sh`, `ec2-demo.json`) — no receipt of a *blocked* crew-UID IMDS request. Separately, "Crew owns and can edit its configuration" and the root-trusted model (notes) never reach a slide, so the table reads as stronger isolation than claimed. | Mark the row "configured; no blocked-request receipt in this packet," and add a footnote: "Crew can edit its own configuration; no tamper resistance claimed." |
| 7 | **Medium** | 12 | CPU-credit mode appears nowhere in slide text. Standard mode is precisely what makes $0.139/h a ceiling (no surplus-credit charges) and what implies throttling to baseline under sustained load — material to an AWS-fluent audience on a burstable t4g. | Add "Standard CPU credits — no surplus charges; sustained load throttles to baseline." |
| 8 | **Low** | 8 | Screenshot header reads `Last 14d` while the caption reads "7 days" retention and "10 s" export; the explanatory line ("Log scale, each profile against its own min–max…") is dim gray on black and will not survive projection. | Caption "14 d display window · 7 d retention"; lighten or move that line out of the screenshot. |
| 9 | **Low** | 9 | `4 %` (client, sum of process-family scheduler averages, can exceed 100%) and `6.2 %` (server, one-second host-wide sample) sit side by side as headline figures; the distinction lives only in screenshot small print. | Add "Client CPU = KiroCrew process family; server CPU = whole host. Not comparable." |
| 10 | **Low** | 7 | Server build is a **custom, unofficial** ARM64 repack one nightly behind the Mac client, with three differing paths and no behavioral-equivalence claim — the slide says only "Custom ARM64 repack". | Append: "Not an official Linux release; client is one nightly ahead — no behavioral equivalence claimed." |

## 4. Agreement priorities for the other council member

1. **Slide 3 styling must encode verification state.** Verified direct-probe legs and the pending native Gateway leg cannot share one visual grammar. This is the deck's single largest overclaim risk.
2. **Every screenshot carries its own clock and window label**, and the deck states plainly that probe, Gateway process, and telemetry window are three intervals — not one end-to-end run (findings 2 and 4).
3. **No claim without its artifact or an explicit "per receipt / configured only" label** — specifically PID 4991 continuity and the crew-UID metadata firewall (findings 3 and 6).

## 5. Material unknowns

- I read PNG renders and `notes.md`; I did not open `deck.pptx`. On-slide/notes fidelity, fonts at projection size, table editability, and the `a:srcRect` crops are unverified by me.
- No underlying receipts are in the packet (`mcp-live-receipt.json`, `observability-api-readback.json`, `final-cloud-verification.json`, `host-checks.txt`, `price.json`). Digests, request IDs, PID, `native_crew_backend_verified=false`, and the 14:22:25Z verification are as-summarized only.
- I computed no SHA-256; the manifest hash and candidate ID in the prompt are unchecked.
- Whether a negative-test receipt exists for the crew-UID metadata block, and whether standard credit mode is receipt-confirmed rather than asserted.
- Slide 2's reference image cites a September 11 baseline; its provenance relative to the September 13 evidence is not established here.
- Whether t4g.xlarge baseline CPU is adequate for the eventual authenticated model-session demo — untestable while sign-in is pending.
