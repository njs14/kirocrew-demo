# Run the demo on another machine

The recordings play without an AWS account or KiroCrew installation. Live controls need a separately installed KiroCrew runtime and an existing deployment. Historical recordings and receipts describe the accepted deployment at their recorded time; copying this repository does not reproduce their results.

## Select one deployment explicitly

Copy `config/demo.example.json` to the ignored `config/demo.local.json` and set your AWS account ID, stack name and verified SSH host key alias. Keep credentials in your existing AWS CLI profile or credential provider, and keep private keys in your SSH setup. The JSON loader rejects credential fields and unknown keys.

```sh
cp config/demo.example.json config/demo.local.json
# Edit the example account, stack and SSH settings before using it.
export KIRO_DEMO_CONFIG="$PWD/config/demo.local.json"
python3 scripts/demo-cloud.py status
```

Every helper also accepts `--config PATH`. Relative local paths are relative to the JSON file, and `~` refers to the current user's home. There is no automatic search for `demo.local.json`; cloud operations cannot select an account or stack from defaults. The example account ID is a placeholder.

The shared configuration modules are:

| Section | Configurable values |
|---|---|
| `aws` | Region, profile name, expected account ID, stack name, optional exact stack ARN and instance ID/type/architecture, resource project tag, offline evidence directory |
| `ssh` | Config file, pinned known-hosts file and host key alias, gateway/admin aliases, local tunnel and remote Gateway ports, public/private/auto address selection |
| `client` | App bundle and config paths, anchored process pattern, exact Linux executable, local Gateway port, optional local-port observation |
| `tunnel` | Manual mode or macOS LaunchAgent, label and plist path |
| `telemetry` | Local state directory, timer label/path/interval, remote collector path |
| `probe` | Local operator port, static asset and receipt directories, expected allowed-object SHA256, remote installation root |

`client.process_pattern` follows an explicitly supplied app path unless a pattern is supplied too. Linux users should leave `client.app_path` unset and provide `client.executable` only when they want measurements for that exact installed executable.

## Existing network and SSH access

Use [DEPLOYMENT.md](DEPLOYMENT.md) to select an existing VPC and subnet. These helpers do not create a VPC, subnet, NAT gateway, VPN or bastion. A private subnet needs an existing route from your machine and suitable outbound access for installation. Choosing a subnet does not establish that route.

Create and verify your dedicated SSH host-key entry using your established trusted process. The helpers do not trust a newly scanned key automatically. Configure one shared SSH `Host` block containing the two aliases, a single `HostName`, `StrictHostKeyChecking yes`, `IdentitiesOnly yes`, the configured `HostKeyAlias` and dedicated `UserKnownHostsFile`. Use alias-specific `User` values (`crew` for the Gateway alias; the instance administration user for the admin alias), and your own `IdentityFile`.

`demo-cloud.py` requires the instance and security group to belong to the selected CloudFormation stack. It also checks account identity, placement, project tags and the existing single TCP 22 `/32` ingress rule. It rejects drift before making a change. Optional exact resource bindings pin a known deployment further; update those values only after reviewing a legitimate replacement.

```sh
python3 scripts/demo-cloud.py start --config config/demo.local.json
python3 scripts/demo-cloud.py update-my-ip --config config/demo.local.json --client-ip 203.0.113.10
# Review the plan, then repeat the intended command with --apply.
```

The example IPv4 above illustrates syntax; replace it with your actual client source address. Public routing requires a globally routable IPv4. With `ssh.address_mode="private"`, use the source IPv4 that EC2 sees through your existing VPN or routed connection; public egress discovery cannot determine it. The rule remains a single `/32`. `auto` uses an available public address, otherwise a private address. A stopped instance with no public address therefore requires `--client-ip` in auto mode; choose `public` when that is the intended deployment path.

On Linux, leave `tunnel.mode` as `manual`. Start/stop can operate the bound instance and update the reviewed SSH block, then print the strict SSH tunnel command for you to run. They do not stop or restart an arbitrary tunnel process. On macOS, `launchagent` mode verifies the exact managed plist before restarting it. A configured port must match the actual client remote-host entry and installed tunnel.

