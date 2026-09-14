# Inspect a native session's current namespace

Use this after a native sensitive-canary result when you need to distinguish a
missing process-view path from a missing host file. The command binds one
`host-controls-demo` session through `/api/sessions/memory`, inspects its current
CLI descendants, then checks that the session binding is unchanged.

First complete the prepared host setup and the [fresh-take workflow](NATIVE-HOST-REVIEW.md).
Save a new host snapshot within 30 minutes of the readback. Supply the exact
reviewed KiroCrew package directory used for this server; the script compares
six local source hashes with root-owned server files. A changed runtime needs
source-contract review before use. Historical setup and source receipts describe
their original host and package.

```sh
.build/demo-tools-venv/bin/python scripts/inspect-native-session-namespace.py \
  --config config/demo.local.json \
  --slot chat-NEW-SLOT \
  --before .build/my-take/after.json \
  --source-root .build/my-reviewed-runtime/kiro_crew \
  --output .build/my-take/current-namespace.json
```

Replace the slot and source directory with this deployment's values. The
`--remote-source-root` default matches the bundled EC2 layout; set it explicitly
if your reviewed installation uses a different package directory. Existing output
files are refused. The demo tools dependency profile supplies `aiohttp`; the
command uses the configured pinned administrator and Gateway SSH aliases.

The owner token and cookie stay in memory and travel through a private Unix
socket owned by this command's SSH child. The command reads the fixed session
API, process identities, mount entries, source hashes and public-fixture metadata.
It does not read credential contents or process environments, enter a namespace,
submit a tool request, change approvals or send probe packets.

Exit zero means the public host fixture exists and every observed current CLI
descendant has a different mount namespace, a `.aws` tmpfs entry and `ENOENT` for
that fixture. Exit one means that evidence was not established. A completed
negative readback is retained; operational failures print a bounded diagnostic.
The readback describes current processes after the native result. It cannot
identify the historical syscall PID or turn CLI argument validation into a Crew
hook denial.

The September 14 receipt was collected by the preserved one-shot inspector named
in that receipt. This parameterized command was validated with offline identity,
fixture, freshness and namespace guards; it has not been presented as a new live
run or a second deployment.
