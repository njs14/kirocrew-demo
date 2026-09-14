# Prepare the EC2 runtime from your installed KiroCrew package

The project can build a complete offline ARM bundle from an explicitly selected KiroCrew installation. It does not require the original developer's `.build` archives. The bundle contains the package, upstream distribution metadata, 48 hash-locked Linux ARM wheels, the official Kiro CLI 2.21.4 ARM archive, a standalone installer, and a manifest of every file.

This is a **custom Linux ARM repack**, not an official KiroCrew Linux release. The package's original build labels remain intact. Preparation does not establish that a new nightly passed the live control demonstrations.

## Supported inputs

The reviewed dependency contract currently covers these exact package versions:

- `0.7.0-nightly.20260912t060850`, used by the accepted EC2 demo.
- `0.7.0-nightly.20260913t061222`, the subsequently installed macOS nightly. Its upstream `METADATA` is byte-identical to the earlier package. This establishes dependency compatibility for preparation; it does not carry forward the earlier native enforcement verdict.

Both require upstream distribution metadata version `0.7.0` and the committed ARM dependency lock. Another version, changed dependency metadata, missing Linux ARM libraries, or an enterprise `BUILD_VERSION` stamp stops preparation. Review a new version's dependencies and live behavior before extending this allowlist. Do not edit the version string to get past the check.

Install KiroCrew through its official distribution, then select the package directory inside that installation. The script reads package bytes without importing the package. It accepts an unpacked official installation on any machine; a package archive must first be extracted and verified using that distribution's instructions. It does not download KiroCrew, inspect user homes, or copy credentials, conversations, sessions, or configuration.

The standard macOS nightly path is:

```text
/Applications/KiroCrew Nightly.app/Contents/Resources/backend-dist/kirocrew-backend-arm64/lib/python3.12/site-packages/kiro_crew
```

The matching `kirocrew-0.7.0.dist-info` directory is normally adjacent. Supply `--metadata /explicit/path/kirocrew-0.7.0.dist-info` when using a separately preserved package. A copied source tree without the original distribution metadata is insufficient.

## Plan and prepare on the Mac

Run from the project checkout with Python 3.10 or newer and pip installed. No global package installation is performed by this workflow. The target wheels are CPython 3.12/Linux ARM even when the preparer runs with a different supported Python on macOS.

```bash
python3 scripts/prepare-arm-runtime.py plan \
  --package '/Applications/KiroCrew Nightly.app/Contents/Resources/backend-dist/kirocrew-backend-arm64/lib/python3.12/site-packages/kiro_crew' \
  --output .build/arm-bundle

python3 scripts/prepare-arm-runtime.py prepare \
  --package '/Applications/KiroCrew Nightly.app/Contents/Resources/backend-dist/kirocrew-backend-arm64/lib/python3.12/site-packages/kiro_crew' \
  --output .build/arm-bundle
```

`plan` validates the source and prints the exact acquisition commands without creating output or downloading dependencies. `prepare` requires a fresh output directory under this checkout's ignored `.build`; it refuses replacement. Allow several minutes and at least 3 GiB of free space for preparation, validation, and temporary files. The pinned Kiro CLI archive is about 488 MiB compressed and its largest executable is about 791 MiB; validation hashes its archive members in bounded chunks.

