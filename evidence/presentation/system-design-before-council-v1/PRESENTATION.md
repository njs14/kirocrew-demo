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
- Select **Original PPTX** to download the accepted 12-slide PowerPoint, preserved without edits.
- The last slide links to the admin portal at `http://localhost:5599/apps/demo-observability`. The demo's SSH connection must be available to use that link.

The story runs from requirements to the execution boundary, host identities, MCP/AWS results, nightly versions, telemetry, cost and the live walkthrough. Growth decisions are explicitly proposed work. The single endpoint-control box and the six original evidence images are preserved.

## Evidence and review

This presentation uses the September 13, 2026 receipts and screenshots. It does not poll the running system. Native Kiro CLI sign-in and the four-turn native enforcement test remain pending in those receipts. Direct MCP/AWS results are identified separately.

The system-design skill guided the narrative. The No AI Slop pass edited the complete slide copy and notes. All 14 slides received browser layout checks and an independent visual/content review; corrected slides were reviewed again. Navigation, notes, image expansion, full screen and mobile navigation were exercised. Desktop and 390 × 844 mobile checks are recorded with the delivery receipt. The Print button and physical printing were not exercised.

The prior Grok/Opus council verdict applies to the frozen PPTX candidate. Its accepted evidence boundaries are preserved here; this HTML edition has no new external council verdict. The original PowerPoint and `ARM-CONTINUATION-RECEIPT.json` remain unchanged. Validation of this new presentation does not resolve earlier browser-policy blocks on other viewers.

See [the delivery receipt](evidence/presentation/kirocrew-system-design/delivery-receipt.json) and [browser screenshots](evidence/presentation/kirocrew-system-design/).

## Rebuild

```sh
python3 scripts/build-system-design-presentation.py
```

The builder reads the preserved source deck copy, original images, walkthrough, `presentation/slides.css` and `presentation/slide-runtime.js`. Rebuilding updates the HTML, notes and build manifest. A changed artifact needs a new review receipt.
