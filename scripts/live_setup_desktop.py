"""Bounded macOS client cutover used by setup-live-demo.py.

The native contracts are website/electron/{host-config,local-gateway,
gateway-supervisor}.js in KiroCrew: remoteHosts is keyed by local port; remote
owner bootstrap uses the default SSH configuration. This helper configures that
existing flow. It never invokes the owner helper, reads token storage, opens the
app, or claims a native connection merely because files were installed.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shlex
import stat
import subprocess
import sys

_SPEC = importlib.util.spec_from_file_location("_live_setup_demo_cloud", Path(__file__).with_name("demo-cloud.py"))
_CLOUD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CLOUD)
MAX_CONFIG = 4 * 1024 * 1024
OWNER_HELPER = "/usr/local/bin/kirocrew-owner-token"
REMOTE_PATH = "/opt/kirocrew/venv/bin:/usr/local/bin:/usr/bin:/bin"


def _require(value, message):
    if not value:
        raise RuntimeError(message)


def _parent_guard(path):
    """No redirected parents or writable shared directory below the root."""
    _require(path.is_absolute(), "Desktop paths must be absolute.")
    for candidate in (path.parent, *path.parent.parents):
        info = candidate.lstat()
        sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
        _require(stat.S_ISDIR(info.st_mode) and info.st_uid in (0, os.getuid())
                 and (not info.st_mode & 0o022 or sticky_root),
                 "A desktop configuration parent is redirected or writable by another user.")
    _require(path.parent.stat().st_uid == os.getuid(), "The destination directory must belong to this user.")


def _read_regular(path, limit=MAX_CONFIG, *, native_store=False):
    _parent_guard(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        current = path.lstat()
        private_native_store = native_store and not path.parent.stat().st_mode & 0o077
        _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                 and (not info.st_mode & 0o022 or private_native_store) and info.st_size <= limit
                 and (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino),
                 "Desktop input must be a bounded regular user-owned file without group/other write access.")
        data = os.read(descriptor, limit + 1)
        _require(len(data) <= limit, "Desktop input exceeded its size limit.")
        return data
    finally:
        os.close(descriptor)


def _unique(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "Desktop configuration has duplicate JSON keys.")
        value[key] = item
    return value


def desktop_definition(config):
    """Return a declarative, nonsecret plan without reading files or processes."""
    ssh = config["ssh"]
    args = argparse.Namespace(config=config)
    entry = {"host": ssh["admin_alias"], "binPath": OWNER_HELPER,
             "remotePort": str(ssh["remote_port"]), "remotePath": REMOTE_PATH}
    return {
        "platform": "macOS", "client_config": config["client"]["config_path"],
        "runLocalGateway": False, "remote_port_key": str(ssh["local_port"]),
        "remote_entry": entry, "tunnel_mode": config["tunnel"]["mode"],
        "tunnel_argv": _CLOUD.tunnel_command(args),
        "launch_plist": config["tunnel"]["launch_plist_path"] if config["tunnel"]["mode"] == "launchagent" else None,
        "requirements": ["Quit the configured KiroCrew app before applying.",
                         "Install the root-owned owner helper on EC2 first.",
                         "The native app must resolve the reviewed aliases through ~/.ssh/config.",
                         "Select the configured remote port after reopening; other remote hosts are preserved."],
        "native_connection_verified": False,
    }


def _client_change(config):
    path = Path(config["client"]["config_path"])
    original = _read_regular(path, native_store=True)
    try:
        value = json.loads(original, object_pairs_hook=_unique)
    except (ValueError, UnicodeError):
        raise RuntimeError("Desktop configuration is not valid UTF-8 JSON.") from None
    _require(isinstance(value, dict), "Desktop configuration must be a JSON object.")
    hosts = value.get("remoteHosts", {})
    _require(isinstance(hosts, dict), "Desktop remoteHosts must be an object.")
    definition = desktop_definition(config)
    port, wanted = definition["remote_port_key"], definition["remote_entry"]
    _require(port != "80", "The native client cannot safely select remote port 80.")
    current = hosts.get(port, {})
    _require(isinstance(current, dict), "The configured remote port has an incompatible entry.")
    _require(all(key not in current or current[key] == item for key, item in wanted.items()),
             "The configured remote port belongs to another host or runtime; refusing to replace it.")
    changed = copy.deepcopy(value)
    changed["runLocalGateway"] = False
    changed.setdefault("remoteHosts", {})[port] = {**current, **wanted}
    return original, (json.dumps(changed, indent=2, ensure_ascii=False) + "\n").encode(), value != changed or bool(path.stat().st_mode & 0o077)


def _inspect_app(config, *, stopped):
    _require(sys.platform == "darwin", "Desktop cutover requires macOS.")
    client = config["client"]
    _require(client["app_path"], "Configure the installed macOS KiroCrew app path.")
    app = Path(client["app_path"])
    expected_pattern = "^" + re.escape(str(app)) + "/Contents/MacOS/"
    accepted_patterns = (expected_pattern, expected_pattern.replace("\\ ", " "))
    _require(client["process_pattern"] in accepted_patterns,
             "client.process_pattern must be the exact anchored prefix of client.app_path/Contents/MacOS/.")
    info_path = app / "Contents/Info.plist"
    # System-installed app bundles can be root-owned; do not apply the user-file guard.
    _require(app.is_dir() and not app.is_symlink() and info_path.is_file()
             and not info_path.is_symlink() and info_path.stat().st_size <= 65536,
             "The configured native app bundle is missing or redirected.")
    try:
        info = plistlib.loads(info_path.read_bytes())
    except Exception:
        raise RuntimeError("The configured native app Info.plist is unreadable.") from None
    _require(info.get("CFBundleIdentifier") == "com.amazon.kiro.crew", "The configured app is not KiroCrew.")
    running = _CLOUD.run(["/usr/bin/pgrep", "-f", expected_pattern], timeout=10)
    _require(running.returncode in (0, 1), "Could not inspect the configured native app process.")
    if stopped:
        _require(running.returncode == 1, "Quit the configured KiroCrew app before applying desktop cutover.")
    return {"bundle_id": info["CFBundleIdentifier"], "running": running.returncode == 0}


def _inspect_ssh(config):
    ssh = config["ssh"]
    selected = Path(ssh["config_path"])
    _require(selected == Path.home() / ".ssh/config",
             "The native app uses ~/.ssh/config without -F. Put the reviewed aliases there before desktop cutover; a custom SSH config is not adopted automatically.")
    source = _read_regular(selected, 262144).decode("utf-8")
    for line in source.splitlines():
        tokens = shlex.split(line, comments=True)
        # Includes and Match exec can execute code even during ssh -G. Require
        # a separately reviewed flattened config instead of traversing them.
        directive = tokens[0].split("=", 1)[0].lower() if tokens else ""
        _require(directive not in ("include", "match"),
                 "Desktop SSH setup requires a directly reviewable config without Include or Match directives.")
    _, address = _CLOUD.ssh_update_text(source, "10.0.0.2", config)
    known = Path(ssh["known_hosts_path"])
    _read_regular(known, 262144)
    pins = _CLOUD.run(["/usr/bin/ssh-keygen", "-F", ssh["host_key_alias"], "-f", str(known)], timeout=10)
    _require(pins.returncode == 0, "The configured host key alias has no pinned key.")
    for alias, user in ((ssh["gateway_alias"], "crew"), (ssh["admin_alias"], "ubuntu")):
        result = _CLOUD.run(["/usr/bin/ssh", "-G", alias], timeout=10)
        _require(result.returncode == 0 and len(result.stdout) <= 65536,
                 "Cannot inspect the native app's effective SSH settings.")
        fields = {}
        for line in result.stdout.splitlines():
            key, _, item = line.partition(" ")
            fields.setdefault(key, []).append(item)
        wanted = {"user": user, "hostname": address, "port": "22",
                  "stricthostkeychecking": "true", "identitiesonly": "yes",
                  "forwardagent": "no", "hostkeyalias": ssh["host_key_alias"],
                  "userknownhostsfile": str(known)}
        _require(all(fields.get(key) == [item] for key, item in wanted.items()),
                 "Effective native SSH aliases do not preserve the expected account and host-key guards.")
        _require(fields.get("permitlocalcommand", ["no"]) == ["no"]
                 and fields.get("remotecommand", ["none"]) == ["none"],
                 "Effective SSH settings include an unexpected local or remote command.")


def _plist_definition(config):
    return {"Label": config["tunnel"]["launch_label"],
            "ProgramArguments": desktop_definition(config)["tunnel_argv"],
            "RunAtLoad": True, "KeepAlive": True, "ProcessType": "Background"}


def _inspect_tunnel(config):
    if config["tunnel"]["mode"] == "manual":
        return {"mode": "manual", "state": "operator_managed"}
    args = argparse.Namespace(config=config)
    path = Path(config["tunnel"]["launch_plist_path"])
    exists = path.exists() or path.is_symlink()
    if exists:
        raw = _read_regular(path, 65536)
        try:
            plist = plistlib.loads(raw)
        except Exception:
            raise RuntimeError("The tunnel LaunchAgent is not a valid plist.") from None
        wanted = _plist_definition(config)
        historical = {"Label": wanted["Label"], "ProgramArguments": wanted["ProgramArguments"],
                      "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 15,
                      "StandardErrorPath": str(Path.home() / ".local/state/kirocrew-demo/tunnel.stderr.log"),
                      "StandardOutPath": str(Path.home() / ".local/state/kirocrew-demo/tunnel.stdout.log")}
        _require(plist == wanted or plist == historical,
                 "The existing tunnel LaunchAgent differs from the managed definition; refusing to adopt it.")
        if plist == historical:
            for key in ("StandardErrorPath", "StandardOutPath"):
                log = Path(plist[key])
                _parent_guard(log)
                if log.exists() or log.is_symlink():
                    info = log.lstat()
                    _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o022,
                             "An existing tunnel log is redirected or writable by another user.")
    loaded = _CLOUD.managed_tunnel_job(args)
    _require(not loaded or exists, "A loaded tunnel job has no matching managed plist; refusing to adopt it.")
    return {"mode": "launchagent", "state": "loaded" if loaded else "absent", "plist_exists": exists}


def plan_desktop(config):
    """Inspect readiness without mutation; missing prerequisites are returned as issues."""
    plan = desktop_definition(config)
    issues = []
    if not config.get("_config_path"):
        issues.append("Select an explicit project configuration before desktop cutover.")
    for name, operation in (("client", lambda: _inspect_app(config, stopped=False)),
                            ("config_change", lambda: {"needed": _client_change(config)[2]}),
                            ("ssh", lambda: _inspect_ssh(config)),
                            ("tunnel", lambda: _inspect_tunnel(config))):
        try:
            plan[name] = operation()
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError):
            # Exceptions below contain only our fixed operational messages or
            # file paths; raw subprocess output and JSON data are never exposed.
            error = sys.exc_info()[1]
            issues.append(str(error))
    plan["issues"] = issues
    plan["ready_for_apply"] = not issues and not plan.get("client", {}).get("running", True)
    return plan


def _create_plist(config):
    path = Path(config["tunnel"]["launch_plist_path"])
    # Create just the exact LaunchAgents directory when its parent is trusted.
    if not path.parent.exists():
        _parent_guard(path.parent)
        path.parent.mkdir(mode=0o700)
    _parent_guard(path)
    raw = plistlib.dumps(_plist_definition(config), sort_keys=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _tighten_mode(path, original):
    """Correct only permissions when bytes already match, without following links."""
    _parent_guard(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        current = path.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and info.st_nlink == 1
                 and (current.st_dev, current.st_ino) == (info.st_dev, info.st_ino)
                 and os.read(fd, MAX_CONFIG + 1) == original,
                 "Native configuration changed before its permission correction.")
        os.fchmod(fd, 0o600)
        os.fsync(fd)
    finally:
        os.close(fd)


def apply_desktop(config):
    """Configure the stopped native client and, optionally, its exact SSH job."""
    _require(config.get("_config_path"), "Choose desktop configuration explicitly with --config.")
    _inspect_app(config, stopped=True)
    original, replacement, changed = _client_change(config)
    _inspect_ssh(config)
    tunnel = _inspect_tunnel(config)
    args = argparse.Namespace(config=config)
    if tunnel["mode"] == "launchagent":
        if not tunnel["plist_exists"]:
            _create_plist(config)
        if tunnel["state"] == "absent":
            # The shared helper rechecks both loaded identity and plist bytes.
            _CLOUD.tunnel(args, True, apply=True)
        _require(_CLOUD.managed_tunnel_job(args), "The managed tunnel job did not load; the native config was not changed.")
    _inspect_app(config, stopped=True)
    path = Path(config["client"]["config_path"])
    _require(_read_regular(path, native_store=True) == original, "The native configuration changed while preparing cutover.")
    if changed and original == replacement:
        _tighten_mode(path, original)
        backup = None  # Only mode changed; original bytes are still the live file.
    else:
        backup = _CLOUD.atomic_backup_write(path, original, replacement) if changed else None
    _require(_client_change(config)[2] is False, "Desktop cutover did not retain its expected fields.")
    return {**desktop_definition(config), "applied": True, "config_changed": changed,
            "backup_path": str(backup) if backup else None,
            "tunnel_state": "loaded" if tunnel["mode"] == "launchagent" else "manual_command_required",
            "next_step": "Start the printed SSH command if using manual mode; reopen KiroCrew and select the configured remote port. Verify native connection in the app."}
