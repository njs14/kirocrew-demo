# Native host-control council: ready interface

Preflight only. No candidate packet or inference has started. Expect one frozen candidate, approximately 19 slides and 12 clips. All slide PNGs and complete notes will be reviewed, with extra attention to the three new host-control cases and updated control map. The screenshots cannot establish playback or every recorded frame.

Root supplies the final HTML and notes with SHA-256 values, slide count, one real PNG per slide, a capture receipt, and public factual receipt/manifest paths for the new takes. Source PNG names may be `slide-01.png` … `slide-19.png` or unpadded equivalents; duplicates and extra numbered PNGs are rejected. Any JPEG-to-PNG conversion should retain original captures and document decoded-pixel identity.

The capture receipt schema is:

```json
{
  "deck_sha256": "<final HTML SHA-256>",
  "slide_count": 19,
  "capture_method": "<actual browser capture method>",
  "slides": [
    {"number": 1, "file": "slide-01.png", "sha256": "<exact source PNG SHA-256>"}
  ]
}
```

Include one ordered row for every slide. The receipt refers to source filenames; the packet intentionally normalizes names to `slide-1.png` onward while preserving hashes. This is not a metadata error.

After root confirms the candidate is frozen, prepare once:

```text
python3 -B evidence/managed-host-20260914/council/run-council.py prepare
  --candidate managed-host-v1
  --deck <final HTML>
  --notes <complete notes>
  --slides <PNG directory>
  --slide-count 19
  --evidence evidence/managed-host-20260914/council/evidence-summary.md
  --capture-receipt <capture receipt JSON>
  --output evidence/managed-host-20260914/council/candidate/review
```

The output directory must be new. Preparation is local and invokes no model. It produces the ignored `prepared.json`, freezes the allowed packet outside HOME, and binds the candidate, images, capture receipt, prompt runner and launch policy.

Start the single concurrent council after preparation:

```text
python3 -B evidence/managed-host-20260914/council/run-council.py run
  --prepared evidence/managed-host-20260914/council/candidate/review/prepared.json
  --confirm-manifest <SHA-256 returned by prepare>
```

The exact models remain Grok Build `grok-4.6` with `--reasoning-effort xhigh` and Claude Code `claude-opus-5` with `--effort xhigh`. Existing read-only launch restrictions and normal product authentication remain unchanged. No fallback model, new account, credential transfer or live AWS/UI operation is part of this task. CLI availability and schemas are verified; current inference entitlement is not exercised before dispatch.

Completion requires exact observed review-response identities, every PNG's decoded payload hash, a successful terminal result and unchanged packet. Record any usage aliases/helper accounting separately; provider-internal effort is not independently visible. Preserve earlier councils at their original scope. Return one concise synthesis; root incorporates agreed findings, applies No AI Slop and performs final QA.

The local `.gitignore` protects only the prepared metadata and standard raw/stderr filenames. Concise reviews, receipts and decisions remain includable.
