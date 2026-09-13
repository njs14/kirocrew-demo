# KiroCrew: brief slides to live control evidence

Plan for about six minutes: three and a half minutes of slides, a minute or two in the terminal, then a short evidence recap. The presentation is for an AWS/security audience. Keep the single endpoint-control box intact throughout.

## Open before presenting

1. Open `output/kirocrew-demo.pptx` in a presentation app. Seven slides include speaker notes and source links.
2. Open `kirocrew-aws-remote.html` in Chrome. The diagrams are self-contained. Use a desktop window of at least 1440×900; focus the endpoint when discussing small labels.
3. Open a terminal in this directory:

```sh
cd /Users/noahsutter/git-projects/kirocrew-demo
./demo.sh
```

The noninteractive preflight runs the complete synthetic rehearsal and writes a fresh receipt. Expect `PASS` at the end. The intentional `SEL HMAC mismatch` line proves the disposable tamper test; the original bytes are then restored and verified. Each run gets its own directory, so rerunning does not consume or modify an earlier receipt.

This Mac's installed nightly is `0.7.0-nightly.20260912t060850`. The runner uses its frozen package snapshot and the Python runtime under `/Applications/KiroCrew Nightly.app`. Updating the app later does not automatically update the snapshot. On another machine, copy the package snapshot and supply Python 3.12+ with matching Crew dependencies through `KIRO_DEMO_PYTHON`; revalidate there before presenting. The PPTX and viewer are independently portable; the executable rehearsal currently depends on this local runtime.

## Present the story

| Time | Surface | Say and show |
| --- | --- | --- |
| 0:00–0:30 | Slide 1 | “Crew provides governance around managed coding-agent execution. Kiro CLI, Codex and Claude Code are backend choices; usable providers need installation, authentication and admission.” |
| 0:30–1:15 | Slide 2 → viewer Security layers | “The box is the execution host. Locally that is the developer machine; remotely, Gateway, backend and workspace run together.” Search for Endpoint and select the result. Dismiss its detail card with Escape, use + to enlarge the diagram, and reset the camera with 0. Enterprise EDR/OS controls remain outside Crew's ownership. |
| 1:15–2:00 | Slide 3 | Explain host controls, Crew checks, MCP grants and target authorization as distinct decisions. “Prevention requires the tool to reach a Crew hook before execution.” |
| 2:00–2:45 | Slide 4 | Explain proposed caller OAuth, tool grants and downstream identity. A direct shell or SDK request does not encounter an MCP gateway merely because one exists. |
| 2:45–3:30 | Slide 5 → viewer AWS deployment | Trace the retained private EC2 + SSM proposal. Crew runs unprivileged. Policy sync, credential isolation, gateway and external collection need implementation. Nothing here was deployed. |
| 3:30–5:30 | Slide 6 → terminal | State the scope below, then run the interactive demonstration. |
| Final 30s | Slide 7 | “We observed Crew function-level control evidence. A deployed MCP denial and a target IAM denial require their own receipts.” |

Use the reference tab for questions, not as extra slides. It contains all 15 control groups, limitations and pinned implementation links. Its source baseline is September 11; the rehearsal is bound separately to the installed September 12 package. “Latest” is user-reported because the feed could not be independently refreshed.

## Run the live sequence

Say: “These are real Crew control functions from the installed nightly, exercised with synthetic requests. This harness supplies the approval prompt and tool handler. It does not start a model or an ACP backend and makes no cloud calls.”

```sh
./demo.sh --interactive
```

| Step | Expected evidence | Presenter action |
| --- | --- | --- |
| Allow | `ReadDemo` returns `auto_approve`; local read completes | Point to the verdict and handler outcome |
| Ask, pending | Crew returns `allow` for normal handling; marker does not exist | Pause and explain that this is the harness approval UI |
| Ask, resolved | The marker appears only after approval | Type `APPROVE` and Enter; any other input rejects the synthetic write |
| Deny | `DenyDemo` returns `deny`; handler is never called | Identify this as the configured Crew rule |
| Protected path | Synthetic `security_policy.json` edit is denied; bytes unchanged | Explain resolved-path protection; this is a disposable fixture |
| Command gate | The exfiltration-shaped string is denied | The string is classified, never run by a shell |
| Policy ∩ Profile | Read permitted; write limited by profile; denied tool limited by policy | Explain which layer constrains each decision |
| Redaction | An AWS documentation example key becomes a redaction marker | No real credential is involved |
| SEL | Seven valid records; one deliberate edit produces six valid records; restore returns seven valid | Explain integrity of recorded events, not complete capture or immutable retention |

Finish on the `PASS. Evidence:` path. The receipt records the actual results, installed package identity and runner hashes. The harness emits its verdicts through Crew's SEL API and correlates `demo-deny`. It does not prove automatic backend capture.

If the preflight fails, use the recorded receipt and transcript under `evidence/live/` and label them as recorded evidence. A snapshot mismatch means the frozen package changed: stop that rehearsal and rebind it deliberately. Do not fall back to an unverified version while presenting it as the same run.

## Follow-on end-to-end checks

Before claiming a backend demonstration, create a disposable session through the chosen backend, observe its real approval UI, and prove a denied handler did not execute. Check native auto-approval and callback delivery explicitly. L0 sandbox behavior and signed-policy enforcement need their own observations.

For an authorized deployed MCP/AWS pilot, use one correlation ID. First show a Crew denial before dispatch. Next permit Crew and deny the MCP tool grant, proving the target was not invoked. Finally permit MCP and show target IAM denies a least-privilege synthetic action, with target evidence. OAuth audience, service credentials and external event retention remain separate checks. Do not describe this future sequence as already rehearsed.
