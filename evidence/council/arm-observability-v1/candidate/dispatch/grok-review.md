**CHANGES REQUIRED**

The packet is a careful ARM-plus-observability demo for an AWS/IAM audience: laptop as client, one EC2 execution host, MCP grants vs IAM as separate stops, and native Kiro CLI sign-in still pending. It should not ship until the observability timestamps and the cost/capacity line cannot be misread. This review used only the allowed files; I did not open `deck.pptx`, hash the packet, or check live AWS.

### Image coverage
All twelve PNGs were read as pixels. None failed.

| Image | Pixels | Notes |
|---|---|---|
| slide-1.png–slide-7.png, slide-11.png–slide-12.png | Readable | Clean type; tables on 4–6 legible |
| slide-2.png | Readable | Frozen endpoint-control box intact; dense type; “Policy n Profile” is truncated inside that box |
| slide-8.png | Readable | Native Latency pane; “Last 14d” chrome is clear |
| slide-9.png | Readable | Custom Client/Server cards; 4% / 772.4 MiB and 6.2% / 14.6 GiB match the summary |
| slide-10.png | Readable | Four collection events; clocks are local |

### Findings
1. **Medium — slide 8.** Caption: local export, **7-day** retention, 64 MiB target, no OTLP. Screenshot chrome: **Last 14d**. `kirocrew.gateway.boot.duration` has **1 sample**, which reads as this process, not a 14-day series. **Revise:** label the chrome as view range, not retention (or crop it), and keep “7 days / 64 MiB **target**.”

2. **Medium — slides 9–10.** Evidence uses UTC (Mac 14:43:14Z, EC2 14:43:35Z, stop 14:44:42Z, relaunch 14:49:34Z). Screenshots show **10:43 / 10:44 / 10:49** with no zone; slide 10’s title is UTC. Notes say Eastern (UTC-4); the slide does not. **Revise:** one on-slide line, e.g. “Screenshot clocks EDT (UTC-4).”

3. **Medium — slide 10.** Title and PID **4991** claim the Gateway survived the quit. The table only shows client health at 10:44:42 and 10:49:34; the last server row is “First sample collected” at 10:31:23. Notes cite a client-stopped frame that is not on the slide. **Revise:** add that frame, or a receipt line that server checks stayed Yes and PID 4991 was unchanged.

4. **Medium — slide 12.** Notes/summary: **standard** CPU credits, On Demand t4g.xlarge **$0.1344** + IPv4 **$0.005** → **$0.1394** ≈ **$0.139**/h; 40 GiB gp3 **$3.20**; stopped x86 **24 GiB $1.92**; 730 h → **~$107** with both disks. The slide omits credit mode and **t3a.small**. Unlimited credits would break the rate. **Revise:** “t4g.xlarge standard credits; stopped t3a.small 24 GiB still billed.”

5. **Low — slide 8.** With n=1, boot **min=max=1.8s** but **p50=1.5s / p90=1.9s**. **Revise:** speaker note that n=1 percentiles are UI artifacts, not a measured boot distribution.

6. **Low — slide 5.** `crew_denied` sits in the same expected-result table as receipt-backed calls. The magenta footer is correct; the row still looks executable. **Revise:** mark that row “configured, not native-probed.”

7. **Low — slide 3.** Host split is right (laptop client; EC2 has Gateway, Kiro CLI, workspace, MCP). The diagram omits loopback **9102** App Kit, which is the custom telemetry path. **Revise:** a small “Demo Observability :9102” in the Crew box.

8. **Low — slide 2.** “Reference map. Verified here: remote client, MCP grants and S3 IAM checks” matches the summary. The box still shows egress, sandbox, HMAC-chain. **Revise:** do **not** replace the box; keep the verified-here line as the only execution claim.

### Agreement priorities
1. Native Kiro CLI login, approval cards, `crew_denied` before dispatch, model-turn metrics, and session survival stay **PENDING**. The ARM `direct_mcp_service_probe` at **2026-09-13T14:07:16Z** (`native_crew_backend_verified=false`) must not be narrated as a Crew session.
2. Split telemetry on-slide: native Gateway **local** export (config vs this pane) vs custom App Kit samples vs no CloudWatch, RUM, traces, or HMAC/SEL audit chain. Fix the 14d vs 7-day chrome and EDT vs UTC clocks before ACCEPT.
3. Keep the frozen endpoint-control image. Architecture remains one remote host plus a laptop client. Cost/capacity must name **t4g.xlarge / standard credits / 40 GiB** and **stopped t3a.small 24 GiB**.

### Material unknowns
Instance IDs across the 14:07 probe, 14:22 cloud check, and 14:43–14:50 observability receipts are asserted, not shown here. Metadata-firewall and IMDSv2 hop-limit **1** are described, not receipt-shown. Whether “Last 14d” holds data older than seven days is unknown. Device-login success is unproven. I did not hash files, inspect the PPTX, or verify live AWS.