Pip downloads wheels using the committed lock with `--require-hashes`, `--only-binary=:all:`, and explicit ARM/Python tags. The Kiro CLI archive comes from [the official versioned download host](https://prod.download.cli.kiro.dev/stable/2.21.4/kirocli-aarch64-linux.tar.xz) and must match SHA-256 `f582eac0e002b4d11bbd061d41fcb49d1d37626a2c1fe230373fcbf97755df6f`, recorded in the original [official manifest snapshot](../evidence/aws/arm-20260913/kiro-cli-manifest.json). This script never executes that archive's installation script.

For an offline repeat, supply both `--wheelhouse /path/to/previous-bundle/wheels` and `--kiro-cli-archive /path/to/previous-bundle/kirocli-aarch64-linux.tar.xz`. The same complete lock and architecture checks apply. A local cache is optional; the original project's private cache is never an implicit input.

Successful preparation prints `manifest` and `manifest_sha256`. Keep that digest with the deployment plan: it is the caller's binding to the reviewed bundle, not a value to discover afresh from an untrusted upload on the server. Archives use fixed timestamps and owners. The manifest omits machine-specific source paths, timestamps, and acquisition-cache differences.

## Verify and install on the ARM host

`scripts/setup-live-demo.py` stages this bundle using the project's explicit AWS/SSH configuration. The underlying installer also supports direct operation:

```bash
python3 infrastructure/install-runtime-bundle.py verify --bundle .build/arm-bundle

# After copying the whole bundle to the configured ARM server:
python3 /path/to/bundle/install-runtime-bundle.py plan \
  --bundle /path/to/bundle --manifest-sha256 REVIEWED_MANIFEST_SHA256

sudo python3 /path/to/bundle/install-runtime-bundle.py install \
  --bundle /path/to/bundle --manifest-sha256 REVIEWED_MANIFEST_SHA256 \
  --prefix /opt/kirocrew
```

Replace `REVIEWED_MANIFEST_SHA256` with the digest returned by local preparation. The `install` command requires it and verifies that the executing installer matches the bundled installer. `verify` and `plan` run on the Mac too; neither installs a runtime or claims native ARM execution.

Installation requires root, Ubuntu 24.04 ARM64, CPython 3.12 with `venv`, and SQLite FTS5. The CloudFormation host bootstrap supplies the operating-system prerequisites. The installer rejects another architecture, linked or writable runtime ancestors, an existing `venv`, and an existing installation receipt. Use the standard `/opt/kirocrew` prefix with the project's service units. A custom prefix is supported for separate runtime preparation, but the operator must align the service units and AppArmor profile before starting services.

Before creating the runtime, the installer verifies every bundle file, the runtime archive inventory, every wheel against its lock, the official CLI checksum, and ELF architecture. It takes a second verified copy under a root-private temporary directory before pip or extraction consumes the files. Runtime archives permit only regular files and directories in the two package roots. Symlinks, traversal, duplicate paths, foreign executables, and unlisted bundle files fail validation.

The runtime is installed at `/opt/kirocrew/venv`, owned by root without group or world write access. Pip runs offline with hash enforcement. The installer regenerates distribution `RECORD`, writes `ARM_REPACK.json`, runs `pip check` and a limited import/version check, then writes `/opt/kirocrew/runtime-installation.json`. A normal installation failure removes only the newly created `venv`; it never removes a preexisting runtime. An interruption that leaves a partial directory requires inspection before a retry.

Kiro CLI installation, the gateway service, MCP service, AppArmor, managed policy, owner access, telemetry, and normal user sign-in remain separate setup stages. Keeping these steps separate lets the project verify each boundary and retain explicit authentication in the correct product. The runtime installer starts no service, authenticates no account, installs no model, and modifies no existing KiroCrew configuration.

## Validate a newly prepared version

Use the project's live setup and policy checks, sign in normally on the server, then run the allowed/denied MCP, AWS, identity, and host-control cases described in the demo guide. Record the selected runtime version and the new bundle digest with those results. A successful source preparation, `pip check`, or fixture test does not replace those native observations.

The historical `infrastructure/install-arm-runtime.sh` and accepted September 13 receipts remain unchanged. They describe the frozen earlier deployment; new installations use this manifest-driven path and produce their own receipts.

Local regression checks for the bundler are:

```bash
python3 -m unittest scripts/tests/test_arm_runtime_bundle.py
```

They cover archive traversal, symlinks and special files, foreign ELF/Mach-O rejection, wheel hash enforcement, unsupported versions, output containment, preserved caller digests, and wrong-host failure before runtime creation. Native installation must be validated on the chosen ARM host.