Saved-receipt checks use `--offline`; they never permit `--apply`. Point `aws.evidence_dir` or `--evidence-dir` at a complete compatible snapshot and use a config whose bindings match that snapshot. Historic receipts from a replaced instance need their own configuration.

## Python and the two live entry points

The shell wrappers choose `KIRO_DEMO_PYTHON`, then `.venv/bin/python3`, then `python3` on your PATH. Set the override to an absolute executable path. Both wrappers start a fresh process with a scrubbed environment. The synthetic wrapper retains the explicit baseline-manifest path; the native wrapper retains the home directory for SSH and the explicit configuration selector.

The synthetic control runner needs Python 3.12+ with the reviewed KiroCrew dependencies and a verified baseline snapshot or pinned source checkout. The native client needs Python 3.10+ with `aiohttp`. A generic Python installation alone does not contain the KiroCrew runtime. Use the reviewed package snapshot preparation in [RECORDING.md](RECORDING.md); runtime source and binary archives are not silently downloaded by these wrappers.

```sh
python3 scripts/prepare-demo-baseline.py \
  --package /resolved/path/to/site-packages/kiro_crew \
  --output .build/demo-baselines/my-installed-build
export KIRO_DEMO_BASELINE="$PWD/.build/demo-baselines/my-installed-build/manifest.json"
KIRO_DEMO_PYTHON=/absolute/path/to/runtime/bin/python3 ./demo.sh --validate-baseline
KIRO_DEMO_PYTHON=/absolute/path/to/runtime/bin/python3 ./demo.sh
KIRO_DEMO_PYTHON=/absolute/path/to/venv/bin/python3 ./native-demo.sh --help
```

The synthetic runner creates isolated local state and disables networking. It records scripted or interactive harness approval, depending on its arguments. It cannot establish native Kiro CLI acceptance.

The native helper's `run` operation accepts `--config`; explicit `--gateway-port` and `--admin-host` arguments override those configuration values. Its `plan`, `approve` and `reject` operations keep their existing local behavior. Run `./native-demo.sh run --help` for the receipt and expected-object-digest arguments.

The EC2 sign-in helper accepts the same explicit configuration:

```sh
python3 scripts/ec2-login.py --config config/demo.local.json
```

It requires an interactive terminal, SSH and `lsof`. It still supports the verified Kiro CLI **2.21.4** login protocol only; another CLI version needs a reviewed protocol update. Login uses a fresh remote flow and verifies ownership of its temporary callback listener. It does not transfer a local login or credentials to EC2.

## Telemetry and the operator screen

A read-only collection works without a target config and does not upload:

```sh
python3 scripts/demo-telemetry.py collect-once
python3 scripts/demo-telemetry.py collect-once --config config/demo.local.json
```

Uploads and timer setup require explicit configuration and `--apply`. macOS timer operations are `setup` and `stop`; Linux users can collect on demand and use their existing scheduling or client workflow. Linux process measurements read only `/proc/<pid>/exe` matches for `client.executable`. The local Gateway state stays unknown on Linux unless `client.check_local_gateway=true` explicitly enables that port observation. An absent port is an observation, not proof of a persisted client preference.

When migrating the old demo timer, `setup` accepts only its exact original interpreter/script/`collect-once --apply` invocation or the exact new config-bound invocation. Use the same interpreter as the installed job. The new plist includes the absolute configuration path. A migrated `stop` command must use that same configuration.

The deployed standalone collector also exposes bounded CLI flags and `KIRO_DEMO_*` environment settings for existing service names, ports, disk path, store directory and reader group. Run its `--help` for those fields. Changing its store location requires configuring the existing receiver and read-only dashboard to use the same directory; this repository does not apply such a migration automatically.

```sh
python3 scripts/serve-demo-probes.py --config config/demo.local.json
```

The operator screen binds only `127.0.0.1` at `probe.port`. Starting it runs no command. Its buttons select one of two fixed command types: the remote direct MCP probe or the isolated local synthetic rehearsal. HTTP input cannot choose a host, shell command or file path. The SSH target and expected object digest come from the selected local configuration; receipts go to `probe.evidence_dir`.

