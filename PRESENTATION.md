# KiroCrew system-design presentation

Open [the standalone 14-slide presentation](output/kirocrew-system-design.html) in a browser. Images, navigation, speaker notes and downloads are embedded in the file. It needs no installation or internet connection to present.

The local preview is at <http://127.0.0.1:5605/> while its preview process is running. Restart it from this project with:

```sh
python3 scripts/serve-presentation.py
```

The preview binds to loopback and serves only this presentation. It does not expose the project directory.

## Presenting

- Use **← / →** or **Space** to advance. **Home / End** select the first or last slide.
- Press **N** for speaker notes, **O** for the slide overview and **F** for full screen.
- Click an architecture image or screenshot to inspect the original. **Escape** closes it.
- Select **Script** to download the [complete slide copy and speaker notes](output/kirocrew-system-design-notes.md).
- Select **Earlier PPTX (12 slides)** to download the accepted ARM PowerPoint, preserved without edits.
- The last slide links to the admin portal at `http://localhost:5599/apps/demo-observability`. The demo's SSH connection must be available to use that link.

The story runs from requirements to the execution boundary, host identities, MCP/AWS results, nightly versions, telemetry, cost and the live walkthrough. Growth decisions are explicitly proposed work. The single endpoint-control box and the six original evidence images are preserved.

## Evidence and review

This presentation uses the September 13, 2026 receipts and screenshots. It does not poll the running system. Native Kiro CLI sign-in and the four-turn native enforcement test remain pending in those receipts. Direct MCP/AWS results are identified separately.

The system-design skill guided the narrative. Grok 4.6 through Grok Build and Opus 5 through Claude Code reviewed the frozen HTML edition, all fourteen slide images and the complete notes. Both requested changes. Their observed model identities and all fourteen exact image payloads per reviewer are verified in the [council receipt](evidence/council/system-design-v1/council-verified-receipt.json). Both launches requested xhigh; provider-internal effort is not independently visible.

The [accepted decisions](evidence/council/system-design-v1/DECISIONS.md) added a separate visible direct-probe flow, clearer reference and native-pending labels, metric and event explanations, identity distinctions and persistent expansion controls. No AI Slop then edited the complete copy and notes. All fourteen final slide captures received an independent visual/content review, and all fourteen layouts passed desktop and 390 × 844 mobile checks. Image expansion and walkthrough notes were exercised again. Existing navigation/fullscreen checks retain their original scope; the navigation code is unchanged. The Print button and physical printing were not exercised.

Council verdicts cover frozen HTML `bfc2516128526ab049a7c4c0b36994aae82d87c44790785ee9125da5d63a5712`. Later edits received author validation; no final-byte council approval is claimed. The original PowerPoint and `ARM-CONTINUATION-RECEIPT.json` remain unchanged. Validation of this presentation does not resolve earlier browser-policy blocks on other viewers.

See [the delivery receipt](evidence/presentation/kirocrew-system-design/delivery-receipt.json) and [browser screenshots](evidence/presentation/kirocrew-system-design/).

## Rebuild

```sh
python3 scripts/build-system-design-presentation.py
```

The builder reads the preserved source deck copy, original images, walkthrough, `presentation/slides.css` and `presentation/slide-runtime.js`. Rebuilding updates the HTML, notes and build manifest. A changed artifact needs a new review receipt.
