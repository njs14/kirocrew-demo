# Local rehearsals and recorded demos

The current native-controls edition plays its included recordings without KiroCrew,
AWS credentials, Node.js or a Python package installation. Python 3.9 or newer is sufficient. From the checkout:

```sh
python3 scripts/serve-recorded-demos.py --build output/kirocrew-native-controls-build.json --port 5612
```

Open the URL printed by the server. It binds to loopback and serves the exact
files listed in the build receipt. See `--help` for port and build-receipt
options. The recordings show historical observations; playback does not test a
new machine or deployment.

Use the [project skill](../.agents/skills/kirocrew-demo/SKILL.md), [dependency manager](DEPENDENCIES.md), and [live setup sequence](LIVE-SETUP.md) for a new machine. The [MCP walkthrough](MCP-GOVERNANCE.md) distinguishes user tool availability from the server's policy decision. Record actual macOS client requests for enforcement demonstrations; reserve browser screenshots for the admin tour.

On macOS, let a timed `screencapture -v -V<seconds>` recording finish normally. Sending SIGINT can discard the movie. Verify the file and decode it before treating a take as recorded. Start the passive observer on an existing idle session after any Gateway restart; a newly created empty client-only slot may not exist on the server yet.

## Rehearse real local control functions

Use macOS or Linux, Python 3.12 or newer, and an installed KiroCrew package you
have obtained and reviewed separately. Python 3.12 is the tested baseline.
The Bash launcher and POSIX file controls do not support native Windows; use a
Linux environment such as WSL and verify it independently.

The package snapshot and application binaries are deliberately excluded from
Git. The preparer never downloads, installs or imports KiroCrew, and never reads
its user state directory. Pass the resolved directory named `kiro_crew` inside
your chosen installation's `site-packages`, not the application root or home
directory:

```sh
python3 scripts/prepare-demo-baseline.py \
  --package /resolved/path/to/site-packages/kiro_crew \
  --output .build/demo-baselines/my-installed-build
```

This copies eligible package bytes into a new private directory and records the
version, file sizes, hashes, digest and source path. Cache directories and known
credential/state filenames are excluded and listed in the manifest. Symlinks,
special files, oversized packages and existing output directories are refused.
No snapshot is labeled an accepted baseline by this command. A different
version or file set needs its own control run and acceptance evidence.

