# Present and rebuild

From the project root:

```sh
python3 scripts/doctor.py --feature playback
python3 scripts/serve-recorded-demos.py --build output/kirocrew-native-controls-build.json --port 5612
```

Open `http://127.0.0.1:5612/`. Use the selected build receipt if the current status identifies a newer edition. Read the notes next to that edition's HTML before presenting. The main walkthrough contains the client control clips and links to the admin screenshot tour and architecture. Follow the user's preferred order; use footage for observed control outcomes and the separate tour for UI explanation.

Use [docs/MANAGED-DEMO.md](../../../../docs/MANAGED-DEMO.md) for the managed edition's claims and walkthrough. The [dated pre-managed forward test](../../../../evidence/enterprise-managed/replication/20260914T015152Z-pre-managed-skill-forward-test.json) covers the earlier 14-slide, eight-clip export. It does not validate the newer managed edition. Refresh the recipe first, then run the clean-checkout forward test for the final edition; retain the old report intact and bind the new result to the new artifact.

For a fresh self-contained export, use `python3 scripts/build-demo-presentation.py --check`, then `python3 scripts/build-demo-presentation.py --output-dir .build/presentation-export`. The output directory must be new. The recipe in `config/presentation-native.json` references committed artifacts. Run the returned `previewCommand`, or `python3 .build/presentation-export/scripts/serve-recorded-demos.py --build .build/presentation-export/kirocrew-native-controls-build.json --port 5612`. No AWS, login, private runtime bundle, or old `.build` state is needed to reproduce the recorded edition; Python 3.9+ is sufficient for these standard-library helpers.

When changing content, use authoring dependencies, update the source/recipe rather than editing receipt hashes by hand, and build a derivative before replacing the current edition. Freeze the content once, run proportionate browser/media checks, incorporate substantive review findings, then publish the exact checked artifact. Do not repeat full reviews merely because bookkeeping changed. Preserve accepted historical artifacts and their receipts.

If requested, run Grok and Opus council review through the project's reviewed council helper and the user's installed clients. Read the helper's model/version contract and the current [scripts/run-native-deck-council.py](../../../../scripts/run-native-deck-council.py) first. Record actual dispatch model/effort and explain any unavailable requested model; do not silently substitute it. Incorporate agreed decisions, then use the available No AI Slop skill for direct, accurate prose. These optional reviewers do not block playback or an ordinary export.
