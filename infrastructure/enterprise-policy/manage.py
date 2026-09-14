#!/usr/bin/env python3
"""Root-side managed-policy lifecycle. Reviewed source arrives over pinned SSH.

Install is additive and restart is a separate action. No credential, Gateway
configuration, mutable deny hook, existing profile or product source is changed.
"""
from __future__ import annotations

import argparse
import ast
import base64
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import pwd
import re
import shlex
import stat
import subprocess
import sys
import time
import uuid

POLICY = "/etc/kirocrew-demo/security-policy.json"
MANIFEST = "/etc/kirocrew-demo/enterprise-policy-install.json"
SOURCE_FILES = ("platform/governance.py", "platform/governance_profiles.py",
                "platform/policy_distribution.py", "platform/__init__.py", "platform/bootstrap.py", "platform/context.py", "hooks.py", "sandbox.py",
                "security/paths.py", "security/denied_rules.py", "dashboard/handlers/terminal.py", "safety_override.py")
MARKER = "KIROCREW_MANAGED_COMMAND_CONTROL"
DEVICES = ("/dev/null", "/dev/zero", "/dev/full", "/dev/random", "/dev/urandom")


def require(value, code):
    if not value:
        raise ValueError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def absolute(value):
    require(isinstance(value, str) and re.fullmatch(r"/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+", value)
            and not {".", ".."}.intersection(value.split("/")), "invalid_absolute_path")
    return value


