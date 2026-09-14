# Managed-policy council findings

Both requested reviewers returned **CHANGES REQUIRED** for the frozen 16-slide, nine-clip presentation. Both read all sixteen PNGs as pixels. Their review covers the slide stills, notes and evidence summary, not video playback or a fresh deployment.

HTML SHA-256: `80cc88e8b845a607a9795b9da17840c3df5e96cda80e4c81d17638fd83888eab`.
Notes SHA-256: `3848de8ebf15e0fa5fc6a669015b7f275a6cd354fc3b154778549f6a98fd0ed8`.
Packet manifest SHA-256: `a84aec60ebbec1f1434bbe631b4dfd4fc776746d23e58004401e331784e4ae8f`.

## Agreed substantive direction

| Slides | Decision for incorporation | Reviewer support |
|---|---|---|
| 15 | Caption the product's `CENTRAL POLICY DISTRIBUTION` heading as an unsigned, root-owned local file fetched at startup. Host root can replace it. Avoid implying a deployed fleet-distribution service, SSO or immutable control plane. | Both explicitly request this. |
| 13, 15 | Make managed-policy attribution readable: Policy v1/file identity and the exact governance deny need a legible caption or expanded notice. State that the duplicate owner-editable hook was retired before the new take. Date the Governance evidence and show the policy hash prefix without inventing process continuity. | Both prioritize the protected-source/identity/native-stop chain; Opus requests hook-retirement and date/hash labels, Grok requests a readable denial notice. |
| 14 | Improve the cropped Connections/session evidence. Keep Crew-only local availability, discarded staging, and `0 of 4` deferred specifications distinguishable. A local toggle cannot lift the root-managed execution deny. | Both flag crop/legibility; Grok also requests precise availability wording. |
| 15 | Label the pinned S3 command screenshot as Governance UI evidence. It does not establish a new native managed S3-upload test. Identify the pinned row so an adjacent ordinary rule is not confused with it. | Grok explicitly flags the missing execution distinction; Opus flags ambiguous adjacent rows. |

Preserve the single endpoint-control enclosure, macOS-client/EC2-execution split and eight earlier clips' pre-managed-policy labels. Keep ui4 as the sole filmed managed denial; the allowed managed read remains separately verified and unfilmed. Neither reviewer requests another native take or full deployment as a condition for these presentation edits.

## Other useful refinements

- **Slides 1–2:** Replace broad `MCP controls` or `User settings can narrow access` with local MCP availability. State that EC2 evaluates the execution policy and local availability cannot remove the managed deny. Small root/Crew responsibility labels can help without adding an enclosure.
- **Slide 15:** Call Linux `cc` a loaded policy floor. PTY EPERM and sampled seccomp/NoNewPrivs/namespace evidence are separate observations; the managed tool refusal does not prove exact-tool sandbox execution.
- **Slide 4:** Keep the incomplete host takes visible and improve crowded spacing. A short evidence qualifier can accompany the pre-MCP result.
- **Slides 5–6 and 10:** Use consistent approximate duration wording. Player display rounding versus editorial cut length is not a change to the underlying footage.
- **Slide 16:** Include the `--check` reproduction step if the visible command sequence should match the notes. Preserve the distinction between tested clean-checkout artifact reproduction/fresh ARM bundle and a second full live deployment, which has not run.

## Adjudication boundaries

The missing-MCP-event finding should not erase the supplied complete bounded journal and continuity checks. The supported attribution can retain its scope while briefly naming that evidence. It does not imply universal non-dispatch coverage.

The Governance screenshot's cache-age display is not itself proof of a Gateway restart. Opus requests clearer timing and policy identity. Use actual receipt times and only claim continuity where the existing receipt establishes it; do not invent continuity or treat the 02:20 summary timestamp as every screenshot's capture time.

Opus flags `slide-01.png` versus `slide-1.png` naming. This is the reviewed helper's deliberate source-to-packet normalization: the capture receipt names original source PNGs, while the manifest binds normalized packet names to the exact same hashes. Preparation and decoded payload checks pass. This is not a reason to alter the frozen packet, rebind its metadata or run a second council.

Root's fresh browser playback/seek/pause, image-expansion, diagram and live AWS observations occurred outside the reviewers' frozen packet. They can support final QA but must not be described as checks performed by these reviewers. The historical clips and all earlier raw receipts keep their original scope and bytes.

## Completion evidence

`candidate/review/dispatch/grok-review.md` and `claude-review.md` preserve the original reviews. Their launch records specify Grok Build `grok-4.6` and Claude Code `claude-opus-5`, each with explicit `xhigh`. Actual review-response IDs match. Both completed successfully with every exact PNG payload observed. `council-verified-receipt.json` rechecks frozen bytes, raw-output/launch integrity, prompt identity and image hashes without invoking a model.

Provider-internal effort is not independently visible. Usage accounting includes Grok's `grok-4.6-build` alias and Claude's additional Haiku entry; those do not change the exact observed review-response identities, but no exclusive-internal-model claim is made. The prepared metadata and raw/stdout/stderr files use the project's ignored filenames.

Root owns the final decisions, incorporation, No AI Slop edit and final QA. This is one frozen council review. Its verdict does not become an approval of later edited HTML bytes.
