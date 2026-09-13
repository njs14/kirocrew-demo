# No-ai-slop edit

Applied after incorporating the council decisions in `evidence/council/candidate-v3/DECISIONS.md`. The preserved source before this edit is `.build/slides/build-ec2-deck.council-incorporated.mjs`. The exact replacements are in `.build/slides/ec2-no-ai-edits.json`.

I read the full revised slide copy and speaker notes, then checked the edited draft directly against `/Users/noahsutter/.codex/plugins/cache/openai-curated-remote/no-ai-slop/1.0.6/skills/no-ai-slop/eval.md`. I also inspected the diagram labels. The accepted reference image remains unchanged as requested.

The deck keeps the user's concise technical language, exact tool names, AWS/IAM distinctions and direct operating instructions. Its purpose is to explain the EC2 setup and lead into the demonstrated checks while keeping native authentication visibly pending.

## What changed

- Removed the repeated execution-host subheading and sentences that only announced what a table shows.
- Replaced abstract wording with specific actions, such as “The MCP service uses the instance role for fixed S3 calls.”
- Removed review/authoring language from presenter notes. Kept the exact versions, prices, request IDs, source paths and limitations.
- Shortened a few long sentences without flattening the technical detail or changing the nine-slide sequence.

The full edited text and notes are in `output/kirocrew-ec2-demo-copy.md`. The PPTX preserves editable copy and native tables.

## Evaluation

| Eval check | Result |
| --- | --- |
| Editing principles 1: preserve meaning and facts | Pass |
| Editing principles 2: preserve vocabulary and voice | Pass |
| Editing principles 3: leave strong sentences alone | Pass |
| Editing principles 4: proportionate cutting | Pass |
| Editing principles 5: lead with useful information | Pass |
| Editing principles 6: avoid forced uniform structure | Pass |
| Editing principles 7: concrete facts and direct verbs | Pass |
| Editing principles 8: active voice where appropriate | Pass |
| Editing principles 9: preserve useful structure | Pass |
| Editing principles 10: untangle without flattening | Pass |
| Words to cut 1: remove banned words and filler | Pass |
| Patterns 1: remove rhetorical contrasts and throat-clearing | Pass |
| Patterns 2: remove faux insights and robotic phrasing | Pass |
| Patterns 3: preserve facts and named sources | Pass |
| Patterns 4: no fake-profound kicker | Pass |
| Patterns 5: end on concrete operating guidance | Pass |
| Patterns 6: formatting follows the slide content | Pass |
| Patterns 7: colons serve labels and source lists | Pass |
| Patterns 8: no decorative em dashes | Pass |
| Final read 1: checked directly against eval.md | Pass |
| Final read 2: no forced sentence symmetry | Pass |
| Final read 3: recognizable technical voice | Pass |
| Final read 4: natural colleague-facing prose | Pass |
| Final read 5: full edited draft and What changed included | Pass |
| Final read 6: detection-only response | Not applicable, edit requested |

Factual negations remain where they define evidence, such as the absence of AWS dispatch for an MCP-denied call. Exact API names, source paths, source-list punctuation and the fixed reference image are retained for accuracy.