class Tree:
    """No-follow descriptor traversal; an alternate root/UID is test-only."""

    def __init__(self, root="/", root_uid=0):
        self.root, self.root_uid = root, root_uid
        self.created_dirs = []

    def directory(self, path, create=False, root_only=True):
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in PurePosixPath(absolute(path)).parts[1:]:
                try:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError:
                    if not create:
                        raise
                    os.mkdir(part, 0o755, dir_fd=fd)
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    os.fchmod(child, 0o755)
                info = os.fstat(child)
                if (root_only and info.st_uid != self.root_uid) or info.st_mode & 0o022:
                    os.close(child)
                    raise ValueError("unprotected_directory_ancestor")
                os.close(fd)
                fd = child
            return fd
        except Exception:
            os.close(fd)
            raise

    def read(self, path, *, root_only=True, limit=4_000_000):
        item = PurePosixPath(absolute(path))
        parent = self.directory(str(item.parent), root_only=root_only)
        try:
            fd = os.open(item.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                info = os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= limit,
                        "unsafe_file_type_or_size")
                require((not root_only or info.st_uid == self.root_uid) and not info.st_mode & 0o022,
                        "unprotected_file")
                data = bytearray()
                while len(data) <= limit:
                    chunk = os.read(fd, min(65536, limit + 1 - len(data)))
                    if not chunk:
                        break
                    data.extend(chunk)
                require(len(data) <= limit, "file_size_limit")
                return bytes(data), {"sha256": sha(data), "uid": info.st_uid,
                                     "gid": info.st_gid, "mode": oct(stat.S_IMODE(info.st_mode)), "bytes": len(data)}
            finally:
                os.close(fd)
        finally:
            os.close(parent)

    def absent(self, path):
        item = PurePosixPath(absolute(path))
        try:
            parent = self.directory(str(item.parent))
        except FileNotFoundError:
            # Validate all existing ancestors, even when the destination parent
            # does not exist; the writer performs the same traversal again.
            return
        try:
            try:
                os.stat(item.name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                return
            raise ValueError("destination_exists")
        finally:
            os.close(parent)

    def write_new(self, path, data, mode=0o644):
        item = PurePosixPath(absolute(path))
        parent = self.directory(str(item.parent), create=True)
        try:
            fd = os.open(item.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=parent)
            try:
                os.fchmod(fd, mode)
                with os.fdopen(fd, "wb", closefd=False) as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                os.unlink(item.name, dir_fd=parent)
                raise
            finally:
                os.close(fd)
            os.fsync(parent)
        finally:
            os.close(parent)

    def remove_exact(self, path, expected_sha):
        data, _ = self.read(path)
        require(sha(data) == expected_sha, "rollback_file_changed")
        item = PurePosixPath(absolute(path))
        parent = self.directory(str(item.parent))
        try:
            os.unlink(item.name, dir_fd=parent)
            os.fsync(parent)
        finally:
            os.close(parent)


def run(argv):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40,
                            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"})
    require(result.returncode == 0 and len(result.stdout) <= 1_000_000, "system_command_failed")
    return result.stdout.decode()


def service_snapshot(service, tree):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}\.service", service), "invalid_service_name")
    raw = run(["systemctl", "show", service, "--property=User,Group,FragmentPath,DropInPaths,Environment,MainPID,ActiveState,ExecMainStartTimestampMonotonic,DevicePolicy,DeviceAllow"])
    rows = [line.split("=", 1) for line in raw.splitlines() if "=" in line]
    props = dict(rows)
    # systemctl show emits one DeviceAllow= line per rule. Preserve every
    # occurrence so verification evaluates the complete effective device set.
    props["DeviceAllow"] = " ".join(value for key, value in rows if key == "DeviceAllow")
    require(props.get("User") == "crew", "crew_service_required")
    units = [props.get("FragmentPath", ""), *shlex.split(props.get("DropInPaths", ""))]
    files = {absolute(path): tree.read(path)[1] for path in units}
    environ = dict(item.split("=", 1) for item in shlex.split(props.get("Environment", "")) if "=" in item)
    pid = int(props.get("MainPID") or 0)
    # Filter in memory; no token, AWS key or unrelated environment value enters
    # the receipt. /proc is a live kernel surface, not a managed regular file.
    proc_raw = b""
    if pid > 0:
        try:
            with open("/proc/" + str(pid) + "/environ", "rb") as stream:
                proc_raw = stream.read(1_000_001)
        except (FileNotFoundError, ProcessLookupError):
            pass  # A failed or restarting service must remain recoverable.
    require(len(proc_raw) <= 1_000_000, "process_environment_size_limit")
    proc_env = dict(item.decode().split("=", 1) for item in proc_raw.split(b"\0") if b"=" in item)
    def policy_env(values):
        return {key: value for key, value in values.items() if key.startswith("KIROCREW_POLICY_")
                or key == "KIROCREW_SECURITY_POLICY"}
    return {"files": files, "unit_environment_sha256": sha(props.get("Environment", "").encode()),
            "policy_environment": policy_env(environ), "process_policy_environment": policy_env(proc_env),
            "state_dir": environ.get("KIROCREW_HOME"), "main_pid": pid,
            "active_state": props.get("ActiveState", "unknown"),
            "started": props.get("ExecMainStartTimestampMonotonic"), "user": props["User"],
            "device_policy": props.get("DevicePolicy", ""), "device_allow": props.get("DeviceAllow", "")}


def terminal_before(config):
    dashboard = config.get("dashboard", {})
    require(isinstance(dashboard, dict), "invalid_dashboard_configuration")
    terminal = dashboard.get("terminal", {})
    require(isinstance(terminal, dict), "invalid_terminal_configuration")
    require("enabled" not in terminal or type(terminal["enabled"]) is bool, "invalid_terminal_enabled")
    return {"dashboard_present": "dashboard" in config, "terminal_present": "terminal" in dashboard,
            "enabled_present": "enabled" in terminal, "enabled": terminal.get("enabled")}


