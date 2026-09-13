KiroCrew security and governance demo

Start with WALKTHROUGH.md. Present output/kirocrew-demo.pptx, open the
self-contained kirocrew-aws-remote.html viewer, then run:

    ./demo.sh --interactive

The seven slides include speaker notes. The viewer contains security layers,
the retained AWS proposal, and all 15 control-reference groups. The single
endpoint-control box is preserved.

Browser validation passed in Chrome across four desktop sizes and both diagram
themes, including tabs, keyboard, focus, presentation mode and PNG/SVG exports.
The live harness passed against frozen modules from the user-installed nightly
0.7.0-nightly.20260912t060850. It uses synthetic requests, an explicit approval
prompt and disposable state; no model/backend or cloud session is started.

The diagram/source-link baseline remains the verified September 11 build.
Current-feed freshness is not independently confirmed. Backend callback delivery,
native approval UI, MCP authorization, target IAM and AWS deployment remain
separate end-to-end work. Read the evidence boundaries in the runbook.

Current artifacts and hashes: CONTINUATION-RECEIPT.json
Current project state and reproduction: HANDOFF.md
Research and version differences: kirocrew-continuation-notes.md
Current interactive runtime evidence: evidence/live/latest.json

Historical accepted files and receipts retain their original scope. The old
packaging and AWS-preview scripts target earlier filenames; do not run them
against the current viewer without adapting and reviewing them.
