# KiroCrew recorded demos

Record short clips of the working system and place them in a new edition of the HTML presentation. Keep the accepted 14-slide deck, PowerPoint, endpoint image and earlier receipts intact. Clips are silent by default, with editable captions and pause points in the HTML player.

## Scenes

| Scene | What the viewer sees | Evidence and recording gate |
| --- | --- | --- |
| 1. One remote execution endpoint | Open the architecture, inspect the single endpoint-control box, then show the current remote connection and local gateway setting. | Label the diagram as a reference. Confirm current Mac configuration and remote Gateway health before claiming the remote topology is running. |
| 2. Find your way around the admin console | Navigate the owner dashboard, workspace and backend controls. Show Kiro CLI as the selected backend and its actual authentication state. | Capture the real portal. Do not record owner tokens, login links or session databases. A selected backend does not prove a completed backend turn. |
| 3. Inspect client and server telemetry | Open Demo Observability, compare Mac and EC2 samples, refresh the dashboard, and inspect collection events. | Show source names, sample times and health checks. Separate custom collection events from Crew security audit events. |
| 4. Prove the remote Gateway survives a client stop | Observe a healthy server, quit the Mac client normally, collect the stopped-client state, relaunch the client and show recovery. | Record the actual sequence and sample timestamps. Confirm the server Gateway PID/start identity is unchanged. Restore the client and connection after the take. |
| 5. Follow an MCP request to AWS | Run the existing bounded direct probe and show allowed S3 read, MCP grant rejection and IAM AccessDenied results, then inspect their receipt. | Use a fresh direct-probe receipt and label it as direct MCP/AWS evidence. Do not describe it as a native Kiro CLI turn. |
| 6. Rehearse the endpoint controls | If useful to the walkthrough, run the existing isolated synthetic controls: allow, approval, configured deny, redaction and SEL verification. | Label the whole scene as a local synthetic rehearsal. Keep it separate from remote enforcement evidence. |

The native Kiro CLI enforcement sequence is a follow-on scene only if a fresh authentication check succeeds and a completed backend turn can be observed. Existing sign-in failures are not replaced with a simulated success.

## Production sequence

1. Inspect live runtime state and the accepted visuals, notes and review receipts. Record current versions and reachable local routes.
2. Install the standalone FFmpeg skill and create the small `demo-clips` skill and build helper. Keep the workflow local and use the installed Playwright/FFmpeg tools.
3. Rehearse each browser flow without recording. Confirm readable framing, expected controls and a useful result before each take.
4. Record complete takes. Preserve original footage and action timestamps; keep editing decisions separate. Do not manufacture dashboard values or hide failures with substituted frames.
5. Trim only lead-in, trailing idle time and clearly documented waiting. Create browser-compatible clips, posters and a timestamped cue manifest. Retain full raw footage for review.
6. Build a new HTML presentation with chapter selection, play/pause, replay, cue seeking, evidence details and automatic pause when leaving a slide. Keep the single endpoint-control box.
7. Inspect representative video frames and screenshots. Check decoding, duration, playback, seeking, keyboard use, mobile layout and media delivery. Review captions with No AI Slop.
8. Deliver the recorded presentation, clips, recording guide and an exact artifact receipt. Record any unavailable scene and its concrete acceptance gate.

## Completion criteria

- Several playable clips show actual UI operation and dashboard data.
- Current observations, direct MCP/AWS results, architectural references and synthetic controls carry distinct labels.
- The client is restored after the stop/recovery scene, with the remote Gateway still running.
- Videos and their cue points work locally without a paid service or external media host.
- Accepted artifacts and historical review verdicts retain their original scope.

## September 13 recording result

Recorded the endpoint reference, admin navigation, client/server telemetry, direct MCP/AWS probe and synthetic rehearsal. Added a sixth clip for native Gateway instrumentation so viewers can distinguish its metrics from the custom collector dashboard. The recorded edition contains the accepted 14 slides followed by these six scenes.

The client quit/relaunch scene remains unrecorded because the Mac is locked and native desktop automation is unavailable. The request to unlock it is pending. Native Kiro CLI enforcement also remains pending because the fresh server authentication check returned signed out. Neither scene is represented by a substituted recording.

The six exports passed FFmpeg decoding and browser playback checks. All 29 chapters seek and pause; guided pauses, keyboard controls, evidence links and desktop/mobile layouts passed. See `DEMO-RECORDING-GUIDE.md` for the completed scenes, remaining gates and repeatable recording process. Exact validation and source-preservation evidence lives under `evidence/demo-clips/20260913/`.