The remote product layout remains intentional: Linux users `crew` and `mcp-demo`, the MCP token file under `/etc/kirocrew-demo`, the Gateway's service contract, and MCP loopback port `8001`. The server installers retain the accepted runtime packaging and architecture gates. A successful CloudFormation stack supplies the host, role, bucket and network configuration; it does not produce a running KiroCrew app or seed the S3 fixtures.

## Prepare the ARM host before service installation

The existing ARM scripts support Ubuntu 24.04 with CPython 3.12 and AArch64. They are fixed artifact installers for the accepted custom repack, not release downloaders. A fresh clone does not include those binary archives or a wheelhouse. Obtain and review the corresponding artifacts separately; substituting another release requires a reviewed checksum, dependency and behavior update.

Stage the following files under root-owned `/opt/kirocrew-demo/install` through your configured trusted administration connection:

| Phase | Required staged files | Source and constraint |
|---|---|---|
| Runtime | `kirocrew-nightly-snapshot.tar.gz`, `crew-dist-info.tar.gz`, `crew-requirements-linux-arm64.lock`, `wheels/` | The two archives and wheelhouse are separately supplied. `install-arm-runtime.sh` pins archive/lock SHA256 values, accepts only the frozen repack and installs hash-locked wheels without a package-index lookup. |
| Services | `kirocli-aarch64-linux.tar.xz` | Separately supplied official Kiro CLI 2.21.4 archive matching the checksum in `configure-arm-services.sh`. |
| Services | `mcp-enforcement/server.py`, `mcp-enforcement/probe.py`, `mcp-enforcement/requirements.txt` | Copy these files from this repository's `infrastructure/mcp-enforcement/` directory. |
| Services | `configure-demo.py`, `kirocrew-demo-wrapper.sh`, `kirocrew-demo.service`, `kirocrew-mcp-demo.service` | Copy from this repository's `infrastructure/` directory. |

Verify the CloudFormation bootstrap marker and metadata firewall as documented in [DEPLOYMENT.md](DEPLOYMENT.md). `install-arm-runtime.sh` requires that prepared host and refuses an existing `/opt/kirocrew/venv`. Its result is the root-owned Crew runtime and launcher at that path; it starts no Gateway. The subsequent service installer also needs the existing `crew` and `mcp-demo` users, Ubuntu administration user's reviewed SSH `authorized_keys`, AppArmor ABI 4.0 and an available `apparmor_parser`. It must not be run against an already configured host.

`configure-arm-services.sh` requires the stack's actual bucket name and region through `--bucket`/`--region` or `DEMO_S3_BUCKET`/`AWS_REGION`. It refuses existing demo configuration before installation, then configures only that prepared host:

```sh
# On the prepared ARM host, after staging and reviewing the listed artifacts:
sudo bash /path/to/configure-arm-services.sh \
  --bucket YOUR-STACK-DEMO-BUCKET --region YOUR-AWS-REGION
```

The fresh bucket is initially empty. Before a probe, provision two tiny, non-sensitive objects through your chosen administrator AWS identity: `allowed/sentinel.txt` and `denied/sentinel.txt`. Both must exist. Keep a provisioning receipt with their bucket, keys, byte counts and SHA256 values; set `probe.expected_allowed_sha256` to the actual allowed object's digest in your local configuration. The example digest represents the old accepted fixture and must not be assumed for a new object. Keep each object at or below the service's 4 KiB limit. The stack's role policy allows the allowed object and explicitly denies the denied object; the existence receipt is needed to attribute the resulting 403 accurately.

Owner-token client integration, native CLI sign-in, telemetry collector installation and the read-only observability app are separate modules. Inspect their existing scripts and runtime-specific requirements before applying them. Installing the two services alone does not configure every admin portal feature or close the native sign-in acceptance gate.

## Local validation

These checks use generated fixtures and local subprocess stubs, with no live AWS or native backend operation:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_demo_config.py'
python3 -m unittest discover -s scripts/tests -p 'test_demo_cloud.py'
python3 -m unittest discover -s scripts/tests -p 'test_demo_probes.py'
python3 infrastructure/observability-collector/test_collector.py
bash -n demo.sh native-demo.sh infrastructure/configure-arm-services.sh
```
