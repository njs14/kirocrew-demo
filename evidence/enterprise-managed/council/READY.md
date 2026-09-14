# Managed-policy council interface

Preflight only. No candidate packet or model review has started. Root will supply the finished candidate and authorize dispatch once. The new runner preserves all existing preparation, launch and verification behavior; only its review prompt and the location of its frozen launch-policy copy differ from the current native-deck helper.

Inputs for the single frozen review:

- Final HTML and its complete exact text/presenter notes.
- Final slide count, expected 14–16. The reviewed runner already accepts dynamic counts through 60.
- One PNG per slide, named either `slide-1.png` … `slide-N.png` or `slide-01.png` … `slide-N.png`; no duplicates or extra numbered PNGs. Files must contain actual PNG bytes. If the capture tool produces JPEG, preserve the originals and record lossless decoded-pixel conversion before preparation.
- One capture receipt binding the HTML SHA-256 and every source screenshot SHA-256, with the following shape:

```json
{
  "deck_sha256": "<final HTML SHA-256>",
  "slide_count": 16,
  "capture_method": "<actual browser capture method>",
  "slides": [
    {"number": 1, "file": "slide-01.png", "sha256": "<exact screenshot SHA-256>"}
  ]
}
```

The `slides` list must contain one ordered row for every slide. Its file names must match the actual source files. The new sanitized evidence summary will cite the final managed-policy/MCP/replication receipts and preserve the dated native outcomes and remaining gaps. No private credentials, sessions, raw security-event dumps or owner-token material belong in the packet.

Prepare once using `run-council.py prepare` with `--candidate`, `--deck`, `--slides`, `--notes`, `--evidence`, `--capture-receipt`, `--output` and `--slide-count`. Preparation does not invoke a model. It records the manifest hash, freezes the input files in a private temporary directory outside HOME and binds the runner plus launch policy.

After root supplies the final candidate and says to proceed, `run-council.py run --prepared <prepared.json> --confirm-manifest <recorded manifest SHA-256>` dispatches both reviewers concurrently. The default attempt directory is fresh and cannot overwrite earlier receipts.

Grok Build uses `grok-4.6` with `--reasoning-effort xhigh`, strict sandbox and only `read_file`. Claude Code uses `claude-opus-5` with `--effort xhigh`, safe/restricted mode and only `Read`. Both preserve their own normal product authentication; the filtered environment excludes cloud/API credentials and MCP/browser/write tools are disabled. Model substitutions are not permitted.

Completion requires the exact observed response model, every exact PNG payload hash, a successful terminal response and unchanged frozen packet. Provider-internal effort is not independently visible; explicit launch settings are recorded. Usage aliases or helper model accounting remain separate from review-response identity.

Deliver one concise synthesis and the raw/model/image receipts. Root incorporates agreed findings and then applies No AI Slop. Browser playback and live deployment verification remain outside the council. Do not repeat full reviews for bookkeeping changes or relabel prior receipts as reviews of later bytes.

The project skill's `docs/DECK-COUNCIL.md` reference is currently missing. The actual native helper, its launch-policy source and historical receipts were inspected directly; the missing documentation does not add an approval requirement.
