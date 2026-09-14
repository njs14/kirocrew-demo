#!/usr/bin/env python3
"""Register the existing demo MCP in Crew's UI; optionally retire its duplicate hook.

The owner session and MCP credential stay in memory on the selected EC2 host.
Only bounded, scoped hashes and booleans return over pinned SSH. This is setup,
not a native tool execution or an enforcement acceptance test.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import shlex
import stat
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit

NAME = "aws-enforcement"
DENY = "@aws-enforcement/crew_denied"
POLICY = "/etc/kirocrew-demo/security-policy.json"
SOURCE_FILES = ("agent.py", "hooks.py", "platform/governance.py", "platform/policy_distribution.py",
                "dashboard/handlers/mcp_custom.py", "dashboard/handlers/security.py", "config/loader.py")


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def decode(data):
    return json.loads(data, object_pairs_hook=unique)


def absolute(value):
    require(isinstance(value, str) and re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", value)
            and not {".", ".."}.intersection(value.split("/")), "invalid_absolute_path")
    return value


def read_file(path, *, missing=False, root_owned=False, limit=2_000_000):
    """Reject symlinks, replaceable root-policy ancestors, devices and huge files."""
    path = Path(absolute(str(path)))
    parent_fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            except FileNotFoundError:
                if missing:
                    return None
                raise
            os.close(parent_fd)
            parent_fd = child
            meta = os.fstat(child)
            require(not meta.st_mode & 0o022 and (not root_owned or meta.st_uid == 0), "unsafe_file_ancestor")
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent_fd)
        except FileNotFoundError:
            if missing:
                return None
            raise
        try:
            meta = os.fstat(fd)
            require(stat.S_ISREG(meta.st_mode) and meta.st_nlink == 1 and meta.st_size <= limit,
                    "unsafe_file_type_or_size")
            require(not meta.st_mode & 0o022 and (not root_owned or meta.st_uid == 0), "unsafe_file_owner_or_mode")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(limit + 1)
            require(len(data) <= limit, "file_size_limit")
            return data
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def json_file(path, **kwargs):
    data = read_file(path, **kwargs)
    value = {} if data is None else decode(data)
    require(isinstance(value, dict), "json_object_required")
    return value, data


def demo_spec(agent):
    """An existing local fixture transport is the only allowed registration."""
    require(agent.get("name") == "enforcement-demo", "source_agent_identity_mismatch")
    spec = agent.get("mcpServers", {}).get(NAME)
    require(isinstance(spec, dict) and set(spec) == {"url", "headers"}, "unexpected_demo_spec_shape")
    parts = urlsplit(spec["url"])
    require(parts.scheme == "http" and parts.hostname == "127.0.0.1" and parts.path == "/mcp"
            and parts.port is not None and not parts.query and not parts.fragment and not parts.username,
            "demo_transport_must_be_remote_host_loopback")
    headers = spec["headers"]
    require(isinstance(headers, dict) and set(headers) == {"Authorization"}, "unexpected_demo_headers")
    credential = headers["Authorization"]
    require(isinstance(credential, str) and re.fullmatch(r"Bearer [A-Za-z0-9_-]{32,256}", credential),
            "invalid_demo_credential_shape")
    require(not any(isinstance(ref, str) and (ref == "*" or ref.startswith("@aws-enforcement"))
                    for ref in agent.get("allowedTools", [])),
            "source_agent_auto_approval_present")
    return copy.deepcopy(spec)


def entry_matches(entry, spec):
    return isinstance(entry, dict) and {key: value for key, value in entry.items() if key != "disabled"} == spec


def registration_state(store, materialized, globals_, spec):
    for value in (store, materialized, *globals_):
        require(isinstance(value.get("mcpServers", {}), dict), "invalid_mcp_server_map")
    require(all(NAME not in item.get("mcpServers", {}) for item in globals_), "global_name_collision")
    stored = store.get("mcpServers", {}).get(NAME)
    emitted = materialized.get("mcpServers", {}).get(NAME)
    if stored is None:
        require(emitted is None, "materialized_name_collision")
        return "add"
    require(entry_matches(stored, spec), "crew_entry_collision")
    require(stored.get("disabled", False) is False, "existing_crew_entry_disabled")
    require(emitted is not None and entry_matches(emitted, spec), "materialized_spec_mismatch")
    require(emitted.get("disabled", False) is False, "materialized_entry_disabled")
    require(not any(isinstance(ref, str) and (ref == "*" or ref.startswith("@aws-enforcement"))
                    for ref in materialized.get("allowedTools", [])),
            "governed_auto_approval_present")
    return "already_registered"


def retired_config(config):
    result = copy.deepcopy(config)
    hooks = result.get("hooks", {})
    require(isinstance(hooks, dict), "invalid_hooks")
    entries = hooks.get("auto_deny_tools", [])
    require(isinstance(entries, list) and all(isinstance(item, str) for item in entries), "invalid_deny_list")
    require(entries.count(DENY) <= 1, "duplicate_mutable_deny_entries")
    # Preserve every other exact entry and every unrelated configuration field.
    if DENY in entries:
        hooks["auto_deny_tools"] = [item for item in entries if item != DENY]
    return result


def policy_posture(snapshot):
    require(isinstance(snapshot, dict) and snapshot.get("has_policy") is True
            and snapshot.get("unavailable") is False, "live_managed_policy_required")
    dist = snapshot.get("distribution", {})
    require(dist.get("configured") is True and dist.get("source_scheme") == "file"
            and dist.get("on_unavailable") == "fail_closed" and not dist.get("error_code"),
            "live_managed_distribution_required")
    rows = [row for row in snapshot.get("scopes", []) if row.get("scope") == "mcp"]
    require(len(rows) == 1 and rows[0].get("governed") is True
            and rows[0].get("source") in {"policy", "policy+profile"}, "live_mcp_policy_required")
    return {"has_policy": True, "source_scheme": "file", "on_unavailable": "fail_closed",
            "mcp_governed": True, "mcp_source": rows[0]["source"]}


def command(argv, *, input=None, timeout=30):
    result = subprocess.run(argv, input=input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    require(result.returncode == 0 and len(result.stdout) <= 2_000_000, "remote_prerequisite_failed")
    return result.stdout


def service(request):
    raw = command(["/usr/bin/systemctl", "show", request["service"], "--no-pager",
                   "--property=MainPID,User,ActiveState,SubState,ExecMainStartTimestampMonotonic"])
    props = dict(line.split("=", 1) for line in raw.decode().splitlines() if "=" in line)
    require(props.get("User") == "crew" and props.get("ActiveState") == "active"
            and props.get("SubState") == "running" and props.get("MainPID", "0").isdigit(), "gateway_not_running")
    pid = int(props["MainPID"])
    require(pid > 1, "gateway_pid_missing")
    with open(f"/proc/{pid}/environ", "rb") as stream:
        raw_env = stream.read(1_000_001)
    require(len(raw_env) <= 1_000_000, "process_environment_limit")
    env = dict(item.decode().split("=", 1) for item in raw_env.split(b"\0") if b"=" in item)
    require(env.get("KIROCREW_HOME") == request["state_dir"], "gateway_state_directory_mismatch")
    require(env.get("KIROCREW_PORT") == str(request["port"]), "gateway_port_mismatch")
    require(env.get("KIROCREW_POLICY_URL") == "file://" + POLICY
            and env.get("KIROCREW_POLICY_ON_UNAVAILABLE") == "fail_closed"
            and not env.get("KIROCREW_SECURITY_POLICY"), "managed_process_policy_required")
    return {"pid": pid, "start": props["ExecMainStartTimestampMonotonic"]}


def owner_session_token(helper):
    read_file(helper, root_owned=True)
    output = command([helper, "token", "--ttl", "5m"]).decode()
    found = []
    for url in re.findall(r"https?://[^\s<>\"']+", output):
        found.extend(parse_qs(urlsplit(url).query).get("token", []))
    if not found:
        found = re.findall(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b", output)
    require(len(set(found)) == 1, "owner_token_not_unambiguous")
    return found[0]


def inventory(request, crew):
    home, state = crew.pw_dir, request["state_dir"]
    paths = {"agent": home + "/.kiro/agents/enforcement-demo.json",
             "materialized": home + "/.kiro/agents/kirocrew.json", "store": state + "/mcp.json",
             "config": state + "/config.json", "kiro_global": home + "/.kiro/settings/mcp.json",
             "claude_global": home + "/.claude.json"}
    objects, hashes = {}, {}
    for key, path in paths.items():
        objects[key], raw = json_file(path, missing=key in {"store", "kiro_global", "claude_global"})
        hashes[key] = sha(raw) if raw is not None else None
    spec = demo_spec(objects["agent"])
    state_value = registration_state(objects["store"], objects["materialized"],
                                     [objects["kiro_global"], objects["claude_global"]], spec)
    return paths, objects, hashes, spec, state_value


def policy_proof(request, root, snapshot):
    process = service(request)
    raw = read_file(POLICY, root_owned=True)
    from kiro_crew.platform import governance
    ceiling = governance.parse_policy(decode(raw))
    denied = governance.resolve(ceiling, None, "mcp", DENY)
    allowed = governance.resolve(ceiling, None, "mcp", "@aws-enforcement/read_allowed")
    require(denied.permitted is False and denied.layer == "policy" and allowed.permitted is True,
            "exact_managed_deny_required")
    # The boot-frozen process exposes counts, never the rule text. Bind its live
    # posture to the exact protected source, immutable parser and cache bytes.
    cache = read_file(request["state_dir"] + "/policy_cache/policy.json")
    require(cache == raw, "running_policy_cache_mismatch")
    sources = {name: sha(read_file(root + "/" + name, root_owned=True, limit=8_000_000)) for name in SOURCE_FILES}
    return {"process": process, "policy_sha256": sha(raw), "sources": sources,
            "exact_demo_tool_denied_by_policy": True, "allowed_demo_tool_permitted": True,
            "cache_matches_root_policy": True, "live": policy_posture(snapshot)}


async def http_json(http, method, url, *, body=None, allowed=(200,)):
    async with http.request(method, url, json=body, allow_redirects=False) as response:
        data = await response.content.read(2_000_001)
        require(len(data) <= 2_000_000 and response.status in allowed, "gateway_request_failed")
        value = decode(data)
        require(isinstance(value, dict), "invalid_gateway_response")
        return value


def retire_hook(request, paths, objects, before_hash):
    old = objects["config"]
    new = retired_config(old)
    if new == old:
        return None
    # Root's backup stores only the one prior hook field, never the full config.
    backup_dir = Path("/etc/kirocrew-demo/mcp-management")
    read_file(POLICY, root_owned=True)  # validates /etc/kirocrew-demo ancestors
    if not backup_dir.exists():
        backup_dir.mkdir(mode=0o700)
    meta = backup_dir.lstat()
    require(stat.S_ISDIR(meta.st_mode) and meta.st_uid == 0 and not meta.st_mode & 0o077, "unsafe_backup_directory")
    backup = backup_dir / (before_hash + "-hook.json")
    payload = encoded({"config_sha256": before_hash, "field": "hooks.auto_deny_tools",
                       "before": old["hooks"]["auto_deny_tools"], "after": new["hooks"]["auto_deny_tools"]})
    try:
        fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        # A failed config CAS can leave this exact before-field backup behind.
        # Reuse only the protected identical bytes; never overwrite a backup.
        require(stat.S_IMODE(backup.lstat().st_mode) == 0o600, "unsafe_existing_backup_mode")
        require(read_file(backup, root_owned=True, limit=128000) == payload, "existing_backup_mismatch")
    else:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    # The product's lock coordinates with its config writers; dropping root
    # before calling it prevents an editable config path becoming a root write.
    mutate_request = base64.b64encode(encoded({"path": paths["config"], "sha": sha(encoded(old)),
                                             "before": old["hooks"]["auto_deny_tools"],
                                             "after": new["hooks"]["auto_deny_tools"]})).decode()
    source = '''import base64, hashlib, json, sys
from pathlib import Path
from kiro_crew.config.loader import update_config_locked
r=json.loads(base64.b64decode(sys.argv[1]))
def mutate(data):
    actual=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    if actual != r["sha"] or data.get("hooks",{}).get("auto_deny_tools") != r["before"]:
        raise RuntimeError("stale_configuration")
    data["hooks"]["auto_deny_tools"]=r["after"]
    return data
update_config_locked(Path(r["path"]),mutate=mutate,fsync=True,stamp_meta=False)
'''
    command(["/usr/sbin/runuser", "-u", "crew", "--", request["python"], "-", mutate_request], input=source.encode())
    after, _ = json_file(paths["config"])
    require(after == new, "hook_retirement_preservation_failed")
    return {"backup_path": str(backup), "backup_sha256": sha(payload), "removed_only_exact_entry": True}


async def operate(request):
    import aiohttp
    require(os.geteuid() == 0 and sys.platform == "linux", "linux_root_required")
    crew = pwd.getpwnam("crew")
    require(crew.pw_uid != 0, "unprivileged_crew_required")
    spec_info = importlib.util.find_spec("kiro_crew")
    require(spec_info and spec_info.origin, "runtime_missing")
    root = str(Path(spec_info.origin).parent)
    base = "http://localhost:" + str(request["port"])
    token = owner_session_token(request["owner_helper"])
    async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(), trust_env=False,
                                     timeout=aiohttp.ClientTimeout(total=30), headers={"Origin": base}) as http:
        async with http.get(base + "/", params={"token": token}, allow_redirects=False) as response:
            require(response.status in (200, 302, 303), "owner_cookie_exchange_failed")
            require(len(await response.content.read(2_000_001)) <= 2_000_000, "response_limit")
        token = None
        snapshot = await http_json(http, "GET", base + "/api/governance/policy")
        proof = policy_proof(request, root, snapshot)
        paths, objects, hashes, spec, state_value = inventory(request, crew)
        planned_hook = retired_config(objects["config"]) != objects["config"] if request["retire_mutable_deny"] else False
        binding = {"deployment": request["deployment"], "service": request["service"], "port": request["port"],
                   "state_dir": request["state_dir"], "crew_uid": crew.pw_uid, "hashes": hashes,
                   "proof": proof, "helper_sha256": request["helper_sha256"]}
        plan = {"kind": "demo_mcp_plan", "schema_version": 1, "binding": binding,
                "registration": state_value, "retire_mutable_deny": request["retire_mutable_deny"],
                "hook_entry_will_be_removed": planned_hook, "gateway_restart_required": planned_hook,
                "scope": "crew_only", "native_enforcement_verified": False}
        plan["plan_id"] = sha(encoded(plan))
        if request["action"] == "plan":
            return plan
        if request["action"] == "verify":
            require(state_value == "already_registered", "mcp_registration_missing")
            return {"kind": "demo_mcp_verification", "schema_version": 1, "binding": binding,
                    "crew_only_enabled": True, "default_agent_materialized": True,
                    "governed_auto_approval_absent": True, "mutable_duplicate_present": DENY in
                    objects["config"].get("hooks", {}).get("auto_deny_tools", []), "native_enforcement_verified": False}
        require(request.get("apply") is True and request.get("expected") == plan, "exact_prior_plan_required")
        require(not planned_hook or request.get("restart_gateway") is True, "hook_retirement_requires_restart_flag")
        if state_value == "add":
            result = await http_json(http, "POST", base + "/api/mcp/custom", body={"servers": {NAME: spec}, "enable": True})
            require(result.get("ok") is True and result.get("added") == [NAME] and result.get("enabled") is True,
                    "mcp_add_not_confirmed")
        paths_after, objects_after, hashes_after, _, registered = inventory(request, crew)
        require(registered == "already_registered", "registration_not_materialized")
        require(all(hashes_after[key] == hashes[key] for key in ("agent", "config", "kiro_global", "claude_global")),
                "unrelated_configuration_changed")
        visible = await http_json(http, "GET", base + "/api/mcp/custom/" + NAME)
        require(visible.get("name") == NAME and visible.get("enabled") is True
                and visible.get("spec", {}).get("url") == spec["url"]
                and "autoApprove" not in visible.get("spec", {}), "mcp_ui_entry_not_confirmed")
        # Re-read the live floor immediately before removing the old mutable
        # hook. An ungoverned host can never retire it through this helper.
        after_proof = policy_proof(request, root, await http_json(http, "GET", base + "/api/governance/policy"))
        require(after_proof == proof, "policy_or_gateway_changed_during_setup")
        retirement = retire_hook(request, paths_after, objects_after, hashes_after["config"]) if planned_hook else None
    if retirement:
        command(["/usr/bin/systemctl", "restart", request["service"]], timeout=45)
        for _ in range(20):
            await asyncio.sleep(0.25)
            try:
                require(service(request)["start"] != proof["process"]["start"], "gateway_restart_not_observed")
                break
            except ValueError:
                continue
        else:
            raise ValueError("gateway_restart_not_observed")
    return {"kind": "demo_mcp_applied", "schema_version": 1, "plan_id": plan["plan_id"],
            "crew_only_enabled": True, "default_agent_materialized": True, "governed_auto_approval_absent": True,
            "global_configurations_unchanged": True, "source_agent_unchanged": True,
            "hook_retirement": retirement, "gateway_restarted": bool(retirement),
            "native_enforcement_verified": False,
            "next": "Run verify after restart, then demonstrate a fresh native managed denial in KiroCrew."}


def execute(args):
    from demo_config import load_config, ssh_options
    config = load_config(args.config, require_target=True)
    require(args.action == "apply" or not args.apply and args.plan_receipt is None, "apply_options_require_apply_action")
    request = {"action": args.action, "apply": args.apply, "retire_mutable_deny": args.retire_mutable_deny,
               "restart_gateway": args.restart_gateway,
               "state_dir": absolute(args.state_dir), "python": absolute(args.remote_python),
               "owner_helper": absolute(args.owner_helper), "service": args.service,
               "port": config["ssh"]["remote_port"], "deployment": {key: config["aws"][key]
               for key in ("region", "account_id", "stack_name")}}
    source = Path(__file__).read_bytes()
    request["helper_sha256"] = sha(source)
    if args.action == "apply":
        require(args.apply and args.plan_receipt, "apply_requires_flag_and_plan")
        raw = args.plan_receipt.read_bytes()
        require(len(raw) <= 128000 and not args.plan_receipt.is_symlink(), "invalid_plan_file")
        request["expected"] = decode(raw)
    encoded_request = base64.b64encode(encoded(request)).decode()
    argv = ["ssh", *ssh_options(config), "-o", "ConnectTimeout=10", config["ssh"]["admin_alias"],
            shlex.join(["sudo", "-n", args.remote_python, "-", "--remote-request", encoded_request])]
    result = subprocess.run(argv, input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=150)
    require(len(result.stdout) <= 128000, "report_size_limit")
    try:
        report = decode(result.stdout)
    except (ValueError, UnicodeDecodeError):
        raise ValueError("remote_operation_failed_without_public_report") from None
    require(isinstance(report, dict) and str(report.get("kind", "")).startswith("demo_mcp_"), "invalid_remote_report")
    require(result.returncode == 0 or "error" in report, "remote_operation_failed")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "apply", "verify"), nargs="?", default="plan")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--plan-receipt", type=Path)
    parser.add_argument("--retire-mutable-deny", action="store_true", help="Retire only the exact old hook after policy verification; restarts Gateway.")
    parser.add_argument("--restart-gateway", action="store_true", help="Required at apply when retiring an existing hook; interrupts Gateway sessions.")
    parser.add_argument("--state-dir", default="/var/lib/kirocrew")
    parser.add_argument("--remote-python", default="/opt/kirocrew/venv/bin/python3")
    parser.add_argument("--owner-helper", default="/usr/local/bin/kirocrew-owner-token")
    parser.add_argument("--service", default="kirocrew-demo.service")
    parser.add_argument("--remote-request", help=argparse.SUPPRESS)
    args = parser.parse_args()
    mutating = args.action == "apply"
    try:
        require(re.fullmatch(r"[A-Za-z0-9_-]+\.service", args.service), "invalid_service_name")
        if args.remote_request:
            require(len(args.remote_request) < 350000, "request_size_limit")
            request = decode(base64.b64decode(args.remote_request, validate=True))
            mutating = request.get("action") == "apply"
            report = asyncio.run(operate(request))
        else:
            report = execute(args)
    except Exception as exc:
        code = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[a-z_]+", str(exc)) else "operation_failed"
        report = {"kind": "demo_mcp_error", "error": code, "mutation_may_have_started": mutating,
                  "native_enforcement_verified": False}
    print(json.dumps(report, sort_keys=True, indent=2))
    return int("error" in report)


if __name__ == "__main__":
    raise SystemExit(main())
