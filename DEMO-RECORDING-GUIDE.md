# KiroCrew recorded demos

Six recorded walkthroughs add working controls, dashboard measurements and fresh command results to the accepted presentation. Open the recorded edition and start at slide 15. The first 14 slides preserve the accepted deck, including its single endpoint-control box.

The clips are silent, 1600 × 1000 H.264 videos at 25 fps. Their combined runtime is 2 minutes 43 seconds. Playback controls operate the recording; they do not send commands to KiroCrew or AWS.

| Slide | Scene | Length | What the recording establishes |
|---|---|---:|---|
| 15 | One endpoint-control boundary | 24.84 s | The accepted enclosure expands for inspection, followed by the recorded ARM deployment view. The reference and historical evidence labels remain visible. |
| 16 | Navigate the admin console | 23.24 s | The owner portal shows the remote Gateway overview, Kiro CLI selection, its sign-in failure in Logs, and the observability app. |
| 17 | Compare client and server telemetry | 22.52 s | Stored Mac/EC2 samples show Local Gateway off, healthy server checks, expanded process measurements and collection-event filters. |
| 18 | Inspect native Gateway telemetry | 20.68 s | Metrics are enabled, anonymous reporting is disabled, and native Gateway instruments contain data. Completed backend turns remain zero. |
| 19 | Follow a direct MCP request to AWS | 25.56 s | A fresh bounded command returns the expected S3 object, rejects a disallowed MCP tool before AWS dispatch, and receives IAM AccessDenied. |
| 20 | Rehearse the synthetic endpoint controls | 45.80 s | An isolated local test runner exercises controls, scripted approval, redaction and SEL integrity. No backend session or network call occurs. |

Use **Replay** to start a scene, select a chapter to seek and pause, or enable **Pause at chapters** for a narrated walkthrough. **Next chapter** advances to the next cue. Chapter details link to the corresponding capture or command receipt. Leaving a slide or opening the overview/notes dialog pauses playback.

For a short demonstration, start with slide 17, explain the Mac/EC2 split, then move to slide 19 and inspect the three outcomes. Use slide 18 to explain why Gateway metrics can exist while completed backend turns remain zero. Slide 20 explains the proposed control behavior through an explicitly synthetic rehearsal.

## Files and local preview

- `output/kirocrew-recorded-demos.html` contains the 20-slide edition and player.
- `output/kirocrew-recorded-demos-notes.md` contains the full speaker notes and timed chapters.
- `output/demo-clips/20260913-final/` contains the six MP4s, posters, contact sheets, selected frames and copied receipts.
- `output/kirocrew-recorded-demos-build.json` binds the presentation to the accepted source, media and copied evidence by SHA-256.
- `recordings/20260913/manifest-final.json` records the selected takes and captions. Raw captures remain in `recordings/20260913/raw/` and are excluded from the portable bundle and preview routes.

The local preview is `http://127.0.0.1:5606/#slide-15`. To restart it from the project directory:

```sh
python3 scripts/serve-recorded-demos.py
```

The portable ZIP contains the presentation and its relative media/evidence paths. Extract it before opening `kirocrew-recorded-demos.html`. Keep the `demo-clips` folder beside that file. Its README also gives a loopback HTTP preview command.

## Recording method and evidence

Playwright CLI recorded actual browser interactions. FFmpeg encoded the full selected takes without retiming or padding, then decoded every export. The processing receipt records source/output hashes, tool versions, cuts and validation. Contact sheets and key result frames were inspected for framing, readability and unintended credential exposure.

The portal recordings show the running server and its stored samples on September 13, 2026. The Mac preflight found Nightly `0.7.0-nightly.20260913t061222`, local Gateway disabled and no local 5476 listener. The ARM server was a running `t4g.xlarge` in `us-east-1`, with Gateway, MCP and collection services active. Its security group admitted SSH from the current client IPv4 `/32`; the application services remained on loopback.

The fresh direct probe ran at 18:21 UTC. S3 returned the expected 55-byte object with SHA-256 `34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160`. The allowed request ID was `CMSJ6HKBJ4YEW6TR`; the IAM-denied request ID was `Y8P2NZ17949A7E6J`. MCP returned `tool_grant_denied` before AWS dispatch for its rejected tool. The receipt keeps native backend verification false.

The synthetic rehearsal ran at 18:23 UTC against the frozen September 12 package. It verified 7 of 7 SEL entries, detected the changed fixture at 6 of 7, restored the original and verified it again. Approval came from the rehearsal script. These results establish the isolated test execution only.

The custom observability panel reports collection events. Those events are separate from Crew security audit events. Its Refresh button reads stored samples; the collectors run every 60 seconds. The recorded historical process-probe warning and recovery do not establish a desktop quit/relaunch. Native metrics can also include earlier Gateway process shards.

## Pending recordings

The client quit/relaunch scene could not be captured because desktop automation reported that the Mac was locked. The recording request to unlock it remains pending. Once available, record the native client and browser together, quit KiroCrew normally, collect a stopped-client sample, relaunch it, and collect recovery. Verify that the EC2 Gateway PID and start timestamp stay unchanged throughout. The independent SSH tunnel must remain available. The existing clips establish Local Gateway off and current server health, but do not replace this sequence.

Native Kiro CLI enforcement is also pending. A fresh server-side `whoami` check returned signed out; the selected backend's portal log shows the corresponding startup failure. Capture this follow-on scene only after native sign-in succeeds and a completed Kiro CLI backend turn can be observed. A separate KAS GitHub identity does not satisfy that gate.

## Repeat the workflow

1. Recheck the deployed version, local Gateway setting, server identity, telemetry freshness and native authentication. Record the observation time.
2. Rehearse the relevant UI flow. Use a clean application route after authentication, readable framing and bounded operations. Keep owner tokens and sign-in screens outside the take.
3. Copy the relevant reviewed script from `recordings/20260913/scripts/`, choose a new raw filename and record the complete scene. Capture its action timestamps and command receipt.
4. Create a new manifest beside the recordings. Label architecture references, portal operation, direct MCP/AWS execution and synthetic controls precisely. Keep raw files unchanged.
5. Process into a new output directory, inspect frames and build the derivative edition:

```sh
python3 scripts/demo-clips.py path/to/manifest.json --check
python3 scripts/demo-clips.py path/to/manifest.json --output output/demo-clips/new-run
python3 scripts/build-recorded-demo-presentation.py --manifest output/demo-clips/new-run/manifest.json
```

6. Restart the preview after rebuilding. Verify playback, cue seeking, guided pauses, keyboard controls, evidence links and desktop/mobile layout against the new build receipt.

The installed `demo-clips` skill documents this process. The standalone FFmpeg skill is pinned to Digital Samba commit `225c80a1c3a57c82d319ea6c73e0eff513787ae8`. Installation and tooling receipts are in `evidence/demo-clips/tooling/`. The workflow uses local tools without a paid product or external media host.

## What changed

The recorded edition adds six scenes, timed chapters and supporting receipts. The No AI Slop pass tightened the operator-screen explanation and changed the new captions' technical noun “harness” to “test runner.” Recorded UI, receipt field values, accepted source slides and historical review wording retain their original text. Previous Grok/Opus council verdicts cover their frozen source candidates; this edition has a separate local review and playback validation.
