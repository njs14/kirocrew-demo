# Recorded demo player

This directory contains synthetic player tests. The generated test pattern and fixture edition do not represent KiroCrew behavior, cloud enforcement, or a recorded app session.

## Integration

After actual recordings pass the media processor:

```sh
python3 scripts/build-recorded-demo-presentation.py --manifest output/demo-clips/RUN/manifest.json
python3 scripts/serve-recorded-demos.py
```

The builder writes these new files:

- `output/kirocrew-recorded-demos.html`
- `output/kirocrew-recorded-demos-notes.md`
- `output/kirocrew-recorded-demos-manifest.json` (public subset)
- `output/kirocrew-recorded-demos-build.json` (exact hashes and serve allowlist)

Open `http://127.0.0.1:5606/`. The server must restart after a rebuild; it rejects files that differ from the loaded build receipt. All original 14 slide section strings must remain byte-identical. The original HTML and notes are protected destinations. The prior council remains scoped to its frozen source candidate.

The manifest must follow `scripts/demo-clips.py` schemaVersion 1. Scene media must have `decodeValidated: true` and exact `sha256`/`bytes`. Posters and contact sheets also need exact hashes and sizes. Local cue evidence must appear in the processed manifest's top-level `evidence` array with matching hashes and sizes. Only linked evidence, processed media, posters, contact sheets, the new edition, its notes, its sanitized manifest and its build receipt enter the server allowlist. The raw capture and processing commands are excluded.

The player provides native muted video controls, replay, chapter seek-and-pause, the next chapter, and optional guided pauses. Videos pause when their slide hides, any presentation dialog opens, the document hides, or the page leaves. Existing slide keyboard guards protect video controls, chapter buttons and the guided-pause checkbox.

## Checks

```sh
python3 evidence/demo-clips/player/test_player.py
node --check presentation/demo-player.js
```

The HTTP and builder tests cover original-slide preservation, input hashes, cue bounds, script escaping, synthetic delivery gating, protected destinations, symlink input/output rejection, hidden raw sources, strict loopback host allowlisting, GET/HEAD, media ranges and rejection of traversal or changed artifacts.

The browser fixture uses a generated FFmpeg test pattern. Its 13 browser checks cover playback metadata, mute/inline controls, cue seek/pause and detail changes, next chapter, guided playback, overview/outgoing-slide pausing, original navigation, keyboard focus, desktop fit, mobile overflow and target size, and embedded notes download. The browser run uses its own named session. Document-visibility and pagehide pause handlers are implemented but were not separately exercised; actual KiroCrew recordings need their own final playback and visual checks.

`browser-fixture/desktop.png` and `mobile.png` show the synthetic player at 1440 × 1000 and 390 × 844. The first layout attempt exposed a footer overlap; the video now fits the available slide height. The final fixture has no horizontal overflow and all chapter targets are at least 44 px high on mobile.
