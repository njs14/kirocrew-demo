# Demo Observability app

This custom App Kit page shows the laptop and EC2 collector samples inside KiroCrew. It does not add client ingestion to KiroCrew's native Telemetry panel. That panel continues to show native Gateway instrumentation.

The app reads only `client.json`, `server.json` and `events.jsonl` from `/var/lib/kirocrew-demo-observability`. Every response rebuilds an allowlisted schema. Collection events have fixed labels; arbitrary log lines, paths, prompts, headers and credentials are discarded. Missing numbers remain unknown. A sample becomes stale after 180 seconds; a timestamp more than 60 seconds in the future is labeled as a clock error.

## Install contract

1. Review `app/app.json`, `app/backend/server.py`, `app/ui/dist/index.mjs` and `stage-app.sh`. Copy this directory to the demo host, then run `sudo bash stage-app.sh` there. The script stages three files under `/opt/kirocrew-demo/observability-app`; it does not execute the app.
2. The collectors create `/var/lib/kirocrew-demo-observability` as `root:crew`, mode `0750`, and its data files as `root:crew`, mode `0640`. The Gateway process runs as `crew` and can read these files. The application has no write or upload endpoint.
3. From the authenticated owner dashboard, install the local path with `POST /api/apps/install` and JSON `{"source":"/opt/kirocrew-demo/observability-app"}`. Installation copies the app, records provenance and generates a fresh app secret through App Kit. Do not supply, print or move a secret yourself.
4. Trust only this reviewed local app with owner `POST /api/security/trusted-apps/demo-observability` and JSON `{}`, then enable it with `POST /api/apps/demo-observability/enable`. Do not change the global third-party trust policy.
5. Open `/apps/demo-observability`. Verify current samples from both sources, then filter Collection logs by Client and Server. Capture the page after the real collectors have written their samples. Do not seed production data with test fixtures.

The app manifest reserves port `9102`, within the Gateway's runtime range of `9100–9200`; check that it is unused before activation. Manifest validation alone does not check this runtime range. KiroCrew starts the backend as its own `crew` subprocess, supplies `PORT` and `KIROCREW_PROXY_SECRET`, and owns the process lifecycle. No standalone systemd unit or shared-secret file is needed. The process binds only `127.0.0.1:9102`; do not add a security-group rule for this port. Disabling the app stops its Gateway-managed backend. Collectors have their own lifecycle.

To update an existing installation, restage the reviewed files and call owner `POST /api/apps/demo-observability/update` with JSON `{"source":"/opt/kirocrew-demo/observability-app"}`. The platform preserves the app's data, generated secret and enabled state, replaces its files, and restarts its backend if enabled. The existing trust grant for this same local app remains in force. Do not uninstall or transfer the secret. Version `1.0.1` corrects the initial invalid `8012` port to `9102`.

Before claiming live operation, verify backend health and an authenticated snapshot after the update. The update endpoint's HTTP 200 confirms the update operation; it does not prove that the child process passed its health check. Runtime spawn also checks the app's execution trust/admission policy, contained entry point, free port, interpreter and proxy-secret availability, and applies the standard OS sandbox and process limits. This app needs read access to its protected data directory within that sandbox; verify both Client and Server files are visible through the authenticated snapshot. The frozen Linux sandbox's default denied-read list does not name this custom data directory, but file permissions and host policy still apply.

## Authentication and data boundaries

The browser uses the host-provided `useAppApi()` SDK and the sole declared API prefix `/apps/demo-observability/api`. KiroCrew authenticates the owner request and signs the forwarded method, raw path, query and body with the per-app HMAC secret. The backend calls the installed `kiro_crew.apps.proxy_auth.verify_proxy_request` for every data request. Missing, wrong, modified and expired signatures fail with HTTP 401. The SDK allows a 60-second timestamp skew window; a valid read signature can be repeated within that window. This is freshness validation, not a single-use nonce system.

Only `GET /health` is unsigned, returning exactly `{"status":"ok"}` for the Gateway's health probe. `GET /api/snapshot` is the single data endpoint. Other routes and all mutation methods are refused. Input files are limited to 128 KiB each, must be regular files and cannot be symlinks. The last 200 collection events are accepted; the page shows the newest 20 matching entries. The page refreshes every 15 seconds. Sample age advances each second between requests. A failed refresh leaves a visible error above the previous snapshot and changes its badges to “Last known sample”; old samples also display “stale”. The client check labeled “SSH tunnel listener reachable” proves only that the local tunnel TCP listener accepted a connection, not that the remote Gateway answered an application request.

Client CPU is the sum of macOS process scheduler averages and can exceed 100%. Server host CPU is a one-second utilization sample normalized to 100%; service CPU and memory cover systemd's main process. These measures should not be compared as identical CPU sampling methods.

Root owns the collector data. These files and this custom app are demo instrumentation, not tamper-proof audit storage or proof of native tool enforcement. The pending native Kiro CLI sign-in remains a separate acceptance gate.

## Checks

Run the tests under an installed KiroCrew Nightly Python environment:

```sh
python -m unittest discover -s infrastructure/observability/tests -p test_app.py -v
node --check infrastructure/observability/app/ui/dist/index.mjs
node --experimental-vm-modules --test infrastructure/observability/tests/test_ui.mjs
```

The 16 backend tests cover actual SDK HMAC verification, freshness, signed request integrity, mutation refusal, data allowlists, symlink/size guards, missing values, event bounds, and the actual Gateway port-range/entry-point contract. They use temporary synthetic fixtures and local HTTP requests. Four UI checks cover advancing age, last-known badges, missing/future timestamps and the exact transport-probe label. They establish local behavior; live installation and browser evidence belong in a separate deployment receipt.

The manifest and UI bundle require no new Python or JavaScript packages. React and the App Kit SDK are supplied by the dashboard host. The UI is a plain ESM module and needs no build step.
