"""Validated, credential-free local demo configuration. Reading never performs I/O beyond the JSON file."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def defaults():
    home = Path.home()
    darwin = sys.platform == "darwin"
    support = home / ("Library/Application Support" if darwin else ".local/state")
    app = "/Applications/KiroCrew Nightly.app"
    return {
        "schema_version": 1,
        "aws": {"region": "us-east-1", "profile": None, "account_id": None, "stack_name": None,
                "stack_arn": None, "instance_id": None, "instance_type": None, "architecture": None,
                "project_tag": "kirocrew-demo", "evidence_dir": str(ROOT / "evidence/aws")},
        "ssh": {"config_path": str(home / ".ssh/config"), "known_hosts_path": str(home / ".ssh/kirocrew-demo-known_hosts"),
                "aliases": ["kirocrew-demo", "kirocrew-demo-admin"], "host_key_alias": None,
                "gateway_alias": "kirocrew-demo", "admin_alias": "kirocrew-demo-admin",
                "local_port": 5599, "remote_port": 5476, "address_mode": "auto"},
        "client": {"app_path": app if darwin else None,
                   "config_path": str(support / "kirocrew-desktop-nightly/config.json"),
                   "process_pattern": r"^/Applications/KiroCrew Nightly\.app/Contents/MacOS/" if darwin else None,
                   "executable": None, "local_gateway_port": 5476, "check_local_gateway": None},
        "tunnel": {"mode": "manual", "launch_label": "com.kirocrew.demo-tunnel",
                   "launch_plist_path": str(home / "Library/LaunchAgents/com.kirocrew.demo-tunnel.plist")},
        "telemetry": {"launch_label": "com.kirocrew.demo-observability", "interval_seconds": 60,
                      "launch_plist_path": str(home / "Library/LaunchAgents/com.kirocrew.demo-observability.plist"),
                      "state_dir": str(support / "kirocrew-demo-observability"),
                      "remote_collector_path": "/opt/kirocrew-demo/observability/collector.py"},
        "probe": {"port": 5607, "assets_dir": str(ROOT / "recordings/20260913/probe-presenter"),
                  "evidence_dir": str(ROOT / "evidence/probes"),
                  "expected_allowed_sha256": "34ebbefeb5f66527fbc80083c3b695a63e675c2093fd5f3f079a7c5bfe4b9160",
                  "remote_root": "/opt/kirocrew-demo"},
    }


def _require(value, message):
    if not value:
        raise ValueError(message)


def _match(value, pattern, label, optional=False):
    _require(optional and value is None or isinstance(value, str) and re.fullmatch(pattern, value) is not None,
             "Invalid config field: " + label)


def load_config(path=None, *, require_target=False):
    """Load explicit --config / KIRO_DEMO_CONFIG; no implicit local file or remote discovery.

    Relative local paths are relative to the config file. Paths in defaults remain
    project/home-relative absolute values. Remote paths must be absolute POSIX paths.
    AWS credentials belong only to the AWS CLI credential chain, never this file.
    """
    selected = path or os.environ.get("KIRO_DEMO_CONFIG")
    config = defaults()
    source = None
    if selected:
        source = Path(selected).expanduser().resolve(strict=True)
        _require(source.is_file() and source.stat().st_size <= 65536, "Config must be a JSON file smaller than 64 KiB.")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                _require(key not in result, "Duplicate config field: " + key)
                result[key] = value
            return result
        data = json.loads(source.read_text(), object_pairs_hook=unique)
        _require(isinstance(data, dict), "Config must be a JSON object.")
        _require(data.get("schema_version") == 1 and type(data["schema_version"]) is int, "Config schema_version must be 1.")
        _require(not set(data) - set(config), "Unknown top-level config fields; credentials are not accepted.")
        for section, values in data.items():
            if section == "schema_version":
                continue
            _require(isinstance(values, dict), "Config section must be an object: " + section)
            _require(not set(values) - set(config[section]), "Unknown fields in " + section + "; credentials are not accepted.")
            config[section].update(values)
        local_paths = {"aws": ("evidence_dir",), "ssh": ("config_path", "known_hosts_path"),
                       "client": ("app_path", "config_path", "executable"), "tunnel": ("launch_plist_path",),
                       "telemetry": ("launch_plist_path", "state_dir"), "probe": ("assets_dir", "evidence_dir")}
        for section, keys in local_paths.items():
            for key in keys:
                value = config[section][key]
                if value is None:
                    _require((section, key) in (("client", "app_path"), ("client", "executable")), "Path cannot be null: " + key)
                    continue
                _require(isinstance(value, str) and value and not any(c in value for c in "\x00\r\n"), "Invalid config path: " + key)
                target = Path(value).expanduser()
                config[section][key] = os.path.abspath(source.parent / target if not target.is_absolute() else target)
        if "app_path" in data.get("client", {}) and "process_pattern" not in data["client"]:
            app_path = config["client"]["app_path"]
            config["client"]["process_pattern"] = ("^" + re.escape(str(Path(app_path).expanduser())) + "/Contents/MacOS/") if app_path else None
    aws = config["aws"]
    _match(aws["region"], r"[a-z]{2}(?:-[a-z0-9]+)+-\d", "aws.region")
    _match(aws["account_id"], r"\d{12}", "aws.account_id", True)
    _match(aws["stack_name"], r"[A-Za-z][A-Za-z0-9-]{0,127}", "aws.stack_name", True)
    _match(aws["profile"], r"[A-Za-z0-9_.@/-]{1,128}", "aws.profile", True)
    _match(aws["stack_arn"], r"arn:(?:aws|aws-us-gov|aws-cn):cloudformation:[a-z0-9-]+:\d{12}:stack/[A-Za-z][A-Za-z0-9-]{0,127}/[a-f0-9-]{36}", "aws.stack_arn", True)
    _match(aws["instance_id"], r"i-[a-f0-9]{8}(?:[a-f0-9]{9})?", "aws.instance_id", True)
    _match(aws["instance_type"], r"[a-z0-9]+\.[a-z0-9]+", "aws.instance_type", True)
    _require(aws["architecture"] in (None, "arm64", "x86_64"), "Invalid aws.architecture")
    _match(aws["project_tag"], r"[A-Za-z0-9_.:/+=@ -]{1,128}", "aws.project_tag")
    if aws["stack_arn"]:
        pieces = aws["stack_arn"].split(":", 5)
        _require(pieces[3] == aws["region"] and pieces[4] == aws["account_id"] and pieces[5].split("/")[1] == aws["stack_name"],
                 "aws.stack_arn must match region, account_id and stack_name.")
    ssh = config["ssh"]
    for key in ("gateway_alias", "admin_alias"):
        _match(ssh[key], r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", "ssh." + key)
    _match(ssh["host_key_alias"], r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", "ssh.host_key_alias", True)
    _require(isinstance(ssh["aliases"], list) and len(ssh["aliases"]) == 2 and
             all(isinstance(alias, str) for alias in ssh["aliases"]) and set(ssh["aliases"]) == {ssh["gateway_alias"], ssh["admin_alias"]}, "ssh.aliases must contain gateway_alias and admin_alias exactly once.")
    _require(ssh["address_mode"] in ("auto", "public", "private"), "Invalid ssh.address_mode.")
    for section, key in (("ssh", "local_port"), ("ssh", "remote_port"), ("client", "local_gateway_port"), ("probe", "port")):
        value = config[section][key]
        _require(type(value) is int and 1 <= value <= 65535, "Invalid TCP port: " + section + "." + key)
    _require(config["tunnel"]["mode"] in ("manual", "launchagent"), "Invalid tunnel.mode.")
    for section in ("tunnel", "telemetry"):
        _match(config[section]["launch_label"], r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", section + ".launch_label")
    _require(type(config["telemetry"]["interval_seconds"]) is int and 15 <= config["telemetry"]["interval_seconds"] <= 3600, "Telemetry interval must be 15-3600 seconds.")
    for section, key in (("telemetry", "remote_collector_path"), ("probe", "remote_root")):
        _match(config[section][key], r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", section + "." + key)
        _require(".." not in config[section][key].split("/"), "Remote path traversal is not accepted.")
    _match(config["probe"]["expected_allowed_sha256"], r"[a-f0-9]{64}", "probe.expected_allowed_sha256")
    pattern = config["client"]["process_pattern"]
    if pattern is not None:
        _require(isinstance(pattern, str) and pattern.startswith("^") and len(pattern) <= 512, "client.process_pattern must be an anchored regex.")
        try:
            re.compile(pattern)
        except re.error:
            raise ValueError("client.process_pattern must be a valid anchored regex.") from None
    _require(config["client"]["check_local_gateway"] is None or type(config["client"]["check_local_gateway"]) is bool, "Invalid client.check_local_gateway.")
    if require_target:
        _require(source is not None, "Choose the deployment explicitly with --config PATH or KIRO_DEMO_CONFIG.")
        _require(aws["account_id"] and aws["stack_name"], "Set aws.account_id and aws.stack_name in the chosen config.")
    config["_config_path"] = str(source) if source else None
    return config


def ssh_options(config):
    """Fixed SSH guards shared by login and operator tools; no shell command input."""
    ssh = config["ssh"]
    _require(config["_config_path"] is not None, "Choose SSH deployment explicitly with --config PATH or KIRO_DEMO_CONFIG.")
    _require(ssh["host_key_alias"], "Set ssh.host_key_alias to the verified pinned host key alias.")
    known = Path(ssh["known_hosts_path"])
    _require(known.is_file() and not known.is_symlink(), "A regular pinned ssh.known_hosts_path file is required.")
    return ["-F", ssh["config_path"], "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "HostKeyAlias=" + ssh["host_key_alias"], "-o", "UserKnownHostsFile=" + str(known),
            "-o", "IdentitiesOnly=yes", "-o", "ForwardAgent=no"]
