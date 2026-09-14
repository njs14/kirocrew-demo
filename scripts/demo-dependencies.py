#!/usr/bin/env python3
"""Plan, install, or inspect local dependencies for a selected demo workflow."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ("playback", "authoring", "cloud", "native", "council", "all")
ALIASES = {"preview": "playback", "record": "authoring"}
NATIVE_REQUIREMENTS = ("aiohttp==3.14.3", "PyYAML==6.0.3")
DEFAULT_BUILD = "output/kirocrew-native-controls-build.json"
PYTHON_PROBE = "import sys; print('.'.join(map(str, sys.version_info[:3])))"


def run_read(argv, cwd=None):
    """Bounded local version/metadata probes, with no product or account connection."""
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=15)
        return result.returncode == 0, result.stdout.strip()[:8192]
    except (OSError, subprocess.TimeoutExpired):
        return False, "unavailable"


def version(value):
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", value)
    return tuple(int(part or 0) for part in match.groups()) if match else (0, 0, 0)


def groups(feature):
    feature = ALIASES.get(feature, feature)
    if feature not in FEATURES:
        raise ValueError("Unknown feature: " + feature)
    # Reviewers are optional even for a complete live installation.
    return {"playback", "authoring", "cloud", "native"} if feature == "all" else {feature}


def project_paths(root, venv=None):
    root = Path(root).expanduser().resolve(strict=True)
    if not (root / "package.json").is_file() or not (root / "requirements-demo.txt").is_file():
        raise ValueError("Select the kirocrew-demo root containing package.json and requirements-demo.txt.")
    candidate = Path(venv).expanduser() if venv else root / ".venv"
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root) or resolved == root or candidate != resolved:
        raise ValueError("The dependency venv must be an unlinked directory inside this project.")
    if resolved.exists() and (not resolved.is_dir() or (any(resolved.iterdir()) and not (resolved / "pyvenv.cfg").is_file())):
        raise ValueError("Refusing to repurpose a non-venv directory; select a new --venv path.")
    return root, resolved


def python_executable(explicit=None, minimum=(3, 12, 0)):
    candidates = [explicit] if explicit else [shutil.which("python3.12"), sys.executable, shutil.which("python3")]
    for candidate in candidates:
        if not candidate:
            continue
        path = str(Path(candidate).expanduser().absolute())
        ok, value = run_read([path, "-I", "-c", PYTHON_PROBE])
        if ok and version(value) >= minimum:
            return path
    return None


def venv_compatible(venv):
    if not (venv / "pyvenv.cfg").exists():
        return False
    ok, output = run_read([str(venv / "bin/python3"), "-I", "-c", PYTHON_PROBE])
    return ok and version(output) >= (3, 12, 0)


def requirements(root, selected):
    if "authoring" in selected:
        return [line.strip() for line in (root / "requirements-demo.txt").read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
    return list(NATIVE_REQUIREMENTS) if selected & {"native", "cloud"} else []


def python_packages(python, required):
    if not python or not Path(python).is_file():
        return {item.split("==")[0]: None for item in required}
    names = [item.split("==")[0] for item in required]
    code = ("import importlib.metadata as m,json,sys\nresult={}\n"
            "for name in json.loads(sys.argv[1]):\n"
            " try: result[name]=m.version(name)\n"
            " except m.PackageNotFoundError: result[name]=None\n"
            "print(json.dumps(result))")
    ok, output = run_read([str(python), "-I", "-c", code, json.dumps(names)])
    try:
        return json.loads(output) if ok else {}
    except ValueError:
        return {}


def package_versions(root):
    result = {}
    for name in ("playwright", "sharp"):
        try:
            result[name] = json.loads((root / "node_modules" / name / "package.json").read_text())["version"]
        except (OSError, ValueError, KeyError, TypeError):
            result[name] = None
    return result


def permission_status():
    """Query only: these APIs do not request or modify macOS permissions."""
    if sys.platform != "darwin":
        return {"screen_recording": None, "accessibility": None}
    output = {}
    for label, library, symbol in (
        ("screen_recording", "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics", "CGPreflightScreenCaptureAccess"),
        ("accessibility", "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices", "AXIsProcessTrusted"),
    ):
        try:
            method = getattr(ctypes.CDLL(library), symbol)
            method.argtypes = []
            method.restype = ctypes.c_bool
            output[label] = bool(method())
        except (OSError, AttributeError):
            output[label] = None
    return output


def artifact_status(root, receipt=DEFAULT_BUILD):
    path = Path(receipt)
    if not path.is_absolute():
        path = root / path
    try:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Build receipt must be inside the project.")
        build = json.loads(path.read_text())
        files = build["serveFiles"]
        if not isinstance(files, dict) or not files:
            raise ValueError("Build receipt has no served files.")
        missing, changed = [], []
        for item in files.values():
            candidate = root / item["path"]
            if not candidate.resolve().is_relative_to(root) or candidate.is_symlink() or not candidate.is_file():
                missing.append(item["path"])
                continue
            data = candidate.read_bytes()
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                changed.append(item["path"])
        return not missing and not changed, {"build": str(path.relative_to(root)), "files": len(files), "missing": missing, "changed": changed}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return False, "Cannot validate current presentation: " + type(exc).__name__


def inspect(feature, root=ROOT, venv=None, python=None, app_path=None, with_browser=False, build=DEFAULT_BUILD):
    root, venv = project_paths(root, venv)
    selected = groups(feature)
    checks = []

    def check(name, passed, detail, required=True):
        checks.append({"name": name, "passed": bool(passed), "required": required, "detail": detail})

    minimum = (3, 9, 0) if selected == {"playback"} else (3, 12, 0)
    interpreter = python_executable(python, minimum)
    required_version = ".".join(str(value) for value in minimum[:2])
    check("python", interpreter is not None, interpreter or "Install Python " + required_version + "+ and rerun this command.")
    if "playback" in selected:
        check("playback_platform", sys.platform in {"darwin", "linux"}, "Restricted preview server supports macOS and Linux.")
        ok, detail = artifact_status(root, build)
        check("presentation_artifacts", ok, detail)
    commands = set()
    if "authoring" in selected:
        commands.update(("node", "npm", "ffmpeg", "ffprobe"))
    if "cloud" in selected:
        commands.update(("aws", "ssh"))
    if "native" in selected:
        commands.update(("ssh", "lsof", "ffmpeg", "ffprobe", "screencapture"))
    if "council" in selected:
        commands.update(("grok", "claude"))
    for command in sorted(commands):
        path = shutil.which(command)
        ok = path is not None
        detail = path or "Install " + command + "; see docs/DEPENDENCIES.md."
        if path and command in {"node", "aws"}:
            ran, output = run_read([path, "--version"])
            ok = ran and (version(output) >= (20, 9, 0) if command == "node" else output.startswith("aws-cli/2."))
            detail = output if ok else "Need Node 20.9+ or AWS CLI v2, respectively. Found: " + output
        check(command, ok, detail)
    required = requirements(root, selected)
    if required:
        check("venv_python", venv_compatible(venv), "The selected project venv must use Python 3.12+; choose a fresh --venv path if its interpreter is older.")
        actual = python_packages(venv / "bin/python3", required)
        missing = [item for item in required if actual.get(item.split("==")[0]) != item.split("==")[1]]
        check("python_packages", not missing, {"venv": str(venv), "missing_or_mismatched": missing})
    if "authoring" in selected:
        expected = json.loads((root / "package.json").read_text())["devDependencies"]
        actual = package_versions(root)
        check("node_packages", all(actual.get(name) == value for name, value in expected.items()), {"expected": expected, "installed": actual})
        if with_browser:
            ok, output = run_read([shutil.which("node") or "node", "-e", "const fs=require('fs'); const p=require('playwright').chromium.executablePath(); console.log(p); process.exit(fs.existsSync(p)?0:1)"], root)
            check("chromium", ok, output if ok else "Run dependency apply with --with-browser for the pinned Playwright Chromium.")
    if "native" in selected:
        check("native_platform", sys.platform == "darwin", "Live endpoint recording is supported on macOS only.")
        app = Path(app_path).expanduser() if app_path else Path("/Applications/KiroCrew Nightly.app")
        try:
            info = plistlib.loads((app / "Contents/Info.plist").read_bytes())
            identity = {key: info.get(key) for key in ("CFBundleIdentifier", "CFBundleShortVersionString", "CFBundleVersion")}
            check("kirocrew_app", identity["CFBundleIdentifier"] == "com.amazon.kiro.crew", {"path": str(app), **identity})
        except (OSError, ValueError):
            check("kirocrew_app", False, "Install the user's KiroCrew Nightly through its product distribution, or pass --app-path.")
        for name, allowed in permission_status().items():
            check(name, allowed is True, {"observed_for": "this process / its responsible application", "allowed": allowed,
                  "action": "If unavailable, enable the recording/automation application in macOS System Settings > Privacy & Security, reopen it, then verify a fresh screenshot and UI action."})
        check("native_acceptance", False, "Run deployment preflight, own-product Kiro CLI sign-in and a fresh visible native request. Local checks do not verify authentication, endpoint cutover or enforcement.", required=False)
    if "council" in selected:
        check("reviewer_authentication", False, "Optional: authenticate each reviewer in its own product and verify the requested model at dispatch. This check does not invoke models or consume usage.", required=False)
    return {"feature": ALIASES.get(feature, feature), "platform": sys.platform, "project_root": str(root),
            "scope": "Local prerequisites and artifact hashes; no remote connection, authentication or native enforcement check.",
            "passed": all(row["passed"] for row in checks if row["required"]), "checks": checks}


def installation_plan(feature, root=ROOT, venv=None, python=None, with_browser=False):
    root, venv = project_paths(root, venv)
    selected = groups(feature)
    if with_browser and "authoring" not in selected:
        raise ValueError("--with-browser applies to authoring or all.")
    minimum = (3, 9, 0) if selected == {"playback"} else (3, 12, 0)
    interpreter = python_executable(python, minimum)
    if python and interpreter is None:
        raise ValueError("The explicit --python executable must exist and report Python " + ".".join(str(value) for value in minimum[:2]) + "+.")
    brew = shutil.which("brew")
    formulae, manual, steps = [], [], []
    if interpreter is None:
        formulae.append("python@3.12")
        interpreter = "{managed_python}"
    needed = {}
    if "authoring" in selected:
        needed.update(node="node", npm="node", ffmpeg="ffmpeg", ffprobe="ffmpeg")
    if "native" in selected:
        needed.update(ffmpeg="ffmpeg", ffprobe="ffmpeg")
        manual.extend(["Install KiroCrew Nightly through its product distribution; use --app-path for a nonstandard location.",
                       "Grant Screen Recording and Accessibility to the actual recording/automation app in macOS settings; verify a fresh visible capture before recording.",
                       "Authenticate the server's original Kiro CLI through its own sign-in after live setup; do not copy client credentials."])
    if "cloud" in selected:
        needed["aws"] = "awscli"
        manual.append("Select account, stack, AWS profile name and trusted SSH bindings in config/demo.local.json; set the existing VPC, subnet and EC2 KeyName in config/cloudformation.local.json. Credentials and private keys stay outside the project.")
    for command, formula in needed.items():
        path = shutil.which(command)
        valid = path is not None
        if path and command in {"node", "aws"}:
            ok, output = run_read([path, "--version"])
            valid = ok and (version(output) >= (20, 9, 0) if command == "node" else output.startswith("aws-cli/2."))
            if not valid:
                manual.append("After Homebrew installation, put its " + command + " on PATH ahead of the older executable.")
        if not valid:
            formulae.append(formula)
    formulae = sorted(set(formulae))
    if formulae:
        if not brew:
            manual.append("Install Homebrew from https://brew.sh/ using its reviewed installer, then rerun this plan. This helper never executes a remote bootstrap script.")
        steps.append({"id": "system_tools", "argv": [brew or "brew", "install", *formulae], "scope": "Homebrew prefix; missing or incompatible selected tools only"})
    required = requirements(root, selected)
    if required:
        if (venv / "pyvenv.cfg").exists() and not venv_compatible(venv):
            raise ValueError("The selected venv has a missing or older Python. Choose a fresh --venv path; this helper does not replace an existing interpreter.")
        if not (venv / "pyvenv.cfg").exists():
            steps.append({"id": "venv", "argv": [interpreter, "-m", "venv", str(venv)], "scope": str(venv)})
        argv = [str(venv / "bin/python3"), "-m", "pip", "install", "--disable-pip-version-check"]
        argv += ["-r", str(root / "requirements-demo.txt")] if "authoring" in selected else list(required)
        steps.append({"id": "python_packages", "argv": argv, "scope": str(venv)})
    if "authoring" in selected:
        steps.append({"id": "node_packages", "argv": ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"], "scope": str(root / "node_modules")})
        if with_browser:
            steps.append({"id": "chromium", "argv": ["node", str(root / "node_modules/playwright/cli.js"), "install", "chromium"], "scope": "Playwright's per-user browser cache"})
    if "council" in selected:
        manual.append("Reviewers are optional: use the user's installed Grok Build and Claude Code, their own authentication and requested model availability. This helper does not install or invoke paid reviewers.")
    for command in (["ssh"] if selected & {"cloud", "native"} else []) + (["lsof", "screencapture"] if "native" in selected else []):
        if not shutil.which(command):
            manual.append("Restore the macOS-provided " + command + " utility before this workflow.")
    blockers = []
    if sys.platform != "darwin" and (formulae or "native" in selected):
        blockers.append("Automated system dependency installation and the live endpoint target macOS. Playback works on supported Linux with Python installed separately.")
    if formulae and not brew:
        blockers.append("Homebrew is unavailable; complete its reviewed installation first.")
    return {"schema_version": 1, "feature": ALIASES.get(feature, feature), "project_root": str(root), "venv": str(venv),
            "mode": "plan", "network_or_install_performed": False, "python": interpreter,
            "steps": steps, "manual_steps": manual, "blockers": blockers, "can_apply": not blockers}


def apply_plan(plan):
    if plan["blockers"]:
        raise ValueError(" ".join(plan["blockers"]))
    root = Path(plan["project_root"])
    completed = []
    managed_bin = None
    for step in plan["steps"]:
        argv = list(step["argv"])
        if "{managed_python}" in argv:
            ok, prefix = run_read([shutil.which("brew") or "brew", "--prefix", "python@3.12"])
            if not ok or not Path(prefix).is_absolute():
                raise ValueError("Cannot resolve Homebrew Python 3.12 after installation.")
            argv[argv.index("{managed_python}")] = str(Path(prefix) / "bin/python3.12")
        env = dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1", HOMEBREW_NO_ANALYTICS="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
        if managed_bin:
            env["PATH"] = managed_bin + os.pathsep + env.get("PATH", "")
            if not Path(argv[0]).is_absolute():
                argv[0] = shutil.which(argv[0], path=env["PATH"]) or argv[0]
        # argv prevents interpolation when a checkout path contains spaces.
        print("Installing " + step["id"] + " …", file=sys.stderr, flush=True)
        result = subprocess.run(argv, cwd=root, env=env, stdout=sys.stderr, stderr=sys.stderr)
        if result.returncode:
            raise RuntimeError("Installation stopped at " + step["id"] + "; earlier completed stages: " + ", ".join(completed))
        completed.append(step["id"])
        if step["id"] == "system_tools":
            ok, prefix = run_read([argv[0], "--prefix"])
            if not ok or not Path(prefix).is_absolute():
                raise ValueError("System tools installed, but Homebrew's prefix could not be resolved. Fix PATH and rerun the plan.")
            managed_bin = str(Path(prefix) / "bin")
    return {**plan, "mode": "apply", "network_or_install_performed": bool(completed), "completed": completed,
            "note": "Run status for local readiness, then complete manual product/permission steps before native acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply", "status"))
    parser.add_argument("--feature", choices=FEATURES + tuple(ALIASES), default="playback")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--venv", type=Path)
    parser.add_argument("--python", help="Explicit Python executable: 3.9+ for playback, 3.12+ for other workflows")
    parser.add_argument("--app-path", type=Path)
    parser.add_argument("--with-browser", action="store_true")
    parser.add_argument("--build", default=DEFAULT_BUILD, help="Presentation build receipt for playback status")
    args = parser.parse_args()
    try:
        if args.mode == "status":
            result = inspect(args.feature, args.project_root, args.venv, args.python, args.app_path, args.with_browser, args.build)
        else:
            result = installation_plan(args.feature, args.project_root, args.venv, args.python, args.with_browser)
            if args.mode == "apply":
                result = apply_plan(result)
        print(json.dumps(result, indent=2))
        return 1 if args.mode == "status" and not result["passed"] else 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc), "mode": args.mode}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