Use the dependencies of that installation, or create an isolated environment
for the tested rehearsal dependency set:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-demo.txt
export KIRO_DEMO_PYTHON="$PWD/.venv/bin/python"
export KIRO_DEMO_BASELINE="$PWD/.build/demo-baselines/my-installed-build/manifest.json"
./demo.sh --validate-baseline
./demo.sh
./demo.sh --interactive
```

You can pass `--baseline-manifest PATH` instead of `KIRO_DEMO_BASELINE`. The
launcher clears inherited credentials and Python module overrides; the runner
verifies the complete selected file inventory before importing the actual Crew
functions. It creates disposable state under `evidence/live/`, disables network
connections and never starts a model or backend. `--interactive` asks for the
literal `APPROVE` in the terminal. The normal rehearsal scripts that decision.
Neither is the native backend's approval interface.

If the original accepted local snapshot is still present, the existing default
manifest continues to work. A fresh clone reports how to prepare a replacement
instead of downloading one. `--baseline pinned` remains an optional historical
source-checkout mode tied to its original commit; it is not prepared implicitly.
An upgrade can add runtime dependencies or change control behavior. Install that
build's documented dependencies and investigate a failed run before recording;
do not patch or mock control functions to make a scene pass.

## Browser inspection and capture

For the repository's browser checks, use Node.js 20.9+ and the locked local module:

```sh
npm ci --ignore-scripts
npm exec -- playwright install chromium
npm run check:browser
npm run check:live-viewer
```

The explicit `playwright install` command downloads its Chromium build. Skip it
when using an already installed compatible browser; set
`KIRO_DEMO_BROWSER_EXECUTABLE` to that executable instead. The scripts never
download or install software by themselves. An existing local Playwright module
can be selected with `KIRO_DEMO_PLAYWRIGHT=/path/to/playwright`; otherwise the
module must be in this checkout's `node_modules`.

`npm run inspect:browser` inspects the local reference viewer by default.
`KIRO_DEMO_VIEWER_URL` can select a served copy. Checks write new local browser
receipts; they do not replace historical review conclusions.

For new footage, the scripts under `recordings/20260913/scripts/` are examples
of the actual recorded interactions. Review selectors, URLs, visible data and
annotations against your current portal before using them. The browser must
authenticate normally in its own product; do not copy authentication state from
another client. Capture actual activity with your installed Playwright CLI or
another local recorder, and keep raw footage under an ignored `raw/` directory.
Inspect it for secrets before producing presentation media.

## Encode and add a recorded edition

Install FFmpeg and FFprobe separately on the local machine. The processor uses
the executables on `PATH`; Python dependencies are not required for encoding.
Keep the original raw files immutable and create a cuts manifest alongside
them. A minimal scene looks like this:

```json
{
  "schemaVersion": 1,
  "title": "My recorded walkthrough",
  "scenes": [{
    "id": "dashboard",
    "title": "Inspect the dashboard",
    "description": "Open the current sample and inspect its timestamp.",
    "evidenceScope": "Actual browser operation; no backend turn performed.",
    "recordedAt": "2026-09-13T18:00:00Z",
    "source": {
      "kind": "browser-recording",
      "raw": "raw/dashboard.webm",
      "description": "Actual browser interaction at its original speed."
    },
    "start": 0,
    "end": 12,
    "cues": [{"time": 2, "label": "Read the timestamp", "detail": "Confirm when the sample was collected."}]
  }]
}
```

Replace the example date, duration and observed details with the recording's
actual values. All raw and cue-evidence paths must remain inside the manifest
directory. The checked-in original recording manifests cannot be reprocessed
without their excluded raw footage.

```sh
python3 scripts/demo-clips.py recordings/my-run/manifest.json --check
python3 scripts/demo-clips.py recordings/my-run/manifest.json \
  --output output/demo-clips/my-run
python3 scripts/build-recorded-demo-presentation.py --help
```

The processor requires a fresh output directory, produces silent H.264 MP4,
posters and contact sheets, decodes every export, and binds source/output hashes.
It preserves timing. Inspect the contact sheet and action/result frames, then
use the presentation builder's explicit output options to create a new edition.
Do not overwrite a reviewed edition or imply that its earlier reviews cover new
bytes. Check playback, cue seeking, pause-on-navigation, keyboard controls and
mobile layout before handing over the new build.

Retain the single endpoint-control box. Keep synthetic controls, direct MCP/AWS
operations, operational telemetry and native Kiro CLI enforcement labeled
separately. A direct probe or replay never closes a pending native sign-in gate.

## Optional historical deck council runner

`scripts/run-deck-council.py` retains its original **nine-slide PPTX** review
protocol. It is not the runner for the current 20-slide recorded edition.
`prepare` only creates the frozen packet; `run` requires its exact manifest
confirmation and intentionally invokes authenticated local reviewer clients.
No reviewer runs as part of setup, browser validation, encoding or preview.

The runner finds `grok` and `claude` on `PATH`, with optional
`KIRO_DEMO_GROK_CLI` and `KIRO_DEMO_CLAUDE_CLI` executable overrides. Each product
must be installed and authenticated independently. Packets use the platform's
temporary directory (`TMPDIR` if set), which must remain the same between
preparation and review and must be outside the user home. Existing model IDs,
`xhigh`, read-only tool restrictions and image-evidence gates are retained;
verify client/model availability before requesting a new review. The runner's
process isolation requires macOS or Linux.

GitHub Actions are not part of this workflow.
