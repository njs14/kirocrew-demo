# Demo probe operator screen

Run `python3 scripts/serve-demo-probes.py` from the project and open
`http://127.0.0.1:5607/` in a 1600 × 1000 browser recording session.

The page is a local recording aid, visibly distinct from KiroCrew's native app.
Starting it does not execute a command. A same-origin button press is required.

## Scenes

1. **Direct MCP/AWS probe:** press **Start bounded probe**. Keep the running state
   on screen, then inspect the allowed S3 read, MCP grant denial and IAM denial.
   Results are from the fresh remote receipt. The probe emits one JSON document
   at completion; no per-tool progress or intermediate results are fabricated.
   Open the sanitized receipt to inspect trace IDs, AWS request IDs and hashes.
2. **Local synthetic control rehearsal:** select the separate tab and press
   **Start synthetic rehearsal**. This runs the existing isolated `demo.sh`
   noninteractively. Approval is supplied by the script. Its frozen package,
   synthetic requests and explicitly emitted SEL events do not establish native
   Kiro CLI approval or a backend session.

Both scenes retain `native_backend_verified = false`. A direct probe pass is
MCP/AWS service evidence. The native CLI sign-in and backend proof remain pending.

## Routes and automation selectors

- `/`: operator screen.
- `/api/state`: read-only current process status and sanitized results.
- `POST /api/run`: only `{"mode":"direct"}` or `{"mode":"synthetic"}`; requires
  exact loopback Host, same Origin and page nonce in `X-Demo-Nonce`.
- `/artifacts/<generated-name>.json`: only the immutable in-memory allowlist of
  receipts produced by this running server. Arbitrary files are not served.
- `#start-run`, `#tab-direct`, `#tab-synthetic`, `#run-status`,
  `#card-read_allowed`, `#card-mcp_denied`, `#card-iam_denied`,
  `#receipt-toggle`, `#receipt-download`.

`/api/state` returns `active`, `server_time`, `native_backend_verified:false`,
and `runs.direct` / `runs.synthetic`. A run has `status`, `started_at`,
`finished_at`, `output_bytes`, `receipt`, and upon retention `artifact_url` and
`artifact_sha256`. A failed validation exposes only a bounded error type.

## Evidence and limits

Fresh command receipts are retained under
`evidence/demo-clips/20260913/probe-presenter/`. Each records the exact fixed
argument vector, timing, exit code, stdout/stderr byte counts and digests,
and a strict field/value allowlist of the parsed result. Raw stdout/stderr are
not retained; unexpected text and exception strings may contain credentials.
The MCP token file is referenced only by the fixed remote command; this server
never reads the token or exposes an arbitrary command or path input.

Both commands have a 90-second timeout, 128 KiB combined output limit, no stdin,
local `shell=False`, and a dedicated process group killed on limits. One run at
a time is allowed. There are no service changes or deployment operations.

Focused tests: `python3 evidence/demo-clips/probe-presenter/test_presenter.py`.
These use known historical fixtures and local stubs only. They do not execute
the real remote probe or the local synthetic rehearsal.
