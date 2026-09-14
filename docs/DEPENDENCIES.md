# Install and manage the demo dependencies

The checked-in presentation plays with Python and a browser. Live reproduction adds the macOS client, an ARM runtime bundle, AWS access and a separate Kiro CLI sign-in on the server. Choose the dependency group for the work you are doing; optional model reviewers are never required to present the demo.

From the project root:

```sh
python3 scripts/demo-dependencies.py plan --feature playback
python3 scripts/demo-dependencies.py apply --feature playback
python3 scripts/doctor.py --feature playback
python3 scripts/serve-recorded-demos.py --build output/kirocrew-native-controls-build.json --port 5612
```

Open `http://127.0.0.1:5612/`. The restricted server publishes only the files bound by the selected build receipt. It does not expose the project directory, AWS credentials or private captures.

| Feature | Installed or checked | When to use it |
|---|---|---|
| `playback` | Python 3.9+ and the current presentation's asset hashes | Present the existing deck, clips and screenshot tour |
| `authoring` | Python venv with `requirements-demo.txt`, Node 20.9+, locked npm packages, FFmpeg and ffprobe | Rebuild assets, process real footage and rehearse the isolated synthetic harness |
| `cloud` | AWS CLI v2, SSH and a venv with aiohttp/PyYAML | Prepare the ARM bundle and operate the explicit CloudFormation deployment |
| `native` | macOS, KiroCrew app identity, SSH, lsof, screencapture, FFmpeg/ffprobe, aiohttp/PyYAML and macOS permission observations | Run and record the actual Mac client against EC2 |
| `council` | Availability of the optional `grok` and `claude` commands | Use already installed, separately authenticated reviewers |
| `all` | Playback, authoring, cloud and native dependencies | Prepare a Mac for the whole demo; reviewers remain optional |

`preview` and `record` remain aliases for `playback` and `authoring`.

## Installation behavior

```sh
python3 scripts/demo-dependencies.py plan --feature all --with-browser
# Apply this scope when dependency installation is authorized:
python3 scripts/demo-dependencies.py apply --feature all --with-browser
python3 scripts/demo-dependencies.py status --feature all --with-browser
```

`plan` runs only local version probes and prints an argument array for each install stage. `apply` installs missing or incompatible system tools through an existing Homebrew installation, creates the project `.venv` when absent, installs pinned Python requirements, and runs `npm ci --ignore-scripts --no-audit --no-fund`. The npm command replaces this project's `node_modules` using its lockfile; no package lifecycle scripts run. It does not upgrade unrelated Homebrew packages. A failed stage stops the run and identifies earlier completed stages. Fix the reported prerequisite and rerun the same feature.

A Mac with no Python cannot run the helper yet. Install Homebrew using its reviewed [official installation instructions](https://brew.sh/), then run `brew install python@3.12`. Homebrew offers an installer package as well as its interactive script. This project does not execute a downloaded bootstrap script. The helper targets macOS system installation; Linux playback remains usable with Python installed through that machine's package manager.

`--with-browser` explicitly installs Chromium for the project's locked Playwright version. Omit it if an existing browser integration supplies the browser. [Playwright's browser documentation](https://playwright.dev/docs/browsers) explains why its browser binary must match the installed Playwright version. No browser or system dependency download occurs in `plan` or `status`.

Use `--project-root '/path/with spaces/kirocrew-demo'` from another directory. Use `--venv .build/demo-python` for a separate project environment and `--python /absolute/path/to/python3.12` to select an interpreter. A nonempty directory without `pyvenv.cfg`, an external path or a linked venv directory is rejected. The helpers never install into the system Python environment. Run subsequent project Python commands through the selected venv, or set `KIRO_DEMO_PYTHON` to its absolute `bin/python3` path for `demo.sh` and `native-demo.sh`.

To update dependencies, change the relevant reviewed version pins or npm lockfile, run the selected install again, and validate the resulting workflow. The historical server installer has separate hashes and compatibility checks: changing local Python packages does not update its runtime. To discard a project environment, stop processes using it and remove only that environment through your normal file-management workflow; the dependency helper does not uninstall shared Homebrew tools or delete environments.

## Product installation, permissions and runtime

Install KiroCrew Nightly through the user's product distribution. `doctor --feature native --app-path '/Applications/KiroCrew Nightly.app'` reads its bundle identity and version. The permission probes query Screen Recording and Accessibility for this process or its responsible application without prompting or changing them. They do not prove that a different recorder has permission, the Mac is unlocked, or a native window capture is fresh. Enable the actual automation/recording app under **System Settings → Privacy & Security**, reopen it when required, and inspect a fresh screenshot plus a visible UI action before recording.

The server runtime is prepared from an explicitly supplied compatible KiroCrew package using [ARM-RUNTIME-BUNDLE.md](ARM-RUNTIME-BUNDLE.md), then deployed through the ten stages in [LIVE-SETUP.md](LIVE-SETUP.md): runtime, services, fixtures, server integrations, managed policy, desktop, client telemetry, app, user-facing MCP and host-control fixtures. The bundle helper checks the supported version and dependency fingerprint and downloads the pinned ARM wheels and official Kiro CLI archive. It never copies app login state. A different Nightly must pass a reviewed compatibility update; the installer does not silently treat it as the accepted build.

Keep AWS credentials in the AWS CLI's existing credential provider. Use `config/demo.local.json` for account, stack, AWS profile name and SSH bindings; use `config/cloudformation.local.json` for the existing VPC, subnet and EC2 KeyName. Neither file contains credentials or a private key. The live setup validates the target before cloud or server changes. Kiro CLI authenticates on EC2 through its own flow; a working desktop login is not proof of remote CLI sign-in. Native acceptance also requires checking the selected backend, local Gateway cutover, server policy and actual tool outcomes.

Read [MANAGED-DEMO.md](MANAGED-DEMO.md) for the current recorded controls. After policy activation, `python3 scripts/verify-managed-host.py --config PATH --output NEW_RECEIPT` checks root-protected files, service-cgroup PTY denial in its own disposable child and native CLI process isolation observations. It does not restart the service or prove that a particular tool was sandboxed. The recorded managed receipts describe the existing deployment; fresh provisioning still needs its own sign-in, setup verification and native acceptance.

Before collecting a control take, finish all Gateway restarts and create a persistent native session with a READY-only, no-tool exchange. Start the observer after that session is idle. Let a timed macOS `screencapture -V` recording complete normally: SIGINT discarded the movie during this workflow. Confirm the file and its ffprobe duration before trimming. See the project's [recording reference](../.agents/skills/kirocrew-demo/references/recording.md) for the evidence boundaries.

Grok Build and Claude Code are optional product installations with their own authentication and usage. The helper checks command availability only, never installs them, logs in, launches reviews or substitutes a different model. When council review is requested, use [run-native-deck-council.py](../scripts/run-native-deck-council.py) and the appropriate current council helper; preserve the actual model and effort reported by each dispatch.
