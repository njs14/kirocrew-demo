# No AI Slop edit

Applied after all decisions in `evidence/council/arm-observability-v1/DECISIONS.md`, including the revised ARM image. The full incorporated draft was read before editing. The source before this pass is `.build/slides/build-arm-observability-deck.council-incorporated.mjs`; `.build/slides/arm-no-ai-edits.json` records the 13 minimum edits.

The deck addresses an AWS/IAM audience and leads into the remote-client, direct-probe and observability walkthrough. Its voice is direct technical prose: exact tool names, plain operating instructions, measured outcomes and explicit limits. The edit preserves those traits and the 12-slide structure.

The edited copy and notes were checked directly against the skill's `eval.md`, then extracted from the final PPTX and read again. Image labels were visually inspected. The accepted endpoint reference and actual screenshots remain byte-preserved evidence; their original text was not rewritten.

## What changed

- Incorporated the Grok and Opus decisions before the writing pass: verification-state labels, current probe receipts, time-zone and metric-window captions, configuration limits and CPU-credit costs.
- Replaced unclear phrases such as “bundle lanes” with the actual arm64 and x64 bundle names, and shortened repeated explanations.
- Kept exact versions, tool names, request IDs, timings, source paths and pending native checks. Original reference and screenshot image bytes remain intact.

## Evaluation

| Check | Result |
| --- | --- |
| Editing principles 1: preserve meaning and facts | Pass |
| Editing principles 2: preserve technical voice | Pass |
| Editing principles 3: leave clear sentences intact | Pass |
| Editing principles 4: proportionate cutting | Pass |
| Editing principles 5: useful information first | Pass |
| Editing principles 6: avoid forced structure | Pass |
| Editing principles 7: concrete details and verbs | Pass |
| Editing principles 8: active voice where appropriate | Pass |
| Editing principles 9: preserve useful structure | Pass |
| Editing principles 10: untangle without flattening | Pass |
| Words to cut 1: banned terms and filler | Pass |
| Patterns 1: no rhetorical binary contrasts or throat-clearing | Pass |
| Patterns 2: no faux insights or robotic phrasing | Pass |
| Patterns 3: named evidence instead of puffery | Pass |
| Patterns 4: no fake-profound ending | Pass |
| Patterns 5: ends on operating guidance | Pass |
| Patterns 6: content-led formatting | Pass |
| Patterns 7: colons used for labels and sources | Pass |
| Patterns 8: no decorative em dashes | Pass |
| Final read 1: checked directly against eval.md | Pass |
| Final read 2: no forced sentence symmetry | Pass |
| Final read 3: recognizable technical voice | Pass |
| Final read 4: natural colleague-facing prose | Pass |
| Final read 5: full edited draft and What changed | Pass |
| Final read 6: detection-only request | Not applicable; edit requested |

Factual exclusions remain where they define the evidence, such as native-session verification being pending and the absence of an HTTP request in the crew metadata probe. These are technical limits, not rhetorical contrasts. Anonymous usage reporting retains its precise meaning with simpler wording. No claim, result or example was added by this writing pass.