def patch_terminal(tree, state, crew, *, expected_sha=None, restore=None):
    """One field under the product's config.json.lock protocol, preserving peers."""
    path = absolute(state) + "/config.json"
    parent = tree.directory(state, root_only=False)
    lock = None
    temporary = ".enterprise-config-" + uuid.uuid4().hex
    try:
        try:
            lock = os.open("config.json.lock", os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError:
            lock = os.open("config.json.lock", os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            os.fchown(lock, crew.pw_uid, crew.pw_gid)
            os.fchmod(lock, 0o600)
        lock_info = os.fstat(lock)
        require(stat.S_ISREG(lock_info.st_mode) and lock_info.st_nlink == 1 and
                lock_info.st_uid in {tree.root_uid, crew.pw_uid} and not lock_info.st_mode & 0o022,
                "unsafe_configuration_lock")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("configuration_lock_busy") from None
        raw, meta = tree.read(path, root_only=False, limit=1_000_000)
        require(meta["uid"] in {tree.root_uid, crew.pw_uid}, "unexpected_gateway_configuration_owner")
        config = json.loads(raw)
        before = terminal_before(config)
        if restore is None:
            require(expected_sha is not None and sha(raw) == expected_sha, "configuration_changed_before_patch")
            config.setdefault("dashboard", {}).setdefault("terminal", {})["enabled"] = False
        else:
            require(before["enabled_present"] and before["enabled"] is False, "terminal_field_changed")
            target = config["dashboard"]["terminal"]
            if restore["enabled_present"]:
                target["enabled"] = restore["enabled"]
            else:
                target.pop("enabled")
            if not target and not restore["terminal_present"]:
                config["dashboard"].pop("terminal")
            if not config["dashboard"] and not restore["dashboard_present"]:
                config.pop("dashboard")
        data = encoded(config)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            os.fchown(fd, meta["uid"], meta["gid"])
            os.fchmod(fd, int(meta["mode"], 8))
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
        finally:
            os.close(fd)
        current_meta = tree.read(path, root_only=False, limit=1_000_000)[1]
        require(all(current_meta[key] == meta[key] for key in ("sha256", "uid", "gid", "mode")),
                "configuration_changed_during_patch")
        os.replace(temporary, "config.json", src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
        return {"before_sha256": sha(raw), "after_sha256": sha(data), "before": before,
                "changed_field": "dashboard.terminal.enabled", "owner_and_mode_preserved": True}
    finally:
        try:
            os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass
        if lock is not None:
            os.close(lock)
        os.close(parent)


def pinned_builtin_pattern(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "DeniedCommandRule":
            values = {item.arg: item.value for item in node.keywords}
            if isinstance(values.get("id"), ast.Constant) and values["id"].value == "credential-exfil-s3-cp":
                found.append(ast.literal_eval(values["pattern"]))
    require(len(found) == 1 and isinstance(found[0], str), "builtin_command_pattern_not_found")
    return found[0]


def render_policy(template, crew_home, source_root):
    require(isinstance(template, str) and len(template) < 16000, "invalid_policy_template")
    result = template.replace("__CREW_HOME__", absolute(crew_home)).replace("__SOURCE_ROOT__", absolute(source_root))
    require("__" not in result, "unresolved_policy_template")
    return encoded(json.loads(result))


def policy_checks(data, governance):
    ceiling = governance.parse_policy(json.loads(data))
    cases = [("mcp", "@aws-enforcement/crew_denied", False),
             ("mcp", "@aws-enforcement/read_allowed", True),
             ("mcp", "@aws-enforcement/mcp_denied", True),
             ("mcp", "@aws-enforcement/iam_denied", True),
             ("approval_modes", "yolo", False), ("approval_modes", "normal", True),
             ("commands", "printf '%s\\n' '" + MARKER + "'", False)]
    checks = []
    for scope, item, expected in cases:
        decision = governance.resolve(ceiling, None, scope, item)
        require(decision.permitted is expected, "unexpected_policy_decision")
        checks.append({"scope": scope, "item": item, "permitted": decision.permitted, "layer": decision.layer})
    floor = ceiling.get("sandbox.min_level")
    require(floor is not None and floor.value == "cc", "unexpected_sandbox_floor")
    return checks


def binding_for(request, tree, crew, source_root, snapshot):
    state = absolute(request["state_dir"])
    require(snapshot["state_dir"] == state, "service_state_directory_mismatch")
    config, config_meta = tree.read(state + "/config.json", root_only=False, limit=1_000_000)
    require(config_meta["uid"] in {tree.root_uid, crew.pw_uid}, "unexpected_gateway_configuration_owner")
    config_data = json.loads(config)
    require(config_data.get("agent", {}).get("approval_mode") == "interactive" and
            not config_data.get("agent", {}).get("dangerouslySkipPermissions"), "interactive_approval_required")
    require(not config_data.get("hooks", {}).get("auto_approve_tools"), "auto_approve_hooks_present")
    require(crew.pw_uid != 0, "unprivileged_crew_required")
    sources = {name: tree.read(absolute(source_root) + "/" + name)[1] for name in SOURCE_FILES}
    machine, _ = tree.read("/etc/machine-id", limit=256)
    return {"machine_id_sha256": sha(machine), "crew_uid": crew.pw_uid, "crew_home": crew.pw_dir,
            "source_root": source_root, "sources": sources, "service": request["service"],
            "service_files": snapshot["files"], "unit_environment_sha256": snapshot["unit_environment_sha256"],
            "state_dir": state, "gateway_config_sha256": sha(config),
            "gateway_config_uid": config_meta["uid"], "deployment": request["deployment"],
            "installer_sha256": request["installer_sha256"], "terminal_before": terminal_before(config_data),
            "device_policy": snapshot["device_policy"], "device_allow": snapshot["device_allow"]}


def plan_for(request, tree, crew, source_root, snapshot, governance):
    require(snapshot.get("active_state", "active") == "active" and snapshot["main_pid"] > 0,
            "active_crew_service_required")
    require(not snapshot["policy_environment"] and not snapshot["process_policy_environment"],
            "existing_policy_environment_requires_manual_review")
    require(not snapshot["device_allow"] and snapshot["device_policy"] == "auto", "existing_device_rules_require_manual_review")
    dropin = "/etc/systemd/system/" + request["service"] + ".d/60-kirocrew-enterprise-policy.conf"
    for path in (POLICY, MANIFEST, dropin):
        tree.absent(path)
    binding = binding_for(request, tree, crew, source_root, snapshot)
    policy = render_policy(request["template"], crew.pw_dir, source_root)
    builtin = pinned_builtin_pattern(tree.read(source_root + "/security/denied_rules.py")[0])
    require(builtin in json.loads(policy)["commands"]["deny"], "builtin_command_pattern_mismatch")
    checks = policy_checks(policy, governance)
    dropin_data = ("[Service]\nEnvironment=KIROCREW_POLICY_URL=file://" + POLICY +
                   "\nEnvironment=KIROCREW_POLICY_ON_UNAVAILABLE=fail_closed\n"
                   "DevicePolicy=strict\nDeviceAllow=\n" +
                   "".join("DeviceAllow=" + device + " rw\n" for device in DEVICES)).encode()
    files = {POLICY: {"content": policy.decode(), "mode": "0o644", "sha256": sha(policy)},
             dropin: {"content": dropin_data.decode(), "mode": "0o644", "sha256": sha(dropin_data)}}
    identity = {"binding": binding, "files": files}
    return {"kind": "enterprise_policy_plan", "schema_version": 1, **identity,
            "plan_id": sha(encoded(identity)), "parser_checks": checks,
            "restart_required": True, "native_enforcement_verified": False,
            "impact": ["Current Gateway connections and in-flight native turns are interrupted only by activate.",
                       "Apply leaves the running process unchanged; activate reloads and restarts exactly the named service.",
                       "Policy integrity rests on root-owned files and ancestors; host root remains the administrator.",
                       "Only dashboard.terminal.enabled changes in ordinary configuration; the duplicate MCP deny hook is preserved.",
                       "Strict device policy allows five standard pseudo devices; native PTY denial and backend compatibility need live checks."]}


def load_install(request, tree):
    data, meta = tree.read(MANIFEST, limit=128000)
    receipt = json.loads(data)
    require(receipt.get("kind") == "enterprise_policy_install" and receipt.get("schema_version") == 1,
            "invalid_install_manifest")
    plan = receipt["plan"]
    require(sha(encoded({"binding": plan["binding"], "files": plan["files"]})) == plan["plan_id"], "invalid_plan_id")
    require(plan["binding"]["deployment"] == request["deployment"] and
            plan["binding"]["service"] == request["service"], "installation_target_mismatch")
    # A reviewed tool update can inspect or recover an older installation.
    # Trust the root-protected manifest and exact prior plan ID here. Code hash
    # equality remains mandatory for the earlier plan-to-apply transition.
    require(request.get("expected_plan_id") == plan["plan_id"], "exact_installation_receipt_required")
    for path, expected in plan["files"].items():
        actual, info = tree.read(path)
        require(sha(actual) == expected["sha256"] and info["mode"] == expected["mode"], "managed_file_changed")
    return receipt, meta


def operate(request, *, tree=None, crew=None, source_root=None, governance=None, snapshotter=None):
    mode = request.get("mode")
    require(mode in {"preflight", "plan", "apply", "verify", "activate", "rollback"}, "invalid_mode")
    if tree is None:
        require(os.geteuid() == 0 and sys.platform == "linux", "linux_root_required")
        tree = Tree()
    crew = crew or pwd.getpwnam("crew")
    if source_root is None:
        spec = importlib.util.find_spec("kiro_crew")
        require(spec is not None and spec.origin is not None, "kirocrew_package_missing")
        source_root = str(Path(spec.origin).parent)
    snapshotter = snapshotter or service_snapshot
    if governance is None:
        from kiro_crew.platform import governance
    snapshot = snapshotter(request["service"], tree)
    if mode in {"preflight", "plan", "apply"}:
        plan = plan_for(request, tree, crew, source_root, snapshot, governance)
        if mode != "apply":
            return plan
        require(request.get("apply") is True and request.get("expected_plan") == plan, "exact_prior_plan_required")
        backup_path = "/etc/kirocrew-demo/enterprise-policy-before-" + plan["plan_id"] + ".json"
        backup = encoded({"kind": "enterprise_policy_before", "plan": plan, "destinations_previously_absent": True})
        tree.absent(backup_path)
        tree.write_new(backup_path, backup, 0o600)
        config_backup_path = backup_path.removesuffix(".json") + ".config.json"
        config_raw, _ = tree.read(request["state_dir"] + "/config.json", root_only=False, limit=1_000_000)
        require(sha(config_raw) == plan["binding"]["gateway_config_sha256"], "configuration_changed_before_backup")
        tree.write_new(config_backup_path, config_raw, 0o600)
        created = []
        patch = None
        try:
            for path, item in plan["files"].items():
                tree.write_new(path, item["content"].encode(), int(item["mode"], 8))
                created.append(path)
            patch = patch_terminal(tree, request["state_dir"], crew,
                                   expected_sha=plan["binding"]["gateway_config_sha256"])
            result = {"kind": "enterprise_policy_install", "schema_version": 1, "plan": plan,
                      "backup_path": backup_path, "backup_sha256": sha(backup), "activation_performed": False,
                      "config_backup_path": config_backup_path, "config_backup_sha256": sha(config_raw),
                      "terminal_patch": patch}
            tree.write_new(MANIFEST, encoded(result), 0o600)
        except Exception:
            if patch is not None:
                patch_terminal(tree, request["state_dir"], crew, restore=patch["before"])
            for path in reversed(created):
                tree.remove_exact(path, plan["files"][path]["sha256"])
            raise
        return result
    install, manifest_meta = load_install(request, tree)
    plan = install["plan"]
    # Bind immutable source/identity and unrelated unit/drop-in files again. Do
    # not require the user-editable config hash after install: tightening it is
    # legitimate, and verify must still describe the installed ceiling.
    current = binding_for(request, tree, crew, source_root, snapshot)
    for key in ("machine_id_sha256", "crew_uid", "crew_home", "source_root", "sources", "state_dir"):
        require(current[key] == plan["binding"][key], "runtime_binding_changed")
    own_dropin = next(path for path in plan["files"] if path.endswith(".conf"))
    observed_unrelated = {path: meta for path, meta in snapshot["files"].items() if path != own_dropin}
    require(observed_unrelated == plan["binding"]["service_files"], "unrelated_service_files_changed")
    policy_checks(tree.read(POLICY)[0], governance)
    if mode == "rollback":
        require(request.get("apply") is True, "explicit_mutation_flag_required")
        require(sha(tree.read(install["backup_path"])[0]) == install["backup_sha256"], "backup_changed")
        require(sha(tree.read(install["config_backup_path"])[0]) == install["config_backup_sha256"], "config_backup_changed")
        restored = patch_terminal(tree, request["state_dir"], crew, restore=install["terminal_patch"]["before"])
        for path, item in reversed(list(plan["files"].items())):
            tree.remove_exact(path, item["sha256"])
        tree.remove_exact(MANIFEST, manifest_meta["sha256"])
        run(["systemctl", "daemon-reload"])
        run(["systemctl", "restart", request["service"]])
        return {"kind": "enterprise_policy_rollback", "plan_id": plan["plan_id"],
                "removed_only_managed_files": True, "backup_retained": install["backup_path"],
                "terminal_field_restored": restored, "service_restarted": True, "native_enforcement_verified": False}
    if mode == "activate":
        require(request.get("apply") is True, "explicit_mutation_flag_required")
        previous = snapshot["started"]
        run(["systemctl", "daemon-reload"])
        run(["systemctl", "restart", request["service"]])
        for _ in range(20):
            time.sleep(0.25)
            snapshot = snapshotter(request["service"], tree)
            if (snapshot.get("active_state", "active") == "active" and snapshot["main_pid"] > 0
                    and snapshot["started"] != previous and snapshot["process_policy_environment"]):
                break
        require(snapshot.get("active_state", "active") == "active" and snapshot["main_pid"] > 0
                and snapshot["started"] != previous, "new_service_start_not_observed")
    expected_env = {"KIROCREW_POLICY_URL": "file://" + POLICY,
                    "KIROCREW_POLICY_ON_UNAVAILABLE": "fail_closed"}
    env_ok = snapshot["policy_environment"] == expected_env and snapshot["process_policy_environment"] == expected_env
    devices = snapshot["device_allow"].split()
    device_ok = snapshot["device_policy"] == "strict" and len(devices) == 2 * len(DEVICES) and {
        (devices[i], devices[i + 1]) for i in range(0, len(devices), 2)} == {(device, "rw") for device in DEVICES}
    current_config = json.loads(tree.read(request["state_dir"] + "/config.json", root_only=False, limit=1_000_000)[0])
    terminal = terminal_before(current_config)
    terminal_disabled = terminal["enabled_present"] and terminal["enabled"] is False
    if mode == "activate":
        require(env_ok, "managed_environment_not_active")
        require(device_ok, "managed_device_policy_not_active")
        require(terminal_disabled, "terminal_disabled_flag_missing")
    return {"kind": "enterprise_policy_verification", "plan_id": plan["plan_id"],
            "root_protected_managed_files_verified": True, "unit_and_process_policy_environment_active": env_ok,
            "unit_device_policy_matches": device_ok, "dashboard_terminal_disabled": terminal_disabled,
            "service_cgroup_pty_denial_verified": False,
            "main_pid": snapshot["main_pid"], "service_start": snapshot["started"],
            "service_active_state": snapshot.get("active_state", "unknown"),
            "activation_performed": mode == "activate", "native_enforcement_verified": False,
            "next": "Confirm the running Governance UI and a fresh native denial with no duplicate mutable hook."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    request = {}
    try:
        require(len(args.request) <= 350000, "request_size_limit")
        request = json.loads(base64.b64decode(args.request, validate=True))
        result = operate(request)
    except Exception as exc:
        error = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[a-z_]+", str(exc)) else "operation_failed"
        result = {"kind": "enterprise_policy_error", "error": error, "action": request.get("mode"),
                  "native_enforcement_verified": False,
                  "mutation_may_have_started": request.get("mode") in {"apply", "activate", "rollback"},
                  "recovery": "Inspect the managed files, retained before receipt and named service before retrying a failed mutation."}
    print(json.dumps(result, indent=2, sort_keys=True))
    return int("error" in result)


if __name__ == "__main__":
    raise SystemExit(main())
