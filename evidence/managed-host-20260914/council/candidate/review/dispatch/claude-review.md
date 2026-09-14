**Verdict: CHANGES REQUIRED**

**Image coverage:** All 19 PNGs (slide-1 … slide-19) read as pixels; manifest and receipt SHA-256 values agree for every slide. Visual coverage limit: each video slide shows only the poster/first frame at 0:00 plus controls. Playback, seeking, chapter jumps and non-poster frames are not verified; media statements below rely on notes.md and evidence-summary.md at that scope. presentation.html was not read; no live checks were made.

**New-case identification (slides 14–16)**

- **Slide 14 – sensitive read.** Request: fs_read `/home/crew/.aws/kirocrew-demo-control-canary.txt` (tool_call_id `…MFDrBC…`). Attempt: one native fs_read, no approval, no block. Result: CLI argument-validation ENOENT. Layer: filesystem/OS (tmpfs mask at `/home/crew/.aws` in mount ns `4026532521` for PIDs 275306/275313), *not* a policy/hook denial. Attribution: post-hoc readback at 13:13:38Z (result was 13:05:47Z), current descendants only, no syscall-PID binding; receipt `accepted:false`, `missing_evidence: namespace_cause_not_established`.
- **Slide 15 – protected write.** Request: fs_write marker under `.kiro/agents/.demo-host-controls/…ui1.txt` (`…3SWMc7…`). Attempt: one fs_write, no approval. Result: automatic block. Layer: policy/hook denial by `crew_write_protected_path_hook`, SEL `6e1003553ace4e4b`, target absent before/after; managed filesystem rule not reached. `accepted:true`.
- **Slide 16 – IMDS TCP.** Request: execute `/opt/kirocrew-demo/host-controls/imds-tcp.py`. Two Allow-once approvals (source read `…EDftjV…` at 13:28:54Z — a read, not execution; execution `…Sd4g37…` at 13:29:09Z). Result: helper self-reports `connected:false`, errno 113, 0 bytes, `native_enforcement_verified:false`. Layer: IPv4 metadata TCP isolation via UID-999 OUTPUT REJECT; counter +1 packet/60 bytes. No per-packet tool-ID or PID; not whole-host, IPv6, HTTP or credential test. `accepted:true`.

Earlier slides 5–12 stay "Before managed policy"; slide 13 is the only managed-policy denial. Single enclosure preserved (slide 2).

**Findings**

1. **HIGH – Slides 18 notes + "Managed source and limits" (notes.md:73, 179).** "Sensitive-path read, protected-path write and native IMDS execution remain unfinished" contradicts slides 14–16 and the evidence summary. This is the 02:20Z summary text carried forward undated. Revision: date it ("as of the 02:20 UTC summary…") and add that the 13:04–13:29Z takes on slides 14–16 later completed them with their own receipts, or delete.

2. **MEDIUM – Slide 4 legibility.** Last row's caption "September 14 host take. Request to result. 0:55" overlaps the footer "Recording coverage and server attribution are separate. Page 2 of 2." This is the updated control map. Revision: tighten row spacing or move the footer.

3. **MEDIUM – Slide 14 on-slide status.** The slide reads as a completed control ("Where each request stops", decision point "CLI validation") but the native receipt is `accepted:false`. Only the notes say so. Revision: footer add "Native receipt: accepted:false; cause corroborated for current descendants only."

4. **MEDIUM – Slide 15 enforcer ownership.** Slide 6 calls the earlier MCP hook "owner-editable"; slide 15 calls this one "Built-in Crew hook". Nothing in the packet states whether `crew_write_protected_path_hook` is root-managed or Crew-editable — the question an IAM audience asks first. Revision: state owner/mutability, or mark unknown on slide and notes.

5. **LOW – Slide 16 wording.** Title "the host rejects TCP" is broader than the UID-scoped rule; subtitle "…169.254.169.254:80" — port 80 appears nowhere in imds-tcp.json (rule is /32, no port). Revision: "a UID firewall rule rejects TCP"; drop ":80" unless the helper source receipt states it.

6. **LOW – Slide 19 duplicate label.** "New recording scope and quality" appears twice in the evidence list. Revision: distinguish targets (managed MCP vs. host takes) or remove.

7. **LOW – Slide 13 clipping.** Right-panel chapter description is cut mid-sentence behind a scrollbar; Print/PDF loses it. Revision: shorten or allow wrap.

8. **LOW – capture-receipt.json names.** Receipt lists `slide-01.png…slide-09.png`; manifest and disk use `slide-1.png…slide-9.png`. Hashes match, so binding holds by digest only. Revision: align names.

Non-defect note for root's No AI Slop pass: slide 4 and 16 notes repeat the same limitation sentences verbatim two to three times; slide 4 notes run ~600 words.

**Agreement priorities for the other reviewer**

1. Finding 1: the "remain unfinished" sentence must be dated or removed before acceptance.
2. Layer labels for slides 14–16: OS-namespace mask (not a denial, `accepted:false`), Crew hook (pre-managed-rule), UID IPv4 firewall — none is managed-policy proof; keep "September 14 host take" headers and do not promote or reset them.
3. Slide 4 overlap plus slide 14 footer status as the minimum visual/factual fixes on the control map.

**Material unknowns**

- Video content past poster frames, chapter seeking, and whether cuts show what notes claim.
- Ownership/mutability of `crew_write_protected_path_hook`.
- Helper target port; IPv6 and non-IMDS egress untested.
- Completeness of the MCP journal and Gateway process-continuity for the ui4 interval — asserted in notes, not in this packet.
- Whether the two slide-19 links resolve to one or two receipts.
- The exact-artifact browser-acceptance receipt referenced on slide 19 notes is not in the packet; no independent final-byte verdict exists per evidence-summary.
