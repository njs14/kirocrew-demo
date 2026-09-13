# Demo metrics collector

This collector sends a small Mac client sample through the existing pinned SSH connection and samples the EC2 host locally. The KiroCrew admin app reads the resulting files. It is a custom demo extension, separate from KiroCrew's built-in diagnostics, analytics and security event log.

The collector does not read command arguments, environment variables, account files, sessions, requests, credentials, MCP headers or raw logs. It never connects to instance metadata or an external analytics endpoint. Its only client upload destination is the existing `kirocrew-demo-admin` SSH alias, with the ARM host key pinned explicitly.

## Measurements

| Source | Measurements | Limit |
| --- | --- | --- |
| Mac client | Process count, summed CPU percentage and RSS for executables inside the installed KiroCrew Nightly app; SSH tunnel listener reachability on local 5599 and absence on 5476 | `ps` CPU is a recent scheduler average. RSS can count shared pages more than once. The 5599 probe checks only the local tunnel listener; it does not establish a response from the remote Gateway. The sample does not measure all laptop agents. |
| EC2 host | CPU utilization over one second; total, available and used RAM; root filesystem used and total capacity | Memory used is total minus available. Values describe the host at sample time. |
| Gateway and MCP | Each systemd unit's active state; main process CPU over one second and RSS; loopback port reachability | Child processes are excluded. A reachable port proves TCP connectivity, not authentication, authorization or an agent response. |

Both schedules run once a minute. Each source retains at most 240 samples, about four hours when running continuously. The shared event file retains the last 200 first-sample, check-change, probe-error and recovery events. Routine unchanged samples do not create event entries. This is local retention; it is not a durable audit archive or native Crew SEL evidence.

Missing values are `null`; `status=partial` or `unknown` reports missing measurements. Known inactive services have zero main-process CPU/RSS. Failed TCP connections are `false`; OS probe errors are `null`. The dashboard must show freshness separately: a stopped client leaves a last-known sample, not a new sample claiming zero use.

## Data contract

`schema_version=1`, `collector=kirocrew-demo-custom`, `source=client|server`, UTC `collected_at`, `status=ok|partial|unknown`, fixed `metrics`, fixed `checks`, and an allowlisted `errors` array. Exact metric/check keys and ranges are enforced in `collector.py`. Unknown fields, arbitrary text, non-finite metrics, invalid status, oversized input, wrong source, samples more than five minutes from the server clock and non-increasing timestamps are rejected.

Server output is fixed under `/var/lib/kirocrew-demo-observability/`:

- `client.json` and `server.json`: latest samples.
- `client-history.jsonl` and `server-history.jsonl`: bounded sample history.
- `events.jsonl`: bounded status events with allowlisted codes, never arbitrary log text.

The directory is root-owned with group `crew`, mode `0750`. Files are root-owned with group `crew`, mode `0640`. The Gateway's `crew` process can read them and cannot change them. Writes use an exclusive bounded lock and atomic replacement. The client keeps only its latest local sample and upload result under `~/Library/Application Support/kirocrew-demo-observability/`; those files are user-owned, mode `0600`.

## Install and activate

Installation and activation are separate. Review the files before invoking these commands. Copy only the four runtime files (`collector.py`, `install.sh`, and the two unit files) to a staging directory on the existing ARM host through its pinned SSH alias. Run `sudo bash install.sh` from that directory. This installs the collector and systemd units; it does not enable the timer.

On the server, collect one stored sample and enable the schedule:

```sh
sudo /usr/bin/python3 /opt/kirocrew-demo/observability/collector.py server --store
sudo systemctl enable --now kirocrew-demo-observability.timer
sudo systemctl status kirocrew-demo-observability.timer --no-pager
```

From the project root on the Mac, inspect the dry-run sample and plan, then activate the client:

```sh
/usr/bin/python3 scripts/demo-telemetry.py collect-once
/usr/bin/python3 scripts/demo-telemetry.py setup
/usr/bin/python3 scripts/demo-telemetry.py setup --apply
```

`setup --apply` first uploads a valid sample to the installed receiver. It installs the LaunchAgent only after that upload succeeds. The job runs on load and every 60 seconds, using the exact Python interpreter that performed setup. Collection plus upload is bounded by the probe and SSH timeouts. An upload failure is recorded as a safe code; SSH stderr is neither stored nor printed.

The server systemd collector can access only loopback IP addresses, has a read-only system view except its data directory, and uses a 20-second service timeout. It needs no additional inbound rule. It never opens a listening port.

## Stop

```sh
/usr/bin/python3 scripts/demo-telemetry.py stop
/usr/bin/python3 scripts/demo-telemetry.py stop --apply
ssh kirocrew-demo-admin sudo systemctl disable --now kirocrew-demo-observability.timer
```

The client command checks the exact launchd job even if its plist was removed. It verifies the loaded interpreter and arguments belong to this collector, unloads that job, and confirms service absence before reporting success. An unknown launchd result fails the operation. It removes only its recognized, unchanged LaunchAgent plist. Run stop with the same Python interpreter used for setup. Samples and upload status remain for inspection. The Gateway and MCP continue running. Use the normal cloud lifecycle helper separately to stop the EC2 instance.

## Verification

```sh
/usr/bin/python3 -m unittest discover -s infrastructure/observability-collector -p 'test_*.py' -v
```

Tests cover process scope, unknown values, strict schema, arbitrary-field and error rejection, clock skew, oversized payloads, bounded history/events, replay rejection, file modes, symlink and writable-directory rejection, dry-run side effects, safe SSH failure reporting, missing-plist loaded jobs, unrelated job refusal and verified stop results. Live activation and dashboard rendering require separate receipts.
