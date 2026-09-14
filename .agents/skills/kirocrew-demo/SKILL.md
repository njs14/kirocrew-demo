---
name: kirocrew-demo
description: Set up, present, reproduce, or update this KiroCrew demo project, including dependencies, its macOS client and EC2 controls, native recordings, and the admin walkthrough.
---

# KiroCrew demo

Work from the checkout containing this skill. Locate the project by ascending from this file to the directory containing `scripts/demo-dependencies.py`; do not reuse a previous machine's absolute paths. Keep the user's chosen presentation or live workflow in scope.

Read `evidence/native-client-demo/current-status.json` and [docs/MANAGED-DEMO.md](../../../docs/MANAGED-DEMO.md) before changing the managed demo. The policy and native MCP observations are under `evidence/enterprise-managed/20260913/`; the completed September 14 host takes are under `evidence/managed-host-20260914/`. Use [docs/NATIVE-HOST-REVIEW.md](../../../docs/NATIVE-HOST-REVIEW.md) for new host-take collection and attribution. `HANDOFF.md` retains earlier work. Historical screenshots, recordings and receipts prove only their recorded deployment and time.

Choose the relevant route:

- **Present or rebuild the delivered artifacts:** read [references/presentation.md](references/presentation.md). Playback needs no AWS account, native app or reviewer subscription.
- **Install dependencies or reproduce the live deployment:** read [references/setup.md](references/setup.md). Use explicit configuration and the existing VPC/subnet; no new network infrastructure is implied.
- **Run controls, capture footage, or revise the walkthrough:** read [references/recording.md](references/recording.md). Show actual macOS client requests and the server's decision, then the relevant admin UI.

Use `scripts/demo-dependencies.py plan` before its `apply` mode. Installation already authorized by the user's setup request can proceed within the printed scope. Dependency installation does not authorize a new account, extra infrastructure, a paid reviewer, or credentials copied between products. Authenticate AWS, KiroCrew, Kiro CLI and optional reviewers through their own products.

Keep one endpoint-control enclosure in the architecture. The endpoint is macOS; execution and the managed policy are on the selected EC2 Gateway running the original Kiro CLI. Verify the server-enforced policy before describing it as managed. A user-facing MCP toggle changes local configuration; it cannot be used as evidence that a central deny was removed. Do not imply enterprise SSO or a centrally managed MCP registry unless that deployment actually uses them.

Complete the selected workflow with its observable result and material remaining prerequisites. Attribute decisions from the exact native tool records and the corresponding host or server evidence, not the model's explanation. Report a synthetic rehearsal, a native UI observation, a backend log and an AWS denial at their actual evidence level. A screenshot of a result is not footage of the action executing.
