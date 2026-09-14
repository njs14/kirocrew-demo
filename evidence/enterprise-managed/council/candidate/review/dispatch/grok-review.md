**CHANGES REQUIRED**

Candidate `enterprise-managed-v1`. Binding docs and all 16 named PNGs were read as pixels (`slide-1.png` … `slide-16.png`). None unread. `capture-receipt.json` aliases `slide-01.png`–`slide-09.png` with SHA-256 values that match these files; this review did not recompute hashes.

Coverage is 1280×720 sequential browser stills of the 16 slides. Video slides show a result-frame poster at `0:00`, chapter lists, and player chrome. **Screenshots show posters and media controls; they do not prove playback, seeking, or any other video frame.** Capture resumed at slide 11 after a tool timeout; slides 11–16 are distinct. HTML was not executed; links were not followed.

The single EC2 endpoint-control enclosure is preserved (slide 2). Clips 5–12 stay labeled **before managed policy**. Host gaps (sensitive-path read, protected-path write, IMDS execution) remain unfinished on slide 4. Slide 12 keeps `native_enforcement_verified:false`. Slide 16 is local rebuild vs live setup, not restore, retention, or failover.

### Findings

1. **High — slide 15.** The Governance still’s **CENTRAL POLICY DISTRIBUTION** badge is the visual policy-identity proof. Packet: unsigned local file `/etc/kirocrew-demo/security-policy.json`, SHA-256 `ca6c7e60…`, startup-only fetch, host root can replace; no signed fleet policy, enterprise SSO, or immutable control plane. **Revision:** Caption the badge as product chrome for a root-owned local file, not fleet/central distribution; keep Policy v1, `Source: file`, and host-root replaceability.

2. **High — slide 15.** **An administrator-pinned command** plus the on/disabled S3-upload switch reads as a running host control. Packet: UI evidence only; no native S3-upload command under the managed policy. **Revision:** “Governance UI; no native S3-upload test in this edition.”

3. **Medium — slide 1.** “The Mac supplies prompts, approvals and **MCP controls**” puts MCP authorization on the client. Packet: MCP is a separate EC2 process with fixed demo grants and the instance role; Gateway loads the file policy; Mac Connections only toggles local availability. **Revision:** Mac supplies prompts, approvals, and local MCP availability; the EC2 Gateway evaluates execution policy.

4. **Medium — slide 13.** The only managed native take is a dark poster; the expanded host notice (governance policy, exact `@aws-enforcement/crew_denied`) is not legible at this capture. A server-enforced managed rule needs a native stop at the claimed layer that an AWS/IAM viewer can actually read. **Revision:** Add a readable crop of the expanded notice; do not replace clip bytes.

5. **Medium — slide 4.** Visible result **Blocked before MCP dispatch** treats a missing event as a dispatch proof. Packet: no matching arrival in a complete, stable MCP journal with continuity; SEL has no direct native trace/tool-ID field. **Revision:** “No arrival in a bounded, continuous MCP journal interval.”

6. **Medium — slide 15.** **Linux cc minimum** sits with Policy v1 as demonstrated isolation. Packet: cc is a loaded floor; PTY `EPERM` and seccomp/NoNewPrivs/mount-namespace checks are point-in-time and not exact-tool sandbox; Linux cc is not macOS Seatbelt or strict-tier isolation. The ui4 policy-layer deny does not prove sandbox execution. **Revision:** Label cc a loaded floor; state no exact-tool sandbox proof.

7. **Medium — slide 14.** The restriction row is cropped (`ools as opted-in.`); the session inventory is clipped. Packet: the staged `crew_denied` restriction was discarded and not applied; the session reports `0 of 4` specs loaded and deferred tools. A local enable/discard is not removal of the root-managed deny. **Revision:** Uncropped stills of Crew-only enable, discarded restriction, and `0/4` deferred tools.

8. **Medium — slide 2.** Footer **User settings can narrow access** can be read as weakening managed policy. Packet: ordinary Crew config can hide tools; it cannot lift the root-managed deny. **Revision:** “Local MCP availability can hide tools; it cannot lift the root-managed deny.” Keep the one EC2 enclosure.

### Agreement priorities

1. Keep the managed claim to protected file source + Policy v1 identity + ui4 native stop; do not let Governance chrome or the S3 pin expand that set.
2. Treat slide 13 poster legibility as a proof issue, not decoration.
3. Keep Mac client vs EC2 Gateway / original Kiro CLI / workspace / MCP, and operator vs host-root, aligned on slides 1–2 and 14–15; do not split the enclosure.

### Material unknowns

- Playback, seeking, and non-poster frames.
- `presentation.html` and linked tours/receipts (hashes only in notes).
- GitHub backend login (cited, not in these stills).
- Body of the unfilmed managed allowed read.
- Whether GLOBALS “Kiro” on slide 14 contradicts “provider-global off.”
- Pixel-hash recompute (not executed).
- HTML-session continuity across the slide-11 capture resume.

Do not promote the unfilmed allowed read, PTY/seccomp samples, or older clips into full managed-policy acceptance. Do not invent SSO, a central MCP registry, immutable policy, protected audit storage, or failover. Telemetry, SEL receipts, and the MCP journal stay separate on slide 15; leave that split.
